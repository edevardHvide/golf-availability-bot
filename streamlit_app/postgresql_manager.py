#!/usr/bin/env python3
"""
PostgreSQL Database Manager for Golf Availability Monitor

This module handles all database operations using PostgreSQL on Render.
Replaces the JSON file storage with a proper database.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import Json, RealDictCursor
from psycopg2.pool import SimpleConnectionPool
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostgreSQLManager:
    """Manages PostgreSQL database operations for golf availability data."""
    
    def __init__(self):
        """Initialize PostgreSQL connection."""
        self.database_url = self._get_database_url()
        self.engine = None
        self.Session = None
        self.connection_pool = None
        self._initialize_database()
    
    def _get_database_url(self) -> str:
        """Get database URL from environment variables."""
        # Render provides DATABASE_URL automatically
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            logger.info("Using DATABASE_URL from environment")
            return database_url
        
        # Fallback: construct from individual components
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_port = os.environ.get('DB_PORT', '5432')
        db_name = os.environ.get('DB_NAME', 'golfdb_li04')
        db_user = os.environ.get('DB_USER', 'golfdb_li04_user')
        db_password = os.environ.get('DB_PASSWORD', '')
        
        if not db_password:
            logger.warning("No database password found in environment variables")
        
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        logger.info(f"Constructed database URL: postgresql://{db_user}:***@{db_host}:{db_port}/{db_name}")
        
        return database_url
    
    def _initialize_database(self):
        """Initialize database connection and create tables."""
        try:
            # Create SQLAlchemy engine
            self.engine = create_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=300
            )
            
            # Create session factory
            self.Session = sessionmaker(bind=self.engine)
            
            # Create connection pool for direct psycopg2 operations
            self.connection_pool = SimpleConnectionPool(
                1, 5, self.database_url
            )
            
            # Create tables
            self._create_tables()
            
            logger.info("✅ PostgreSQL database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            raise
    
    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        create_tables_sql = """
        -- User preferences table
        CREATE TABLE IF NOT EXISTS user_preferences (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            preferences JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create index on email for faster lookups
        CREATE INDEX IF NOT EXISTS idx_user_preferences_email ON user_preferences(email);
        
        -- Create index on JSONB preferences for faster JSON queries
        CREATE INDEX IF NOT EXISTS idx_user_preferences_preferences ON user_preferences USING GIN (preferences);
        
        -- Monitoring sessions table (for tracking active monitoring)
        CREATE TABLE IF NOT EXISTS monitoring_sessions (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) REFERENCES user_preferences(email) ON DELETE CASCADE,
            session_data JSONB NOT NULL,
            status VARCHAR(50) DEFAULT 'active',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_check TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- System status table (for application health tracking)
        CREATE TABLE IF NOT EXISTS system_status (
            id SERIAL PRIMARY KEY,
            status_type VARCHAR(100) NOT NULL,
            status_data JSONB NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Cached availability results table
        CREATE TABLE IF NOT EXISTS cached_availability (
            id SERIAL PRIMARY KEY,
            check_type VARCHAR(50) NOT NULL, -- 'scheduled', 'immediate', 'manual'
            check_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            user_email VARCHAR(255) REFERENCES user_preferences(email) ON DELETE CASCADE,
            availability_data JSONB NOT NULL,
            courses_checked TEXT[] NOT NULL,
            date_range_start DATE NOT NULL,
            date_range_end DATE NOT NULL,
            total_courses INTEGER DEFAULT 0,
            total_availability_slots INTEGER DEFAULT 0,
            new_availability_count INTEGER DEFAULT 0,
            check_duration_seconds NUMERIC(8,2),
            success BOOLEAN DEFAULT TRUE,
            error_message TEXT,
            metadata JSONB DEFAULT '{}'::jsonb
        );
        
        -- Create indexes for cached availability
        CREATE INDEX IF NOT EXISTS idx_cached_availability_timestamp ON cached_availability(check_timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_cached_availability_user_email ON cached_availability(user_email);
        CREATE INDEX IF NOT EXISTS idx_cached_availability_check_type ON cached_availability(check_type);
        CREATE INDEX IF NOT EXISTS idx_cached_availability_date_range ON cached_availability(date_range_start, date_range_end);
        
        -- Create function to update updated_at timestamp
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        -- Create trigger for user_preferences
        DROP TRIGGER IF EXISTS update_user_preferences_updated_at ON user_preferences;
        CREATE TRIGGER update_user_preferences_updated_at
            BEFORE UPDATE ON user_preferences
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text(create_tables_sql))
                conn.commit()
            logger.info("✅ Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool."""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def health_check(self) -> Dict[str, Any]:
        """Check database health and return status."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    
                    # Get database stats
                    cur.execute("""
                        SELECT 
                            COUNT(*) as user_count,
                            COUNT(CASE WHEN updated_at > NOW() - INTERVAL '1 day' THEN 1 END) as active_today
                        FROM user_preferences
                    """)
                    stats = cur.fetchone()
                    
                    return {
                        "status": "healthy",
                        "database": "postgresql",
                        "connected": True,
                        "user_count": stats[0] if stats else 0,
                        "active_today": stats[1] if stats else 0,
                        "timestamp": datetime.now().isoformat()
                    }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "database": "postgresql", 
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def save_user_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Save user preferences to database."""
        try:
            email = preferences.get('email')
            name = preferences.get('name')
            
            if not email or not name:
                logger.error("Email and name are required")
                return False
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Use UPSERT (INSERT ... ON CONFLICT)
                    cur.execute("""
                        INSERT INTO user_preferences (email, name, preferences)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (email) 
                        DO UPDATE SET 
                            name = EXCLUDED.name,
                            preferences = EXCLUDED.preferences,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id, created_at, updated_at
                    """, (email, name, Json(preferences)))
                    
                    result = cur.fetchone()
                    conn.commit()
                    
                    logger.info(f"✅ Saved preferences for {email} (ID: {result['id']})")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Failed to save preferences: {e}")
            return False
    
    def load_user_preferences(self, email: str) -> Optional[Dict[str, Any]]:
        """Load user preferences from database."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT preferences, name, created_at, updated_at
                        FROM user_preferences 
                        WHERE email = %s
                    """, (email,))
                    
                    result = cur.fetchone()
                    
                    if result:
                        preferences = dict(result['preferences'])
                        preferences['_metadata'] = {
                            'created_at': result['created_at'].isoformat(),
                            'updated_at': result['updated_at'].isoformat()
                        }
                        logger.info(f"✅ Loaded preferences for {email}")
                        return preferences
                    else:
                        logger.info(f"ℹ️ No preferences found for {email}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Failed to load preferences for {email}: {e}")
            return None
    
    def get_all_user_preferences(self) -> Dict[str, Dict[str, Any]]:
        """Get all user preferences."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT email, name, preferences, created_at, updated_at
                        FROM user_preferences
                        ORDER BY updated_at DESC
                    """)
                    
                    results = cur.fetchall()
                    
                    preferences_dict = {}
                    for row in results:
                        email = row['email']
                        prefs = dict(row['preferences'])
                        prefs['_metadata'] = {
                            'created_at': row['created_at'].isoformat(),
                            'updated_at': row['updated_at'].isoformat()
                        }
                        preferences_dict[email] = prefs
                    
                    logger.info(f"✅ Retrieved {len(preferences_dict)} user preferences")
                    return preferences_dict
                    
        except Exception as e:
            logger.error(f"❌ Failed to get all preferences: {e}")
            return {}
    
    def delete_user_preferences(self, email: str) -> bool:
        """Delete user preferences."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        DELETE FROM user_preferences WHERE email = %s
                    """, (email,))
                    
                    deleted_count = cur.rowcount
                    conn.commit()
                    
                    if deleted_count > 0:
                        logger.info(f"✅ Deleted preferences for {email}")
                        return True
                    else:
                        logger.info(f"ℹ️ No preferences found to delete for {email}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Failed to delete preferences for {email}: {e}")
            return False
    
    def get_user_list(self) -> List[str]:
        """Get list of all user emails."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT email FROM user_preferences 
                        ORDER BY updated_at DESC
                    """)
                    
                    results = cur.fetchall()
                    emails = [row[0] for row in results]
                    
                    logger.info(f"✅ Retrieved {len(emails)} user emails")
                    return emails
                    
        except Exception as e:
            logger.error(f"❌ Failed to get user list: {e}")
            return []
    
    def save_monitoring_session(self, user_email: str, session_data: Dict[str, Any]) -> bool:
        """Save monitoring session data."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO monitoring_sessions (user_email, session_data)
                        VALUES (%s, %s)
                        RETURNING id
                    """, (user_email, Json(session_data)))
                    
                    result = cur.fetchone()
                    conn.commit()
                    
                    logger.info(f"✅ Saved monitoring session for {user_email} (ID: {result[0]})")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Failed to save monitoring session: {e}")
            return False
    
    def log_system_status(self, status_type: str, status_data: Dict[str, Any]) -> bool:
        """Log system status for monitoring."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO system_status (status_type, status_data)
                        VALUES (%s, %s)
                    """, (status_type, Json(status_data)))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Failed to log system status: {e}")
            return False
    
    def save_cached_availability(self, check_data: Dict) -> bool:
        """Save availability check results to cache."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO cached_availability (
                            check_type, user_email, availability_data, courses_checked,
                            date_range_start, date_range_end, total_courses, 
                            total_availability_slots, new_availability_count,
                            check_duration_seconds, success, error_message, metadata
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        check_data.get('check_type'),
                        check_data.get('user_email'),
                        Json(check_data.get('availability_data', {})),
                        check_data.get('courses_checked', []),
                        check_data.get('date_range_start'),
                        check_data.get('date_range_end'),
                        check_data.get('total_courses', 0),
                        check_data.get('total_availability_slots', 0),
                        check_data.get('new_availability_count', 0),
                        check_data.get('check_duration_seconds'),
                        check_data.get('success', True),
                        check_data.get('error_message'),
                        Json(check_data.get('metadata', {}))
                    ))
                    
                    conn.commit()
                    logger.info(f"✅ Saved cached availability for {check_data.get('user_email', 'system')}")
                    return True
        except Exception as e:
            logger.error(f"❌ Error saving cached availability: {e}")
            return False
    
    def get_latest_cached_availability(self, user_email: str = None, hours_limit: int = 24) -> Optional[Dict]:
        """Get the most recent cached availability results."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    if user_email:
                        cursor.execute("""
                            SELECT * FROM cached_availability 
                            WHERE user_email = %s 
                            AND check_timestamp > NOW() - INTERVAL %s
                            AND success = TRUE
                            ORDER BY check_timestamp DESC 
                            LIMIT 1
                        """, (user_email, f"{hours_limit} hours"))
                    else:
                        cursor.execute("""
                            SELECT * FROM cached_availability 
                            WHERE check_timestamp > NOW() - INTERVAL %s
                            AND success = TRUE
                            ORDER BY check_timestamp DESC 
                            LIMIT 1
                        """, (f"{hours_limit} hours",))
                    
                    result = cursor.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"❌ Error getting cached availability: {e}")
            return None
    
    def get_cached_availability_history(self, user_email: str = None, limit: int = 10) -> List[Dict]:
        """Get history of cached availability results."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    if user_email:
                        cursor.execute("""
                            SELECT * FROM cached_availability 
                            WHERE user_email = %s 
                            ORDER BY check_timestamp DESC 
                            LIMIT %s
                        """, (user_email, limit))
                    else:
                        cursor.execute("""
                            SELECT * FROM cached_availability 
                            ORDER BY check_timestamp DESC 
                            LIMIT %s
                        """, (limit,))
                    
                    results = cursor.fetchall()
                    return [dict(result) for result in results]
        except Exception as e:
            logger.error(f"❌ Error getting cached availability history: {e}")
            return []
    
    def cleanup_old_data(self, days: int = 30) -> bool:
        """Clean up old monitoring sessions and system status logs."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Clean old monitoring sessions
                    cur.execute("""
                        DELETE FROM monitoring_sessions 
                        WHERE created_at < NOW() - INTERVAL '%s days'
                    """, (days,))
                    sessions_deleted = cur.rowcount
                    
                    # Clean old system status logs
                    cur.execute("""
                        DELETE FROM system_status 
                        WHERE timestamp < NOW() - INTERVAL '%s days'
                    """, (days,))
                    status_deleted = cur.rowcount
                    
                    # Clean old cached availability (keep recent ones)
                    cur.execute("""
                        DELETE FROM cached_availability 
                        WHERE check_timestamp < NOW() - INTERVAL '%s days'
                    """, (days,))
                    cache_deleted = cur.rowcount
                    
                    conn.commit()
                    
                    logger.info(f"✅ Cleanup: {sessions_deleted} sessions, {status_deleted} status logs, {cache_deleted} cached results deleted")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old data: {e}")
            return False
    
    def close(self):
        """Close database connections."""
        try:
            if self.connection_pool:
                self.connection_pool.closeall()
            if self.engine:
                self.engine.dispose()
            logger.info("✅ Database connections closed")
        except Exception as e:
            logger.error(f"❌ Error closing database connections: {e}")

# Global database manager instance
db_manager = None

def get_db_manager() -> PostgreSQLManager:
    """Get global database manager instance."""
    global db_manager
    if db_manager is None:
        db_manager = PostgreSQLManager()
    return db_manager

def initialize_database():
    """Initialize database for the application."""
    try:
        manager = get_db_manager()
        health = manager.health_check()
        if health['connected']:
            logger.info("🎉 PostgreSQL database ready for use!")
            return True
        else:
            logger.error("💥 Database health check failed")
            return False
    except Exception as e:
        logger.error(f"💥 Failed to initialize database: {e}")
        return False

# Compatibility functions for existing code
def load_user_preferences(email: str = None) -> Dict[str, Any]:
    """Load user preferences - compatibility with JSON version."""
    manager = get_db_manager()
    
    if email:
        result = manager.load_user_preferences(email)
        return result if result else {}
    else:
        return manager.get_all_user_preferences()

def save_user_preferences(preferences: Dict[str, Any]) -> bool:
    """Save user preferences - compatibility with JSON version."""
    manager = get_db_manager()
    return manager.save_user_preferences(preferences)
