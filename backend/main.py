#!/usr/bin/env python3
"""
BigCommerce MCP Server

This server provides tools to interact with BigCommerce API endpoints for:
- Products and Product Metafields
- Orders and Order Metafields  
- Customers and Customer Metafields
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import httpx
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Configuration
STORE_HASH = os.getenv("BIGCOMMERCE_STORE_HASH")
ACCESS_TOKEN = os.getenv("BIGCOMMERCE_ACCESS_TOKEN")

if not STORE_HASH or not ACCESS_TOKEN:
    raise ValueError("Please set BIGCOMMERCE_STORE_HASH and BIGCOMMERCE_ACCESS_TOKEN in .env file")

BASE_URL = f"https://api.bigcommerce.com/stores/{STORE_HASH}/v3"
HEADERS = {
    "X-Auth-Token": ACCESS_TOKEN,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Initialize FastMCP server
mcp = FastMCP("BigCommerce MCP Server")

@dataclass
class APIResponse:
    """Standard API response format"""
    success: bool
    data: Any
    message: str = ""
    status_code: int = 200

async def make_api_request(endpoint: str, method: str = "GET", params: Optional[Dict] = None) -> APIResponse:
    """Make API request to BigCommerce"""
    try:
        url = f"{BASE_URL}/{endpoint}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=HEADERS,
                params=params or {},
                timeout=30.0
            )
            
            if response.status_code == 200:
                return APIResponse(
                    success=True,
                    data=response.json(),
                    status_code=response.status_code
                )
            else:
                return APIResponse(
                    success=False,
                    data=None,
                    message=f"API Error: {response.status_code} - {response.text}",
                    status_code=response.status_code
                )
                
    except Exception as e:
        return APIResponse(
            success=False,
            data=None,
            message=f"Request failed: {str(e)}",
            status_code=500
        )

# PRODUCTS TOOLS
@mcp.tool()
async def get_all_products(limit: int = 50, page: int = 1) -> Dict[str, Any]:
    """
    Get all products from BigCommerce store
    
    Args:
        limit: Number of products to return (default: 50, max: 250)
        page: Page number (default: 1)
    """
    params = {
        "limit": min(limit, 250),
        "page": page
    }
    
    response = await make_api_request("catalog/products", params=params)
    
    if response.success:
        return {
            "success": True,
            "products": response.data.get("data", []),
            "meta": response.data.get("meta", {}),
            "message": f"Retrieved {len(response.data.get('data', []))} products"
        }
    else:
        return {
            "success": False,
            "products": [],
            "message": response.message
        }

@mcp.tool()
async def get_all_product_metafields(product_id: Optional[int] = None, limit: int = 50, page: int = 1) -> Dict[str, Any]:
    """
    Get all product metafields. If product_id is provided, get metafields for that product.
    
    Args:
        product_id: Specific product ID to get metafields for (optional)
        limit: Number of metafields to return (default: 50, max: 250)
        page: Page number (default: 1)
    """
    params = {
        "limit": min(limit, 250),
        "page": page
    }
    
    if product_id:
        # Get metafields for specific product
        endpoint = f"catalog/products/{product_id}/metafields"
        message_prefix = f"Retrieved metafields for product {product_id}"
    else:
        # Get all product metafields
        endpoint = "catalog/products/metafields"
        message_prefix = "Retrieved all product metafields"
    
    response = await make_api_request(endpoint, params=params)
    
    if response.success:
        return {
            "success": True,
            "metafields": response.data.get("data", []),
            "meta": response.data.get("meta", {}),
            "message": f"{message_prefix}: {len(response.data.get('data', []))} metafields"
        }
    else:
        return {
            "success": False,
            "metafields": [],
            "message": response.message
        }

@mcp.tool()
async def get_product_metafield_by_id(product_id: int, metafield_id: int) -> Dict[str, Any]:
    """
    Get a specific product metafield by ID
    
    Args:
        product_id: Product ID
        metafield_id: Metafield ID
    """
    endpoint = f"catalog/products/{product_id}/metafields/{metafield_id}"
    response = await make_api_request(endpoint)
    
    if response.success:
        return {
            "success": True,
            "metafield": response.data.get("data", {}),
            "message": f"Retrieved metafield {metafield_id} for product {product_id}"
        }
    else:
        return {
            "success": False,
            "metafield": {},
            "message": response.message
        }

# ORDERS TOOLS
@mcp.tool()
async def get_all_orders(limit: int = 50, page: int = 1, status_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get all orders from BigCommerce store
    
    Args:
        limit: Number of orders to return (default: 50, max: 250)
        page: Page number (default: 1)
        status_id: Filter by order status ID (optional)
    """
    params = {
        "limit": min(limit, 250),
        "page": page
    }
    
    if status_id:
        params["status_id"] = status_id
    
    response = await make_api_request("orders", params=params)
    
    if response.success:
        return {
            "success": True,
            "orders": response.data.get("data", []),
            "meta": response.data.get("meta", {}),
            "message": f"Retrieved {len(response.data.get('data', []))} orders"
        }
    else:
        return {
            "success": False,
            "orders": [],
            "message": response.message
        }

@mcp.tool()
async def get_all_order_metafields(order_id: Optional[int] = None, limit: int = 50, page: int = 1) -> Dict[str, Any]:
    """
    Get all order metafields. If order_id is provided, get metafields for that order.
    
    Args:
        order_id: Specific order ID to get metafields for (optional)
        limit: Number of metafields to return (default: 50, max: 250)
        page: Page number (default: 1)
    """
    params = {
        "limit": min(limit, 250),
        "page": page
    }
    
    if order_id:
        # Get metafields for specific order
        endpoint = f"orders/{order_id}/metafields"
        message_prefix = f"Retrieved metafields for order {order_id}"
    else:
        # Get all order metafields
        endpoint = "orders/metafields"
        message_prefix = "Retrieved all order metafields"
    
    response = await make_api_request(endpoint, params=params)
    
    if response.success:
        return {
            "success": True,
            "metafields": response.data.get("data", []),
            "meta": response.data.get("meta", {}),
            "message": f"{message_prefix}: {len(response.data.get('data', []))} metafields"
        }
    else:
        return {
            "success": False,
            "metafields": [],
            "message": response.message
        }

@mcp.tool()
async def get_order_metafield_by_id(order_id: int, metafield_id: int) -> Dict[str, Any]:
    """
    Get a specific order metafield by ID
    
    Args:
        order_id: Order ID
        metafield_id: Metafield ID
    """
    endpoint = f"orders/{order_id}/metafields/{metafield_id}"
    response = await make_api_request(endpoint)
    
    if response.success:
        return {
            "success": True,
            "metafield": response.data.get("data", {}),
            "message": f"Retrieved metafield {metafield_id} for order {order_id}"
        }
    else:
        return {
            "success": False,
            "metafield": {},
            "message": response.message
        }

# CUSTOMERS TOOLS
@mcp.tool()
async def get_all_customers(limit: int = 50, page: int = 1) -> Dict[str, Any]:
    """
    Get all customers from BigCommerce store
    
    Args:
        limit: Number of customers to return (default: 50, max: 250)
        page: Page number (default: 1)
    """
    params = {
        "limit": min(limit, 250),
        "page": page
    }
    
    response = await make_api_request("customers", params=params)
    
    if response.success:
        return {
            "success": True,
            "customers": response.data.get("data", []),
            "meta": response.data.get("meta", {}),
            "message": f"Retrieved {len(response.data.get('data', []))} customers"
        }
    else:
        return {
            "success": False,
            "customers": [],
            "message": response.message
        }

@mcp.tool()
async def get_all_customer_metafields(customer_id: Optional[int] = None, limit: int = 50, page: int = 1) -> Dict[str, Any]:
    """
    Get all customer metafields. If customer_id is provided, get metafields for that customer.
    
    Args:
        customer_id: Specific customer ID to get metafields for (optional)
        limit: Number of metafields to return (default: 50, max: 250)
        page: Page number (default: 1)
    """
    params = {
        "limit": min(limit, 250),
        "page": page
    }
    
    if customer_id:
        # Get metafields for specific customer
        endpoint = f"customers/{customer_id}/metafields"
        message_prefix = f"Retrieved metafields for customer {customer_id}"
    else:
        # Get all customer metafields
        endpoint = "customers/metafields"
        message_prefix = "Retrieved all customer metafields"
    
    response = await make_api_request(endpoint, params=params)
    
    if response.success:
        return {
            "success": True,
            "metafields": response.data.get("data", []),
            "meta": response.data.get("meta", {}),
            "message": f"{message_prefix}: {len(response.data.get('data', []))} metafields"
        }
    else:
        return {
            "success": False,
            "metafields": [],
            "message": response.message
        }

@mcp.tool()
async def get_customer_metafield_by_id(customer_id: int, metafield_id: int) -> Dict[str, Any]:
    """
    Get a specific customer metafield by ID
    
    Args:
        customer_id: Customer ID
        metafield_id: Metafield ID
    """
    endpoint = f"customers/{customer_id}/metafields/{metafield_id}"
    response = await make_api_request(endpoint)
    
    if response.success:
        return {
            "success": True,
            "metafield": response.data.get("data", {}),
            "message": f"Retrieved metafield {metafield_id} for customer {customer_id}"
        }
    else:
        return {
            "success": False,
            "metafield": {},
            "message": response.message
        }

if __name__ == "__main__":
    # Run the server
    mcp.run()