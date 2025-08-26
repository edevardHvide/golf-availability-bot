#!/bin/bash
# Enhanced Render.com startup script for Golf Availability Monitor
# This runs the unified server with robust JSON handling and enhanced features

echo "🚀 Starting Golf Availability Monitor v2.0 on Render..."
echo "=============================================="

# Display environment info
echo "🔧 Environment Information:"
echo "  Port: $PORT"
echo "  Python: $(python --version)"
echo "  Working Directory: $(pwd)"

# Change to the streamlit_app directory
cd streamlit_app

echo ""
echo "📦 Checking components..."

# Check if robust JSON manager exists
if [ -f "robust_json_manager.py" ]; then
    echo "  ✅ Robust JSON Manager available"
else
    echo "  ⚠️  Robust JSON Manager not found - using basic JSON"
fi

# Check if enhanced unified server exists
if [ -f "enhanced_unified_server.py" ]; then
    echo "  ✅ Enhanced Unified Server available"
    SERVER_FILE="enhanced_unified_server.py"
elif [ -f "unified_server.py" ]; then
    echo "  ✅ Basic Unified Server available"
    SERVER_FILE="unified_server.py"
else
    echo "  ❌ No unified server found - fallback to separate services"
    SERVER_FILE="api_server.py"
fi

# Check if enhanced app exists
if [ -f "enhanced_app.py" ]; then
    echo "  ✅ Enhanced Streamlit App available"
else
    echo "  ✅ Basic Streamlit App available"
fi

echo ""
echo "🚀 Starting server..."

# Create user preferences file if it doesn't exist
if [ ! -f "user_preferences.json" ]; then
    echo "📝 Creating initial preferences file..."
    echo '{"_metadata":{"version":"2.0","created":"'$(date -Iseconds)'"},"users":{}}' > user_preferences.json
fi

# Set environment variables for the application
export RENDER_DEPLOYMENT=true
export DATA_PERSISTENCE=true

# Start the unified server
echo "📡 Starting $SERVER_FILE on port $PORT..."

if [ "$SERVER_FILE" = "enhanced_unified_server.py" ]; then
    # Enhanced unified server with robust features
    python enhanced_unified_server.py
elif [ "$SERVER_FILE" = "unified_server.py" ]; then
    # Basic unified server
    python unified_server.py
else
    # Fallback: separate API and Streamlit
    echo "🔄 Fallback: Starting API server and Streamlit separately..."
    
    # Start FastAPI backend in the background
    python api_server.py &
    API_PID=$!
    echo "📡 API server started with PID: $API_PID"
    
    # Give API time to start
    sleep 3
    
    # Start Streamlit frontend
    streamlit run app.py \
      --server.address 0.0.0.0 \
      --server.port $PORT \
      --server.enableCORS false \
      --server.enableXsrfProtection false \
      --server.headless true \
      --server.runOnSave false \
      --browser.gatherUsageStats false
    
    # Keep the process running
    wait
fi
