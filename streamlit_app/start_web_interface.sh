#!/bin/bash

# Golf Availability Monitor - Streamlit App Startup Script
# This script starts both the FastAPI backend and Streamlit frontend

echo "🏌️ Starting Golf Availability Monitor Web Interface..."

# Check if Python environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "Consider running: python -m venv venv && source venv/bin/activate"
fi

# Install dependencies if needed
if [ ! -f "streamlit_app/requirements_installed.flag" ]; then
    echo "📦 Installing dependencies..."
    pip install -r streamlit_app/requirements.txt
    touch streamlit_app/requirements_installed.flag
fi

# Start FastAPI backend in background
echo "🚀 Starting API server..."
cd streamlit_app
python api_server.py &
API_PID=$!
echo "API server started with PID: $API_PID"

# Wait a moment for API to start
sleep 3

# Start Streamlit frontend
echo "🌐 Starting Streamlit app..."
streamlit run app.py --server.address 0.0.0.0 --server.port 8501 &
STREAMLIT_PID=$!
echo "Streamlit app started with PID: $STREAMLIT_PID"

echo ""
echo "✅ Both services are running!"
echo "📱 Streamlit App: http://localhost:8501"
echo "🔗 API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $API_PID 2>/dev/null
    kill $STREAMLIT_PID 2>/dev/null
    echo "Services stopped"
    exit 0
}

# Trap Ctrl+C and cleanup
trap cleanup INT

# Wait for either process to exit
wait
