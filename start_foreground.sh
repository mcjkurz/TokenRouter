#!/bin/bash
# Start TokenRouter in foreground

cd "$(dirname "$0")"

echo "🚀 Starting TokenRouter..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if PROVIDER_API_KEY is set
if [ -z "$PROVIDER_API_KEY" ]; then
    echo "⚠️  Warning: PROVIDER_API_KEY not set. Set it with: export PROVIDER_API_KEY='your-key'"
fi

# Display configuration
echo ""
echo "Configuration:"
echo "  PROVIDER_API_KEY: ${PROVIDER_API_KEY:0:10}..." 
echo "  ADMIN_PASSWORD: ${ADMIN_PASSWORD:-admin123}"
echo ""

# Start server
python run.py

