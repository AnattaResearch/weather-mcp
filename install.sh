#!/bin/bash
# ECMWF OpenCharts MCP Server Installation Script

set -e

echo "Installing ECMWF OpenCharts MCP Server..."

# Check Python version
python3 --version

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Make executable
chmod +x ecmwf_charts_mcp.py

# Get absolute path
SCRIPT_PATH=$(cd "$(dirname "$0")" && pwd)/ecmwf_charts_mcp.py

echo ""
echo "✓ Installation complete!"
echo ""
echo "Add this to your Claude Desktop config:"
echo ""
echo '{'
echo '  "mcpServers": {'
echo '    "ecmwf-charts": {'
echo '      "command": "python3",'
echo "      \"args\": [\"$SCRIPT_PATH\"]"
echo '    }'
echo '  }'
echo '}'
echo ""
echo "Config location:"
echo "  macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "  Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
echo ""
echo "After adding, restart Claude Desktop."
