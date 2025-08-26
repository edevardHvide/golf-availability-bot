#!/usr/bin/env python3
"""
Render Deployment Helper Script

This script helps you deploy the Golf Availability Monitor to Render
with PostgreSQL database integration.
"""

import os
import sys
import json
from pathlib import Path

def check_environment():
    """Check if environment is ready for deployment."""
    print("🔍 Checking Deployment Prerequisites...")
    print("=" * 50)
    
    issues = []
    
    # Check if files exist
    required_files = [
        "streamlit_app/postgresql_manager.py",
        "streamlit_app/render_api_server_postgresql.py", 
        "streamlit_app/render_streamlit_app.py",
        "streamlit_app/requirements.txt"
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            issues.append(f"Missing file: {file_path}")
    
    # Check requirements.txt content
    try:
        with open("streamlit_app/requirements.txt", "r") as f:
            content = f.read()
            
        required_packages = ["psycopg2-binary", "sqlalchemy", "fastapi", "streamlit"]
        for package in required_packages:
            if package in content:
                print(f"✅ Package: {package}")
            else:
                print(f"❌ Package: {package} - MISSING")
                issues.append(f"Missing package in requirements.txt: {package}")
                
    except FileNotFoundError:
        issues.append("requirements.txt not found")
    
    # Check if DATABASE_URL is available (for local testing)
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        print("✅ DATABASE_URL environment variable set")
        # Hide password
        safe_url = database_url.split('@')[0].split(':')[:-1]
        safe_url = ':'.join(safe_url) + ':***@' + database_url.split('@')[1]
        print(f"   URL: {safe_url}")
    else:
        print("⚠️ DATABASE_URL not set (will be provided by Render)")
    
    print(f"\n📋 Issues Found: {len(issues)}")
    for issue in issues:
        print(f"   - {issue}")
    
    return len(issues) == 0

def show_deployment_steps():
    """Show step-by-step deployment instructions."""
    print("\n🚀 Render Deployment Steps")
    print("=" * 50)
    
    print("""
📌 **YOUR DATABASE IS READY:**
   Service ID: dpg-d2mne7ogjchc73cs6650-a
   Name: golf-availability-db
   Database: golfdb_li04
   Username: golfdb_li04_user

🎯 **DEPLOYMENT PROCESS:**

## Step 1: Deploy API Service

1. **Go to Render Dashboard** (https://dashboard.render.com)
   
2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect to your GitHub repository: golf-availability-bot
   
3. **Configure API Service:**
   ```
   Service Name: golf-availability-api
   Environment: Python 3
   Region: Choose your preferred region
   Branch: main
   
   Build Command:
   pip install -r requirements.txt && pip install -r streamlit_app/requirements.txt
   
   Start Command:
   cd streamlit_app && python render_api_server_postgresql.py
   ```

4. **Add Environment Variables:**
   - API_MODE = production
   - DATA_STORAGE_MODE = postgresql
   
5. **Connect Database:**
   - Go to "Environment" tab
   - Click "Add Database"
   - Select your existing database: golf-availability-db
   - Render will automatically add DATABASE_URL

6. **Deploy API Service**
   - Click "Create Web Service"
   - Wait for deployment to complete (5-10 minutes)
   - Note the URL (e.g., https://golf-availability-api.onrender.com)

## Step 2: Deploy UI Service

1. **Create Second Web Service**
   - Click "New +" → "Web Service" 
   - Connect to same GitHub repository
   
2. **Configure UI Service:**
   ```
   Service Name: golf-availability-ui
   Environment: Python 3
   Region: Same as API service
   Branch: main
   
   Build Command:
   pip install -r streamlit_app/requirements.txt
   
   Start Command:
   cd streamlit_app && streamlit run render_streamlit_app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true
   ```

3. **Add Environment Variables:**
   - API_BASE_URL = https://golf-availability-api.onrender.com
   (Replace with your actual API service URL from Step 1)

4. **Deploy UI Service**
   - Click "Create Web Service"
   - Wait for deployment to complete

## Step 3: Test Deployment

1. **Test API Service:**
   - Visit: https://your-api-service.onrender.com/health
   - Should return: {"status": "healthy"}
   
2. **Test Database Connection:**
   - Visit: https://your-api-service.onrender.com/api/database/health
   - Should show PostgreSQL connection status
   
3. **Test UI Service:**
   - Visit: https://your-ui-service.onrender.com
   - Should show Golf Availability Monitor interface
   - Sidebar should show "🟢 API Connected"

4. **Test Full Integration:**
   - Create a test user profile
   - Save preferences
   - Verify data persists in PostgreSQL
   
🎉 **SUCCESS INDICATORS:**
   ✅ API health check returns "healthy"
   ✅ Database health shows "connected: true"
   ✅ UI connects to API (green indicator in sidebar)
   ✅ User preferences save and load successfully
""")

def show_troubleshooting():
    """Show common deployment issues and solutions."""
    print("\n🔧 Troubleshooting Guide")
    print("=" * 50)
    
    print("""
## Common Issues & Solutions

### API Service Issues:

**❌ Build Failed - Missing Dependencies**
   Solution: Check streamlit_app/requirements.txt includes:
   - psycopg2-binary>=2.9.9
   - sqlalchemy>=2.0.0
   - fastapi>=0.104.0
   - uvicorn[standard]>=0.24.0

**❌ Database Connection Failed**
   Solution: 
   1. Verify database is connected in "Environment" tab
   2. Check DATABASE_URL is automatically added
   3. Ensure database service is running

**❌ Import Errors**
   Solution: Check file paths in start command:
   cd streamlit_app && python render_api_server_postgresql.py

### UI Service Issues:

**❌ API Connection Failed**
   Solution:
   1. Verify API_BASE_URL points to correct API service
   2. Wait for API service to be fully deployed first
   3. Check API service is accessible via health endpoint

**❌ Streamlit Won't Start**
   Solution: Check start command format:
   cd streamlit_app && streamlit run render_streamlit_app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true

### Database Issues:

**❌ PostgreSQL Connection Timeout**
   Solution:
   1. Check database service is active
   2. Verify connection limits not exceeded
   3. Check database URL format

**❌ Table Creation Failed**
   Solution: 
   1. Check database user has CREATE permissions
   2. Verify sqlalchemy and psycopg2 versions
   3. Check logs for specific SQL errors

## Getting Help:

1. **Check Render Logs:**
   - Go to service dashboard
   - Click "Logs" tab
   - Look for error messages

2. **Test Locally First:**
   ```bash
   $env:DATABASE_URL = "your_database_url_from_render"
   python streamlit_app/test_postgresql.py
   ```

3. **Verify Database Access:**
   - Test DATABASE_URL connection
   - Check user permissions
   - Verify database exists
""")

def main():
    """Main deployment helper function."""
    print("🎯 Golf Availability Monitor - Render Deployment Helper")
    print("PostgreSQL Integration Ready!")
    print("=" * 60)
    
    # Check prerequisites
    ready = check_environment()
    
    if not ready:
        print("\n❌ Please fix the issues above before deploying.")
        return False
    
    # Show deployment steps
    show_deployment_steps()
    
    # Ask if user wants troubleshooting guide
    print("\n" + "=" * 50)
    show_help = input("📖 Show troubleshooting guide? (y/N): ").lower().strip() == 'y'
    
    if show_help:
        show_troubleshooting()
    
    print(f"\n🎉 Ready to deploy! Follow the steps above.")
    print(f"📍 Your database: golf-availability-db (dpg-d2mne7ogjchc73cs6650-a)")
    print(f"🔗 Render Dashboard: https://dashboard.render.com")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Deployment helper interrupted")
        sys.exit(1)
