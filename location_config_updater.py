#!/usr/bin/env python3
"""Update configuration with location-based golf club selection."""

import os
from typing import List
from rich.console import Console
from rich.prompt import Prompt, Confirm
from location_finder import find_nearby_golf_clubs, GolfClub

console = Console()

def update_config_with_location():
    """Update .env configuration with location-based club selection."""
    console.print("🏌️ Location-Based Golf Club Configuration", style="bold blue")
    console.print("=" * 60, style="blue")
    
    # Get user location
    location = Prompt.ask("📍 Enter your location (address, city, or coordinates)")
    
    # Get driving time preference
    max_minutes = int(Prompt.ask("⏰ Maximum driving time in minutes", default="60"))
    
    # Find nearby clubs
    console.print(f"\n🔍 Searching for golf clubs within {max_minutes} minutes of {location}...")
    clubs = find_nearby_golf_clubs(location, max_minutes)
    
    if not clubs:
        console.print("❌ No golf clubs found within your range.", style="red")
        return
    
    # Display found clubs
    console.print(f"\n✅ Found {len(clubs)} golf clubs:", style="bold green")
    for i, club in enumerate(clubs, 1):
        drive_time = f"{club.drive_time_minutes} min" if club.drive_time_minutes else "~"
        console.print(f"  {i}. {club.name} - {drive_time} ({club.distance_km} km)")
    
    # Ask user to select clubs
    console.print(f"\n📋 Club Selection:")
    selection_mode = Prompt.ask(
        "How would you like to select clubs?",
        choices=["all", "top", "custom"],
        default="all"
    )
    
    selected_clubs = []
    
    if selection_mode == "all":
        selected_clubs = clubs
    elif selection_mode == "top":
        top_count = int(Prompt.ask("How many closest clubs?", default="5"))
        selected_clubs = clubs[:top_count]
    else:  # custom
        console.print("Enter club numbers (comma-separated, e.g., 1,3,5):")
        indices_str = Prompt.ask("Club numbers")
        try:
            indices = [int(x.strip()) - 1 for x in indices_str.split(",")]
            selected_clubs = [clubs[i] for i in indices if 0 <= i < len(clubs)]
        except (ValueError, IndexError):
            console.print("❌ Invalid selection. Using all clubs.", style="yellow")
            selected_clubs = clubs
    
    if not selected_clubs:
        console.print("❌ No clubs selected.", style="red")
        return
    
    # Generate configuration
    club_keys = [club.golfbox_key for club in selected_clubs if club.golfbox_key]
    config_line = ",".join(club_keys)
    
    console.print(f"\n📝 Selected {len(selected_clubs)} clubs:", style="bold green")
    for club in selected_clubs:
        drive_time = f"{club.drive_time_minutes} min" if club.drive_time_minutes else "~"
        console.print(f"  • {club.name} - {drive_time}")
    
    console.print(f"\n🔧 Configuration:", style="bold cyan")
    console.print(f"SELECTED_CLUBS={config_line}")
    
    # Update .env file
    if Confirm.ask("\n💾 Update your .env file with these clubs?"):
        update_env_file_clubs(config_line)
        console.print("✅ .env file updated!", style="bold green")
    
    # Save summary
    if Confirm.ask("📄 Save club summary to file?"):
        save_club_summary(location, max_minutes, selected_clubs, config_line)
        console.print("✅ Summary saved to golf_clubs_summary.txt", style="green")


def update_env_file_clubs(club_config: str):
    """Update SELECTED_CLUBS in .env file."""
    env_file = ".env"
    
    if not os.path.exists(env_file):
        console.print("❌ .env file not found. Creating from template...", style="yellow")
        if os.path.exists("config_template.env"):
            import shutil
            shutil.copy("config_template.env", env_file)
        else:
            console.print("❌ No template found. Please create .env manually.", style="red")
            return
    
    # Read current content
    with open(env_file, "r") as f:
        lines = f.readlines()
    
    # Update SELECTED_CLUBS line
    updated_lines = []
    updated = False
    
    for line in lines:
        if line.startswith("SELECTED_CLUBS=") or line.startswith("#SELECTED_CLUBS="):
            updated_lines.append(f"SELECTED_CLUBS={club_config}\n")
            updated = True
        else:
            updated_lines.append(line)
    
    # Add if not found
    if not updated:
        updated_lines.append(f"\n# Location-based club selection\nSELECTED_CLUBS={club_config}\n")
    
    # Write back
    with open(env_file, "w") as f:
        f.writelines(updated_lines)


def save_club_summary(location: str, max_minutes: int, clubs: List[GolfClub], config: str):
    """Save a summary of selected clubs to file."""
    with open("golf_clubs_summary.txt", "w", encoding="utf-8") as f:
        f.write("🏌️ Golf Club Selection Summary\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"📍 Your Location: {location}\n")
        f.write(f"⏰ Max Drive Time: {max_minutes} minutes\n")
        f.write(f"🎯 Selected Clubs: {len(clubs)}\n\n")
        
        f.write("Selected Golf Clubs:\n")
        f.write("-" * 20 + "\n")
        for club in clubs:
            drive_time = f"{club.drive_time_minutes} min" if club.drive_time_minutes else "Unknown"
            f.write(f"• {club.name}\n")
            f.write(f"  Drive Time: {drive_time}\n")
            f.write(f"  Distance: {club.distance_km} km\n")
            f.write(f"  Address: {club.address}\n\n")
        
        f.write("Configuration for .env:\n")
        f.write("-" * 20 + "\n")
        f.write(f"SELECTED_CLUBS={config}\n")


if __name__ == "__main__":
    update_config_with_location()
