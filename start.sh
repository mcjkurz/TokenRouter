#!/bin/bash
# Start TokenRouter in background

cd "$(dirname "$0")"

PORT=8001

# Kill any existing process on the port
EXISTING_PID=$(lsof -ti:$PORT -sTCP:LISTEN 2>/dev/null)
if [ -n "$EXISTING_PID" ]; then
    echo "Stopping existing process on port $PORT (PID: $EXISTING_PID)..."
    kill $EXISTING_PID 2>/dev/null
    sleep 1
    # Force kill if still running
    for pid in $EXISTING_PID; do
        if kill -0 $pid 2>/dev/null; then
            kill -9 $pid 2>/dev/null
        fi
    done
    sleep 1
fi

echo "Starting TokenRouter on port $PORT..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run:"
    echo "  python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if config.json exists
if [ ! -f "config.json" ]; then
    echo "config.json not found. Please run:"
    echo "  cp config.example.json config.json"
    echo "Then edit config.json with your configuration."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Create logs directory if it doesn't exist
mkdir -p logs

# Generate timestamped log filename
LOG_FILE="logs/tokenrouter_$(date +%Y%m%d_%H%M%S).log"

# Start in background with timestamped log file
nohup python run.py > "$LOG_FILE" 2>&1 &
PID=$!

echo "TokenRouter started (PID: $PID)"
echo "Logs: $LOG_FILE"
echo "View logs: tail -f $LOG_FILE"
echo "Stop server: ./stop.sh"
