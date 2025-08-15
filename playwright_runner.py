#!/usr/bin/env python3
"""Playwright-based local tee-time checker for GolfBox legacy grid URLs.

Architecture:
 - Runner (CLI): loads .env, constants, starts async loop with graceful shutdown
 - Browser Controller: launches Chromium (headless by default), persists storage state
 - Auth Manager: detects login, fills credentials if provided, or lets user login once
 - Target Navigator: directly visits configured grid URL(s) each cycle
 - Scraper/Parser: detects 'Ledig/Available' cells and extracts HH:MM times
 - Change Detector: only reports newly discovered times per URL during this run
 - Scheduler: async loop every CHECK_INTERVAL_SECONDS with small jitter
 - Notifier: console output by default, optional Windows/macOS popups
"""

import asyncio
import argparse
import json
import os
import random
import re
import signal
import sys
import datetime
import platform
import subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from typing import Dict, List, Set, Tuple, Optional

from dotenv import load_dotenv
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich import box

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


console = Console()
# ------------------------------ Debug helper ------------------------------ #

def _dbg(message: str, enabled: bool) -> None:
    if enabled:
        try:
            console.print(message, style="dim")
        except Exception:
            pass

def _course_from_label(label: str, url: str) -> str:
    if label and " · " in label:
        return label.split(" · ", 1)[0].strip()
    try:
        return urlparse(url).netloc or "Course"
    except Exception:
        return "Course"

def _format_min(mins: int) -> str:
    mins = max(0, min(24 * 60 - 1, int(mins)))
    h, m = divmod(mins, 60)
    return f"{h:02d}:{m:02d}"



# --------------------------- Config & Constants --------------------------- #

ROOT_DIR = Path(__file__).parent.resolve()
STATE_PATH = ROOT_DIR / "state.json"
DEBUG_DIR = ROOT_DIR / "debug_html"


def load_config():
    # Force-refresh .env each start; prefer .env over existing shell vars
    try:
        # Do not override shell env; shell overrides take precedence over .env
        load_dotenv(dotenv_path=ROOT_DIR / ".env", override=False)
    except Exception:
        load_dotenv()
    grid_urls_csv = os.getenv("GOLFBOX_GRID_URL", "").strip()
    # Accept commas or newlines as separators; do NOT split on spaces to preserve labels
    raw_parts = re.split(r"[,;\n\r\t]+", grid_urls_csv) if grid_urls_csv else []
    def _strip_quotes(s: str) -> str:
        s = s.strip()
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
        return s
    grid_urls = [_strip_quotes(u) for u in raw_parts if u.strip()]
    # Normalize URLs: add https:// if missing
    normalized_urls: List[str] = []
    for u in grid_urls:
        if not (u.startswith("http://") or u.startswith("https://")):
            normalized_urls.append(f"https://{u}")
        else:
            normalized_urls.append(u)
    # Optional labels aligned with GRID_URLS
    labels_csv = os.getenv("GRID_LABELS", "").strip()
    raw_labels = re.split(r"[,;\n\r]+", labels_csv) if labels_csv else []
    labels = [_strip_quotes(s) for s in raw_labels if s.strip()]
    return {
        "GOLFBOX_USER": os.getenv("GOLFBOX_USER", "").strip(),
        "GOLFBOX_PASS": os.getenv("GOLFBOX_PASS", "").strip(),
        "GRID_URLS": normalized_urls,
        "HEADLESS": os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes"),
        "CHECK_INTERVAL_SECONDS": int(os.getenv("CHECK_INTERVAL_SECONDS", "300")),
        "JITTER_SECONDS": int(os.getenv("JITTER_SECONDS", "20")),
        "PERSIST_NOTIFIED": os.getenv("PERSIST_NOTIFIED", "false").lower() in ("1", "true", "yes"),
        "DEBUG": os.getenv("DEBUG", "false").lower() in ("1", "true", "yes"),
        "NEXT_WEEKEND": os.getenv("NEXT_WEEKEND", "false").lower() in ("1", "true", "yes"),
        # Default time window 07:00–15:00 unless overridden via CLI
        "DEFAULT_START": os.getenv("DEFAULT_START", "07:00"),
        "DEFAULT_END": os.getenv("DEFAULT_END", "15:00"),
        "GRID_LABELS": labels,
        "TEE_CAPACITY": int(os.getenv("TEE_CAPACITY", "4")),
    }


# ------------------------------- Notifier -------------------------------- #

def send_notification(title: str, message: str) -> None:
    """Lightweight popup notifier for Windows/macOS; print fallback."""
    try:
        system = platform.system()
        if system == "Windows":
            try:
                from win10toast import ToastNotifier

                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=5, threaded=True)
                return
            except Exception:
                pass
        elif system == "Darwin":
            script = f"""
            display alert "{title}" message "{message}" giving up after 5
            """
            subprocess.run(["osascript", "-e", script], check=True)
            return
    except Exception:
        pass
    print(f"[ALERT] {title}: {message}")


# ------------------------------ HTML Parser ------------------------------ #

TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")
def _parse_hhmm(hhmm: str) -> Optional[int]:
    """Return minutes since midnight for 'HH:MM' or None."""
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", hhmm.strip())
    if not m:
        return None
    h = int(m.group(1))
    mi = int(m.group(2))
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return None
    return h * 60 + mi


def _apply_between_filter(times: Dict[str, List[str]], start_minute: int | None = None, end_minute: int | None = None) -> Dict[str, List[str]]:
    if start_minute is None or end_minute is None:
        return times
    filtered: Dict[str, List[str]] = {}
    for hhmm, slots in times.items():
        mins = _parse_hhmm(hhmm)
        if mins is None:
            # keep unparseable to avoid hiding useful data
            filtered[hhmm] = slots
            continue
        if start_minute <= mins < end_minute:
            filtered[hhmm] = slots
    return filtered


def parse_grid_html(html: str) -> Dict[str, List[str]]:
    """Parse legacy grid HTML → { 'HH:MM': ['Tee N', ...], ... }.

    Heuristics similar to the requests-based implementation; looks for cells that
    appear 'available' and associates them to a time label from the row header.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table") or soup

    header_labels: List[str] = []
    thead = table.find("thead") if table else None
    if thead:
        header_cells = thead.find_all(["th", "td"]) if thead else []
        for i, cell in enumerate(header_cells):
            text = cell.get_text(" ", strip=True)
            header_labels.append(text or f"Tee {i}")

    tee_times: Dict[str, List[str]] = {}

    def is_available_cell(cell) -> bool:
        classes = " ".join(cell.get("class", [])).lower()
        text = cell.get_text(" ", strip=True).lower()
        # Exclude explicitly non-full availability
        if any(k in classes for k in ["partfree", "partial", "full", "occupied", "taken"]):
            return False
        if any(k in text for k in ["partfree", "partial", "full", "occupied", "taken"]):
            return False
        if any(k in classes for k in ["ledig", "available", "free", "bookable", "open"]):
            return True
        if any(k in text for k in ["ledig", "available", "free", "bookable", "ledig tid", "åpen"]):
            return True
        a = cell.find(["a", "button"], string=True)
        if a and any(k in a.get_text(" ", strip=True).lower() for k in ["book", "bestill", "reserver", "reserve"]):
            return True
        return False

    tbody = table.find("tbody") if table else None
    row_iter = (tbody.find_all("tr") if tbody else table.find_all("tr")) if table else []
    for row_idx, row in enumerate(row_iter):
        cells = row.find_all(["th", "td"])
        if not cells:
            continue
        time_label = None
        first_text = cells[0].get_text(" ", strip=True) if cells else ""
        m = TIME_RE.search(first_text)
        if m:
            time_label = m.group(0)
        else:
            row_text = row.get_text(" ", strip=True)
            m2 = TIME_RE.search(row_text)
            if m2:
                time_label = m2.group(0)
        if not time_label:
            continue

        for col_idx, cell in enumerate(cells[1:], start=1):
            if not is_available_cell(cell):
                continue
            if header_labels and col_idx < len(header_labels):
                col_label = header_labels[col_idx]
            else:
                col_label = f"Tee {col_idx}"
            tee_times.setdefault(time_label, []).append(col_label)

    # If the table-based parser found nothing, try tile-based grids like:
    # <div id="row15col3" class="hour free"><div class="time">20:30</div> ...</div>
    if not tee_times:
        tile_times: Dict[str, List[str]] = {}
        tile_slots: Dict[str, int] = {}

        def extract_hhmm_from_iso(s: str) -> str | None:
            # Example: 20250815T203000 → 20:30
            m = re.search(r"T(\d{2})(\d{2})", s)
            if m:
                return f"{m.group(1)}:{m.group(2)}"
            return None

        # Only include fully free tiles (exclude partfree)
        tiles = soup.select(
            "div.hour.free, div.free.hour, .booking-slot.free, .time-slot.free"
        )
        full_tiles = soup.select("div.hour.full, div.full.hour, .booking-slot.full, .time-slot.full")
        for tile in tiles:
            # Prefer explicit nested time label
            time_text = None
            time_div = tile.find(class_=re.compile(r"\btime\b", re.I))
            if time_div:
                txt = time_div.get_text(" ", strip=True)
                m = TIME_RE.search(txt)
                if m:
                    time_text = m.group(0)

            # Fallback: parse from tile text
            if not time_text:
                m = TIME_RE.search(tile.get_text(" ", strip=True))
                if m:
                    time_text = m.group(0)

            # Fallback: parse from onclick ISO string
            if not time_text:
                onclick = tile.get("onclick") or ""
                parsed = extract_hhmm_from_iso(onclick)
                if parsed:
                    time_text = parsed

            if not time_text:
                continue

            # Column/slot label from id like row15col3 → Tee 3
            col_label = "Slot"
            tile_id = tile.get("id") or ""
            m = re.search(r"col(\d+)", tile_id)
            if m:
                col_label = f"Tee {m.group(1)}"

            tile_times.setdefault(time_text, []).append(col_label)

            # Capacity estimation: count seat icons inside .item
            try:
                item = tile.find(class_=re.compile(r"\bitem\b", re.I))
                icons = item.find_all("img") if item else []
                # If specific filenames encode occupancy, refine here; otherwise count imgs
                available_slots = len(icons) if icons else 1
                tile_slots[time_text] = tile_slots.get(time_text, 0) + available_slots
            except Exception:
                pass

        if tile_times:
            free_count = sum(len(v) for v in tile_times.values())
            part_count = len(soup.select("div.hour.partfree, div.partfree.hour, .booking-slot.partfree, .time-slot.partfree"))
            console.print(f"[dim]Tile-based free slots: {free_count} (partial tiles: {part_count}) · full tiles: {len(full_tiles)}[/dim]")
            # Attach capacity counts by appending "(N)" to labels if >1
            enhanced: Dict[str, List[str]] = {}
            for hhmm, labels in tile_times.items():
                n = tile_slots.get(hhmm)
                if n and n > 1:
                    enhanced[hhmm] = [f"{lbl} ({n})" for lbl in labels]
                else:
                    enhanced[hhmm] = labels
            return enhanced

    return tee_times


async def parse_by_aria(page: Page, debug: bool = False) -> Dict[str, List[str]]:
    """Scan elements whose aria-label includes availability and extract HH:MM.

    Returns a dict plus logs debug samples to the console.
    """
    results: Dict[str, List[str]] = {}
    candidates = page.locator("[aria-label*='ledig' i], [aria-label*='available' i], [aria-label*='free' i]")
    # Still run ARIA scan silently; no status print
    count = await candidates.count()
    for i in range(count):
        label = (await candidates.nth(i).get_attribute("aria-label")) or ""
        m = TIME_RE.search(label)
        if not m:
            continue
        hhmm = m.group(0)
        results.setdefault(hhmm, []).append("Tee")
    return results


# --------------------------- Browser Orchestration ------------------------ #

async def ensure_context(browser: Browser) -> BrowserContext:
    if STATE_PATH.exists():
        context = await browser.new_context(storage_state=str(STATE_PATH))
    else:
        context = await browser.new_context()
    return context


async def maybe_login(page: Page, user: str, password: str) -> bool:
    """Attempt to detect a login screen and sign in. Returns True if logged in.

    If no credentials provided, returns False and lets user do it manually.
    """
    try:
        # Try to accept cookie banners that can block UI
        try:
            for sel in [
                "button:has-text('Godta')",
                "button:has-text('Aksepter')",
                "button:has-text('Accept')",
                "#onetrust-accept-btn-handler",
            ]:
                if await page.locator(sel).count():
                    await page.locator(sel).first.click()
                    await asyncio.sleep(0.2)
        except Exception:
            pass

        # If there's a visible login trigger, click it
        try:
            for sel in [
                "a:has-text('Logg inn')",
                "button:has-text('Logg inn')",
                "a:has-text('Login')",
                "button:has-text('Login')",
                "a[href*='login']",
                "button[href*='login']",
            ]:
                if await page.locator(sel).count():
                    await page.locator(sel).first.click()
                    try:
                        await page.wait_for_load_state('networkidle', timeout=8000)
                    except Exception:
                        pass
                    break
        except Exception:
            pass

        # Heuristic: look for a password field on the current page (wait a bit)
        try:
            await page.wait_for_selector("input[type='password'], input[name='password'], #password", timeout=5000)
        except Exception:
            pass
        has_password = await page.locator("input[type='password']").count() > 0 or await page.locator("#password").count() > 0
        at_login_url = "login" in page.url.lower() or "signin" in page.url.lower() or "auth" in page.url.lower()
        if not (has_password or at_login_url):
            # Also search iframes for a login form
            try:
                for frame in page.frames:
                    if await frame.locator("input[type='password'], #password").count() > 0:
                        has_password = True
                        break
            except Exception:
                pass
            if not has_password:
                return False

        if not user or not password:
            console.print("[yellow]Login page detected but credentials not provided. Please login manually once.[/yellow]")
            return False

        # Try common selectors (incl. two-step flows)
        email_selectors = [
            "input[type='email']",
            "input[name='email']",
            "input[name*='user' i]",
            "input[name='username']",
            "#username",
            "input[placeholder*='mail' i]",
            "input[placeholder*='e-post' i]",
            "input[id='i0116']",  # Microsoft AAD style
        ]
        pass_selectors = [
            "input[type='password']",
            "input[name*='pass' i]",
            "#password",
            "input[id='i0118']",  # Microsoft AAD style
        ]
        login_button_selectors = [
            "button[type='submit']",
            "button:has-text('Login')",
            "button:has-text('Logg inn')",
            "button:has-text('Logg på')",
            "input[type='submit']",
            "a:has-text('Sign in')",
        ]
        next_button_selectors = [
            "button:has-text('Neste')",
            "button:has-text('Next')",
            "button:has-text('Fortsett')",
            "input[type='submit']",
        ]

        filled = False
        # Try fill on main page
        for sel in email_selectors:
            if await page.locator(sel).count():
                await page.fill(sel, user)
                filled = True
                # Support two-step: click Next to reveal password
                for nb in next_button_selectors:
                    if await page.locator(nb).count():
                        await page.locator(nb).first.click()
                        try:
                            await page.wait_for_load_state("networkidle", timeout=8000)
                        except Exception:
                            pass
                break
        for sel in pass_selectors:
            if await page.locator(sel).count():
                await page.fill(sel, password)
                filled = True
                break
        # If not found, try within iframes
        if not filled:
            try:
                for frame in page.frames:
                    for sel in email_selectors:
                        if await frame.locator(sel).count():
                            await frame.fill(sel, user)
                            filled = True
                            for nb in next_button_selectors:
                                if await frame.locator(nb).count():
                                    await frame.locator(nb).first.click()
                                    try:
                                        await frame.wait_for_load_state("networkidle", timeout=8000)
                                    except Exception:
                                        pass
                            break
                    for sel in pass_selectors:
                        if await frame.locator(sel).count():
                            await frame.fill(sel, password)
                            filled = True
                            break
                    if filled:
                        page = frame  # submit within this frame
                        break
            except Exception:
                pass
        if filled:
            # Click a login/submit button if present; otherwise press Enter
            clicked = False
            for sel in login_button_selectors:
                if await page.locator(sel).count():
                    await page.locator(sel).first.click()
                    clicked = True
                    break
            if not clicked:
                await page.keyboard.press("Enter")

            # Wait a bit for navigation/content
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            # Heuristic: check if we're no longer on a login page
            try:
                login_markers = ["logg inn", "login", "sign in"]
                page_text = (await page.content()).lower()
                if not any(m in page_text for m in login_markers):
                    return True
            except Exception:
                return True
    except Exception:
        return False
    return False


async def save_storage_state(context: BrowserContext) -> None:
    try:
        await context.storage_state(path=str(STATE_PATH))
    except Exception:
        pass


async def fetch_times_for_url(context: BrowserContext, url: str, debug: bool = False, assume_logged_in: bool = False) -> Dict[str, List[str]]:
    page = await context.new_page()
    try:
        # 1) Optionally visit app to refresh/validate session
        user = os.getenv("GOLFBOX_USER", "").strip()
        password = os.getenv("GOLFBOX_PASS", "").strip()
        if not assume_logged_in:
            app_url = "https://golfbox.golf/#/"
            try:
                await page.goto(app_url, wait_until="domcontentloaded")
                _dbg("Loaded golfbox.golf app", debug)
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
            except Exception:
                pass

            # Attempt login if the app shows a login form
            _dbg("Checking for login…", debug)
            logged = await maybe_login(page, user, password)
            if logged:
                await save_storage_state(context)
                _dbg("Login successful, storage state saved", debug)

        # 2) Navigate to the legacy grid target
        _dbg(f"Navigating to grid: {url}", debug)
        await page.goto(url, wait_until="domcontentloaded")
        # Wait for grid to render (either table grid or tile grid)
        try:
            await page.wait_for_selector("div.hour, table", timeout=10000)
            _dbg("Grid DOM detected", debug)
        except Exception:
            pass

        # If redirected to a login page during grid navigation, try again then retry target
        redirected_login = await maybe_login(page, user, password)
        if redirected_login:
            await save_storage_state(context)
            _dbg("Redirected to login; re-visiting grid", debug)
            await page.goto(url, wait_until="domcontentloaded")
            try:
                await page.wait_for_selector("div.hour, table", timeout=10000)
            except Exception:
                pass

        # Attempt parsing by ARIA first
        _dbg("Parsing ARIA…", debug)
        aria = await parse_by_aria(page, debug=debug)
        if aria:
            _dbg(f"ARIA found {sum(len(v) for v in aria.values())} slots", debug)
            return aria

        # Fallback to HTML heuristic parser
        _dbg("Falling back to HTML parse…", debug)
        html = await page.content()
        parsed = parse_grid_html(html)
        _dbg(f"HTML parse found {sum(len(v) for v in parsed.values())} slots", debug)

        if debug:
            try:
                DEBUG_DIR.mkdir(exist_ok=True)
                date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                with open(DEBUG_DIR / f"grid-{date_str}.html", "w", encoding="utf-8") as f:
                    f.write(html)
                await page.screenshot(path=str(DEBUG_DIR / f"grid-{date_str}.png"))
            except Exception:
                pass

        return parsed
    finally:
        try:
            await page.close()
        except Exception:
            pass


async def navigate_to_starttidsbestilling(page: Page) -> bool:
    """From the app home, click 'Bestill starttid' / 'Starttidsbestilling' (or English).

    Returns True if we believe we navigated to a booking grid page.
    """
    selectors = [
        "a:has-text('Bestill starttid')",
        "button:has-text('Bestill starttid')",
        "a:has-text('Starttidsbestilling')",
        "button:has-text('Starttidsbestilling')",
        "a:has-text('Book tee time')",
        "button:has-text('Book tee time')",
        "a:has-text('Bestill')",
        "button:has-text('Bestill')",
        "a:has-text('Booking')",
        "button:has-text('Booking')",
    ]

    # Some UIs hide the action in a menu; try opening any clearly visible burger
    try:
        menu_candidates = ["button[aria-label*='menu' i]", "button:has-text('Meny')", "button:has-text('Menu')"]
        for sel in menu_candidates:
            if await page.locator(sel).count():
                await page.locator(sel).first.click()
                await asyncio.sleep(0.2)
    except Exception:
        pass

    for sel in selectors:
        try:
            if await page.locator(sel).count():
                await page.locator(sel).first.click()
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
                # Heuristic: booking grid tends to be on golfbox.no with grid.asp in path
                url = page.url.lower()
                if ("golfbox.no" in url and "grid.asp" in url) or "ressources/booking" in url:
                    return True
        except Exception:
            continue
    return False


async def fetch_times_via_app(context: BrowserContext, debug: bool = False) -> tuple[Dict[str, List[str]], str]:
    """Open app → maybe login → click 'Bestill starttid' → parse grid → return (times, final_url)."""
    page = await context.new_page()
    final_url = ""
    try:
        app_url = "https://golfbox.golf/#/"
        await page.goto(app_url, wait_until="domcontentloaded")
        _dbg("Loaded golfbox.golf app", debug)
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass

        user = os.getenv("GOLFBOX_USER", "").strip()
        password = os.getenv("GOLFBOX_PASS", "").strip()
        _dbg("Checking for login…", debug)
        logged = await maybe_login(page, user, password)
        if logged:
            await save_storage_state(context)
            _dbg("Login successful, storage state saved", debug)

        # Navigate to booking grid
        _dbg("Navigating to Starttidsbestilling…", debug)
        went = await navigate_to_starttidsbestilling(page)
        if not went:
            # Try once more after a small delay (UI might be loading)
            await asyncio.sleep(0.5)
            went = await navigate_to_starttidsbestilling(page)
        if not went:
            return {}, final_url

        final_url = page.url

        # Parse with ARIA first
        _dbg("Parsing ARIA…", debug)
        aria = await parse_by_aria(page, debug=debug)
        if aria:
            return aria, final_url

        # Fallback to HTML parse
        _dbg("Falling back to HTML parse…", debug)
        html = await page.content()
        parsed = parse_grid_html(html)
        # Optional debug heading
        if debug:
            try:
                h1 = await page.locator("h1, h2").first.text_content()
                console.print(f"[dim]Page heading:[/dim] {h1}")
            except Exception:
                pass

        if debug:
            try:
                DEBUG_DIR.mkdir(exist_ok=True)
                date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                with open(DEBUG_DIR / f"grid-{date_str}.html", "w", encoding="utf-8") as f:
                    f.write(html)
                await page.screenshot(path=str(DEBUG_DIR / f"grid-{date_str}.png"))
            except Exception:
                pass

        return parsed, final_url
    finally:
        try:
            await page.close()
        except Exception:
            pass


# ------------------------------- Scheduler ------------------------------- #

class ChangeDetector:
    def __init__(self, persist: bool = False):
        self._seen: Dict[str, Set[str]] = {}
        self._persist = persist
        self._path = ROOT_DIR / "notified.json"
        if self._persist and self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._seen = {k: set(v) for k, v in data.items()}
            except Exception:
                self._seen = {}

    def diff_new(self, url: str, tee_times: Dict[str, List[str]]) -> List[str]:
        new_items: List[str] = []
        seen = self._seen.setdefault(url, set())
        for hhmm, slots in tee_times.items():
            for slot in slots:
                key = f"{hhmm}||{slot}"
                if key not in seen:
                    new_items.append(key)
                    seen.add(key)
        if self._persist:
            try:
                serializable = {k: sorted(list(v)) for k, v in self._seen.items()}
                self._path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
        return new_items


def _rewrite_url_for_day(u: str, day: datetime.date) -> str:
    """Rewrite common date params to target day while preserving time if present.

    - Booking_Start=YYYYMMDDTHHMMSS → replace date part, keep time
    - date/dato/resdate/selectedDate=YYYY-MM-DD → set to target
    """
    try:
        parsed = urlparse(u)
        qs = dict(parse_qsl(parsed.query))
        # Booking_Start
        if "Booking_Start" in qs and re.search(r"T\d{6}$", qs["Booking_Start"]):
            time_part = qs["Booking_Start"].split("T", 1)[1]
            qs["Booking_Start"] = f"{day.strftime('%Y%m%d')}T{time_part}"
        # Generic date keys
        date_keys = ["date", "dato", "resdate", "selectedDate"]
        for k in date_keys:
            if k in qs:
                qs[k] = day.strftime("%Y-%m-%d")
        new_query = urlencode(qs)
        return urlunparse((parsed.scheme or "https", parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    except Exception:
        return u


async def run_loop(grid_urls: List[str], headless: bool, check_interval: int, jitter_seconds: int, persist_notified: bool, debug: bool = False, grid_labels: Optional[List[str]] = None) -> None:
    """Main monitoring loop.

    between_minutes: optional (start_minute, end_minute) window applied to parsed tee times.
    """
    use_app_navigation = len(grid_urls) == 0
    if use_app_navigation:
        console.print("No grid URL provided. Will navigate via app → 'Bestill starttid'.", style="yellow")

    detector = ChangeDetector(persist=persist_notified)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await ensure_context(browser)
        console.print(f"Chromium launched (headless={headless}). Checking {len(grid_urls)} URL(s).", style="green")
        # Pre-run summary
        try:
            start_h = globals().get("_APPLY_START_MIN", 0)
            end_h = globals().get("_APPLY_END_MIN", 24*60)
            time_win = f"{_format_min(start_h)}–{_format_min(end_h)}"
        except Exception:
            time_win = "(all day)"
        if not use_app_navigation:
            clubs = []
            for idx, u in enumerate(grid_urls):
                label = (grid_labels or [])[idx] if grid_labels and idx < len(grid_labels) else _course_from_label("", u)
                clubs.append(label)
            console.print(f"Clubs: {', '.join(clubs)}", style="blue")
        console.print(f"Time window: {time_win}", style="blue")

        stop = asyncio.Event()

        def _graceful(*_):
            stop.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _graceful)
            except NotImplementedError:
                # Windows with ProactorEventLoop may not support it; rely on KeyboardInterrupt
                pass

        while not stop.is_set():
            cycle_start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            console.print(f"\n⛳ Cycle start {cycle_start}", style="bold blue")

            if use_app_navigation:
                try:
                    console.print("Checking via app navigation …", style="dim")
                    times, final_url = await fetch_times_via_app(context, debug=debug)
                    url_key = final_url or "app://starttidsbestilling"

                    table = Table(title=f"Booking: {url_key}", box=box.SIMPLE, show_header=True, header_style="bold")
                    table.add_column("Tee Time", style="cyan")
                    table.add_column("Slots", style="white")
                    # Apply optional time filter
                    try:
                        times = _apply_between_filter(times, _APPLY_START_MIN, _APPLY_END_MIN)
                    except NameError:
                        pass
                    if not times:
                        table.add_row("", "[dim]No available tee times[/dim]")
                    else:
                        for hhmm in sorted(times.keys()):
                            table.add_row(hhmm, ", ".join(times[hhmm]))
                    console.print(table)

                    new_items = detector.diff_new(url_key, times)
                    if new_items:
                        preview = "; ".join(sorted({ni.split("||")[0] for ni in new_items}))
                        send_notification("⛳ New tee times", f"{preview}")
                        console.print(f"[green]New openings:[/green] {', '.join(new_items)}")
                except Exception as e:
                    console.print(f"[red]App navigation failed:[/red] {e}")
            else:
                # If NEXT_WEEKEND is set, rewrite URLs for upcoming Saturday and Sunday
                cfg_next_weekend = os.getenv("NEXT_WEEKEND", "false").lower() in ("1", "true", "yes")
                urls_to_check: List[tuple[str, str, str]] = []  # (url, label, base_url)
                if cfg_next_weekend:
                    today = datetime.date.today()
                    # Next Saturday
                    days_until_sat = (5 - today.weekday()) % 7
                    saturday = today + datetime.timedelta(days=days_until_sat or 7)
                    sunday = saturday + datetime.timedelta(days=1)

                    for idx, base in enumerate(grid_urls):
                        course_label = (grid_labels or [])[idx] if grid_labels and idx < len(grid_labels) else ""
                        url_sat = _rewrite_url_for_day(base, saturday)
                        url_sun = _rewrite_url_for_day(base, sunday)
                        urls_to_check.append((url_sat, f"{course_label + ' · ' if course_label else ''}Saturday {saturday}", base))
                        urls_to_check.append((url_sun, f"{course_label + ' · ' if course_label else ''}Sunday {sunday}", base))
                else:
                    for idx, u in enumerate(grid_urls):
                        course_label = (grid_labels or [])[idx] if grid_labels and idx < len(grid_labels) else ""
                        urls_to_check.append((u, course_label, u))

                # Login once per cycle on the first URL, then reuse state for the rest
                for idx, (url, label, base_url) in enumerate(urls_to_check):
                    try:
                        # Derive course name priority: provided label aligns with base index
                        base_index = grid_urls.index(base_url) if base_url in grid_urls else idx
                        provided_label = (grid_labels or [])[base_index] if grid_labels and base_index < len(grid_labels) else ""
                        course_name = provided_label or _course_from_label(label, url)
                        console.print(f"Checking {course_name or url} …", style="dim")
                        times = await fetch_times_for_url(context, url, debug=debug, assume_logged_in=(idx > 0))
                        # Apply optional time filter
                        try:
                            times = _apply_between_filter(times, _APPLY_START_MIN, _APPLY_END_MIN)
                        except NameError:
                            pass
                        # Pretty output: Course | Day | Tee Time
                        def split_course_and_day(lbl: str, url_text: str) -> tuple[str, str]:
                            if lbl and " · " in lbl:
                                a, b = lbl.split(" · ", 1)
                                return a.strip(), b.strip()
                            return (lbl.strip() if lbl else (urlparse(url_text).netloc or "Course"), "-")

                        course_name, day_str = split_course_and_day(label or course_name, url)
                        table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
                        table.add_column("Course", style="magenta")
                        table.add_column("Day", style="cyan")
                        table.add_column("Tee Time", style="white")
                        if not times:
                            table.add_row(course_name, day_str, "No tee times found :'(")
                        else:
                            # Print each tee time as we iterate for more granular feedback
                            for hhmm in sorted(times.keys()):
                                table.add_row(course_name, day_str, hhmm)
                                _dbg(f"Found time: {course_name} | {day_str} | {hhmm}", debug)
                        console.print(table)

                        key = f"{base_url}||{course_name}||{day_str}" if day_str else f"{base_url}||{course_name}"
                        new_items = detector.diff_new(key, times)
                        if new_items:
                            # Only times (optionally with capacity), comma-separated
                            preview = ", ".join(sorted({ni.split("||")[0] for ni in new_items}))
                            send_notification("⛳ New tee times", preview)
                            console.print(f"[green]New openings:[/green] {', '.join(new_items)}")
                    except Exception as e:
                        console.print(f"[red]Failed to check URL:[/red] {url} → {e}")

            # Save state at end of cycle
            await save_storage_state(context)

            # Sleep with jitter
            jitter = random.randint(-max(0, jitter_seconds // 2), jitter_seconds)
            wait = max(5, check_interval + jitter)
            next_ts = (datetime.datetime.now() + datetime.timedelta(seconds=wait)).strftime("%H:%M:%S")
            console.print(f"⏰ Next check in {wait}s (at {next_ts})", style="dim")

            try:
                await asyncio.wait_for(stop.wait(), timeout=wait)
            except asyncio.TimeoutError:
                pass

        # Cleanup
        try:
            await save_storage_state(context)
            await context.close()
            await browser.close()
        except Exception:
            pass


def main() -> None:
    cfg = load_config()

    # CLI: --between HH:MM-HH:MM to override default window
    parser = argparse.ArgumentParser(description="GolfBox Playwright runner")
    parser.add_argument("--between", type=str, default=None, help="Filter times within HH:MM-HH:MM (default 07:00-15:00)")
    args, _ = parser.parse_known_args()

    # Resolve between window
    default_start = cfg["DEFAULT_START"]
    default_end = cfg["DEFAULT_END"]
    if args.between:
        try:
            start_s, end_s = args.between.replace(" ", "").split("-", 1)
        except ValueError:
            console.print("[red]--between must be HH:MM-HH:MM[/red]")
            return
    else:
        start_s, end_s = default_start, default_end

    start_min = _parse_hhmm(start_s) or 0
    end_min = _parse_hhmm(end_s) or 24 * 60

    # Stash chosen window in a global closure for _apply_between_filter
    global _APPLY_START_MIN, _APPLY_END_MIN
    _APPLY_START_MIN = start_min
    _APPLY_END_MIN = end_min
    if not cfg["GRID_URLS"]:
        console.print("Set `GOLFBOX_GRID_URL` in .env (one or comma-separated legacy grid URL(s)).", style="yellow")
    console.print("Playwright runner starting. Press Ctrl+C to stop.", style="blue")

    try:
        asyncio.run(
            run_loop(
                grid_urls=cfg["GRID_URLS"],
                headless=cfg["HEADLESS"],
                check_interval=cfg["CHECK_INTERVAL_SECONDS"],
                jitter_seconds=cfg["JITTER_SECONDS"],
                persist_notified=cfg["PERSIST_NOTIFIED"],
                debug=cfg["DEBUG"],
                grid_labels=cfg.get("GRID_LABELS"),
            )
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()


