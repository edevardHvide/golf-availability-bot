#!/usr/bin/env python3
"""
Test script to retrieve user profiles from your cloud API
and run personalized golf monitoring.
"""

import os
import json
import requests
import asyncio
from dotenv import load_dotenv
from rich.console import Console
from pathlib import Path

# Load environment
load_dotenv(override=True)
console = Console()

def test_cloud_api():
    """Test connection to cloud API with both ports."""
    api_url = os.getenv("API_URL", "").strip()
    
    if not api_url:
        console.print("❌ API_URL not set in .env file", style="red")
        return False
    
    console.print(f"🔍 Testing API connection to: {api_url}")
    
    # Test both main port and port 8000 for API
    test_urls = [
        f"{api_url}/health",           # Streamlit health (if API is embedded)
        f"{api_url}:8000/health",      # API server on port 8000
        f"{api_url}/api/health",       # API through Streamlit
    ]
    
    for test_url in test_urls:
        try:
            console.print(f"  🔗 Trying: {test_url}")
            response = requests.get(test_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                console.print(f"  ✅ Success! Status: {data.get('status', 'OK')}", style="green")
                console.print(f"  📊 User count: {data.get('user_count', 0)}")
                return test_url.replace('/health', '')
        except Exception as e:
            console.print(f"  ❌ Failed: {str(e)[:50]}...", style="red")
    
    return False

def get_users_from_api(base_url):
    """Get all user profiles from the API."""
    try:
        response = requests.get(f"{base_url}/api/preferences", timeout=10)
        if response.status_code == 200:
            data = response.json()
            preferences = data.get("preferences", {})
            console.print(f"✅ Retrieved {len(preferences)} user profiles from cloud API:", style="green")
            
            for email, user_data in preferences.items():
                name = user_data.get('name', 'Unknown')
                courses = len(user_data.get('selected_courses', []))
                time_slots = len(user_data.get('time_slots', user_data.get('selected_time_slots', [])))
                console.print(f"  📧 {email}")
                console.print(f"     👤 {name}")
                console.print(f"     🏌️ {courses} courses, ⏰ {time_slots} time slots")
            
            return preferences
        else:
            console.print(f"❌ API returned status {response.status_code}", style="red")
            return {}
    except Exception as e:
        console.print(f"❌ Error retrieving users: {e}", style="red")
        return {}

def get_user_profile(base_url, email):
    """Get specific user profile from API."""
    try:
        response = requests.get(f"{base_url}/api/preferences/{email}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            console.print(f"❌ User {email} not found", style="red")
            return None
    except Exception as e:
        console.print(f"❌ Error getting user profile: {e}", style="red")
        return None

def run_monitoring_for_user(email, user_data):
    """Run golf monitoring for a specific user."""
    console.print(f"\n🚀 Starting Personal Golf Monitor", style="bold green")
    console.print(f"👤 User: {user_data.get('name', 'Unknown')} ({email})")
    console.print(f"🏌️ Courses: {len(user_data.get('selected_courses', []))}")
    console.print(f"⏰ Time slots: {len(user_data.get('time_slots', user_data.get('selected_time_slots', [])))}")
    console.print(f"📅 Days ahead: {user_data.get('days_ahead', 7)}")
    console.print("=" * 60)
    
    # Create temporary preferences file
    temp_file = Path("temp_cloud_prefs.json")
    temp_prefs = {email: user_data}
    
    try:
        with open(temp_file, 'w') as f:
            json.dump(temp_prefs, f, indent=2)
        
        console.print("💾 Created temporary preferences file")
        console.print("🌐 Opening browser for golfbox login...")
        console.print("⏳ Monitoring in progress...")
        
        # Temporarily disable API URL to force file usage
        original_api_url = os.environ.get("API_URL")
        os.environ["API_URL"] = "http://localhost:8000"  # Force fallback
        
        # Import and run monitoring
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        
        from golf_availability_monitor import main as monitor_main
        
        # Run the monitoring
        asyncio.run(monitor_main())
        
        console.print("✅ Monitoring completed!", style="green")
        console.print("📧 Check your email for any notifications")
        return True
        
    except KeyboardInterrupt:
        console.print("\n⏹️ Cancelled by user", style="yellow")
        return False
    except Exception as e:
        console.print(f"❌ Monitoring failed: {e}", style="red")
        console.print("💡 Try running the basic monitoring script instead")
        return False
    finally:
        # Restore API URL
        if original_api_url:
            os.environ["API_URL"] = original_api_url
        
        # Clean up
        if temp_file.exists():
            temp_file.unlink()
            console.print("🗑️ Cleaned up temporary file")

def main():
    """Main function."""
    console.print("🌐 Cloud API Golf Monitor", style="bold blue")
    console.print("Retrieve user profiles from cloud and run monitoring")
    console.print("=" * 60)
    
    # Test API connection
    base_url = test_cloud_api()
    if not base_url:
        console.print("\n❌ Cannot connect to your cloud API!", style="red")
        console.print("\n💡 Solutions:")
        console.print("1. Check your Render deployment is running")
        console.print("2. Update Render start command to: bash startup.sh")
        console.print("3. Wait a few minutes for deployment")
        console.print(f"4. Verify API_URL in .env: {os.getenv('API_URL', 'NOT SET')}")
        return
    
    console.print(f"\n✅ Connected to API at: {base_url}", style="green")
    
    # Get all users
    users = get_users_from_api(base_url)
    if not users:
        console.print("\n❌ No user profiles found!", style="red")
        console.print("💡 Create profiles using your Streamlit app:")
        console.print(f"   {os.getenv('API_URL')}")
        return
    
    # Let user choose
    console.print(f"\n🎯 Select user for monitoring:")
    emails = list(users.keys())
    
    for i, email in enumerate(emails, 1):
        name = users[email].get('name', 'Unknown')
        console.print(f"  {i}. {email} ({name})")
    
    try:
        choice = input(f"\nEnter number (1-{len(emails)}) or email: ").strip()
        
        # Parse choice
        selected_email = None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(emails):
                selected_email = emails[idx]
        elif choice in users:
            selected_email = choice
        
        if not selected_email:
            console.print("❌ Invalid selection", style="red")
            return
        
        # Get fresh profile data
        user_data = get_user_profile(base_url, selected_email)
        if not user_data:
            return
        
        # Run monitoring
        success = run_monitoring_for_user(selected_email, user_data)
        
        if success:
            console.print(f"\n🎉 Successfully monitored for {user_data.get('name', selected_email)}!")
        
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!")
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")

if __name__ == "__main__":
    main()
