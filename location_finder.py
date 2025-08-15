#!/usr/bin/env python3
"""Golf club location finder - find clubs within driving distance."""

import requests
import json
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import os
from rich.console import Console
from rich.table import Table
from rich import box
from golf_club_urls import golf_url_manager, get_club_config_string

console = Console()

@dataclass
class GolfClub:
    """Golf club with location information."""
    name: str
    address: str
    latitude: float
    longitude: float
    distance_km: float
    drive_time_minutes: Optional[int] = None
    golfbox_key: Optional[str] = None

class GolfClubLocationFinder:
    """Find golf clubs within driving distance using various APIs."""
    
    def __init__(self):
        self.geolocator = Nominatim(user_agent="golf-availability-bot")
        
        # Load golf clubs from URL manager (includes GolfBox URLs)
        self.norwegian_golf_clubs = {}
        
        # Convert from golf_url_manager to our format
        for club in golf_url_manager.get_all_clubs():
            key = club.display_name.lower()
            self.norwegian_golf_clubs[key] = {
                "address": f"{club.display_name} Area, Norway",  # Generic address
                "lat": club.location[0] if club.location else 59.9139,
                "lng": club.location[1] if club.location else 10.7522,
                "golfbox_key": club.name,
                "display_name": club.display_name,
                "resource_guid": club.resource_guid,
                "club_guid": club.club_guid
            }
        
        # Add additional clubs not in URL manager
        additional_clubs = {
            "bogstad golfklubb": {
                "address": "Sørkedalen, Oslo, Norway",
                "lat": 59.9725, "lng": 10.6047,
                "golfbox_key": "bogstad golfklubb"
            },
            "losby gods": {
                "address": "Lørenskog, Norway",
                "lat": 59.9186, "lng": 10.9553,
                "golfbox_key": "losby gods"
            },
            "holtsmark golfklubb": {
                "address": "Holtsmark, Drammen, Norway",
                "lat": 59.7439, "lng": 10.1731,
                "golfbox_key": "holtsmark golfklubb"
            },
            "bjaavann golfklubb": {
                "address": "Grorud, Oslo, Norway",
                "lat": 59.9567, "lng": 10.8789,
                "golfbox_key": "bjaavann golfklubb"
            },
            "drammen golfklubb": {
                "address": "Drammen, Norway",
                "lat": 59.7436, "lng": 10.2045,
                "golfbox_key": "drammen golfklubb"
            },
            "asker golfklubb": {
                "address": "Asker, Norway",
                "lat": 59.8378, "lng": 10.4358,
                "golfbox_key": "asker golfklubb"
            },
            "vestfold golfklubb": {
                "address": "Sandefjord, Norway",
                "lat": 59.1319, "lng": 10.2167,
                "golfbox_key": "vestfold golfklubb"
            },
            "moss golfklubb": {
                "address": "Moss, Norway",
                "lat": 59.4358, "lng": 10.6628,
                "golfbox_key": "moss golfklubb"
            }
        }
        
        # Add additional clubs to our database
        self.norwegian_golf_clubs.update(additional_clubs)
    
    def geocode_location(self, location: str) -> Optional[Tuple[float, float]]:
        """Geocode a location string to coordinates."""
        try:
            location_obj = self.geolocator.geocode(location, timeout=10)
            if location_obj:
                return (location_obj.latitude, location_obj.longitude)
            return None
        except Exception as e:
            console.print(f"[red]Geocoding error: {e}[/red]")
            return None
    
    def calculate_driving_time_osrm(self, start_coords: Tuple[float, float], 
                                   end_coords: Tuple[float, float]) -> Optional[int]:
        """Calculate driving time using OSRM (Open Source Routing Machine)."""
        try:
            start_lng, start_lat = start_coords[1], start_coords[0]
            end_lng, end_lat = end_coords[1], end_coords[0]
            
            url = f"http://router.project-osrm.org/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}?overview=false"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("routes"):
                    duration_seconds = data["routes"][0]["duration"]
                    return int(duration_seconds / 60)  # Convert to minutes
            
            return None
        except Exception as e:
            console.print(f"[dim red]OSRM routing error: {e}[/dim red]")
            return None
    
    def calculate_driving_time_google(self, start_coords: Tuple[float, float], 
                                     end_coords: Tuple[float, float]) -> Optional[int]:
        """Calculate driving time using Google Maps API (requires API key)."""
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            return None
        
        try:
            start_str = f"{start_coords[0]},{start_coords[1]}"
            end_str = f"{end_coords[0]},{end_coords[1]}"
            
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": start_str,
                "destination": end_str,
                "mode": "driving",
                "key": api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("routes") and data["routes"][0].get("legs"):
                    duration_seconds = data["routes"][0]["legs"][0]["duration"]["value"]
                    return int(duration_seconds / 60)  # Convert to minutes
            
            return None
        except Exception as e:
            console.print(f"[dim red]Google Maps API error: {e}[/dim red]")
            return None
    
    def find_clubs_within_radius(self, user_location: str, 
                                max_drive_minutes: int = 60) -> List[GolfClub]:
        """Find golf clubs within driving time from user location."""
        console.print(f"🔍 Finding golf clubs within {max_drive_minutes} minutes of {user_location}...")
        
        # Geocode user location
        user_coords = self.geocode_location(user_location)
        if not user_coords:
            console.print(f"[red]Could not find coordinates for: {user_location}[/red]")
            return []
        
        console.print(f"📍 Your location: {user_coords[0]:.4f}, {user_coords[1]:.4f}")
        
        nearby_clubs = []
        
        for club_name, club_info in self.norwegian_golf_clubs.items():
            club_coords = (club_info["lat"], club_info["lng"])
            
            # Calculate straight-line distance first (quick filter)
            distance_km = geodesic(user_coords, club_coords).kilometers
            
            # Skip clubs that are too far even in straight line (rough filter)
            if distance_km > max_drive_minutes * 1.5:  # Assume ~90km/h average speed
                continue
            
            # Calculate actual driving time
            drive_time = None
            
            # Try OSRM first (free)
            drive_time = self.calculate_driving_time_osrm(user_coords, club_coords)
            
            # Fallback to Google Maps if available
            if drive_time is None:
                drive_time = self.calculate_driving_time_google(user_coords, club_coords)
            
            # If no driving time available, estimate based on straight-line distance
            if drive_time is None:
                # Rough estimate: straight-line distance * 1.3 / 60km/h average speed
                drive_time = int((distance_km * 1.3) / 60 * 60)
            
            # Only include clubs within the time limit
            if drive_time <= max_drive_minutes:
                club = GolfClub(
                    name=club_name.title(),
                    address=club_info["address"],
                    latitude=club_info["lat"],
                    longitude=club_info["lng"],
                    distance_km=round(distance_km, 1),
                    drive_time_minutes=drive_time,
                    golfbox_key=club_info["golfbox_key"]
                )
                nearby_clubs.append(club)
            
            # Add small delay to be respectful to APIs
            time.sleep(0.1)
        
        # Sort by driving time
        nearby_clubs.sort(key=lambda x: x.drive_time_minutes or 999)
        
        return nearby_clubs
    
    def display_nearby_clubs(self, clubs: List[GolfClub]) -> None:
        """Display nearby clubs in a nice table."""
        if not clubs:
            console.print("❌ No golf clubs found within your specified range.", style="yellow")
            return
        
        table = Table(
            title=f"🏌️ Golf Clubs Within Range ({len(clubs)} found)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold green"
        )
        
        table.add_column("Golf Club", style="bold cyan", width=25)
        table.add_column("Drive Time", style="white", justify="center")
        table.add_column("Distance", style="dim", justify="center") 
        table.add_column("Location", style="dim", width=30)
        
        for club in clubs:
            drive_time_str = f"{club.drive_time_minutes} min" if club.drive_time_minutes else "~"
            distance_str = f"{club.distance_km} km"
            
            table.add_row(
                club.name,
                drive_time_str,
                distance_str,
                club.address
            )
        
        console.print(table)
    
    def generate_club_config(self, clubs: List[GolfClub]) -> str:
        """Generate configuration string for selected clubs."""
        if not clubs:
            return ""
        
        club_keys = [club.golfbox_key for club in clubs if club.golfbox_key]
        return ",".join(club_keys)


def find_nearby_golf_clubs(location: str, max_drive_minutes: int = 60) -> List[GolfClub]:
    """Main function to find nearby golf clubs."""
    finder = GolfClubLocationFinder()
    return finder.find_clubs_within_radius(location, max_drive_minutes)


def interactive_club_finder():
    """Interactive function to find and select golf clubs."""
    console.print("🏌️ Golf Club Location Finder", style="bold blue")
    console.print("=" * 50, style="blue")
    
    # Get user location
    location = input("\n📍 Enter your location (address, city, or coordinates): ").strip()
    if not location:
        console.print("❌ No location provided.", style="red")
        return
    
    # Get driving time preference
    try:
        max_minutes = input("⏰ Maximum driving time in minutes (default: 60): ").strip()
        max_minutes = int(max_minutes) if max_minutes else 60
    except ValueError:
        max_minutes = 60
    
    # Find clubs
    finder = GolfClubLocationFinder()
    clubs = finder.find_clubs_within_radius(location, max_minutes)
    
    # Display results
    finder.display_nearby_clubs(clubs)
    
    if clubs:
        console.print(f"\n📋 Configuration for .env file:", style="bold green")
        config_str = finder.generate_club_config(clubs)
        console.print(f"SELECTED_CLUBS={config_str}", style="cyan")
        
        # Save to file option
        save_config = input("\n💾 Save configuration to file? (y/n): ").strip().lower()
        if save_config == 'y':
            with open("nearby_clubs_config.txt", "w") as f:
                f.write(f"# Golf clubs within {max_minutes} minutes of {location}\n")
                f.write(f"SELECTED_CLUBS={config_str}\n\n")
                f.write("# Individual club details:\n")
                for club in clubs:
                    f.write(f"# {club.name}: {club.drive_time_minutes} min, {club.distance_km} km\n")
            
            console.print("✅ Configuration saved to nearby_clubs_config.txt", style="green")


if __name__ == "__main__":
    # Example usage
    interactive_club_finder()
    