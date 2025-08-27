"""
Golf Course Data Module for Streamlit App

This module provides golf course data either from the main golf_club_urls module
or as a standalone fallback for the streamlit app.
"""

import sys
from pathlib import Path
from typing import List, Dict

# Try to import from parent directory
try:
    sys.path.append(str(Path(__file__).parent.parent))
    from golf_club_urls import golf_url_manager
    GOLF_SYSTEM_AVAILABLE = True
except ImportError:
    GOLF_SYSTEM_AVAILABLE = False
    golf_url_manager = None

def get_available_courses() -> List[Dict]:
    """Get available golf courses with consistent format."""
    
    if GOLF_SYSTEM_AVAILABLE and golf_url_manager:
        try:
            courses = []
            for key, club in golf_url_manager.clubs.items():
                courses.append({
                    'key': key,
                    'name': club.display_name,
                    'location': f"{club.location[0]:.2f}, {club.location[1]:.2f}" if club.location else "Unknown",
                    'default_start_time': f"{club.default_start_time[:2]}:{club.default_start_time[2:4]}" if len(club.default_start_time) >= 4 else "07:00"
                })
            
            # Sort by name for better UX
            return sorted(courses, key=lambda x: x['name'])
            
        except Exception as e:
            print(f"Error loading from golf_url_manager: {e}")
    
    # Fallback courses if golf system is not available
    return [
        {'key': 'oslo_golfklubb', 'name': 'Oslo Golfklubb', 'location': '59.91, 10.75', 'default_start_time': '07:30'},
        {'key': 'haga_gk', 'name': 'Haga GK', 'location': '59.28, 11.11', 'default_start_time': '07:30'},
        {'key': 'grini_gk', 'name': 'Grini GK', 'location': '60.22, 10.42', 'default_start_time': '07:00'},
        {'key': 'baerum_gk', 'name': 'Bærum GK', 'location': '59.89, 10.52', 'default_start_time': '06:00'},
        {'key': 'miklagard_gk', 'name': 'Miklagard GK', 'location': '59.97, 11.04', 'default_start_time': '07:00'},
        {'key': 'hauger_gk', 'name': 'Hauger GK', 'location': '59.27, 10.41', 'default_start_time': '07:00'},
        {'key': 'drobak_bk', 'name': 'Drøbak BK', 'location': '59.66, 10.63', 'default_start_time': '00:00'},
        {'key': 'onsoy_gk', 'name': 'Onsøy GK', 'location': '59.22, 10.93', 'default_start_time': '07:00'},
        {'key': 'tyrifjord_gk', 'name': 'Tyrifjord GK', 'location': '59.97, 9.98', 'default_start_time': '07:00'},
        {'key': 'oppegard_gk', 'name': 'Oppegård GK', 'location': '59.78, 10.78', 'default_start_time': '07:00'},
        {'key': 'asker_golfklubb', 'name': 'Asker Golfklubb', 'location': '59.84, 10.44', 'default_start_time': '07:00'},
        {'key': 'askim_golfklubb', 'name': 'Askim Golfklubb', 'location': '59.58, 11.17', 'default_start_time': '07:00'},
        {'key': 'ballerud_golfklubb', 'name': 'Ballerud Golfklubb', 'location': '59.92, 10.48', 'default_start_time': '07:00'},
        {'key': 'borre_golfklubb', 'name': 'Borre Golfklubb', 'location': '59.42, 10.43', 'default_start_time': '09:00'},
        {'key': 'borregaard_golfklubb', 'name': 'Borregaard Golfklubb', 'location': '59.22, 11.17', 'default_start_time': '07:00'},
        {'key': 'gersjoen_golfklubb', 'name': 'Gersjøen Golfklubb', 'location': '59.88, 10.82', 'default_start_time': '07:00'},
        {'key': 'grenland_og_omegn_golfklubb', 'name': 'Grenland og Omegn Golfklubb', 'location': '59.17, 9.67', 'default_start_time': '06:30'},
        {'key': 'groruddalen_golfklubb', 'name': 'Groruddalen Golfklubb', 'location': '59.97, 10.88', 'default_start_time': '07:00'},
        {'key': 'gronmo_golfklubb', 'name': 'Grønmo Golfklubb', 'location': '59.82, 10.77', 'default_start_time': '06:00'},
        {'key': 'kongsberg_golfklubb', 'name': 'Kongsberg Golfklubb', 'location': '59.67, 9.65', 'default_start_time': '06:00'},
        {'key': 'losby_golfklubb', 'name': 'Losby Golfklubb', 'location': '59.92, 10.96', 'default_start_time': '07:00'},
        {'key': 'holtsmark_golfklubb', 'name': 'Holtsmark Golfklubb', 'location': '59.75, 10.22', 'default_start_time': '00:00'},
        {'key': 'larvik_golfklubb', 'name': 'Larvik Golfklubb', 'location': '59.05, 10.04', 'default_start_time': '00:00'},
        {'key': 'moss_og_rygge_golfklubb', 'name': 'Moss & Rygge Golfklubb', 'location': '59.44, 10.66', 'default_start_time': '07:00'},
        {'key': 'notteroy_golfklubb', 'name': 'Nøtterøy Golfklubb', 'location': '59.22, 10.42', 'default_start_time': '06:00'},
        {'key': 'ostmarka_golfklubb', 'name': 'Østmarka Golfklubb', 'location': '59.88, 10.92', 'default_start_time': '07:00'}
    ]

def get_course_by_key(key: str) -> Dict:
    """Get a specific course by its key."""
    courses = get_available_courses()
    for course in courses:
        if course['key'] == key:
            return course
    return None

def get_courses_by_keys(keys: List[str]) -> List[Dict]:
    """Get multiple courses by their keys."""
    courses = get_available_courses()
    result = []
    for key in keys:
        for course in courses:
            if course['key'] == key:
                result.append(course)
                break
    return result
