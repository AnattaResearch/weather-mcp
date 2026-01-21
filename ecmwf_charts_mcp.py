#!/usr/bin/env python3
"""
ECMWF OpenCharts MCP Server
Provides tools to fetch weather charts from ECMWF OpenCharts API
"""

import json
import requests
from datetime import datetime, timedelta
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent
import mcp.server.stdio
import base64

app = Server("ecmwf-charts")

# Product catalog - key products for weather analysis
PRODUCTS = {
    # Sub-seasonal forecasts
    "extended-anomaly-z500": {
        "name": "500 hPa height: Weekly mean anomalies",
        "range": "sub-seasonal",
        "type": "forecast",
        "parameters": ["geopotential"],
    },
    "extended-anomaly-2t": {
        "name": "2m temperature: Weekly mean anomalies",
        "range": "sub-seasonal",
        "type": "forecast",
        "parameters": ["temperature"],
    },
    "extended-anomaly-uv": {
        "name": "10m wind: Weekly mean anomalies",
        "range": "sub-seasonal",
        "type": "forecast",
        "parameters": ["wind"],
    },
    # Medium range ENS forecasts
    "medium-2t-mean-spread": {
        "name": "Ensemble mean and spread: 2m temperature",
        "range": "medium",
        "type": "forecast",
        "parameters": ["temperature"],
    },
    "medium-t500-mean-spread": {
        "name": "Ensemble mean and spread: 500 hPa geopotential height",
        "range": "medium",
        "type": "forecast",
        "parameters": ["geopotential"],
    },
    "medium-10ws-mean-spread": {
        "name": "Ensemble mean and spread: 10m wind speed",
        "range": "medium",
        "type": "forecast",
        "parameters": ["wind"],
    },
    "medium-ens-wind": {
        "name": "Probabilities: 100m wind speed",
        "range": "medium",
        "type": "forecast",
        "parameters": ["wind"],
    },
}


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="fetch_ecmwf_chart",
            description="Fetch weather chart from ECMWF OpenCharts API. Returns chart image and metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": f"Product identifier. Available: {', '.join(PRODUCTS.keys())}",
                        "enum": list(PRODUCTS.keys()),
                    },
                    "base_time": {
                        "type": "string",
                        "description": "Base time in ISO format (YYYY-MM-DDTHH:MM:SSZ). Use latest available date.",
                    },
                    "valid_time": {
                        "type": "string",
                        "description": "Valid time in ISO format (YYYY-MM-DDTHH:MM:SSZ). Must be available for the product.",
                    },
                },
                "required": ["product_id", "base_time", "valid_time"],
            },
        ),
        Tool(
            name="list_ecmwf_products",
            description="List all available ECMWF chart products with descriptions",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter_range": {
                        "type": "string",
                        "description": "Filter by forecast range: medium, sub-seasonal",
                        "enum": ["medium", "sub-seasonal", "all"],
                    },
                    "filter_parameter": {
                        "type": "string",
                        "description": "Filter by parameter: temperature, wind, geopotential",
                        "enum": ["temperature", "wind", "geopotential", "all"],
                    },
                },
            },
        ),
        Tool(
            name="get_available_times",
            description="Get available valid times for a product and base time (makes API call to check)",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": f"Product identifier. Available: {', '.join(PRODUCTS.keys())}",
                        "enum": list(PRODUCTS.keys()),
                    },
                    "base_time": {
                        "type": "string",
                        "description": "Base time in ISO format (YYYY-MM-DDTHH:MM:SSZ)",
                    },
                },
                "required": ["product_id", "base_time"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent]:
    if name == "list_ecmwf_products":
        filter_range = arguments.get("filter_range", "all")
        filter_param = arguments.get("filter_parameter", "all")

        filtered = {}
        for pid, info in PRODUCTS.items():
            if filter_range != "all" and info["range"] != filter_range:
                continue
            if filter_param != "all" and filter_param not in info["parameters"]:
                continue
            filtered[pid] = info

        result = "# ECMWF OpenCharts Products\n\n"
        for pid, info in filtered.items():
            result += f"## {pid}\n"
            result += f"- Name: {info['name']}\n"
            result += f"- Range: {info['range']}\n"
            result += f"- Type: {info['type']}\n"
            result += f"- Parameters: {', '.join(info['parameters'])}\n\n"

        return [TextContent(type="text", text=result)]

    elif name == "get_available_times":
        product_id = arguments["product_id"]
        base_time = arguments["base_time"]

        # Make a test call to get error message with available times
        url = f"https://charts.ecmwf.int/opencharts-api/v1/products/{product_id}/"
        params = {"base_time": base_time, "valid_time": "2099-01-01T00:00:00Z"}

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                data = response.json()
                if "error" in data and len(data["error"]) > 0:
                    error_msg = data["error"][0]
                    # Extract available times from error message
                    if "available valid_time" in error_msg:
                        import re

                        match = re.search(r"\[(.*?)\]", error_msg)
                        if match:
                            times_str = match.group(1)
                            times = eval(times_str)  # Safe here as it's from ECMWF
                            result = f"Available valid times for {product_id}:\n\n"
                            for t in times:
                                result += f"- {t}\n"
                            return [TextContent(type="text", text=result)]

            return [
                TextContent(
                    type="text",
                    text=f"Could not determine available times for {product_id}",
                )
            ]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    elif name == "fetch_ecmwf_chart":
        product_id = arguments["product_id"]
        base_time = arguments["base_time"]
        valid_time = arguments["valid_time"]

        url = f"https://charts.ecmwf.int/opencharts-api/v1/products/{product_id}/"
        params = {"base_time": base_time, "valid_time": valid_time}

        try:
            # Get chart metadata
            response = requests.get(url, params=params, timeout=30)

            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error", ["Unknown error"])[0]
                return [TextContent(type="text", text=f"Error: {error_msg}")]

            data = response.json()

            # Extract image URL
            if "data" not in data or "link" not in data["data"]:
                return [
                    TextContent(
                        type="text", text="Error: No image link found in response"
                    )
                ]

            image_url = data["data"]["link"]["href"]

            # Download image
            img_response = requests.get(image_url, timeout=30)
            if img_response.status_code != 200:
                return [
                    TextContent(
                        type="text",
                        text=f"Error downloading image: {img_response.status_code}",
                    )
                ]

            # Encode image as base64
            image_b64 = base64.b64encode(img_response.content).decode("utf-8")

            # Build metadata
            product_info = PRODUCTS.get(product_id, {})
            metadata = f"""# ECMWF Chart: {product_info.get('name', product_id)}

**Product ID:** {product_id}
**Range:** {product_info.get('range', 'N/A')}
**Parameters:** {', '.join(product_info.get('parameters', []))}

**Base time:** {base_time}
**Valid time:** {valid_time}

**Image URL:** {image_url}
**Size:** {len(img_response.content)} bytes
"""

            return [
                TextContent(type="text", text=metadata),
                ImageContent(type="image", data=image_b64, mimeType="image/png"),
            ]

        except requests.exceptions.RequestException as e:
            return [TextContent(type="text", text=f"Network error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
