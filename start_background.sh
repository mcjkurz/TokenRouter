#!/bin/bash
# Start TokenRouter in background

cd "$(dirname "$0")"

echo "🚀 Starting TokenRouter in background..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment and start server
source venv/bin/activate

# Check if PROVIDER_API_KEY is set
if [ -z "$PROVIDER_API_KEY" ]; then
    echo "⚠️  Warning: PROVIDER_API_KEY not set. Set it with: export PROVIDER_API_KEY='your-key'"
fi

# Start in background
nohup python run.py > tokenrouter.log 2>&1 &
PID=$!

echo "✅ TokenRouter started in background (PID: $PID)"
echo "📝 Logs are being written to: tokenrouter.log"
echo "🔍 View logs: tail -f tokenrouter.log"
echo "🛑 Stop server: kill $PID"

