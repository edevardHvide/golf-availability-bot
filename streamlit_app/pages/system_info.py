"""
System Information Page for Golf Availability Monitor

This page contains technical details, service status, and configuration information
that end users don't need to see in the main interface.
"""

import streamlit as st
import requests
import os
from datetime import datetime

# Configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="System Info - Golf Monitor",
    page_icon="🔧",
    layout="wide"
)

def main():
    """System information page."""
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem;">
        <h1>🔧 System Information</h1>
        <p>Technical details and service status for administrators</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Back to main page button
    if st.button("← Back to Main Page"):
        st.switch_page("render_streamlit_app.py")
    
    st.markdown("---")
    
    # Service Status Section
    st.markdown("## 🚀 Service Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔗 API Connection")
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                st.success("🟢 API Service Connected")
                health_data = response.json()
                st.json(health_data)
            else:
                st.error(f"🔴 API Service Error: {response.status_code}")
        except Exception as e:
            st.error(f"🔴 API Service Unavailable: {e}")
    
    with col2:
        st.markdown("### 📊 System Status")
        try:
            response = requests.get(f"{API_BASE_URL}/api/status", timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                st.success("🟢 System Status Retrieved")
                st.json(status_data)
            else:
                st.error(f"🔴 Status Error: {response.status_code}")
        except Exception as e:
            st.error(f"🔴 Status Unavailable: {e}")
    
    st.markdown("---")
    
    # Configuration Section
    st.markdown("## ⚙️ Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🌐 Environment Variables")
        config_info = {
            "API_BASE_URL": API_BASE_URL,
            "SERVICE_MODE": "render_ui_service",
            "Timestamp": datetime.now().isoformat()
        }
        st.json(config_info)
    
    with col2:
        st.markdown("### 🏗️ Architecture")
        st.info("""
        **Two-Service Architecture:**
        
        - **UI Service**: Streamlit application (this service)
        - **API Service**: FastAPI backend with PostgreSQL
        - **Database**: PostgreSQL for data persistence
        - **Deployment**: Render cloud platform
        """)
    
    st.markdown("---")
    
    # Database Health Section
    st.markdown("## 🗄️ Database Health")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/database/health", timeout=5)
        if response.status_code == 200:
            db_health = response.json()
            st.success("🟢 Database Health Check Successful")
            st.json(db_health)
        else:
            st.error(f"🔴 Database Health Check Failed: {response.status_code}")
    except Exception as e:
        st.error(f"🔴 Database Health Check Unavailable: {e}")
    
    st.markdown("---")
    
    # API Endpoints Section
    st.markdown("## 🔌 Available API Endpoints")
    
    endpoints = [
        {"endpoint": "/health", "method": "GET", "description": "Health check"},
        {"endpoint": "/api/status", "method": "GET", "description": "System status"},
        {"endpoint": "/api/preferences", "method": "GET", "description": "All user preferences"},
        {"endpoint": "/api/preferences/{email}", "method": "GET", "description": "Specific user preferences"},
        {"endpoint": "/api/preferences", "method": "POST", "description": "Save user preferences"},
        {"endpoint": "/api/preferences/{email}", "method": "DELETE", "description": "Delete user preferences"},
        {"endpoint": "/api/courses", "method": "GET", "description": "Available golf courses"},
        {"endpoint": "/api/cached-availability", "method": "GET", "description": "Cached availability results"},
        {"endpoint": "/api/all-times", "method": "GET", "description": "All available times from database"},
        {"endpoint": "/api/database/health", "method": "GET", "description": "Database health check"},
        {"endpoint": "/docs", "method": "GET", "description": "Interactive API documentation"},
        {"endpoint": "/redoc", "method": "GET", "description": "Alternative API documentation"}
    ]
    
    # Create a DataFrame-like display
    st.markdown("| Endpoint | Method | Description |")
    st.markdown("|----------|--------|-------------|")
    for endpoint in endpoints:
        st.markdown(f"| `{endpoint['endpoint']}` | {endpoint['method']} | {endpoint['description']} |")
    
    st.markdown("---")
    
    # Troubleshooting Section
    st.markdown("## 🛠️ Troubleshooting")
    
    with st.expander("🔍 Common Issues & Solutions"):
        st.markdown("""
        **API Service Unavailable:**
        - Check if API service is deployed on Render
        - Verify API service logs for errors
        - Ensure environment variables are set correctly
        
        **Database Connection Issues:**
        - Verify PostgreSQL database is running
        - Check database connection string
        - Ensure database tables are created
        
        **Performance Issues:**
        - Check API service response times
        - Monitor database query performance
        - Verify caching is working properly
        """)
    
    with st.expander("📋 Logs & Debugging"):
        st.markdown("""
        **To view logs:**
        1. Go to Render dashboard
        2. Select your API service
        3. Click on "Logs" tab
        4. Look for error messages or warnings
        
        **To test API directly:**
        - Visit: `{API_BASE_URL}/health`
        - Visit: `{API_BASE_URL}/docs`
        
        **Environment variables to check:**
        - `DATABASE_URL`
        - `API_BASE_URL`
        - `SMTP_USER` and `SMTP_PASS`
        """.format(API_BASE_URL=API_BASE_URL))
    
    st.markdown("---")
    
    # Footer
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <small>🔧 System Information Page - For administrators and developers only</small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
