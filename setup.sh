#!/bin/bash

# dbt Guard MCP Server Setup Script

echo "Setting up dbt Guard MCP Server..."

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy and edit the environment file:"
echo "   cp .env.example .env"
echo "   # Edit .env with your dbt Cloud connection details"
echo ""
echo "2. Get your dbt Cloud API token:"
echo "   - Login to dbt Cloud"
echo "   - Go to Account Settings → API Access"
echo "   - Generate new token with appropriate permissions"
echo ""
echo "3. Add the following to your Claude Desktop config:"
echo ""
echo '{'
echo '  "mcpServers": {'
echo '    "dbt-guard": {'
echo '      "command": "'$(pwd)'/venv/bin/python",'
echo '      "args": ["'$(pwd)'/server.py"]'
echo '    }'
echo '  }'
echo '}'
echo ""
echo "🛡️  Safety Features:"
echo "   - All dangerous operations require explicit confirmation"
echo "   - Read-only operations (search, preview) are always safe"
echo "   - Guardrails prevent accidental data modifications"
echo ""
echo "⚠️  Remember: Always set confirm_execution=true for run/test operations!"