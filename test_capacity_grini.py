#!/usr/bin/env python3
import asyncio
import datetime
import os
import re
from typing import Dict, List

from playwright.async_api import async_playwright
from golf_club_urls import golf_url_manager
from playwright_runner import ensure_context, fetch_times_for_url


def next_sunday(today: datetime.date | None = None) -> datetime.date:
	if today is None:
		today = datetime.date.today()
	# Monday=0, Sunday=6
	days_ahead = (6 - today.weekday()) % 7
	if days_ahead == 0:
		# if today is Sunday, use next Sunday
		days_ahead = 7
	return today + datetime.timedelta(days=days_ahead)


def hhmm_to_booking_start(hhmm: str) -> str:
	clean = hhmm.strip()
	if ":" in clean:
		h, m = clean.split(":", 1)
	else:
		h, m = clean[:2], clean[2:]
	return f"{int(h):02d}{int(m):02d}00"


def parse_capacity_from_label(label: str) -> int:
	# Label format now is: "N spots available" or "1 spot available"
	m = re.match(r"\s*(\d+)\s+spot", label.strip(), re.I)
	if m:
		try:
			return int(m.group(1))
		except ValueError:
			pass
	return 0


async def run() -> int:
	club = golf_url_manager.get_club_by_name("grini_gk")
	if not club:
		print("Club not found: grini_gk")
		return 2

	# Configurable via env
	target_hhmm = os.getenv("TEST_HHMM", "06:30")
	expect_cap_env = os.getenv("EXPECT_CAPACITY")
	expected_capacity = int(expect_cap_env) if expect_cap_env else None

	target_day = next_sunday()
	url = club.get_url_for_date(target_day, start_time=hhmm_to_booking_start(target_hhmm))
	print(f"Testing Grini GK · {target_day} · {target_hhmm}")
	print(f"URL: {url}")

	async with async_playwright() as pw:
		browser = await pw.chromium.launch(headless=True)
		context = await ensure_context(browser)
		try:
			times: Dict[str, List[str]] = await fetch_times_for_url(context, url, debug=False, assume_logged_in=True)
		finally:
			await context.close()
			await browser.close()

	print("Parsed times:")
	for hhmm in sorted(times.keys()):
		print(f"  {hhmm}: {', '.join(times[hhmm])}")

	labels = times.get(target_hhmm, [])
	if not labels:
		print(f"No entry for {target_hhmm}. Available keys: {', '.join(sorted(times.keys()))}")
		return 1

	# With simplified labels there is exactly one label per time
	capacity = 0
	for lbl in labels:
		capacity = max(capacity, parse_capacity_from_label(lbl))

	print(f"Estimated capacity at {target_hhmm}: {capacity}")

	if expected_capacity is not None:
		ok = (capacity == expected_capacity)
		print(f"Assertion: capacity == {expected_capacity} → {'PASS' if ok else 'FAIL'}")
		return 0 if ok else 1
	return 0


if __name__ == "__main__":
	code = asyncio.run(run())
	exit(code)
