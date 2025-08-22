#!/usr/bin/env python3
import asyncio
import datetime
import os
from playwright.async_api import async_playwright
from golfbot.grid_parser import parse_grid_html

async def main():
    print("Starting simple test...")
    
    # Use a direct URL - replace with your actual Grini URL
    url = "https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?Ressource_GUID={1BEE50FC-669C-4383-A47E-5354F7AC08EC}&Club_GUID=EE00C492-7F02-4C2C-851B-8CDDC89181DB&Booking_Start=20250817T070000"
    
    print(f"Opening URL: {url}")
    print("Browser will open - login manually if needed")
    
    async with async_playwright() as pw:
        print("Launching browser (headless=False)...")
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            print("Navigating to page...")
            await page.goto(url, wait_until="domcontentloaded")
            print("Page loaded!")
            
            # Wait for grid or give user time to login
            print("Waiting for grid to appear...")
            try:
                await page.wait_for_selector("div.hour, table", timeout=30000)
                print("Grid found!")
            except:
                print("No grid detected, but continuing...")
            
            input("Press Enter to extract HTML and parse times...")
            
            # Get HTML
            html = await page.content()
            
            # Save HTML
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            html_path = f"debug_html/simple-test-{timestamp}.html"
            os.makedirs("debug_html", exist_ok=True)
            
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"HTML saved: {html_path}")
            
            # Parse times
            times = parse_grid_html(html)
            
            print("\n=== PARSED TIMES ===")
            if not times:
                print("No times found!")
            else:
                for hhmm in sorted(times.keys()):
                    print(f"{hhmm}: {', '.join(times[hhmm])}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
