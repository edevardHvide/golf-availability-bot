#!/usr/bin/env python3
import asyncio
import datetime
import os
import re
from typing import Dict, List
import logging
from pathlib import Path
from bs4 import BeautifulSoup

from playwright.async_api import async_playwright
from golf_club_urls import golf_url_manager

from playwright_runner import (
	ensure_context,
	fetch_times_for_url,
	load_config,
	fetch_player_counts_for_url,
	fetch_availability_for_url,
	maybe_login,
	save_storage_state,
	login_and_goto_with_retries,
)
from golfbot.grid_parser import parse_grid_html


def offline_count_players_per_tee_time_html(html: str, parent_selector: str = ".d-flex.grid-row.w-100") -> Dict[str, int]:
	soup = BeautifulSoup(html, "html.parser")
	parent = soup.select_one(parent_selector)
	results: Dict[str, int] = {}
	if not parent:
		# fallback: any .hour tiles
		tiles = soup.select(".hour, .booking-slot, .time-slot")
	else:
		tiles = parent.select(":scope > .hour")
	for tee in tiles:
		time_el = tee.select_one(".time")
		tee_time = None
		if time_el:
			m = re.search(r"\b\d{1,2}:\d{2}\b", time_el.get_text(" ", strip=True))
			if m:
				tee_time = m.group(0)
		if not tee_time:
			m2 = re.search(r"\b\d{1,2}:\d{2}\b", tee.get_text(" ", strip=True))
			if m2:
				tee_time = m2.group(0)
		if not tee_time:
			continue
		item = tee.select_one(".item")
		num_players = len(item.find_all("img")) if item else 0
		if num_players == 0:
			num_players = len(tee.select("img[src*='bookinggrid/greenfee']"))
		results[tee_time] = num_players
	return results



async def _save_html_for_url(context, url: str, out_html: Path, out_png: Path | None = None, logger: logging.Logger | None = None) -> None:
	from playwright.async_api import Page
	# Use strict helper to ensure login + direct navigation to target
	page = await login_and_goto_with_retries(context, url, debug=True, max_attempts=3, assume_logged_in=False)
	try:
		try:
			await page.wait_for_selector("div.hour, table", timeout=10000)
		except Exception:
			pass
		html = await page.content()
		out_html.parent.mkdir(parents=True, exist_ok=True)
		out_html.write_text(html, encoding="utf-8")
		if out_png is not None:
			try:
				await page.screenshot(path=str(out_png))
			except Exception:
				pass
		if logger:
			logger.info(f"Saved HTML → {out_html}")
	finally:
		try:
			await page.close()
		except Exception:
			pass


def tomorrow(today: datetime.date | None = None) -> datetime.date:
	if today is None:
		today = datetime.date.today()
	return today + datetime.timedelta(days=1)


def hhmm_to_booking_start(hhmm: str) -> str:
	clean = hhmm.strip()
	if ":" in clean:
		h, m = clean.split(":", 1)
	else:
		h, m = clean[:2], clean[2:]
	return f"{int(h):02d}{int(m):02d}00"


def parse_capacity_from_label(label: str) -> int:
	# Label format: "N spots available" or "1 spot available"
	m = re.match(r"\s*(\d+)\s+spot", label.strip(), re.I)
	if m:
		try:
			return int(m.group(1))
		except ValueError:
			pass
	return 0


async def run() -> int:
	# Ensure .env is loaded so login credentials (GOLFBOX_USER/GOLFBOX_PASS) are available
	try:
		load_config()
	except Exception:
		pass

	# Setup logging to file
	logs_dir = Path("logs")
	logs_dir.mkdir(exist_ok=True)
	log_path = logs_dir / f"capacity_grini_{datetime.date.today().isoformat()}.log"
	logger = logging.getLogger("capacity_grini")
	logger.setLevel(logging.DEBUG)
	if not logger.handlers:
		fh = logging.FileHandler(log_path, encoding="utf-8")
		fh.setLevel(logging.DEBUG)
		fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
		fh.setFormatter(fmt)
		logger.addHandler(fh)
		ch = logging.StreamHandler()
		ch.setLevel(logging.INFO)
		ch.setFormatter(fmt)
		logger.addHandler(ch)

	# Basic env summary
	user = os.getenv("GOLFBOX_USER", "")
	masked = (user[:2] + "***" + user[-2:]) if len(user) >= 4 else ("***" if user else "(none)")
	try:
		default_capacity = int(os.getenv("TEE_CAPACITY", "4"))
	except Exception:
		default_capacity = 4
	logger.info(f"Starting Grini capacity test; user={masked}, TEE_CAPACITY={default_capacity}")
	club = golf_url_manager.get_club_by_name("grini_gk")
	if not club:
		print("Club not found: grini_gk")
		logger.error("Club not found: grini_gk")
		return 2

	target_times = ["07:10", "07:30", "10:30"]
	target_day = tomorrow()
	results: Dict[str, int] = {}

	async with async_playwright() as pw:
		headless = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")
		logger.info(f"Launching Chromium headless={headless}")
		browser = await pw.chromium.launch(headless=headless)
		context = await ensure_context(browser)
		try:
			# For each desired tee time, navigate to that exact grid and compute players + capacity
			for hhmm in target_times:
				url = club.get_url_for_date(target_day, start_time=hhmm_to_booking_start(hhmm))
				print(f"Testing Grini GK · {target_day} · {hhmm}")
				print(f"URL: {url}")
				logger.info(f"=== Checking {hhmm} @ {target_day} ===")
				logger.debug(f"URL: {url}")
				# Offline snapshot control
				save_local = os.getenv("SAVE_LOCAL_HTML", "0").lower() in ("1", "true", "yes")
				use_local = os.getenv("USE_LOCAL_HTML", "0").lower() in ("1", "true", "yes")
				debug_dir = Path("debug_html")
				debug_dir.mkdir(exist_ok=True)
				stamp = target_day.strftime("%Y-%m-%d")
				local_html = debug_dir / f"grini-{stamp}-{hhmm.replace(':','')}.html"
				local_png = debug_dir / f"grini-{stamp}-{hhmm.replace(':','')}.png"
				if save_local and not use_local:
					await _save_html_for_url(context, url, local_html, local_png, logger)

				# 1) Direct availability from DOM (aria/labels or inferred)
				if use_local and local_html.exists():
					try:
						html = local_html.read_text(encoding="utf-8")
						players_map = offline_count_players_per_tee_time_html(html)
						labels_map = parse_grid_html(html)
						logger.debug(f"[OFFLINE] players_map: {players_map}")
						logger.debug(f"[OFFLINE] labels_map: {labels_map}")
						players = players_map.get(hhmm, 0)
						cap_from_label = 0
						for lbl in labels_map.get(hhmm, []):
							cap_from_label = max(cap_from_label, parse_capacity_from_label(lbl))
						try:
							default_capacity = int(os.getenv("TEE_CAPACITY", "4"))
						except Exception:
							default_capacity = 4
						cap = max(cap_from_label, max(0, default_capacity - players))
						logger.info(f"[OFFLINE] players={players}, label_cap={cap_from_label}, final available={cap}")
					except Exception as e:
						logger.error(f"[OFFLINE] parse failed: {e}")
						cap = 0
				else:
					availability = await fetch_availability_for_url(context, url, debug=True, assume_logged_in=False, parent_selector=".d-flex.grid-row.w-100")
					logger.debug(f"availability map: {availability}")
					cap = availability.get(hhmm, 0)
				logger.info(f"Initial available (DOM-derived) for {hhmm}: {cap}")
				# Also compute raw player counts for visibility
				if not use_local:
					player_counts = await fetch_player_counts_for_url(context, url, debug=True, assume_logged_in=True, parent_selector=".d-flex.grid-row.w-100")
					logger.debug(f"player_counts map: {player_counts}")
					players = player_counts.get(hhmm, None)
					if players is not None:
						logger.info(f"Observed players at {hhmm}: {players}")
				# 2) Do NOT override with heuristic HTML labels.
				#    We have observed mismatches; the tile-based DOM count is the source of truth.
				#    Keep this block for optional diagnostics only.
				if os.getenv("LOG_LABELS", "0").lower() in ("1", "true", "yes"):
					if use_local and local_html.exists():
						labels = parse_grid_html(local_html.read_text(encoding="utf-8")).get(hhmm, [])
					else:
						times: Dict[str, List[str]] = await fetch_times_for_url(context, url, debug=True, assume_logged_in=True, use_aria=False)
						labels = times.get(hhmm, [])
					logger.debug(f"labels for {hhmm}: {labels}")
					for lbl in labels:
						parsed_cap = parse_capacity_from_label(lbl)
						logger.debug(f"[diagnostic] parsed from label '{lbl}': {parsed_cap}")
				results[hhmm] = cap
				logger.info(f"Final available for {hhmm}: {cap}")
		finally:
			await context.close()
			await browser.close()

	print("\nParsed capacities:")
	for hhmm in target_times:
		print(f"  {hhmm}: {results.get(hhmm, 0)}")
		logger.info(f"Result {hhmm}: {results.get(hhmm, 0)}")
	return 0


if __name__ == "__main__":
	code = asyncio.run(run())
	exit(code)
