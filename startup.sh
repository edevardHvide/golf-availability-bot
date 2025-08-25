#!/bin/bash
# Render startup script for Golf Availability Monitor

echo "🚀 Starting Golf Availability Monitor..."

# Change to streamlit_app directory
cd streamlit_app

# Start API server in background on port 8000
echo "📡 Starting API server on port 8000..."
python api_server.py &
API_PID=$!

# Wait for API to start
sleep 5

# Start Streamlit on the main port
echo "🎯 Starting Streamlit interface on port $PORT..."
exec streamlit run app.py \
  --server.port $PORT \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false
