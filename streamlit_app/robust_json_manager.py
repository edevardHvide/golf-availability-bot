#!/usr/bin/env python3
"""
Robust JSON Manager for Golf Availability Monitor

This module provides robust JSON file handling with backup, recovery,
and atomic writes. Essential for Render deployment where file persistence
needs to be reliable.
"""

import json
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class RobustJSONManager:
    """
    Robust JSON file manager with atomic writes, backups, and recovery.
    
    Features:
    - Atomic writes (write to temp file, then rename)
    - Automatic backups with rotation
    - Lock-based thread safety
    - Corruption detection and recovery
    - Retry logic for failed operations
    """
    
    def __init__(self, file_path: str, backup_count: int = 3, create_dirs: bool = True):
        """
        Initialize the robust JSON manager.
        
        Args:
            file_path: Path to the JSON file
            backup_count: Number of backup files to keep
            create_dirs: Whether to create parent directories if they don't exist
        """
        self.file_path = Path(file_path)
        self.backup_count = backup_count
        self.lock = threading.RLock()
        
        if create_dirs:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize backup directory
        self.backup_dir = self.file_path.parent / f".{self.file_path.stem}_backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Initialize file if it doesn't exist
        if not self.file_path.exists():
            self._write_data({})
    
    def load(self) -> Dict[str, Any]:
        """
        Load data from JSON file with automatic recovery if corrupted.
        
        Returns:
            Dictionary containing the loaded data
        """
        with self.lock:
            return self._load_with_retry()
    
    def save(self, data: Dict[str, Any]) -> bool:
        """
        Save data to JSON file atomically with backup.
        
        Args:
            data: Dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            return self._save_with_retry(data)
    
    def backup(self) -> bool:
        """
        Create a backup of the current file.
        
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                if not self.file_path.exists():
                    return True
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.backup_dir / f"{self.file_path.stem}_{timestamp}.json"
                
                shutil.copy2(self.file_path, backup_file)
                
                # Rotate old backups
                self._rotate_backups()
                
                logger.info(f"Backup created: {backup_file}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to create backup: {e}")
                return False
    
    def get_backups(self) -> list:
        """
        Get list of available backup files.
        
        Returns:
            List of backup file paths, sorted by creation time (newest first)
        """
        if not self.backup_dir.exists():
            return []
        
        backups = list(self.backup_dir.glob(f"{self.file_path.stem}_*.json"))
        return sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def restore_from_backup(self, backup_index: int = 0) -> bool:
        """
        Restore from a backup file.
        
        Args:
            backup_index: Index of backup to restore (0 = newest)
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                backups = self.get_backups()
                if not backups or backup_index >= len(backups):
                    logger.error("No backup available for restoration")
                    return False
                
                backup_file = backups[backup_index]
                
                # Verify backup is valid JSON
                with open(backup_file, 'r', encoding='utf-8') as f:
                    json.load(f)  # This will raise an exception if invalid
                
                # Copy backup to main file
                shutil.copy2(backup_file, self.file_path)
                
                logger.info(f"Restored from backup: {backup_file}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to restore from backup: {e}")
                return False
    
    def _load_with_retry(self, max_retries: int = 3) -> Dict[str, Any]:
        """Load data with retry and recovery logic."""
        for attempt in range(max_retries):
            try:
                if not self.file_path.exists():
                    return {}
                
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Validate data structure
                if not isinstance(data, dict):
                    raise ValueError("JSON file does not contain a dictionary")
                
                return data
                
            except (json.JSONDecodeError, ValueError, FileNotFoundError) as e:
                logger.warning(f"Attempt {attempt + 1}: Failed to load JSON: {e}")
                
                if attempt < max_retries - 1:
                    # Try to recover from backup
                    if self._try_recovery():
                        continue
                    
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error("All attempts failed, returning empty dictionary")
                    return {}
            
            except Exception as e:
                logger.error(f"Unexpected error loading JSON: {e}")
                return {}
        
        return {}
    
    def _save_with_retry(self, data: Dict[str, Any], max_retries: int = 3) -> bool:
        """Save data with retry logic."""
        # Create backup before writing
        self.backup()
        
        for attempt in range(max_retries):
            try:
                return self._write_data(data)
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}: Failed to save JSON: {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error("All save attempts failed")
                    return False
        
        return False
    
    def _write_data(self, data: Dict[str, Any]) -> bool:
        """Write data atomically using temporary file."""
        try:
            # Add metadata
            enriched_data = {
                "_metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0",
                    "source": "golf_availability_monitor"
                },
                "users": data if isinstance(data, dict) else {}
            }
            
            # Write to temporary file first
            temp_file = self.file_path.with_suffix('.tmp')
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(enriched_data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            # Atomic rename
            temp_file.replace(self.file_path)
            
            logger.debug(f"Successfully wrote JSON to {self.file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write JSON: {e}")
            # Clean up temp file if it exists
            if 'temp_file' in locals() and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            return False
    
    def _try_recovery(self) -> bool:
        """Try to recover from the most recent backup."""
        try:
            backups = self.get_backups()
            if backups:
                logger.info("Attempting recovery from backup")
                return self.restore_from_backup(0)
            return False
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return False
    
    def _rotate_backups(self):
        """Remove old backup files, keeping only the specified number."""
        try:
            backups = self.get_backups()
            
            # Remove excess backups
            for backup in backups[self.backup_count:]:
                backup.unlink()
                logger.debug(f"Removed old backup: {backup}")
                
        except Exception as e:
            logger.error(f"Failed to rotate backups: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the JSON file and backups."""
        with self.lock:
            stats = {
                "file_exists": self.file_path.exists(),
                "file_size": self.file_path.stat().st_size if self.file_path.exists() else 0,
                "backup_count": len(self.get_backups()),
                "last_modified": None
            }
            
            if self.file_path.exists():
                stats["last_modified"] = datetime.fromtimestamp(
                    self.file_path.stat().st_mtime
                ).isoformat()
            
            return stats


# Global instance for user preferences
preferences_manager = RobustJSONManager(
    file_path="user_preferences.json",
    backup_count=5
)

def load_user_preferences() -> Dict[str, Any]:
    """Load user preferences using the robust manager."""
    data = preferences_manager.load()
    return data.get("users", {})

def save_user_preferences(preferences: Dict[str, Any]) -> bool:
    """Save user preferences using the robust manager."""
    return preferences_manager.save(preferences)

def get_preferences_stats() -> Dict[str, Any]:
    """Get statistics about the preferences file."""
    return preferences_manager.get_stats()


if __name__ == "__main__":
    # Demo/test the robust JSON manager
    print("🧪 Testing Robust JSON Manager")
    
    # Test data
    test_data = {
        "user1@example.com": {
            "name": "Test User 1",
            "email": "user1@example.com",
            "preferences": ["course1", "course2"]
        },
        "user2@example.com": {
            "name": "Test User 2", 
            "email": "user2@example.com",
            "preferences": ["course3", "course4"]
        }
    }
    
    # Test saving
    print("💾 Testing save...")
    success = save_user_preferences(test_data)
    print(f"Save result: {'✅ Success' if success else '❌ Failed'}")
    
    # Test loading
    print("📖 Testing load...")
    loaded_data = load_user_preferences()
    print(f"Loaded {len(loaded_data)} users")
    
    # Test stats
    print("📊 File stats:")
    stats = get_preferences_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("✅ Robust JSON Manager test complete!")
