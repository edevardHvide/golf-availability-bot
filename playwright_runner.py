#!/usr/bin/env python3
"""
Playwright-based Golf Availability Runner

This runner uses Playwright to directly navigate to GolfBox legacy grid URLs
and monitor for available tee times. It persists login sessions and provides
real-time monitoring with desktop notifications.
"""

import os
import sys
import asyncio
import json
import random
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from dotenv import load_dotenv
from rich.console import Console
from playwright.async_api import async_playwright, BrowserContext, Page

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from golfbot.grid_parser import parse_grid_html
from golf_utils import send_desktop_notification

# Load environment variables
load_dotenv()

console = Console()


class PlaywrightRunner:
    """Main Playwright-based runner for golf availability monitoring."""
    
    def __init__(self):
        self.grid_urls = self._parse_grid_urls()
        self.username = os.getenv("GOLFBOX_USER", "")
        self.password = os.getenv("GOLFBOX_PASS", "")
        self.headless = os.getenv("HEADLESS", "true").lower() == "true"
        self.check_interval = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
        self.jitter_seconds = int(os.getenv("JITTER_SECONDS", "20"))
        self.persist_notified = os.getenv("PERSIST_NOTIFIED", "false").lower() == "true"
        self.state_file = Path("state.json")
        self.debug_dir = Path("debug_html")
        self.previous_availability = {}
        
        # Create debug directory if it doesn't exist
        self.debug_dir.mkdir(exist_ok=True)
        
    def _parse_grid_urls(self) -> List[str]:
        """Parse grid URLs from environment variable."""
        urls_str = os.getenv("GOLFBOX_GRID_URL", "").strip()
        if not urls_str:
            console.print("❌ No GOLFBOX_GRID_URL found in environment variables", style="red")
            console.print("Please set GOLFBOX_GRID_URL in your .env file", style="yellow")
            return []
        
        # Split by comma and clean up
        urls = [url.strip() for url in urls_str.split(",") if url.strip()]
        console.print(f"📋 Found {len(urls)} grid URL(s) to monitor", style="cyan")
        return urls
    
    async def save_state(self, context: BrowserContext):
        """Save browser state to file."""
        try:
            state = await context.storage_state()
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            console.print("💾 Browser state saved", style="dim")
        except Exception as e:
            console.print(f"⚠️ Failed to save state: {e}", style="yellow")
    
    async def load_state(self, context: BrowserContext) -> bool:
        """Load browser state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                await context.add_cookies(state.get('cookies', []))
                console.print("📂 Browser state loaded", style="dim")
                return True
        except Exception as e:
            console.print(f"⚠️ Failed to load state: {e}", style="yellow")
        return False
    
    async def attempt_login(self, page: Page) -> bool:
        """Attempt to login if credentials are provided."""
        if not (self.username and self.password):
            console.print("🔐 No credentials provided, manual login may be required", style="yellow")
            return False
        
        try:
            # Look for login form elements
            username_field = await page.query_selector('input[type="email"], input[name*="email"], input[name*="user"]')
            password_field = await page.query_selector('input[type="password"]')
            
            if username_field and password_field:
                console.print("🔑 Login form detected, attempting automatic login...", style="cyan")
                await username_field.fill(self.username)
                await password_field.fill(self.password)
                
                # Look for login button
                login_button = await page.query_selector('button[type="submit"], input[type="submit"], button:has-text("Log"), button:has-text("Sign")')
                if login_button:
                    await login_button.click()
                    await page.wait_for_load_state("networkidle")
                    console.print("✅ Login attempted", style="green")
                    return True
            
        except Exception as e:
            console.print(f"❌ Login failed: {e}", style="red")
        
        return False
    
    async def fetch_availability(self, page: Page, url: str) -> Dict[str, List[str]]:
        """Fetch availability from a grid URL."""
        try:
            console.print(f"🌐 Fetching: {url[:80]}...", style="dim")
            await page.goto(url, wait_until="domcontentloaded")
            
            # Wait for content to load
            try:
                await page.wait_for_selector("div.hour, table, .grid", timeout=8000)
            except:
                pass  # Continue even if selector not found
            
            # Try ARIA-based detection first (more reliable)
            aria_elements = await page.locator("[aria-label*='ledig' i], [aria-label*='available' i], [aria-label*='free' i]").all()
            if aria_elements:
                console.print(f"🎯 Found {len(aria_elements)} ARIA-labeled available slots", style="green")
                results = {}
                for element in aria_elements:
                    text = await element.text_content()
                    if text:
                        # Extract time from text
                        import re
                        time_match = re.search(r'\b\d{1,2}:\d{2}\b', text)
                        if time_match:
                            time_slot = time_match.group(0)
                            results.setdefault(time_slot, []).append("Available")
                return results
            
            # Fallback to HTML parsing
            html = await page.content()
            results = parse_grid_html(html)
            
            # Save debug info if enabled
            if not self.headless:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_file = self.debug_dir / f"debug_{timestamp}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                
                # Take screenshot
                screenshot_file = self.debug_dir / f"screenshot_{timestamp}.png"
                await page.screenshot(path=str(screenshot_file))
            
            return results
            
        except Exception as e:
            console.print(f"❌ Error fetching {url}: {e}", style="red")
            return {}
    
    def check_for_new_availability(self, current: Dict[str, List[str]], url: str) -> List[str]:
        """Check for new availability compared to previous state."""
        previous = self.previous_availability.get(url, {})
        new_slots = []
        
        for time_slot, types in current.items():
            prev_types = previous.get(time_slot, [])
            if len(types) > len(prev_types):  # More availability than before
                new_slots.append(f"{time_slot} ({len(types)} slots)")
        
        return new_slots
    
    def send_notification(self, new_slots: List[str], url: str):
        """Send desktop notification for new availability."""
        if not new_slots:
            return
        
        title = "🏌️ New Golf Availability!"
        message = f"Found {len(new_slots)} new tee times:\n" + "\n".join(new_slots[:5])
        if len(new_slots) > 5:
            message += f"\n... and {len(new_slots) - 5} more"
        
        send_desktop_notification(title, message)
        console.print(f"🔔 Notification sent: {len(new_slots)} new slots", style="green bold")
    
    async def run_monitoring_cycle(self, browser_context: BrowserContext):
        """Run one monitoring cycle for all URLs."""
        page = await browser_context.new_page()
        
        try:
            for url in self.grid_urls:
                current_availability = await self.fetch_availability(page, url)
                
                if current_availability:
                    console.print(f"✅ Found {sum(len(slots) for slots in current_availability.values())} total slots", style="green")
                    
                    # Check for new availability
                    new_slots = self.check_for_new_availability(current_availability, url)
                    if new_slots:
                        self.send_notification(new_slots, url)
                    else:
                        console.print("📋 No new availability detected", style="dim")
                    
                    # Update previous state
                    self.previous_availability[url] = current_availability
                else:
                    console.print("❌ No availability found", style="yellow")
                
                # Small delay between URLs
                if len(self.grid_urls) > 1:
                    await asyncio.sleep(2)
        
        finally:
            await page.close()
    
    async def run(self):
        """Main monitoring loop."""
        if not self.grid_urls:
            console.print("❌ No grid URLs configured. Exiting.", style="red")
            return
        
        console.print("🚀 Starting Playwright-based Golf Availability Monitor", style="cyan bold")
        console.print(f"📊 Monitoring {len(self.grid_urls)} URL(s) every {self.check_interval}s", style="cyan")
        console.print(f"🎭 Headless mode: {self.headless}", style="cyan")
        
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            
            try:
                # Load previous state
                await self.load_state(context)
                
                # Create a page for initial setup
                page = await context.new_page()
                
                # Navigate to first URL to check if login is needed
                if self.grid_urls:
                    await page.goto(self.grid_urls[0])
                    
                    # Check if login is needed and attempt if credentials provided
                    if "login" in page.url.lower() or await page.query_selector('input[type="password"]'):
                        login_success = await self.attempt_login(page)
                        if not login_success and not self.headless:
                            console.print("🔐 Please log in manually in the browser window", style="yellow")
                            await page.wait_for_load_state("networkidle")
                        
                        # Save state after login
                        await self.save_state(context)
                
                await page.close()
                
                # Main monitoring loop
                cycle = 0
                while True:
                    cycle += 1
                    console.print(f"\n🔄 Cycle {cycle} - {datetime.now().strftime('%H:%M:%S')}")
                    
                    await self.run_monitoring_cycle(context)
                    
                    # Calculate sleep time with jitter
                    jitter = random.randint(-self.jitter_seconds, self.jitter_seconds)
                    sleep_time = max(30, self.check_interval + jitter)  # Minimum 30 seconds
                    
                    console.print(f"😴 Sleeping for {sleep_time} seconds...", style="dim")
                    await asyncio.sleep(sleep_time)
            
            finally:
                await browser.close()


def main():
    """Main entry point."""
    runner = PlaywrightRunner()
    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        console.print("\n👋 Monitoring stopped by user", style="yellow")
    except Exception as e:
        console.print(f"💥 Unexpected error: {e}", style="red")
        raise


if __name__ == "__main__":
    main()
