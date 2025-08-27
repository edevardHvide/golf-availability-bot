"""
Enhanced Unified Server for Golf Availability Monitor - Render Deployment

This serves both the FastAPI backend and Streamlit frontend on a single port,
perfect for Render deployment with robust data handling and error recovery.
"""

import sys
import os
import subprocess
import threading
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
import uvicorn
import requests

# Import the robust JSON manager
try:
    from robust_json_manager import (
        load_user_preferences, 
        save_user_preferences, 
        get_preferences_stats,
        preferences_manager
    )
    ROBUST_JSON_AVAILABLE = True
except ImportError:
    ROBUST_JSON_AVAILABLE = False
    print("Warning: Robust JSON manager not available. Using basic JSON handling.")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the golf monitoring functions
sys.path.append(str(Path(__file__).parent.parent))

try:
    from golf_utils import send_email_notification
    from golf_club_urls import golf_url_manager
    GOLF_SYSTEM_AVAILABLE = True
    logger.info("✅ Golf monitoring system available")
except ImportError:
    GOLF_SYSTEM_AVAILABLE = False
    logger.warning("⚠️ Golf monitoring system not available. Running in demo mode.")

app = FastAPI(
    title="Golf Availability Monitor - Unified Server",
    description="Combined FastAPI + Streamlit server with robust data handling for Render deployment",
    version="2.0.0"
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
    time_preferences: Dict[str, Dict] = {}  # New flexible weekday/weekend format
    preference_type: str = "Same for all days"
    min_players: int = 1
    days_ahead: int = 4
    timestamp: Optional[str] = None
    # Legacy fields for backward compatibility
    time_slots: List[str] = []  # Optional for backward compatibility
    notification_frequency: str = "immediate"

class SystemStatus(BaseModel):
    status: str
    timestamp: str
    golf_system_available: bool
    robust_json_available: bool
    user_count: int
    backup_count: int
    streamlit_status: str

# Data storage with fallback
PREFERENCES_FILE = Path(__file__).parent / "user_preferences.json"

def load_preferences() -> Dict:
    """Load preferences with robust handling if available, fallback otherwise."""
    if ROBUST_JSON_AVAILABLE:
        try:
            return load_user_preferences()
        except Exception as e:
            logger.error(f"Robust JSON load failed: {e}")
    
    # Fallback to basic JSON
    try:
        if PREFERENCES_FILE.exists():
            import json
            with open(PREFERENCES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both old and new format
            if isinstance(data, dict):
                if "users" in data:
                    return data["users"]
                else:
                    return data
        return {}
    except Exception as e:
        logger.error(f"Fallback JSON load failed: {e}")
        return {}

def save_preferences(preferences: Dict) -> bool:
    """Save preferences with robust handling if available, fallback otherwise."""
    if ROBUST_JSON_AVAILABLE:
        try:
            return save_user_preferences(preferences)
        except Exception as e:
            logger.error(f"Robust JSON save failed: {e}")
    
    # Fallback to basic JSON
    try:
        import json
        
        # Create new format with metadata
        data = {
            "_metadata": {
                "last_updated": datetime.now().isoformat(),
                "version": "2.0",
                "source": "unified_server_fallback"
            },
            "users": preferences
        }
        
        # Ensure parent directory exists
        PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first, then rename (atomic operation)
        temp_file = PREFERENCES_FILE.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        temp_file.replace(PREFERENCES_FILE)
        logger.info(f"Saved preferences for {len(preferences)} users (fallback)")
        return True
        
    except Exception as e:
        logger.error(f"Fallback JSON save failed: {e}")
        return False

def get_system_stats() -> Dict:
    """Get system statistics with fallback."""
    if ROBUST_JSON_AVAILABLE:
        try:
            return get_preferences_stats()
        except Exception as e:
            logger.error(f"Robust stats failed: {e}")
    
    # Fallback stats
    try:
        return {
            "file_exists": PREFERENCES_FILE.exists(),
            "file_size": PREFERENCES_FILE.stat().st_size if PREFERENCES_FILE.exists() else 0,
            "backup_count": 0,
            "last_modified": datetime.fromtimestamp(
                PREFERENCES_FILE.stat().st_mtime
            ).isoformat() if PREFERENCES_FILE.exists() else None
        }
    except Exception:
        return {"file_exists": False, "file_size": 0, "backup_count": 0, "last_modified": None}

# Streamlit process management
streamlit_process = None
streamlit_status = "not_started"

def start_streamlit():
    """Start Streamlit in a separate process."""
    global streamlit_process, streamlit_status
    
    try:
        streamlit_status = "starting"
        logger.info("🌐 Starting Streamlit frontend...")
        
        # Use enhanced_app.py if available, fallback to app.py
        app_file = "enhanced_app.py" if Path("enhanced_app.py").exists() else "app.py"
        
        streamlit_process = subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', app_file,
            '--server.port', '8501',
            '--server.address', '127.0.0.1',
            '--server.headless', 'true',
            '--server.enableCORS', 'false',
            '--server.enableXsrfProtection', 'false',
            '--browser.gatherUsageStats', 'false'
        ], 
        cwd=Path(__file__).parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
        )
        
        # Wait a moment to check if it started successfully
        time.sleep(3)
        
        if streamlit_process.poll() is None:
            streamlit_status = "running"
            logger.info("✅ Streamlit started successfully on port 8501")
        else:
            streamlit_status = "failed"
            logger.error("❌ Streamlit failed to start")
            
    except Exception as e:
        streamlit_status = "error"
        logger.error(f"Error starting Streamlit: {e}")

def check_streamlit_health():
    """Check if Streamlit is responding."""
    try:
        response = requests.get("http://127.0.0.1:8501/", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

# API Routes
@app.get("/")
async def root():
    """Root endpoint - proxy to Streamlit or show status."""
    if streamlit_status == "running" and check_streamlit_health():
        try:
            response = requests.get("http://127.0.0.1:8501/", timeout=5)
            return HTMLResponse(content=response.text, status_code=response.status_code)
        except Exception as e:
            logger.warning(f"Streamlit proxy failed: {e}")
    
    # Fallback status page
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>Golf Availability Monitor</title>
            <meta http-equiv="refresh" content="5">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; color: #4CAF50; margin-bottom: 30px; }}
                .status {{ padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .status-running {{ background: #d4edda; color: #155724; }}
                .status-starting {{ background: #fff3cd; color: #856404; }}
                .status-error {{ background: #f8d7da; color: #721c24; }}
                .info {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏌️ Golf Availability Monitor</h1>
                    <p>Unified Server v2.0</p>
                </div>
                
                <div class="status status-{streamlit_status.replace('_', '-')}">
                    <strong>Streamlit Status:</strong> {streamlit_status.replace('_', ' ').title()}
                </div>
                
                <div class="info">
                    <h3>🔧 System Information</h3>
                    <ul>
                        <li><strong>API Server:</strong> ✅ Running</li>
                        <li><strong>Golf System:</strong> {'✅ Available' if GOLF_SYSTEM_AVAILABLE else '🔶 Demo Mode'}</li>
                        <li><strong>Data Storage:</strong> {'✅ Robust' if ROBUST_JSON_AVAILABLE else '🔶 Basic'}</li>
                        <li><strong>Port:</strong> {os.environ.get('PORT', '10000')}</li>
                    </ul>
                </div>
                
                <div class="info">
                    <h3>📡 Available Endpoints</h3>
                    <ul>
                        <li><a href="/health">Health Check</a></li>
                        <li><a href="/api/status">System Status</a></li>
                        <li><a href="/api/preferences">User Preferences</a></li>
                        <li><a href="/api/courses">Golf Courses</a></li>
                    </ul>
                </div>
                
                <p style="text-align: center; color: #666; margin-top: 30px;">
                    This page will refresh automatically. The frontend will be available once Streamlit finishes starting.
                </p>
            </div>
        </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "streamlit_status": streamlit_status
    }

@app.get("/api/status", response_model=SystemStatus)
async def get_system_status():
    """Comprehensive system status endpoint."""
    try:
        stats = get_system_stats()
        user_prefs = load_preferences()
        
        return SystemStatus(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            golf_system_available=GOLF_SYSTEM_AVAILABLE,
            robust_json_available=ROBUST_JSON_AVAILABLE,
            user_count=len(user_prefs),
            backup_count=stats.get("backup_count", 0),
            streamlit_status=streamlit_status
        )
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")

@app.get("/api/preferences")
async def get_all_preferences():
    """Get all user preferences."""
    try:
        preferences = load_preferences()
        
        last_updated = "Never"
        if preferences:
            timestamps = [p.get('timestamp', '') for p in preferences.values() if isinstance(p, dict)]
            last_updated = max(t for t in timestamps if t) or "Never"
        
        return {
            "preferences": preferences,
            "user_count": len(preferences),
            "last_updated": last_updated,
            "robust_json": ROBUST_JSON_AVAILABLE
        }
    except Exception as e:
        logger.error(f"Error retrieving preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve preferences")

@app.get("/api/preferences/{email}")
async def get_user_preferences(email: str):
    """Get preferences for a specific user."""
    try:
        preferences = load_preferences()
        
        if email in preferences:
            return preferences[email]
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving preferences for {email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve preferences")

@app.post("/api/preferences")
async def save_user_preferences_endpoint(user_prefs: UserPreferences):
    """Save user preferences."""
    try:
        preferences = load_preferences()
        
        # Check if user is new or existing
        is_new_user = user_prefs.email not in preferences
        
        # Create preference dictionary
        prefs_dict = {
            "name": user_prefs.name,
            "email": user_prefs.email,
            "selected_courses": user_prefs.selected_courses,
            "time_slots": user_prefs.time_slots,
            "min_players": user_prefs.min_players,
            "days_ahead": user_prefs.days_ahead,
            "notification_frequency": user_prefs.notification_frequency,
            "timestamp": datetime.now().isoformat()
        }
        
        preferences[user_prefs.email] = prefs_dict
        success = save_preferences(preferences)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save preferences")
        
        action = "created" if is_new_user else "updated"
        
        return {
            "success": True,
            "message": f"Preferences {action} successfully for {user_prefs.name}",
            "user_count": len(preferences),
            "user": user_prefs.email
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving preferences: {str(e)}")

@app.delete("/api/preferences/{email}")
async def delete_user_preferences(email: str):
    """Delete user preferences."""
    try:
        preferences = load_preferences()
        
        if email not in preferences:
            raise HTTPException(status_code=404, detail="User not found")
        
        del preferences[email]
        success = save_preferences(preferences)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save changes")
        
        return {
            "success": True,
            "message": "Preferences deleted successfully",
            "remaining_users": len(preferences)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting preferences: {str(e)}")

@app.get("/api/courses")
async def get_available_courses():
    """Get list of available golf courses."""
    try:
        if GOLF_SYSTEM_AVAILABLE:
            try:
                courses = golf_url_manager.get_all_courses()
                return {"courses": courses, "source": "golf_system"}
            except Exception as e:
                logger.warning(f"Golf system error, using fallback: {e}")
        
        # Fallback course list
        fallback_courses = [
            {"id": "oslo_golfklubb", "name": "Oslo Golfklubb", "location": "Oslo"},
            {"id": "miklagard_gk", "name": "Miklagard Golf Club", "location": "Bærum"},
            {"id": "bogstad_golfklubb", "name": "Bogstad Golfklubb", "location": "Oslo"},
            {"id": "drammen_golfklubb", "name": "Drammen Golfklubb", "location": "Drammen"},
            {"id": "holmestrand_golfklubb", "name": "Holmestrand Golfklubb", "location": "Holmestrand"},
            {"id": "kongsberg_golfklubb", "name": "Kongsberg Golfklubb", "location": "Kongsberg"}
        ]
        
        return {"courses": fallback_courses, "source": "fallback"}
        
    except Exception as e:
        logger.error(f"Error getting courses: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve courses")

@app.post("/api/test-notification")
async def send_test_notification(request: dict):
    """Send a test notification."""
    try:
        email = request.get("email")
        name = request.get("name", "User")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        
        if GOLF_SYSTEM_AVAILABLE:
            try:
                send_email_notification(
                    subject="🏌️ Golf Monitor Test Notification",
                    message=f"Hello {name}! Your golf availability monitoring is working correctly.",
                    override_email=email
                )
                return {
                    "success": True,
                    "message": f"Test notification sent to {email}",
                    "type": "real_email"
                }
            except Exception as e:
                logger.warning(f"Real email failed: {e}")
        
        # Demo mode response
        return {
            "success": True,
            "message": f"Demo: Test notification would be sent to {email}",
            "type": "demo_mode"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test notification")

@app.post("/api/backup")
async def create_backup():
    """Create a manual backup if robust JSON is available."""
    if not ROBUST_JSON_AVAILABLE:
        return {
            "success": False,
            "message": "Backup functionality requires robust JSON manager",
            "available": False
        }
    
    try:
        success = preferences_manager.backup()
        
        if success:
            backups = preferences_manager.get_backups()
            return {
                "success": True,
                "message": "Backup created successfully",
                "backup_count": len(backups)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create backup")
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(status_code=500, detail="Failed to create backup")

# Proxy remaining requests to Streamlit
@app.get("/{path:path}")
async def streamlit_proxy(path: str):
    """Proxy all other requests to Streamlit."""
    if streamlit_status == "running" and check_streamlit_health():
        try:
            response = requests.get(f"http://127.0.0.1:8501/{path}", timeout=5)
            return HTMLResponse(content=response.text, status_code=response.status_code)
        except Exception as e:
            logger.warning(f"Streamlit proxy failed for {path}: {e}")
    
    return RedirectResponse(url="/")

if __name__ == "__main__":
    # Start Streamlit in background
    logger.info("🚀 Starting Golf Availability Monitor Unified Server v2.0")
    
    streamlit_thread = threading.Thread(target=start_streamlit)
    streamlit_thread.daemon = True
    streamlit_thread.start()
    
    # Give Streamlit time to start
    time.sleep(5)
    
    # Start FastAPI
    port = int(os.environ.get("PORT", 10000))
    
    logger.info(f"📡 Starting FastAPI server on port {port}")
    logger.info(f"🏌️ Golf System: {'Available' if GOLF_SYSTEM_AVAILABLE else 'Demo Mode'}")
    logger.info(f"💾 Data Storage: {'Robust' if ROBUST_JSON_AVAILABLE else 'Basic'}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False
    )
