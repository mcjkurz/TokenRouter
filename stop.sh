#!/bin/bash
# Stop TokenRouter

echo "Stopping TokenRouter..."

# Find process listening on port 8000
PID=$(lsof -ti:8000 -sTCP:LISTEN 2>/dev/null)

if [ -z "$PID" ]; then
    echo "No TokenRouter process found on port 8000"
else
    echo "Killing process $PID..."
    kill -9 $PID
    echo "TokenRouter stopped"
fi
