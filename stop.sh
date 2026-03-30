#!/bin/bash
# Stop TokenRouter

PORT=8001

echo "Stopping TokenRouter..."

# Find process listening on the port
PID=$(lsof -ti:$PORT -sTCP:LISTEN 2>/dev/null)

if [ -z "$PID" ]; then
    echo "No TokenRouter process found on port $PORT"
else
    echo "Killing process $PID..."
    kill -9 $PID
    echo "TokenRouter stopped"
fi
