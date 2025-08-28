"""
Enhanced FastAPI Backend for Golf Availability Monitor

This provides robust API endpoints with proper error handling and data persistence.
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import uvicorn

# Import the robust JSON manager
from robust_json_manager import (
    load_user_preferences, 
    save_user_preferences, 
    get_preferences_stats,
    preferences_manager
)

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
    title="Golf Availability Monitor API",
    description="Enhanced API for managing golf tee time monitoring preferences with robust data handling",
    version="2.0.0"
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
class TimePreferences(BaseModel):
    time_slots: List[str] = []
    time_intervals: List[str] = []
    method: str = "Preset Ranges"

class UserPreferences(BaseModel):
    name: str
    email: EmailStr
    selected_courses: List[str]
    time_preferences: Dict[str, Dict] = {}  # More flexible to accept any dict structure
    preference_type: str = "Same for all days"
    min_players: int = 1
    days_ahead: int = 4
    timestamp: Optional[str] = None

class PreferencesResponse(BaseModel):
    success: bool
    message: str
    user_count: Optional[int] = None

class TestNotificationRequest(BaseModel):
    email: EmailStr
    name: str

class SystemStatus(BaseModel):
    status: str
    timestamp: str
    golf_system_available: bool
    preferences_file_stats: Dict
    user_count: int
    backup_count: int

# Enhanced data operations using robust JSON manager
def load_preferences() -> Dict:
    """Load user preferences using robust JSON manager."""
    try:
        return load_user_preferences()
    except Exception as e:
        logger.error(f"Error loading preferences: {e}")
        return {}

def save_preferences(preferences: Dict) -> bool:
    """Save user preferences using robust JSON manager."""
    try:
        success = save_user_preferences(preferences)
        if success:
            logger.info(f"Successfully saved preferences for {len(preferences)} users")
        else:
            logger.error("Failed to save preferences with robust manager")
        return success
    except Exception as e:
        logger.error(f"Error saving preferences: {e}")
        return False

# API Routes
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Golf Availability Monitor API v2.0",
        "description": "Enhanced API with robust data handling",
        "version": "2.0.0",
        "golf_system": "available" if GOLF_SYSTEM_AVAILABLE else "demo_mode",
        "endpoints": {
            "health": "/health",
            "system_status": "/api/status",
            "preferences": "/api/preferences",
            "courses": "/api/courses",
            "test_notification": "/api/test-notification",
            "backup": "/api/backup",
            "cached_availability": "/api/cached-availability"
        }
    }

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }

@app.get("/api/status", response_model=SystemStatus)
async def get_system_status():
    """Comprehensive system status endpoint."""
    try:
        stats = get_preferences_stats()
        user_prefs = load_preferences()
        
        return SystemStatus(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            golf_system_available=GOLF_SYSTEM_AVAILABLE,
            preferences_file_stats=stats,
            user_count=len(user_prefs),
            backup_count=stats.get("backup_count", 0)
        )
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")

@app.get("/api/courses")
async def get_courses():
    """Get available golf courses."""
    try:
        if GOLF_SYSTEM_AVAILABLE and golf_url_manager:
            try:
                # Get all clubs from golf_url_manager
                all_clubs = golf_url_manager.get_all_clubs()
                
                # Convert to the expected format
                courses = []
                for club in all_clubs:
                    courses.append({
                        'key': club.name,  # The key used in the system
                        'name': club.display_name,
                        'location': f"{club.location[0]:.2f}, {club.location[1]:.2f}" if club.location else "Unknown",
                        'default_start_time': f"{club.default_start_time[:2]}:{club.default_start_time[2:4]}" if len(club.default_start_time) >= 4 else "07:00"
                    })
                
                # Sort by name for better UX
                courses = sorted(courses, key=lambda x: x['name'])
                
                return {
                    "courses": courses,
                    "source": "golf_system",
                    "count": len(courses)
                }
            except Exception as e:
                logger.warning(f"Golf system error, using fallback: {e}")
        
        # Fallback courses for demo mode - using consistent format
        fallback_courses = [
            {"key": "oslo_golfklubb", "name": "Oslo Golfklubb", "location": "59.91, 10.75", "default_start_time": "07:30"},
            {"key": "miklagard_gk", "name": "Miklagard GK", "location": "59.97, 11.04", "default_start_time": "07:00"},
            {"key": "baerum_gk", "name": "Bærum GK", "location": "59.89, 10.52", "default_start_time": "06:00"},
            {"key": "asker_golfklubb", "name": "Asker Golfklubb", "location": "59.84, 10.44", "default_start_time": "07:00"},
            {"key": "kongsberg_golfklubb", "name": "Kongsberg Golfklubb", "location": "59.67, 9.65", "default_start_time": "06:00"},
            {"key": "losby_golfklubb", "name": "Losby Golfklubb", "location": "59.92, 10.96", "default_start_time": "07:00"}
        ]
        
        return {
            "courses": fallback_courses,
            "source": "fallback",
            "count": len(fallback_courses)
        }
        
    except Exception as e:
        logger.error(f"Error getting courses: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve courses")

@app.post("/api/preferences", response_model=PreferencesResponse)
async def save_user_preferences_endpoint(preferences: UserPreferences):
    """Save user preferences for golf monitoring."""
    try:
        # Load existing preferences
        all_preferences = load_preferences()
        
        # Add timestamp if not provided
        prefs_dict = preferences.dict()
        if not prefs_dict.get('timestamp'):
            prefs_dict['timestamp'] = datetime.now().isoformat()
        
        # Check if user is new or existing
        is_new_user = preferences.email not in all_preferences
        
        # Save preferences keyed by email
        all_preferences[preferences.email] = prefs_dict
        
        # Save to file using robust manager
        success = save_preferences(all_preferences)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save preferences to storage")
        
        action = "created" if is_new_user else "updated"
        
        return PreferencesResponse(
            success=True,
            message=f"Preferences {action} successfully for {preferences.name}",
            user_count=len(all_preferences)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save preferences: {str(e)}")

@app.get("/api/preferences/{email}")
async def get_user_preferences(email: str):
    """Get preferences for a specific user."""
    try:
        all_preferences = load_preferences()
        
        if email not in all_preferences:
            raise HTTPException(status_code=404, detail="User preferences not found")
        
        return all_preferences[email]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving preferences for {email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve preferences")

@app.get("/api/preferences")
async def get_all_preferences():
    """Get all user preferences (admin endpoint)."""
    try:
        all_preferences = load_preferences()
        
        last_updated = "Never"
        if all_preferences:
            timestamps = [p.get('timestamp', '') for p in all_preferences.values() if isinstance(p, dict)]
            last_updated = max(t for t in timestamps if t) or "Never"
        
        return {
            "preferences": all_preferences,
            "user_count": len(all_preferences),
            "last_updated": last_updated,
            "system_status": "healthy"
        }
    
    except Exception as e:
        logger.error(f"Error retrieving all preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve preferences")

@app.post("/api/test-notification")
async def send_test_notification(request: TestNotificationRequest):
    """Send a test notification to the user."""
    try:
        if GOLF_SYSTEM_AVAILABLE:
            try:
                # Try to send real email
                send_email_notification(
                    subject="🏌️ Golf Monitor Test Notification",
                    message=f"Hello {request.name}! Your golf availability monitoring is working correctly.",
                    override_email=request.email
                )
                return {
                    "success": True,
                    "message": f"Test notification sent to {request.email}",
                    "type": "real_email"
                }
            except Exception as e:
                logger.warning(f"Real email failed, using demo mode: {e}")
        
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

@app.delete("/api/preferences/{email}")
async def delete_user_preferences(email: str):
    """Delete preferences for a specific user."""
    try:
        all_preferences = load_preferences()
        
        if email not in all_preferences:
            raise HTTPException(status_code=404, detail="User preferences not found")
        
        del all_preferences[email]
        success = save_preferences(all_preferences)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save changes")
        
        return {
            "success": True, 
            "message": f"Preferences deleted for {email}",
            "remaining_users": len(all_preferences)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting preferences for {email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete preferences")

@app.post("/api/backup")
async def create_backup():
    """Create a manual backup of the preferences file."""
    try:
        success = preferences_manager.backup()
        
        if success:
            backups = preferences_manager.get_backups()
            return {
                "success": True,
                "message": "Backup created successfully",
                "backup_count": len(backups),
                "latest_backup": str(backups[0]) if backups else None
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create backup")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(status_code=500, detail="Failed to create backup")

@app.get("/api/backups")
async def list_backups():
    """List available backup files."""
    try:
        backups = preferences_manager.get_backups()
        backup_info = []
        
        for backup in backups:
            stat = backup.stat()
            backup_info.append({
                "filename": backup.name,
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size": stat.st_size
            })
        
        return {
            "backups": backup_info,
            "count": len(backup_info)
        }
    
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        raise HTTPException(status_code=500, detail="Failed to list backups")

@app.get("/api/cached-availability")
async def get_cached_availability(user_email: str = None, hours_limit: int = 24):
    """Get cached availability results from database."""
    try:
        # Try to use PostgreSQL manager if available
        try:
            from postgresql_manager import get_db_manager
            db_manager = get_db_manager()
            
            # Get latest cached availability
            cached_data = db_manager.get_latest_cached_availability(user_email, hours_limit)
            
            if cached_data:
                # Extract availability data from the cached result
                availability_data = cached_data.get('availability_data', {})
                check_timestamp = cached_data.get('check_timestamp')
                
                return {
                    "success": True,
                    "cached": True,
                    "check_timestamp": check_timestamp,
                    "availability": availability_data,
                    "total_courses": cached_data.get('total_courses', 0),
                    "total_availability_slots": cached_data.get('total_availability_slots', 0),
                    "message": f"✅ Retrieved {len(availability_data)} course results from database"
                }
            else:
                return {
                    "success": True,
                    "cached": False,
                    "message": "💾 No recent cached results available. Data will be available after your local computer runs a check.",
                    "note": "The cached availability feature requires your local golf monitor to be running and checking for availability.",
                    "availability": {},
                    "instructions": [
                        "1. Run your local golf monitor with: python golf_availability_monitor.py",
                        "2. Or use the scheduled monitoring to get automatic updates",
                        "3. Results will be cached and available here after each check"
                    ]
                }
                
        except ImportError:
            # Fallback to JSON-based storage message
            return {
                "success": True,
                "cached": False,
                "message": "💾 No recent cached results available. Data will be available after your local computer runs a check.",
                "note": "The cached availability feature requires your local golf monitor to be running and checking for availability. This API service stores user preferences but doesn't perform golf course checks itself.",
                "availability": {},
                "instructions": [
                    "1. Run your local golf monitor with: python golf_availability_monitor.py",
                    "2. Or use the scheduled monitoring to get automatic updates",
                    "3. Results will be cached and available here after each check"
                ]
            }
            
    except Exception as e:
        logger.error(f"Error getting cached availability: {e}")
        return {
            "success": False,
            "cached": False,
            "error": str(e),
            "message": "Error retrieving cached availability data"
        }

@app.get("/api/all-times")
async def get_all_times():
    """Get all available times from the latest database entry."""
    try:
        # Try to use PostgreSQL manager if available
        try:
            from postgresql_manager import get_db_manager
            db_manager = get_db_manager()
            
            # Get latest cached availability (no time limit to get the most recent)
            cached_data = db_manager.get_latest_cached_availability(hours_limit=168)  # 7 days
            
            if cached_data:
                # Extract availability data from the cached result
                availability_data = cached_data.get('availability_data', {})
                check_timestamp = cached_data.get('check_timestamp')
                
                # Debug: Check the type and content of availability_data
                logger.info(f"Debug: availability_data type: {type(availability_data)}")
                logger.info(f"Debug: availability_data keys: {list(availability_data.keys())[:5] if availability_data else 'None'}")
                
                # Ensure availability_data is a dictionary
                if isinstance(availability_data, str):
                    try:
                        import json
                        availability_data = json.loads(availability_data)
                        logger.info("Debug: Successfully parsed JSON string to dict")
                    except json.JSONDecodeError as e:
                        logger.error(f"Debug: Failed to parse JSON string: {e}")
                        availability_data = {}
                
                # Count total slots across all courses and dates
                total_slots = 0
                courses_with_data = 0
                dates_found = set()
                
                for state_key, times in availability_data.items():
                    if '_' in state_key:
                        course_name = state_key.split('_')[0]
                        date_part = state_key.split('_')[-1]
                        if len(date_part) == 10:  # YYYY-MM-DD format
                            dates_found.add(date_part)
                            if times:
                                courses_with_data += 1
                                total_slots += len(times)
                
                return {
                    "success": True,
                    "cached": True,
                    "check_timestamp": check_timestamp,
                    "availability": availability_data,
                    "total_courses": cached_data.get('total_courses', 0),
                    "total_availability_slots": total_slots,
                    "courses_with_data": courses_with_data,
                    "dates_found": sorted(list(dates_found)),
                    "message": f"✅ Retrieved {len(availability_data)} course results with {total_slots} total time slots"
                }
            else:
                return {
                    "success": True,
                    "cached": False,
                    "message": "💾 No cached results available. Run the golf monitor to collect data.",
                    "availability": {},
                    "total_courses": 0,
                    "total_availability_slots": 0,
                    "courses_with_data": 0,
                    "dates_found": []
                }
                
        except ImportError:
            return {
                "success": False,
                "cached": False,
                "message": "PostgreSQL manager not available. Database connection required.",
                "availability": {},
                "total_courses": 0,
                "total_availability_slots": 0,
                "courses_with_data": 0,
                "dates_found": []
            }
            
    except Exception as e:
        logger.error(f"Error getting all times: {e}")
        return {
            "success": False,
            "cached": False,
            "error": str(e),
            "message": "Error retrieving all times data"
        }

if __name__ == "__main__":
    # Development server
    port = int(os.environ.get("PORT", 8000))
    
    logger.info(f"🚀 Starting Golf Availability Monitor API v2.0 on port {port}")
    logger.info(f"📡 Golf System: {'Available' if GOLF_SYSTEM_AVAILABLE else 'Demo Mode'}")
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
