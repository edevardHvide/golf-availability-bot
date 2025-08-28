#!/usr/bin/env python3
"""Golf Availability Monitor - Main monitoring script for multiple courses.

Environment Variables:
    SELECTED_CLUBS: Optional comma-separated list of club keys to monitor
                   (if not set, uses default configuration)
    API_URL: URL for the Streamlit API server (default: http://localhost:8000)
    
A browser window will open for manual login to golfbox.golf.
"""

import asyncio
import argparse
import datetime
import os
import re
import json
import requests
import sys
import time
from typing import Dict, List
from pathlib import Path
from dotenv import load_dotenv

from playwright.async_api import async_playwright, BrowserContext, Page
from rich.console import Console
from rich.table import Table

from golfbot.grid_parser import parse_grid_html
from golf_utils import send_email_notification, rewrite_url_for_day
from golf_club_urls import golf_url_manager

# Load environment (override=True to ensure .env values are used)
load_dotenv(override=True)
console = Console()

# Import weekday/weekend utility functions
sys.path.append(str(Path(__file__).parent / "streamlit_app"))
try:
    from time_utils import get_time_slots_for_date
    WEEKDAY_WEEKEND_SUPPORT = True
except ImportError:
    WEEKDAY_WEEKEND_SUPPORT = False
    console.print("⚠️ Weekday/weekend support not available - using legacy time slot format", style="yellow")

# No longer using saved sessions

async def check_login_status(page: Page) -> bool:
    """Check if user is logged in to golfbox.golf."""
    try:
        # Wait for page to load
        await page.wait_for_load_state("domcontentloaded", timeout=10000)
        await page.wait_for_timeout(2000)  # Additional wait for JS to execute
        
        # Check for login indicators - adjust these selectors based on the actual site
        # Common indicators: profile menu, logout button, user name, etc.
        login_indicators = [
            "text=Logout",
            "text=Log out", 
            "text=My Profile",
            "text=Settings",
            "[data-testid='user-menu']",
            ".user-menu",
            ".profile-menu"
        ]
        
        for selector in login_indicators:
            try:
                element = await page.wait_for_selector(selector, timeout=3000)
                if element:
                    console.print("User is logged in", style="green")
                    return True
            except Exception:
                continue
        
        # If no login indicators found, check if login form is present
        login_form_selectors = [
            "input[type='email']",
            "input[type='password']", 
            "text=Sign In",
            "text=Login",
            "text=Log In"
        ]
        
        for selector in login_form_selectors:
            try:
                element = await page.wait_for_selector(selector, timeout=3000)
                if element:
                    console.print("Login form detected - user needs to log in", style="yellow")
                    return False
            except Exception:
                continue
        
        # Default assumption if we can't determine status
        console.print("Login status unclear - assuming logged in", style="yellow")
        return True
        
    except Exception as e:
        console.print(f"Error checking login status: {e}", style="yellow")
        return False

async def automatic_login(playwright_instance, context: BrowserContext) -> bool:
    """Open browser for manual login."""
    console.print("Opening browser for manual login...", style="yellow")
    
    try:
        # Launch a visible browser for manual login
        manual_browser = await playwright_instance.chromium.launch(headless=False)
        manual_context = await manual_browser.new_context()
        manual_page = await manual_context.new_page()
        
        await manual_page.goto("https://golfbox.golf/#/", wait_until="domcontentloaded")
        
        console.print("Please log in manually in the browser window.", style="cyan")
        console.print("Waiting for login completion...", style="yellow")
        
        # Wait for login to be completed (check every 2 seconds)
        for attempt in range(150):  # Wait up to 5 minutes
            await manual_page.wait_for_timeout(2000)
            if await check_login_status(manual_page):
                console.print("Login successful!", style="green")
                # Copy cookies to main context
                cookies = await manual_context.cookies()
                await context.add_cookies(cookies)
                await manual_browser.close()
                return True
        
        console.print("Login timeout", style="red")
        await manual_browser.close()
        return False
            
    except Exception as e:
        console.print(f"Login error: {e}", style="red")
        return False

def parse_time_window(time_str: str) -> tuple[int, int]:
    """Parse time window like '08:00-17:00' into (start_minutes, end_minutes)."""
    try:
        start_str, end_str = time_str.split('-')
        start_h, start_m = map(int, start_str.split(':'))
        end_h, end_m = map(int, end_str.split(':'))
        return (start_h * 60 + start_m, end_h * 60 + end_m)
    except Exception:
        raise ValueError(f"Invalid time window format: {time_str}. Use HH:MM-HH:MM")

def time_in_window(time_str: str, window: tuple[int, int]) -> bool:
    """Check if HH:MM time is within the window."""
    try:
        h, m = map(int, time_str.split(':'))
        minutes = h * 60 + m
        return window[0] <= minutes <= window[1]
    except Exception:
        return False

def time_has_passed(time_str: str, target_date: datetime.date) -> bool:
    """Check if a time has already passed for the given date."""
    try:
        # Only filter for today - future dates are always valid
        if target_date != datetime.date.today():
            return False
            
        h, m = map(int, time_str.split(':'))
        time_minutes = h * 60 + m
        
        # Get current time in minutes
        now = datetime.datetime.now()
        current_minutes = now.hour * 60 + now.minute
        
        # Add a small buffer (e.g., 15 minutes) to account for booking time
        buffer_minutes = 15
        return time_minutes <= (current_minutes + buffer_minutes)
    except Exception:
        return False

def parse_capacity_from_label(label: str) -> int:
    """Extract capacity number from labels like '2 spots available'."""
    m = re.match(r"\s*(\d+)\s+spot", label.strip(), re.I)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return 0

async def check_course_availability(context: BrowserContext, url: str, course_name: str, target_date: datetime.date, time_window: tuple[int, int], min_players: int = 1, no_time_filter: bool = False) -> Dict[str, int]:
    """Check availability for a single course and return times within window (or all times if no_time_filter=True)."""
    page = None
    try:
        console.print(f"  → Checking {course_name} for {target_date.strftime('%Y-%m-%d')}...", style="cyan")
        console.print(f"    URL: {url}", style="dim")
        
        # Create a new page for this course to avoid navigation conflicts
        page = await context.new_page()
        
        # Add extra headers to prevent caching
        await page.set_extra_http_headers({
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        })
        
        # Navigate to the course URL
        await page.goto(url, wait_until="domcontentloaded")
        
        # Wait briefly for grid to load
        try:
            await page.wait_for_selector("div.hour, table", timeout=10000)
        except Exception:
            pass
        
        # Add a small delay to ensure page is fully loaded
        await page.wait_for_timeout(2000)
        
        # Get HTML and parse
        html = await page.content()
        times = parse_grid_html(html)
        
        console.print(f"    DEBUG: Raw times found: {len(times)} entries", style="dim")
        if times:
            console.print(f"    DEBUG: Sample times: {dict(list(times.items())[:3])}", style="dim")
        
        # Filter times and calculate capacity
        available_times = {}
        for time_str, labels in times.items():
            # If no_time_filter is True, include all times regardless of window
            time_passes_filter = no_time_filter or time_in_window(time_str, time_window)
            
            # Skip times that have already passed for today (but keep all future dates)
            if time_passes_filter and not time_has_passed(time_str, target_date):
                total_capacity = sum(parse_capacity_from_label(lbl) for lbl in labels)
                if total_capacity >= min_players:
                    available_times[time_str] = total_capacity
        
        if available_times:
            times_str = ", ".join([f"{t}({c})" for t, c in sorted(available_times.items())])
            console.print(f"    ✓ {course_name}: {times_str}", style="green")
        else:
            console.print(f"    - {course_name}: No availability", style="dim")
        
        return available_times
        
    except Exception as e:
        console.print(f"    ✗ {course_name}: Error - {e}", style="red")
        return {}
    finally:
        if page:
            await page.close()

def get_user_preferences() -> List[Dict]:
    """Fetch all user preferences from API or local file."""
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    # Always try cloud API first
    if api_url and "localhost" not in api_url:
        console.print(f"🌐 Fetching user preferences from cloud API: {api_url}", style="cyan")
        
        # Try multiple endpoints for API access
        api_endpoints = [
            f"{api_url}/api/preferences",
            f"{api_url}:8000/api/preferences"
        ]
        
        for endpoint in api_endpoints:
            try:
                console.print(f"  🔗 Trying: {endpoint}", style="dim")
                response = requests.get(endpoint, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    user_preferences = list(data.get("preferences", {}).values())
                    console.print(f"✅ Successfully loaded {len(user_preferences)} user profiles from cloud API", style="green")
                    
                    # Show user summary
                    for user in user_preferences:
                        name = user.get('name', 'Unknown')
                        email = user.get('email', 'No email')
                        courses = len(user.get('selected_courses', []))
                        console.print(f"  👤 {name} ({email}) - {courses} courses", style="dim")
                    
                    return user_preferences
                else:
                    console.print(f"  ⚠️ Endpoint returned status {response.status_code}", style="yellow")
                    
            except requests.exceptions.ConnectionError:
                console.print(f"  ❌ Connection failed to {endpoint}", style="red")
            except Exception as e:
                console.print(f"  ❌ Error: {str(e)[:50]}...", style="red")
        
        console.print("⚠️ All cloud API endpoints failed, falling back to local file", style="yellow")
    
    # Fallback to localhost API
    elif "localhost" in api_url:
        try:
            console.print("📋 Fetching user preferences from local API...", style="cyan")
            response = requests.get(f"{api_url}/api/preferences", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                user_preferences = list(data.get("preferences", {}).values())
                console.print(f"✅ Loaded {len(user_preferences)} user profiles from local API", style="green")
                return user_preferences
            else:
                console.print(f"⚠️ Local API returned status {response.status_code}", style="yellow")
                
        except requests.exceptions.ConnectionError:
            console.print("⚠️ Local API server not available", style="yellow")
        except Exception as e:
            console.print(f"⚠️ Error fetching from local API: {e}", style="yellow")
    
    # Final fallback to local file
    try:
        console.print("📄 Falling back to local preferences file...", style="yellow")
        preferences_file = Path(__file__).parent / "streamlit_app" / "user_preferences.json"
        if preferences_file.exists():
            with open(preferences_file, 'r') as f:
                all_prefs = json.load(f)
            user_preferences = list(all_prefs.values())
            console.print(f"✅ Loaded {len(user_preferences)} user profiles from local file", style="green")
            return user_preferences
        else:
            console.print("📄 No local preferences file found", style="dim")
            return []
    except Exception as e:
        console.print(f"❌ Error loading local preferences: {e}", style="red")
        return []

def filter_availability_for_user(user_prefs: Dict, all_availability: Dict, target_date: datetime.date) -> Dict[str, Dict[str, int]]:
    """Filter availability results based on user preferences with weekday/weekend support."""
    filtered = {}
    
    # Get user's preferred courses
    user_courses = user_prefs.get('selected_courses', [])
    
    # Get time slots based on weekday/weekend preferences if supported
    if WEEKDAY_WEEKEND_SUPPORT:
        try:
            user_time_slots = get_time_slots_for_date(user_prefs, target_date)
            preference_type = user_prefs.get('preference_type', 'Same for all days')
            day_type = "weekend" if target_date.weekday() >= 5 else "weekday"
            console.print(f"    Using {preference_type} preferences for {day_type} ({target_date}): {len(user_time_slots)} time slots", style="dim")
        except Exception as e:
            console.print(f"⚠️ Error getting weekday/weekend time slots, falling back to legacy format: {e}", style="yellow")
            user_time_slots = user_prefs.get('time_slots', [])
    else:
        # Fallback to legacy format
        user_time_slots = user_prefs.get('time_slots', [])
    
    min_players = user_prefs.get('min_players', 1)
    
    date_str = target_date.strftime('%Y-%m-%d')
    
    for state_key, available_times in all_availability.items():
        if not state_key.endswith(f"_{date_str}"):
            continue
            
        # Extract course name from state key (format: "Course Name_YYYY-MM-DD")
        course_label = state_key.replace(f"_{date_str}", "")
        
        # Check if this course matches any of the user's selected courses
        # Need to map from display name back to course key
        course_matches = False
        for course_key in user_courses:
            club = golf_url_manager.get_club_by_name(course_key)
            if club and club.display_name == course_label:
                course_matches = True
                break
        
        if not course_matches:
            continue
            
        # Filter times based on user preferences
        filtered_times = {}
        for time_str, capacity in available_times.items():
            # Check if time matches user's preferred time slots
            if user_time_slots and time_str not in user_time_slots:
                continue
                
            # Check if capacity meets minimum player requirement
            if capacity >= min_players:
                filtered_times[time_str] = capacity
        
        if filtered_times:
            filtered[state_key] = filtered_times
    
    return filtered

def send_personalized_notifications(user_preferences: List[Dict], all_availability: Dict, dates_to_check: List[datetime.date], previous_state: Dict):
    """Send personalized email notifications to each user based on their preferences."""
    
    for user_prefs in user_preferences:
        user_name = user_prefs.get('name', 'Golf Enthusiast')
        user_email = user_prefs.get('email')
        
        if not user_email:
            console.print(f"⚠️ Skipping user {user_name} - no email address", style="yellow")
            continue
        
        # Collect new availability for this user across all dates
        user_new_availability = []
        user_all_availability = {}
        
        for target_date in dates_to_check:
            # Filter availability for this user on this date
            user_filtered = filter_availability_for_user(user_prefs, all_availability, target_date)
            user_all_availability.update(user_filtered)
            
            # Check for new availability (compared to previous state)
            date_str = target_date.strftime('%Y-%m-%d')
            for state_key, available_times in user_filtered.items():
                previous_times = previous_state.get(state_key, {})
                course_label = state_key.replace(f"_{date_str}", "")
                
                for time_str, capacity in available_times.items():
                    if time_str not in previous_times or capacity > previous_times[time_str]:
                        day_name = "Today" if target_date == datetime.date.today() else target_date.strftime('%A')
                        user_new_availability.append(f"{course_label} on {day_name} ({date_str}) at {time_str}: {capacity} spots")
        
        # Send notification if there's new availability for this user
        if user_new_availability:
            console.print(f"📧 Sending personalized notification to {user_name} ({user_email})", style="green")
            console.print(f"   Found {len(user_new_availability)} new slots matching their preferences", style="dim")
            
            # Prepare user-specific configuration info
            config_info = {
                'user_name': user_name,
                'user_email': user_email,
                'courses': len(user_prefs.get('selected_courses', [])),
                'time_slots': len(user_prefs.get('time_slots', [])),
                'min_players': user_prefs.get('min_players', 1),
                'days_ahead': user_prefs.get('days_ahead', 4),
                'notification_frequency': user_prefs.get('notification_frequency', 'immediate')
            }
            
            subject = f"⛳ Personal Golf Alert for {user_name} - {dates_to_check[0].strftime('%Y-%m-%d')}"
            
            # Send personalized email
            send_email_notification(
                subject=subject,
                new_availability=user_new_availability,
                all_availability=user_all_availability,
                time_window="Personalized",
                config_info=config_info,
                club_order=None,  # Will be determined from user's preferences
                user_preferences=user_prefs
            )
        else:
            console.print(f"📭 No new availability for {user_name} based on their preferences", style="dim")

def is_scheduled_time() -> bool:
    """Check if current time is one of the scheduled notification times (9am, 12pm, 9pm)"""
    now = datetime.datetime.now()
    scheduled_hours = [9, 12, 21]  # 9am, 12pm, 9pm
    return now.hour in scheduled_hours and now.minute < 5  # 5-minute window

def wait_for_next_scheduled_time():
    """Wait until the next scheduled notification time"""
    now = datetime.datetime.now()
    scheduled_hours = [9, 12, 21]  # 9am, 12pm, 9pm
    
    # Find next scheduled time
    next_hour = None
    for hour in scheduled_hours:
        if now.hour < hour:
            next_hour = hour
            break
    
    if next_hour is None:
        # Next scheduled time is tomorrow at 9am
        next_time = now.replace(hour=9, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    else:
        next_time = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
    
    wait_seconds = (next_time - now).total_seconds()
    console.print(f"⏰ Next scheduled check: {next_time.strftime('%Y-%m-%d %H:%M:%S')}", style="cyan")
    console.print(f"⏰ Waiting {wait_seconds/3600:.1f} hours...", style="dim")
    
    return wait_seconds

async def run_scheduled_monitoring(args, time_window, window_str):
    """Run monitoring in scheduled mode - only at 9am, 12pm, and 9pm"""
    
    # Load user preferences
    user_preferences = get_user_preferences() if not args.local else []
    
    if user_preferences:
        console.print(f"👥 Scheduled monitoring for {len(user_preferences)} users", style="blue")
    else:
        console.print("👥 No user preferences found - using legacy mode", style="yellow")
    
    # Track previous state for detecting new availability
    previous_state: Dict[str, Dict[str, int]] = {}
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        
        try:
            # Attempt automatic login
            console.print("🔐 Authenticating with golfbox.golf...", style="cyan")
            login_success = await automatic_login(pw, context)
            if not login_success:
                console.print("Authentication failed. Exiting.", style="red")
                return
            
            console.print("Authentication successful! Starting scheduled monitoring...", style="green")
            
            while True:
                # Check if it's a scheduled time
                if is_scheduled_time():
                    console.print(f"\n⏰ SCHEDULED CHECK - {datetime.datetime.now().strftime('%H:%M:%S')}", style="bold green")
                    
                    # Perform the availability check
                    await perform_availability_check(args, time_window, window_str, user_preferences, previous_state, context)
                    
                    # Wait a bit to avoid duplicate runs in the same 5-minute window
                    await asyncio.sleep(300)  # 5 minutes
                else:
                    # Wait until next scheduled time
                    wait_seconds = wait_for_next_scheduled_time()
                    await asyncio.sleep(min(wait_seconds, 300))  # Check every 5 minutes or until next scheduled time
                    
        except KeyboardInterrupt:
            console.print("\n\n👋 Scheduled monitoring stopped. Happy golfing!", style="bold blue")
        finally:
            await browser.close()

async def run_immediate_check(args, time_window, window_str):
    """Run a single immediate check and exit"""
    
    # Load user preferences
    user_preferences = get_user_preferences() if not args.local else []
    
    console.print(f"⚡ Running immediate check for {len(user_preferences)} users", style="cyan")
    
    # Track previous state (empty for immediate check)
    previous_state: Dict[str, Dict[str, int]] = {}
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        
        try:
            # Attempt automatic login
            console.print("🔐 Authenticating with golfbox.golf...", style="cyan")
            login_success = await automatic_login(pw, context)
            if not login_success:
                console.print("Authentication failed. Exiting.", style="red")
                return {"success": False, "error": "Authentication failed"}
            
            console.print("Authentication successful! Running immediate check...", style="green")
            
            # Perform the availability check
            results = await perform_availability_check(args, time_window, window_str, user_preferences, previous_state, context)
            
            console.print("✅ Immediate check completed!", style="green")
            return results
            
        except Exception as e:
            console.print(f"❌ Immediate check failed: {e}", style="red")
            return {"success": False, "error": str(e)}
        finally:
            await browser.close()

async def save_results_to_database(results: Dict, check_type: str = "scheduled"):
    """Save availability results to database for offline access and notification system"""
    # Check if database is enabled
    database_enabled = os.getenv("DATABASE_ENABLED", "true").lower() == "true"
    if not database_enabled:
        console.print("🏠 Database disabled - skipping database save", style="yellow")
        return
    
    # First, try to ingest the scraped data for the notification system
    try:
        from data_ingestion_service import integrate_with_golf_monitor
        ingestion_service = integrate_with_golf_monitor()
        
        if ingestion_service:
            # Add check_type to results for metadata
            results_with_type = results.copy()
            results_with_type['check_type'] = check_type
            
            success = ingestion_service.ingest_from_monitoring_results(results_with_type)
            if success:
                console.print("✅ Scraped data ingested for notification system", style="green")
            else:
                console.print("⚠️ Failed to ingest scraped data for notifications", style="yellow")
        else:
            console.print("⚠️ Data ingestion service not available", style="yellow")
    except Exception as e:
        console.print(f"⚠️ Data ingestion failed: {e}", style="yellow")
    
    try:
        # Try to import and use PostgreSQL manager with fallback
        sys.path.append(str(Path(__file__).parent / "streamlit_app"))
        
        # Try PostgreSQL first
        try:
            from postgresql_manager import get_db_manager
            db_manager = get_db_manager()
            
            # Extract data for database
            availability_data = results.get("availability", {})
            new_availability = results.get("new_availability", [])
            
            # Calculate statistics
            total_slots = 0
            courses_checked = set()
            
            for state_key, times in availability_data.items():
                if '_' in state_key:
                    course_name = state_key.split('_')[0]
                    courses_checked.add(course_name)
                    total_slots += len(times) if times else 0
            
            # Determine date range from state keys
            dates_found = set()
            for key in availability_data.keys():
                if '_' in key:
                    date_part = key.split('_')[-1]
                    if len(date_part) == 10:  # YYYY-MM-DD format
                        dates_found.add(date_part)
            
            if not dates_found:
                # Fallback to today and next few days
                from datetime import date, timedelta
                today = date.today()
                dates_found = {(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(4)}
            
            date_range_start = min(dates_found) if dates_found else date.today().strftime('%Y-%m-%d')
            date_range_end = max(dates_found) if dates_found else date.today().strftime('%Y-%m-%d')
            
            # Prepare cache data
            cache_data = {
                'check_type': check_type,
                'user_email': None,  # System-wide cache for scheduled checks
                'availability_data': availability_data,
                'courses_checked': list(courses_checked),
                'date_range_start': date_range_start,
                'date_range_end': date_range_end,
                'total_courses': len(courses_checked),
                'total_availability_slots': total_slots,
                'new_availability_count': len(new_availability),
                'check_duration_seconds': results.get("duration_seconds"),
                'success': results.get("success", True),
                'error_message': results.get("error"),
                'metadata': {
                    'new_availability': new_availability,
                    'check_timestamp': results.get("timestamp"),
                    'total_dates': results.get("total_dates", len(dates_found))
                }
            }
            
            # Save to database
            success = db_manager.save_cached_availability(cache_data)
            if success:
                console.print(f"✅ Results saved to PostgreSQL database for offline access", style="green")
                return
            else:
                console.print(f"⚠️ Failed to save results to PostgreSQL database", style="yellow")
                
        except Exception as e:
            console.print(f"⚠️ PostgreSQL not available: {e}", style="yellow")
            console.print("🔄 Falling back to JSON storage...", style="blue")
        
        # Fallback to JSON storage
        try:
            from robust_json_manager import preferences_manager
            if hasattr(preferences_manager, 'save_cached_availability'):
                # Use robust JSON manager if available
                success = preferences_manager.save_cached_availability(results)
                if success:
                    console.print(f"✅ Results saved to JSON storage for offline access", style="green")
                else:
                    console.print(f"⚠️ Failed to save results to JSON storage", style="yellow")
            else:
                # Basic JSON fallback
                cache_file = Path(__file__).parent / "availability_cache.json"
                cache_data = {
                    'timestamp': datetime.datetime.now().isoformat(),
                    'check_type': check_type,
                    'results': results
                }
                
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2, default=str)
                console.print(f"✅ Results saved to basic JSON cache: {cache_file}", style="green")
                
        except Exception as json_error:
            console.print(f"⚠️ JSON storage also failed: {json_error}", style="yellow")
            console.print("📝 Results will not be cached for offline access", style="dim")
            
    except Exception as e:
        console.print(f"⚠️ Could not save to any storage system: {e}", style="dim")

async def perform_availability_check(args, time_window, window_str, user_preferences, previous_state, context):
    """Perform the actual availability check - extracted for reuse"""
    
    start_time = datetime.datetime.now()
    
    # Determine which clubs to monitor
    # Always monitor ALL clubs when not in local mode, then filter notifications by user preferences
    selected_clubs_env = os.getenv("SELECTED_CLUBS", "").strip()
    if selected_clubs_env:
        # Environment variable override (for testing specific clubs)
        club_keys = [key.strip() for key in re.split(r"[,;\n\r\t]+", selected_clubs_env) if key.strip()]
        console.print(f"📋 Using environment SELECTED_CLUBS override: {len(club_keys)} courses", style="yellow")
    else:
        # Monitor ALL available clubs - user preferences will filter notifications
        club_keys = golf_url_manager.get_default_club_configuration()
        console.print(f"📋 Monitoring ALL available courses: {len(club_keys)} courses", style="cyan")
        
        if user_preferences:
            # Show what courses users are interested in (for info only)
            all_user_courses = set()
            for user in user_preferences:
                all_user_courses.update(user.get('selected_courses', []))
            console.print(f"💡 Users are interested in {len(all_user_courses)} specific courses (notifications will be filtered)", style="dim")
    
    # Get URLs and labels from golf_club_urls.py
    today = datetime.date.today()
    urls = [golf_url_manager.get_club_by_name(key).get_url_for_date(today) for key in club_keys if golf_url_manager.get_club_by_name(key)]
    labels = [golf_url_manager.get_club_by_name(key).display_name for key in club_keys if golf_url_manager.get_club_by_name(key)]
    
    # Check current day + next (days-1) days
    dates_to_check = [today + datetime.timedelta(days=i) for i in range(args.days)]
    
    console.print(f"Checking availability for {len(dates_to_check)} days: {dates_to_check[0]} to {dates_to_check[-1]}")
    
    current_state = {}
    new_availability = []
    
    # Check each date
    for target_date in dates_to_check:
        date_str = target_date.strftime('%Y-%m-%d')
        day_name = "Today" if target_date == today else target_date.strftime('%A')
        console.print(f"\n📅 {day_name} ({date_str})")
        
        # Check each course for this date
        for i, (base_url, label) in enumerate(zip(urls, labels)):
            # Use the existing URL rewriting logic that handles SelectedDate properly
            url = rewrite_url_for_day(base_url, target_date)
            console.print(f"  DEBUG: Course {i+1} - {label}, Date: {date_str}", style="dim")
            
            # When no user preferences exist, scrape all times (no filtering)
            no_time_filter = len(user_preferences) == 0
            if no_time_filter:
                console.print(f"    📍 Scraping ALL times (no time window filter)", style="yellow")
            available_times = await check_course_availability(context, url, label, target_date, time_window, args.players, no_time_filter)
            
            # Store state with date key
            state_key = f"{label}_{date_str}"
            current_state[state_key] = available_times
            
            # Check for new availability
            previous_times = previous_state.get(state_key, {})
            for time_str, capacity in available_times.items():
                if time_str not in previous_times or capacity > previous_times[time_str]:
                    new_availability.append(f"{label} on {date_str} at {time_str}: {capacity} spots")
    
    # Send personalized notifications to users or fallback to generic email
    if user_preferences:
        # Send personalized notifications to each user
        console.print("\n📧 Sending personalized notifications...", style="bold cyan")
        send_personalized_notifications(user_preferences, current_state, dates_to_check, previous_state)
    else:
        # Fallback to original generic email notification
        if new_availability:
            console.print("\n🚨 New availability detected!", style="bold green")
            for item in new_availability:
                console.print(f"  • {item}", style="green")
            
            # Send generic email notification
            alert_date = dates_to_check[0].strftime('%Y-%m-%d')
            subject = f"⛳ Golf Availability Alert - {alert_date}"
            
            # Prepare configuration info for email
            config_info = {
                'courses': len(urls),
                'time_window': window_str,
                'interval': args.interval,
                'min_players': args.players,
                'days': args.days
            }
            
            send_email_notification(
                subject=subject, 
                new_availability=new_availability,
                all_availability=current_state,
                time_window=window_str,
                config_info=config_info,
                club_order=labels
            )
            console.print("Generic email notification sent!", style="green")
    
    # Calculate duration
    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Return results for API use
    results = {
        "success": True,
        "timestamp": end_time.isoformat(),
        "availability": current_state,
        "new_availability": new_availability,
        "total_courses": len(labels),
        "total_dates": len(dates_to_check),
        "duration_seconds": duration
    }
    
    # Save results to database for offline access
    check_type = "immediate" if hasattr(args, 'immediate') and args.immediate else "scheduled"
    await save_results_to_database(results, check_type)
    
    return results

async def main():
    """Main monitoring loop."""
    # Check database configuration
    database_enabled = os.getenv("DATABASE_ENABLED", "true").lower() == "true"
    if not database_enabled:
        console.print("🏠 Database disabled via DATABASE_ENABLED=false - using JSON storage only", style="yellow")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Golf Availability Monitor")
    parser.add_argument("--time-window", default="16:00-18:00", 
                       help="Time window to monitor (default: 16:00-18:00)")
    parser.add_argument("--interval", type=int, default=300, 
                       help="Check interval in seconds (default: 300 = 5 minutes)")
    parser.add_argument("--scheduled", action="store_true",
                       help="Run in scheduled mode - only check at 9am, 12pm, and 9pm")
    parser.add_argument("--immediate", action="store_true",
                       help="Run immediate check once and exit")
    parser.add_argument("--players", type=int, default=3, 
                       help="Minimum number of available slots required (default: 3)")
    parser.add_argument("--days", type=int, default=2,
                       help="Number of days to check from today (default: 2)")
    parser.add_argument("--local", action="store_true", 
                       help="Run in local mode - skip API/UI, use only CLI arguments and environment variables")
    args = parser.parse_args()
    
    # Parse time window
    try:
        time_window = parse_time_window(args.time_window)
        window_str = f"{time_window[0]//60:02d}:{time_window[0]%60:02d}-{time_window[1]//60:02d}:{time_window[1]%60:02d}"
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        return

    console.print("🏌️ Golf Availability Monitor - Personalized Edition", style="bold blue")
    console.print("=" * 60)
    
    # Handle scheduled mode
    if args.scheduled:
        console.print("⏰ Running in SCHEDULED MODE - notifications at 9am, 12pm, and 9pm", style="bold cyan")
        return await run_scheduled_monitoring(args, time_window, window_str)
    
    # Handle immediate mode
    if args.immediate:
        console.print("⚡ Running IMMEDIATE CHECK - single check and exit", style="bold yellow")
        return await run_immediate_check(args, time_window, window_str)
    
    # Check if running in local mode
    if args.local:
        console.print("🏠 Running in LOCAL MODE - skipping API/UI, using CLI arguments only", style="bold yellow")
        user_preferences = []
    else:
        # Load user preferences from cloud API first
        user_preferences = get_user_preferences()
    
    if user_preferences:
        console.print(f"👥 Running personalized monitoring for {len(user_preferences)} users:", style="blue")
        for user in user_preferences:
            user_name = user.get('name', 'Unknown')
            user_email = user.get('email', 'No email')
            courses_count = len(user.get('selected_courses', []))
            times_count = len(user.get('time_slots', user.get('selected_time_slots', [])))
            console.print(f"  📧 {user_email} ({user_name}): {courses_count} courses, {times_count} time slots", style="cyan")
        console.print("📧 Each user will receive personalized email notifications based on their preferences", style="green")
    else:
        console.print("👥 No user preferences found - using legacy mode", style="yellow")
        console.print("🔓 SCRAPING ALL TIMES - No time window filtering will be applied", style="bold yellow")
        console.print("💡 Create user profiles at your Streamlit app to enable personalized monitoring", style="dim")
    
    # Determine which clubs to monitor
    # Always monitor ALL clubs when not in local mode, then filter notifications by user preferences
    selected_clubs_env = os.getenv("SELECTED_CLUBS", "").strip()
    if selected_clubs_env:
        # Environment variable override (for testing specific clubs)
        club_keys = [key.strip() for key in re.split(r"[,;\n\r\t]+", selected_clubs_env) if key.strip()]
        console.print(f"📋 Using environment SELECTED_CLUBS override: {len(club_keys)} courses", style="yellow")
    else:
        # Monitor ALL available clubs - user preferences will filter notifications
        club_keys = golf_url_manager.get_default_club_configuration()
        console.print(f"📋 Monitoring ALL available courses: {len(club_keys)} courses", style="cyan")
        
        if user_preferences:
            # Show what courses users are interested in (for info only)
            all_user_courses = set()
            for user in user_preferences:
                all_user_courses.update(user.get('selected_courses', []))
            console.print(f"💡 Users are interested in {len(all_user_courses)} specific courses (notifications will be filtered)", style="dim")
    
    # Get URLs and labels from golf_club_urls.py
    today = datetime.date.today()
    urls = [golf_url_manager.get_club_by_name(key).get_url_for_date(today) for key in club_keys if golf_url_manager.get_club_by_name(key)]
    labels = [golf_url_manager.get_club_by_name(key).display_name for key in club_keys if golf_url_manager.get_club_by_name(key)]
    
    console.print(f"Debug - Using club keys: {club_keys[:10]}{'...' if len(club_keys) > 10 else ''}", style="dim")
    console.print(f"Debug - Final labels count: {len(labels)}, URLs count: {len(urls)}", style="dim")
    
    # Debug: Check for clubs that couldn't be resolved
    missing_clubs = []
    for key in club_keys:
        club = golf_url_manager.get_club_by_name(key)
        if not club:
            missing_clubs.append(key)
    
    if missing_clubs:
        console.print(f"⚠️ Warning: {len(missing_clubs)} clubs couldn't be resolved: {missing_clubs[:5]}", style="yellow")
    
    console.print(f"Monitoring {len(club_keys)} courses total", style="blue")
    console.print(f"Time window: {window_str}", style="blue")
    console.print(f"Check interval: {args.interval} seconds", style="blue")
    
    # Show course list
    console.print("\nCourses to monitor:", style="cyan")
    for i, label in enumerate(labels[:len(urls)]):
        console.print(f"  {i+1}. {label}", style="dim")
    
    console.print("\nPress Ctrl+C to stop\n", style="dim")
    
    # Track previous state to detect new availability
    previous_state: Dict[str, Dict[str, int]] = {}
    
    # Launch browser once and reuse
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        
        try:
            # Attempt automatic login
            console.print("🔐 Authenticating with golfbox.golf...", style="cyan")
            
            login_success = await automatic_login(pw, context)
            if not login_success:
                console.print("Authentication failed. Exiting.", style="red")
                return
            
            console.print("Authentication successful! Starting monitoring...", style="green")
            
            cycle = 0
            while True:
                cycle += 1
                
                # Check current day + next (days-1) days
                today = datetime.date.today()
                dates_to_check = [today + datetime.timedelta(days=i) for i in range(args.days)]
                
                console.print(f"\n🔄 Cycle {cycle} - {datetime.datetime.now().strftime('%H:%M:%S')}")
                console.print(f"Checking availability for {len(dates_to_check)} days: {dates_to_check[0]} to {dates_to_check[-1]}")
                
                current_state = {}
                new_availability = []
                
                # Check each date
                for target_date in dates_to_check:
                    date_str = target_date.strftime('%Y-%m-%d')
                    day_name = "Today" if target_date == today else target_date.strftime('%A')
                    console.print(f"\n📅 {day_name} ({date_str})")
                    
                    # Check each course for this date
                    for i, (base_url, label) in enumerate(zip(urls, labels)):
                        # Use the existing URL rewriting logic that handles SelectedDate properly
                        url = rewrite_url_for_day(base_url, target_date)
                        console.print(f"  DEBUG: Course {i+1} - {label}, Date: {date_str}", style="dim")
                        console.print(f"  DEBUG: Base URL: {base_url[:100]}...", style="dim")
                        console.print(f"  DEBUG: Rewritten URL: {url[:100]}...", style="dim")
                        
                        # When no user preferences exist, scrape all times (no filtering)
                        no_time_filter = len(user_preferences) == 0
                        if no_time_filter:
                            console.print(f"    📍 Scraping ALL times (no time window filter)", style="yellow")
                        available_times = await check_course_availability(context, url, label, target_date, time_window, args.players, no_time_filter)
                        
                        # Store state with date key
                        state_key = f"{label}_{date_str}"
                        current_state[state_key] = available_times
                        
                        # Check for new availability
                        previous_times = previous_state.get(state_key, {})
                        for time_str, capacity in available_times.items():
                            if time_str not in previous_times or capacity > previous_times[time_str]:
                                new_availability.append(f"{label} on {date_str} at {time_str}: {capacity} spots")
                
                # Display results summary
                console.print(f"\n📊 Summary for {len(dates_to_check)} days:")
                
                total_found = 0
                for target_date in dates_to_check:
                    date_str = target_date.strftime('%Y-%m-%d')
                    day_name = "Today" if target_date == today else target_date.strftime('%A')
                    
                    # Create table for this date
                    table = Table(title=f"{day_name} ({date_str})", show_header=True, header_style="bold blue")
                    table.add_column("Course", style="cyan", no_wrap=True)
                    table.add_column("Available Times", style="green")
                    
                    date_total = 0
                    for label in labels[:len(urls)]:
                        state_key = f"{label}_{date_str}"
                        times = current_state.get(state_key, {})
                        if times:
                            times_str = ", ".join([f"{t}({c})" for t, c in sorted(times.items())])
                            table.add_row(label, times_str)
                            date_total += len(times)
                            total_found += len(times)
                        else:
                            table.add_row(label, "[dim]No availability[/dim]")
                    
                    console.print(table)
                    console.print(f"Times found for {day_name}: {date_total}")
                
                console.print(f"\n🎯 Total times found across all days: {total_found}")
                
                # Send personalized notifications to users or fallback to generic email
                if user_preferences:
                    # Send personalized notifications to each user
                    console.print("\n📧 Sending personalized notifications...", style="bold cyan")
                    send_personalized_notifications(user_preferences, current_state, dates_to_check, previous_state)
                else:
                    # Fallback to original generic email notification
                    if new_availability:
                        console.print("\n🚨 New availability detected!", style="bold green")
                        for item in new_availability:
                            console.print(f"  • {item}", style="green")
                        
                        # Send generic email notification
                        alert_date = dates_to_check[0].strftime('%Y-%m-%d')
                        subject = f"⛳ Golf Availability Alert - {alert_date}"
                        
                        # Prepare configuration info for email
                        config_info = {
                            'courses': len(urls),
                            'time_window': window_str,
                            'interval': args.interval,
                            'min_players': args.players,
                            'days': args.days
                        }
                        
                        send_email_notification(
                            subject=subject, 
                            new_availability=new_availability,
                            all_availability=current_state,
                            time_window=window_str,
                            config_info=config_info,
                            club_order=labels
                        )
                        console.print("Generic email notification sent!", style="green")
                
                # Save results to database for offline access
                end_time = datetime.datetime.now()
                duration = (end_time - datetime.datetime.now().replace(minute=0, second=0, microsecond=0)).total_seconds()
                
                results = {
                    "success": True,
                    "timestamp": end_time.isoformat(),
                    "availability": current_state,
                    "new_availability": new_availability,
                    "total_courses": len(labels),
                    "total_dates": len(dates_to_check),
                    "duration_seconds": duration
                }
                
                await save_results_to_database(results, check_type="scheduled")
                
                # Update previous state
                previous_state = current_state.copy()
                
                # Wait for next check
                next_check = datetime.datetime.now() + datetime.timedelta(seconds=args.interval)
                console.print(f"\nNext check: {next_check.strftime('%H:%M:%S')}", style="dim")
                
                await asyncio.sleep(args.interval)
                
        except KeyboardInterrupt:
            console.print("\n\n👋 Monitoring stopped. Happy golfing!", style="bold blue")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
