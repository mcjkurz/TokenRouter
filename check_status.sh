#!/bin/bash
# Check if TokenRouter server is running

PORT=${PORT:-8000}

echo "🔍 Checking TokenRouter status on port $PORT..."
echo ""

# Check if process is running on port
PIDS=$(lsof -ti:$PORT 2>/dev/null)

if [ -z "$PIDS" ]; then
    echo "❌ TokenRouter is NOT running"
    echo "   No process found on port $PORT"
    echo ""
    echo "💡 To start the server, run:"
    echo "   ./start_foreground.sh  (foreground mode)"
    echo "   ./start_background.sh  (background mode)"
    exit 1
else
    echo "✅ TokenRouter is running"
    # Get first PID for display
    FIRST_PID=$(echo "$PIDS" | head -n 1)
    PID_COUNT=$(echo "$PIDS" | wc -l | tr -d ' ')
    
    if [ "$PID_COUNT" -eq 1 ]; then
        echo "   Process ID: $FIRST_PID"
    else
        echo "   Process IDs: $(echo $PIDS | tr '\n' ' ')"
    fi
    echo "   Port: $PORT"
    
    # Try to get more process info
    PROCESS_INFO=$(ps -p $FIRST_PID -o comm= 2>/dev/null)
    if [ -n "$PROCESS_INFO" ]; then
        echo "   Process: $PROCESS_INFO"
    fi
    
    # Check if server is responding
    echo ""
    echo "🌐 Checking server response..."
    
    if command -v curl &> /dev/null; then
        # Try to hit the docs endpoint (should return 200 or redirect)
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/docs 2>/dev/null)
        
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "307" ] || [ "$HTTP_CODE" = "404" ]; then
            echo "   ✅ Server is responding (HTTP $HTTP_CODE)"
            echo ""
            echo "📍 Server URLs:"
            echo "   Local:  http://localhost:$PORT"
            echo "   Admin:  http://localhost:$PORT/admin"
            echo "   API:    http://localhost:$PORT/v1"
            echo "   Docs:   http://localhost:$PORT/docs"
        else
            echo "   ⚠️  Server process exists but not responding properly (HTTP $HTTP_CODE)"
        fi
    else
        echo "   ⚠️  curl not found, skipping HTTP check"
        echo "   Server process is running but HTTP response not verified"
    fi
    
    exit 0
fi

