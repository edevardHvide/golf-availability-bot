#!/bin/bash
# Render startup script for Golf Availability Monitor
# This file should be in the root directory of your repository

echo "🚀 Starting Golf Availability Monitor (Unified Server)..."

# Change to streamlit_app directory  
cd streamlit_app

# Start the unified server (serves both API and Streamlit on the same port)
echo "🎯 Starting unified server on port $PORT..."
exec python unified_server.py
