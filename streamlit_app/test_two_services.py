#!/usr/bin/env python3
"""
Local test script for two-service architecture
"""

import subprocess
import time
import requests
import sys
from pathlib import Path

def test_api_service():
    """Test the API service locally."""
    print("🧪 Testing API Service...")
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API Health check passed")
            data = response.json()
            print(f"   Status: {data.get('status')}")
        else:
            print(f"❌ API Health check failed: {response.status_code}")
            return False
            
        # Test status endpoint
        response = requests.get("http://localhost:8000/api/status", timeout=5)
        if response.status_code == 200:
            print("✅ API Status endpoint working")
            data = response.json()
            print(f"   Version: {data.get('version')}")
            print(f"   Users: {data.get('user_count')}")
        else:
            print(f"❌ API Status endpoint failed: {response.status_code}")
            
        # Test courses endpoint
        response = requests.get("http://localhost:8000/api/courses", timeout=5)
        if response.status_code == 200:
            print("✅ API Courses endpoint working")
            data = response.json()
            print(f"   Courses available: {len(data.get('courses', []))}")
        else:
            print(f"❌ API Courses endpoint failed: {response.status_code}")
            
        return True
        
    except Exception as e:
        print(f"❌ API Service test failed: {e}")
        return False

def test_ui_connection():
    """Test that UI can connect to API."""
    print("\n🧪 Testing UI-API Connection...")
    
    try:
        # Simulate the UI's API connection check
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ UI can connect to API")
            return True
        else:
            print(f"❌ UI cannot connect to API: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ UI-API connection test failed: {e}")
        return False

def main():
    """Run local two-service test."""
    print("🚀 Two-Service Architecture Local Test")
    print("=" * 50)
    
    # Check if API service is running
    print("Checking if API service is running on localhost:8000...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        api_running = response.status_code == 200
    except:
        api_running = False
    
    if not api_running:
        print("❌ API service not running. Start it first:")
        print("   python streamlit_app/render_api_server.py")
        print("\nThen run this test again.")
        return
    
    # Test API service
    api_ok = test_api_service()
    
    # Test UI connection
    ui_ok = test_ui_connection()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary")
    print(f"API Service: {'✅ OK' if api_ok else '❌ Failed'}")
    print(f"UI Connection: {'✅ OK' if ui_ok else '❌ Failed'}")
    
    if api_ok and ui_ok:
        print("\n🎉 Two-service architecture test PASSED!")
        print("\nYou can now:")
        print("1. Deploy API service to Render")
        print("2. Deploy UI service to Render")
        print("3. Update UI service API_BASE_URL environment variable")
        
        print("\nLocal URLs:")
        print("📡 API: http://localhost:8000")
        print("🎨 UI: Run 'streamlit run streamlit_app/render_streamlit_app.py'")
    else:
        print("\n❌ Tests failed. Check the issues above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
