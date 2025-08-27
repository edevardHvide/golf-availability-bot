#!/usr/bin/env python3
"""
Enhanced Streamlit Frontend for Golf Availability Monitor

This provides a modern, user-friendly interface for configuring golf monitoring preferences
with robust API integration and error handling.
"""

import streamlit as st
import requests
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging

# Import golf course data and time utilities
from golf_courses import get_available_courses
from time_utils import validate_time_preferences, format_preferences_summary

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000"
FALLBACK_PREFERENCES_FILE = Path(__file__).parent.parent / "user_preferences.json"

# Page configuration
st.set_page_config(
    page_title="Golf Availability Monitor",
    page_icon="🏌️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #4CAF50 0%, #45a049 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .course-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4CAF50;
        margin: 0.5rem 0;
    }
    .preference-section {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .success-message {
        background: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #c3e6cb;
    }
    .warning-message {
        background: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #ffeaa7;
    }
    .error-message {
        background: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #f5c6cb;
    }
    .status-indicator {
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    .status-healthy {
        background: #d4edda;
        color: #155724;
    }
    .status-warning {
        background: #fff3cd;
        color: #856404;
    }
    .status-error {
        background: #f8d7da;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

class GolfMonitorApp:
    """Main application class for the Golf Availability Monitor."""
    
    def __init__(self):
        self.api_available = self._check_api_status()
        self.system_status = self._get_system_status()
        
    def _check_api_status(self) -> bool:
        """Check if the API server is available."""
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=3)
            return response.status_code == 200
        except Exception:
            return False
    
    def _get_system_status(self) -> Dict:
        """Get comprehensive system status."""
        try:
            if self.api_available:
                response = requests.get(f"{API_BASE_URL}/api/status", timeout=5)
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Failed to get system status: {e}")
        
        return {
            "status": "api_unavailable",
            "golf_system_available": False,
            "user_count": 0,
            "backup_count": 0
        }
    
    def show_status_indicator(self):
        """Display system status indicator in sidebar."""
        status = self.system_status.get("status", "unknown")
        
        st.sidebar.markdown("### 🔗 Connection Status")
        
        if status == "healthy" and self.api_available:
            st.sidebar.markdown(
                '<div class="status-indicator status-healthy">🟢 System Online</div>',
                unsafe_allow_html=True
            )
        elif status == "api_unavailable":
            st.sidebar.markdown(
                '<div class="status-indicator status-warning">🟡 API Offline (Local Mode)</div>',
                unsafe_allow_html=True
            )
        else:
            st.sidebar.markdown(
                '<div class="status-indicator status-error">🔴 System Issues</div>',
                unsafe_allow_html=True
            )
        
        # Show additional system info
        if self.api_available:
            st.sidebar.metric("Active Users", self.system_status.get("user_count", 0))
            
            golf_status = "✅ Available" if self.system_status.get("golf_system_available") else "🔶 Demo Mode"
            st.sidebar.markdown(f"**Golf System:** {golf_status}")
    
    def show_service_info(self):
        """Show service information at bottom of sidebar."""
        st.sidebar.markdown("### 🔧 System Info")
        
        if self.api_available:
            st.sidebar.success("🟢 API Server Online")
            if self.system_status.get("golf_system_available"):
                st.sidebar.success("🟢 Golf System Available")
            else:
                st.sidebar.warning("🔶 Golf System in Demo Mode")
            
            st.sidebar.metric("Backups Available", self.system_status.get("backup_count", 0))
        else:
            st.sidebar.warning("🟡 API Offline - Local Mode")
            st.sidebar.info("💡 Data will be saved locally")
    
    def load_preferences_from_api(self, email: str) -> Dict:
        """Load user preferences from API."""
        try:
            response = requests.get(f"{API_BASE_URL}/api/preferences/{email}", timeout=5)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {}
        except Exception as e:
            logger.warning(f"API request failed: {e}")
        
        return self._load_preferences_fallback(email)
    
    def _load_preferences_fallback(self, email: str) -> Dict:
        """Fallback to local file when API is unavailable."""
        try:
            if FALLBACK_PREFERENCES_FILE.exists():
                with open(FALLBACK_PREFERENCES_FILE, 'r') as f:
                    data = json.load(f)
                
                if isinstance(data, dict) and "users" in data:
                    return data["users"].get(email, {})
        except Exception as e:
            logger.error(f"Fallback load failed: {e}")
        
        return {}
    
    def save_preferences_to_api(self, preferences: Dict) -> bool:
        """Save user preferences to API."""
        try:
            if self.api_available:
                response = requests.post(
                    f"{API_BASE_URL}/api/preferences",
                    json=preferences,
                    timeout=10
                )
                if response.status_code == 200:
                    return True
                else:
                    st.error(f"API Error: {response.text}")
        except Exception as e:
            st.warning(f"API unavailable, saving locally: {e}")
        
        return self._save_preferences_fallback(preferences)
    
    def _save_preferences_fallback(self, preferences: Dict) -> bool:
        """Fallback to local file when API is unavailable."""
        try:
            # Load existing data
            existing_data = {"users": {}}
            if FALLBACK_PREFERENCES_FILE.exists():
                with open(FALLBACK_PREFERENCES_FILE, 'r') as f:
                    existing_data = json.load(f)
            
            # Ensure proper format
            if "users" not in existing_data:
                existing_data = {"users": {}}
            
            # Add new preferences
            existing_data["users"][preferences['email']] = preferences
            
            # Save with metadata
            existing_data["_metadata"] = {
                "last_updated": datetime.now().isoformat(),
                "version": "2.0",
                "source": "streamlit_fallback"
            }
            
            FALLBACK_PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(FALLBACK_PREFERENCES_FILE, 'w') as f:
                json.dump(existing_data, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Fallback save failed: {e}")
            return False

    def get_available_courses(self) -> List[Dict]:
        """Get list of available golf courses - using static data for efficiency."""
        # Golf courses rarely change, so we keep them static for better performance
        return get_available_courses()
    
    def generate_time_slots(self) -> List[str]:
        """Generate available time slots for selection."""
        slots = []
        for hour in range(7, 20):  # 7 AM to 7 PM
            for minute in [0, 30]:
                slots.append(f"{hour:02d}:{minute:02d}")
        return slots
    
    def get_existing_users(self) -> List[str]:
        """Get list of existing user emails for quick selection."""
        try:
            if self.api_available:
                response = requests.get(f"{API_BASE_URL}/api/preferences", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    prefs = data.get("preferences", {})
                    return list(prefs.keys())
        except Exception:
            pass
        
        # Fallback to local file
        try:
            if FALLBACK_PREFERENCES_FILE.exists():
                with open(FALLBACK_PREFERENCES_FILE, 'r') as f:
                    data = json.load(f)
                
                if "users" in data:
                    return list(data["users"].keys())
        except Exception:
            pass
    
        return []
    
    def send_test_notification(self, email: str, name: str) -> bool:
        """Send a test notification."""
        try:
            if self.api_available:
                response = requests.post(
                    f"{API_BASE_URL}/api/test-notification",
                    json={"email": email, "name": name},
                    timeout=10
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get("type") == "demo_mode":
                        st.info("📧 Demo Mode: Test notification simulated successfully")
                    else:
                        st.success("📧 Test notification sent successfully!")
                    return True
                else:
                    st.error(f"Failed to send test notification: {response.text}")
        except Exception as e:
            st.error(f"Error sending test notification: {e}")
        
        return False
    
    def show_profile_management(self):
        """Show profile loading/management section."""
        st.sidebar.markdown("### 👤 Profile Management")
        
        existing_users = self.get_existing_users()
        
        if existing_users:
            selected_user = st.sidebar.selectbox(
                "Quick Load Profile",
                [""] + existing_users,
                help="Select an existing profile to load quickly"
            )
            
            if selected_user and selected_user != st.session_state.get('current_user_email'):
                if st.sidebar.button("🔄 Load Selected Profile"):
                    preferences = self.load_preferences_from_api(selected_user)
                    if preferences:
                        st.session_state.user_preferences = preferences
                        st.session_state.current_user_email = selected_user
                        st.success(f"✅ Loaded profile for {preferences.get('name', selected_user)}")
                        st.rerun()
        
        # Manual email load
        st.sidebar.markdown("---")
        email_to_load = st.sidebar.text_input(
            "Load by Email",
            placeholder="user@example.com"
        )
        
        if email_to_load and st.sidebar.button("📥 Load Profile"):
            preferences = self.load_preferences_from_api(email_to_load)
            if preferences:
                st.session_state.user_preferences = preferences
                st.session_state.current_user_email = email_to_load
                st.success(f"✅ Loaded profile for {preferences.get('name', email_to_load)}")
                st.rerun()
            else:
                st.warning(f"❌ No profile found for {email_to_load}")
        
        # Show current loaded profile
        if st.session_state.get('current_user_email'):
            st.sidebar.markdown("#### Current Profile")
            current_prefs = st.session_state.get('user_preferences', {})
            st.sidebar.markdown(f"""
            <div style="background: #e3f2fd; padding: 1rem; border-radius: 8px; margin: 0.5rem 0;">
                <strong>{current_prefs.get('name', 'Unknown')}</strong><br>
                <small>{current_prefs.get('email', '')}</small>
            </div>
            """, unsafe_allow_html=True)
            
            if st.sidebar.button("🗑️ Clear Profile"):
                st.session_state.user_preferences = {}
                st.session_state.current_user_email = None
                st.rerun()
    
def main():
    """Main Streamlit application."""
    
    # Initialize the app
    app = GolfMonitorApp()
    
    # Initialize session state
    if 'user_preferences' not in st.session_state:
        st.session_state.user_preferences = {}
    
    # Show header
    st.markdown("""
    <div class="main-header">
        <h1>🏌️ Golf Availability Monitor</h1>
        <p>Configure your personalized golf tee time notifications</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Sidebar status and profile management
    app.show_status_indicator()
    app.show_profile_management()
    
    # Move service info to bottom of sidebar
    st.sidebar.markdown("---")
    app.show_service_info()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Load current preferences
        preferences = st.session_state.get('user_preferences', {})
        
        st.markdown("### 👤 User Information")
        
        name = st.text_input(
            "Full Name",
            value=preferences.get('name', ''),
            placeholder="Enter your full name",
            help="This will be used in email notifications"
        )
        
        email = st.text_input(
            "Email Address",
            value=preferences.get('email', ''),
            placeholder="your.email@example.com",
            help="Where you'll receive availability notifications"
        )
        
        st.markdown("---")
        
        # Golf Course Selection
        st.markdown("### 🏌️ Golf Course Selection")
        
        available_courses = app.get_available_courses()
        course_options = {course["name"]: course["key"] for course in available_courses}
        
        selected_course_names = st.multiselect(
            "Select Golf Courses",
            options=list(course_options.keys()),
            default=[
                name for name, course_key in course_options.items()
                if course_key in preferences.get('selected_courses', [])
            ],
            help="Choose the golf courses you want to monitor"
        )
        
        selected_courses = [course_options[name] for name in selected_course_names]
        
        st.markdown("---")
        
        # Time Preferences
        st.markdown("### ⏰ Time Preferences")
        
        # Day type selection
        day_type_preference = st.radio(
            "Preference Type",
            ["Same for all days", "Different for weekdays/weekends"],
            help="Choose whether you want the same preferences for all days or different ones for weekdays vs weekends"
        )
        
        if day_type_preference == "Same for all days":
            day_types_to_configure = ["all_days"]
        else:
            day_types_to_configure = ["weekdays", "weekends"]
        
        time_slots = []
        all_preferences = {}
        
        # Configure preferences for each day type
        for day_type in day_types_to_configure:
            if len(day_types_to_configure) > 1:
                day_label = "Weekdays (Mon-Fri)" if day_type == "weekdays" else "Weekends (Sat-Sun)"
                st.markdown(f"#### {day_label}")
            
            # Initialize session state keys for this day type
            time_intervals_key = f'time_intervals_{day_type}'
            if time_intervals_key not in st.session_state:
                existing_prefs = preferences.get('time_preferences', {}).get(day_type, {})
                st.session_state[time_intervals_key] = existing_prefs.get('time_intervals', [])
            
            time_preference = st.radio(
                "Time Selection Method",
                ["Preset Ranges", "Custom Time Intervals"],
                key=f"time_pref_{day_type}",
                help="Choose how you want to specify your preferred times"
            )
            
            day_time_slots = []
            
            if time_preference == "Preset Ranges":
                preset_ranges = st.multiselect(
                    "Select Time Ranges",
                    ["Morning (07:00-11:00)", "Afternoon (11:00-15:00)", "Evening (15:00-19:00)"],
                    key=f"preset_{day_type}",
                    help="Select your preferred time ranges"
                )
                
                # Convert preset ranges to time slots
                for preset in preset_ranges:
                    if "Morning" in preset:
                        day_time_slots.extend([f"{h:02d}:00" for h in range(7, 11)])
                        day_time_slots.extend([f"{h:02d}:30" for h in range(7, 11)])
                    elif "Afternoon" in preset:
                        day_time_slots.extend([f"{h:02d}:00" for h in range(11, 15)])
                        day_time_slots.extend([f"{h:02d}:30" for h in range(11, 15)])
                    elif "Evening" in preset:
                        day_time_slots.extend([f"{h:02d}:00" for h in range(15, 19)])
                        day_time_slots.extend([f"{h:02d}:30" for h in range(15, 19)])
            
            else:
                st.markdown("**Define Custom Time Intervals**")
                
                # Add new interval section
                st.markdown("**Add Time Interval:**")
                col_start, col_end, col_add = st.columns([2, 2, 1])
                
                with col_start:
                    start_time = st.time_input(
                        "Start Time",
                        value=datetime.strptime("07:00", "%H:%M").time(),
                        key=f"start_time_{day_type}"
                    )
                
                with col_end:
                    end_time = st.time_input(
                        "End Time",
                        value=datetime.strptime("11:00", "%H:%M").time(),
                        key=f"end_time_{day_type}"
                    )
                
                with col_add:
                    st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
                    if st.button("Add Interval", key=f"add_interval_{day_type}"):
                        interval = f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
                        if interval not in st.session_state[time_intervals_key]:
                            st.session_state[time_intervals_key].append(interval)
                            st.rerun()
                
                # Display current intervals
                if st.session_state[time_intervals_key]:
                    st.markdown("**Current Time Intervals:**")
                    intervals_to_remove = []
                    
                    for i, interval in enumerate(st.session_state[time_intervals_key]):
                        col_interval, col_remove = st.columns([3, 1])
                        with col_interval:
                            st.markdown(f"• {interval}")
                        with col_remove:
                            if st.button("Remove", key=f"remove_{day_type}_{i}"):
                                intervals_to_remove.append(interval)
                    
                    # Remove intervals that were marked for removal
                    for interval in intervals_to_remove:
                        st.session_state[time_intervals_key].remove(interval)
                        st.rerun()
                    
                    # Convert intervals to time slots for compatibility
                    for interval in st.session_state[time_intervals_key]:
                        start_str, end_str = interval.split('-')
                        start_hour = int(start_str.split(':')[0])
                        start_min = int(start_str.split(':')[1])
                        end_hour = int(end_str.split(':')[0])
                        end_min = int(end_str.split(':')[1])
                        
                        # Generate 30-minute slots within the interval
                        current_hour = start_hour
                        current_min = start_min
                        
                        while (current_hour < end_hour) or (current_hour == end_hour and current_min < end_min):
                            day_time_slots.append(f"{current_hour:02d}:{current_min:02d}")
                            current_min += 30
                            if current_min >= 60:
                                current_min = 0
                                current_hour += 1
                else:
                    st.info(f"Add time intervals for {day_type.replace('_', ' ')}.")
            
            # Store the preferences for this day type
            all_preferences[day_type] = {
                'time_slots': day_time_slots,
                'time_intervals': st.session_state[time_intervals_key] if time_preference == "Custom Time Intervals" else [],
                'method': time_preference
            }
            
            # Add all time slots to the main list for validation
            time_slots.extend(day_time_slots)
            
            if len(day_types_to_configure) > 1:
                st.markdown("---")
        
        st.markdown("---")
        
        # Monitoring preferences
        st.markdown("### ⚙️ Monitoring Settings")
        
        col_settings1, col_settings2 = st.columns(2)
        
        with col_settings1:
            min_players = st.selectbox(
                "Minimum Available Spots",
                [1, 2, 3, 4],
                index=preferences.get('min_players', 1) - 1,
                help="Minimum number of spots needed for notification"
            )
        
        days_ahead = st.slider(
            "Days to Monitor Ahead",
            min_value=1,
            max_value=14,
            value=preferences.get('days_ahead', 4),
            help="How many days in advance to check for availability"
        )
        
        with col_settings2:
            # Removed notification frequency - not used anymore
            st.markdown("**Additional Settings**")
            st.info("Notifications are sent immediately when availability is found.")
        
        st.markdown("---")
        
        # Validation and save
        st.markdown("### 💾 Save Configuration")
        
        # Validate preferences
        validation_issues = []
        if not name:
            validation_issues.append("Enter your name")
        if not email:
            validation_issues.append("Enter your email")
        if not selected_courses:
            validation_issues.append("Select at least one golf course")
        
        # Validate time preferences using utility function
        time_validation_errors = validate_time_preferences({
            'time_preferences': all_preferences,
            'preference_type': day_type_preference
        })
        validation_issues.extend(time_validation_errors)
        
        is_valid = len(validation_issues) == 0
        
        if not is_valid:
            st.info(f"📝 To save your profile, please: {', '.join(validation_issues)}")
        
        col_save1, col_save2, col_save3 = st.columns(3)
        
        with col_save1:
            if st.button("💾 Save Profile", disabled=not is_valid, use_container_width=True):
                # Check if this is an existing user
                existing_prefs = app.load_preferences_from_api(email)
                is_existing_user = bool(existing_prefs)
                
                # Create preferences object with proper structure
                new_preferences = {
                    'name': name,
                    'email': email,
                    'selected_courses': selected_courses,
                    'time_preferences': all_preferences,
                    'preference_type': day_type_preference,
                    'min_players': min_players,
                    'days_ahead': days_ahead,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Save preferences
                success = app.save_preferences_to_api(new_preferences)
                
                if success:
                    st.session_state.user_preferences = new_preferences
                    st.session_state.current_user_email = email
                    
                    action = "updated" if is_existing_user else "created"
                    st.success(f"✅ Profile {action} successfully for {name}!")
                    
                    # Refresh system status
                    app.system_status = app._get_system_status()
                else:
                    st.error("❌ Failed to save profile. Please try again.")
        
        with col_save2:
            if st.button("🧪 Test Notification", disabled=not (name and email), use_container_width=True):
                app.send_test_notification(email, name)
        
        with col_save3:
            if st.button("🗑️ Clear Form", use_container_width=True):
                st.session_state.user_preferences = {}
                st.session_state.current_user_email = None
                st.rerun()
        
        # Immediate availability check section
        if name and email and selected_courses and time_slots:
            st.markdown("---")
            st.markdown("### ⚡ Immediate Availability Check")
            st.info("💻 **Note:** This feature requires your local computer to be running the golf monitor.")
            
            col_immediate1, col_immediate2 = st.columns(2)
            
            with col_immediate1:
                if st.button("⚡ Check Now", use_container_width=True, type="primary"):
                    # Trigger immediate check
                    with st.spinner("Checking availability... This may take 1-2 minutes."):
                        result = trigger_immediate_availability_check(email, new_preferences if 'new_preferences' in locals() else preferences)
                    
                    if result.get('success'):
                        st.success("✅ Immediate check started! Results will appear below.")
                        # Auto-refresh to show results
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to start check: {result.get('error', 'Unknown error')}")
            
            with col_immediate2:
                if st.button("🔄 Refresh Results", use_container_width=True):
                    st.rerun()
            
            # Show immediate check results
            show_immediate_check_results(email)
    
    with col2:
        # Summary panel
        st.markdown("### 📋 Configuration Summary")
        
        if name and email:
            st.markdown(f"**User:** {name}")
            st.markdown(f"**Email:** {email}")
        
        if selected_courses:
            st.markdown(f"**Courses:** {len(selected_courses)} selected")
            for course_name in selected_course_names[:3]:  # Show first 3
                st.markdown(f"• {course_name}")
            if len(selected_course_names) > 3:
                st.markdown(f"• ... and {len(selected_course_names) - 3} more")
        
        if time_slots:
            st.markdown(f"**Time Slots:** {len(time_slots)} selected")
            if len(time_slots) <= 6:
                for slot in time_slots:
                    st.markdown(f"• {slot}")
            else:
                for slot in time_slots[:3]:
                    st.markdown(f"• {slot}")
                st.markdown(f"• ... and {len(time_slots) - 3} more")
        
        if is_valid:
            st.markdown(f"**Monitoring:** {days_ahead} days ahead")
            st.markdown(f"**Min Players:** {min_players}")
            
            # Show time preferences summary
            if all_preferences:
                st.markdown(f"**Time Preferences:** {day_type_preference}")
                total_intervals = 0
                for day_type, prefs in all_preferences.items():
                    if prefs['time_intervals']:
                        total_intervals += len(prefs['time_intervals'])
                        day_label = day_type.replace('_', ' ').title()
                        st.markdown(f"• {day_label}: {len(prefs['time_intervals'])} intervals")
                
                if total_intervals == 0 and time_slots:
                    st.markdown(f"• Using preset ranges: {len(set(time_slots))} time slots")

def trigger_immediate_availability_check(user_email: str, preferences: Dict) -> Dict:
    """Trigger an immediate availability check via local API server"""
    LOCAL_API_URL = "http://localhost:5000"
    
    try:
        # First check if local server is running
        health_response = requests.get(f"{LOCAL_API_URL}/health", timeout=3)
        if health_response.status_code != 200:
            return {"success": False, "error": "Local golf monitor is not running"}
        
        # Trigger immediate check
        payload = {
            "user_email": user_email,
            "time_window": "06:00-21:00",  # Wide window for immediate checks
            "days": preferences.get('days_ahead', 4),
            "players": preferences.get('min_players', 1)
        }
        
        response = requests.post(f"{LOCAL_API_URL}/api/immediate-check", json=payload, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            return {"success": False, "error": "Check already in progress. Please wait."}
        else:
            return {"success": False, "error": f"Server error: {response.status_code}"}
            
    except requests.exceptions.ConnectionError:
        return {
            "success": False, 
            "error": "Cannot connect to local golf monitor. Make sure it's running with: python local_api_server.py"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def show_immediate_check_results(user_email: str):
    """Show results from the most recent immediate check"""
    LOCAL_API_URL = "http://localhost:5000"
    
    try:
        # Get check status
        status_response = requests.get(f"{LOCAL_API_URL}/api/check-status", timeout=3)
        if status_response.status_code != 200:
            return
        
        status_data = status_response.json()
        
        if status_data.get('check_in_progress'):
            st.info("⏳ Check in progress... Please wait 1-2 minutes and refresh.")
            return
        
        # Get last result
        result_response = requests.get(f"{LOCAL_API_URL}/api/check-result", timeout=3)
        if result_response.status_code != 200:
            st.info("📋 No recent check results available.")
            return
        
        result_data = result_response.json()
        
        # Check if result is for current user
        if result_data.get('user_email') != user_email:
            st.info("📋 No recent check results for your profile.")
            return
        
        # Display results
        st.markdown("#### 📈 Latest Availability Check Results")
        
        result_time = result_data.get('timestamp', '')
        if result_time:
            try:
                dt = datetime.fromisoformat(result_time.replace('Z', '+00:00'))
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                st.caption(f"Last checked: {time_str}")
            except:
                st.caption(f"Last checked: {result_time}")
        
        if result_data.get('success'):
            results = result_data.get('results', {})
            availability = results.get('availability', {})
            new_availability = results.get('new_availability', [])
            
            if availability:
                # Show availability by date
                dates_found = set()
                for key in availability.keys():
                    if '_' in key:
                        date_part = key.split('_')[-1]
                        dates_found.add(date_part)
                
                for date_str in sorted(dates_found):
                    st.markdown(f"**{date_str}:**")
                    
                    date_availability = {k: v for k, v in availability.items() if k.endswith(f"_{date_str}")}
                    
                    if any(date_availability.values()):
                        for state_key, times in date_availability.items():
                            if times:
                                course_name = state_key.replace(f"_{date_str}", "")
                                times_str = ", ".join([f"{t}({c})" for t, c in sorted(times.items())])
                                st.success(f"✅ {course_name}: {times_str}")
                    else:
                        st.info("🚫 No availability found for this date")
                
                # Show new availability if any
                if new_availability:
                    st.markdown("**🎆 New Availability (since last check):**")
                    for item in new_availability:
                        st.success(f"✨ {item}")
            else:
                st.info("🚫 No availability found matching your preferences.")
        else:
            error_msg = result_data.get('error', 'Unknown error')
            st.error(f"❌ Check failed: {error_msg}")
            
            # Show raw output if available for debugging
            if result_data.get('raw_output'):
                with st.expander("🔍 Debug Information"):
                    st.text(result_data['raw_output'])
    
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ Cannot connect to local golf monitor. Make sure it's running.")
    except Exception as e:
        st.error(f"❌ Error getting results: {e}")

if __name__ == "__main__":
    main()
