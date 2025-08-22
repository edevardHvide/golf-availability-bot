#!/usr/bin/env python3
"""Golf Availability Monitor - Main monitoring script for multiple courses."""

import asyncio
import argparse
import datetime
import os
import re
from typing import Dict, List
from dotenv import load_dotenv

from playwright.async_api import async_playwright, BrowserContext
from rich.console import Console
from rich.table import Table

from golfbot.grid_parser import parse_grid_html
from check_availability import send_email_notification
from playwright_runner import _rewrite_url_for_day

# Load environment (override=True to ensure .env values are used)
load_dotenv(override=True)
console = Console()

def parse_time_window(time_str: str) -> tuple[int, int]:
    """Parse time window like '08:00-17:00' into (start_minutes, end_minutes)."""
    try:
        start_str, end_str = time_str.split('-')
        start_h, start_m = map(int, start_str.split(':'))
        end_h, end_m = map(int, end_str.split(':'))
        return (start_h * 60 + start_m, end_h * 60 + end_m)
    except:
        raise ValueError(f"Invalid time window format: {time_str}. Use HH:MM-HH:MM")

def time_in_window(time_str: str, window: tuple[int, int]) -> bool:
    """Check if HH:MM time is within the window."""
    try:
        h, m = map(int, time_str.split(':'))
        minutes = h * 60 + m
        return window[0] <= minutes <= window[1]
    except:
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

async def check_course_availability(context: BrowserContext, url: str, course_name: str, target_date: datetime.date, time_window: tuple[int, int]) -> Dict[str, int]:
    """Check availability for a single course and return times within window."""
    page = None
    try:
        console.print(f"  → Checking {course_name} for {target_date.strftime('%Y-%m-%d')}...", style="cyan")
        
        # Create a new page for this course to avoid navigation conflicts
        page = await context.new_page()
        
        # Navigate to the course URL
        await page.goto(url, wait_until="domcontentloaded")
        
        # Wait briefly for grid to load
        try:
            await page.wait_for_selector("div.hour, table", timeout=10000)
        except:
            pass
        
        # Get HTML and parse
        html = await page.content()
        times = parse_grid_html(html)
        
        # Filter times within window and calculate capacity
        available_times = {}
        for time_str, labels in times.items():
            if time_in_window(time_str, time_window):
                total_capacity = sum(parse_capacity_from_label(lbl) for lbl in labels)
                if total_capacity > 0:
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
    
    console.print(f"🏌️ Golf Availability Monitor", style="bold blue")
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
            # Always offer manual login at startup
            console.print("Opening golfbox.golf for authentication...", style="yellow")
            
            # Launch a visible browser for login
            login_browser = await pw.chromium.launch(headless=False)
            login_page = await login_browser.new_page()
            await login_page.goto("https://golfbox.golf/#/", wait_until="domcontentloaded")
            
            console.print("Browser window opened. Please login to golfbox.golf if needed...", style="yellow")
            console.print("Waiting for login completion (will auto-detect)...", style="dim")
            
            # Auto-detect login completion by checking for login indicators
            logged_in = False
            for attempt in range(60):  # Wait up to 60 seconds
                try:
                    # Check if we're still on a login page or if we're logged in
                    page_content = await login_page.content()
                    
                    # Signs we're logged in: no login forms, presence of logout/profile elements
                    has_login_form = await login_page.locator("input[type='password'], form[action*='login']").count() > 0
                    has_logout = "logout" in page_content.lower() or "logg ut" in page_content.lower()
                    has_profile = "min side" in page_content.lower() or "profile" in page_content.lower()
                    
                    if not has_login_form or has_logout or has_profile:
                        console.print("Login detected! Proceeding...", style="green")
                        logged_in = True
                        break
                        
                except Exception:
                    pass
                
                await asyncio.sleep(1)  # Check every second
            
            if not logged_in:
                console.print("Login timeout reached. Continuing anyway...", style="yellow")
            
            # Copy cookies to main headless context
            cookies = await login_page.context.cookies()
            await context.add_cookies(cookies)
            await login_browser.close()
            
            console.print("Authentication session saved. Starting monitoring with headless browser...", style="green")
            
            cycle = 0
            while True:
                cycle += 1
                
                # Check today and tomorrow only (for testing)
                today = datetime.date.today()
                dates_to_check = [today, today + datetime.timedelta(days=1)]
                
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
                        url = _rewrite_url_for_day(base_url, target_date)
                        
                        available_times = await check_course_availability(context, url, label, target_date, time_window)
                        
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
                    console.print(f"\n🚨 New availability detected!", style="bold green")
                    for item in new_availability:
                        console.print(f"  • {item}", style="green")
                    
                    # Send email notification
                    alert_date = dates_to_check[0].strftime('%Y-%m-%d')
                    subject = f"⛳ Golf Availability Alert - {alert_date}"
                    body = f"""New golf tee times available!

Time window: {window_str}

New availability:
""" + "\n".join([f"• {item}" for item in new_availability]) + f"""

All current availability:
""" + "\n".join([f"• {label}: {', '.join([f'{t}({c} spots)' for t, c in times.items()]) if times else 'None'}" 
                              for label, times in current_state.items()]) + f"""

Happy golfing! ⛳

--- Golf Availability Monitor ---
"""
                    
                    send_email_notification(subject, body)
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