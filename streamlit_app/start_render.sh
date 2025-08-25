#!/bin/bash
# Simple Render startup script for Streamlit

echo "Starting Streamlit Golf Availability Monitor..."
cd streamlit_app
exec streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.enableCORS false --server.enableXsrfProtection false --server.headless true --browser.gatherUsageStats false
