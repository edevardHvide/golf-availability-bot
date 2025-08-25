#!/bin/bash
# Render startup script for Golf Availability Monitor

echo "🚀 Starting Golf Availability Monitor..."

# Start API server in background
cd streamlit_app
echo "📡 Starting API server..."
python api_server.py &
API_PID=$!

# Wait a moment for API to start
sleep 3

# Start Streamlit on the main port
echo "🎯 Starting Streamlit interface..."
exec streamlit run app.py \
  --server.port $PORT \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false

# If we get here, something went wrong
echo "❌ Streamlit exited, stopping API server..."
kill $API_PID 2>/dev/null
