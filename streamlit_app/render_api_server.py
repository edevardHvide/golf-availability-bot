"""
Dedicated API Server for Render Deployment with PostgreSQL

This is a streamlined FastAPI server designed specifically for Render deployment
as a separate service from the Streamlit frontend. Now uses PostgreSQL for data persistence.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import uvicorn

# Import database managers with fallback
try:
    from postgresql_manager import get_db_manager, initialize_database
    DATABASE_TYPE = "postgresql"
    print("🐘 Using PostgreSQL database")
except ImportError as e:
    print(f"⚠️ PostgreSQL not available: {e}")
    try:
        from robust_json_manager import (
            load_user_preferences, 
            save_user_preferences, 
            get_preferences_stats,
            preferences_manager
        )
        DATABASE_TYPE = "json"
        print("📄 Falling back to JSON storage")
    except ImportError:
        DATABASE_TYPE = "none"
        print("❌ No storage system available")
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

# FastAPI app configuration
app = FastAPI(
    title="Golf Availability Monitor API",
    description="Dedicated API service for golf monitoring with robust data handling",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration for Render deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://*.onrender.com",  # Allow all Render subdomains
        "http://localhost:8501",   # Local development
        "http://localhost:3000",   # Alternative local port
        "*"  # For development - restrict in production
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Pydantic models
class TimePreferences(BaseModel):
    time_slots: List[str] = []
    time_intervals: List[str] = []
    method: str = "Preset Ranges"

class UserPreferences(BaseModel):
    name: str
    email: EmailStr
    selected_courses: List[str]
    time_preferences: Dict[str, TimePreferences] = {}
    preference_type: str = "Same for all days"
    min_players: int = 1
    days_ahead: int = 4

class PreferencesResponse(BaseModel):
    success: bool
    message: str
    user_count: int

class SystemStatus(BaseModel):
    status: str
    timestamp: str
    golf_system_available: bool
    robust_json_available: bool
    user_count: int
    backup_count: int
    version: str
    deployment: str

class TestNotificationRequest(BaseModel):
    email: EmailStr
    name: str

# Data handling with database fallback
def load_preferences() -> Dict:
    """Load preferences using available storage system."""
    if DATABASE_TYPE == "postgresql":
        try:
            db_manager = get_db_manager()
            return db_manager.get_all_user_preferences()
        except Exception as e:
            logger.error(f"PostgreSQL load failed: {e}")
            return {}
    elif DATABASE_TYPE == "json":
        try:
            return load_user_preferences()
        except Exception as e:
            logger.error(f"JSON load failed: {e}")
            return {}
    else:
        logger.warning("No storage system available")
        return {}

def save_preferences(preferences: Dict) -> bool:
    """Save preferences using available storage system."""
    if DATABASE_TYPE == "postgresql":
        try:
            db_manager = get_db_manager()
            return db_manager.save_user_preferences(preferences)
        except Exception as e:
            logger.error(f"PostgreSQL save failed: {e}")
            return False
    elif DATABASE_TYPE == "json":
        try:
            return save_user_preferences(preferences)
        except Exception as e:
            logger.error(f"JSON save failed: {e}")
            return False
    else:
        logger.warning("No storage system available")
        return False

def get_user_preferences(email: str) -> Dict:
    """Get specific user preferences."""
    if DATABASE_TYPE == "postgresql":
        try:
            db_manager = get_db_manager()
            result = db_manager.load_user_preferences(email)
            return result if result else {}
        except Exception as e:
            logger.error(f"PostgreSQL load user failed: {e}")
            return {}
    elif DATABASE_TYPE == "json":
        try:
            all_prefs = load_user_preferences()
            return all_prefs.get(email, {})
        except Exception as e:
            logger.error(f"JSON load user failed: {e}")
            return {}
    else:
        return {}

def get_storage_stats() -> Dict:
    """Get storage system statistics."""
    if DATABASE_TYPE == "postgresql":
        try:
            db_manager = get_db_manager()
            health = db_manager.health_check()
            return {
                "type": "postgresql",
                "status": health.get("status", "unknown"),
                "user_count": health.get("user_count", 0),
                "active_today": health.get("active_today", 0),
                "connected": health.get("connected", False)
            }
        except Exception as e:
            return {"type": "postgresql", "status": "error", "error": str(e)}
    elif DATABASE_TYPE == "json":
        try:
            if 'get_preferences_stats' in globals():
                stats = get_preferences_stats()
                return {
                    "type": "json", 
                    "status": "healthy",
                    "user_count": stats.get("user_count", 0),
                    "backup_count": stats.get("backup_count", 0)
                }
            else:
                prefs = load_user_preferences()
                return {
                    "type": "json",
                    "status": "basic",
                    "user_count": len(prefs)
                }
        except Exception as e:
            return {"type": "json", "status": "error", "error": str(e)}
    else:
        return {"type": "none", "status": "unavailable"}

# API Routes
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Golf Availability Monitor API",
        "version": "2.1.0",
        "description": "Dedicated API service for Render deployment",
        "deployment": "render_two_service",
        "endpoints": {
            "health": "/health",
            "system_status": "/api/status", 
            "preferences": "/api/preferences",
            "courses": "/api/courses",
            "test_notification": "/api/test-notification",
            "documentation": "/docs"
        },
        "golf_system": "available" if GOLF_SYSTEM_AVAILABLE else "demo_mode",
        "database_type": DATABASE_TYPE
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Render monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.1.0",
        "service": "api"
    }

@app.get("/api/status", response_model=SystemStatus)
async def get_system_status():
    """Comprehensive system status endpoint."""
    try:
        user_prefs = load_preferences()
        backup_count = 0
        robust_json_available = DATABASE_TYPE == "json" and 'get_preferences_stats' in globals()
        
        if robust_json_available:
            try:
                stats = get_preferences_stats()
                backup_count = stats.get("backup_count", 0)
            except Exception:
                pass
        
        return SystemStatus(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            golf_system_available=GOLF_SYSTEM_AVAILABLE,
            robust_json_available=robust_json_available,
            user_count=len(user_prefs),
            backup_count=backup_count,
            version="2.1.0",
            deployment="render_api_service"
        )
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")

@app.get("/api/courses")
async def get_courses():
    """Get available golf courses."""
    try:
        if GOLF_SYSTEM_AVAILABLE:
            try:
                courses = golf_url_manager.get_all_courses()
                formatted_courses = []
                
                for key, club in golf_url_manager.clubs.items():
                    formatted_courses.append({
                        'key': key,
                        'name': club.display_name,
                        'location': f"{club.location[0]:.2f}, {club.location[1]:.2f}" if club.location else "Unknown",
                        'default_start_time': f"{club.default_start_time[:2]}:{club.default_start_time[2:4]}" if len(club.default_start_time) >= 4 else "07:00"
                    })
                
                return {
                    "courses": sorted(formatted_courses, key=lambda x: x['name']),
                    "source": "golf_system",
                    "count": len(formatted_courses)
                }
            except Exception as e:
                logger.warning(f"Golf system error, using fallback: {e}")
        
        # Fallback courses
        fallback_courses = [
            {'key': 'oslo_golfklubb', 'name': 'Oslo Golfklubb', 'location': '59.91, 10.75', 'default_start_time': '07:00'},
            {'key': 'miklagard_gk', 'name': 'Miklagard GK', 'location': '59.97, 11.04', 'default_start_time': '07:00'},
            {'key': 'baerum_gk', 'name': 'Bærum GK', 'location': '59.89, 10.52', 'default_start_time': '06:00'},
            {'key': 'bogstad_golfklubb', 'name': 'Bogstad Golfklubb', 'location': '59.95, 10.63', 'default_start_time': '07:00'},
            {'key': 'asker_golfklubb', 'name': 'Asker Golfklubb', 'location': '59.83, 10.43', 'default_start_time': '07:00'},
            {'key': 'drammen_golfklubb', 'name': 'Drammen Golfklubb', 'location': '59.74, 10.20', 'default_start_time': '07:00'},
            {'key': 'losby_golfklubb', 'name': 'Losby Golfklubb', 'location': '59.93, 11.13', 'default_start_time': '07:00'},
            {'key': 'kongsberg_golfklubb', 'name': 'Kongsberg Golfklubb', 'location': '59.67, 9.65', 'default_start_time': '06:00'},
        ]
        
        return {
            "courses": fallback_courses,
            "source": "fallback",
            "count": len(fallback_courses)
        }
        
    except Exception as e:
        logger.error(f"Error getting courses: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve courses")

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
            "database_type": DATABASE_TYPE,
            "service": "render_api"
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
            raise HTTPException(status_code=404, detail="User preferences not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving preferences for {email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve preferences")

@app.post("/api/preferences", response_model=PreferencesResponse)
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
            "time_preferences": {k: v.dict() for k, v in user_prefs.time_preferences.items()},
            "preference_type": user_prefs.preference_type,
            "min_players": user_prefs.min_players,
            "days_ahead": user_prefs.days_ahead,
            "timestamp": datetime.now().isoformat(),
            "source": "render_api"
        }
        
        preferences[user_prefs.email] = prefs_dict
        success = save_preferences(preferences)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save preferences")
        
        action = "created" if is_new_user else "updated"
        logger.info(f"User preferences {action} for {user_prefs.email}")
        
        return PreferencesResponse(
            success=True,
            message=f"Preferences {action} successfully for {user_prefs.name}",
            user_count=len(preferences)
        )
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
            raise HTTPException(status_code=404, detail="User preferences not found")
        
        del preferences[email]
        success = save_preferences(preferences)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save changes")
        
        logger.info(f"User preferences deleted for {email}")
        
        return {
            "success": True,
            "message": f"Preferences deleted for {email}",
            "remaining_users": len(preferences)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting preferences for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting preferences: {str(e)}")

@app.post("/api/test-notification")
async def send_test_notification(request: TestNotificationRequest):
    """Send a test notification."""
    try:
        if GOLF_SYSTEM_AVAILABLE:
            try:
                send_email_notification(
                    subject="🏌️ Golf Monitor Test Notification",
                    message=f"Hello {request.name}! Your golf availability monitoring is working correctly.",
                    override_email=request.email
                )
                logger.info(f"Test notification sent to {request.email}")
                return {
                    "success": True,
                    "message": f"Test notification sent to {request.email}",
                    "type": "real_email"
                }
            except Exception as e:
                logger.warning(f"Real email failed: {e}")
        
        # Demo mode response
        return {
            "success": True,
            "message": f"Demo: Test notification would be sent to {request.email}",
            "type": "demo_mode",
            "note": "Email functionality not available in demo mode"
        }
        
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test notification")

@app.post("/api/backup")
async def create_backup():
    """Create a manual backup if robust JSON is available."""
    robust_json_available = DATABASE_TYPE == "json" and 'preferences_manager' in globals()
    if not robust_json_available:
        return {
            "success": False,
            "message": "Backup functionality requires robust JSON manager",
            "available": False
        }
    
    try:
        success = preferences_manager.backup()
        
        if success:
            backups = preferences_manager.get_backups()
            logger.info("Manual backup created")
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

if __name__ == "__main__":
    # Get port from environment (Render provides this)
    port = int(os.environ.get("PORT", 8000))
    
    logger.info("🚀 Starting Golf Availability Monitor API Service")
    logger.info(f"📡 Port: {port}")
    logger.info(f"🏌️ Golf System: {'Available' if GOLF_SYSTEM_AVAILABLE else 'Demo Mode'}")
    logger.info(f"💾 JSON Storage: {'Robust' if ROBUST_JSON_AVAILABLE else 'Basic'}")
    logger.info(f"🌐 Deployment: Render API Service")
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        access_log=True
    )
