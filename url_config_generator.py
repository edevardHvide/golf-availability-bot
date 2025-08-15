#!/usr/bin/env python3
"""Generate GolfBox URL configurations for different dates and club selections."""

import os
from datetime import date, datetime, timedelta
from typing import List, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box
from golf_club_urls import golf_url_manager, get_club_config_string

console = Console()

def interactive_url_generator():
    """Interactive URL configuration generator."""
    console.print("🔗 GolfBox URL Configuration Generator", style="bold blue")
    console.print("=" * 60, style="blue")
    
    # Show available clubs
    console.print("\n🏌️ Available Golf Clubs:", style="bold green")
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    table.add_column("Key", style="yellow", width=15)
    table.add_column("Club Name", style="white", width=20)
    table.add_column("Default Start Time", style="dim", justify="center")
    
    for key, club in golf_url_manager.clubs.items():
        start_time = f"{club.default_start_time[:2]}:{club.default_start_time[2:4]}"
        table.add_row(key, club.display_name, start_time)
    
    console.print(table)
    
    # Get club selection
    console.print(f"\n📋 Club Selection:")
    selection_method = Prompt.ask(
        "How do you want to select clubs?",
        choices=["all", "list", "oslo-area"],
        default="oslo-area"
    )
    
    if selection_method == "all":
        selected_keys = list(golf_url_manager.clubs.keys())
    elif selection_method == "oslo-area":
        selected_keys = ["oslo_golfklubb", "baerum_gk", "miklagard_gk", "haga_gk", "grini_gk"]
    else:  # list
        keys_input = Prompt.ask("Enter club keys (comma-separated)")
        selected_keys = [key.strip() for key in keys_input.split(",") if key.strip()]
    
    # Validate keys
    valid_keys = []
    for key in selected_keys:
        if golf_url_manager.get_club_by_name(key):
            valid_keys.append(key)
        else:
            console.print(f"⚠️ Unknown club key: {key}", style="yellow")
    
    if not valid_keys:
        console.print("❌ No valid clubs selected.", style="red")
        return
    
    # Get date selection
    console.print(f"\n📅 Date Configuration:")
    date_method = Prompt.ask(
        "Date configuration method",
        choices=["today", "tomorrow", "weekend", "specific", "range"],
        default="weekend"
    )
    
    target_dates = []
    if date_method == "today":
        target_dates = [date.today()]
    elif date_method == "tomorrow":
        target_dates = [date.today() + timedelta(days=1)]
    elif date_method == "weekend":
        today = date.today()
        # Find next Saturday
        days_until_sat = (5 - today.weekday()) % 7
        if days_until_sat == 0 and today.weekday() == 5:  # Today is Saturday
            saturday = today
        else:
            saturday = today + timedelta(days=days_until_sat or 7)
        sunday = saturday + timedelta(days=1)
        target_dates = [saturday, sunday]
    elif date_method == "specific":
        date_str = Prompt.ask("Enter date (YYYY-MM-DD)", default=date.today().strftime("%Y-%m-%d"))
        try:
            target_dates = [datetime.strptime(date_str, "%Y-%m-%d").date()]
        except ValueError:
            console.print("❌ Invalid date format.", style="red")
            return
    else:  # range
        start_str = Prompt.ask("Start date (YYYY-MM-DD)")
        end_str = Prompt.ask("End date (YYYY-MM-DD)")
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            current = start_date
            while current <= end_date:
                target_dates.append(current)
                current += timedelta(days=1)
        except ValueError:
            console.print("❌ Invalid date format.", style="red")
            return
    
    # Get start time
    console.print(f"\n⏰ Time Configuration:")
    use_default = Confirm.ask("Use default start times for each club?", default=True)
    
    custom_start_time = None
    if not use_default:
        time_input = Prompt.ask("Enter start time (HH:MM)", default="07:00")
        try:
            time_obj = datetime.strptime(time_input, "%H:%M").time()
            custom_start_time = time_obj.strftime("%H%M00")
        except ValueError:
            console.print("❌ Invalid time format. Using default times.", style="yellow")
    
    # Generate configurations for each date
    console.print(f"\n🔧 Generated Configurations:", style="bold green")
    console.print("=" * 60, style="green")
    
    for i, target_date in enumerate(target_dates):
        date_str = target_date.strftime("%Y-%m-%d (%A)")
        console.print(f"\n📅 {date_str}:", style="bold cyan")
        
        urls, labels = get_club_config_string(valid_keys, target_date, custom_start_time)
        
        console.print(f"GOLFBOX_GRID_URL={urls}", style="dim")
        console.print(f"GRID_LABELS={labels}", style="dim")
        
        if i == 0:  # Show details for first date only
            console.print(f"\n📋 Selected Clubs ({len(valid_keys)}):", style="bold")
            for key in valid_keys:
                club = golf_url_manager.get_club_by_name(key)
                if club:
                    start_time_display = custom_start_time or club.default_start_time
                    start_formatted = f"{start_time_display[:2]}:{start_time_display[2:4]}"
                    console.print(f"  • {club.display_name} - {start_formatted}")
    
    # Save to file
    if Confirm.ask(f"\n💾 Save configurations to file?"):
        filename = f"golf_urls_{date.today().strftime('%Y%m%d')}.txt"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write("# Golf Club URL Configurations\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Selected clubs: {', '.join([golf_url_manager.get_club_by_name(k).display_name for k in valid_keys if golf_url_manager.get_club_by_name(k)])}\n\n")
            
            for target_date in target_dates:
                date_str = target_date.strftime("%Y-%m-%d (%A)")
                f.write(f"# {date_str}\n")
                
                urls, labels = get_club_config_string(valid_keys, target_date, custom_start_time)
                f.write(f"GOLFBOX_GRID_URL={urls}\n")
                f.write(f"GRID_LABELS={labels}\n\n")
        
        console.print(f"✅ Configurations saved to {filename}", style="bold green")


def generate_config_for_clubs(club_keys: List[str], target_date: Optional[date] = None,
                             start_time: Optional[str] = None) -> dict:
    """Generate configuration for specific clubs and date."""
    if target_date is None:
        target_date = date.today()
    
    urls, labels = get_club_config_string(club_keys, target_date, start_time)
    
    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "clubs": [golf_url_manager.get_club_by_name(k).display_name for k in club_keys 
                 if golf_url_manager.get_club_by_name(k)],
        "urls": urls,
        "labels": labels,
        "start_time": start_time or "default"
    }


def update_env_with_urls(club_keys: List[str], target_date: Optional[date] = None,
                        start_time: Optional[str] = None):
    """Update .env file with generated URLs."""
    config = generate_config_for_clubs(club_keys, target_date, start_time)
    
    env_file = ".env"
    if not os.path.exists(env_file):
        console.print("❌ .env file not found.", style="red")
        return
    
    # Read current content
    with open(env_file, "r") as f:
        lines = f.readlines()
    
    # Update lines
    updated_lines = []
    updated_urls = False
    updated_labels = False
    
    for line in lines:
        if line.startswith("GOLFBOX_GRID_URL="):
            updated_lines.append(f"GOLFBOX_GRID_URL={config['urls']}\n")
            updated_urls = True
        elif line.startswith("GRID_LABELS="):
            updated_lines.append(f"GRID_LABELS={config['labels']}\n")
            updated_labels = True
        else:
            updated_lines.append(line)
    
    # Add if not found
    if not updated_urls:
        updated_lines.append(f"GOLFBOX_GRID_URL={config['urls']}\n")
    if not updated_labels:
        updated_lines.append(f"GRID_LABELS={config['labels']}\n")
    
    # Write back
    with open(env_file, "w") as f:
        f.writelines(updated_lines)
    
    console.print(f"✅ Updated .env file with URLs for {len(club_keys)} clubs", style="green")


if __name__ == "__main__":
    interactive_url_generator()
