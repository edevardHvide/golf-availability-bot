#!/usr/bin/env python3
"""
Test connection to your cloud-hosted Streamlit API
"""

import requests
import os
from dotenv import load_dotenv

def test_cloud_connection():
    load_dotenv()
    
    # Get API URL from environment or ask user
    api_url = os.getenv("API_URL", "").strip()
    
    if not api_url or api_url == "http://localhost:8000":
        print("🌐 Testing Cloud API Connection")
        print("=" * 40)
        api_url = input("Enter your Render app URL (e.g., https://your-app.onrender.com): ").strip()
        
        if not api_url.startswith('http'):
            api_url = 'https://' + api_url
    
    print(f"\n🔍 Testing connection to: {api_url}")
    
    try:
        # Test basic connection
        print("1. Testing basic connection...")
        response = requests.get(f"{api_url}/", timeout=15)
        if response.status_code == 200:
            print("   ✅ Server is responding")
        else:
            print(f"   ⚠️ Server returned status {response.status_code}")
        
        # Test API endpoint
        print("2. Testing preferences API...")
        response = requests.get(f"{api_url}/api/preferences", timeout=15)
        if response.status_code == 200:
            data = response.json()
            user_count = len(data.get("preferences", {}))
            print(f"   ✅ API working! Found {user_count} user profiles")
            
            # Show first user as example
            if user_count > 0:
                first_user = list(data["preferences"].values())[0]
                print(f"   📋 Example user: {first_user.get('name', 'Unknown')} ({first_user.get('email', 'No email')})")
        else:
            print(f"   ❌ API returned status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
        
        # Test courses endpoint
        print("3. Testing courses API...")
        response = requests.get(f"{api_url}/api/courses", timeout=15)
        if response.status_code == 200:
            data = response.json()
            course_count = data.get("total", 0)
            print(f"   ✅ Courses API working! Found {course_count} golf courses")
        else:
            print(f"   ⚠️ Courses API returned status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Could not connect to the server")
        print("   Check that your Render app is deployed and running")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"\n💡 To use this URL, set: API_URL={api_url}")
    print("   Either in your .env file or as an environment variable")

if __name__ == "__main__":
    test_cloud_connection()
