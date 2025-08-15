#!/usr/bin/env python3
"""Parse additional golf club URLs."""

import re

def parse_additional_clubs():
    urls_data = """
Losby Golfklubb: https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={3C44C599-4A4C-40D9-8AF7-9F3CDB9EDD7F}&Club_GUID=90FA30D3-FF9D-4C3E-92C9-115B01A8D7BD&Booking_Start=20250815T070000
Moss & Rygge Golfklubb: https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={D61EEF17-D1F1-43FC-9F3E-9C0BD6201A81}&Club_GUID=D7C2237C-50B2-47E7-A3FB-1E860D3D37EC&Booking_Start=20250815T070000
Nøtterøy Golfklubb: https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={D5851F1C-F54E-48D7-B38C-C0EEBE8D8EF6}&Club_GUID=D6C93387-6D38-4EDA-A937-E995ADF6776D&Booking_Start=20250815T060000
Østmarka Golfklubb: https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={0A0D6D74-67AA-4319-BE2E-A9CDCFAD76BE}&Club_GUID=11A0819E-6D9D-46E2-9585-01379C806AC2&Booking_Start=20250815T070000
"""

    clubs = []
    for line in urls_data.strip().split('\n'):
        if not line.strip():
            continue
        
        # Extract club name
        club_name = line.split(':')[0].strip()
        
        # Extract Resource GUID
        resource_match = re.search(r'Ressource_GUID=\{([A-F0-9-]+)\}', line)
        resource_guid = resource_match.group(1) if resource_match else None
        
        # Extract Club GUID
        club_match = re.search(r'Club_GUID=([A-F0-9-]+)', line)
        club_guid = club_match.group(1) if club_match else None
        
        # Extract start time
        time_match = re.search(r'Booking_Start=\d{8}T(\d{6})', line)
        start_time = time_match.group(1) if time_match else '070000'
        
        if resource_guid and club_guid:
            clubs.append({
                'name': club_name,
                'resource_guid': resource_guid,
                'club_guid': club_guid,
                'start_time': start_time
            })

    print('✅ Parsed Additional Golf Club URLs:')
    print('=' * 80)
    for i, club in enumerate(clubs, 1):
        key = club['name'].lower().replace(' ', '_').replace('æ', 'ae').replace('ø', 'o').replace('å', 'aa').replace('&', 'og')
        key = re.sub(r'[^a-z0-9_]', '', key)
        
        time_formatted = f"{club['start_time'][:2]}:{club['start_time'][2:4]}:{club['start_time'][4:6]}"
        
        print(f"{i:2d}. {club['name']:30} → {key:30} → {time_formatted}")
        print(f"    Resource: {club['resource_guid']}")
        print(f"    Club:     {club['club_guid']}")
        print()

    # Generate Python mapping code
    print("\n🐍 Python Mapping Code for golf_club_urls.py:")
    print("=" * 80)
    
    for club in clubs:
        key = club['name'].lower().replace(' ', '_').replace('æ', 'ae').replace('ø', 'o').replace('å', 'aa').replace('&', 'og')
        key = re.sub(r'[^a-z0-9_]', '', key)
        
        print(f'            "{key}": GolfClubURL(')
        print(f'                name="{key}",')
        print(f'                display_name="{club["name"]}",')
        print(f'                resource_guid="{club["resource_guid"]}",')
        print(f'                club_guid="{club["club_guid"]}",')
        print(f'                base_url_template="{key}_template",')
        print(f'                default_start_time="{club["start_time"]}",')
        print(f'                location=None  # Add coordinates if known')
        print(f'            ),')

if __name__ == "__main__":
    parse_additional_clubs()
