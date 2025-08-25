# Local Testing Guide for Golf Monitor Streamlit App

## 🚀 Quick Start

### Step 1: Navigate to the Streamlit App Directory
```bash
cd streamlit_app
```

### Step 2: Run the Local Test (Windows)
```batch
test_local.bat
```

### Step 3: Run the Local Test (Linux/Mac)
```bash
python run_local.py
```

## 📋 What the Local Test Does

1. **Installs Dependencies**: Automatically installs all required Python packages
2. **Starts API Server**: Launches the FastAPI backend on port 8000
3. **Starts Streamlit App**: Launches the web interface on port 8501
4. **Health Monitoring**: Monitors both services and restarts if needed

## 🌐 Accessing the App

Once running, you can access:

- **Web Interface**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health

## 🧪 Testing the App

After starting the services, run the test script to verify everything is working:

```bash
python test_app.py
```

This will test:
- ✅ API server connectivity
- ✅ Golf courses endpoint
- ✅ User preferences saving
- ✅ File storage
- ✅ Streamlit app accessibility

## 📝 How to Use the Interface

1. **Fill in Your Details**:
   - Name: Your full name for personalized emails
   - Email: Where you'll receive notifications

2. **Select Golf Courses**:
   - Choose from Oslo area courses or other available courses
   - Courses are grouped geographically for easier selection

3. **Set Time Preferences**:
   - Morning (6:00-12:00)
   - Afternoon (12:00-17:00)
   - Evening (17:00-20:00)
   - Custom: Select specific time slots

4. **Configure Settings**:
   - Minimum players required (1-4)
   - Days ahead to monitor (1-14)
   - Notification frequency (immediate, hourly, daily)

5. **Save and Test**:
   - Click "Save Preferences" to store your settings
   - Click "Test Notification" to verify email delivery

## 🎯 Demo Mode Features

The app runs in demo mode when the main golf monitoring system isn't available:

- **Demo Courses**: Shows a sample list of Norwegian golf courses
- **Mock Notifications**: Test notifications work but don't send real emails
- **All Features Available**: You can test the full interface functionality

## 📁 Data Storage

Your preferences are saved in:
```
golf-availability-bot/user_preferences.json
```

Example format:
```json
{
  "user@example.com": {
    "name": "John Doe",
    "email": "user@example.com",
    "selected_courses": ["oslo_golfklubb", "miklagard_gk"],
    "time_slots": ["10:00", "10:30", "14:00"],
    "min_players": 2,
    "days_ahead": 4,
    "notification_frequency": "immediate",
    "timestamp": "2025-08-25T10:30:00"
  }
}
```

## 🔧 Troubleshooting

### Port Already in Use
If you get port errors:
```bash
# Check what's using the ports
netstat -ano | findstr :8501
netstat -ano | findstr :8000

# Kill the processes if needed
taskkill /PID <process_id> /F
```

### Dependencies Issues
If installation fails:
```bash
# Update pip first
python -m pip install --upgrade pip

# Install manually
pip install streamlit fastapi uvicorn pydantic[email]
```

### Import Errors
If you see import errors:
- Make sure you're in the `streamlit_app` directory
- The app automatically handles missing golf monitoring components

### Email Testing
For email testing to work, you need to set up environment variables:
```bash
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
EMAIL_FROM=your-email@gmail.com
```

## 🛑 Stopping the Services

To stop the local development server:
- Press `Ctrl+C` in the terminal where you started it
- Or close the terminal window

The script will automatically clean up both the API server and Streamlit processes.

## 🔄 Restarting

To restart after making changes:
1. Stop the current services (Ctrl+C)
2. Run the startup script again
3. The app will pick up any code changes automatically

## 📊 Next Steps

Once you've tested locally and are satisfied with the interface:

1. **Cloud Database Integration**: We'll add the JSON database fetching functionality
2. **Production Deployment**: Deploy to Render or another cloud platform
3. **Integration**: Connect with your main golf monitoring system

## 💡 Tips for Development

- **Code Changes**: Streamlit auto-reloads when you save changes to `app.py`
- **API Changes**: Restart the local server to pick up changes to `api_server.py`
- **Debugging**: Check the terminal output for detailed logs and error messages
- **Browser Console**: Use F12 in your browser to see any frontend errors
