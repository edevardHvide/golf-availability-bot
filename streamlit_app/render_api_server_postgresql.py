"""
PostgreSQL-Enhanced API Server for Render Deployment

This FastAPI server uses PostgreSQL for data persistence and falls back to JSON if needed.
Optimized for Render's two-service architecture.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import database managers with fallback
try:
    from postgresql_manager import get_db_manager, initialize_database
    DATABASE_TYPE = "postgresql"
    logger.info("🐘 Using PostgreSQL database")
except ImportError as e:
    logger.warning(f"PostgreSQL not available: {e}")
    try:
        from robust_json_manager import (
            load_user_preferences, 
            save_user_preferences, 
            get_preferences_stats,
            preferences_manager
        )
        DATABASE_TYPE = "json"
        logger.info("📄 Using JSON storage")
    except ImportError:
        DATABASE_TYPE = "none"
        logger.error("❌ No storage system available")

# Environment configuration
PORT = int(os.environ.get("PORT", 8000))
DATA_STORAGE_MODE = os.environ.get("DATA_STORAGE_MODE", "render")
API_MODE = os.environ.get("API_MODE", "development")

# Pydantic models
class UserPreferences(BaseModel):
    name: str
    email: EmailStr
    selected_courses: List[str]
    time_preferences: Dict[str, Dict] = {}  # New flexible weekday/weekend format
    preference_type: str = "Same for all days"
    min_players: int = 1
    days_ahead: int = 7
    timestamp: Optional[str] = None
    # Legacy fields for backward compatibility
    time_slots: List[str] = []  # Optional for backward compatibility
    notification_frequency: str = "immediate"

class SystemStatus(BaseModel):
    status: str
    golf_system_available: bool
    user_count: int
    storage_type: str
    version: str
    deployment: str

class TestNotificationRequest(BaseModel):
    email: EmailStr
    name: str

# Database functions
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

# FastAPI app initialization
app = FastAPI(
    title="Golf Availability Monitor API",
    description="API service for golf tee time monitoring with PostgreSQL backend",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for cross-service communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    if DATABASE_TYPE == "postgresql":
        try:
            success = initialize_database()
            if success:
                logger.info("🎉 PostgreSQL database initialized successfully")
            else:
                logger.error("💥 PostgreSQL initialization failed")
        except Exception as e:
            logger.error(f"💥 Database startup error: {e}")

# API Routes
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    storage_stats = get_storage_stats()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "golf-availability-api",
        "version": "3.0.0",
        "storage": storage_stats
    }

@app.get("/api/status")
async def get_status():
    """Get system status with database information."""
    storage_stats = get_storage_stats()
    
    return SystemStatus(
        status="healthy",
        golf_system_available=True,
        user_count=storage_stats.get("user_count", 0),
        storage_type=storage_stats.get("type", "unknown"),
        version="3.0.0",
        deployment="render-postgresql"
    )

@app.get("/api/courses")
async def get_courses():
    """Get available golf courses."""
    courses = [
        {
            "key": "oslo_golfklubb",
            "name": "Oslo Golfklubb",
            "location": "59.91, 10.75",
            "default_start_time": "07:00"
        },
        {
            "key": "miklagard_gk", 
            "name": "Miklagard GK",
            "location": "59.97, 11.04",
            "default_start_time": "07:00"
        },
        {
            "key": "baerum_gk",
            "name": "Bærum GK", 
            "location": "59.89, 10.52",
            "default_start_time": "06:00"
        },
        {
            "key": "bogstad_golfklubb",
            "name": "Bogstad Golfklubb",
            "location": "59.95, 10.63", 
            "default_start_time": "07:00"
        },
        {
            "key": "asker_golfklubb",
            "name": "Asker Golfklubb",
            "location": "59.83, 10.43",
            "default_start_time": "07:00"
        },
        {
            "key": "drammen_golfklubb",
            "name": "Drammen Golfklubb", 
            "location": "59.74, 10.20",
            "default_start_time": "07:00"
        }
    ]
    
    return {
        "courses": courses,
        "count": len(courses),
        "source": "api_server"
    }

@app.get("/api/preferences")
async def get_all_preferences():
    """Get all user preferences."""
    try:
        preferences = load_preferences()
        storage_stats = get_storage_stats()
        
        return {
            "preferences": preferences,
            "user_count": len(preferences),
            "storage": storage_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to load preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load preferences: {str(e)}")

@app.get("/api/preferences/{email}")
async def get_user_preferences_endpoint(email: str):
    """Get preferences for specific user."""
    try:
        preferences = get_user_preferences(email)
        
        if not preferences:
            raise HTTPException(status_code=404, detail="User preferences not found")
        
        return preferences
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load preferences for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load preferences: {str(e)}")

@app.post("/api/preferences")
async def save_user_preferences_endpoint(preferences: UserPreferences):
    """Save user preferences."""
    try:
        # Convert Pydantic model to dict
        prefs_dict = preferences.dict()
        
        # Save preferences
        success = save_preferences(prefs_dict)
        
        if success:
            logger.info(f"✅ Saved preferences for {preferences.email}")
            
            # Log to system status if using PostgreSQL
            if DATABASE_TYPE == "postgresql":
                try:
                    db_manager = get_db_manager()
                    db_manager.log_system_status("user_preference_saved", {
                        "email": preferences.email,
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Failed to log system status: {e}")
            
            return {
                "message": f"Preferences saved successfully for {preferences.name}",
                "email": preferences.email,
                "storage_type": DATABASE_TYPE,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save preferences")
            
    except Exception as e:
        logger.error(f"Error saving preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving preferences: {str(e)}")

@app.delete("/api/preferences/{email}")
async def delete_user_preferences_endpoint(email: str):
    """Delete user preferences."""
    try:
        if DATABASE_TYPE == "postgresql":
            db_manager = get_db_manager()
            success = db_manager.delete_user_preferences(email)
        elif DATABASE_TYPE == "json":
            # Load all preferences, remove user, save back
            all_prefs = load_preferences()
            if email in all_prefs:
                del all_prefs[email]
                success = save_preferences(all_prefs)
            else:
                success = False
        else:
            success = False
        
        if success:
            return {"message": f"Preferences deleted for {email}"}
        else:
            raise HTTPException(status_code=404, detail="User preferences not found")
            
    except Exception as e:
        logger.error(f"Error deleting preferences for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting preferences: {str(e)}")

@app.post("/api/test-notification")
async def send_test_notification(request: TestNotificationRequest):
    """Send test notification."""
    try:
        logger.info(f"📧 Test notification requested for {request.email}")
        
        # For now, this is a demo mode response
        return {
            "message": f"Test notification sent to {request.name} at {request.email}",
            "type": "demo_mode",
            "timestamp": datetime.now().isoformat(),
            "storage_type": DATABASE_TYPE
        }
        
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending notification: {str(e)}")

@app.get("/api/cached-availability")
async def get_cached_availability(user_email: str = None, hours_limit: int = 24):
    """Get cached availability results for offline access."""
    try:
        if DATABASE_TYPE == "postgresql":
            db_manager = get_db_manager()
            cached_result = db_manager.get_latest_cached_availability(user_email, hours_limit)
            
            if cached_result:
                return {
                    "success": True,
                    "cached": True,
                    "check_timestamp": cached_result["check_timestamp"].isoformat(),
                    "check_type": cached_result["check_type"],
                    "availability": cached_result["availability_data"],
                    "courses_checked": cached_result["courses_checked"],
                    "total_courses": cached_result["total_courses"],
                    "total_availability_slots": cached_result["total_availability_slots"],
                    "new_availability": cached_result["metadata"].get("new_availability", []),
                    "date_range": {
                        "start": cached_result["date_range_start"].isoformat(),
                        "end": cached_result["date_range_end"].isoformat()
                    },
                    "cache_age_hours": hours_limit,
                    "message": f"Showing cached results from {cached_result['check_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"
                }
            else:
                return {
                    "success": False,
                    "cached": False,
                    "message": f"No cached results available within the last {hours_limit} hours"
                }
        else:
            return {
                "success": False,
                "cached": False,
                "message": "Cached availability requires PostgreSQL database"
            }
    except Exception as e:
        logger.error(f"Error getting cached availability: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/cached-availability/history")
async def get_cached_availability_history(user_email: str = None, limit: int = 10):
    """Get cached availability history."""
    try:
        if DATABASE_TYPE == "postgresql":
            db_manager = get_db_manager()
            history = db_manager.get_cached_availability_history(user_email, limit)
            
            formatted_history = []
            for result in history:
                formatted_history.append({
                    "id": result["id"],
                    "check_timestamp": result["check_timestamp"].isoformat(),
                    "check_type": result["check_type"],
                    "user_email": result["user_email"],
                    "total_courses": result["total_courses"],
                    "total_availability_slots": result["total_availability_slots"],
                    "new_availability_count": result["new_availability_count"],
                    "success": result["success"],
                    "check_duration_seconds": float(result["check_duration_seconds"]) if result["check_duration_seconds"] else None,
                    "date_range": {
                        "start": result["date_range_start"].isoformat(),
                        "end": result["date_range_end"].isoformat()
                    }
                })
            
            return {
                "success": True,
                "history": formatted_history,
                "count": len(formatted_history)
            }
        else:
            return {
                "success": False,
                "message": "Cached availability history requires PostgreSQL database"
            }
    except Exception as e:
        logger.error(f"Error getting cached availability history: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/all-times")
async def get_all_times():
    """Get all available times from the latest database entry."""
    try:
        if DATABASE_TYPE == "postgresql":
            try:
                db_manager = get_db_manager()
                
                # Get latest cached availability (no time limit to get the most recent)
                cached_data = db_manager.get_latest_cached_availability(hours_limit=168)  # 7 days
                
                if cached_data:
                    # Extract availability data from the cached result
                    availability_data = cached_data.get('availability_data', {})
                    check_timestamp = cached_data.get('check_timestamp')
                    
                    # Ensure availability_data is a dictionary
                    if isinstance(availability_data, str):
                        try:
                            import json
                            availability_data = json.loads(availability_data)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON string: {e}")
                            availability_data = {}
                    
                    # Count total slots across all courses and dates
                    total_slots = 0
                    courses_with_data = 0
                    dates_found = set()
                    
                    for state_key, times in availability_data.items():
                        if '_' in state_key:
                            course_name = state_key.split('_')[0]
                            date_part = state_key.split('_')[-1]  # Fixed: use [-1] for date part
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
                    
            except Exception as e:
                logger.error(f"PostgreSQL error in get_all_times: {e}")
                return {
                    "success": False,
                    "cached": False,
                    "error": str(e),
                    "message": "Error retrieving data from PostgreSQL"
                }
        else:
            return {
                "success": False,
                "cached": False,
                "message": "PostgreSQL database required for this endpoint",
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

@app.get("/api/database/health")
async def database_health():
    """Database-specific health check."""
    if DATABASE_TYPE == "postgresql":
        try:
            db_manager = get_db_manager()
            health = db_manager.health_check()
            return health
        except Exception as e:
            return {
                "status": "error",
                "database": "postgresql",
                "connected": False,
                "error": str(e)
            }
    else:
        return {
            "status": "info",
            "database": DATABASE_TYPE,
            "message": "Using non-PostgreSQL storage"
        }

@app.post("/api/database/cleanup")
async def cleanup_old_data():
    """Clean up old database records."""
    if DATABASE_TYPE == "postgresql":
        try:
            db_manager = get_db_manager()
            success = db_manager.cleanup_old_data(days=30)
            if success:
                return {"message": "Database cleanup completed successfully"}
            else:
                raise HTTPException(status_code=500, detail="Cleanup failed")
        except Exception as e:
            logger.error(f"Database cleanup error: {e}")
            raise HTTPException(status_code=500, detail=f"Cleanup error: {str(e)}")
    else:
        return {"message": "Cleanup not available for current storage type"}

# Main entry point
def main():
    """Run the API server."""
    logger.info("🚀 Starting Golf Availability API Server")
    logger.info(f"🏗️ Environment: {API_MODE}")
    logger.info(f"🔌 Port: {PORT}")
    logger.info(f"💾 Storage: {DATABASE_TYPE}")
    logger.info(f"📊 Data Mode: {DATA_STORAGE_MODE}")
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
