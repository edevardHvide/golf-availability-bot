# Weekday/Weekend Preferences Integration Guide

## Overview

The application now supports different time preferences for weekdays and weekends. This guide explains how to integrate this functionality throughout the golf monitoring system.

## Data Structure

### New Preference Format

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "selected_courses": ["oslo_golfklubb", "baerum_gk"],
  "preference_type": "Different for weekdays/weekends",
  "time_preferences": {
    "weekdays": {
      "time_slots": ["07:00", "07:30", "08:00", "08:30"],
      "time_intervals": ["07:00-09:00"],
      "method": "Custom Time Intervals"
    },
    "weekends": {
      "time_slots": ["09:00", "09:30", "10:00", "10:30", "11:00"],
      "time_intervals": ["09:00-12:00"],
      "method": "Custom Time Intervals"
    }
  },
  "min_players": 2,
  "days_ahead": 4
}
```

### Legacy Format (Same for all days)

```json
{
  "preference_type": "Same for all days",
  "time_preferences": {
    "all_days": {
      "time_slots": ["07:00", "07:30", "08:00"],
      "time_intervals": ["07:00-09:00"],
      "method": "Custom Time Intervals"
    }
  }
}
```

## Utility Functions

Use the functions from `time_utils.py`:

```python
from time_utils import (
    get_time_slots_for_date,
    get_time_intervals_for_date,
    get_day_type,
    is_weekend,
    validate_time_preferences,
    format_preferences_summary
)

# Example usage
from datetime import date

target_date = date(2024, 1, 15)  # Monday
user_preferences = load_user_preferences(email)

# Get appropriate time slots for the date
time_slots = get_time_slots_for_date(user_preferences, target_date)

# Check if it's a weekend
if is_weekend(target_date):
    print("It's a weekend!")

# Get day type
day_type = get_day_type(target_date)  # Returns 'weekdays' or 'weekends'
```

## Integration Points

### 1. Golf Availability Monitor (`golf_availability_monitor.py`)

Update the monitoring logic to use date-specific preferences:

```python
def check_availability_for_user(user_email, target_date):
    """Check availability for a user on a specific date"""
    user_preferences = load_user_preferences(user_email)
    
    # Get time slots for this specific date
    time_slots = get_time_slots_for_date(user_preferences, target_date)
    
    if not time_slots:
        logger.info(f"No time preferences for {user_email} on {target_date}")
        return []
    
    # Continue with existing availability checking logic
    return check_golf_availability(
        courses=user_preferences['selected_courses'],
        time_slots=time_slots,
        target_date=target_date
    )
```

### 2. Notification System

Update notification logic to include day-specific information:

```python
def send_availability_notification(user_email, available_slots, target_date):
    """Send notification with day-specific context"""
    user_preferences = load_user_preferences(user_email)
    
    day_type = "weekend" if is_weekend(target_date) else "weekday"
    
    message = f"""
    Golf availability found for {target_date.strftime('%A, %B %d')} ({day_type})!
    
    Available slots: {', '.join(available_slots)}
    
    Your {day_type} preferences: {format_preferences_summary(user_preferences)}
    """
    
    send_email_notification(user_email, "Golf Availability Alert", message)
```

### 3. Batch Processing

When processing multiple days, handle each date individually:

```python
def process_availability_for_user(user_email, date_range):
    """Process availability for a user across multiple dates"""
    user_preferences = load_user_preferences(user_email)
    
    for target_date in date_range:
        # Get date-specific preferences
        time_slots = get_time_slots_for_date(user_preferences, target_date)
        
        if time_slots:
            availability = check_availability_for_date(
                user_preferences['selected_courses'],
                time_slots,
                target_date
            )
            
            if availability:
                send_availability_notification(user_email, availability, target_date)
```

## UI Integration

### Profile Display

Show preference summary in the UI:

```python
def display_user_profile(preferences):
    st.write(f"**Preference Type:** {preferences['preference_type']}")
    st.write(f"**Time Preferences:** {format_preferences_summary(preferences)}")
    
    if preferences['preference_type'] == "Different for weekdays/weekends":
        weekday_prefs = preferences['time_preferences'].get('weekdays', {})
        weekend_prefs = preferences['time_preferences'].get('weekends', {})
        
        st.write("**Weekday Times:**", ', '.join(weekday_prefs.get('time_intervals', [])))
        st.write("**Weekend Times:**", ', '.join(weekend_prefs.get('time_intervals', [])))
```

## Migration Notes

### Existing Users

For users with the old format, the system will:

1. Treat existing `time_slots` as "Same for all days"
2. Set `preference_type` to "Same for all days"
3. Move existing preferences to `time_preferences.all_days`

### Database Updates

If using PostgreSQL, update the schema to accommodate the new nested structure:

```sql
-- Add new columns
ALTER TABLE user_preferences ADD COLUMN preference_type VARCHAR(50) DEFAULT 'Same for all days';
ALTER TABLE user_preferences ADD COLUMN time_preferences JSONB;

-- Migrate existing data
UPDATE user_preferences 
SET time_preferences = jsonb_build_object(
    'all_days', jsonb_build_object(
        'time_slots', time_slots,
        'time_intervals', time_intervals,
        'method', 'Preset Ranges'
    )
)
WHERE time_preferences IS NULL;
```

## Testing

Test with different scenarios:

```python
def test_weekday_weekend_logic():
    from datetime import date
    
    # Test weekday
    monday = date(2024, 1, 15)
    assert get_day_type(monday) == "weekdays"
    assert not is_weekend(monday)
    
    # Test weekend
    saturday = date(2024, 1, 13)
    assert get_day_type(saturday) == "weekends"
    assert is_weekend(saturday)
    
    # Test preferences
    prefs = {
        'preference_type': 'Different for weekdays/weekends',
        'time_preferences': {
            'weekdays': {'time_slots': ['07:00', '08:00']},
            'weekends': {'time_slots': ['09:00', '10:00']}
        }
    }
    
    weekday_slots = get_time_slots_for_date(prefs, monday)
    weekend_slots = get_time_slots_for_date(prefs, saturday)
    
    assert weekday_slots == ['07:00', '08:00']
    assert weekend_slots == ['09:00', '10:00']
```

## Error Handling

Handle edge cases gracefully:

```python
def safe_get_time_slots(preferences, target_date):
    """Safely get time slots with fallback"""
    try:
        return get_time_slots_for_date(preferences, target_date)
    except KeyError:
        # Fallback to legacy format
        return preferences.get('time_slots', [])
    except Exception as e:
        logger.error(f"Error getting time slots: {e}")
        return []
```

This comprehensive integration ensures that the weekday/weekend preferences are respected throughout the entire golf monitoring system.
