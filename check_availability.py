#!/usr/bin/env python3
"""Golf Course Availability Monitor for golfbox.golf facilities."""

import argparse
import datetime
import os
import re
import subprocess
import time
import platform

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

from facilities import facilities
from golfbot.core.availability import fetch_available_tee_times as fetch_available_tee_times_core
from golfbot.scraping.requests_client import (
    ensure_session as _ensure_session_http,
    login_to_golfbox as _login_to_golfbox_http,
    apply_manual_cookies as _apply_manual_cookies_http,
)

# Bridge aliases to keep existing function names used below
_ensure_session = _ensure_session_http
login_to_golfbox = _login_to_golfbox_http
_apply_manual_cookies = _apply_manual_cookies_http

# Initialize rich console
console = Console()


def send_notification(title, message):
    """Send a visual alert popup (Windows/macOS)."""
    try:
        system = platform.system()

        if system == "Windows":
            # Use Windows toast notifications
            try:
                from win10toast import ToastNotifier

                toaster = ToastNotifier()
                # duration is seconds; threaded avoids blocking
                toaster.show_toast(title, message, duration=5, threaded=True)
                return
            except Exception as e:
                print(f"Failed to send Windows toast: {e}")
                # Fall through to console output

        elif system == "Darwin":
            # Use macOS AppleScript alert (no special permissions)
            script = f"""
            display alert "{title}" message "{message}" giving up after 5
            """
            subprocess.run(["osascript", "-e", script], check=True)
            return

        # For unsupported platforms or if notification fails, just print
        print(f"[ALERT] {title}: {message}")

    except subprocess.CalledProcessError as e:
        print(f"Failed to send alert: {e}")
    except Exception as e:
        print(f"Error sending alert: {e}")


def send_email_notification(subject: str, body: str) -> None:
    """Send email notification using SMTP settings from environment variables."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    # Check if email is enabled
    email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() in ("1", "true", "yes")
    if not email_enabled:
        print("[EMAIL] Email notifications disabled")
        return
    
    try:
        smtp_host = os.getenv("SMTP_HOST", "").strip()
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_ssl = os.getenv("SMTP_SSL", "false").lower() in ("1", "true", "yes")
        smtp_user = os.getenv("SMTP_USER", "").strip()
        smtp_pass = os.getenv("SMTP_PASS", "").strip()
        email_from = os.getenv("EMAIL_FROM", "").strip()
        email_to = os.getenv("EMAIL_TO", "").strip()
        
        if not all([smtp_host, smtp_user, smtp_pass, email_from, email_to]):
            print("[EMAIL] Missing SMTP configuration")
            return
        
        # Parse multiple recipients (comma-separated)
        recipients = [email.strip() for email in email_to.split(',') if email.strip()]
        if not recipients:
            print("[EMAIL] No valid recipients found")
            return
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = ', '.join(recipients)  # Display all recipients in header
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        if smtp_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
        
        server.login(smtp_user, smtp_pass)
        server.send_message(msg, to_addrs=recipients)  # Send to all recipients
        server.quit()
        
        print(f"[EMAIL] Sent: {subject}")
        
    except Exception as e:
        print(f"[EMAIL] Failed to send: {e}")


def _ensure_session(session: requests.Session | None) -> requests.Session:
    """Return a configured requests.Session.

    Adds a desktop-like User-Agent to reduce chances of being blocked.
    """
    if session is not None:
        return session
    sess = requests.Session()
    sess.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept-Language": "en,nb;q=0.9",
            "Accept": "text/html, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        }
    )
    return sess


def _apply_manual_cookies(session: requests.Session, cookie_strings: list[str] | None):
    """Apply cookies provided by the user (copied from browser) to the session.

    Accepts one or more cookie header strings like "name=value; name2=value2".
    """
    if not cookie_strings:
        return
    # Try to parse into the cookie jar
    for cookie_str in cookie_strings:
        if not cookie_str:
            continue
        parts = [p.strip() for p in cookie_str.split(";") if p.strip()]
        for part in parts:
            if "=" not in part:
                continue
            name, value = part.split("=", 1)
            try:
                session.cookies.set(name.strip(), value.strip(), domain="golfbox.golf", path="/")
            except Exception:
                # Fallback: set Cookie header (may be overridden by jar)
                existing = session.headers.get("Cookie", "")
                combined = (existing + "; " if existing else "") + f"{name}={value}"
                session.headers["Cookie"] = combined


def login_to_golfbox(session: requests.Session, email: str, password: str) -> bool:
    """Attempt to log in to golfbox.golf with provided credentials.

    Returns True if login appears successful; otherwise False. The function is
    best-effort and will not raise on failure.
    """
    try:
        # First, get the main login page to understand the structure
        login_url = "https://golfbox.golf/#/"
        r = session.get(login_url)
        r.raise_for_status()
        
        # If we're already logged in, we might be redirected to the dashboard
        if "myFrontPage" in r.url and "login" not in r.text.lower():
            return True
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Look for login form - golfbox might use different form structure
        login_form = soup.find("form") or soup.find("form", {"action": re.compile(r"login", re.I)})
        
        if not login_form:
            # Try direct POST to common login endpoints
            login_endpoints = [
                "https://golfbox.golf/api/login",
                "https://golfbox.golf/login",
                "https://golfbox.golf/auth/login"
            ]
            
            for endpoint in login_endpoints:
                try:
                    payload = {
                        "email": email,
                        "password": password,
                        "username": email,  # Some sites use username instead
                        "user": email,
                        "brukernavn": email,  # Norwegian
                        "passord": password,  # Norwegian
                    }
                    
                    headers = {"Referer": login_url}
                    pr = session.post(endpoint, data=payload, headers=headers, allow_redirects=True)
                    
                    # Check if login was successful
                    if pr.status_code == 200:
                        # Check current page for login success indicators
                        home = session.get("https://golfbox.golf/#/")
                        if home.status_code == 200 and (
                            "logout" in home.text.lower() 
                            or "logg ut" in home.text.lower()
                            or "min side" in home.text.lower()
                            or "dashboard" in home.text.lower()
                        ):
                            return True
                except Exception:
                    continue
        else:
            # Extract form action and method
            action = login_form.get("action", "")
            method = login_form.get("method", "post").lower()
            
            if action and not action.startswith("http"):
                if action.startswith("/"):
                    action = f"https://golfbox.golf{action}"
                else:
                    action = f"https://golfbox.golf/{action}"
            elif not action:
                action = login_url
            
            # Build payload from form inputs
            payload = {}
            for input_tag in login_form.find_all("input"):
                name = input_tag.get("name")
                value = input_tag.get("value", "")
                input_type = input_tag.get("type", "").lower()
                
                if name:
                    if input_type in ("email", "text") or "email" in name.lower() or "user" in name.lower():
                        payload[name] = email
                    elif input_type == "password" or "password" in name.lower() or "passord" in name.lower():
                        payload[name] = password
                    elif input_type in ("hidden", "submit"):
                        payload[name] = value
            
            headers = {"Referer": login_url}
            if method == "get":
                pr = session.get(action, params=payload, headers=headers, allow_redirects=True)
            else:
                pr = session.post(action, data=payload, headers=headers, allow_redirects=True)
            
            pr.raise_for_status()
            
            # Check if login was successful
            home = session.get("https://golfbox.golf/#/")
            if home.status_code == 200 and (
                "logout" in home.text.lower() 
                or "logg ut" in home.text.lower()
                or "min side" in home.text.lower()
                or "dashboard" in home.text.lower()
            ):
                return True
                
    except Exception as e:
        console.print(f"[dim red]Login attempt failed: {e}[/dim red]")
        return False
    return False


def resolve_golf_course_id(
    session: requests.Session,
    course_name: str,
    overrides: dict[str, int] | None = None,
) -> int:
    """Resolve golf course identifier for a given course key.

    - If facilities map contains an integer, return it directly.
    - If it contains a string slug, fetch the course page and extract courseId.
    """
    key = course_name.lower()
    # Check override first
    if overrides:
        for k, v in overrides.items():
            if k.lower() == key:
                return int(v)

    value = facilities[key]
    if isinstance(value, int):
        return value

    slug = str(value).strip()
    if not slug:
        raise ValueError(f"Empty slug for golf course '{course_name}'")

    # Try to find course ID from the golf course page
    url = f"https://golfbox.golf/course/{slug}"
    try:
        resp = session.get(url)
        resp.raise_for_status()
        html = resp.text

        # Try various patterns where the course id may appear
        patterns = [
            r"courseId[=:]\s*(\d+)",
            r"course_id[=:]\s*(\d+)",
            r"data-course-id=\"(\d+)\"",
            r"\"courseId\"\s*:\s*(\d+)",
            r"\"course\"\s*:\s*\{\s*\"id\"\s*:\s*(\d+)",
        ]
        for pattern in patterns:
            m = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
            if m:
                return int(m.group(1))

        # As a last resort, try to find booking/schedule links
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            if "/booking" in a["href"] and ("courseId=" in a["href"] or "course=" in a["href"]):
                try:
                    course_id_match = re.search(r"courseId=(\d+)", a["href"]) or re.search(r"course=(\d+)", a["href"])
                    if course_id_match:
                        return int(course_id_match.group(1))
                except Exception:
                    continue

    except Exception as e:
        console.print(f"[dim red]Failed to fetch course page: {e}[/dim red]")

    raise RuntimeError(
        f"Unable to resolve courseId for '{course_name}' from slug '{slug}'"
    )


def _parse_golfbox_grid_html(html: str) -> dict[str, list[str]]:
    """Parse GolfBox legacy grid HTML into tee time -> slots mapping.

    Heuristics:
    - Time label taken from the row header cell (first th/td in the row)
    - Column label taken from table header (thead th) when present; otherwise
      falls back to column index like "Tee #"
    - Available/free cells are detected by class names or link/button text
    """
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")
    if not table:
        # Fallback: search within any container
        table = soup

    # Build column headers if present
    header_labels: list[str] = []
    thead = table.find("thead") if table else None
    if thead:
        header_cells = thead.find_all(["th", "td"]) if thead else []
        for i, cell in enumerate(header_cells):
            text = cell.get_text(" ", strip=True)
            header_labels.append(text or f"Tee {i}")

    tee_times: dict[str, list[str]] = {}

    def is_available_cell(cell) -> bool:
        classes = " ".join(cell.get("class", [])).lower()
        text = cell.get_text(" ", strip=True).lower()
        # Common indicators
        keywords = ["ledig", "available", "free", "bookable", "ledig tid", "åpen"]
        if any(k in classes for k in ["ledig", "available", "free", "bookable", "open"]):
            return True
        if any(k in text for k in keywords):
            return True
        # Anchors/buttons with book text
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
        # Time label from first cell that looks like time
        time_label = None
        time_pattern = re.compile(r"\b\d{1,2}:\d{2}\b")
        first_text = cells[0].get_text(" ", strip=True) if cells else ""
        m = time_pattern.search(first_text)
        if m:
            time_label = m.group(0)
        else:
            # Try any text within row
            row_text = row.get_text(" ", strip=True)
            m2 = time_pattern.search(row_text)
            if m2:
                time_label = m2.group(0)
        if not time_label:
            # No time in this row; skip
            continue

        # Iterate over data cells (skip the first header/time cell)
        for col_idx, cell in enumerate(cells[1:], start=1):
            if not is_available_cell(cell):
                continue
            # Column label from header, if available
            if header_labels and col_idx < len(header_labels):
                col_label = header_labels[col_idx]
            else:
                # Try column header from the first row if it looks like header
                col_label = f"Tee {col_idx}"

            tee_times.setdefault(time_label, []).append(col_label)

    return tee_times


def _fetch_golfbox_grid(
    session: requests.Session,
    grid_url: str,
    target_date: datetime.date,
    debug: bool = False,
) -> dict[str, list[str]]:
    """Fetch and parse the GolfBox legacy grid endpoint.

    Tries appending a date query parameter if not present, using common names.
    """
    date_str = target_date.strftime("%Y-%m-%d")

    candidate_urls: list[str] = []
    base = grid_url
    if "?" in base:
        candidate_urls.append(f"{base}&date={date_str}")
        candidate_urls.append(f"{base}&dato={date_str}")
        candidate_urls.append(f"{base}&resdate={date_str}")
        candidate_urls.append(f"{base}&selectedDate={date_str}")
    else:
        candidate_urls.append(f"{base}?date={date_str}")
        candidate_urls.append(f"{base}?dato={date_str}")
        candidate_urls.append(f"{base}?resdate={date_str}")
        candidate_urls.append(f"{base}?selectedDate={date_str}")
    # Also try the base as-is
    candidate_urls.insert(0, base)

    headers = {
        "Referer": "https://www.golfbox.no/site/my_golfbox/myFrontPage.asp",
        "Accept": "text/html, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }

    last_error: Exception | None = None
    for url in candidate_urls:
        try:
            resp = session.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            html = resp.text
            if debug:
                try:
                    out_dir = os.path.join(os.getcwd(), "debug_html")
                    os.makedirs(out_dir, exist_ok=True)
                    safe = re.sub(r"[^a-z0-9]+", "-", "grid")
                    with open(os.path.join(out_dir, f"grid-{date_str}.html"), "w", encoding="utf-8") as f:
                        f.write(html)
                except Exception:
                    pass
            parsed = _parse_golfbox_grid_html(html)
            # If we parsed any rows, consider it success
            if parsed:
                return parsed
        except Exception as e:
            last_error = e
            if debug:
                console.print(f"[dim yellow]Grid fetch failed: {url} → {e}[/dim yellow]")

    # If none worked, return empty or raise in debug
    if debug and last_error:
        console.print(f"[dim red]All grid attempts failed: {last_error}[/dim red]")
    return {}


def fetch_available_tee_times(
    course_name: str,
    target_date: datetime.date,
    session: requests.Session | None = None,
    overrides: dict[str, int] | None = None,
    grid_overrides: dict[str, str] | None = None,
    email: str | None = None,
    password: str | None = None,
    debug: bool = False,
):
    """Fetch available tee times for a specific golf course and date."""
    return fetch_available_tee_times_core(
        course_name,
        target_date,
        session=session,
        overrides=overrides,
        grid_overrides=grid_overrides,
        email=email,
        password=password,
        debug=debug,
    )


def get_date_range(days_ahead: int = 2, start_date: datetime.date | None = None):
    """Get a list of dates from start_date to start_date + days_ahead (inclusive).

    If start_date is None, uses today.
    """
    if days_ahead < 0:
        raise ValueError("days_ahead must be >= 0")

    base_date = start_date or datetime.date.today()
    return [base_date + datetime.timedelta(days=i) for i in range(days_ahead + 1)]


def parse_dates_list(dates_csv: str) -> list[datetime.date]:
    """Parse a comma-separated list of YYYY-MM-DD into sorted unique dates."""
    parsed: set[datetime.date] = set()
    for part in dates_csv.split(","):
        text = part.strip()
        if not text:
            continue
        try:
            year, month, day = map(int, text.split("-"))
            parsed.add(datetime.date(year, month, day))
        except Exception as exc:
            raise argparse.ArgumentTypeError(
                f"Invalid date '{text}'. Use YYYY-MM-DD."
            ) from exc
    if not parsed:
        raise argparse.ArgumentTypeError("No valid dates provided")
    return sorted(parsed)


def _parse_hhmm(text: str) -> datetime.time:
    """Parse time strings like '17', '17:00', '08:30' into datetime.time."""
    text = text.strip()
    if not text:
        raise argparse.ArgumentTypeError("Empty time component")
    if ":" in text:
        hour_str, minute_str = text.split(":", 1)
        hour = int(hour_str)
        minute = int(minute_str)
    else:
        hour = int(text)
        minute = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise argparse.ArgumentTypeError("Time must be between 00:00 and 23:59")
    return datetime.time(hour=hour, minute=minute)


def parse_between_time_range(arg: str) -> tuple[datetime.time, datetime.time]:
    """Parse --between ranges like '17-22' or '17:30-22:00'."""
    if not arg:
        raise argparse.ArgumentTypeError("--between requires a value like 17-22")
    raw = arg.replace(" ", "")
    if "-" not in raw:
        raise argparse.ArgumentTypeError(
            "--between must be in the form HH:MM-HH:MM or HH-HH"
        )
    start_str, end_str = raw.split("-", 1)
    start_time = _parse_hhmm(start_str)
    end_time = _parse_hhmm(end_str)
    if end_time <= start_time:
        raise argparse.ArgumentTypeError("End time must be after start time")
    return start_time, end_time


def format_date_header(date):
    """Format date for display headers."""
    if date == datetime.date.today():
        return f"Today ({date.strftime('%Y-%m-%d')})"
    elif date == datetime.date.today() + datetime.timedelta(days=1):
        return f"Tomorrow ({date.strftime('%Y-%m-%d')})"
    else:
        return f"{date.strftime('%A, %Y-%m-%d')}"


def get_teetime_style(course_info, is_new=False, is_removed=False):
    """Get styling for tee time based on type and status."""
    # Determine tee type and icon
    if "18" in course_info.lower():
        icon = "🏌️"  # 18-hole round
    elif "9" in course_info.lower():
        icon = "⛳"   # 9-hole round
    else:
        icon = "🎯"   # General tee time

    # Apply status styling
    if is_new:
        return "bold bright_green", f"🆕{icon}"
    elif is_removed:
        return "strike dim white", f"❌{icon}"
    else:
        return "white", icon


def collect_all_tee_times(
    dates: list[datetime.date],
    session: requests.Session | None = None,
    overrides: dict[str, int] | None = None,
    email: str | None = None,
    password: str | None = None,
    debug: bool = False,
):
    """Collect tee times for all golf courses and dates."""
    all_times = {}

    console.print("\n⛳ Checking golf tee time availability...\n", style="bold blue")

    for course_name in facilities.keys():
        course_display_name = course_name.capitalize()
        all_times[course_name] = {}

        for date in dates:
            try:
                times = fetch_available_tee_times(
                    course_name,
                    date,
                    session=session,
                    overrides=overrides,
                    email=email,
                    password=password,
                    debug=debug,
                )
                all_times[course_name][date] = times
                console.print(
                    f"✓ Checked {course_display_name} for {format_date_header(date)}",
                    style="green",
                )
            except Exception as e:
                console.print(
                    "✗ Error checking "
                    f"{course_display_name} for {format_date_header(date)}: {e}",
                    style="red",
                )
                all_times[course_name][date] = {}

    return all_times


def get_teetime_changes(current_times, previous_times, course_name, date):
    """Get new and removed tee times for a specific course and date."""
    current = set()
    previous = set()

    current_day_times = current_times.get(course_name, {}).get(date, {})
    previous_day_times = previous_times.get(course_name, {}).get(date, {})

    # Flatten tee time lists for comparison
    for tee_time, courses in current_day_times.items():
        for course in courses:
            current.add((tee_time, course))

    for tee_time, courses in previous_day_times.items():
        for course in courses:
            previous.add((tee_time, course))

    new_times = current - previous
    removed_times = previous - current

    return new_times, removed_times


def _filter_times_by_between(
    times: dict[str, list[str]], between: tuple[datetime.time, datetime.time] | None
) -> dict[str, list[str]]:
    """Filter a single day's tee_time -> courses mapping by a time range.

    A tee time is included if its start time is within [between_start, between_end).
    """
    if not between:
        return times

    start_time, end_time = between
    filtered: dict[str, list[str]] = {}

    for tee_time_label, courses in times.items():
        try:
            tee_time = _parse_hhmm(tee_time_label.replace(" ", ""))
        except argparse.ArgumentTypeError:
            # If we can't parse, keep original behavior: include it
            filtered[tee_time_label] = courses
            continue

        if start_time <= tee_time < end_time:
            filtered[tee_time_label] = courses

    return filtered


def display_teetimes_table(
    all_times,
    previous_times=None,
    dates: list[datetime.date] | None = None,
):
    """Display tee times in a beautiful colored tabular format with highlighting."""
    if previous_times is None:
        previous_times = {}

    if dates is None:
        dates = get_date_range(2)

    for course_name, course_data in all_times.items():
        course_display_name = course_name.capitalize()

        # Create course header
        console.print(
            f"\n⛳ {course_display_name} Golf Course", style="bold magenta"
        )
        console.print("=" * 60, style="magenta")

        for date in dates:
            date_header = format_date_header(date)
            times = course_data.get(date, {})

            # Get changes for this course and date (only if we have previous data)
            if previous_times:
                new_times, removed_times = get_teetime_changes(
                    all_times, previous_times, course_name, date
                )
            else:
                new_times, removed_times = set(), set()

            # Create table for this date
            table = Table(
                title=f"📅 {date_header}",
                box=box.ROUNDED,
                title_style="bold blue",
                show_header=True,
                header_style="bold white",
            )
            table.add_column("Tee Time", style="bold cyan", width=15)
            table.add_column("Available Slots", style="white", min_width=40)

            if not times:
                table.add_row("", "[dim]No available tee times[/dim]")
            else:
                # Add rows for each tee time
                for tee_time in sorted(times.keys()):
                    courses = times[tee_time]

                    # Style each course slot individually
                    styled_courses = []
                    for course in courses:
                        is_new = (tee_time, course) in new_times
                        is_removed = (tee_time, course) in removed_times

                        style, icon = get_teetime_style(course, is_new, is_removed)
                        styled_course = Text(f"{icon} {course}", style=style)
                        styled_courses.append(styled_course)

                    # Combine styled courses
                    if styled_courses:
                        courses_display = Text()
                        for i, styled_course in enumerate(styled_courses):
                            if i > 0:
                                courses_display.append(", ")
                            courses_display.append(styled_course)
                        table.add_row(tee_time, courses_display)

            console.print(table)
            console.print()  # Add spacing between tables


def has_changes(current_times, previous_times):
    """Check if there are any changes between current and previous tee times."""
    # If previous_times is empty (first run), don't consider it a change
    if not previous_times:
        return False
    return current_times != previous_times


def get_changes_summary(
    current_times,
    previous_times,
    dates: list[datetime.date] | None = None,
):
    """Get a summary of what changed."""
    changes = []
    if dates is None:
        dates = get_date_range(2)

    # Don't generate changes if previous_times is empty (first run)
    if not previous_times:
        return changes

    for course_name in facilities.keys():
        course_display = course_name.capitalize()
        for date in dates:
            current = current_times.get(course_name, {}).get(date, {})
            previous = previous_times.get(course_name, {}).get(date, {})

            if current != previous:
                date_str = format_date_header(date)

                # Count actual new tee times
                current_teetimes = set()
                previous_teetimes = set()

                for tee_time, courses in current.items():
                    for course in courses:
                        current_teetimes.add((tee_time, course))

                for tee_time, courses in previous.items():
                    for course in courses:
                        previous_teetimes.add((tee_time, course))

                new_teetimes = current_teetimes - previous_teetimes
                removed_teetimes = previous_teetimes - current_teetimes

                if new_teetimes:
                    changes.append(
                        f"New tee times available at {course_display} on {date_str}"
                    )
                if removed_teetimes:
                    changes.append(f"Tee times taken at {course_display} on {date_str}")

    return changes


def show_legend(
    dates: list[datetime.date],
    between: tuple[datetime.time, datetime.time] | None = None,
):
    """Display the legend for tee time types and status indicators."""
    console.print("\n⛳ Golf Tee Time Availability Monitor", style="bold blue")
    if not dates:
        date_summary = "No dates"
    elif len(dates) <= 5:
        date_summary = ", ".join(d.strftime("%Y-%m-%d") for d in dates)
    else:
        start_str = dates[0].strftime("%Y-%m-%d")
        end_str = dates[-1].strftime("%Y-%m-%d")
        date_summary = f"{start_str} … {end_str} ({len(dates)} dates)"
    course_list = ", ".join(name.capitalize() for name in facilities.keys())
    console.print(
        f"Monitoring {course_list} for: {date_summary}",
        style="blue",
    )
    if between:
        start_hhmm = between[0].strftime("%H:%M")
        end_hhmm = between[1].strftime("%H:%M")
        console.print(
            f"Time filter: {start_hhmm}–{end_hhmm}",
            style="blue",
        )

    legend_table = Table(
        title="Legend",
        box=box.SIMPLE,
        show_header=False,
        title_style="bold yellow",
    )
    legend_table.add_column("Symbol", style="bold")
    legend_table.add_column("Meaning")

    legend_table.add_row("🏌️ 18-hole", "[green]Full round[/green]")
    legend_table.add_row("⛳ 9-hole", "[cyan]Half round[/cyan]")
    legend_table.add_row("🎯 Tee time", "[white]General slot[/white]")
    legend_table.add_row(
        "🆕 New", "[bold bright_green]Newly available[/bold bright_green]"
    )
    legend_table.add_row("❌ Removed", "[strike dim]No longer available[/strike dim]")
    legend_table.add_row(
        "🔔 Alerts", "[blue]Visual popups (auto-close after 5s)[/blue]"
    )

    console.print(legend_table)
    console.print("Press Ctrl+C to stop monitoring\n", style="dim")


def test_notifications():
    """Test the alert system to ensure it's working."""
    console.print("🔔 Testing alert system...\n", style="bold blue")

    console.print(
        "💡 This system uses visual popup alerts instead of notifications.",
        style="blue",
    )
    console.print(
        "Alerts appear as dialogs and automatically disappear after 5 seconds.",
        style="blue",
    )
    console.print("No special permissions required!\n", style="green")

    # Ask for confirmation before proceeding
    console.print(
        "Press Enter to continue with alert test, or Ctrl+C to exit...",
        style="dim",
    )
    try:
        input()
    except KeyboardInterrupt:
        console.print("\n❌ Test cancelled.", style="yellow")
        return

    test_messages = [
        (
            "⛳ Golf Alert Test",
            "If you see this popup, alerts are working perfectly!",
        ),
        (
            "🏌️ System Check",
            "Golf tee time monitor will show popups when slots become available.",
        ),
        ("✅ Test Complete", "Alert system is functioning correctly."),
    ]

    for i, (title, message) in enumerate(test_messages, 1):
        console.print(f"Sending test alert {i}/3...", style="dim")
        send_notification(title, message)

        if i < len(test_messages):
            console.print("Waiting 3 seconds before next test...", style="dim")
            time.sleep(3)

    console.print("\n🔔 Alert test complete!", style="bold green")
    console.print(
        "✅ If you saw 3 popup dialogs: System is working correctly!",
        style="bold green",
    )
    console.print(
        "❌ If you didn't see any popups: Check if Terminal has permission "
        "to control your computer",
        style="yellow",
    )
    console.print(
        "💡 Alerts appear as popup dialogs and disappear automatically after 5 seconds",
        style="dim blue",
    )


def run_monitor(
    dates: list[datetime.date],
    between: tuple[datetime.time, datetime.time] | None = None,
    email: str | None = None,
    password: str | None = None,
    course_id_overrides: dict[str, int] | None = None,
    course_grid_overrides: dict[str, str] | None = None,
    debug: bool = False,
    cookie: list[str] | None = None,
):
    """Run the main tee time availability monitoring loop."""
    # Initialize previous state
    previous_times = {}

    # Prepare HTTP session and optional login
    session = _ensure_session(None)
    if email and password:
        logged_in = login_to_golfbox(session, email, password)
        if logged_in:
            console.print("🔐 Logged in to golfbox.golf successfully.", style="green")
        else:
            console.print(
                "⚠️ Could not verify login. Continuing without authentication.",
                style="yellow",
            )
    # Apply manual cookies if provided (e.g., membership tokens)
    _apply_manual_cookies(session, cookie)

    show_legend(dates, between)

    while True:  # Infinite loop to keep the script running
        try:
            current_times = collect_all_tee_times(
                dates,
                session=session,
                overrides=course_id_overrides,
                grid_overrides=course_grid_overrides,
                email=email,
                password=password,
                debug=debug,
            )
            # Apply time filtering (if any)
            if between:
                for course_name in list(current_times.keys()):
                    for date in list(current_times[course_name].keys()):
                        times = current_times[course_name][date]
                        current_times[course_name][date] = _filter_times_by_between(
                            times, between
                        )

            # Check for changes (only after first run)
            changes_detected = has_changes(current_times, previous_times)
            if changes_detected:
                changes = get_changes_summary(current_times, previous_times, dates)

                # Send notification
                if changes:
                    summary = "; ".join(
                        changes[:3]
                    )  # Limit to first 3 changes for notification
                    if len(changes) > 3:
                        summary += f" and {len(changes) - 3} more..."

                    send_notification(
                        title="⛳ Golf Tee Times Updated!",
                        message=summary,
                    )
                    send_email_notification(
                        subject="⛳ Golf Tee Times Updated!",
                        body=summary,
                    )

                console.print("\n🔔 Changes detected!", style="bold green")
                if changes:
                    for change in changes:
                        console.print(f"   • {change}", style="green")
            elif previous_times:  # Only show "no changes" if this isn't the first run
                console.print(
                    "\n✓ No changes detected. Tee times status unchanged.",
                    style="dim green",
                )

            # Always display current state (with highlighting if there were changes)
            display_teetimes_table(
                current_times,
                previous_times if changes_detected else {},
                dates,
            )

            # Update previous state
            previous_times = current_times.copy()

            next_check_time = (
                datetime.datetime.now() + datetime.timedelta(minutes=5)
            ).strftime("%H:%M:%S")
            console.print(
                f"\n⏰ Next check in 5 minutes... (at {next_check_time})",
                style="dim blue",
            )
            time.sleep(300)  # Sleep for 5 minutes

        except KeyboardInterrupt:
            console.print(
                "\n\n👋 Monitoring stopped. Have a great round!", style="bold blue"
            )
            break
        except Exception as e:
            console.print(f"\n❌ Error occurred: {e}", style="red")
            console.print("Retrying in 1 minute...", style="yellow")
            time.sleep(60)


def main():
    """Main entry point with command-line argument parsing."""
    parser = argparse.ArgumentParser(
        description="⛳ Golf Tee Time Availability Monitor for golfbox.golf",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     Start monitoring (default)
  %(prog)s monitor             Start monitoring
  %(prog)s test-notifications  Test alert system
  %(prog)s --help              Show this help message

For more information, visit: https://github.com/your-username/golf-bot
        """.strip(),
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", metavar="COMMAND"
    )

    # Monitor command (default)
    monitor_parser = subparsers.add_parser(
        "monitor",
        help="Start monitoring golf tee time availability (default)",
        description=(
            "Monitor golf tee times and send notifications when slots become "
            "available"
        ),
    )

    # Test notifications command
    subparsers.add_parser(
        "test-notifications",
        help="Test the alert system",
        description="Send test popup alerts to verify the system is working",
    )

    # One-off fetch command (no monitor loop)
    fetch_parser = subparsers.add_parser(
        "fetch-once",
        help="Fetch tee times for a single course/date and exit",
        description=(
            "Fetch available tee times for one course on one date and print the result."
        ),
    )
    fetch_parser.add_argument(
        "--course",
        required=True,
        type=str,
        help="Course name (must match a key in facilities.py or provided via --course-id/--course-grid)",
    )
    fetch_parser.add_argument(
        "--date",
        required=False,
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Date to fetch (defaults to today)",
    )
    fetch_parser.add_argument(
        "--course-id",
        action="append",
        default=None,
        metavar="NAME=ID",
        help="Override course id mapping (can be used multiple times)",
    )
    fetch_parser.add_argument(
        "--course-grid",
        action="append",
        default=None,
        metavar="NAME=URL",
        help="Use a GolfBox legacy grid URL for this course (can be used multiple times)",
    )
    fetch_parser.add_argument(
        "--debug",
        action="store_true",
        help="Print scrape diagnostics while fetching",
    )

    # Monitoring options (apply to monitor command)
    monitor_parser.add_argument(
        "--days-ahead",
        type=int,
        default=2,
        help=(
            "Number of days ahead to include (inclusive). 0 means only today. "
            "Default: 2"
        ),
    )
    monitor_parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Start date (defaults to today). Used with --days-ahead.",
    )
    monitor_parser.add_argument(
        "--dates",
        type=str,
        default=None,
        metavar="YYYY-MM-DD,YYYY-MM-DD",
        help=(
            "Comma-separated specific dates to monitor. Overrides "
            "--start-date/--days-ahead if provided."
        ),
    )
    monitor_parser.add_argument(
        "--between",
        type=str,
        default=None,
        metavar="START-END",
        help=(
            "Only include tee times whose start is within the interval. "
            "Formats: HH-HH or HH:MM-HH:MM (e.g., 17-22 or 17:30-22:00)."
        ),
    )

    # Optional authentication
    monitor_parser.add_argument(
        "--email",
        type=str,
        default=None,
        help="Golfbox account email (or set env GOLFBOX_EMAIL)",
    )
    monitor_parser.add_argument(
        "--password",
        type=str,
        default=None,
        help="Golfbox account password (or set env GOLFBOX_PASSWORD)",
    )
    monitor_parser.add_argument(
        "--course-id",
        action="append",
        default=None,
        metavar="NAME=ID",
        help=(
            "Override course id mapping. Can be specified multiple times. "
            "Example: --course-id 'oslo golfklubb=9999'"
        ),
    )
    monitor_parser.add_argument(
        "--course-grid",
        action="append",
        default=None,
        metavar="NAME=URL",
        help=(
            "Override course to use a GolfBox grid URL (legacy). Can be specified multiple times. "
            "Example: --course-grid 'oslo golfklubb=https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?clubid=123'"
        ),
    )
    monitor_parser.add_argument(
        "--debug",
        action="store_true",
        help="Print scrape diagnostics while monitoring",
    )
    monitor_parser.add_argument(
        "--cookie",
        action="append",
        default=None,
        metavar="COOKIE",
        help=(
            "Add a Cookie header string (can be used multiple times). Copy from browser devtools."
        ),
    )
    monitor_parser.add_argument(
        "--cookie-file",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to a file containing a Cookie header (first line is used)",
    )

    args = parser.parse_args()

    # Default to monitor if no command specified
    if args.command is None:
        args.command = "monitor"

    # Route to appropriate function
    if args.command == "monitor":
        # Build dates to monitor
        dates: list[datetime.date]
        if getattr(args, "dates", None):
            dates = parse_dates_list(args.dates)
        else:
            start_date = None
            if getattr(args, "start_date", None):
                try:
                    y, m, d = map(int, args.start_date.split("-"))
                    start_date = datetime.date(y, m, d)
                except Exception as exc:
                    raise SystemExit(
                        f"Invalid --start-date '{args.start_date}'. Use YYYY-MM-DD."
                    ) from exc
            days_ahead = getattr(args, "days_ahead", 2)
            dates = get_date_range(days_ahead=days_ahead, start_date=start_date)

        # Build optional time filter
        between = None
        if getattr(args, "between", None):
            try:
                between = parse_between_time_range(args.between)
            except argparse.ArgumentTypeError as exc:
                raise SystemExit(str(exc)) from exc

        # Resolve credentials from flags or environment
        email = getattr(args, "email", None) or os.getenv("GOLFBOX_EMAIL")
        password = getattr(args, "password", None) or os.getenv("GOLFBOX_PASSWORD")

        # Parse overrides
        overrides: dict[str, int] | None = None
        raw_overrides = getattr(args, "course_id", None)
        if raw_overrides:
            overrides = {}
            for entry in raw_overrides:
                if not entry or "=" not in entry:
                    raise SystemExit(
                        f"Invalid --course-id '{entry}'. Use NAME=ID (e.g., oslo golfklubb=123)."
                    )
                name, id_text = entry.split("=", 1)
                name = name.strip()
                try:
                    overrides[name.lower()] = int(id_text.strip())
                except ValueError:
                    raise SystemExit(
                        f"Invalid course id in '{entry}'. Must be an integer."
                    )

        # Parse grid overrides
        grid_overrides: dict[str, str] | None = None
        raw_grids = getattr(args, "course_grid", None)
        if raw_grids:
            grid_overrides = {}
            for entry in raw_grids:
                if not entry or "=" not in entry:
                    raise SystemExit(
                        f"Invalid --course-grid '{entry}'. Use NAME=URL (e.g., oslo golfklubb=https://…/grid.asp?...)."
                    )
                name, url = entry.split("=", 1)
                name = name.strip().lower()
                url = url.strip()
                if not (url.startswith("http://") or url.startswith("https://")):
                    raise SystemExit(
                        f"Invalid URL in --course-grid '{entry}'. Must start with http(s)://"
                    )
                grid_overrides[name] = url

        # Build cookie list from flags, env, or file
        cookie_list: list[str] | None = None
        raw_cookies = []
        cli_cookies = getattr(args, "cookie", None)
        if cli_cookies:
            raw_cookies.extend(cli_cookies)
        env_cookie = os.getenv("GOLFBOX_COOKIE")
        if env_cookie:
            raw_cookies.append(env_cookie)
        cookie_file = getattr(args, "cookie_file", None)
        if cookie_file:
            try:
                with open(cookie_file, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line:
                        raw_cookies.append(first_line)
            except Exception as exc:
                raise SystemExit(f"Failed to read --cookie-file: {exc}")
        if raw_cookies:
            cookie_list = raw_cookies

        run_monitor(
            dates,
            between,
            email=email,
            password=password,
            course_id_overrides=overrides,
            course_grid_overrides=grid_overrides,
            debug=getattr(args, "debug", False),
            cookie=cookie_list,
        )
    elif args.command == "fetch-once":
        # Parse date
        if getattr(args, "date", None):
            try:
                y, m, d = map(int, args.date.split("-"))
                target_date = datetime.date(y, m, d)
            except Exception as exc:
                raise SystemExit(
                    f"Invalid --date '{args.date}'. Use YYYY-MM-DD."
                ) from exc
        else:
            target_date = datetime.date.today()

        # Parse overrides
        overrides: dict[str, int] | None = None
        raw_overrides = getattr(args, "course_id", None)
        if raw_overrides:
            overrides = {}
            for entry in raw_overrides:
                if not entry or "=" not in entry:
                    raise SystemExit(
                        f"Invalid --course-id '{entry}'. Use NAME=ID."
                    )
                name, id_text = entry.split("=", 1)
                name = name.strip().lower()
                try:
                    overrides[name] = int(id_text.strip())
                except ValueError:
                    raise SystemExit(
                        f"Invalid course id in '{entry}'. Must be an integer."
                    )

        grid_overrides: dict[str, str] | None = None
        raw_grids = getattr(args, "course_grid", None)
        if raw_grids:
            grid_overrides = {}
            for entry in raw_grids:
                if not entry or "=" not in entry:
                    raise SystemExit(
                        f"Invalid --course-grid '{entry}'. Use NAME=URL."
                    )
                name, url = entry.split("=", 1)
                name = name.strip().lower()
                url = url.strip()
                if not (url.startswith("http://") or url.startswith("https://")):
                    raise SystemExit(
                        f"Invalid URL in --course-grid '{entry}'. Must start with http(s)://"
                    )
                grid_overrides[name] = url

        # Create a session and fetch once
        session = _ensure_session(None)
        course = getattr(args, "course", "").strip()
        try:
            times = fetch_available_tee_times(
                course,
                target_date,
                session=session,
                overrides=overrides,
                grid_overrides=grid_overrides,
                debug=getattr(args, "debug", False),
            )
        except Exception as exc:
            raise SystemExit(f"Fetch failed: {exc}")

        # Print lightweight summary
        if not times:
            console.print("No available tee times found.")
        else:
            console.print(f"Available tee times for {course.capitalize()} on {target_date}:")
            for hhmm in sorted(times.keys()):
                slots = ", ".join(times[hhmm])
                console.print(f"  {hhmm}: {slots}")
    elif args.command == "test-notifications":
        test_notifications()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()