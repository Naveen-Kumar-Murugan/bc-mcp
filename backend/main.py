#!/usr/bin/env python3
"""
BigCommerce MCP Server

This server provides tools to interact with BigCommerce API endpoints for:
- Products and Product Metafields
- Orders and Order Metafields  
- Customers and Customer Metafields
- Cart Operations
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Union
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

BASE_URL = f"https://api.bigcommerce.com/stores/{STORE_HASH}"
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

async def make_api_request(
    endpoint: str, 
    method: str = "GET", 
    params: Optional[Dict] = None,
    json_data: Optional[Dict] = None
) -> APIResponse:
    """Make API request to BigCommerce"""
    try:
        url = f"{BASE_URL}/{endpoint}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=HEADERS,
                params=params or {},
                json=json_data,
                timeout=30.0
            )
            
            if response.status_code in [200, 201]:
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
    
    response = await make_api_request("v3/catalog/products", params=params)
    
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
async def search_products(
    keyword: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 50,
    page: int = 1,
    sort_by: Optional[str] = None,
    sort_direction: Optional[str] = None,
    include: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search products in the BigCommerce catalog with advanced filtering options. 
    This tool allows you to search for products using keywords, filter by category, 
    price range, and sort results. It supports pagination and can include additional 
    product details like variants and images in the response.
    
    Args:
        keyword: Search term to find products by name, SKU, or description
        category_id: Filter products by specific category ID
        min_price: Filter products with price greater than or equal to this value
        max_price: Filter products with price less than or equal to this value
        limit: Number of products to return per page (default: 50, max: 250)
        page: Page number for paginated results (starts at 1)
        sort_by: Sort field (options: name, price, date_created, date_modified)
        sort_direction: Sort order (asc: ascending, desc: descending)
        include: Additional data to include (options: variants, images, custom_fields, bulk_pricing_rules, primary_image)
    """
    params = {
        "limit": min(limit, 250),
        "page": page
    }
    
    # Add parameters if they are provided
    if keyword:
        params["keyword"] = keyword
    if category_id:
        params["category_id"] = category_id
    if min_price:
        params["min_price"] = min_price
    if max_price:
        params["max_price"] = max_price
    if sort_by:
        params["sort"] = sort_by
    if sort_direction:
        params["direction"] = sort_direction
    if include:
        params["include"] = include
    
    response = await make_api_request("v3/catalog/products", params=params)
    
    if response.success:
        products_data = response.data.get("data", [])
        return {
            "success": True,
            "products": products_data,
            "meta": response.data.get("meta", {}),
            "message": f"Successfully fetched {len(products_data)} products"
        }
    else:
        return {
            "success": False,
            "products": [],
            "message": f"Error searching products: {response.message}"
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
        endpoint = f"v3/catalog/products/{product_id}/metafields"
        message_prefix = f"Retrieved metafields for product {product_id}"
    else:
        # Get all product metafields
        endpoint = "v3/catalog/products/metafields"
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
    endpoint = f"v3/catalog/products/{product_id}/metafields/{metafield_id}"
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

# CART TOOLS
@mcp.tool()
async def create_cart_with_product(
    product_id: Union[str, int],
    quantity: int = 1,
    variant_id: Optional[int] = None,
    options: Optional[List[Dict[str, Union[int, str]]]] = None
) -> Dict[str, Any]:
    """
    Create a new shopping cart and add a product to it. This tool initializes 
    a new cart session and adds the specified product with optional variants 
    and custom options. The cart can be used for further shopping or checkout operations.
    
    Args:
        product_id: Unique identifier of the product to add to cart
        quantity: Number of product units to add (minimum: 1)
        variant_id: Specific variant ID if the product has multiple variants
        options: Product customization options (e.g., size, color)
                Format: [{"option_id": int, "option_value": int|str}, ...]
    """
    if quantity < 1:
        return {
            "success": False,
            "cart": {},
            "message": "Quantity must be at least 1"
        }
    
    # Build line item
    line_item = {
        "product_id": product_id,
        "quantity": quantity
    }
    
    if variant_id:
        line_item["variant_id"] = variant_id
    if options:
        line_item["options"] = options
    
    request_data = {
        "line_items": [line_item]
    }
    
    # Include redirect_urls in the response
    endpoint = "v3/carts?include=redirect_urls"
    
    response = await make_api_request(endpoint, method="POST", json_data=request_data)
    
    if response.success:
        cart_data = response.data.get("data", {})
        return {
            "success": True,
            "cart": cart_data,
            "message": f"Successfully created cart with ID: {cart_data.get('id', 'unknown')}"
        }
    else:
        return {
            "success": False,
            "cart": {},
            "message": f"Error creating cart: {response.message}"
        }

@mcp.tool()
async def get_cart(
    cart_id: str,
    include: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve detailed information about a specific shopping cart. This tool fetches 
    cart contents, including products, quantities, prices, and any applied discounts. 
    You can optionally include additional data like redirect URLs and detailed product information.
    
    Args:
        cart_id: Unique identifier of the cart to retrieve
        include: Additional data to include in response 
                (options: redirect_urls, line_items.physical_items.options, line_items.digital_items.options)
    """
    endpoint = f"v3/carts/{cart_id}"
    params = {}
    
    if include:
        params["include"] = include
    
    response = await make_api_request(endpoint, params=params)
    
    if response.success:
        cart_data = response.data.get("data", {})
        return {
            "success": True,
            "cart": cart_data,
            "message": f"Successfully retrieved cart {cart_id}"
        }
    else:
        return {
            "success": False,
            "cart": {},
            "message": f"Error getting cart: {response.message}"
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
    
    response = await make_api_request("v2/orders", params=params)
    
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
        endpoint = f"v3/orders/{order_id}/metafields"
        message_prefix = f"Retrieved metafields for order {order_id}"
    else:
        # Get all order metafields
        endpoint = "v3/orders/metafields"
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
    endpoint = f"v3/orders/{order_id}/metafields/{metafield_id}"
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
    
    response = await make_api_request("v3/customers", params=params)
    
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
        endpoint =f"v3/customers/{customer_id}/metafields"
        message_prefix = f"Retrieved metafields for customer {customer_id}"
    else:
        # Get all customer metafields
        endpoint = "v3/customers/metafields"
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
    endpoint = f"v3/customers/{customer_id}/metafields/{metafield_id}"
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