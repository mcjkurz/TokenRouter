#!/bin/bash
# Kill any process using port 8000

echo "🔍 Checking for processes on port 8000..."

PID=$(lsof -ti:8000)

if [ -z "$PID" ]; then
    echo "✅ No process found on port 8000"
else
    echo "🔪 Killing process $PID on port 8000..."
    kill -9 $PID
    echo "✅ Process killed successfully"
fi

