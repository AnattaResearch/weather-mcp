# ECMWF OpenCharts MCP Server

MCP server for fetching weather charts from ECMWF OpenCharts API. Built with [FastMCP](https://github.com/jlowin/fastmcp).

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

### stdio mode (for Claude Desktop)

```bash
python ecmwf_charts_mcp.py
```

### HTTP mode (for remote access)

```bash
python -c "from ecmwf_charts_mcp import mcp; mcp.run(transport='http', port=8000)"
```

### Deploy to Railway (MCP HTTP transport)

This repo includes a `Procfile` and `railway.toml` that start the MCP server over HTTP using the
FastMCP CLI. Railway provides the `PORT` environment variable automatically.

**Steps:**
1. Create a new Railway project and link this repository.
2. Ensure the start command is `fastmcp run ecmwf_charts_mcp.py:mcp --transport http --port $PORT`
   (preconfigured in `railway.toml`).
3. Deploy, then configure your MCP-capable client to connect to the Railway URL.

## Configuration

### Claude Desktop

Add to Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS or `~/.config/Claude/claude_desktop_config.json` on Linux):

```json
{
  "mcpServers": {
    "ecmwf-charts": {
      "command": "python3",
      "args": ["/path/to/ecmwf_charts_mcp.py"]
    }
  }
}
```

### Using FastMCP CLI

You can also run the server using the FastMCP CLI:

```bash
fastmcp run ecmwf_charts_mcp.py
```

## Available Tools

### 1. `list_ecmwf_products`
List available chart products with optional filters.

**Parameters:**
- `filter_range` (optional): "medium", "sub-seasonal", or "all"
- `filter_parameter` (optional): "temperature", "wind", "geopotential", or "all"

**Example:**
```json
{
  "filter_range": "sub-seasonal",
  "filter_parameter": "temperature"
}
```

### 2. `get_available_times`
Get available valid times for a product and base time.

**Parameters:**
- `product_id`: Product identifier (e.g., "extended-anomaly-z500")
- `base_time`: Base time in ISO format (e.g., "2026-01-20T00:00:00Z")

**Example:**
```json
{
  "product_id": "extended-anomaly-z500",
  "base_time": "2026-01-20T00:00:00Z"
}
```

### 3. `fetch_ecmwf_chart`
Fetch a weather chart image with metadata.

**Parameters:**
- `product_id`: Product identifier
- `base_time`: Base time in ISO format
- `valid_time`: Valid time in ISO format

**Example:**
```json
{
  "product_id": "extended-anomaly-z500",
  "base_time": "2026-01-20T00:00:00Z",
  "valid_time": "2026-02-02T00:00:00Z"
}
```

**Returns:**
- Chart metadata (text)
- PNG image (base64)

## Key Products

### Sub-seasonal (Week 2-6)
- `extended-anomaly-z500`: 500 hPa height anomalies
- `extended-anomaly-2t`: 2m temperature anomalies
- `extended-anomaly-uv`: 10m wind anomalies

### Medium Range (0-15 days)
- `medium-2t-mean-spread`: 2m temperature ensemble
- `medium-t500-mean-spread`: 500 hPa geopotential ensemble
- `medium-10ws-mean-spread`: 10m wind speed ensemble
- `medium-ens-wind`: 100m wind probabilities

## Time Formats

Sub-seasonal products use weekly intervals:
- Base: Latest run (e.g., "2026-01-20T00:00:00Z")
- Valid: Weekly steps (e.g., "2026-02-02T00:00:00Z", "2026-02-09T00:00:00Z")

Medium range products use 6-hourly intervals (check available times first).

## Usage Example

```python
# List products
result = await call_tool("list_ecmwf_products", {
    "filter_range": "sub-seasonal"
})

# Check available times
result = await call_tool("get_available_times", {
    "product_id": "extended-anomaly-z500",
    "base_time": "2026-01-20T00:00:00Z"
})

# Fetch chart
result = await call_tool("fetch_ecmwf_chart", {
    "product_id": "extended-anomaly-z500",
    "base_time": "2026-01-20T00:00:00Z",
    "valid_time": "2026-02-02T00:00:00Z"
})
```

## Chart Interpretation

### 500 hPa Geopotential Anomalies
- **Positive (orange/red)**: High pressure ridges, warmer than normal
- **Negative (blue)**: Low pressure troughs, colder than normal
- Used for blocking patterns and temperature forecasts

### 2m Temperature Anomalies
- Direct indicator of heating/cooling demand
- Key for natural gas consumption forecasts

### Wind Anomalies
- Important for wind energy production
- Affects temperature advection patterns

## API Documentation

Full ECMWF OpenCharts API docs: https://charts.ecmwf.int/

## License

MIT
