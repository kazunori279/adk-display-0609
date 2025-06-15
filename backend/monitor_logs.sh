#!/bin/bash

# Log monitoring script for ADK Backend Server
echo "🔍 ADK Backend Server Log Monitor"
echo "=================================="

# Find the most recent server log file
LATEST_LOG=$(ls -t logs/server_*.log 2>/dev/null | head -1)

if [ -z "$LATEST_LOG" ]; then
    echo "❌ No server log files found in logs/ directory"
    echo "Make sure the server is running with ./run.sh"
    exit 1
fi

echo "📄 Monitoring: $LATEST_LOG"
echo "🔍 Looking for PARSE_DOC output..."
echo "=================================="
echo ""

# Follow the log file and highlight parse_doc output
tail -f "$LATEST_LOG" | while read line; do
    # Check if line contains parse_doc related content
    if echo "$line" | grep -i "parse_doc\|gemini.*calling\|gemini.*response\|gcs.*uri" > /dev/null; then
        # Highlight parse_doc lines in green
        echo -e "\033[32m$line\033[0m"
    elif echo "$line" | grep -i "error\|failed\|exception" > /dev/null; then
        # Highlight errors in red
        echo -e "\033[31m$line\033[0m"
    else
        # Regular lines
        echo "$line"
    fi
done