#!/usr/bin/env python3
"""
Golf Availability Monitor with User Preferences Integration

This script reads user preferences from the Streamlit app and runs 
personalized monitoring for each user.
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import os
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from golf_utils import send_email_notification
from golf_club_urls import golf_url_manager
from golf_availability_monitor import monitor_courses
from rich.console import Console

console = Console()

class UserPreferencesMonitor:
    """Monitor golf availability based on individual user preferences."""
    
    def __init__(self, preferences_file: Path = None):
        self.preferences_file = preferences_file or Path(__file__).parent.parent / "user_preferences.json"
        self.console = Console()
    
    def load_user_preferences(self) -> Dict:
        """Load all user preferences from file."""
        if not self.preferences_file.exists():
            self.console.print("[yellow]No user preferences file found. Users can configure preferences via the Streamlit app.[/yellow]")
            return {}
        
        try:
            with open(self.preferences_file, 'r') as f:
                preferences = json.load(f)
            self.console.print(f"[green]Loaded preferences for {len(preferences)} users[/green]")
            return preferences
        except Exception as e:
            self.console.print(f"[red]Error loading preferences: {e}[/red]")
            return {}
    
    def get_active_users(self, preferences: Dict) -> List[Dict]:
        """Get list of users with valid preferences."""
        active_users = []
        
        for email, user_prefs in preferences.items():
            # Validate required fields
            if all([
                user_prefs.get('name'),
                user_prefs.get('email'),
                user_prefs.get('selected_courses'),
                user_prefs.get('time_slots')
            ]):
                active_users.append(user_prefs)
            else:
                self.console.print(f"[yellow]Skipping incomplete preferences for {email}[/yellow]")
        
        return active_users
    
    def filter_courses_for_user(self, user_prefs: Dict) -> List[str]:
        """Get list of course keys that user wants to monitor."""
        selected_courses = user_prefs.get('selected_courses', [])
        
        # Validate that courses exist in our system
        valid_courses = []
        for course_key in selected_courses:
            if course_key in golf_url_manager.clubs:
                valid_courses.append(course_key)
            else:
                self.console.print(f"[yellow]Unknown course key: {course_key}[/yellow]")
        
        return valid_courses
    
    def should_notify_user(self, user_prefs: Dict, last_notification_time: datetime = None) -> bool:
        """Check if user should be notified based on frequency preferences."""
        frequency = user_prefs.get('notification_frequency', 'immediate')
        
        if frequency == 'immediate':
            return True
        
        if last_notification_time is None:
            return True
        
        now = datetime.now()
        time_diff = now - last_notification_time
        
        if frequency == 'hourly' and time_diff.total_seconds() >= 3600:
            return True
        elif frequency == 'daily' and time_diff.total_seconds() >= 86400:
            return True
        
        return False
    
    def generate_time_window_filter(self, user_prefs: Dict) -> str:
        """Generate time window string for filtering."""
        time_slots = user_prefs.get('time_slots', [])
        
        if not time_slots:
            return "00:00-23:59"
        
        # Find min and max times
        min_time = min(time_slots)
        max_time = max(time_slots)
        
        return f"{min_time}-{max_time}"
    
    def send_personalized_notification(self, user_prefs: Dict, new_availability: List, all_availability: Dict):
        """Send notification to specific user with their preferences."""
        # Temporarily override email settings for this user
        original_email_to = os.environ.get('EMAIL_TO', '')
        os.environ['EMAIL_TO'] = user_prefs['email']
        
        try:
            # Filter availability based on user's time preferences
            filtered_availability = self.filter_availability_by_time(
                new_availability, 
                user_prefs.get('time_slots', [])
            )
            
            # Filter by minimum players required
            min_players = user_prefs.get('min_players', 1)
            player_filtered_availability = self.filter_availability_by_players(
                filtered_availability, 
                min_players
            )
            
            if player_filtered_availability:
                # Create personalized configuration info
                config_info = {
                    'user_name': user_prefs['name'],
                    'courses': len(user_prefs.get('selected_courses', [])),
                    'time_window': self.generate_time_window_filter(user_prefs),
                    'min_players': min_players,
                    'days': user_prefs.get('days_ahead', 4),
                    'notification_frequency': user_prefs.get('notification_frequency', 'immediate')
                }
                
                # Send personalized email
                send_email_notification(
                    subject=f"⛳ Golf Availability Alert for {user_prefs['name']}",
                    new_availability=player_filtered_availability,
                    all_availability=all_availability,
                    time_window=config_info['time_window'],
                    config_info=config_info,
                    club_order=user_prefs.get('selected_courses', [])
                )
                
                self.console.print(f"[green]Sent personalized notification to {user_prefs['name']} ({user_prefs['email']})[/green]")
                return True
            else:
                self.console.print(f"[blue]No relevant availability for {user_prefs['name']} based on their preferences[/blue]")
                return False
        
        finally:
            # Restore original email setting
            if original_email_to:
                os.environ['EMAIL_TO'] = original_email_to
            elif 'EMAIL_TO' in os.environ:
                del os.environ['EMAIL_TO']
    
    def filter_availability_by_time(self, availability: List, preferred_times: List) -> List:
        """Filter availability list based on user's preferred time slots."""
        if not preferred_times:
            return availability
        
        filtered = []
        for item in availability:
            # Extract time from availability string (format: "Course on YYYY-MM-DD at HH:MM: X spots")
            import re
            time_match = re.search(r'at (\d{2}:\d{2}):', item)
            if time_match:
                item_time = time_match.group(1)
                if item_time in preferred_times:
                    filtered.append(item)
        
        return filtered
    
    def filter_availability_by_players(self, availability: List, min_players: int) -> List:
        """Filter availability based on minimum players required."""
        filtered = []
        for item in availability:
            # Extract number of spots from availability string
            import re
            spots_match = re.search(r'(\d+) spot', item)
            if spots_match:
                available_spots = int(spots_match.group(1))
                if available_spots >= min_players:
                    filtered.append(item)
        
        return filtered
    
    async def run_personalized_monitoring(self):
        """Run monitoring with personalized settings for each user."""
        self.console.print("[bold green]🏌️ Starting Golf Availability Monitor with User Preferences[/bold green]")
        
        # Load user preferences
        all_preferences = self.load_user_preferences()
        active_users = self.get_active_users(all_preferences)
        
        if not active_users:
            self.console.print("[yellow]No active users found. Please configure preferences via the Streamlit app.[/yellow]")
            return
        
        self.console.print(f"[green]Monitoring for {len(active_users)} active users[/green]")
        
        # For each user, get their preferred courses and run monitoring
        for user_prefs in active_users:
            user_name = user_prefs['name']
            user_courses = self.filter_courses_for_user(user_prefs)
            
            if not user_courses:
                self.console.print(f"[yellow]No valid courses for {user_name}[/yellow]")
                continue
            
            self.console.print(f"[cyan]Monitoring {len(user_courses)} courses for {user_name}[/cyan]")
            
            # Generate URLs for user's selected courses
            from datetime import date
            target_dates = []
            days_ahead = user_prefs.get('days_ahead', 4)
            
            for i in range(days_ahead):
                target_dates.append(date.today() + timedelta(days=i))
            
            # Monitor each date for this user's courses
            for target_date in target_dates:
                urls = golf_url_manager.generate_comma_separated_urls(user_courses, target_date)
                labels = golf_url_manager.generate_labels_string(user_courses)
                
                self.console.print(f"[blue]Checking {target_date} for {user_name}[/blue]")
                
                # Note: You'll need to adapt the monitor_courses function to work with individual user preferences
                # For now, this is a framework - you'll need to integrate with your existing monitoring logic

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Golf Availability Monitor with User Preferences")
    parser.add_argument("--preferences-file", type=Path, help="Path to user preferences file")
    parser.add_argument("--run-once", action="store_true", help="Run once instead of continuous monitoring")
    
    args = parser.parse_args()
    
    monitor = UserPreferencesMonitor(args.preferences_file)
    
    if args.run_once:
        asyncio.run(monitor.run_personalized_monitoring())
    else:
        # Continuous monitoring loop
        async def continuous_monitoring():
            while True:
                try:
                    await monitor.run_personalized_monitoring()
                    console.print("[blue]Waiting 5 minutes before next check...[/blue]")
                    await asyncio.sleep(300)  # Wait 5 minutes
                except KeyboardInterrupt:
                    console.print("[yellow]Monitoring stopped by user[/yellow]")
                    break
                except Exception as e:
                    console.print(f"[red]Error in monitoring loop: {e}[/red]")
                    await asyncio.sleep(60)  # Wait 1 minute on error
        
        asyncio.run(continuous_monitoring())

if __name__ == "__main__":
    main()
