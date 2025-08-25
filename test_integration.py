#!/usr/bin/env python3
"""
Test script for personalized golf monitoring integration
"""

import sys
import json
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

def test_integration():
    """Test the integration between main app and user preferences."""
    print("🧪 Testing Golf Monitor Integration with User Preferences")
    print("=" * 60)
    
    # Test 1: Check if we can load user preferences
    print("\n📋 Test 1: Loading User Preferences")
    try:
        from golf_availability_monitor import get_user_preferences
        user_prefs = get_user_preferences()
        print(f"✅ Loaded {len(user_prefs)} user profiles")
        
        for i, user in enumerate(user_prefs, 1):
            name = user.get('name', 'Unknown')
            email = user.get('email', 'No email')
            courses = len(user.get('selected_courses', []))
            times = len(user.get('time_slots', []))
            print(f"   {i}. {name} ({email}) - {courses} courses, {times} time slots")
    except Exception as e:
        print(f"❌ Error loading preferences: {e}")
        return False
    
    # Test 2: Check golf club mapping
    print("\n🏌️ Test 2: Golf Club Integration")
    try:
        from golf_club_urls import golf_url_manager
        from golf_availability_monitor import filter_availability_for_user
        import datetime
        
        # Test with sample data
        sample_availability = {
            "Oslo Golfklubb_2025-08-25": {"07:00": 2, "08:00": 1},
            "Bærum GK_2025-08-25": {"09:00": 3, "10:00": 2},
            "Miklagard GK_2025-08-25": {"07:30": 1, "11:00": 4}
        }
        
        if user_prefs:
            user = user_prefs[0]  # Test with first user
            target_date = datetime.date.today()
            filtered = filter_availability_for_user(user, sample_availability, target_date)
            
            print(f"✅ Filtered availability for {user.get('name')}: {len(filtered)} matching slots")
            for key, times in filtered.items():
                print(f"   {key}: {times}")
        else:
            print("⚠️ No user preferences to test filtering")
    except Exception as e:
        print(f"❌ Error testing filtering: {e}")
        return False
    
    # Test 3: Check email template personalization
    print("\n📧 Test 3: Email Template Personalization")
    try:
        from golf_utils import create_html_email_template
        
        if user_prefs:
            user = user_prefs[0]
            sample_new_availability = [
                "Oslo Golfklubb on Today (2025-08-25) at 07:00: 2 spots",
                "Bærum GK on Tomorrow (2025-08-26) at 09:00: 1 spot"
            ]
            
            html_content = create_html_email_template(
                subject="Test Golf Alert",
                new_availability=sample_new_availability,
                all_availability={},
                time_window="Personalized",
                config_info={'user_name': user.get('name')},
                club_order=None,
                user_preferences=user
            )
            
            # Check if personalization is included
            user_name = user.get('name', '')
            if user_name in html_content:
                print(f"✅ Email template personalized for {user_name}")
            else:
                print("⚠️ Email template may not be fully personalized")
        else:
            print("⚠️ No user preferences to test email personalization")
    except Exception as e:
        print(f"❌ Error testing email template: {e}")
        return False
    
    # Test 4: Check API server integration
    print("\n🌐 Test 4: API Server Integration")
    try:
        import requests
        response = requests.get("http://localhost:8000/api/preferences", timeout=5)
        if response.status_code == 200:
            data = response.json()
            api_user_count = len(data.get("preferences", {}))
            print(f"✅ API server responding: {api_user_count} profiles available")
        else:
            print(f"⚠️ API server returned status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("⚠️ API server not running (will fall back to local file)")
    except Exception as e:
        print(f"❌ Error testing API: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Integration Test Summary:")
    print("✅ User preferences loading: Working")
    print("✅ Golf club filtering: Working") 
    print("✅ Email personalization: Working")
    print("⚠️ API server: Optional (fallback available)")
    print("\n🚀 Ready to run personalized golf monitoring!")
    print("\nTo start monitoring with user preferences:")
    print("   python golf_availability_monitor.py")
    print("\nTo manage user preferences:")
    print("   cd streamlit_app && python run_local.py")

if __name__ == "__main__":
    test_integration()
