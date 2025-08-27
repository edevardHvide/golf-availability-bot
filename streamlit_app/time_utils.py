"""
Time utility functions for handling weekday/weekend preferences
"""

from datetime import datetime, date
from typing import Dict, List, Any


def is_weekend(target_date: date) -> bool:
    """Check if a given date is a weekend (Saturday=5, Sunday=6)"""
    return target_date.weekday() >= 5


def get_day_type(target_date: date) -> str:
    """Get the day type ('weekdays' or 'weekends') for a given date"""
    return "weekends" if is_weekend(target_date) else "weekdays"


def get_time_slots_for_date(preferences: Dict[str, Any], target_date: date) -> List[str]:
    """
    Get the appropriate time slots for a given date based on user preferences.
    
    Args:
        preferences: User preferences dictionary
        target_date: The date to get time slots for
    
    Returns:
        List of time slots for the given date
    """
    time_preferences = preferences.get('time_preferences', {})
    preference_type = preferences.get('preference_type', 'Same for all days')
    
    if preference_type == "Same for all days":
        # Use 'all_days' preferences
        all_days_prefs = time_preferences.get('all_days', {})
        return all_days_prefs.get('time_slots', [])
    else:
        # Use weekday/weekend specific preferences
        day_type = get_day_type(target_date)
        day_prefs = time_preferences.get(day_type, {})
        return day_prefs.get('time_slots', [])


def get_time_intervals_for_date(preferences: Dict[str, Any], target_date: date) -> List[str]:
    """
    Get the appropriate time intervals for a given date based on user preferences.
    
    Args:
        preferences: User preferences dictionary
        target_date: The date to get time intervals for
    
    Returns:
        List of time intervals for the given date
    """
    time_preferences = preferences.get('time_preferences', {})
    preference_type = preferences.get('preference_type', 'Same for all days')
    
    if preference_type == "Same for all days":
        # Use 'all_days' preferences
        all_days_prefs = time_preferences.get('all_days', {})
        return all_days_prefs.get('time_intervals', [])
    else:
        # Use weekday/weekend specific preferences
        day_type = get_day_type(target_date)
        day_prefs = time_preferences.get(day_type, {})
        return day_prefs.get('time_intervals', [])


def format_preferences_summary(preferences: Dict[str, Any]) -> str:
    """
    Create a human-readable summary of time preferences.
    
    Args:
        preferences: User preferences dictionary
    
    Returns:
        Formatted string summarizing the preferences
    """
    time_preferences = preferences.get('time_preferences', {})
    preference_type = preferences.get('preference_type', 'Same for all days')
    
    if preference_type == "Same for all days":
        all_days_prefs = time_preferences.get('all_days', {})
        slots_count = len(all_days_prefs.get('time_slots', []))
        intervals_count = len(all_days_prefs.get('time_intervals', []))
        
        if intervals_count > 0:
            return f"All days: {intervals_count} time intervals"
        elif slots_count > 0:
            return f"All days: {slots_count} time slots"
        else:
            return "No time preferences set"
    else:
        summary_parts = []
        
        for day_type in ['weekdays', 'weekends']:
            day_prefs = time_preferences.get(day_type, {})
            slots_count = len(day_prefs.get('time_slots', []))
            intervals_count = len(day_prefs.get('time_intervals', []))
            
            day_label = "Weekdays" if day_type == "weekdays" else "Weekends"
            
            if intervals_count > 0:
                summary_parts.append(f"{day_label}: {intervals_count} intervals")
            elif slots_count > 0:
                summary_parts.append(f"{day_label}: {slots_count} slots")
        
        return "; ".join(summary_parts) if summary_parts else "No time preferences set"


def validate_time_preferences(preferences: Dict[str, Any]) -> List[str]:
    """
    Validate time preferences and return any validation errors.
    
    Args:
        preferences: User preferences dictionary
    
    Returns:
        List of validation error messages
    """
    errors = []
    time_preferences = preferences.get('time_preferences', {})
    preference_type = preferences.get('preference_type', 'Same for all days')
    
    if preference_type == "Same for all days":
        all_days_prefs = time_preferences.get('all_days', {})
        slots = all_days_prefs.get('time_slots', [])
        intervals = all_days_prefs.get('time_intervals', [])
        
        if not slots and not intervals:
            errors.append("Please set time preferences for all days")
    else:
        for day_type in ['weekdays', 'weekends']:
            day_prefs = time_preferences.get(day_type, {})
            slots = day_prefs.get('time_slots', [])
            intervals = day_prefs.get('time_intervals', [])
            
            day_label = "weekdays" if day_type == "weekdays" else "weekends"
            
            if not slots and not intervals:
                errors.append(f"Please set time preferences for {day_label}")
    
    return errors
