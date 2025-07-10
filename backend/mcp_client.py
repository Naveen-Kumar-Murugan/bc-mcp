from typing import Optional
import traceback
import asyncio
import subprocess
import weakref
import atexit

from utils.logger import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from datetime import datetime
import json
import os

from openai import OpenAI
from openai.types.chat import ChatCompletion


class MCPClient:
    _instances = weakref.WeakSet()
    
    def __init__(self, model_name: str = "anthropic/claude-3.5-haiku"):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.stdio = None
        self.write = None
        self._server_process = None
        self._stdio_context = None
        self._session_context = None
        
        # Initialize OpenRouter client
        self.llm = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model_name = model_name
        
        self.tools = []
        self.messages = []
        self.logger = logger
        self._connected = False
        
        # Track instances for cleanup
        MCPClient._instances.add(self)

    # connect to the MCP server
    async def connect_to_server(self, server_script_path: str):
        if self._connected:
            return True
            
        try:
            is_python = server_script_path.endswith(".py")
            is_js = server_script_path.endswith(".js")
            if not (is_python or is_js):
                raise ValueError("Server script must be a .py or .js file")

            command = "python" if is_python else "node"
            server_params = StdioServerParameters(
                command=command, args=[server_script_path], env=None
            )

            # Create the stdio connection
            self._stdio_context = stdio_client(server_params)
            self.stdio, self.write = await self._stdio_context.__aenter__()
            
            # Create the session
            self._session_context = ClientSession(self.stdio, self.write)
            self.session = await self._session_context.__aenter__()
            
            # Initialize the session
            await self.session.initialize()
            
            self._connected = True
            self.logger.info("Connected to MCP server")
            
            # Get tools
            mcp_tools = await self.get_mcp_tools()
            self.tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    }
                }
                for tool in mcp_tools
            ]

            self.logger.info(
                f"Available tools: {[tool['function']['name'] for tool in self.tools]}"
            )
            
            return True

        except Exception as e:
            self.logger.error(f"Error connecting to MCP server: {e}")
            traceback.print_exc()
            await self._cleanup_connection()
            raise

    async def _cleanup_connection(self):
        """Clean up the connection safely"""
        try:
            self._connected = False
            
            # Clean up session
            if self._session_context and self.session:
                try:
                    await self._session_context.__aexit__(None, None, None)
                except Exception as e:
                    self.logger.error(f"Error closing session: {e}")
                finally:
                    self._session_context = None
                    self.session = None
            
            # Clean up stdio
            if self._stdio_context:
                try:
                    await self._stdio_context.__aexit__(None, None, None)
                except Exception as e:
                    self.logger.error(f"Error closing stdio: {e}")
                finally:
                    self._stdio_context = None
                    self.stdio = None
                    self.write = None
            
        except Exception as e:
            self.logger.error(f"Error during connection cleanup: {e}")

    # get mcp tool list
    async def get_mcp_tools(self):
        try:
            if not self.session:
                raise RuntimeError("Not connected to MCP server")
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            self.logger.error(f"Error getting MCP tools: {e}")
            raise

    # process query
    async def process_query(self, query: str):
        try:
            if not self._connected:
                raise RuntimeError("Not connected to MCP server")
                
            self.logger.info(f"Processing query: {query}")
            user_message = {"role": "user", "content": query}
            self.messages = [user_message]

            while True:
                response = await self.call_llm()

                # the response is a text message
                if response.choices[0].message.content and not response.choices[0].message.tool_calls:
                    assistant_message = {
                        "role": "assistant",
                        "content": response.choices[0].message.content,
                    }
                    self.messages.append(assistant_message)
                    await self.log_conversation()
                    break

                # the response includes tool calls
                assistant_message = {
                    "role": "assistant",
                    "content": response.choices[0].message.content,
                    "tool_calls": response.choices[0].message.tool_calls,
                }
                self.messages.append(assistant_message)
                await self.log_conversation()

                for tool_call in response.choices[0].message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_call_id = tool_call.id
                    
                    self.logger.info(
                        f"Calling tool {tool_name} with args {tool_args}"
                    )
                    try:
                        if not self.session:
                            raise RuntimeError("Session is not available")
                        result = await self.session.call_tool(tool_name, tool_args)
                        self.logger.info(f"Tool {tool_name} result: {result}...")
                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": str(result.content),
                            }
                        )
                        await self.log_conversation()
                    except Exception as e:
                        self.logger.error(f"Error calling tool {tool_name}: {e}")
                        raise

            return self.messages

        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            raise

    # call llm
    async def call_llm(self):
        try:
            self.logger.info("Calling LLM")
            return self.llm.chat.completions.create(
                model=self.model_name,
                messages=self.messages,
                tools=self.tools if self.tools else None,
                max_tokens=1000,
            )
        except Exception as e:
            self.logger.error(f"Error calling LLM: {e}")
            raise

    # cleanup
    async def cleanup(self):
        try:
            await self._cleanup_connection()
            self.logger.info("Disconnected from MCP server")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            traceback.print_exc()

    async def log_conversation(self):
        """Log the conversation - implement this method as needed"""
        pass

    def __del__(self):
        """Destructor to ensure cleanup"""
        if self._connected:
            # If there's still an active connection, we need to clean it up
            # This is a fallback - proper cleanup should be done explicitly
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._cleanup_connection())
            except Exception:
                pass

    @classmethod
    async def cleanup_all(cls):
        """Cleanup all instances - useful for application shutdown"""
        for instance in list(cls._instances):
            try:
                await instance.cleanup()
            except Exception as e:
                print(f"Error cleaning up MCP client instance: {e}")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
        return False


# Register cleanup function for application shutdown
@atexit.register
def cleanup_on_exit():
    """Cleanup function for application shutdown"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(MCPClient.cleanup_all())
    except Exception:
        pass