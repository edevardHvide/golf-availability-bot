#!/usr/bin/env python3
"""Golf Club URL Mapping System for GolfBox Integration."""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, date
import re

@dataclass
class GolfClubURL:
    """Golf club with GolfBox URL information."""
    name: str
    display_name: str
    resource_guid: str
    club_guid: str
    base_url_template: str
    default_start_time: str = "070000"  # 07:00:00
    location: Optional[Tuple[float, float]] = None  # (lat, lng)
    
    def get_url_for_date(self, target_date: date, start_time: str = None) -> str:
        """Generate GolfBox URL for specific date and time."""
        if start_time is None:
            start_time = self.default_start_time
        
        date_str = target_date.strftime("%Y%m%d")
        booking_start = f"{date_str}T{start_time}"
        
        return (f"https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?"
                f"Ressource_GUID={{{self.resource_guid}}}&"
                f"Club_GUID={self.club_guid}&"
                f"Booking_Start={booking_start}")


class GolfClubURLManager:
    """Manages golf club URLs and mappings."""
    
    def __init__(self):
        # Based on your existing URLs and labels
        self.clubs = {
            "oslo_golfklubb": GolfClubURL(
                name="oslo_golfklubb",
                display_name="Oslo Golfklubb",
                resource_guid="8034D31E-F798-4EA4-8475-D9F869AA217F",
                club_guid="5C6BDC3C-3D0A-43D0-B4A7-DCC2E9F8B454",
                base_url_template="oslo_template",
                default_start_time="073000",  # 07:30:00
                location=(59.9493, 10.6343)
            ),
            "haga_gk": GolfClubURL(
                name="haga_gk", 
                display_name="Haga GK",
                resource_guid="E95F6988-C683-43F8-919C-7F835DBFAF27",
                club_guid="E0105CD4-744F-4323-9B70-426E833E2EE6",
                base_url_template="haga_template",
                default_start_time="073000",  # 07:30:00
                location=(59.2839, 11.1097)
            ),
            "grini_gk": GolfClubURL(
                name="grini_gk",
                display_name="Grini GK", 
                resource_guid="1BEE50FC-669C-4383-A47E-5354F7AC08EC",
                club_guid="EE00C492-7F02-4C2C-851B-8CDDC89181DB",
                base_url_template="grini_template",
                default_start_time="070000",  # 07:00:00
                location=(60.2167, 10.4167)
            ),
            "baerum_gk": GolfClubURL(
                name="baerum_gk",
                display_name="Bærum GK",
                resource_guid="8BA75266-8EF6-49CA-BD9E-30468D3FF6DC", 
                club_guid="340DE8DC-D776-475E-AB12-32C742E70B49",
                base_url_template="baerum_template",
                default_start_time="060000",  # 06:00:00
                location=(59.8939, 10.5236)
            ),
            "miklagard_gk": GolfClubURL(
                name="miklagard_gk",
                display_name="Miklagard GK",
                resource_guid="76FDC7B8-EB17-4C65-94DB-5A3BF156FC45",
                club_guid="E26F8BF9-1D66-4A2A-A6EA-65763E379DA9", 
                base_url_template="miklagard_template",
                default_start_time="070000",  # 07:00:00
                location=(59.9695, 11.0358)
            ),
            "hauger_gk": GolfClubURL(
                name="hauger_gk",
                display_name="Hauger GK",
                resource_guid="9AB90FB6-5954-4BF9-BEC9-FC50867CC324",
                club_guid="FEE57961-2559-4E30-BDB6-7C9B8367CA5F",
                base_url_template="hauger_template", 
                default_start_time="070000",  # 07:00:00
                location=(59.2675, 10.4078)
            ),
            "drobak_bk": GolfClubURL(
                name="drobak_bk",
                display_name="Drøbak BK",
                resource_guid="A2804229-985A-484F-A19F-BDDBA6FB2A55",
                club_guid="608E1A63-A10E-4C54-B3C8-D53FA9A087F4",
                base_url_template="drobak_template",
                default_start_time="000000",  # 00:00:00 (midnight start)
                location=(59.6597, 10.6306)
            ),
            "onsoy_gk": GolfClubURL(
                name="onsoy_gk", 
                display_name="Onsøy GK",
                resource_guid="884D570B-7F66-4ECD-88E2-215E3B386422",
                club_guid="A85DA1E0-B469-4702-BDBC-4E8972EC50A9",
                base_url_template="onsoy_template",
                default_start_time="070000",  # 07:00:00
                location=(59.2181, 10.9298)
            ),
            "tyrifjord_gk": GolfClubURL(
                name="tyrifjord_gk",
                display_name="Tyrifjord GK", 
                resource_guid="4F6C5CA4-0E11-4982-9CED-FC75A608B8BD",
                club_guid="31F8375C-430B-461C-A98E-D3659A8CD836",
                base_url_template="tyrifjord_template",
                default_start_time="070000",  # 07:00:00
                location=(59.9667, 9.9833)
            ),
            "oppegard_gk": GolfClubURL(
                name="oppegard_gk",
                display_name="Oppegård GK",
                resource_guid="4B1D1E06-B945-4F97-8955-37BF3DC261F2", 
                club_guid="10FD393E-4608-4CCA-825D-E41245EFA260",
                base_url_template="oppegard_template",
                default_start_time="070000",  # 07:00:00
                location=(59.7833, 10.7833)
            ),
            
            # New clubs added from URL parsing
            "asker_golfklubb": GolfClubURL(
                name="asker_golfklubb",
                display_name="Asker Golfklubb",
                resource_guid="6DDA6B72-66C5-4A9A-BF6C-FDBE08599317",
                club_guid="38219782-908C-4602-87D5-282049EB5A09",
                base_url_template="asker_golfklubb_template",
                default_start_time="070000",
                location=(59.8378, 10.4358)  # Asker location
            ),
            "askim_golfklubb": GolfClubURL(
                name="askim_golfklubb",
                display_name="Askim Golfklubb",
                resource_guid="858D7A9B-9E24-471D-928E-AAE156DC82B0",
                club_guid="D61B48DA-B190-4A8D-AB88-EC820EE03536",
                base_url_template="askim_golfklubb_template",
                default_start_time="070000",
                location=(59.5833, 11.1667)  # Askim location
            ),
            "ballerud_golfklubb": GolfClubURL(
                name="ballerud_golfklubb",
                display_name="Ballerud Golfklubb",
                resource_guid="82966715-948D-41EB-BCAB-3F7458EDB82E",
                club_guid="FD174477-19BD-4120-BD4F-DF422371C961",
                base_url_template="ballerud_golfklubb_template",
                default_start_time="070000",
                location=(59.9167, 10.4833)  # Ballerud location
            ),
            "borre_golfklubb": GolfClubURL(
                name="borre_golfklubb",
                display_name="Borre Golfklubb",
                resource_guid="55138E91-DA52-4D34-8396-B9A06156868E",
                club_guid="353891C0-DEA9-4AFB-B35B-E4DA63C20B44",
                base_url_template="borre_golfklubb_template",
                default_start_time="090000",  # 09:00:00 start
                location=(59.4167, 10.4333)  # Borre location
            ),
            "borregaard_golfklubb": GolfClubURL(
                name="borregaard_golfklubb",
                display_name="Borregaard Golfklubb",
                resource_guid="408E9F31-A0A4-44EE-8A9E-FAD1CA7D6A57",
                club_guid="12C3A03E-951B-4BBC-9A6C-B2FEF75D6D05",
                base_url_template="borregaard_golfklubb_template",
                default_start_time="070000",
                location=(59.2167, 11.1667)  # Sarpsborg area
            ),
            "gersjoen_golfklubb": GolfClubURL(
                name="gersjoen_golfklubb",
                display_name="Gersjøen Golfklubb",
                resource_guid="41F8CCDD-AF5B-42ED-8796-F408A472E95C",
                club_guid="1E4427C3-5055-45A3-B147-046189FC61E5",
                base_url_template="gersjoen_golfklubb_template",
                default_start_time="070000",
                location=(59.8833, 10.8167)  # Gersjøen location
            ),
            "grenland_og_omegn_golfklubb": GolfClubURL(
                name="grenland_og_omegn_golfklubb",
                display_name="Grenland og Omegn Golfklubb",
                resource_guid="D3D00C92-8A47-4656-BB51-0AC0679D14F4",
                club_guid="E107EF6A-B3E0-486F-9BC7-5E21108DC3A8",
                base_url_template="grenland_og_omegn_golfklubb_template",
                default_start_time="063000",  # 06:30:00 start
                location=(59.1667, 9.6667)  # Grenland area
            ),
            "groruddalen_golfklubb": GolfClubURL(
                name="groruddalen_golfklubb",
                display_name="Groruddalen Golfklubb",
                resource_guid="ADDA65B0-1513-4AE9-8FD0-B52D372175DD",
                club_guid="90DB15A5-1265-4C5D-BD34-4414259D98BD",
                base_url_template="groruddalen_golfklubb_template",
                default_start_time="070000",
                location=(59.9667, 10.8833)  # Groruddalen location
            ),
            "gronmo_golfklubb": GolfClubURL(
                name="gronmo_golfklubb",
                display_name="Grønmo Golfklubb",
                resource_guid="721B0378-4C6E-4125-A33C-A98423F5F196",
                club_guid="B13984B1-DE27-4DCE-968C-F850C890C427",
                base_url_template="gronmo_golfklubb_template",
                default_start_time="060000",  # 06:00:00 start
                location=(59.8167, 10.7667)  # Grønmo location
            ),
            "kongsberg_golfklubb": GolfClubURL(
                name="kongsberg_golfklubb",
                display_name="Kongsberg Golfklubb",
                resource_guid="028C89E4-D112-4159-BAD3-F54DE71BCDB8",
                club_guid="370101F2-E253-4D63-A8CD-0CFE25E3F31B",
                base_url_template="kongsberg_golfklubb_template",
                default_start_time="060000",  # 06:00:00 start
                location=(59.6667, 9.6500)  # Kongsberg location
            ),
            
            # Additional clubs - second batch
            "losby_golfklubb": GolfClubURL(
                name="losby_golfklubb",
                display_name="Losby Golfklubb",
                resource_guid="3C44C599-4A4C-40D9-8AF7-9F3CDB9EDD7F",
                club_guid="90FA30D3-FF9D-4C3E-92C9-115B01A8D7BD",
                base_url_template="losby_golfklubb_template",
                default_start_time="070000",
                location=(59.9186, 10.9553)  # Lørenskog location
            ),
            "moss_og_rygge_golfklubb": GolfClubURL(
                name="moss_og_rygge_golfklubb",
                display_name="Moss & Rygge Golfklubb",
                resource_guid="D61EEF17-D1F1-43FC-9F3E-9C0BD6201A81",
                club_guid="D7C2237C-50B2-47E7-A3FB-1E860D3D37EC",
                base_url_template="moss_og_rygge_golfklubb_template",
                default_start_time="070000",
                location=(59.4358, 10.6628)  # Moss area location
            ),
            "notteroy_golfklubb": GolfClubURL(
                name="notteroy_golfklubb",
                display_name="Nøtterøy Golfklubb",
                resource_guid="D5851F1C-F54E-48D7-B38C-C0EEBE8D8EF6",
                club_guid="D6C93387-6D38-4EDA-A937-E995ADF6776D",
                base_url_template="notteroy_golfklubb_template",
                default_start_time="060000",  # 06:00:00 start
                location=(59.2167, 10.4167)  # Nøtterøy location
            ),
            "ostmarka_golfklubb": GolfClubURL(
                name="ostmarka_golfklubb",
                display_name="Østmarka Golfklubb",
                resource_guid="0A0D6D74-67AA-4319-BE2E-A9CDCFAD76BE",
                club_guid="11A0819E-6D9D-46E2-9585-01379C806AC2",
                base_url_template="ostmarka_golfklubb_template",
                default_start_time="070000",
                location=(59.8833, 10.9167)  # Østmarka location
            )
        }
        
        # Create reverse lookup mappings
        self.display_name_to_key = {club.display_name.lower(): key for key, club in self.clubs.items()}
        self.guid_to_key = {club.club_guid: key for key, club in self.clubs.items()}
    
    def get_club_by_name(self, name: str) -> Optional[GolfClubURL]:
        """Get club by name (flexible matching)."""
        name_lower = name.lower().strip()
        
        # Direct key match
        if name_lower in self.clubs:
            return self.clubs[name_lower]
        
        # Display name match
        if name_lower in self.display_name_to_key:
            return self.clubs[self.display_name_to_key[name_lower]]
        
        # Partial matching
        for key, club in self.clubs.items():
            if (name_lower in club.display_name.lower() or 
                name_lower in key or
                club.display_name.lower() in name_lower):
                return club
        
        return None
    
    def get_club_by_guid(self, club_guid: str) -> Optional[GolfClubURL]:
        """Get club by GUID."""
        if club_guid in self.guid_to_key:
            return self.clubs[self.guid_to_key[club_guid]]
        return None
    
    def get_all_clubs(self) -> List[GolfClubURL]:
        """Get all available clubs."""
        return list(self.clubs.values())
    
    def get_clubs_by_keys(self, keys: List[str]) -> List[GolfClubURL]:
        """Get clubs by list of keys."""
        clubs = []
        for key in keys:
            club = self.get_club_by_name(key)
            if club:
                clubs.append(club)
        return clubs
    
    def generate_urls_for_date(self, club_keys: List[str], target_date: date, 
                              start_time: str = None) -> Dict[str, str]:
        """Generate URLs for multiple clubs for a specific date."""
        urls = {}
        for key in club_keys:
            club = self.get_club_by_name(key)
            if club:
                urls[club.display_name] = club.get_url_for_date(target_date, start_time)
        return urls
    
    def generate_comma_separated_urls(self, club_keys: List[str], target_date: date,
                                     start_time: str = None) -> str:
        """Generate comma-separated URL string for configuration."""
        urls = []
        for key in club_keys:
            club = self.get_club_by_name(key)
            if club:
                urls.append(club.get_url_for_date(target_date, start_time))
        return ",".join(urls)
    
    def generate_labels_string(self, club_keys: List[str]) -> str:
        """Generate comma-separated labels string."""
        labels = []
        for key in club_keys:
            club = self.get_club_by_name(key)
            if club:
                labels.append(club.display_name)
        return ",".join(labels)
    
    def parse_existing_urls(self, url_string: str) -> List[str]:
        """Parse existing URL string to extract club keys."""
        urls = [url.strip() for url in url_string.split(",") if url.strip()]
        club_keys = []
        
        for url in urls:
            # Extract Club_GUID from URL
            match = re.search(r"Club_GUID=([A-F0-9-]+)", url)
            if match:
                guid = match.group(1)
                club = self.get_club_by_guid(guid)
                if club:
                    club_keys.append(club.name)
        
        return club_keys
    
    def get_mapping_table(self) -> str:
        """Get a formatted mapping table for documentation."""
        table = "Golf Club URL Mapping Table\n"
        table += "=" * 50 + "\n\n"
        
        for key, club in self.clubs.items():
            table += f"Club: {club.display_name}\n"
            table += f"Key: {key}\n"
            table += f"Resource GUID: {club.resource_guid}\n"
            table += f"Club GUID: {club.club_guid}\n"
            table += f"Default Start Time: {club.default_start_time}\n"
            if club.location:
                table += f"Location: {club.location[0]:.4f}, {club.location[1]:.4f}\n"
            table += f"Example URL: {club.get_url_for_date(date.today())}\n"
            table += "-" * 30 + "\n\n"
        
        return table


# Global instance
golf_url_manager = GolfClubURLManager()


def get_urls_for_clubs(club_names: List[str], target_date: date = None, 
                      start_time: str = None) -> Dict[str, str]:
    """Convenience function to get URLs for clubs."""
    if target_date is None:
        target_date = date.today()
    
    return golf_url_manager.generate_urls_for_date(club_names, target_date, start_time)


def get_club_config_string(club_names: List[str], target_date: date = None,
                          start_time: str = None) -> Tuple[str, str]:
    """Get both URL and label strings for configuration."""
    if target_date is None:
        target_date = date.today()
    
    urls = golf_url_manager.generate_comma_separated_urls(club_names, target_date, start_time)
    labels = golf_url_manager.generate_labels_string(club_names)
    
    return urls, labels


if __name__ == "__main__":
    # Demo the mapping system
    from rich.console import Console
    from rich.table import Table
    from rich import box
    
    console = Console()
    manager = golf_url_manager
    
    console.print("🏌️ Golf Club URL Mapping System", style="bold blue")
    console.print("=" * 50, style="blue")
    
    # Create table
    table = Table(
        title="Available Golf Clubs",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold green"
    )
    
    table.add_column("Club Name", style="bold cyan", width=20)
    table.add_column("Key", style="yellow", width=15)
    table.add_column("Location", style="dim", width=15)
    table.add_column("Default Start", style="white", justify="center")
    
    for key, club in manager.clubs.items():
        location_str = f"{club.location[0]:.2f}, {club.location[1]:.2f}" if club.location else "N/A"
        start_time = f"{club.default_start_time[:2]}:{club.default_start_time[2:4]}"
        
        table.add_row(
            club.display_name,
            key,
            location_str,
            start_time
        )
    
    console.print(table)
    
    # Example usage
    console.print(f"\n📋 Example Configuration for Oslo area clubs:", style="bold green")
    oslo_clubs = ["oslo_golfklubb", "baerum_gk", "miklagard_gk"]
    urls, labels = get_club_config_string(oslo_clubs)
    
    console.print(f"\nGOLFBOX_GRID_URL={urls[:100]}...", style="cyan")
    console.print(f"GRID_LABELS={labels}", style="cyan")
