#!/usr/bin/env python3
"""
Test script for ECMWF OpenCharts MCP Server
"""

import requests
import json
from datetime import datetime


def test_api_directly():
    """Test the ECMWF API directly"""
    print("=== Testing ECMWF OpenCharts API ===\n")

    # Test 1: List products (simulated)
    print("1. Available products:")
    products = [
        "extended-anomaly-z500",
        "extended-anomaly-2t",
        "medium-2t-mean-spread",
    ]
    for p in products:
        print(f"   - {p}")

    # Test 2: Get available times
    print("\n2. Testing get_available_times:")
    product_id = "extended-anomaly-z500"
    base_time = "2026-01-20T00:00:00Z"

    url = f"https://charts.ecmwf.int/opencharts-api/v1/products/{product_id}/"
    params = {"base_time": base_time, "valid_time": "2099-01-01T00:00:00Z"}

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            data = response.json()
            if "error" in data:
                error_msg = data["error"][0]
                print(f"   Error message: {error_msg[:100]}...")
                # Extract times
                import re

                match = re.search(r"\[(.*?)\]", error_msg)
                if match:
                    times_str = match.group(1)
                    times = eval(times_str)
                    print(f"   Available times: {times[:3]}...")
    except Exception as e:
        print(f"   Error: {e}")

    # Test 3: Fetch actual chart
    print("\n3. Testing fetch_ecmwf_chart:")
    valid_time = "2026-02-02T00:00:00Z"
    params = {"base_time": base_time, "valid_time": valid_time}

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "link" in data["data"]:
                image_url = data["data"]["link"]["href"]
                print(f"   ✓ Chart URL obtained: {image_url[:60]}...")

                # Download image
                img_response = requests.get(image_url, timeout=30)
                if img_response.status_code == 200:
                    size_kb = len(img_response.content) / 1024
                    print(f"   ✓ Image downloaded: {size_kb:.1f} KB")

                    # Save test image
                    with open("test_chart.png", "wb") as f:
                        f.write(img_response.content)
                    print(f"   ✓ Saved to test_chart.png")
                else:
                    print(f"   ✗ Failed to download image: {img_response.status_code}")
            else:
                print(f"   ✗ No image link in response")
        else:
            print(f"   ✗ API error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_api_directly()
