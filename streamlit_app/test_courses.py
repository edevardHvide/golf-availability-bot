#!/usr/bin/env python3
"""
Test script to verify all golf courses are loaded correctly
"""

import sys
from pathlib import Path

# Add parent directory to path to import golf modules
sys.path.append(str(Path(__file__).parent.parent))

def test_courses():
    """Test that all courses are loaded correctly."""
    print("🏌️ Testing Golf Course Loading")
    print("=" * 40)
    
    try:
        from golf_club_urls import golf_url_manager
        print(f"✅ Successfully imported golf_url_manager")
        print(f"📊 Total courses available: {len(golf_url_manager.clubs)}")
        print()
        
        # Test the same function that the Streamlit app uses
        courses = []
        for key, club in golf_url_manager.clubs.items():
            courses.append({
                'key': key,
                'name': club.display_name,
                'location': f"{club.location[0]:.2f}, {club.location[1]:.2f}" if club.location else "Unknown",
                'default_start_time': f"{club.default_start_time[:2]}:{club.default_start_time[2:4]}"
            })
        
        # Sort by display name (same as in Streamlit app)
        sorted_courses = sorted(courses, key=lambda x: x['name'])
        
        print("📋 All Available Golf Courses:")
        print("-" * 40)
        for i, course in enumerate(sorted_courses, 1):
            print(f"{i:2d}. {course['name']}")
            print(f"     Key: {course['key']}")
            print(f"     Location: {course['location']}")
            print(f"     Default Start: {course['default_start_time']}")
            print()
        
        print(f"✅ Successfully loaded {len(sorted_courses)} golf courses")
        print("🎯 All courses will be available in the Streamlit interface!")
        
    except ImportError as e:
        print(f"❌ Failed to import golf_club_urls: {e}")
        print("The app will fall back to demo data.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_courses()
