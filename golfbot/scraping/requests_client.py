from __future__ import annotations

import os
import re
import datetime
from typing import Dict, List

import requests
from bs4 import BeautifulSoup
from rich.console import Console

from golfbot.grid_parser import parse_grid_html


console = Console()


def ensure_session(session: requests.Session | None) -> requests.Session:
    """Return a configured requests.Session with desktop-like headers."""
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


def apply_manual_cookies(session: requests.Session, cookie_strings: list[str] | None) -> None:
    """Apply semi-colon separated cookie header strings onto the session jar."""
    if not cookie_strings:
        return
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
                existing = session.headers.get("Cookie", "")
                combined = (existing + "; " if existing else "") + f"{name}={value}"
                session.headers["Cookie"] = combined


def login_to_golfbox(session: requests.Session, email: str, password: str) -> bool:
    """Best-effort login to golfbox.golf; returns True if it appears logged in."""
    try:
        login_url = "https://golfbox.golf/#/"
        r = session.get(login_url)
        r.raise_for_status()

        if "myFrontPage" in r.url and "login" not in r.text.lower():
            return True

        soup = BeautifulSoup(r.text, "html.parser")
        login_form = soup.find("form") or soup.find("form", {"action": re.compile(r"login", re.I)})

        if not login_form:
            # Try common endpoints
            for endpoint in (
                "https://golfbox.golf/api/login",
                "https://golfbox.golf/login",
                "https://golfbox.golf/auth/login",
            ):
                try:
                    payload = {
                        "email": email,
                        "password": password,
                        "username": email,
                        "user": email,
                        "brukernavn": email,
                        "passord": password,
                    }
                    pr = session.post(endpoint, data=payload, headers={"Referer": login_url}, allow_redirects=True)
                    if pr.status_code == 200:
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
            action = login_form.get("action", "")
            method = login_form.get("method", "post").lower()
            if action and not action.startswith("http"):
                if action.startswith("/"):
                    action = f"https://golfbox.golf{action}"
                else:
                    action = f"https://golfbox.golf/{action}"
            elif not action:
                action = login_url

            payload: Dict[str, str] = {}
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

            if method == "get":
                pr = session.get(action, params=payload, headers={"Referer": login_url}, allow_redirects=True)
            else:
                pr = session.post(action, data=payload, headers={"Referer": login_url}, allow_redirects=True)
            pr.raise_for_status()

            home = session.get("https://golfbox.golf/#/")
            if home.status_code == 200 and (
                "logout" in home.text.lower()
                or "logg ut" in home.text.lower()
                or "min side" in home.text.lower()
                or "dashboard" in home.text.lower()
            ):
                return True
    except Exception as e:
        try:
            console.print(f"[dim red]Login attempt failed: {e}[/dim red]")
        except Exception:
            pass
        return False
    return False


def fetch_golfbox_grid(session: requests.Session, grid_url: str, target_date: datetime.date, debug: bool = False) -> Dict[str, List[str]]:
    """Fetch and parse GolfBox legacy grid HTML for a given URL/date."""
    date_str = target_date.strftime("%Y-%m-%d")
    candidate_urls: List[str] = []
    base = grid_url
    if "?" in base:
        candidate_urls.extend([
            f"{base}&date={date_str}",
            f"{base}&dato={date_str}",
            f"{base}&resdate={date_str}",
            f"{base}&selectedDate={date_str}",
        ])
    else:
        candidate_urls.extend([
            f"{base}?date={date_str}",
            f"{base}?dato={date_str}",
            f"{base}?resdate={date_str}",
            f"{base}?selectedDate={date_str}",
        ])
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
                    with open(os.path.join(out_dir, f"grid-{date_str}.html"), "w", encoding="utf-8") as f:
                        f.write(html)
                except Exception:
                    pass
            parsed = parse_grid_html(html)
            if parsed:
                return parsed
        except Exception as e:
            last_error = e
            if debug:
                try:
                    console.print(f"[dim yellow]Grid fetch failed: {url} → {e}[/dim yellow]")
                except Exception:
                    pass

    if debug and last_error:
        try:
            console.print(f"[dim red]All grid attempts failed: {last_error}[/dim red]")
        except Exception:
            pass
    return {}


