#!/usr/bin/env python3
"""Setup script to help users configure their .env file."""

import os
import shutil
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box

console = Console()

def create_env_from_template():
    """Create .env file from template with user input."""
    
    console.print("🏌️ Golf Bot Configuration Setup", style="bold blue")
    console.print("=" * 50, style="blue")
    
    # Check if .env already exists
    if os.path.exists(".env"):
        if not Confirm.ask("⚠️ .env file already exists. Overwrite?"):
            console.print("Setup cancelled.", style="yellow")
            return
    
    # Copy template
    if os.path.exists("config_template.env"):
        shutil.copy("config_template.env", ".env")
        console.print("✅ Created .env from template", style="green")
    else:
        console.print("❌ Template file not found!", style="red")
        return
    
    console.print("\n📋 Let's configure your preferences:", style="bold")
    
    # Golf clubs selection
    console.print("\n🏌️ Golf Club Selection:")
    console.print("Available clubs: oslo, miklagard, bogstad, losby, holtsmark, bjaavann, drammen, asker, vestfold, moss")
    clubs = Prompt.ask("Enter clubs to monitor (comma-separated, or leave empty for all)", default="oslo,miklagard,bogstad")
    
    # Date selection
    console.print("\n📅 Date Selection:")
    console.print("1. Days ahead (e.g., next 7 days)")
    console.print("2. Specific dates (e.g., 2025-01-20,2025-01-21)")
    console.print("3. Weekend mode (next few weekends)")
    date_mode = Prompt.ask("Choose date mode", choices=["1", "2", "3"], default="1")
    
    days_ahead = "7"
    specific_dates = ""
    weekend_mode = "false"
    
    if date_mode == "1":
        days_ahead = Prompt.ask("How many days ahead to monitor", default="7")
    elif date_mode == "2":
        specific_dates = Prompt.ask("Enter specific dates (YYYY-MM-DD,YYYY-MM-DD)")
    else:
        weekend_mode = "true"
        weekends = Prompt.ask("How many weekends to monitor", default="2")
    
    # Time preferences
    console.print("\n⏰ Time Preferences:")
    time_start = Prompt.ask("Start time (HH:MM)", default="07:00")
    time_end = Prompt.ask("End time (HH:MM)", default="18:00")
    
    # Player count
    console.print("\n👥 Player Requirements:")
    player_count = Prompt.ask("Number of players in your group", default="4")
    
    # Email setup
    console.print("\n📧 Email Notifications:")
    email_enabled = Confirm.ask("Enable email notifications?", default=True)
    email_to = ""
    if email_enabled:
        email_to = Prompt.ask("Email recipients (comma-separated)")
    
    # Update .env file
    update_env_file({
        "SELECTED_CLUBS": clubs,
        "DAYS_AHEAD": days_ahead,
        "SPECIFIC_DATES": specific_dates,
        "WEEKEND_MODE": weekend_mode,
        "TIME_START": time_start,
        "TIME_END": time_end,
        "PLAYER_COUNT": player_count,
        "EMAIL_ENABLED": "true" if email_enabled else "false",
        "EMAIL_TO": email_to
    })
    
    console.print("\n✅ Configuration complete!", style="bold green")
    console.print("\n🚀 To start monitoring, run:", style="bold")
    console.print("   python golf_monitor.py", style="cyan")


def update_env_file(updates: dict):
    """Update specific values in the .env file."""
    if not os.path.exists(".env"):
        return
    
    # Read current content
    with open(".env", "r") as f:
        lines = f.readlines()
    
    # Update values
    updated_lines = []
    for line in lines:
        updated = False
        for key, value in updates.items():
            if line.startswith(f"{key}=") or line.startswith(f"#{key}="):
                updated_lines.append(f"{key}={value}\n")
                updated = True
                break
        
        if not updated:
            updated_lines.append(line)
    
    # Write back
    with open(".env", "w") as f:
        f.writelines(updated_lines)


def show_current_config():
    """Show current configuration from .env file."""
    if not os.path.exists(".env"):
        console.print("❌ No .env file found. Run setup first.", style="red")
        return
    
    try:
        from config import load_golf_config
        config = load_golf_config()
        
        console.print("\n📋 Current Configuration:", style="bold blue")
        console.print("=" * 50, style="blue")
        console.print(config.get_summary())
        
    except Exception as e:
        console.print(f"❌ Error loading configuration: {e}", style="red")


def main():
    """Main setup interface."""
    console.print("🏌️ Golf Bot Setup & Configuration", style="bold green")
    console.print("=" * 50, style="green")
    
    while True:
        console.print("\nWhat would you like to do?")
        console.print("1. Create/update .env configuration")
        console.print("2. Show current configuration")
        console.print("3. Test configuration")
        console.print("4. Exit")
        
        choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4"], default="1")
        
        if choice == "1":
            create_env_from_template()
        elif choice == "2":
            show_current_config()
        elif choice == "3":
            console.print("\n🧪 Testing configuration...")
            try:
                from config import load_golf_config
                config = load_golf_config()
                console.print("✅ Configuration loaded successfully!", style="green")
                console.print(config.get_summary())
            except Exception as e:
                console.print(f"❌ Configuration error: {e}", style="red")
        else:
            break
    
    console.print("\n👋 Setup complete! Happy golfing!", style="bold blue")


if __name__ == "__main__":
    main()
