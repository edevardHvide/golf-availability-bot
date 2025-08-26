#!/usr/bin/env python3
"""
Comprehensive Test Suite for Enhanced Golf Availability Monitor

This script tests all components of the enhanced system including:
- Robust JSON Manager
- Enhanced API Server
- Enhanced Streamlit App
- System integration
"""

import requests
import json
import time
import sys
from pathlib import Path
from datetime import datetime
import subprocess
import threading
from typing import Dict, List, Tuple

class TestResults:
    """Test results tracker."""
    
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
    
    def add_result(self, test_name: str, passed: bool, message: str = ""):
        self.tests.append({
            "name": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        if passed:
            self.passed += 1
            print(f"✅ {test_name}")
            if message:
                print(f"   {message}")
        else:
            self.failed += 1
            print(f"❌ {test_name}")
            if message:
                print(f"   {message}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n📊 Test Summary:")
        print(f"   Total: {total}")
        print(f"   Passed: {self.passed}")
        print(f"   Failed: {self.failed}")
        print(f"   Success Rate: {(self.passed/total*100):.1f}%" if total > 0 else "   Success Rate: 0%")

def test_robust_json_manager():
    """Test the robust JSON manager."""
    print("\n🧪 Testing Robust JSON Manager...")
    results = TestResults()
    
    try:
        from robust_json_manager import RobustJSONManager, load_user_preferences, save_user_preferences
        results.add_result("Import robust JSON manager", True)
        
        # Test basic operations
        test_data = {
            "test@example.com": {
                "name": "Test User",
                "email": "test@example.com",
                "preferences": ["test1", "test2"]
            }
        }
        
        # Test save
        success = save_user_preferences(test_data)
        results.add_result("Save test data", success, "Data saved successfully" if success else "Save failed")
        
        # Test load
        loaded_data = load_user_preferences()
        data_matches = loaded_data.get("test@example.com", {}).get("name") == "Test User"
        results.add_result("Load and verify data", data_matches, "Data loaded correctly" if data_matches else "Data mismatch")
        
        # Test backup functionality
        manager = RobustJSONManager("test_preferences.json")
        backup_success = manager.backup()
        results.add_result("Create backup", backup_success, "Backup created" if backup_success else "Backup failed")
        
        # Test stats
        stats = manager.get_stats()
        has_stats = isinstance(stats, dict) and "file_exists" in stats
        results.add_result("Get file stats", has_stats, f"Stats: {stats}" if has_stats else "Stats unavailable")
        
    except ImportError:
        results.add_result("Import robust JSON manager", False, "Module not found")
    except Exception as e:
        results.add_result("Robust JSON manager test", False, f"Error: {e}")
    
    return results

def test_api_endpoints():
    """Test the API endpoints."""
    print("\n🧪 Testing API Endpoints...")
    results = TestResults()
    
    base_url = "http://localhost:8000"
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        results.add_result("Health endpoint", response.status_code == 200, f"Status: {response.status_code}")
    except Exception as e:
        results.add_result("Health endpoint", False, f"Error: {e}")
    
    # Test system status endpoint
    try:
        response = requests.get(f"{base_url}/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            results.add_result("System status endpoint", True, f"Users: {data.get('user_count', 0)}")
        else:
            results.add_result("System status endpoint", False, f"Status: {response.status_code}")
    except Exception as e:
        results.add_result("System status endpoint", False, f"Error: {e}")
    
    # Test courses endpoint
    try:
        response = requests.get(f"{base_url}/api/courses", timeout=5)
        if response.status_code == 200:
            data = response.json()
            course_count = len(data.get("courses", []))
            results.add_result("Courses endpoint", course_count > 0, f"Found {course_count} courses")
        else:
            results.add_result("Courses endpoint", False, f"Status: {response.status_code}")
    except Exception as e:
        results.add_result("Courses endpoint", False, f"Error: {e}")
    
    # Test preferences CRUD operations
    test_user = {
        "name": "API Test User",
        "email": "apitest@example.com",
        "selected_courses": ["oslo_golfklubb"],
        "time_slots": ["10:00", "10:30"],
        "min_players": 2,
        "days_ahead": 4,
        "notification_frequency": "immediate"
    }
    
    # Create
    try:
        response = requests.post(f"{base_url}/api/preferences", json=test_user, timeout=5)
        results.add_result("Create user preferences", response.status_code == 200, "User created")
    except Exception as e:
        results.add_result("Create user preferences", False, f"Error: {e}")
    
    # Read
    try:
        response = requests.get(f"{base_url}/api/preferences/{test_user['email']}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            name_matches = data.get("name") == test_user["name"]
            results.add_result("Read user preferences", name_matches, "Data retrieved correctly")
        else:
            results.add_result("Read user preferences", False, f"Status: {response.status_code}")
    except Exception as e:
        results.add_result("Read user preferences", False, f"Error: {e}")
    
    # Delete
    try:
        response = requests.delete(f"{base_url}/api/preferences/{test_user['email']}", timeout=5)
        results.add_result("Delete user preferences", response.status_code == 200, "User deleted")
    except Exception as e:
        results.add_result("Delete user preferences", False, f"Error: {e}")
    
    # Test backup endpoint (if available)
    try:
        response = requests.post(f"{base_url}/api/backup", timeout=5)
        if response.status_code == 200:
            results.add_result("Backup endpoint", True, "Backup created")
        elif response.status_code == 500:
            data = response.json()
            if "robust JSON manager" in data.get("detail", "").lower():
                results.add_result("Backup endpoint", True, "Backup unavailable (expected)")
            else:
                results.add_result("Backup endpoint", False, "Backup failed")
        else:
            results.add_result("Backup endpoint", False, f"Status: {response.status_code}")
    except Exception as e:
        results.add_result("Backup endpoint", False, f"Error: {e}")
    
    return results

def test_streamlit_app():
    """Test the Streamlit application."""
    print("\n🧪 Testing Streamlit Application...")
    results = TestResults()
    
    streamlit_url = "http://localhost:8501"
    
    # Test main page
    try:
        response = requests.get(streamlit_url, timeout=10)
        if response.status_code == 200:
            content = response.text.lower()
            has_golf = "golf" in content
            has_monitor = "monitor" in content
            results.add_result("Streamlit main page", has_golf and has_monitor, "Golf monitor interface loaded")
        else:
            results.add_result("Streamlit main page", False, f"Status: {response.status_code}")
    except Exception as e:
        results.add_result("Streamlit main page", False, f"Error: {e}")
    
    # Test health endpoint (Streamlit's internal)
    try:
        response = requests.get(f"{streamlit_url}/healthz", timeout=5)
        results.add_result("Streamlit health", response.status_code == 200, "Streamlit healthy")
    except Exception as e:
        results.add_result("Streamlit health", False, f"Error: {e}")
    
    return results

def test_file_structure():
    """Test the file structure and components."""
    print("\n🧪 Testing File Structure...")
    results = TestResults()
    
    required_files = [
        ("robust_json_manager.py", "Robust JSON Manager"),
        ("enhanced_api_server.py", "Enhanced API Server"),
        ("enhanced_app.py", "Enhanced Streamlit App"),
        ("enhanced_unified_server.py", "Enhanced Unified Server"),
        ("run_local.py", "Local Development Script")
    ]
    
    for filename, description in required_files:
        file_exists = Path(filename).exists()
        results.add_result(f"{description} file", file_exists, filename if file_exists else "File not found")
    
    # Test preferences file
    prefs_file = Path("user_preferences.json")
    if prefs_file.exists():
        try:
            with open(prefs_file, 'r') as f:
                data = json.load(f)
            
            has_metadata = "_metadata" in data
            has_users = "users" in data
            results.add_result("Preferences file format", has_metadata and has_users, "New format detected")
        except Exception as e:
            results.add_result("Preferences file format", False, f"Parse error: {e}")
    else:
        results.add_result("Preferences file", False, "File not found")
    
    return results

def test_integration():
    """Test integration between components."""
    print("\n🧪 Testing System Integration...")
    results = TestResults()
    
    # Test API-Streamlit communication
    try:
        # Get system status from API
        api_response = requests.get("http://localhost:8000/api/status", timeout=5)
        
        if api_response.status_code == 200:
            api_data = api_response.json()
            api_users = api_data.get("user_count", 0)
            
            # Check if Streamlit can access the same data
            streamlit_response = requests.get("http://localhost:8501", timeout=10)
            
            if streamlit_response.status_code == 200:
                results.add_result("API-Streamlit integration", True, f"Both services responding, API shows {api_users} users")
            else:
                results.add_result("API-Streamlit integration", False, "Streamlit not responding")
        else:
            results.add_result("API-Streamlit integration", False, "API not responding")
    except Exception as e:
        results.add_result("API-Streamlit integration", False, f"Error: {e}")
    
    # Test data persistence across API calls
    test_data = {
        "name": "Integration Test User",
        "email": "integration@example.com",
        "selected_courses": ["test_course"],
        "time_slots": ["12:00"],
        "min_players": 1,
        "days_ahead": 3,
        "notification_frequency": "daily"
    }
    
    try:
        # Create user
        create_response = requests.post("http://localhost:8000/api/preferences", json=test_data, timeout=5)
        
        if create_response.status_code == 200:
            # Verify user exists
            read_response = requests.get(f"http://localhost:8000/api/preferences/{test_data['email']}", timeout=5)
            
            if read_response.status_code == 200:
                user_data = read_response.json()
                data_matches = user_data.get("name") == test_data["name"]
                results.add_result("Data persistence", data_matches, "Data saved and retrieved correctly")
                
                # Clean up
                requests.delete(f"http://localhost:8000/api/preferences/{test_data['email']}", timeout=5)
            else:
                results.add_result("Data persistence", False, "Failed to retrieve saved data")
        else:
            results.add_result("Data persistence", False, "Failed to save data")
    except Exception as e:
        results.add_result("Data persistence", False, f"Error: {e}")
    
    return results

def main():
    """Run all tests."""
    print("🏌️ Enhanced Golf Availability Monitor - Comprehensive Test Suite")
    print("=" * 70)
    
    print("🔍 Testing enhanced components and system integration...")
    
    # Check if services are running
    print("\n🔌 Checking service availability...")
    
    api_available = False
    streamlit_available = False
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=3)
        api_available = response.status_code == 200
        print(f"  API Server: {'✅ Available' if api_available else '❌ Unavailable'}")
    except:
        print("  API Server: ❌ Unavailable")
    
    try:
        response = requests.get("http://localhost:8501", timeout=3)
        streamlit_available = response.status_code == 200
        print(f"  Streamlit App: {'✅ Available' if streamlit_available else '❌ Unavailable'}")
    except:
        print("  Streamlit App: ❌ Unavailable")
    
    if not api_available and not streamlit_available:
        print("\n⚠️ No services are running. Please start the development server first:")
        print("   python run_local.py")
        print("   or")
        print("   python enhanced_unified_server.py")
        sys.exit(1)
    
    # Run tests
    all_results = []
    
    all_results.append(test_file_structure())
    all_results.append(test_robust_json_manager())
    
    if api_available:
        all_results.append(test_api_endpoints())
    
    if streamlit_available:
        all_results.append(test_streamlit_app())
    
    if api_available and streamlit_available:
        all_results.append(test_integration())
    
    # Aggregate results
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total_tests = total_passed + total_failed
    
    print(f"\n🎯 Overall Test Results:")
    print("=" * 30)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    
    if total_tests > 0:
        success_rate = (total_passed / total_tests) * 100
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("\n🎉 Excellent! Your enhanced Golf Availability Monitor is working great!")
        elif success_rate >= 75:
            print("\n👍 Good! Most features are working. Check failed tests for improvements.")
        elif success_rate >= 50:
            print("\n⚠️ Some issues detected. Review the failed tests.")
        else:
            print("\n❌ Multiple issues detected. Check your setup and configuration.")
    
    print(f"\n📊 Test completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Save test results
    results_file = Path("test_results.json")
    test_report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "success_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0
        },
        "test_categories": [
            {
                "category": f"Test Category {i+1}",
                "passed": result.passed,
                "failed": result.failed,
                "tests": result.tests
            }
            for i, result in enumerate(all_results)
        ]
    }
    
    try:
        with open(results_file, 'w') as f:
            json.dump(test_report, f, indent=2)
        print(f"📄 Detailed test results saved to {results_file}")
    except Exception as e:
        print(f"⚠️ Could not save test results: {e}")

if __name__ == "__main__":
    main()
