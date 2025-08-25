#!/bin/bash
# Render.com startup script for Golf Availability Monitor
# This runs both the FastAPI backend and Streamlit frontend

echo "🚀 Starting Golf Availability Monitor on Render..."

# Change to the streamlit_app directory
cd streamlit_app

# Start FastAPI backend in the background on the PORT provided by Render
echo "📡 Starting FastAPI backend on port $PORT..."
python -m uvicorn api_server:app --host 0.0.0.0 --port $PORT --workers 1 &

# Give FastAPI time to start
sleep 3

# Start Streamlit on a different internal port
echo "🎯 Starting Streamlit frontend..."
streamlit run app.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.enableCORS false \
  --server.enableXsrfProtection false \
  --server.headless true \
  --server.runOnSave false \
  --browser.gatherUsageStats false

# Keep the process running
wait
