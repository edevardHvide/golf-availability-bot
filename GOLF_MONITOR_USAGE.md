# 🏌️ Golf Availability Monitor - Usage Guide

## Overview

Your golf monitoring system now supports both **scheduled notifications** and **immediate on-demand checks** with a perfect hybrid approach:

- **Local Machine**: Runs Playwright for web scraping and scheduled notifications
- **Web UI**: Deployed on Render for user management and immediate checks
- **Best of Both Worlds**: Reliable scheduled monitoring + on-demand checking

## 🚀 Quick Start

### 1. Scheduled Monitoring (Recommended)

Run scheduled notifications at 9am, 12pm, and 9pm:

```bash
python start_golf_monitor.py scheduled
```

Or directly:
```bash
python golf_availability_monitor.py --scheduled
```

### 2. Enable Immediate Checks

Start the local API server to enable immediate checks from the web UI:

```bash
python start_golf_monitor.py api
```

Or directly:
```bash
python local_api_server.py
```

### 3. Use the Web UI

- **Create profiles** at your Streamlit app (deployed on Render)
- **Set weekday/weekend preferences** with custom time intervals
- **Click "⚡ Check Now"** for immediate availability checks
- **View results** directly in the UI

## 📋 Available Modes

### 🕘 Scheduled Mode (Default Recommendation)
```bash
python golf_availability_monitor.py --scheduled
```
- **When**: Automatically runs at 9am, 12pm, and 9pm
- **Notifications**: Email sent to all users with their personalized results
- **Weekday/Weekend**: Respects different preferences for weekdays vs weekends
- **Efficient**: Only runs when needed, saves resources

### 🌐 Local API Mode (For Immediate Checks)
```bash
python local_api_server.py
```
- **Purpose**: Enables immediate checks from web UI
- **Port**: Runs on http://localhost:5000
- **Features**: 
  - Health check endpoint
  - Immediate availability checking
  - Results display in web UI
  - User-specific email notifications

### ⚡ Immediate Check Mode
```bash
python golf_availability_monitor.py --immediate
```
- **When**: Single check, then exits
- **Use Case**: Manual testing or one-off checks
- **Results**: Returns structured data for API consumption

### 🔄 Continuous Mode (Legacy)
```bash
python golf_availability_monitor.py
```
- **When**: Checks every 5 minutes continuously
- **Use Case**: If you want constant monitoring (resource intensive)

## 🌟 Recommended Setup

### For Daily Use:
1. **Start scheduled monitoring** in the morning:
   ```bash
   python start_golf_monitor.py scheduled
   ```

2. **Start local API server** (optional, for immediate checks):
   ```bash
   python start_golf_monitor.py api
   ```

3. **Use the web UI** for:
   - Creating and managing user profiles
   - Setting different weekday/weekend preferences
   - Running immediate checks when needed

## 📊 Web UI Features

### Profile Management
- **Weekday/Weekend Preferences**: Different time preferences for work days vs weekends
- **Time Intervals**: Define ranges like "07:00-09:00" instead of individual slots
- **Golf Course Selection**: Choose from 25+ Norwegian golf courses
- **Personalized Settings**: Minimum players, days ahead, etc.

### Immediate Availability Check
- **⚡ Check Now Button**: Triggers immediate availability check
- **Real-time Results**: Shows availability within 1-2 minutes
- **User-specific**: Only shows results matching your preferences
- **Email Notification**: Sends personalized email to just you

### Status Indicators
- **🟢 System Online**: Local monitor is running and connected
- **🟡 API Offline**: Local monitor not running (scheduled only)
- **🔴 System Issues**: Connection problems

## 🛠️ Configuration

### User Preferences Structure
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "preference_type": "Different for weekdays/weekends",
  "time_preferences": {
    "weekdays": {
      "time_intervals": ["07:00-09:00", "17:00-19:00"],
      "method": "Custom Time Intervals"
    },
    "weekends": {
      "time_intervals": ["09:00-12:00"],
      "method": "Custom Time Intervals"
    }
  },
  "selected_courses": ["oslo_golfklubb", "baerum_gk"],
  "min_players": 2,
  "days_ahead": 4
}
```

### Environment Variables
```bash
# Optional: Specify which courses to monitor (if no user preferences)
SELECTED_CLUBS="oslo_golfklubb,baerum_gk,miklagard_gk"

# Optional: API URL for cloud deployment
API_URL="https://your-app.onrender.com"
```

## 📧 Email Notifications

### Scheduled Notifications (9am, 12pm, 9pm)
- **All Users**: Receive personalized emails based on their preferences
- **Weekday/Weekend Aware**: Different results based on day type
- **Course Filtering**: Only shows selected courses
- **Time Filtering**: Only shows preferred time slots
- **New Availability**: Highlights newly available slots

### Immediate Check Notifications
- **Single User**: Only the requesting user receives email
- **Real-time**: Sent immediately after check completes
- **Web UI Display**: Results also shown in the web interface

## 🔧 Troubleshooting

### Local Monitor Not Running
**Symptom**: "Cannot connect to local golf monitor" in web UI

**Solution**:
```bash
# Start the local API server
python local_api_server.py

# Or start scheduled monitoring
python golf_availability_monitor.py --scheduled
```

### Authentication Issues
**Symptom**: "Authentication failed" messages

**Solution**:
1. Run the monitor manually first to complete login
2. Browser window will open for manual authentication
3. Once authenticated, scheduled mode will work automatically

### No Email Notifications
**Symptom**: System runs but no emails sent

**Solution**:
1. Check email configuration in `golf_utils.py`
2. Verify user profiles exist in the system
3. Check that users have valid email addresses

### Web UI Connection Issues
**Symptom**: Cannot access Streamlit app

**Solution**:
1. Check if deployed on Render
2. Verify API endpoints are accessible
3. Check local fallback files exist

## 📱 Usage Examples

### Example 1: Weekend Golfer
```python
# Profile setup
{
  "preference_type": "Different for weekdays/weekends",
  "weekdays": {"time_intervals": []},  # No weekday golf
  "weekends": {"time_intervals": ["08:00-12:00"]}  # Weekend morning golf
}

# Will only get notifications on weekends for 8am-12pm slots
```

### Example 2: Early Bird Golfer
```python
# Profile setup
{
  "preference_type": "Same for all days",
  "all_days": {"time_intervals": ["06:00-08:00"]}  # Early morning only
}

# Will get notifications for 6-8am slots every day
```

### Example 3: Flexible Golfer
```python
# Profile setup
{
  "preference_type": "Different for weekdays/weekends",
  "weekdays": {"time_intervals": ["16:00-19:00"]},  # After work
  "weekends": {"time_intervals": ["08:00-18:00"]}   # All day weekends
}

# Different notifications based on day type
```

## 🎯 Best Practices

1. **Use Scheduled Mode**: More efficient than continuous monitoring
2. **Set Realistic Preferences**: Don't select all time slots - be specific
3. **Different Weekday/Weekend**: Most users prefer different times
4. **Monitor Multiple Courses**: Increases chances of finding availability
5. **Check Immediate Results**: Use web UI for urgent tee time needs
6. **Keep Local Monitor Running**: For best experience with immediate checks

## 🆘 Support

- **Logs**: Check console output for detailed information
- **Debug Mode**: Use `--immediate` mode for testing
- **Health Check**: Visit http://localhost:5000/health when API is running
- **Web UI Status**: Check connection indicators in sidebar

Happy golfing! ⛳
