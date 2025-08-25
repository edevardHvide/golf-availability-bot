# Golf Availability Monitor - Web Interface

This directory contains the Streamlit web interface for the Golf Availability Monitor, allowing users to configure their preferences through a user-friendly web application.

## 🌟 Features

- **User-Friendly Interface**: Configure golf monitoring preferences through a modern web interface
- **Course Selection**: Multi-select interface for choosing preferred golf courses
- **Time Preferences**: Flexible time slot selection (morning, afternoon, evening, or custom)
- **Player Requirements**: Specify minimum available spots needed
- **Personalized Notifications**: Each user receives notifications based on their specific preferences
- **Email Configuration**: Built-in email validation and testing
- **Export/Import**: Download and share preference configurations

## 🚀 Quick Start

### Option 1: Using the Startup Scripts

**Windows:**
```batch
cd streamlit_app
start_web_interface.bat
```

**Linux/Mac:**
```bash
cd streamlit_app
chmod +x start_web_interface.sh
./start_web_interface.sh
```

### Option 2: Manual Start

1. **Install Dependencies:**
   ```bash
   pip install -r streamlit_app/requirements.txt
   ```

2. **Start the API Server:**
   ```bash
   cd streamlit_app
   python api_server.py
   ```

3. **Start the Streamlit App (in another terminal):**
   ```bash
   cd streamlit_app
   streamlit run app.py
   ```

### Option 3: Docker Deployment

```bash
cd streamlit_app
docker build -t golf-monitor-web .
docker run -p 8501:8501 -p 8000:8000 golf-monitor-web
```

## 🌐 Accessing the Application

- **Web Interface**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health

## 📋 How to Use

1. **Open the Web Interface** at http://localhost:8501

2. **Fill in Your Information:**
   - Full name (for personalized emails)
   - Email address (where notifications will be sent)

3. **Select Golf Courses:**
   - Choose from Oslo area courses or other available courses
   - Courses are grouped geographically for easier selection

4. **Configure Time Preferences:**
   - Choose from preset time ranges (Morning, Afternoon, Evening)
   - Or select custom time slots for more precise control

5. **Set Player Requirements:**
   - Specify minimum number of spots needed for notification

6. **Configure Monitoring Settings:**
   - Days ahead to monitor (1-14 days)
   - Notification frequency (immediate, hourly, daily)

7. **Save Your Preferences:**
   - Click "Save Preferences" to store your configuration
   - Test notifications to ensure email delivery works

## 🔧 Technical Architecture

### Components

1. **Streamlit Frontend** (`app.py`):
   - User interface for preference configuration
   - Real-time validation and preview
   - Course selection with geographic grouping

2. **FastAPI Backend** (`api_server.py`):
   - RESTful API for preference management
   - User preference storage and retrieval
   - Test notification functionality

3. **User Preferences Integration** (`user_preferences_integration.py`):
   - Bridge between web preferences and monitoring system
   - Personalized notification filtering
   - Multi-user support

4. **Personalized Monitor** (`personalized_monitor.py`):
   - Enhanced monitoring with user-specific settings
   - Individual user notification processing
   - Preference-based filtering

### API Endpoints

- `GET /api/courses` - List available golf courses
- `POST /api/preferences` - Save user preferences
- `GET /api/preferences/{email}` - Get user preferences
- `GET /api/preferences` - List all preferences (admin)
- `POST /api/test-notification` - Send test notification
- `DELETE /api/preferences/{email}` - Delete user preferences

### Data Storage

User preferences are stored in `user_preferences.json` in the project root:

```json
{
  "user@example.com": {
    "name": "John Doe",
    "email": "user@example.com",
    "selected_courses": ["oslo_golfklubb", "miklagard_gk"],
    "time_slots": ["10:00", "10:30", "11:00", "14:00"],
    "min_players": 2,
    "days_ahead": 4,
    "notification_frequency": "immediate",
    "timestamp": "2025-01-20T10:30:00"
  }
}
```

## 🚀 Deployment on Render

### Auto-Deploy from Git

1. **Connect Repository**: Link your GitHub repository to Render
2. **Service Type**: Choose "Web Service"
3. **Build Command**: 
   ```bash
   pip install -r streamlit_app/requirements.txt && pip install -r requirements.txt
   ```
4. **Start Command**:
   ```bash
   cd streamlit_app && python api_server.py & sleep 3 && streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.enableCORS false --server.enableXsrfProtection false
   ```

### Environment Variables for Render

Set these in your Render service settings:

```
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SSL=false
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=admin@example.com
```

## 🔧 Integration with Main Monitor

The web interface integrates with the main monitoring system through:

1. **Shared Preferences File**: `user_preferences.json` stores all user configurations
2. **Enhanced Monitor Script**: Reads preferences and personalizes monitoring
3. **Email Override**: Temporarily changes email recipients for personalized notifications

To use with your existing monitor:

```python
from streamlit_app.user_preferences_integration import UserPreferencesManager

# In your monitoring loop
prefs_manager = UserPreferencesManager()
active_users = prefs_manager.get_active_users()

if active_users:
    # Use personalized notifications
    prefs_manager.filter_and_notify_users(new_availability, all_availability)
else:
    # Fall back to default notification
    send_email_notification(...)
```

## 🎨 Customization

### Styling

The app uses custom CSS defined in `app.py`. You can modify:
- Color schemes
- Layout spacing
- Component styling
- Responsive design

### Adding New Features

1. **New Preference Fields**: Add to the Streamlit form and update the API models
2. **Additional Courses**: Golf courses are automatically loaded from `golf_club_urls.py`
3. **Custom Time Ranges**: Modify the `generate_time_slots()` function
4. **Notification Templates**: Customize in `golf_utils.py`

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the correct directory
2. **Port Conflicts**: Check that ports 8501 and 8000 are available
3. **Email Issues**: Verify SMTP settings and app passwords for Gmail
4. **Preference Loading**: Check file permissions for `user_preferences.json`

### Debugging

Enable debug mode by setting environment variables:
```bash
export STREAMLIT_LOG_LEVEL=debug
export FASTAPI_LOG_LEVEL=debug
```

### Logs

- Streamlit logs: Check the terminal where you started the app
- API logs: Check the FastAPI server terminal
- Email logs: Look for `[EMAIL]` prefixed messages

## 📁 File Structure

```
streamlit_app/
├── app.py                          # Main Streamlit application
├── api_server.py                   # FastAPI backend server
├── requirements.txt                # Python dependencies
├── user_preferences_integration.py # Integration with main monitor
├── personalized_monitor.py         # Enhanced monitoring script
├── Dockerfile                      # Docker configuration
├── render_config.txt               # Render deployment settings
├── start_web_interface.bat         # Windows startup script
├── start_web_interface.sh          # Linux/Mac startup script
├── .streamlit/
│   └── config.toml                 # Streamlit configuration
└── README.md                       # This file
```

## 🤝 Contributing

When adding new features:

1. Update both the Streamlit frontend and FastAPI backend
2. Add appropriate validation and error handling
3. Update the documentation
4. Test the integration with the main monitoring system

## 📄 License

This project is part of the Golf Availability Monitor and follows the same license terms.
