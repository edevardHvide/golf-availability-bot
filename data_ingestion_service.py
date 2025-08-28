#!/usr/bin/env python3
"""
Data Ingestion Service for Golf Availability Monitor

This service handles saving scraped golf availability data to the database.
It processes the results from the golf monitoring system and stores them
in a structured format for the notification system to use.
"""

import os
import sys
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the streamlit_app directory to the path for imports
sys.path.append(str(Path(__file__).parent / "streamlit_app"))

try:
    from postgresql_manager import get_db_manager
    DATABASE_AVAILABLE = True
    logger.info("✅ PostgreSQL database available for data ingestion")
except ImportError as e:
    DATABASE_AVAILABLE = False
    logger.error(f"❌ Database not available: {e}")

class DataIngestionService:
    """Service for ingesting scraped golf availability data into the database."""
    
    def __init__(self):
        """Initialize the data ingestion service."""
        if not DATABASE_AVAILABLE:
            raise RuntimeError("Database is required for data ingestion service")
        
        self.db_manager = get_db_manager()
        logger.info("📥 Data ingestion service initialized")
    
    def process_availability_results(self, availability_data: Dict[str, Dict[str, int]], 
                                   metadata: Dict[str, Any] = None) -> bool:
        """
        Process availability results from the golf monitoring system.
        
        Args:
            availability_data: Dict with format {"Course Name_YYYY-MM-DD": {"HH:MM": spots_available}}
            metadata: Additional metadata about the scraping run
            
        Returns:
            bool: True if processing was successful
        """
        try:
            scraped_entries = []
            
            for state_key, time_slots in availability_data.items():
                # Parse the state key to extract course name and date
                if '_' not in state_key:
                    logger.warning(f"Invalid state key format: {state_key}")
                    continue
                
                # Split on the last underscore to handle course names with underscores
                parts = state_key.rsplit('_', 1)
                if len(parts) != 2:
                    logger.warning(f"Could not parse state key: {state_key}")
                    continue
                
                course_name = parts[0]
                date_str = parts[1]
                
                # Validate date format
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"Invalid date format in state key: {state_key}")
                    continue
                
                # Process each time slot
                for time_slot, spots_available in time_slots.items():
                    # Validate time slot format
                    if not self._is_valid_time_format(time_slot):
                        logger.warning(f"Invalid time format: {time_slot}")
                        continue
                    
                    # Create scraped entry
                    entry = {
                        'course_name': course_name,
                        'date': date_obj,
                        'time_slot': time_slot,
                        'spots_available': int(spots_available),
                        'metadata': {
                            'scraping_timestamp': datetime.now().isoformat(),
                            'source': 'golf_availability_monitor',
                            **(metadata or {})
                        }
                    }
                    scraped_entries.append(entry)
            
            if scraped_entries:
                # Save to database
                success = self.db_manager.save_scraped_times(scraped_entries)
                if success:
                    logger.info(f"✅ Successfully ingested {len(scraped_entries)} availability entries")
                    return True
                else:
                    logger.error(f"❌ Failed to save {len(scraped_entries)} entries to database")
                    return False
            else:
                logger.info("📭 No valid availability entries to ingest")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error processing availability results: {e}")
            return False
    
    def _is_valid_time_format(self, time_str: str) -> bool:
        """Validate that time string is in HH:MM format."""
        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                return False
            
            hour, minute = int(parts[0]), int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except (ValueError, AttributeError):
            return False
    
    def ingest_from_monitoring_results(self, results: Dict[str, Any]) -> bool:
        """
        Ingest data from golf monitoring results.
        
        Args:
            results: Results dict from golf_availability_monitor.py
            
        Returns:
            bool: True if ingestion was successful
        """
        try:
            availability_data = results.get('availability', {})
            if not availability_data:
                logger.info("📭 No availability data in results")
                return True
            
            # Extract metadata from results
            metadata = {
                'check_timestamp': results.get('timestamp'),
                'check_type': results.get('check_type', 'unknown'),
                'total_courses': results.get('total_courses', 0),
                'total_dates': results.get('total_dates', 0),
                'duration_seconds': results.get('duration_seconds'),
                'success': results.get('success', True)
            }
            
            return self.process_availability_results(availability_data, metadata)
            
        except Exception as e:
            logger.error(f"❌ Error ingesting monitoring results: {e}")
            return False
    
    def ingest_from_json_file(self, json_file_path: str) -> bool:
        """
        Ingest data from a JSON file (for testing or batch processing).
        
        Args:
            json_file_path: Path to JSON file with availability data
            
        Returns:
            bool: True if ingestion was successful
        """
        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            # Handle different JSON formats
            if 'availability' in data:
                # Format from golf monitoring results
                return self.ingest_from_monitoring_results(data)
            elif isinstance(data, dict):
                # Direct availability data format
                return self.process_availability_results(data)
            else:
                logger.error(f"❌ Unrecognized JSON format in {json_file_path}")
                return False
                
        except FileNotFoundError:
            logger.error(f"❌ JSON file not found: {json_file_path}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in {json_file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error ingesting from JSON file: {e}")
            return False
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """
        Clean up old scraped data to prevent database bloat.
        
        Args:
            days_to_keep: Number of days of data to keep
            
        Returns:
            bool: True if cleanup was successful
        """
        try:
            # Use the database manager's cleanup method
            success = self.db_manager.cleanup_old_data(days_to_keep)
            if success:
                logger.info(f"✅ Cleaned up data older than {days_to_keep} days")
            else:
                logger.error(f"❌ Failed to clean up old data")
            return success
            
        except Exception as e:
            logger.error(f"❌ Error during data cleanup: {e}")
            return False

def integrate_with_golf_monitor():
    """
    Integration function to be called from golf_availability_monitor.py
    This allows the existing monitoring system to save data to the database.
    """
    if not DATABASE_AVAILABLE:
        logger.warning("⚠️ Database not available - skipping data ingestion")
        return None
    
    try:
        return DataIngestionService()
    except Exception as e:
        logger.error(f"❌ Failed to initialize data ingestion service: {e}")
        return None

# Command-line interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Golf Availability Data Ingestion Service")
    parser.add_argument("--json-file", help="Ingest data from JSON file")
    parser.add_argument("--cleanup", type=int, help="Clean up data older than N days")
    parser.add_argument("--test", action="store_true", help="Run test ingestion")
    
    args = parser.parse_args()
    
    if not DATABASE_AVAILABLE:
        logger.error("❌ Database not available. Set DATABASE_URL environment variable.")
        sys.exit(1)
    
    try:
        ingestion_service = DataIngestionService()
        
        if args.json_file:
            logger.info(f"📥 Ingesting data from {args.json_file}")
            success = ingestion_service.ingest_from_json_file(args.json_file)
            if success:
                logger.info("✅ JSON ingestion completed successfully")
            else:
                logger.error("❌ JSON ingestion failed")
                sys.exit(1)
        
        elif args.cleanup:
            logger.info(f"🧹 Cleaning up data older than {args.cleanup} days")
            success = ingestion_service.cleanup_old_data(args.cleanup)
            if success:
                logger.info("✅ Data cleanup completed successfully")
            else:
                logger.error("❌ Data cleanup failed")
                sys.exit(1)
        
        elif args.test:
            logger.info("🧪 Running test ingestion")
            # Create test data
            test_data = {
                "Test Golf Club_2024-01-15": {
                    "09:00": 4,
                    "10:00": 2,
                    "14:00": 3
                },
                "Another Course_2024-01-16": {
                    "08:30": 2,
                    "16:00": 1
                }
            }
            
            success = ingestion_service.process_availability_results(test_data, {"test": True})
            if success:
                logger.info("✅ Test ingestion completed successfully")
            else:
                logger.error("❌ Test ingestion failed")
                sys.exit(1)
        
        else:
            parser.print_help()
            
    except Exception as e:
        logger.error(f"💥 Data ingestion service failed: {e}")
        sys.exit(1)
