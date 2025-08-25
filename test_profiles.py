#!/usr/bin/env python3
"""
Test user profile retrieval from cloud API without running full monitoring.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the project directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
load_dotenv(override=True)

# Import the function we want to test
from golf_availability_monitor import get_user_preferences
from rich.console import Console

console = Console()

def main():
    """Test user profile retrieval."""
    console.print("🧪 Testing User Profile Retrieval", style="bold blue")
    console.print("=" * 50)
    
    # Show API configuration
    api_url = os.getenv("API_URL", "")
    console.print(f"📍 API URL: {api_url}")
    
    # Test profile retrieval
    try:
        user_preferences = get_user_preferences()
        
        if user_preferences:
            console.print(f"\n✅ SUCCESS! Retrieved {len(user_preferences)} user profiles", style="bold green")
            console.print("\n📋 User Profiles Summary:")
            
            for i, user in enumerate(user_preferences, 1):
                name = user.get('name', 'Unknown')
                email = user.get('email', 'No email')
                courses = user.get('selected_courses', [])
                time_slots = user.get('time_slots', user.get('selected_time_slots', []))
                days_ahead = user.get('days_ahead', 7)
                min_players = user.get('min_players', 1)
                
                console.print(f"\n👤 User {i}: {name}")
                console.print(f"   📧 Email: {email}")
                console.print(f"   🏌️ Courses: {len(courses)} ({', '.join(courses[:3])}{'...' if len(courses) > 3 else ''})")
                console.print(f"   ⏰ Time slots: {len(time_slots)}")
                console.print(f"   📅 Days ahead: {days_ahead}")
                console.print(f"   👥 Min players: {min_players}")
            
            console.print(f"\n🎯 Personalized monitoring is ready!", style="green")
            console.print("When you run the full monitoring script, it will:")
            console.print("• Monitor all courses from all users' preferences")
            console.print("• Send personalized emails to each user")
            console.print("• Each email will contain only slots matching their criteria")
            
        else:
            console.print("\n❌ No user profiles found", style="red")
            console.print("\n💡 Solutions:")
            console.print("1. Make sure your Render app is running both API and Streamlit")
            console.print("2. Update Render start command to: bash startup.sh")
            console.print("3. Create user profiles in your Streamlit app")
            console.print(f"4. Visit: {api_url}")
            
    except Exception as e:
        console.print(f"\n❌ Error retrieving profiles: {e}", style="red")

if __name__ == "__main__":
    main()
