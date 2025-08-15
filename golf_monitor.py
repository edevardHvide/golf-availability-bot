#!/usr/bin/env python3
"""Enhanced Golf Availability Monitor with comprehensive .env configuration."""

import asyncio
import datetime
import os
import sys
import time
from typing import Dict, List

from rich.console import Console
from rich.table import Table
from rich import box

# Import our modules
from config import load_golf_config
from check_availability import (
    collect_all_tee_times, 
    send_notification, 
    send_email_notification,
    display_teetimes_table,
    has_changes,
    get_changes_summary,
    _ensure_session,
    _apply_manual_cookies,
    login_to_golfbox
)

console = Console()


def filter_times_by_config(times_dict: Dict[str, List[str]], config) -> Dict[str, List[str]]:
    """Filter tee times based on configuration preferences."""
    if not times_dict:
        return times_dict
    
    filtered = {}
    for time_str, slots in times_dict.items():
        # Check if time should be included
        if config.should_include_time(time_str):
            # Filter slots based on player requirements
            if len(slots) >= config.min_available_slots:
                filtered[time_str] = slots
    
    return filtered


def filter_clubs_data(all_times: Dict, config) -> Dict:
    """Filter data to only include selected clubs."""
    if not config.selected_clubs:
        return all_times
    
    filtered_data = {}
    for club_name, club_data in all_times.items():
        if club_name in config.selected_clubs:
            filtered_data[club_name] = club_data
    
    return filtered_data


def create_enhanced_email_body(changes: List[str], config) -> str:
    """Create a detailed email body with configuration context."""
    body = f"""🏌️ Golf Tee Time Alert!

New tee times have been found matching your preferences:

{chr(10).join([f"• {change}" for change in changes])}

Your Configuration:
• Golf Clubs: {', '.join([club.title() for club in config.selected_clubs])}
• Players: {config.player_count}
• Time Window: {config.time_start.strftime('%H:%M')} - {config.time_end.strftime('%H:%M')}
• Dates: {len(config.dates)} days ({config.dates[0]} to {config.dates[-1]})

Happy golfing! ⛳

---
Golf Availability Bot
"""
    return body


def display_config_summary(config):
    """Display a nice configuration summary."""
    console.print("\n🏌️ Golf Availability Monitor", style="bold blue")
    console.print("=" * 60, style="blue")
    
    # Create configuration table
    config_table = Table(
        title="Configuration Summary",
        box=box.ROUNDED,
        show_header=False,
        title_style="bold green"
    )
    config_table.add_column("Setting", style="bold cyan", width=20)
    config_table.add_column("Value", style="white")
    
    config_table.add_row("🏌️ Golf Clubs", f"{len(config.selected_clubs)} clubs")
    for club in config.selected_clubs:
        config_table.add_row("", f"  • {club.title()}")
    
    config_table.add_row("📅 Monitoring", f"{len(config.dates)} days")
    config_table.add_row("", f"  {config.dates[0]} to {config.dates[-1]}")
    
    config_table.add_row("⏰ Time Window", 
                        f"{config.time_start.strftime('%H:%M')} - {config.time_end.strftime('%H:%M')}")
    
    if config.preferred_times:
        preferred_str = ', '.join([t.strftime('%H:%M') for t in config.preferred_times])
        config_table.add_row("🎯 Preferred Times", preferred_str)
    
    config_table.add_row("👥 Players", f"{config.player_count} players")
    config_table.add_row("📊 Min Slots", f"{config.min_available_slots} slots required")
    config_table.add_row("🔄 Check Interval", f"{config.check_interval} seconds")
    
    if config.email_enabled and config.email_to:
        config_table.add_row("📧 Email Alerts", f"{len(config.email_to)} recipients")
    
    console.print(config_table)
    console.print("\nPress Ctrl+C to stop monitoring\n", style="dim")


def run_monitor_with_config():
    """Run the monitoring loop using .env configuration."""
    # Load configuration
    config = load_golf_config()
    
    # Display configuration
    display_config_summary(config)
    
    # Initialize session
    session = _ensure_session(None)
    
    # Login if credentials provided
    if config.golfbox_user and config.golfbox_pass:
        logged_in = login_to_golfbox(session, config.golfbox_user, config.golfbox_pass)
        if logged_in:
            console.print("🔐 Logged in to golfbox.golf successfully.", style="green")
        else:
            console.print("⚠️ Could not verify login. Continuing without authentication.", style="yellow")
    
    # Initialize state
    previous_times = {}
    
    try:
        while True:
            console.print(f"\n⛳ Checking availability at {datetime.datetime.now().strftime('%H:%M:%S')}", 
                         style="bold blue")
            
            # Collect tee times for all clubs and dates
            current_times = collect_all_tee_times(
                dates=config.dates,
                session=session,
                overrides=config.course_id_overrides,
                grid_overrides=config.grid_url_overrides,
                email=config.golfbox_user,
                password=config.golfbox_pass,
                debug=config.debug
            )
            
            # Filter by selected clubs
            current_times = filter_clubs_data(current_times, config)
            
            # Filter times by configuration preferences
            for club_name in current_times:
                for date in current_times[club_name]:
                    current_times[club_name][date] = filter_times_by_config(
                        current_times[club_name][date], config
                    )
            
            # Check for changes
            changes_detected = has_changes(current_times, previous_times)
            if changes_detected:
                changes = get_changes_summary(current_times, previous_times, config.dates)
                
                if changes:
                    # Send notifications
                    summary = "; ".join(changes[:3])
                    if len(changes) > 3:
                        summary += f" and {len(changes) - 3} more..."
                    
                    if config.desktop_notifications:
                        send_notification("⛳ Golf Tee Times Updated!", summary)
                    
                    if config.email_notifications and config.email_enabled:
                        detailed_body = create_enhanced_email_body(changes, config)
                        send_email_notification("⛳ Golf Tee Times Found!", detailed_body)
                    
                    if config.console_output:
                        console.print("\n🔔 Changes detected!", style="bold green")
                        for change in changes:
                            console.print(f"   • {change}", style="green")
            
            elif previous_times and config.console_output:
                console.print("\n✓ No changes detected.", style="dim green")
            
            # Display current state
            if config.console_output:
                display_teetimes_table(
                    current_times,
                    previous_times if changes_detected else {},
                    config.dates
                )
            
            # Update state
            previous_times = current_times.copy()
            
            # Wait for next check
            next_check = (datetime.datetime.now() + 
                         datetime.timedelta(seconds=config.check_interval)).strftime("%H:%M:%S")
            
            if config.console_output:
                console.print(f"\n⏰ Next check at {next_check}", style="dim blue")
            
            time.sleep(config.check_interval)
    
    except KeyboardInterrupt:
        console.print("\n\n👋 Monitoring stopped. Have a great round!", style="bold blue")
    except Exception as e:
        console.print(f"\n❌ Error occurred: {e}", style="red")
        console.print("Check your .env configuration and try again.", style="yellow")


def main():
    """Main entry point."""
    if not os.path.exists(".env"):
        console.print("❌ No .env file found!", style="bold red")
        console.print("\n📋 To get started:", style="bold yellow")
        console.print("1. Copy config_template.env to .env")
        console.print("2. Edit .env with your preferences")
        console.print("3. Run this script again")
        console.print("\nExample:", style="dim")
        console.print("  copy config_template.env .env", style="dim")
        return
    
    try:
        run_monitor_with_config()
    except Exception as e:
        console.print(f"❌ Configuration error: {e}", style="red")
        console.print("Please check your .env file settings.", style="yellow")


if __name__ == "__main__":
    main()
