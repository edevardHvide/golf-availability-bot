# ⛳ Golf Availability Bot - Complete Notification System

## 🎯 Overview

The Golf Availability Bot is a comprehensive Norwegian golf availability monitoring and notification system. It automatically scrapes golf course availability from Golfbox and sends personalized Norwegian email notifications to users based on their preferences.

## ✨ Key Features

### 🔔 Automated Notifications
- **Daily Morning Reports** (07:00 UTC) - Personalized Norwegian summaries
- **Immediate New Availability Alerts** (every 10 minutes) - Real-time notifications
- **No Duplicate Notifications** - Database prevents repeat alerts
- **Personalized Content** - Tailored to each user's courses and time preferences

### 🌐 Multi-Service Architecture
- **Streamlit UI** - User-friendly preference management
- **FastAPI Backend** - Robust data handling and API endpoints
- **Background Worker** - 24/7 notification monitoring on Render
- **PostgreSQL Database** - Reliable data persistence and tracking

### 🏌️ Golf Course Monitoring
- **Multiple Course Support** - Monitor dozens of golf courses simultaneously
- **Time Window Filtering** - Focus on preferred tee times
- **Real Browser Automation** - Uses Playwright for reliable scraping
- **Smart Login Management** - Persistent session handling

### 📧 Professional Email System
- **Norwegian Language** - All notifications in professional Norwegian
- **Gmail Integration** - Uses your existing Gmail account
- **HTML & Plain Text** - Beautiful formatting with fallback support
- **Error Resilience** - Graceful handling of email service issues

## 🏗️ System Architecture

### Complete Cloud + Local Setup

```mermaid
graph TB
    %% Users and External Systems
    Users[👥 Golf Users]
    Gmail[📧 Gmail SMTP]
    RenderDB[(🐘 PostgreSQL<br/>Database)]
    
    %% Render Services
    subgraph "🌐 Render Cloud Platform"
        UI[🖥️ Streamlit UI<br/>Web Service]
        API[⚙️ FastAPI Server<br/>Web Service] 
        Worker[🔔 Notification Worker<br/>Background Service]
    end
    
    %% Local/External Monitoring
    subgraph "📍 Local/External"
        Monitor[🏌️ Golf Monitor<br/>Scraping System]
        LocalData[📊 Availability Data]
    end
    
    %% User Interactions
    Users -.->|"1. Configure preferences<br/>courses, times, email"| UI
    UI -->|"2. Save user settings"| API
    API -->|"3. Store preferences"| RenderDB
    
    %% Data Flow
    Monitor -->|"4. Scrape golf sites"| LocalData
    LocalData -->|"5. Send availability data"| RenderDB
    
    %% Notification Flow  
    Worker -->|"6a. Check for matches<br/>every 10 minutes"| RenderDB
    Worker -->|"6b. Send daily reports<br/>07:00 UTC"| RenderDB
    Worker -->|"7. Send Norwegian emails"| Gmail
    Gmail -.->|"8. Deliver notifications"| Users
```

### 🔄 User Journey

1. **Setup**: Users configure preferences via Streamlit UI
2. **Monitoring**: Local golf monitor scrapes course availability  
3. **Processing**: Data stored in PostgreSQL database
4. **Notifications**: Background worker sends personalized Norwegian emails
5. **Delivery**: Users receive daily reports and immediate alerts

### 🎯 Three-Service Architecture

| Service | Type | Purpose | Technology |
|---------|------|---------|------------|
| **UI Service** | Web Service | User preference management | Streamlit |
| **API Service** | Web Service | Data operations & endpoints | FastAPI |
| **Notification Worker** | Background Service | Automated email notifications | Python + SMTP |

## 📧 Sample Norwegian Notifications

### Daily Morning Report (07:00 UTC)
```
Subject: ⛳ Daglig golfrapport for John - 3 tilgjengelige tider

Hei John!

Her er din daglige oversikt over tilgjengelige golftider som matcher dine preferanser:

🏌️ Oslo Golf Club:
  📅 I dag (2024-08-28):
    ⏰ 09:00 - 4 plasser
    ⏰ 14:00 - 2 plasser

🏌️ Bergen Golf Course:
  📅 I morgen (2024-08-29):
    ⏰ 10:30 - 3 plasser

Lykke til med å booke! 🍀

Mvh,
Golf Availability Monitor
```

### New Availability Alert (Every 10 minutes)
```
Subject: 🚨 Nye golftider tilgjengelig for John - 2 nye plasser!

Hei John!

Vi har funnet 2 nye golftider som matcher dine preferanser:

🏌️ Oslo Golf Club:
  📅 I dag kl. 15:30 - 2 plasser
  📅 Fredag 01.09 kl. 09:00 - 4 plasser

⚡ Disse tidene er nylig blitt tilgjengelige, så vær rask med å booke!

Lykke til! 🍀

Mvh,
Golf Availability Monitor
```

## 🚀 Quick Start

### For End Users (Receive Notifications)
1. **Access the Streamlit UI** - Configure your golf preferences
2. **Set Your Preferences** - Choose courses, times, and email
3. **Receive Notifications** - Get daily reports and instant alerts

### For System Administrators
1. **Deploy to Render** - Set up the three services (UI, API, Worker)
2. **Configure Email** - Set up Gmail SMTP credentials
3. **Monitor Operation** - Check logs and database for health

## Pre-requisites

- Windows 10/11 or macOS (for local development)
- Render account (for cloud deployment)
- Gmail account (for email notifications)
- No global Python required if you use `uv` (recommended)

## 🔧 Installation & Deployment

### 📋 Render Cloud Deployment (Recommended)

The complete system runs on Render with three services:

#### 1. Deploy UI Service (Streamlit)
```bash
# Service Type: Web Service
# Build Command: pip install -r streamlit_app/requirements.txt
# Start Command: streamlit run streamlit_app/render_streamlit_app.py --server.port=$PORT
```

#### 2. Deploy API Service (FastAPI)  
```bash
# Service Type: Web Service
# Build Command: pip install -r requirements.txt
# Start Command: python streamlit_app/render_api_server_postgresql.py
```

#### 3. Deploy Notification Worker (Background Service)
```bash
# Service Type: Background Worker
# Build Command: pip install -r requirements.txt  
# Start Command: bash render_worker_start.sh
```

#### 4. Environment Variables for Notification Worker
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/db?sslmode=require

# Email (Gmail)
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-gmail-app-password
EMAIL_FROM=your-email@gmail.com
```

### 🏠 Local Development

#### Clone the Repository

```bash
git clone <repository_url>
cd golf-availability-bot
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

### 🆕 **Web Interface Configuration (Recommended)**

The easiest way to configure your preferences is through the web interface:

#### **Quick Start:**
```powershell
# 1. Activate your environment
.venv\Scripts\activate.ps1

# 2. Start the web interface
cd streamlit_app
python run_local.py

# 3. Open http://localhost:8501 in your browser
# 4. Configure your preferences and save

# 5. Start monitoring (in a new terminal)
python golf_availability_monitor.py
```

### **Configuration Examples:**

**Weekend Golfer (Oslo area, afternoons only):**
```bash
SELECTED_CLUBS=oslo,miklagard,bogstad
WEEKEND_MODE=true
WEEKENDS_COUNT=3
TIME_START=13:00
TIME_END=17:00
PLAYER_COUNT=4
```

**Flexible Weekday Player (any club, mornings):**
```bash
SELECTED_CLUBS=
DAYS_AHEAD=14
TIME_START=07:00
TIME_END=12:00
PLAYER_COUNT=2
```

**Specific Tournament Preparation:**
```bash
SELECTED_CLUBS=oslo
SPECIFIC_DATES=2025-02-15,2025-02-16
PREFERRED_TIMES=09:00,10:00,11:00
PLAYER_COUNT=4
MIN_AVAILABLE_SLOTS=2
```

### **Command Line Usage**

You can also use the command-line interface:

```powershell
# Start monitoring with user preferences from web interface
python check_availability.py monitor

# Test notifications
python check_availability.py test-notifications
```

**Note:** The command-line version now uses the enhanced monitoring system that loads user preferences from the web interface. For the best experience, configure your preferences through the web interface first.

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

If you have a Golfbox account, the system will automatically handle authentication. The monitoring system includes smart login capabilities that work with the web interface.

### Email Notifications

To receive email notifications when new tee times are found, set up email configuration in your `.env` file:

```bash
# Copy the example configuration
copy env.example .env

# Edit .env with your email settings
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SSL=false
SMTP_USER=your@gmail.com
SMTP_PASS=your_app_password
EMAIL_FROM=your@gmail.com
EMAIL_TO=recipient@email.com
```

**Common SMTP Settings:**

**Gmail:**
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SSL=false
SMTP_USER=your@gmail.com
SMTP_PASS=your_app_password  # Generate at https://myaccount.google.com/apppasswords
```

**Outlook/Hotmail:**
```bash
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_SSL=false
SMTP_USER=your@outlook.com
SMTP_PASS=your_password
```

**Yahoo:**
```bash
SMTP_HOST=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_SSL=false
SMTP_USER=your@yahoo.com
SMTP_PASS=your_app_password  # Generate in Yahoo Account Security settings
```

**Note:** For Gmail and Yahoo, you'll need to generate an app-specific password rather than using your regular account password.

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

### Web Interface Issues
- Make sure you're in the virtual environment: `.venv\Scripts\activate.ps1`
- Start the web interface: `cd streamlit_app && python run_local.py`
- Access at http://localhost:8501
- API documentation available at http://localhost:8000/docs

## Contributing

Feel free to submit issues and enhancement requests! To add new golf courses:

1. Find the course on golfbox.no
2. Add the course name and slug/ID to `facilities.py`
3. Test with `--debug` flag to ensure it works

## 🔔 Notification System

### Norwegian Email Notifications

The system automatically sends professional Norwegian email notifications:

#### 🌅 Daily Morning Reports (07:00 UTC)
- **Personalized summaries** of available times matching user preferences
- **Course-specific filtering** based on user's selected golf courses
- **Time window filtering** for preferred tee times
- **Only sent when matches exist** - no spam emails

#### ⚡ Immediate New Availability Alerts (Every 10 minutes)
- **Real-time notifications** when new times become available
- **Duplicate prevention** - never sends the same alert twice
- **Professional Norwegian content** with course details and booking urgency
- **Smart timing** - checks every 10 minutes for new opportunities

### 🎯 User Experience

1. **Set Preferences Once** - Configure courses, times, and email via Streamlit UI
2. **Receive Notifications** - Get relevant alerts automatically
3. **Book Quickly** - Norwegian emails with clear course and time information
4. **Stay Informed** - Daily summaries keep you updated on availability trends

### 📊 System Monitoring

- **Database Tracking** - All notifications logged for analytics
- **Error Resilience** - System continues operating even if email service is temporarily down
- **Health Monitoring** - Render dashboard shows all service status and logs
- **Scalable Architecture** - Handles multiple users with personalized notifications

### 🔧 Technical Implementation

- **Background Worker** - Runs 24/7 on Render cloud platform
- **PostgreSQL Database** - Reliable data persistence and duplicate prevention
- **Gmail SMTP** - Professional email delivery using your existing Gmail account
- **Norwegian Templates** - Culturally appropriate and professional email content

## License

This project is licensed under the terms of the license specified in the [LICENSE](LICENSE) file.