#!/usr/bin/env python3
"""Golf Availability Monitor - Main monitoring script for multiple courses.

Environment Variables:
    GOLFBOX_GRID_URL: Comma-separated URLs to monitor
    GRID_LABELS: Comma-separated names for the courses
    
A browser window will open for manual login to golfbox.golf.
"""

import asyncio
import argparse
import datetime
import os
import re
from typing import Dict
from dotenv import load_dotenv

from playwright.async_api import async_playwright, BrowserContext, Page
from rich.console import Console
from rich.table import Table

from golfbot.grid_parser import parse_grid_html
from golf_utils import send_email_notification, rewrite_url_for_day

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
    args = parser.parse_args()
    
    # Parse time window
    try:
        time_window = parse_time_window(args.time_window)
        window_str = f"{time_window[0]//60:02d}:{time_window[0]%60:02d}-{time_window[1]//60:02d}:{time_window[1]%60:02d}"
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        return
    
    # Get URLs from environment
    grid_urls_csv = os.getenv("GOLFBOX_GRID_URL", "").strip()
    if not grid_urls_csv:
        console.print("Error: GOLFBOX_GRID_URL not set in environment", style="red")
        return
    
    # Parse URLs (comma/semicolon separated)
    raw_urls = re.split(r"[,;\n\r\t]+", grid_urls_csv)
    urls = []
    for url in raw_urls:
        url = url.strip().strip('"\'')
        if url:
            # Fix missing protocol
            if url.startswith('//'):
                url = 'https:' + url
            elif not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            urls.append(url)
    
    # Get course labels from environment
    labels_csv = os.getenv("GRID_LABELS", "").strip()
    console.print(f"Debug - GRID_LABELS from env: '{labels_csv}'", style="dim")
    
    if labels_csv:
        raw_labels = re.split(r"[,;\n\r]+", labels_csv)
        labels = [lbl.strip().strip('"\'') for lbl in raw_labels if lbl.strip()]
        console.print(f"Debug - Parsed {len(labels)} labels: {labels}", style="dim")
    else:
        labels = [f"Course {i+1}" for i in range(len(urls))]
        console.print("Debug - No GRID_LABELS found, using generic names", style="dim")
    
    # Ensure we have enough labels
    while len(labels) < len(urls):
        labels.append(f"Course {len(labels)+1}")
    
    console.print(f"Debug - Final labels count: {len(labels)}, URLs count: {len(urls)}", style="dim")
    
    console.print("🏌️ Golf Availability Monitor", style="bold blue")
    console.print(f"Monitoring {len(urls)} courses", style="blue")
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
                
                # Send email for new availability
                if new_availability:
                    console.print("\n🚨 New availability detected!", style="bold green")
                    for item in new_availability:
                        console.print(f"  • {item}", style="green")
                    
                    # Send email notification
                    alert_date = dates_to_check[0].strftime('%Y-%m-%d')
                    subject = f"⛳ Golf Availability Alert - {alert_date}"
                    
                    send_email_notification(
                        subject=subject, 
                        new_availability=new_availability,
                        all_availability=current_state,
                        time_window=window_str
                    )
                    console.print("Email notification sent!", style="green")
                
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