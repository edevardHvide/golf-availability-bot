#!/usr/bin/env python3
import asyncio
import datetime
import os
import re
from playwright.async_api import async_playwright
from golfbot.grid_parser import parse_grid_html

def parse_capacity_from_label(label: str) -> int:
    # Label format now is: "N spots available" or "1 spot available"
    m = re.match(r"\s*(\d+)\s+spot", label.strip(), re.I)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return 0

async def main():
    print("Testing Grini GK capacity parsing...")
    
    # Grini GK URL for tomorrow
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y%m%d")
    
    # Grini GK URL (using the GUID from your config)
    url = f"https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={{1BEE50FC-669C-4383-A47E-5354F7AC08EC}}&Club_GUID=EE00C492-7F02-4C2C-851B-8CDDC89181DB&Booking_Start={tomorrow_str}T070000"
    
    print(f"Testing Grini GK for {tomorrow} (tomorrow)")
    print(f"Opening URL: {url}")
    print("Browser will open - login manually if needed")
    
    async with async_playwright() as pw:
        print("Launching browser (headless=False)...")
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            print("First, opening golfbox.golf for login...")
            await page.goto("https://golfbox.golf/#/", wait_until="domcontentloaded")
            print("Golfbox.golf loaded!")
            
            print("Please login to golfbox.golf if needed...")
            input("Press Enter after you've logged in and are ready to navigate to the grid...")
            
            print(f"Now navigating to Grini GK grid...")
            print(f"URL: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            print("Grid page loaded!")
            
            # Wait for grid to appear
            print("Waiting for booking grid to appear...")
            try:
                await page.wait_for_selector("div.hour, table", timeout=30000)  # 30 seconds
                print("Grid found!")
            except:
                print("No grid detected, but continuing...")
            
            input("Press Enter when ready to extract HTML and parse all times...")
            
            # Get HTML
            html = await page.content()
            
            # Save HTML for analysis
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            html_path = f"debug_html/grini-test-{timestamp}.html"
            os.makedirs("debug_html", exist_ok=True)
            
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"HTML saved: {html_path}")
            
            # Take screenshot for reference
            screenshot_path = f"debug_html/grini-test-{timestamp}.png"
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot saved: {screenshot_path}")
            
            # Parse times using the fixed grid parser
            times = parse_grid_html(html)
            
            print(f"\n=== ALL PARSED TIMES FOR {tomorrow} ===")
            if not times:
                print("No times found!")
            else:
                for hhmm in sorted(times.keys()):
                    labels = times[hhmm]
                    print(f"  {hhmm}: {', '.join(labels)}")
                    
                    # Show capacity for each time
                    total_capacity = 0
                    for lbl in labels:
                        cap = parse_capacity_from_label(lbl)
                        total_capacity += cap
                    if total_capacity > 0:
                        print(f"    → Total capacity: {total_capacity}")
                
                print(f"\nTotal unique times found: {len(times)}")
                
                # Check specific time if requested
                target_time = os.getenv("TEST_HHMM", "06:30")
                if target_time in times:
                    labels = times[target_time]
                    capacity = sum(parse_capacity_from_label(lbl) for lbl in labels)
                    print(f"\nSpecific check for {target_time}: {capacity} spots available")
                    
                    expected = os.getenv("EXPECT_CAPACITY")
                    if expected:
                        expected_cap = int(expected)
                        result = "PASS" if capacity == expected_cap else "FAIL"
                        print(f"Assertion: capacity == {expected_cap} → {result}")
                else:
                    print(f"\nTime {target_time} not found in results")
            
            print(f"\nHTML analysis file: {html_path}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())