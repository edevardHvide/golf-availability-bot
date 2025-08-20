from __future__ import annotations

import datetime
import os
import re
import time
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from golfbot.scraping.requests_client import (
	ensure_session,
	login_to_golfbox as login_http,
	fetch_golfbox_grid,
)


def fetch_available_tee_times(
	course_name: str,
	target_date: datetime.date,
	session: Optional[requests.Session] = None,
	overrides: Optional[dict[str, int]] = None,
	grid_overrides: Optional[dict[str, str]] = None,
	email: Optional[str] = None,
	password: Optional[str] = None,
	debug: bool = False,
) -> dict[str, list[str]]:
    """Requests-based fetch for golfbox.golf tee-time availability.

    - Tries a provided legacy grid URL first (if present) via HTML parse
    - Otherwise resolves courseId and queries several GolfBox endpoints
    - Parses returned HTML heuristically for available slots
    """
    from facilities import facilities  # local map

    sess = ensure_session(session)

    # Grid URL override path
    if grid_overrides:
        for k, url in grid_overrides.items():
            if k.lower() == course_name.lower() and url:
                grid_times = fetch_golfbox_grid(sess, url, target_date, debug=debug)
                if grid_times:
                    return grid_times

    # Resolve courseId
    def resolve_golf_course_id(session: requests.Session, course_name: str, overrides: Optional[dict[str, int]] = None) -> int:
        key = course_name.lower()
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
        url = f"https://golfbox.golf/course/{slug}"
        resp = session.get(url)
        resp.raise_for_status()
        html = resp.text
        for pattern in (
            r"courseId[=:]\s*(\d+)",
            r"course_id[=:]\s*(\d+)",
            r"data-course-id=\"(\d+)\"",
            r"\"courseId\"\s*:\s*(\d+)",
            r"\"course\"\s*:\s*\{\s*\"id\"\s*:\s*(\d+)",
        ):
            m = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
            if m:
                return int(m.group(1))
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            if "/booking" in a["href"] and ("courseId=" in a["href"] or "course=" in a["href"]):
                m = re.search(r"courseId=(\d+)", a["href"]) or re.search(r"course=(\d+)", a["href"])
                if m:
                    return int(m.group(1))
        raise RuntimeError(f"Unable to resolve courseId for '{course_name}' from slug '{slug}'")

    try:
        course_id = resolve_golf_course_id(sess, course_name, overrides=overrides)
    except RuntimeError:
        if email and password and login_http(sess, email, password):
            course_id = resolve_golf_course_id(sess, course_name, overrides=overrides)
        else:
            raise

    date_str = target_date.strftime("%Y-%m-%d")
    possible_urls = [
        f"https://golfbox.golf/api/teetimes?courseId={course_id}&date={date_str}",
        f"https://golfbox.golf/booking/schedule?courseId={course_id}&date={date_str}",
        f"https://golfbox.golf/course/{course_id}/booking?date={date_str}",
        f"https://golfbox.golf/teetimes?course={course_id}&date={date_str}",
        f"https://golfbox.golf/booking?courseId={course_id}&date={date_str}",
    ]

    timestamp = str(int(time.time() * 1000))
    req_headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "text/html, application/json, */*; q=0.01",
        "Referer": "https://golfbox.golf/#/",
    }

    response = None
    for url in possible_urls:
        try:
            params = {"_": timestamp}
            response = sess.get(url, params=params, headers=req_headers, timeout=10)
            response.raise_for_status()
            if len(response.text) > 100 and "error" not in response.text.lower():
                break
        except Exception:
            continue

    if not response or response.status_code != 200:
        raise RuntimeError(f"Unable to fetch tee times for '{course_name}' on {date_str}")

    soup = BeautifulSoup(response.text, "html.parser")
    if "login" in str(response.url).lower() or soup.find("form", attrs={"action": re.compile(r"login", re.I)}):
        raise RuntimeError("Login required or session expired while fetching tee times")

    # Heuristic extraction of times from HTML blocks
    available_times = soup.select(
		".available-time, .tee-time.available, .booking-slot.free, .time-slot.available, .teetime.bookable"
	) or soup.find_all(
		lambda t: t.name in ("div", "td", "li", "button") and t.has_attr("class") and any(
			cls in str(t.get("class", [])).lower() for cls in ["available", "free", "bookable", "open"]
		)
	)

    if not available_times:
        booking_links = soup.select('a[href*="book"], button[onclick*="book"], .book-button, .booking-btn')
        available_times = []
        for link in booking_links:
            parent = link.find_parent(["div", "td", "li"]) or link
            if parent not in available_times:
                available_times.append(parent)

    tee_times: Dict[str, List[str]] = {}
    for time_element in available_times:
        details = (
            time_element.get("title")
            or time_element.get("data-time")
            or time_element.get("data-teetime")
            or time_element.get("data-original-title")
            or ""
        )
        if not details:
            details = time_element.get_text(" ", strip=True)
        normalized = (
            details.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
        )
        parts = [p.strip() for p in re.split(r"\n|\s{2,}|<br\s*/?>", normalized) if p.strip()]

        time_pattern = re.compile(r"\b(\d{1,2}):(\d{2})\b")
        time_match = None
        course_info = "Standard"
        for part in parts:
            if not time_match:
                m = time_pattern.search(part)
                if m:
                    time_match = m.group(0)
            if any(k in part.lower() for k in ["tee", "course", "hole", "9", "18"]):
                course_info = part
        if time_match:
            tee_times.setdefault(time_match, []).append(course_info)

    return tee_times


