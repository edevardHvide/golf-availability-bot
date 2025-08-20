from __future__ import annotations

import asyncio
import os
from typing import List, Dict

from rich.console import Console

from playwright.async_api import async_playwright

from golfbot.grid_parser import parse_grid_html


console = Console()


async def fetch_once(url: str, headless: bool = True, debug: bool = False) -> Dict[str, List[str]]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        try:
            await page.wait_for_selector("div.hour, table", timeout=8000)
        except Exception:
            pass
        # Try ARIA first
        aria = await page.locator("[aria-label*='ledig' i], [aria-label*='available' i], [aria-label*='free' i]").all_text_contents()
        if aria:
            # If ARIA present, naive time extraction fallback
            import re as _re
            results: Dict[str, List[str]] = {}
            for t in aria:
                m = _re.search(r"\b\d{1,2}:\d{2}\b", t or "")
                if not m:
                    continue
                results.setdefault(m.group(0), []).append("Tee")
            await browser.close()
            return results
        html = await page.content()
        results = parse_grid_html(html)
        await browser.close()
        return results


def main() -> None:
    url = os.getenv("GOLFBOX_GRID_URL", "").strip()
    if not url:
        console.print("Set GOLFBOX_GRID_URL to a legacy grid URL.")
        return
    debug = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
    headless = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")
    results = asyncio.run(fetch_once(url, headless=headless, debug=debug))
    if not results:
        console.print("No available tee times found.")
        return
    for hhmm in sorted(results.keys()):
        console.print(f"{hhmm}: {', '.join(results[hhmm])}")


if __name__ == "__main__":
    main()


