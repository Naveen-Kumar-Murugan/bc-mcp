import { useState, useEffect, useRef } from 'react'
import { Send, Bot, User, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'

interface ToolCall {
  tool_name: string
  arguments: any
  result: any
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  tool_calls?: ToolCall[]
  timestamp: Date
  status?: 'sending' | 'sent' | 'error'
}

interface Tool {
  name: string
  description: string
  inputSchema: any
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [availableTools, setAvailableTools] = useState<Tool[]>([])
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    // Initialize connection and get tools
    initializeConnection()
    
    // Focus input on mount
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    // Scroll to bottom when messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const initializeConnection = async () => {
    setConnectionStatus('connecting')
    try {
      const response = await fetch('/api/connect', {
        method: 'POST',
      })
      
      if (response.ok) {
        setConnectionStatus('connected')
        await loadTools()
      } else {
        setConnectionStatus('disconnected')
      }
    } catch (error) {
      console.error('Failed to connect:', error)
      setConnectionStatus('disconnected')
    }
  }

  const loadTools = async () => {
    try {
      const response = await fetch('/api/tools')
      if (response.ok) {
        const tools = await response.json()
        setAvailableTools(tools.tools)
      }
    } catch (error) {
      console.error('Failed to load tools:', error)
    }
  }

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
      status: 'sent'
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: inputValue,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      const result = await response.json()

      const lastMessage = result.messages[result.messages.length - 1]

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: lastMessage.role,
        content: lastMessage.content || 'No response received',
        tool_calls: lastMessage.tool_calls || [],
        timestamp: new Date(),
        status: 'sent'
      }

      setMessages(prev => [...prev, ...result.messages.map((msg: any) => ({
        id: Date.now().toString(),
        role: msg.role,
        content: msg.content,
        tool_calls: msg.tool_calls || [],
        timestamp: new Date(),
        status: 'sent'
      }))])
    } catch (error) {
      console.error('Error sending message:', error)
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request.',
        timestamp: new Date(),
        status: 'error'
      }

      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const formatArguments = (args: any) => {
    return JSON.stringify(args, null, 2)
  }

  const formatResult = (result: any) => {
    if (typeof result === 'string') {
      return result
    }
    return JSON.stringify(result, null, 2)
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Bot className="w-8 h-8 text-primary-600" />
            <div>
              <h1 className="text-xl font-semibold text-gray-900">MCP Chat Assistant</h1>
              <div className="flex items-center space-x-2 text-sm">
                <div className={`w-2 h-2 rounded-full ${
                  connectionStatus === 'connected' ? 'bg-green-500' : 
                  connectionStatus === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'
                }`} />
                <span className="text-gray-500">
                  {connectionStatus === 'connected' ? 'Connected' : 
                   connectionStatus === 'connecting' ? 'Connecting...' : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">
              {availableTools.length} tools available
            </span>
            <div className="flex space-x-1">
              {availableTools && availableTools.slice(0, 3).map((tool, index) => (
                <div
                  key={index}
                  className="px-2 py-1 bg-primary-100 text-primary-700 rounded-md text-xs"
                  title={tool.description}
                >
                  {tool.name}
                </div>
              ))}
              {availableTools.length > 3 && (
                <div className="px-2 py-1 bg-gray-100 text-gray-600 rounded-md text-xs">
                  +{availableTools.length - 3} more
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <Bot className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Welcome to MCP Chat Assistant
            </h3>
            <p className="text-gray-500">
              Start a conversation and I'll help you using the available MCP tools.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-3xl flex ${
                  message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                } space-x-3`}
              >
                <div className={`flex-shrink-0 ${message.role === 'user' ? 'ml-3' : 'mr-3'}`}>
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      message.role === 'user'
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-200 text-gray-600'
                    }`}
                  >
                    {message.role === 'user' ? (
                      <User className="w-4 h-4" />
                    ) : (
                      <Bot className="w-4 h-4" />
                    )}
                  </div>
                </div>

                <div className="flex-1">
                  <div
                    className={`rounded-lg px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-primary-600 text-white'
                        : 'bg-white border border-gray-200 text-gray-900'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    
                    {message.status === 'error' && (
                      <div className="mt-2 flex items-center space-x-1 text-red-600">
                        <AlertCircle className="w-4 h-4" />
                        <span className="text-sm">Error occurred</span>
                      </div>
                    )}
                  </div>

                  {/* Tool calls display */}
                  {message.tool_calls && message.tool_calls.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {message.tool_calls.map((toolCall, index) => (
                        <div
                          key={index}
                          className="bg-blue-50 border border-blue-200 rounded-lg p-3"
                        >
                          <div className="flex items-center space-x-2 mb-2">
                            {/* <Tool className="w-4 h-4 text-blue-600" /> */}
                            <span className="font-medium text-blue-900">
                              {toolCall.tool_name}
                            </span>
                            <CheckCircle className="w-4 h-4 text-green-600" />
                          </div>
                          
                          <div className="text-sm space-y-2">
                            <div>
                              <span className="font-medium text-gray-700">Arguments:</span>
                              <pre className="mt-1 bg-gray-100 p-2 rounded text-xs overflow-x-auto">
                                {formatArguments(toolCall.arguments)}
                              </pre>
                            </div>
                            
                            <div>
                              <span className="font-medium text-gray-700">Result:</span>
                              <pre className="mt-1 bg-gray-100 p-2 rounded text-xs overflow-x-auto">
                                {formatResult(toolCall.result)}
                              </pre>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="mt-1 text-xs text-gray-500">
                    {message.timestamp.toLocaleTimeString()}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="max-w-3xl flex flex-row space-x-3">
              <div className="flex-shrink-0 mr-3">
                <div className="w-8 h-8 rounded-full bg-gray-200 text-gray-600 flex items-center justify-center">
                  <Bot className="w-4 h-4" />
                </div>
              </div>
              <div className="flex-1">
                <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                  <div className="flex items-center space-x-2">
                    <Loader2 className="w-4 h-4 animate-spin text-primary-600" />
                    <span className="text-gray-600">Thinking...</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end space-x-3">
            <div className="flex-1">
              <div className="relative">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your message..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                  disabled={isLoading || connectionStatus !== 'connected'}
                />
                {connectionStatus !== 'connected' && (
                  <div className="absolute inset-0 bg-gray-100 bg-opacity-75 rounded-lg flex items-center justify-center">
                    <span className="text-gray-500 text-sm">
                      {connectionStatus === 'connecting' ? 'Connecting...' : 'Disconnected'}
                    </span>
                  </div>
                )}
              </div>
            </div>
            <button
              onClick={sendMessage}
              disabled={!inputValue.trim() || isLoading || connectionStatus !== 'connected'}
              className="px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}