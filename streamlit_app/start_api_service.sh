#!/bin/bash
# Render API Service Startup Script

echo "🚀 Starting Golf Availability API Service..."
echo "Environment: Render Two-Service Architecture"
echo "Service Type: API Backend"
echo "Port: ${PORT:-10000}"
echo "Data Mode: ${DATA_STORAGE_MODE:-render}"

# Create data directory if it doesn't exist
mkdir -p /opt/render/project/src/data

# Start the API server
python streamlit_app/render_api_server.py
