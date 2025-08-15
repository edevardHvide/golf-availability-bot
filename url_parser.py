#!/usr/bin/env python3
"""Parse GolfBox URLs to extract GUIDs and update club mappings."""

import re
from typing import List, Dict, Tuple, Optional
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

def parse_golfbox_url(url: str) -> Optional[Dict[str, str]]:
    """Parse a single GolfBox URL to extract GUIDs and other info."""
    try:
        # Extract Resource_GUID
        resource_match = re.search(r'Ressource_GUID=\{([A-F0-9-]+)\}', url, re.IGNORECASE)
        resource_guid = resource_match.group(1) if resource_match else None
        
        # Extract Club_GUID  
        club_match = re.search(r'Club_GUID=([A-F0-9-]+)', url, re.IGNORECASE)
        club_guid = club_match.group(1) if club_match else None
        
        # Extract Booking_Start (contains date and time info)
        booking_match = re.search(r'Booking_Start=(\d{8}T\d{6})', url, re.IGNORECASE)
        booking_start = booking_match.group(1) if booking_match else None
        
        # Extract default start time from Booking_Start
        default_time = None
        if booking_start:
            time_part = booking_start.split('T')[1] if 'T' in booking_start else None
            if time_part:
                default_time = time_part
        
        if resource_guid and club_guid:
            return {
                'resource_guid': resource_guid,
                'club_guid': club_guid,
                'booking_start': booking_start,
                'default_time': default_time,
                'full_url': url
            }
        
        return None
        
    except Exception as e:
        console.print(f"[red]Error parsing URL: {e}[/red]")
        return None

def parse_multiple_urls(urls_input: str) -> List[Dict[str, str]]:
    """Parse multiple URLs (comma-separated or line-separated)."""
    # Split by comma or newline
    urls = []
    
    # First try comma separation
    if ',' in urls_input:
        urls = [url.strip() for url in urls_input.split(',') if url.strip()]
    else:
        # Try line separation
        urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
    
    parsed_clubs = []
    
    for i, url in enumerate(urls):
        if not url.startswith('http'):
            continue
            
        parsed = parse_golfbox_url(url)
        if parsed:
            parsed['index'] = i
            parsed_clubs.append(parsed)
        else:
            console.print(f"[yellow]Could not parse URL {i+1}[/yellow]")
    
    return parsed_clubs

def display_parsed_clubs(parsed_clubs: List[Dict[str, str]], club_names: List[str] = None):
    """Display parsed clubs in a nice table."""
    if not parsed_clubs:
        console.print("❌ No valid URLs parsed.", style="red")
        return
    
    console.print(f"✅ Parsed {len(parsed_clubs)} golf club URLs:", style="bold green")
    
    table = Table(
        title="Parsed Golf Club URLs",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold green"
    )
    
    table.add_column("#", justify="center", width=3)
    table.add_column("Club Name", style="bold cyan", width=20)
    table.add_column("Resource GUID", style="yellow", width=36)
    table.add_column("Club GUID", style="white", width=36)
    table.add_column("Default Time", justify="center", width=12)
    
    for i, club in enumerate(parsed_clubs):
        club_name = club_names[i] if club_names and i < len(club_names) else f"Club {i+1}"
        default_time = club.get('default_time', 'Unknown')
        if default_time and len(default_time) == 6:
            # Format HHMMSS to HH:MM:SS
            formatted_time = f"{default_time[:2]}:{default_time[2:4]}:{default_time[4:6]}"
        else:
            formatted_time = default_time or "Unknown"
        
        table.add_row(
            str(i+1),
            club_name,
            club['resource_guid'],
            club['club_guid'],
            formatted_time
        )
    
    console.print(table)

def generate_python_mapping(parsed_clubs: List[Dict[str, str]], club_names: List[str] = None) -> str:
    """Generate Python code to update the golf_club_urls.py mapping."""
    
    if not parsed_clubs:
        return ""
    
    code = "# Updated golf club mappings - add these to golf_club_urls.py\n\n"
    code += "# Add to the GolfClubURLManager.__init__ method:\n\n"
    
    for i, club in enumerate(parsed_clubs):
        club_name = club_names[i] if club_names and i < len(club_names) else f"club_{i+1}"
        
        # Generate a key from club name
        key = club_name.lower().replace(' ', '_').replace('æ', 'ae').replace('ø', 'o').replace('å', 'aa')
        key = re.sub(r'[^a-z0-9_]', '', key)
        
        default_time = club.get('default_time', '070000')
        
        code += f'            "{key}": GolfClubURL(\n'
        code += f'                name="{key}",\n'
        code += f'                display_name="{club_name}",\n'
        code += f'                resource_guid="{club["resource_guid"]}",\n'
        code += f'                club_guid="{club["club_guid"]}",\n'
        code += f'                base_url_template="{key}_template",\n'
        code += f'                default_start_time="{default_time}",\n'
        code += f'                location=None  # Add coordinates if known\n'
        code += f'            ),\n'
    
    return code

def interactive_url_parser():
    """Interactive URL parser."""
    console.print("🔗 GolfBox URL Parser & Mapping Updater", style="bold blue")
    console.print("=" * 60, style="blue")
    
    console.print("\n📋 Instructions:", style="bold yellow")
    console.print("1. Paste your GolfBox URLs (comma-separated or one per line)")
    console.print("2. Optionally provide club names (comma-separated)")
    console.print("3. I'll extract the GUIDs and generate the mapping code")
    
    # Get URLs
    console.print(f"\n🔗 Paste your GolfBox URLs:", style="bold green")
    urls_input = input().strip()
    
    if not urls_input:
        console.print("❌ No URLs provided.", style="red")
        return
    
    # Parse URLs
    parsed_clubs = parse_multiple_urls(urls_input)
    
    if not parsed_clubs:
        console.print("❌ No valid URLs could be parsed.", style="red")
        return
    
    # Get club names
    console.print(f"\n🏌️ Provide club names (optional, comma-separated):", style="bold green")
    console.print(f"   Found {len(parsed_clubs)} URLs - provide {len(parsed_clubs)} names or leave empty")
    names_input = input().strip()
    
    club_names = None
    if names_input:
        club_names = [name.strip() for name in names_input.split(',')]
        if len(club_names) != len(parsed_clubs):
            console.print(f"⚠️ Name count mismatch. Expected {len(parsed_clubs)}, got {len(club_names)}", style="yellow")
            club_names = None
    
    # Display results
    display_parsed_clubs(parsed_clubs, club_names)
    
    # Generate mapping code
    mapping_code = generate_python_mapping(parsed_clubs, club_names)
    
    console.print(f"\n🐍 Generated Python Mapping Code:", style="bold green")
    console.print("=" * 60, style="green")
    console.print(mapping_code, style="dim")
    
    # Save to file
    from rich.prompt import Confirm
    if Confirm.ask("💾 Save mapping code to file?"):
        filename = "new_club_mappings.py"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(mapping_code)
        console.print(f"✅ Saved to {filename}", style="bold green")
        console.print("📋 Copy the code from this file into golf_club_urls.py", style="cyan")

if __name__ == "__main__":
    interactive_url_parser()
