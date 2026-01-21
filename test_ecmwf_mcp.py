#!/usr/bin/env python3
"""
Test script for ECMWF OpenCharts MCP Server
"""

import io
import requests
import json
from datetime import datetime

from PIL import Image as PILImage


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


def test_image_compression():
    """Test that image compression keeps output under Claude Desktop's 1MB limit"""
    print("\n=== Testing Image Compression ===\n")

    MAX_SIZE_BYTES = 700 * 1024  # Target size (leaves headroom for base64)
    MAX_DIMENSION = 1400
    CLAUDE_LIMIT = 1024 * 1024  # 1MB

    product_id = "extended-anomaly-z500"
    base_time = "2026-01-20T00:00:00Z"
    valid_time = "2026-02-02T00:00:00Z"

    url = f"https://charts.ecmwf.int/opencharts-api/v1/products/{product_id}/"
    params = {"base_time": base_time, "valid_time": valid_time}

    try:
        # Get chart metadata
        print("1. Fetching chart metadata...")
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            print(f"   ✗ API error: {response.status_code}")
            return False

        data = response.json()
        image_url = data["data"]["link"]["href"]
        print(f"   ✓ Got image URL")

        # Download original image
        print("\n2. Downloading original image...")
        img_response = requests.get(image_url, timeout=30)
        original_size = len(img_response.content)
        print(f"   Original size: {original_size / 1024:.1f} KB")

        # Open and get dimensions
        img = PILImage.open(io.BytesIO(img_response.content))
        print(f"   Original dimensions: {img.size[0]}x{img.size[1]}")

        # Resize if needed
        print("\n3. Applying compression...")
        if max(img.size) > MAX_DIMENSION:
            ratio = MAX_DIMENSION / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, PILImage.Resampling.LANCZOS)
            print(f"   Resized to: {img.size[0]}x{img.size[1]}")

        # Convert to RGB for JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Progressive quality reduction
        compressed_data: bytes = b""
        quality = 85
        while quality >= 30:
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            compressed_data = buffer.getvalue()
            if len(compressed_data) <= MAX_SIZE_BYTES:
                break
            quality -= 10

        compressed_size = len(compressed_data)
        base64_estimated = compressed_size * 1.33

        print(f"   Compressed size: {compressed_size / 1024:.1f} KB (quality={quality})")
        print(f"   Compression ratio: {compressed_size / original_size * 100:.1f}%")
        print(f"   Base64 estimated: {base64_estimated / 1024:.1f} KB")

        # Save compressed image for inspection
        with open("test_chart_compressed.jpg", "wb") as f:
            f.write(compressed_data)
        print(f"   ✓ Saved to test_chart_compressed.jpg")

        # Verify it fits under limit
        print("\n4. Checking Claude Desktop limit...")
        if base64_estimated < CLAUDE_LIMIT:
            print(f"   ✓ Will fit under 1MB limit ({base64_estimated / 1024:.1f} KB < 1024 KB)")
            return True
        else:
            print(f"   ✗ Still too large ({base64_estimated / 1024:.1f} KB >= 1024 KB)")
            return False

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


if __name__ == "__main__":
    test_api_directly()
    test_image_compression()
