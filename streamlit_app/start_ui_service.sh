#!/bin/bash
# Render UI Service Startup Script

echo "🎨 Starting Golf Availability UI Service..."
echo "Environment: Render Two-Service Architecture" 
echo "Service Type: Streamlit Frontend"
echo "Port: ${PORT:-10000}"
echo "API URL: ${API_BASE_URL:-http://localhost:8000}"

# Start Streamlit
streamlit run streamlit_app/render_streamlit_app.py \
    --server.port=${PORT:-10000} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
