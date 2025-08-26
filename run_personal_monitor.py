#!/usr/bin/env python3
"""
Simple script to run personalized golf monitoring for a specific user.
Works with both cloud API and local user preferences.
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

def get_users_from_cloud():
    """Try to get users from cloud API."""
    api_url = os.getenv("API_URL", "")
    if not api_url or "localhost" in api_url:
        return {}
    
    try:
        response = requests.get(f"{api_url}/api/preferences", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("preferences", {})
    except:
        pass
    return {}

def get_users_from_local():
    """Get users from local file."""
    prefs_file = Path("streamlit_app/user_preferences.json")
    if prefs_file.exists():
        try:
            with open(prefs_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def get_all_users():
    """Get all available users (cloud first, then local)."""
    # Try cloud first
    users = get_users_from_cloud()
    source = "cloud API"
    
    # Fallback to local
    if not users:
        users = get_users_from_local()
        source = "local file"
    
    if users:
        console.print(f"✅ Found {len(users)} user profiles from {source}:", style="green")
        for email, user_data in users.items():
            name = user_data.get('name', 'Unknown')
            courses = len(user_data.get('selected_courses', []))
            console.print(f"  📧 {email} - {name} ({courses} courses)")
    else:
        console.print("❌ No user profiles found!", style="red")
        console.print("💡 Create profiles using your Streamlit app first:")
        console.print(f"   {os.getenv('API_URL', 'https://your-app.onrender.com')}")
    
    return users

def show_user_details(user_data):
    """Show detailed user preferences."""
    console.print(f"\n📋 User Profile Details:", style="bold blue")
    console.print(f"  👤 Name: {user_data.get('name', 'Unknown')}")
    console.print(f"  📧 Email: {user_data.get('email')}")
    console.print(f"  🏌️ Selected Courses: {len(user_data.get('selected_courses', []))}")
    
    # Show courses
    courses = user_data.get('selected_courses', [])
    if courses:
        console.print(f"     Courses: {', '.join(courses[:3])}{'...' if len(courses) > 3 else ''}")
    
    # Show time preferences
    time_slots = user_data.get('time_slots', user_data.get('selected_time_slots', []))
    console.print(f"  ⏰ Time Slots: {len(time_slots)}")
    if time_slots:
        console.print(f"     Times: {time_slots[0]} - {time_slots[-1]} (and {len(time_slots)-2} others)" if len(time_slots) > 2 else f"     Times: {', '.join(time_slots)}")
    
    console.print(f"  📅 Days Ahead: {user_data.get('days_ahead', 7)}")
    console.print(f"  👥 Min Players: {user_data.get('min_players', 1)}")

def run_monitoring_for_user(email, user_data):
    """Run golf monitoring for a specific user."""
    console.print(f"\n🚀 Starting Golf Monitoring for {user_data.get('name', email)}", style="bold green")
    console.print("=" * 60)
    
    # Show user details
    show_user_details(user_data)
    
    # Create temporary preferences file
    temp_file = Path("temp_monitoring_prefs.json")
    temp_prefs = {email: user_data}
    
    try:
        with open(temp_file, 'w') as f:
            json.dump(temp_prefs, f, indent=2)
        
        console.print(f"\n💾 Created temporary preferences file")
        console.print("🌐 Starting browser for golfbox login...")
        console.print("⏳ This may take a few minutes to complete...")
        
        # Set environment to force use of temp file
        original_api_url = os.environ.get("API_URL")
        os.environ["API_URL"] = "http://localhost:8000"  # Force fallback to file
        
        # Import and run monitoring
        import asyncio
        import sys
        
        # Add current directory to path
        sys.path.insert(0, str(Path(__file__).parent))
        
        from golf_availability_monitor import main as monitor_main
        
        # Run the monitoring
        result = asyncio.run(monitor_main())
        
        console.print("✅ Monitoring completed successfully!", style="green")
        return True
        
    except KeyboardInterrupt:
        console.print("\n⏹️ Monitoring cancelled by user", style="yellow")
        return False
    except Exception as e:
        console.print(f"❌ Monitoring failed: {e}", style="red")
        return False
    finally:
        # Restore original API URL
        if original_api_url:
            os.environ["API_URL"] = original_api_url
        
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()
            console.print(f"🗑️ Cleaned up temporary file")

def main():
    """Main function."""
    console.print("🏌️ Personal Golf Availability Monitor", style="bold blue")
    console.print("Monitor golf availability for a specific user profile")
    console.print("=" * 60)
    
    # Get all available users
    users = get_all_users()
    
    if not users:
        console.print("\n💡 To create user profiles:")
        console.print("1. Visit your Streamlit app")
        console.print("2. Fill out the golf preferences form")
        console.print("3. Save your profile")
        console.print("4. Run this script again")
        return
    
    # Let user choose
    console.print(f"\n🎯 Select a user to monitor:")
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
        
        # Run monitoring
        user_data = users[selected_email]
        success = run_monitoring_for_user(selected_email, user_data)
        
        if success:
            console.print(f"\n🎉 Monitoring completed for {user_data.get('name', selected_email)}!")
            console.print("📧 Check your email for any availability notifications")
        
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!")
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")

if __name__ == "__main__":
    main()
