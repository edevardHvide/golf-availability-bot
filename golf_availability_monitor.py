l
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

async def check_course_availability(context: BrowserContext, url: str, course_name: str, target_date: datetime.date, time_window: tuple[int, int], min_players: int = 1) -> Dict[str, int]:
    """Check availability for a single course and return times within window."""
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
        
        # Filter times within window and calculate capacity
        available_times = {}
        for time_str, labels in times.items():
            # Skip times that are within window but have already passed for today
            if time_in_window(time_str, time_window) and not time_has_passed(time_str, target_date):
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
    """Filter availability results based on user preferences."""
    filtered = {}
    
    # Get user's preferred courses
    user_courses = user_prefs.get('selected_courses', [])
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

async def main():
    """Main monitoring loop."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Golf Availability Monitor")
    parser.add_argument("--time-window", default="08:00-17:00", 
                       help="Time window to monitor (default: 08:00-17:00)")
    parser.add_argument("--interval", type=int, default=300, 
                       help="Check interval in seconds (default: 300 = 5 minutes)")
    parser.add_argument("--players", type=int, default=1, 
                       help="Minimum number of available slots required (default: 1)")
    parser.add_argument("--days", type=int, default=4,
                       help="Number of days to check from today (default: 4)")
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
        console.print("💡 Create user profiles at your Streamlit app to enable personalized monitoring", style="dim")
    
    # Determine which clubs to monitor
    if user_preferences:
        # Build comprehensive club list from all users
        all_user_courses = set()
        for user in user_preferences:
            all_user_courses.update(user.get('selected_courses', []))
        
        club_keys = list(all_user_courses)
        console.print(f"📋 Monitoring all courses from user preferences: {len(club_keys)} courses", style="cyan")
    else:
        # Fallback to original logic
        selected_clubs_env = os.getenv("SELECTED_CLUBS", "").strip()
        if selected_clubs_env:
            club_keys = [key.strip() for key in re.split(r"[,;\n\r\t]+", selected_clubs_env) if key.strip()]
        else:
            club_keys = golf_url_manager.get_default_club_configuration()
        console.print(f"📋 Using default/environment configuration: {len(club_keys)} courses", style="cyan")
    
    # Get URLs and labels from golf_club_urls.py
    today = datetime.date.today()
    urls = [golf_url_manager.get_club_by_name(key).get_url_for_date(today) for key in club_keys if golf_url_manager.get_club_by_name(key)]
    labels = [golf_url_manager.get_club_by_name(key).display_name for key in club_keys if golf_url_manager.get_club_by_name(key)]
    
    console.print(f"Debug - Using club keys: {club_keys}", style="dim")
    console.print(f"Debug - Final labels count: {len(labels)}, URLs count: {len(urls)}", style="dim")
    
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
                        
                        available_times = await check_course_availability(context, url, label, target_date, time_window, args.players)
                        
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
