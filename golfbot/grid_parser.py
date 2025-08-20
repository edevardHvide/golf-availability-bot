from __future__ import annotations

import os
import re
from typing import Dict, List

from bs4 import BeautifulSoup


# Shared time pattern (HH:MM)
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")


def parse_grid_html(html: str) -> Dict[str, List[str]]:
    """Parse GolfBox booking grids from HTML into { 'HH:MM': ['label', ...] }.

    Supports two main structures:
    - Table-based legacy grids: detect available cells and map to time + column.
    - Tile-based grids: compute available seats per time based on icons/rows/attrs.
    """
    soup = BeautifulSoup(html, "html.parser")

    # ----------------------------- Table-based grid -----------------------------
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
        # Exclude explicitly non-full availability hints
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
    for row in row_iter:
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

    # ----------------------------- Tile-based grid ------------------------------
    if not tee_times:
        tile_total: Dict[str, int] = {}

        def extract_hhmm_from_iso(s: str) -> str | None:
            # Example: 20250815T203000 → 20:30
            m = re.search(r"T(\d{2})(\d{2})", s)
            if m:
                return f"{m.group(1)}:{m.group(2)}"
            return None

        tiles = soup.select("div.hour, .booking-slot, .time-slot")

        def _read_available_from_text(text: str) -> int | None:
            if not text:
                return None
            try:
                low = text.lower()
                # Common phrases in NO/EN for availability
                if any(k in low for k in ["ledig", "ledige", "available", "free", "spots", "plass", "plasser"]):
                    m = re.search(r"(\d+)", low)
                    if m:
                        n = int(m.group(1))
                        if n >= 0:
                            return n
            except Exception:
                return None
            return None

        def _read_capacity_attr(el) -> int | None:
            try:
                if not el:
                    return None
                for key in ("data-capacity", "data-slots", "data_capacity", "data_slots"):
                    val = el.get(key)
                    if val is None and hasattr(el, "attrs"):
                        val = el.attrs.get(key)
                    if val is None:
                        continue
                    m = re.search(r"\d+", str(val))
                    if m:
                        n = int(m.group(0))
                        if n > 0:
                            return n
            except Exception:
                return None
            return None

        for tile in tiles:
            # Skip non-bookable groupings (e.g., tournaments)
            try:
                classes = " ".join(tile.get("class", [])).lower()
                if ("tournament" in classes) or (tile.get("data-grouping") is not None):
                    continue
            except Exception:
                pass

            time_text = None
            time_div = tile.find(class_=re.compile(r"\btime\b", re.I))
            if time_div:
                txt = time_div.get_text(" ", strip=True)
                m = TIME_RE.search(txt)
                if m:
                    time_text = m.group(0)
            if not time_text:
                m = TIME_RE.search(tile.get_text(" ", strip=True))
                if m:
                    time_text = m.group(0)
            if not time_text:
                onclick = tile.get("onclick") or ""
                parsed = extract_hhmm_from_iso(onclick)
                if parsed:
                    time_text = parsed
            if not time_text:
                continue

            try:
                try:
                    env_capacity = int(os.getenv("TEE_CAPACITY", "4"))
                except Exception:
                    env_capacity = 4

                # Detect booked players
                players = 0
                total_rows = 0
                flight = tile.find(class_=re.compile(r"\btime-players\b", re.I))
                if flight:
                    direct_rows = [child for child in flight.find_all("div", recursive=False)]
                    row_blocks = []
                    for row in direct_rows:
                        cls = " ".join(row.get("class", [])).lower()
                        if all(k in cls for k in ("d-flex", "align-items-center", "row", "flex-nowrap")):
                            row_blocks.append(row)
                    total_rows = len(row_blocks)
                    for row in row_blocks:
                        name_cell = row.find(class_=re.compile(r"\bfw-bold\b", re.I))
                        if name_cell and name_cell.get_text(strip=True):
                            players += 1
                else:
                    # Mobile/classic: icons per booked player
                    item = tile.find(class_=re.compile(r"\bitem\b", re.I))
                    if item:
                        players = len(item.find_all("img"))
                    if players == 0:
                        players = len(tile.select("img[src*='bookinggrid/greenfee']"))

                # Try to read explicit available spots from attributes/text first
                available_from_text: int | None = None
                # aria-label/title on tile
                for key in ("aria-label", "title", "data-original-title"):
                    val = tile.get(key)
                    if val:
                        available_from_text = _read_available_from_text(str(val))
                        if available_from_text is not None:
                            break
                if available_from_text is None:
                    # Check child clickable elements
                    clickable = tile.find(["a", "button"], string=True) or tile.find(["a", "button"]) or tile
                    if clickable:
                        cand = clickable.get("aria-label") or clickable.get("title") or clickable.get_text(" ", strip=True)
                        available_from_text = _read_available_from_text(str(cand) if cand else "")

                cap_attr = _read_capacity_attr(tile) or _read_capacity_attr(flight) or _read_capacity_attr(tile.find(class_=re.compile(r"\bitem\b", re.I)) if tile else None)
                if cap_attr and cap_attr > 0:
                    capacity = cap_attr
                elif total_rows and total_rows > players:
                    capacity = total_rows
                else:
                    capacity = env_capacity

                if available_from_text is not None:
                    available = max(0, int(available_from_text))
                else:
                    classes = " ".join(tile.get("class", [])).lower()
                    if "full" in classes:
                        available = 0
                    elif "free" in classes and players == 0:
                        available = capacity
                    else:
                        available = max(0, capacity - players)

                if available > 0:
                    current = tile_total.get(time_text, 0)
                    tile_total[time_text] = current + available
            except Exception:
                # Best-effort fallback: assume env capacity free for this tile
                current = tile_total.get(time_text, 0)
                tile_total[time_text] = current + (env_capacity if 'env_capacity' in locals() else 4)

        if tile_total:
            simplified: Dict[str, List[str]] = {}
            for hhmm, total in tile_total.items():
                n = max(0, int(total)) if total is not None else 0
                label = f"{n} spot{'s' if n != 1 else ''} available"
                simplified[hhmm] = [label]
            return simplified

    return tee_times


