#!/usr/bin/env python3
"""
Demo script to create sample user profiles for testing the profile loading functionality
"""

import json
from pathlib import Path
from datetime import datetime

def create_sample_profiles():
    """Create sample user profiles for testing."""
    
    preferences_file = Path(__file__).parent.parent / "user_preferences.json"
    
    # Sample user profiles
    sample_profiles = {
        "john.doe@example.com": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "selected_courses": ["oslo_golfklubb", "baerum_gk", "asker_golfklubb"],
            "time_slots": ["07:00", "08:00", "09:00"],
            "min_players": 2,
            "days_ahead": 7,
            "notification_frequency": "immediate",
            "timestamp": "2025-08-25T10:30:00"
        },
        "jane.smith@example.com": {
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "selected_courses": ["miklagard_gk", "losby_golfklubb", "groruddalen_golfklubb"],
            "time_slots": ["06:00", "07:00", "08:00", "16:00", "17:00"],
            "min_players": 1,
            "days_ahead": 4,
            "notification_frequency": "hourly",
            "timestamp": "2025-08-25T14:15:00"
        },
        "alex.johnson@example.com": {
            "name": "Alex Johnson",
            "email": "alex.johnson@example.com",
            "selected_courses": ["kongsberg_golfklubb", "larvik_golfklubb"],
            "time_slots": ["09:00", "10:00", "11:00", "14:00"],
            "min_players": 3,
            "days_ahead": 10,
            "notification_frequency": "daily",
            "timestamp": "2025-08-24T16:45:00"
        }
    }
    
    # Save sample profiles
    with open(preferences_file, 'w') as f:
        json.dump(sample_profiles, f, indent=2)
    
    print("🎯 Sample User Profiles Created!")
    print("=" * 40)
    print(f"📁 File: {preferences_file}")
    print(f"👥 Users: {len(sample_profiles)}")
    print()
    
    for email, profile in sample_profiles.items():
        print(f"📧 {email}")
        print(f"   Name: {profile['name']}")
        print(f"   Courses: {len(profile['selected_courses'])} selected")
        print(f"   Time Slots: {len(profile['time_slots'])} selected")
        print(f"   Notification: {profile['notification_frequency']}")
        print()
    
    print("✅ You can now test the profile loading feature by entering any of these emails:")
    for email in sample_profiles.keys():
        print(f"   • {email}")

if __name__ == "__main__":
    create_sample_profiles()
