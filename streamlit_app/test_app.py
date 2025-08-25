#!/usr/bin/env python3
"""
Test script for the Streamlit Golf Monitor app

This script performs basic tests to ensure the app is working correctly.
"""

import sys
import requests
import json
from pathlib import Path

def test_api_connection():
    """Test if the API server is running and responsive."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running")
            return True
        else:
            print(f"❌ API server returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to API server: {e}")
        return False

def test_courses_endpoint():
    """Test the courses API endpoint."""
    try:
        response = requests.get("http://localhost:8000/api/courses", timeout=5)
        if response.status_code == 200:
            data = response.json()
            courses = data.get('courses', [])
            print(f"✅ Courses endpoint working - {len(courses)} courses available")
            
            if data.get('demo_mode'):
                print("ℹ️  Running in demo mode (golf system not available)")
            
            return True
        else:
            print(f"❌ Courses endpoint returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to courses endpoint: {e}")
        return False

def test_preferences_saving():
    """Test saving user preferences."""
    test_preferences = {
        "name": "Test User",
        "email": "test@example.com",
        "selected_courses": ["oslo_golfklubb", "miklagard_gk"],
        "time_slots": ["10:00", "10:30", "14:00"],
        "min_players": 2,
        "days_ahead": 4,
        "notification_frequency": "immediate"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/preferences",
            json=test_preferences,
            timeout=5
        )
        
        if response.status_code == 200:
            print("✅ Preferences saving working")
            return True
        else:
            print(f"❌ Preferences saving failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot test preferences saving: {e}")
        return False

def test_preferences_file():
    """Test if the preferences file is created and readable."""
    preferences_file = Path(__file__).parent.parent / "user_preferences.json"
    
    if preferences_file.exists():
        try:
            with open(preferences_file, 'r') as f:
                data = json.load(f)
            print(f"✅ Preferences file exists with {len(data)} users")
            return True
        except Exception as e:
            print(f"❌ Cannot read preferences file: {e}")
            return False
    else:
        print("ℹ️  Preferences file doesn't exist yet (will be created when users save preferences)")
        return True

def test_streamlit_app():
    """Test if Streamlit app is running."""
    try:
        response = requests.get("http://localhost:8501", timeout=5)
        if response.status_code == 200:
            print("✅ Streamlit app is running")
            return True
        else:
            print(f"❌ Streamlit app returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to Streamlit app: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Golf Monitor Streamlit App")
    print("=" * 40)
    
    tests = [
        ("API Server Health", test_api_connection),
        ("Courses Endpoint", test_courses_endpoint),
        ("Preferences Saving", test_preferences_saving),
        ("Preferences File", test_preferences_file),
        ("Streamlit App", test_streamlit_app),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"   Failed: {test_name}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The app is ready to use.")
        print("\n📱 Open your browser and go to: http://localhost:8501")
        print("🔗 API docs available at: http://localhost:8000/docs")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
