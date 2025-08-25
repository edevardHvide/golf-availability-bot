"""
FastAPI Backend for Golf Availability Monitor

This provides the API endpoints for the Streamlit frontend to save user preferences
and integrates with the monitoring system.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional
import json
import os
from pathlib import Path
from datetime import datetime
import uvicorn

# Import the golf monitoring functions
import sys
sys.path.append(str(Path(__file__).parent.parent))

try:
    from golf_utils import send_email_notification
    from golf_club_urls import golf_url_manager
    GOLF_SYSTEM_AVAILABLE = True
except ImportError:
    GOLF_SYSTEM_AVAILABLE = False
    print("Warning: Golf monitoring system not available. Running in demo mode.")

app = FastAPI(
    title="Golf Availability Monitor API",
    description="API for managing golf tee time monitoring preferences",
    version="1.0.0"
)

# Add CORS middleware for Streamlit integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class UserPreferences(BaseModel):
    name: str
    email: EmailStr
    selected_courses: List[str]
    time_slots: List[str]
    min_players: int = 1
    days_ahead: int = 4
    notification_frequency: str = "immediate"
    timestamp: Optional[str] = None

class PreferencesResponse(BaseModel):
    success: bool
    message: str
    user_count: Optional[int] = None

class TestNotificationRequest(BaseModel):
    email: EmailStr
    name: str

# Data storage (in production, use a proper database)
PREFERENCES_FILE = Path(__file__).parent.parent / "user_preferences.json"

def load_preferences() -> Dict:
    """Load user preferences from file."""
    if PREFERENCES_FILE.exists():
        with open(PREFERENCES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_preferences(preferences: Dict):
    """Save user preferences to file."""
    with open(PREFERENCES_FILE, 'w') as f:
        json.dump(preferences, f, indent=2)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Golf Availability Monitor API",
        "version": "1.0.0",
        "endpoints": {
            "preferences": "/api/preferences",
            "courses": "/api/courses",
            "test_notification": "/api/test-notification"
        }
    }

@app.get("/api/courses")
async def get_courses():
    """Get available golf courses."""
    if GOLF_SYSTEM_AVAILABLE:
        courses = []
        for key, club in golf_url_manager.clubs.items():
            courses.append({
                'key': key,
                'name': club.display_name,
                'location': club.location,
                'default_start_time': club.default_start_time
            })
        
        return {
            "courses": sorted(courses, key=lambda x: x['name']),
            "total": len(courses)
        }
    else:
        # Demo data for testing
        demo_courses = [
            {'key': 'oslo_golfklubb', 'name': 'Oslo Golfklubb', 'location': [59.91, 10.75], 'default_start_time': '070000'},
            {'key': 'miklagard_gk', 'name': 'Miklagard GK', 'location': [59.97, 11.04], 'default_start_time': '070000'},
            {'key': 'baerum_gk', 'name': 'Bærum GK', 'location': [59.89, 10.52], 'default_start_time': '060000'},
            {'key': 'bogstad_golfklubb', 'name': 'Bogstad Golfklubb', 'location': [59.95, 10.63], 'default_start_time': '070000'},
        ]
        
        return {
            "courses": demo_courses,
            "total": len(demo_courses),
            "demo_mode": True
        }

@app.post("/api/preferences", response_model=PreferencesResponse)
async def save_user_preferences(preferences: UserPreferences):
    """Save user preferences for golf monitoring."""
    try:
        # Load existing preferences
        all_preferences = load_preferences()
        
        # Add timestamp if not provided
        prefs_dict = preferences.dict()
        if not prefs_dict.get('timestamp'):
            prefs_dict['timestamp'] = datetime.now().isoformat()
        
        # Save preferences keyed by email
        all_preferences[preferences.email] = prefs_dict
        
        # Save to file
        save_preferences(all_preferences)
        
        return PreferencesResponse(
            success=True,
            message=f"Preferences saved successfully for {preferences.name}",
            user_count=len(all_preferences)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save preferences: {str(e)}")

@app.get("/api/preferences/{email}")
async def get_user_preferences(email: str):
    """Get preferences for a specific user."""
    all_preferences = load_preferences()
    
    if email not in all_preferences:
        raise HTTPException(status_code=404, detail="User preferences not found")
    
    return all_preferences[email]

@app.get("/api/preferences")
async def get_all_preferences():
    """Get all user preferences (admin endpoint)."""
    all_preferences = load_preferences()
    
    return {
        "preferences": all_preferences,
        "user_count": len(all_preferences),
        "last_updated": max([p.get('timestamp', '') for p in all_preferences.values()] or ['Never'])
    }

@app.post("/api/test-notification")
async def send_test_notification(request: TestNotificationRequest):
    """Send a test notification to the user."""
    if not GOLF_SYSTEM_AVAILABLE:
        # In demo mode, just return success
        return {
            "success": True, 
            "message": f"Test notification sent to {request.email} (Demo Mode)",
            "demo_mode": True
        }
    
    try:
        # Create test availability data
        test_availability = [
            f"Oslo Golfklubb on {datetime.now().strftime('%Y-%m-%d')} at 10:00: 2 spots available",
            f"Miklagard GK on {datetime.now().strftime('%Y-%m-%d')} at 14:30: 4 spots available"
        ]
        
        # Temporarily set email recipient for test
        original_email_to = os.environ.get('EMAIL_TO', '')
        os.environ['EMAIL_TO'] = request.email
        
        try:
            # Send test notification
            send_email_notification(
                subject=f"🧪 Test Notification for {request.name}",
                new_availability=test_availability,
                time_window="Test Mode",
                config_info={
                    'courses': 2,
                    'time_window': 'All Day',
                    'min_players': 1,
                    'notification_type': 'Test'
                }
            )
            
            return {"success": True, "message": f"Test notification sent to {request.email}"}
        
        finally:
            # Restore original email setting
            if original_email_to:
                os.environ['EMAIL_TO'] = original_email_to
            elif 'EMAIL_TO' in os.environ:
                del os.environ['EMAIL_TO']
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test notification: {str(e)}")

@app.delete("/api/preferences/{email}")
async def delete_user_preferences(email: str):
    """Delete preferences for a specific user."""
    all_preferences = load_preferences()
    
    if email not in all_preferences:
        raise HTTPException(status_code=404, detail="User preferences not found")
    
    del all_preferences[email]
    save_preferences(all_preferences)
    
    return {"success": True, "message": f"Preferences deleted for {email}"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "preferences_file_exists": PREFERENCES_FILE.exists(),
        "user_count": len(load_preferences())
    }

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
