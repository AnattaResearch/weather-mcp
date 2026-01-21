#!/usr/bin/env python3
"""
ECMWF OpenCharts MCP Server
Provides tools to fetch weather charts from ECMWF OpenCharts API

Built with FastMCP
"""

import re
from typing import Annotated, Literal

import requests
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from pydantic import Field

# Initialize FastMCP server
mcp = FastMCP("ecmwf-charts")

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

# Type alias for product IDs
ProductId = Literal[
    "extended-anomaly-z500",
    "extended-anomaly-2t",
    "extended-anomaly-uv",
    "medium-2t-mean-spread",
    "medium-t500-mean-spread",
    "medium-10ws-mean-spread",
    "medium-ens-wind",
]


@mcp.tool
def list_ecmwf_products(
    filter_range: Annotated[
        Literal["medium", "sub-seasonal", "all"],
        Field(description="Filter by forecast range"),
    ] = "all",
    filter_parameter: Annotated[
        Literal["temperature", "wind", "geopotential", "all"],
        Field(description="Filter by parameter type"),
    ] = "all",
) -> str:
    """List all available ECMWF chart products with descriptions."""
    filtered = {}
    for pid, info in PRODUCTS.items():
        if filter_range != "all" and info["range"] != filter_range:
            continue
        if filter_parameter != "all" and filter_parameter not in info["parameters"]:
            continue
        filtered[pid] = info

    result = "# ECMWF OpenCharts Products\n\n"
    for pid, info in filtered.items():
        result += f"## {pid}\n"
        result += f"- Name: {info['name']}\n"
        result += f"- Range: {info['range']}\n"
        result += f"- Type: {info['type']}\n"
        result += f"- Parameters: {', '.join(info['parameters'])}\n\n"

    return result


@mcp.tool
def get_available_times(
    product_id: Annotated[
        ProductId,
        Field(description="Product identifier"),
    ],
    base_time: Annotated[
        str,
        Field(description="Base time in ISO format (YYYY-MM-DDTHH:MM:SSZ)"),
    ],
) -> str:
    """Get available valid times for a product and base time (makes API call to check)."""
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
                    match = re.search(r"\[(.*?)\]", error_msg)
                    if match:
                        times_str = match.group(1)
                        times = eval(times_str)  # Safe here as it's from ECMWF
                        result = f"Available valid times for {product_id}:\n\n"
                        for t in times:
                            result += f"- {t}\n"
                        return result

        return f"Could not determine available times for {product_id}"

    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool
def fetch_ecmwf_chart(
    product_id: Annotated[
        ProductId,
        Field(description="Product identifier"),
    ],
    base_time: Annotated[
        str,
        Field(description="Base time in ISO format (YYYY-MM-DDTHH:MM:SSZ). Use latest available date."),
    ],
    valid_time: Annotated[
        str,
        Field(description="Valid time in ISO format (YYYY-MM-DDTHH:MM:SSZ). Must be available for the product."),
    ],
) -> list[str | Image]:
    """Fetch weather chart from ECMWF OpenCharts API. Returns chart image and metadata."""
    url = f"https://charts.ecmwf.int/opencharts-api/v1/products/{product_id}/"
    params = {"base_time": base_time, "valid_time": valid_time}

    try:
        # Get chart metadata
        response = requests.get(url, params=params, timeout=30)

        if response.status_code != 200:
            error_data = response.json()
            error_msg = error_data.get("error", ["Unknown error"])[0]
            return [f"Error: {error_msg}"]

        data = response.json()

        # Extract image URL
        if "data" not in data or "link" not in data["data"]:
            return ["Error: No image link found in response"]

        image_url = data["data"]["link"]["href"]

        # Download image
        img_response = requests.get(image_url, timeout=30)
        if img_response.status_code != 200:
            return [f"Error downloading image: {img_response.status_code}"]

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

        # Return metadata and image using FastMCP's Image helper
        return [metadata, Image(data=img_response.content, format="png")]

    except requests.exceptions.RequestException as e:
        return [f"Network error: {str(e)}"]
    except Exception as e:
        return [f"Error: {str(e)}"]


if __name__ == "__main__":
    mcp.run()
