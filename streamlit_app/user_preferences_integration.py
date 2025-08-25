#!/usr/bin/env python3
"""
Enhanced Golf Availability Monitor with User Preferences Support

This script extends the existing golf_availability_monitor.py to support
user preferences from the Streamlit web interface.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from golf_utils import send_email_notification
from golf_club_urls import golf_url_manager
from rich.console import Console

console = Console()

class UserPreferencesManager:
    """Manages user preferences for personalized monitoring."""
    
    def __init__(self, preferences_file: Optional[Path] = None):
        self.preferences_file = preferences_file or Path(__file__).parent.parent / "user_preferences.json"
        
    def load_preferences(self) -> Dict:
        """Load user preferences from file."""
        if not self.preferences_file.exists():
            return {}
        
        try:
            with open(self.preferences_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[red]Error loading preferences: {e}[/red]")
            return {}
    
    def get_active_users(self) -> List[Dict]:
        """Get list of users with complete preferences."""
        all_prefs = self.load_preferences()
        active_users = []
        
        for email, user_prefs in all_prefs.items():
            if self.validate_user_preferences(user_prefs):
                active_users.append(user_prefs)
        
        return active_users
    
    def validate_user_preferences(self, prefs: Dict) -> bool:
        """Validate that user preferences are complete."""
        required_fields = ['name', 'email', 'selected_courses', 'time_slots']
        return all(prefs.get(field) for field in required_fields)
    
    def get_aggregated_courses(self) -> List[str]:
        """Get all courses that any user wants to monitor."""
        all_prefs = self.load_preferences()
        all_courses = set()
        
        for user_prefs in all_prefs.values():
            if self.validate_user_preferences(user_prefs):
                all_courses.update(user_prefs.get('selected_courses', []))
        
        return list(all_courses)
    
    def filter_and_notify_users(self, new_availability: List[str], all_availability: Dict):
        """Send personalized notifications to users based on their preferences."""
        active_users = self.get_active_users()
        
        if not active_users:
            console.print("[yellow]No active users with preferences found[/yellow]")
            return
        
        console.print(f"[green]Processing notifications for {len(active_users)} users[/green]")
        
        for user_prefs in active_users:
            try:
                self.send_user_notification(user_prefs, new_availability, all_availability)
            except Exception as e:
                console.print(f"[red]Error sending notification to {user_prefs.get('email', 'unknown')}: {e}[/red]")
    
    def send_user_notification(self, user_prefs: Dict, new_availability: List[str], all_availability: Dict):
        """Send personalized notification to a specific user."""
        # Filter availability based on user preferences
        filtered_availability = self.filter_availability_for_user(new_availability, user_prefs)
        
        if not filtered_availability:
            console.print(f"[blue]No relevant availability for {user_prefs['name']}[/blue]")
            return
        
        # Temporarily set email recipient
        original_email = os.environ.get('EMAIL_TO', '')
        os.environ['EMAIL_TO'] = user_prefs['email']
        
        try:
            # Create personalized config info
            config_info = {
                'user_name': user_prefs['name'],
                'courses': len(user_prefs.get('selected_courses', [])),
                'time_window': self.get_time_window_string(user_prefs.get('time_slots', [])),
                'min_players': user_prefs.get('min_players', 1),
                'days': user_prefs.get('days_ahead', 4),
                'notification_frequency': user_prefs.get('notification_frequency', 'immediate')
            }
            
            # Send personalized notification
            send_email_notification(
                subject=f"⛳ Personal Golf Alert for {user_prefs['name']}",
                new_availability=filtered_availability,
                all_availability=all_availability,
                time_window=config_info['time_window'],
                config_info=config_info,
                club_order=user_prefs.get('selected_courses', [])
            )
            
            console.print(f"[green]✓ Sent notification to {user_prefs['name']} ({user_prefs['email']})[/green]")
            
        finally:
            # Restore original email setting
            if original_email:
                os.environ['EMAIL_TO'] = original_email
            elif 'EMAIL_TO' in os.environ:
                del os.environ['EMAIL_TO']
    
    def filter_availability_for_user(self, availability: List[str], user_prefs: Dict) -> List[str]:
        """Filter availability based on user's preferences."""
        filtered = []
        
        user_courses = set(user_prefs.get('selected_courses', []))
        user_times = set(user_prefs.get('time_slots', []))
        min_players = user_prefs.get('min_players', 1)
        
        for item in availability:
            # Check if this availability item matches user preferences
            if self.availability_matches_user(item, user_courses, user_times, min_players):
                filtered.append(item)
        
        return filtered
    
    def availability_matches_user(self, availability_item: str, user_courses: set, user_times: set, min_players: int) -> bool:
        """Check if an availability item matches user preferences."""
        import re
        
        # Extract course name (check against display names)
        course_matches = False
        for course_key in user_courses:
            club = golf_url_manager.get_club_by_name(course_key)
            if club and club.display_name.lower() in availability_item.lower():
                course_matches = True
                break
        
        if not course_matches:
            return False
        
        # Extract time
        time_match = re.search(r'at (\d{2}:\d{2}):', availability_item)
        if time_match:
            item_time = time_match.group(1)
            if user_times and item_time not in user_times:
                return False
        
        # Extract number of spots
        spots_match = re.search(r'(\d+) spot', availability_item)
        if spots_match:
            available_spots = int(spots_match.group(1))
            if available_spots < min_players:
                return False
        
        return True
    
    def get_time_window_string(self, time_slots: List[str]) -> str:
        """Convert time slots list to a readable time window string."""
        if not time_slots:
            return "All times"
        
        min_time = min(time_slots)
        max_time = max(time_slots)
        
        if len(time_slots) <= 3:
            return ", ".join(time_slots)
        else:
            return f"{min_time} - {max_time} ({len(time_slots)} slots)"

def enhance_golf_monitor_with_preferences():
    """Enhance the existing golf monitor with user preferences support."""
    
    # This function can be imported and used to modify the existing monitoring logic
    prefs_manager = UserPreferencesManager()
    
    # Return functions that can be used in the main monitor
    return {
        'get_courses_to_monitor': prefs_manager.get_aggregated_courses,
        'process_notifications': prefs_manager.filter_and_notify_users,
        'has_active_users': lambda: len(prefs_manager.get_active_users()) > 0
    }

def create_enhanced_monitor_script():
    """Create an enhanced version of the golf monitor that uses preferences."""
    
    script_content = '''#!/usr/bin/env python3
"""
Enhanced Golf Availability Monitor with User Preferences

This script automatically loads user preferences and monitors accordingly.
"""

import sys
from pathlib import Path

# Add the streamlit_app directory to path
sys.path.append(str(Path(__file__).parent / "streamlit_app"))

from user_preferences_integration import UserPreferencesManager
from golf_availability_monitor import *  # Import all existing functions

# Override the email notification behavior
original_send_notification = send_email_notification

def enhanced_main():
    """Main function with user preferences support."""
    prefs_manager = UserPreferencesManager()
    
    # Check if we have any users with preferences
    active_users = prefs_manager.get_active_users()
    
    if active_users:
        console.print(f"[green]Found {len(active_users)} users with preferences[/green]")
        
        # Get all courses that users want to monitor
        courses_to_monitor = prefs_manager.get_aggregated_courses()
        
        if courses_to_monitor:
            console.print(f"[blue]Monitoring {len(courses_to_monitor)} courses based on user preferences[/blue]")
            
            # Override the SELECTED_CLUBS environment variable
            import os
            os.environ['SELECTED_CLUBS'] = ','.join(courses_to_monitor)
            
            # Run the original monitoring logic
            # But replace the notification system with personalized notifications
            # This would require modifying the original script...
            
            console.print("[yellow]Enhanced monitoring with user preferences is ready![/yellow]")
            console.print("[yellow]Integration with existing monitor script needed.[/yellow]")
        else:
            console.print("[yellow]No valid courses found in user preferences[/yellow]")
    else:
        console.print("[yellow]No users with preferences found. Using default monitoring.[/yellow]")
        console.print("[blue]Users can set preferences at: http://localhost:8501[/blue]")

if __name__ == "__main__":
    enhanced_main()
'''
    
    # Save the enhanced script
    enhanced_script_path = Path(__file__).parent.parent / "golf_monitor_enhanced.py"
    with open(enhanced_script_path, 'w') as f:
        f.write(script_content)
    
    console.print(f"[green]Created enhanced monitor script: {enhanced_script_path}[/green]")

if __name__ == "__main__":
    # Create the enhanced monitor script
    create_enhanced_monitor_script()
    
    # Test the preferences manager
    prefs_manager = UserPreferencesManager()
    active_users = prefs_manager.get_active_users()
    
    if active_users:
        console.print(f"[green]Found {len(active_users)} active users with preferences[/green]")
        for user in active_users:
            console.print(f"  - {user['name']} ({user['email']}): {len(user.get('selected_courses', []))} courses")
    else:
        console.print("[yellow]No active users found. Configure preferences via the Streamlit app.[/yellow]")
