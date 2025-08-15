#!/usr/bin/env python3
"""Parse new golf club URLs."""

import re

def parse_clubs():
    urls_data = """
Asker Golfklubb: Ressource_GUID={6DDA6B72-66C5-4A9A-BF6C-FDBE08599317}&Club_GUID=38219782-908C-4602-87D5-282049EB5A09
Askim Golfklubb: https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={858D7A9B-9E24-471D-928E-AAE156DC82B0}&Club_GUID=D61B48DA-B190-4A8D-AB88-EC820EE03536&Booking_Start=20250815T070000
Ballerud Golfklubb: https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={82966715-948D-41EB-BCAB-3F7458EDB82E}&Club_GUID=FD174477-19BD-4120-BD4F-DF422371C961&Booking_Start=20250815T070000
Borre Golfklubb: https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={55138E91-DA52-4D34-8396-B9A06156868E}&Club_GUID=353891C0-DEA9-4AFB-B35B-E4DA63C20B44&Booking_Start=20250815T090000
Borregaard Golfklubb: https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={408E9F31-A0A4-44EE-8A9E-FAD1CA7D6A57}&Club_GUID=12C3A03E-951B-4BBC-9A6C-B2FEF75D6D05&Booking_Start=20250815T070000
Gersjøen Golfklubb: https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={41F8CCDD-AF5B-42ED-8796-F408A472E95C}&Club_GUID=1E4427C3-5055-45A3-B147-046189FC61E5&Booking_Start=20250815T070000
Grenland og Omegn Golfklubb: https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={D3D00C92-8A47-4656-BB51-0AC0679D14F4}&Club_GUID=E107EF6A-B3E0-486F-9BC7-5E21108DC3A8&Booking_Start=20250815T063000
Groruddalen Golfklubb: https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={ADDA65B0-1513-4AE9-8FD0-B52D372175DD}&Club_GUID=90DB15A5-1265-4C5D-BD34-4414259D98BD&Booking_Start=20250815T070000
Grønmo Golfklubb: https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={721B0378-4C6E-4125-A33C-A98423F5F196}&Club_GUID=B13984B1-DE27-4DCE-968C-F850C890C427&Booking_Start=20250815T060000
Kongsberg Golfklubb: https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={028C89E4-D112-4159-BAD3-F54DE71BCDB8}&Club_GUID=370101F2-E253-4D63-A8CD-0CFE25E3F31B&Booking_Start=20250815T060000
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

    print('✅ Parsed Golf Club URLs:')
    print('=' * 80)
    for i, club in enumerate(clubs, 1):
        key = club['name'].lower().replace(' ', '_').replace('æ', 'ae').replace('ø', 'o').replace('å', 'aa')
        key = re.sub(r'[^a-z0-9_]', '', key)
        
        time_formatted = f"{club['start_time'][:2]}:{club['start_time'][2:4]}:{club['start_time'][4:6]}"
        
        print(f"{i:2d}. {club['name']:30} → {key:30} → {time_formatted}")
        print(f"    Resource: {club['resource_guid']}")
        print(f"    Club:     {club['club_guid']}")
        print()

    # Generate Python mapping code
    print("\n🐍 Python Mapping Code for golf_club_urls.py:")
    print("=" * 80)
    print("# Add these to the GolfClubURLManager.__init__ method:")
    print()
    
    for club in clubs:
        key = club['name'].lower().replace(' ', '_').replace('æ', 'ae').replace('ø', 'o').replace('å', 'aa')
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
        print()

if __name__ == "__main__":
    parse_clubs()
