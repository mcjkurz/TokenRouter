#!/bin/bash
# Start TokenRouter in background

cd "$(dirname "$0")"

echo "🚀 Starting TokenRouter in background..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check required environment variables
echo ""
echo "Checking required environment variables..."
MISSING=()

if [ -z "$PROVIDER_API_KEY" ]; then
    MISSING+=("PROVIDER_API_KEY")
fi

if [ -z "$PROVIDER_BASE_URL" ]; then
    MISSING+=("PROVIDER_BASE_URL")
fi

if [ -z "$ADMIN_PASSWORD" ]; then
    MISSING+=("ADMIN_PASSWORD")
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    echo "============================================================"
    echo "❌ ERROR: Required environment variables not set!"
    echo "============================================================"
    echo ""
    echo "Missing variables: ${MISSING[*]}"
    echo ""
    echo "You must set these environment variables before starting:"
    echo ""
    echo "  export PROVIDER_API_KEY='your-api-key-here'"
    echo "  export PROVIDER_BASE_URL='https://api.poe.com/v1'"
    echo "  export ADMIN_PASSWORD='your-secure-password'"
    echo ""
    echo "Then run this script again:"
    echo "  ./start_background.sh"
    echo ""
    echo "============================================================"
    echo ""
    exit 1
fi

echo "✅ All required variables are set"
echo ""

# Start in background
nohup python run.py > tokenrouter.log 2>&1 &
PID=$!

echo "✅ TokenRouter started in background (PID: $PID)"
echo "📝 Logs are being written to: tokenrouter.log"
echo "🔍 View logs: tail -f tokenrouter.log"
echo "🛑 Stop server: kill $PID"

