#!/usr/bin/env python3
"""
Test script to retrieve a specific user's profile from cloud API
and run personalized golf monitoring for them.
"""

import os
import json
import requests
from dotenv import load_dotenv
from rich.console import Console
from pathlib import Path

# Load environment
load_dotenv(override=True)
console = Console()

def test_api_connection():
    """Test connection to the cloud API."""
    api_url = os.getenv("API_URL", "http://localhost:8000")
    console.print(f"🔍 Testing API connection to: {api_url}")
    
    try:
        # Test health endpoint
        response = requests.get(f"{api_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            console.print(f"✅ API Health: {data.get('status', 'OK')}", style="green")
            console.print(f"📊 User count: {data.get('user_count', 0)}")
            return True
        else:
            console.print(f"❌ API Health check failed: {response.status_code}", style="red")
            return False
    except Exception as e:
        console.print(f"❌ API connection failed: {e}", style="red")
        return False

def get_all_users():
    """Get all user profiles from the API."""
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    try:
        response = requests.get(f"{api_url}/api/preferences", timeout=10)
        if response.status_code == 200:
            data = response.json()
            preferences = data.get("preferences", {})
            console.print(f"✅ Found {len(preferences)} user profiles:", style="green")
            
            for email, user_data in preferences.items():
                name = user_data.get('name', 'Unknown')
                courses = len(user_data.get('selected_courses', []))
                console.print(f"  📧 {email} - {name} ({courses} courses)")
            
            return preferences
        else:
            console.print(f"❌ Failed to get users: {response.status_code}", style="red")
            return {}
    except Exception as e:
        console.print(f"❌ Error getting users: {e}", style="red")
        return {}

def get_user_profile(email):
    """Get a specific user's profile."""
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    try:
        response = requests.get(f"{api_url}/api/preferences/{email}", timeout=10)
        if response.status_code == 200:
            user_data = response.json()
            console.print(f"✅ Profile loaded for {user_data.get('name', 'Unknown')}:", style="green")
            console.print(f"  📧 Email: {user_data.get('email')}")
            console.print(f"  🏌️ Courses: {len(user_data.get('selected_courses', []))}")
            console.print(f"  ⏰ Time slots: {len(user_data.get('selected_time_slots', []))}")
            console.print(f"  📅 Days ahead: {user_data.get('days_ahead', 7)}")
            console.print(f"  👥 Min players: {user_data.get('min_players', 1)}")
            
            return user_data
        else:
            console.print(f"❌ User not found: {email}", style="red")
            return None
    except Exception as e:
        console.print(f"❌ Error getting user profile: {e}", style="red")
        return None

def run_monitoring_for_user(email):
    """Run the golf monitoring for a specific user."""
    console.print(f"\n🎯 Running personalized monitoring for: {email}")
    
    # Get user profile
    user_profile = get_user_profile(email)
    if not user_profile:
        return False
    
    # Save to temporary file for the monitoring script
    temp_file = Path("temp_user_profile.json")
    temp_prefs = {email: user_profile}
    
    with open(temp_file, 'w') as f:
        json.dump(temp_prefs, f, indent=2)
    
    console.print(f"💾 Saved profile to: {temp_file}")
    
    # Set environment variable to use the temp file
    os.environ["USER_PREFERENCES_FILE"] = str(temp_file)
    
    console.print("🚀 Starting golf availability monitoring...")
    console.print("📌 This will open a browser for golfbox login if needed")
    
    # Import and run the monitoring
    try:
        import asyncio
        from golf_availability_monitor import main as monitor_main
        
        # Run the monitoring
        asyncio.run(monitor_main())
        
        console.print("✅ Monitoring completed!", style="green")
        
    except Exception as e:
        console.print(f"❌ Monitoring failed: {e}", style="red")
    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()
            console.print(f"🗑️ Cleaned up {temp_file}")

def main():
    """Main function to test user profile retrieval and monitoring."""
    console.print("🏌️ Golf Availability Monitor - User Profile Test", style="bold blue")
    console.print("=" * 60)
    
    # Test API connection
    if not test_api_connection():
        console.print("❌ Cannot connect to API. Check your .env file:", style="red")
        console.print(f"   API_URL={os.getenv('API_URL', 'NOT SET')}")
        return
    
    console.print("\n📋 Available user profiles:")
    users = get_all_users()
    
    if not users:
        console.print("❌ No users found. Create some profiles in your Streamlit app first!", style="red")
        return
    
    # Let user choose which profile to test
    console.print(f"\n🎯 Choose a user to run monitoring for:")
    emails = list(users.keys())
    
    for i, email in enumerate(emails, 1):
        name = users[email].get('name', 'Unknown')
        console.print(f"  {i}. {email} ({name})")
    
    try:
        choice = input(f"\nEnter number (1-{len(emails)}) or email address: ").strip()
        
        # Check if it's a number
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(emails):
                selected_email = emails[idx]
            else:
                console.print("❌ Invalid number", style="red")
                return
        else:
            # Check if it's an email
            if choice in users:
                selected_email = choice
            else:
                console.print("❌ Email not found", style="red")
                return
        
        # Run monitoring for selected user
        run_monitoring_for_user(selected_email)
        
    except KeyboardInterrupt:
        console.print("\n👋 Cancelled by user")
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")

if __name__ == "__main__":
    main()
