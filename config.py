#!/usr/bin/env python3
"""Enhanced configuration management for Golf Availability Bot."""

import os
import datetime
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
from location_finder import GolfClubLocationFinder

# Load environment variables
load_dotenv()

class GolfBotConfig:
    """Comprehensive configuration management for the Golf Bot."""
    
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """Load all configuration from environment variables."""
        
        # Authentication
        self.golfbox_user = os.getenv("GOLFBOX_USER", "").strip()
        self.golfbox_pass = os.getenv("GOLFBOX_PASS", "").strip()
        
        # Golf clubs
        # Location-based selection controls
        self.select_by_location = os.getenv("SELECT_BY_LOCATION", "false").lower() in ("1", "true", "yes")
        self.user_location = os.getenv("USER_LOCATION", "").strip()
        try:
            self.max_drive_minutes = int(os.getenv("MAX_DRIVE_MINUTES", "60"))
        except ValueError:
            self.max_drive_minutes = 60

        self.selected_clubs = self._parse_clubs()
        
        # Date selection
        self.dates = self._parse_dates()
        
        # Time preferences
        self.time_start = self._parse_time(os.getenv("TIME_START", "07:00"))
        self.time_end = self._parse_time(os.getenv("TIME_END", "18:00"))
        self.preferred_times = self._parse_preferred_times()
        
        # Player requirements
        self.player_count = int(os.getenv("PLAYER_COUNT", "4"))
        self.min_available_slots = int(os.getenv("MIN_AVAILABLE_SLOTS", "1"))
        
        # Monitoring behavior
        self.check_interval = int(os.getenv("CHECK_INTERVAL", "300"))
        self.jitter_seconds = int(os.getenv("JITTER_SECONDS", "30"))
        self.headless = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")
        self.persist_notifications = os.getenv("PERSIST_NOTIFICATIONS", "false").lower() in ("1", "true", "yes")
        self.debug = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
        
        # Email configuration
        self.email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() in ("1", "true", "yes")
        self.smtp_host = os.getenv("SMTP_HOST", "").strip()
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_ssl = os.getenv("SMTP_SSL", "false").lower() in ("1", "true", "yes")
        self.smtp_user = os.getenv("SMTP_USER", "").strip()
        self.smtp_pass = os.getenv("SMTP_PASS", "").strip()
        self.email_from = os.getenv("EMAIL_FROM", "").strip()
        self.email_to = self._parse_email_recipients()
        
        # Notifications
        self.desktop_notifications = os.getenv("DESKTOP_NOTIFICATIONS", "true").lower() in ("1", "true", "yes")
        self.email_notifications = os.getenv("EMAIL_NOTIFICATIONS", "true").lower() in ("1", "true", "yes")
        self.console_output = os.getenv("CONSOLE_OUTPUT", "true").lower() in ("1", "true", "yes")
        
        # Advanced settings
        self.course_id_overrides = self._parse_overrides("COURSE_ID_OVERRIDES")
        self.grid_url_overrides = self._parse_overrides("GRID_URL_OVERRIDES")
    
    def _parse_clubs(self) -> List[str]:
        """Parse selected golf clubs from configuration."""
        clubs_str = os.getenv("SELECTED_CLUBS", "").strip()
        # If explicitly selecting by location via env, compute clubs programmatically
        if self.select_by_location and self.user_location:
            try:
                finder = GolfClubLocationFinder()
                nearby = finder.find_clubs_within_radius(self.user_location, self.max_drive_minutes)
                # Map friendly names to facilities keys when possible
                facilities_keys = {
                    "oslo golfklubb": "oslo golfklubb",
                    "miklagard": "miklagard golfklubb",
                    "losby": "losby gods",
                    "holtsmark": "holtsmark golfklubb",
                    "drammen": "drammen golfklubb",
                    "asker": "asker golfklubb",
                    "vestfold": "vestfold golfklubb",
                    "moss": "moss golfklubb",
                }
                resolved: List[str] = []
                for club in nearby:
                    name_lower = club.name.lower()
                    # direct match
                    if name_lower in facilities_keys:
                        resolved.append(facilities_keys[name_lower])
                        continue
                    # heuristic substring match
                    for fragment, fac in facilities_keys.items():
                        if fragment in name_lower and fac not in resolved:
                            resolved.append(fac)
                            break
                if resolved:
                    return resolved
            except Exception:
                # fall back to manual or default below
                pass

        if not clubs_str:
            # Return all available clubs if none specified
            return ["oslo golfklubb", "miklagard golfklubb", "bogstad golfklubb", 
                   "losby gods", "holtsmark golfklubb", "bjaavann golfklubb",
                   "drammen golfklubb", "asker golfklubb", "vestfold golfklubb", "moss golfklubb"]
        
        # Map short names to full names
        club_mapping = {
            "oslo": "oslo golfklubb",
            "miklagard": "miklagard golfklubb",
            "bogstad": "bogstad golfklubb",
            "losby": "losby gods",
            "holtsmark": "holtsmark golfklubb",
            "bjaavann": "bjaavann golfklubb",
            "drammen": "drammen golfklubb",
            "asker": "asker golfklubb",
            "vestfold": "vestfold golfklubb",
            "moss": "moss golfklubb"
        }
        
        selected = []
        for club in clubs_str.split(","):
            club = club.strip().lower()
            if club in club_mapping:
                selected.append(club_mapping[club])
            elif club:  # Allow full names too
                selected.append(club)
        
        return selected or list(club_mapping.values())
    
    def _parse_dates(self) -> List[datetime.date]:
        """Parse date selection from configuration."""
        today = datetime.date.today()
        
        # Method 1: Days ahead
        if os.getenv("START_FROM_TODAY", "false").lower() in ("1", "true", "yes"):
            days_ahead = int(os.getenv("DAYS_AHEAD", "7"))
            return [today + datetime.timedelta(days=i) for i in range(days_ahead + 1)]
        
        # Method 2: Date range
        date_start = os.getenv("DATE_START")
        date_end = os.getenv("DATE_END")
        if date_start and date_end:
            start = datetime.datetime.strptime(date_start, "%Y-%m-%d").date()
            end = datetime.datetime.strptime(date_end, "%Y-%m-%d").date()
            dates = []
            current = start
            while current <= end:
                dates.append(current)
                current += datetime.timedelta(days=1)
            return dates
        
        # Method 3: Specific dates
        specific_dates = os.getenv("SPECIFIC_DATES")
        if specific_dates:
            dates = []
            for date_str in specific_dates.split(","):
                date_str = date_str.strip()
                if date_str:
                    dates.append(datetime.datetime.strptime(date_str, "%Y-%m-%d").date())
            return sorted(dates)
        
        # Method 4: Weekend mode
        if os.getenv("WEEKEND_MODE", "false").lower() in ("1", "true", "yes"):
            weekends_count = int(os.getenv("WEEKENDS_COUNT", "2"))
            dates = []
            current_date = today
            weekends_found = 0
            
            while weekends_found < weekends_count:
                # Find next Saturday (weekday 5)
                days_until_saturday = (5 - current_date.weekday()) % 7
                if days_until_saturday == 0 and current_date == today:
                    days_until_saturday = 7  # Next Saturday if today is Saturday
                
                saturday = current_date + datetime.timedelta(days=days_until_saturday)
                sunday = saturday + datetime.timedelta(days=1)
                
                dates.extend([saturday, sunday])
                weekends_found += 1
                current_date = sunday + datetime.timedelta(days=1)
            
            return dates
        
        # Default: next 7 days
        return [today + datetime.timedelta(days=i) for i in range(8)]
    
    def _parse_time(self, time_str: str) -> datetime.time:
        """Parse time string to datetime.time."""
        try:
            return datetime.datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            return datetime.time(7, 0)  # Default to 07:00
    
    def _parse_preferred_times(self) -> Optional[List[datetime.time]]:
        """Parse preferred times list."""
        preferred_str = os.getenv("PREFERRED_TIMES", "").strip()
        if not preferred_str:
            return None
        
        times = []
        for time_str in preferred_str.split(","):
            time_str = time_str.strip()
            if time_str:
                times.append(self._parse_time(time_str))
        
        return times if times else None
    
    def _parse_email_recipients(self) -> List[str]:
        """Parse email recipients."""
        email_to = os.getenv("EMAIL_TO", "").strip()
        if not email_to:
            return []
        
        return [email.strip() for email in email_to.split(",") if email.strip()]
    
    def _parse_overrides(self, env_var: str) -> Dict[str, str]:
        """Parse override configurations."""
        overrides_str = os.getenv(env_var, "").strip()
        if not overrides_str:
            return {}
        
        overrides = {}
        for override in overrides_str.split(","):
            if "=" in override:
                key, value = override.split("=", 1)
                overrides[key.strip()] = value.strip()
        
        return overrides
    
    def get_time_filter(self) -> Tuple[datetime.time, datetime.time]:
        """Get time filter range."""
        return (self.time_start, self.time_end)
    
    def should_include_time(self, time_str: str) -> bool:
        """Check if a time should be included based on preferences."""
        try:
            time_obj = datetime.datetime.strptime(time_str, "%H:%M").time()
            
            # Check if within time window
            if not (self.time_start <= time_obj <= self.time_end):
                return False
            
            # Check preferred times if specified
            if self.preferred_times:
                return time_obj in self.preferred_times
            
            return True
        except ValueError:
            return True  # Include unparseable times to be safe
    
    def get_summary(self) -> str:
        """Get a human-readable configuration summary."""
        summary = []
        summary.append(f"🏌️ Golf Clubs: {', '.join(self.selected_clubs)}")
        summary.append(f"📅 Dates: {len(self.dates)} days ({self.dates[0]} to {self.dates[-1]})")
        summary.append(f"⏰ Time Window: {self.time_start.strftime('%H:%M')} - {self.time_end.strftime('%H:%M')}")
        if self.preferred_times:
            preferred_str = ', '.join([t.strftime('%H:%M') for t in self.preferred_times])
            summary.append(f"🎯 Preferred Times: {preferred_str}")
        summary.append(f"👥 Players: {self.player_count} (min {self.min_available_slots} slots)")
        summary.append(f"🔄 Check Interval: {self.check_interval}s")
        if self.email_enabled and self.email_to:
            summary.append(f"📧 Email: {len(self.email_to)} recipients")
        
        return "\n".join(summary)


def load_golf_config() -> GolfBotConfig:
    """Load the golf bot configuration."""
    return GolfBotConfig()


if __name__ == "__main__":
    # Test configuration loading
    config = load_golf_config()
    print("Golf Bot Configuration:")
    print("=" * 50)
    print(config.get_summary())
