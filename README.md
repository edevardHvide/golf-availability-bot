# Golf Availability Bot

## Overview

The Golf Availability Bot is a Python application designed to check and notify users about available tee times for golf courses listed on the Golfbox booking website (`https://golfbox.golf/#/`). It uses web scraping techniques to fetch the available tee times for a specified golf course and date.

## Features

- Fetches available tee times for a given golf course and date from Golfbox's website.
- Sends desktop notifications when new tee times become available.
- Supports monitoring multiple golf courses simultaneously.
- Time filtering to focus on specific time ranges (e.g., afternoon rounds).
- Beautiful console output with colored tables and status indicators.

### New: Playwright-based Local Runner (optional)

- Uses a real Chromium browser via Playwright
- Persists login cookies/localStorage in `state.json` so you rarely need to log in again
- Directly navigates to your GolfBox legacy grid URL(s)
- Parses for "Ledig/Available" slots using text and ARIA heuristics
- Checks every 5 minutes with a small jitter and only notifies on new openings

## Pre-requisites

- Windows 10/11 or macOS
- No global Python required if you use `uv` (recommended)

## Installation

### Clone the Repository

First, clone the repository to your local machine:

```bash
git clone <repository_url>
```

### Install with uv (recommended)

uv will install a local Python and create a virtual environment automatically.

```powershell
# 1) Install uv (once)
powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2) Clone and enter the repo
git clone <repository_url>
cd golf-availability-bot

# 3) One-off run (ephemeral env)
uv run --python 3.11 --with requests --with beautifulsoup4 --with rich --with win10toast python check_availability.py monitor

# Or create a reusable venv
uv python install 3.11
uv venv --python 3.11 .venv
./.venv/Scripts/Activate.ps1
uv pip install -r requirements.txt
```

### Alternative: Install with Poetry

```bash
# Install Poetry if you don't have it
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

### One-time Playwright browser install

After installing Python dependencies, install the Chromium runtime for Playwright:

```powershell
python -m playwright install chromium
```
```

## Usage

### Run the monitor

```powershell
python check_availability.py monitor --between 14-18 --days-ahead 2
```

Examples:
```powershell
# Only today, 14:00–18:00 (afternoon rounds)
python check_availability.py monitor --days-ahead 0 --between 14-18

# Specific dates
python check_availability.py monitor --dates 2025-08-20,2025-08-21

# Morning rounds only
python check_availability.py monitor --between 7-12

# Use GolfBox legacy grid for a specific course
python check_availability.py monitor \
  --course-grid "oslo golfklubb=https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?clubid=123" \
  --dates 2025-08-20
```

### Test notifications
```powershell
python check_availability.py test-notifications

### Run the Playwright runner (legacy grid URLs)

1) Create a `.env` file in the project root (see `.env.example`) with at least:

```
GOLFBOX_GRID_URL=https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?...  
# Optional
GOLFBOX_USER=you@example.com
GOLFBOX_PASS=yourpassword
HEADLESS=true
CHECK_INTERVAL_SECONDS=300
JITTER_SECONDS=20
PERSIST_NOTIFIED=false
```

You can provide multiple grid URLs by separating them with commas in `GOLFBOX_GRID_URL`.

2) Start the runner:

```powershell
python playwright_runner.py
```

Notes:
- First run may open a login page; if `GOLFBOX_USER`/`GOLFBOX_PASS` are set the runner will try to log you in; otherwise log in once manually and the session will be saved to `state.json`.
- HTML snapshots and screenshots are saved under `debug_html/` if debugging is enabled in code.
```

### Authentication (Optional)

If you have a Golfbox account, you can provide credentials to access member-only tee times:

```powershell
# Using command line arguments
python check_availability.py monitor --email your@email.com --password yourpassword

# Using environment variables (recommended for security)
set GOLFBOX_EMAIL=your@email.com
set GOLFBOX_PASSWORD=yourpassword
python check_availability.py monitor
```

### Command Line Options

- `--days-ahead N`: Monitor N days ahead (default: 2)
- `--start-date YYYY-MM-DD`: Start monitoring from specific date
- `--dates YYYY-MM-DD,YYYY-MM-DD`: Monitor specific dates only
- `--between HH-HH`: Filter tee times within time range (e.g., 14-18)
- `--email EMAIL`: Golfbox account email
- `--password PASSWORD`: Golfbox account password
- `--debug`: Show detailed scraping information
- `--cookie "cookie_string"`: Manual cookie authentication
- `--course-id NAME=ID`: Override course name to GolfBox numeric id
- `--course-grid NAME=URL`: Use GolfBox legacy grid URL for this course (e.g. `https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?...`)

References:
- GolfBox app login and main app: [golfbox.golf](https://golfbox.golf/#/)
- Legacy grid endpoint example: [grid.asp](https://www.golfbox.no/site/my_golfbox/ressources/booking/grid.asp?)

## Golf Courses

The bot monitors the following golf courses by default:

- Oslo Golfklubb
- Miklagard Golfklubb  
- Bogstad Golfklubb
- Losby Gods
- Holtsmark Golfklubb
- Bjaavann Golfklubb
- Drammen Golfklubb
- Asker Golfklubb
- Vestfold Golfklubb
- Moss Golfklubb

You can modify the `facilities.py` file to add or remove golf courses.

## Notifications

- On Windows, notifications use `win10toast` to show toast popups.
- On macOS, notifications use AppleScript alerts via `osascript`.
- If Focus Assist (Do Not Disturb) is on, toasts may be suppressed.

## Legend

- 🏌️ 18-hole rounds
- ⛳ 9-hole rounds  
- 🎯 General tee times
- 🆕 Newly available slots (highlighted in green)
- ❌ Recently taken slots (highlighted with strikethrough)

## Optional: Start automatically at login (Windows)

Use Task Scheduler → Create Task → Run only when user is logged on.

Program/script:
```
C:\Users\<you>\git\golf-availability-bot\.venv\Scripts\python.exe
```
Arguments:
```
check_availability.py monitor --between 14-18

Or for the Playwright runner:
```
playwright_runner.py
```
```
Start in:
```
C:\Users\<you>\git\golf-availability-bot
```

## Troubleshooting

### Login Issues
- Make sure your Golfbox credentials are correct
- Some courses may require special membership access
- Try using browser cookies if login fails

### No Tee Times Found
- Check if the golf course is available on golfbox.no
- Try running with `--debug` to see detailed information
- Verify the course name matches those in `facilities.py`

### Notification Issues
- Run `python check_availability.py test-notifications` to verify alerts work
- On Windows, check if notifications are enabled in system settings
- On macOS, grant Terminal permission to control your computer if prompted

## Contributing

Feel free to submit issues and enhancement requests! To add new golf courses:

1. Find the course on golfbox.no
2. Add the course name and slug/ID to `facilities.py`
3. Test with `--debug` flag to ensure it works

## License

This project is licensed under the terms of the license specified in the [LICENSE](LICENSE) file.