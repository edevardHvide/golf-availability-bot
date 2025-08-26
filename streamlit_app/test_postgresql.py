#!/usr/bin/env python3
"""
PostgreSQL Connection Test for Golf Availability Monitor

This script tests the PostgreSQL database connection and basic operations.
Run this before deploying to Render to ensure everything works.
"""

import os
import sys
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_postgresql_connection():
    """Test PostgreSQL database connection."""
    print("🧪 Testing PostgreSQL Connection...")
    print("=" * 50)
    
    # Check if DATABASE_URL is set
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        print("\nFor local testing, set:")
        print("DATABASE_URL=postgresql://golfdb_li04_user:your_password@host:5432/golfdb_li04")
        return False
    
    # Hide password in logs
    safe_url = database_url.replace(database_url.split('@')[0].split(':')[-1], '***')
    print(f"🔗 Database URL: {safe_url}")
    
    try:
        # Import and test PostgreSQL manager
        from postgresql_manager import PostgreSQLManager, initialize_database
        
        print("✅ PostgreSQL manager imported successfully")
        
        # Initialize database
        print("\n🔧 Initializing database...")
        success = initialize_database()
        
        if not success:
            print("❌ Database initialization failed")
            return False
            
        print("✅ Database initialized successfully")
        
        # Create manager instance
        db_manager = PostgreSQLManager()
        
        # Test health check
        print("\n🩺 Running health check...")
        health = db_manager.health_check()
        print(f"Status: {health.get('status')}")
        print(f"Connected: {health.get('connected')}")
        print(f"User Count: {health.get('user_count')}")
        
        if not health.get('connected'):
            print("❌ Database health check failed")
            return False
            
        # Test saving user preferences
        print("\n💾 Testing user preferences save...")
        test_preferences = {
            "name": "Test User",
            "email": "test@example.com",
            "selected_courses": ["oslo_golfklubb"],
            "time_slots": ["08:00", "09:00"],
            "min_players": 2,
            "days_ahead": 7,
            "notification_frequency": "immediate"
        }
        
        save_success = db_manager.save_user_preferences(test_preferences)
        if save_success:
            print("✅ User preferences saved successfully")
        else:
            print("❌ Failed to save user preferences")
            return False
        
        # Test loading user preferences
        print("\n📤 Testing user preferences load...")
        loaded_prefs = db_manager.load_user_preferences("test@example.com")
        
        if loaded_prefs:
            print("✅ User preferences loaded successfully")
            print(f"Name: {loaded_prefs.get('name')}")
            print(f"Courses: {len(loaded_prefs.get('selected_courses', []))}")
        else:
            print("❌ Failed to load user preferences")
            return False
        
        # Test getting all preferences
        print("\n📋 Testing get all preferences...")
        all_prefs = db_manager.get_all_user_preferences()
        print(f"✅ Found {len(all_prefs)} user profiles")
        
        # Test cleanup (optional)
        print("\n🧹 Testing cleanup (deleting test user)...")
        delete_success = db_manager.delete_user_preferences("test@example.com")
        if delete_success:
            print("✅ Test user deleted successfully")
        else:
            print("⚠️ Test user not found (maybe already deleted)")
        
        # Final health check
        print("\n🏁 Final health check...")
        final_health = db_manager.health_check()
        print(f"Final status: {final_health.get('status')}")
        
        db_manager.close()
        
        print("\n🎉 All PostgreSQL tests PASSED!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nMake sure you have installed:")
        print("pip install psycopg2-binary sqlalchemy")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_api_with_postgresql():
    """Test the API server with PostgreSQL."""
    print("\n🚀 Testing API Server with PostgreSQL...")
    print("=" * 50)
    
    try:
        import requests
        import time
        import subprocess
        import threading
        
        # Start API server in background
        def start_api():
            try:
                subprocess.run([
                    "python", "render_api_server_postgresql.py"
                ], cwd=".", capture_output=True)
            except Exception as e:
                print(f"API startup error: {e}")
        
        print("🔧 Starting API server...")
        api_thread = threading.Thread(target=start_api, daemon=True)
        api_thread.start()
        
        # Wait for server to start
        time.sleep(3)
        
        # Test health endpoint
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print("✅ API health check passed")
                print(f"Status: {data.get('status')}")
                print(f"Storage: {data.get('storage', {}).get('type')}")
            else:
                print(f"❌ API health check failed: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ API connection failed: {e}")
            print("Make sure no other service is running on port 8000")
            return False
        
        # Test database health endpoint
        try:
            response = requests.get("http://localhost:8000/api/database/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print("✅ Database health endpoint working")
                print(f"Database status: {data.get('status')}")
            else:
                print(f"⚠️ Database health endpoint issue: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Database health endpoint error: {e}")
        
        print("✅ API server with PostgreSQL working!")
        return True
        
    except ImportError:
        print("❌ 'requests' not installed. Run: pip install requests")
        return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def main():
    """Run all PostgreSQL tests."""
    print("🎯 PostgreSQL Integration Test Suite")
    print("For Golf Availability Monitor on Render")
    print("=" * 50)
    
    # Test 1: PostgreSQL Connection
    db_test = test_postgresql_connection()
    
    # Test 2: API with PostgreSQL (optional, requires stopping manually)
    if db_test:
        print("\n" + "=" * 50)
        run_api_test = input("🤔 Run API test? (y/N): ").lower().strip() == 'y'
        
        if run_api_test:
            api_test = test_api_with_postgresql()
        else:
            api_test = True  # Skip API test
    else:
        api_test = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary")
    print(f"Database Connection: {'✅ PASS' if db_test else '❌ FAIL'}")
    print(f"API Integration: {'✅ PASS' if api_test else '❌ FAIL'}")
    
    if db_test and api_test:
        print("\n🎉 Ready for Render deployment!")
        print("\nNext steps:")
        print("1. Commit and push your changes to GitHub")
        print("2. Deploy API service with PostgreSQL connection")
        print("3. Deploy UI service with API_BASE_URL")
        print("4. Test the live deployment")
    else:
        print("\n❌ Fix issues before deploying to Render")
        
    return db_test and api_test

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
        sys.exit(1)
