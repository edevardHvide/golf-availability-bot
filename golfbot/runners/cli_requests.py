from __future__ import annotations

import argparse
import datetime
import os
from typing import Optional

from rich.console import Console

from golfbot.core.availability import fetch_available_tee_times


console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch tee times once via requests")
    parser.add_argument("--course", required=True)
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    date = (
        datetime.date(*map(int, args.date.split("-"))) if args.date else datetime.date.today()
    )

    times = fetch_available_tee_times(args.course.strip(), date, debug=args.debug)
    if not times:
        console.print("No available tee times found.")
        return
    console.print(f"Available tee times for {args.course.capitalize()} on {date}:")
    for hhmm in sorted(times.keys()):
        console.print(f"  {hhmm}: {', '.join(times[hhmm])}")


if __name__ == "__main__":
    main()


