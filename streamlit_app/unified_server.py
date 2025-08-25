"""
Unified Server for Golf Availability Monitor

This serves both the FastAPI backend and the Streamlit frontend on the same port.
Perfect for Render deployment where only one port is exposed.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from typing import List, Dict
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
import uvicorn
import requests

# Import the golf monitoring functions
import sys
sys.path.append(str(Path(__file__).parent.parent))

try:
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class UserPreferences(BaseModel):
    name: str
    email: EmailStr
    selected_courses: List[str]
    time_slots: List[str]

# Data storage
PREFERENCES_FILE = Path(__file__).parent / "user_preferences.json"

def load_preferences() -> Dict:
    """Load preferences from JSON file"""
    if PREFERENCES_FILE.exists():
        try:
            with open(PREFERENCES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}

def save_preferences(preferences: Dict) -> None:
    """Save preferences to JSON file"""
    try:
        with open(PREFERENCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(preferences, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving preferences: {e}")

# API Routes
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "golf_system": "available" if GOLF_SYSTEM_AVAILABLE else "unavailable"
    }

@app.get("/api/preferences")
async def get_all_preferences():
    """Get all user preferences"""
    try:
        preferences = load_preferences()
        return {
            "preferences": preferences,
            "count": len(preferences)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading preferences: {str(e)}")

@app.get("/api/preferences/{email}")
async def get_user_preferences(email: str):
    """Get preferences for a specific user"""
    try:
        preferences = load_preferences()
        if email in preferences:
            return preferences[email]
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading preferences: {str(e)}")

@app.post("/api/preferences")
async def save_user_preferences(user_prefs: UserPreferences):
    """Save user preferences"""
    try:
        preferences = load_preferences()
        preferences[user_prefs.email] = {
            "name": user_prefs.name,
            "email": user_prefs.email,
            "selected_courses": user_prefs.selected_courses,
            "time_slots": user_prefs.time_slots,
            "updated_at": datetime.now().isoformat()
        }
        save_preferences(preferences)
        
        return {
            "message": "Preferences saved successfully",
            "user": user_prefs.email
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving preferences: {str(e)}")

@app.delete("/api/preferences/{email}")
async def delete_user_preferences(email: str):
    """Delete user preferences"""
    try:
        preferences = load_preferences()
        if email in preferences:
            del preferences[email]
            save_preferences(preferences)
            return {"message": "Preferences deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting preferences: {str(e)}")

@app.get("/api/courses")
async def get_available_courses():
    """Get list of available golf courses"""
    if GOLF_SYSTEM_AVAILABLE:
        try:
            courses = golf_url_manager.get_all_courses()
            return {"courses": courses}
        except Exception as e:
            print(f"Error getting courses: {e}")
    
    # Fallback course list
    fallback_courses = [
        "Drammen Golf Club", "Holmestrand Golf Club", "Kongsberg Golf Club",
        "Oslo Golf Club", "Bogstad Golf Club", "Miklagard Golf Club"
    ]
    return {"courses": fallback_courses}

# Streamlit integration
streamlit_process = None

def start_streamlit():
    """Start Streamlit in a separate thread"""
    global streamlit_process
    try:
        # Start Streamlit on a different port
        streamlit_process = subprocess.Popen([
            'streamlit', 'run', 'app.py',
            '--server.port', '8501',
            '--server.address', '127.0.0.1',
            '--server.headless', 'true',
            '--browser.gatherUsageStats', 'false'
        ], cwd=Path(__file__).parent)
        print("Streamlit started on port 8501")
    except Exception as e:
        print(f"Error starting Streamlit: {e}")

# Proxy requests to Streamlit
@app.get("/")
async def streamlit_proxy():
    """Proxy the main page to Streamlit"""
    try:
        response = requests.get("http://127.0.0.1:8501/")
        return HTMLResponse(content=response.text, status_code=response.status_code)
    except requests.exceptions.RequestException:
        return HTMLResponse(content="""
        <html>
            <head><title>Golf Availability Monitor</title></head>
            <body>
                <h1>Golf Availability Monitor</h1>
                <p>Starting up... Please refresh in a moment.</p>
                <script>setTimeout(() => location.reload(), 3000);</script>
            </body>
        </html>
        """)

@app.get("/{path:path}")
async def streamlit_proxy_all(path: str):
    """Proxy all other requests to Streamlit"""
    try:
        response = requests.get(f"http://127.0.0.1:8501/{path}")
        return HTMLResponse(content=response.text, status_code=response.status_code)
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="Streamlit service unavailable")

if __name__ == "__main__":
    # Start Streamlit in background
    streamlit_thread = threading.Thread(target=start_streamlit)
    streamlit_thread.daemon = True
    streamlit_thread.start()
    
    # Give Streamlit time to start
    time.sleep(3)
    
    # Start FastAPI
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False
    )
