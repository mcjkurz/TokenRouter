#!/bin/bash
# Start TokenRouter in background

cd "$(dirname "$0")"

echo "Starting TokenRouter..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run:"
    echo "  python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo ".env file not found. Please run:"
    echo "  cp .env.example .env"
    echo "Then edit .env with your configuration."
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
