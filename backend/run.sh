#!/bin/bash

# Backend server startup script
echo "Starting ADK Backend Server..."

# Kill any existing processes on port 8000
echo "Checking for existing processes on port 8000..."
EXISTING_PIDS=$(lsof -ti:8000 2>/dev/null)
if [ -n "$EXISTING_PIDS" ]; then
    echo "Found processes using port 8000: $EXISTING_PIDS"
    echo "Killing existing processes..."
    echo $EXISTING_PIDS | xargs kill -9 2>/dev/null
    sleep 2
    echo "Processes killed."
else
    echo "No existing processes found on port 8000."
fi

# Also kill any uvicorn processes to be safe
echo "Killing any remaining uvicorn processes..."
pkill -f uvicorn 2>/dev/null || true
sleep 1

# Set SSL certificate file
export SSL_CERT_FILE=$(python -m certifi)
echo "SSL_CERT_FILE set to: $SSL_CERT_FILE"

# Change to backend directory (if not already there)
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Set log file with timestamp
LOG_FILE="logs/server_$(date +%Y%m%d_%H%M%S).log"

# Start the FastAPI server with uvicorn and log output
echo "Starting server on http://0.0.0.0:8000 (accessible via localhost:8000)"
echo "Server logs will be written to: $LOG_FILE"

# Start server in background with logging
echo "Starting server in background..."
nohup python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > "$LOG_FILE" 2>&1 &

# Get the process ID
SERVER_PID=$!
echo "Server started with PID: $SERVER_PID"

# Save PID to file for easy management
echo $SERVER_PID > logs/server.pid

# Wait a moment for server to start
sleep 3

# Check if server is running
if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo "✅ Server is running successfully!"
    echo "📍 URL: http://localhost:8000"
    echo "📄 Logs: $LOG_FILE"
    echo "🔍 PID: $SERVER_PID (saved to logs/server.pid)"
    echo ""
    echo "Commands:"
    echo "  tail -f $LOG_FILE          # Follow logs"
    echo "  kill $SERVER_PID           # Stop server"
    echo "  kill \$(cat logs/server.pid) # Stop server using PID file"
    echo ""
else
    echo "❌ Server failed to start. Check logs: $LOG_FILE"
    exit 1
fi
