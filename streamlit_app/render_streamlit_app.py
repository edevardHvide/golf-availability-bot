"""
Dedicated Streamlit App for Render Deployment with PostgreSQL Support

This Streamlit app connects to the PostgreSQL-enhanced API service via subdomain.
Optimized for Render's two-service architecture.
"""

import streamlit as st
import requests
import json
import os
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
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
SERVICE_MODE = "render_ui_service"

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

    .status-healthy { background: #d4edda; color: #155724; padding: 0.5rem; border-radius: 5px; }
    .status-warning { background: #fff3cd; color: #856404; padding: 0.5rem; border-radius: 5px; }
    .status-error { background: #f8d7da; color: #721c24; padding: 0.5rem; border-radius: 5px; }
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
</style>
""", unsafe_allow_html=True)

class GolfMonitorUI:
    """Main UI class for the Golf Availability Monitor Render deployment."""
    
    def __init__(self):
        self.api_available = self._check_api_connection()
        self.system_status = self._get_system_status()
        
    def _check_api_connection(self) -> bool:
        """Check if the API service is available."""
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"API connection failed: {e}")
            return False
    
    def _get_system_status(self) -> Dict:
        """Get system status from API service."""
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
            "version": "unknown"
        }
    

    
    def show_connection_status(self):
        """Show API connection status in sidebar."""
        st.sidebar.markdown("### 🔗 Connection Status")
        
        if self.api_available:
            st.sidebar.markdown(
                '<div class="status-healthy">🟢 API Connected</div>',
                unsafe_allow_html=True
            )
            
            if self.system_status:
                st.sidebar.metric("Active Users", self.system_status.get("user_count", 0))
                
                golf_status = "✅ Available" if self.system_status.get("golf_system_available") else "🔶 Demo Mode"
                st.sidebar.markdown(f"**Golf System:** {golf_status}")
        else:
            st.sidebar.markdown(
                '<div class="status-error">🔴 API Unavailable</div>',
                unsafe_allow_html=True
            )
            st.sidebar.error("Cannot connect to API service. Please check the API service status.")
    
    def show_service_info(self):
        """Show service information at bottom of sidebar."""
        st.sidebar.markdown("### 🔧 Service Info")
        
        if self.api_available:
            st.sidebar.success("🟢 Two-Service Architecture")
            st.sidebar.markdown("**UI Service:** Running")
            st.sidebar.markdown("**API Service:** Connected")
            st.sidebar.markdown(f"**API URL:** `{API_BASE_URL}`")
        else:
            st.sidebar.warning("🟡 UI Service Only")
            st.sidebar.markdown("**UI Service:** Running")
            st.sidebar.markdown("**API Service:** Disconnected")
        
        if self.system_status:
            version = self.system_status.get("version", "unknown")
            st.sidebar.markdown(f"**Version:** {version}")
    
    def load_user_preferences(self, email: str) -> Dict:
        """Load user preferences from API service."""
        try:
            response = requests.get(f"{API_BASE_URL}/api/preferences/{email}", timeout=5)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {}
            else:
                st.error(f"API Error: {response.status_code}")
                return {}
        except Exception as e:
            st.error(f"Failed to load preferences: {e}")
            return {}
    
    def save_user_preferences(self, preferences: Dict) -> bool:
        """Save user preferences to API service."""
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/preferences",
                json=preferences,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return True, data.get("message", "Saved successfully")
            else:
                error_detail = response.json().get("detail", "Unknown error") if response.content else "Unknown error"
                return False, f"API Error: {error_detail}"
        except Exception as e:
            return False, f"Connection error: {e}"
    
    def get_available_courses(self) -> List[Dict]:
        """Get available courses from API service."""
        try:
            response = requests.get(f"{API_BASE_URL}/api/courses", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("courses", [])
        except Exception as e:
            logger.warning(f"Failed to get courses from API: {e}")
        
        # Use local golf course data as fallback
        return get_available_courses()
    
    def get_existing_users(self) -> List[str]:
        """Get list of existing user emails."""
        try:
            response = requests.get(f"{API_BASE_URL}/api/preferences", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return list(data.get("preferences", {}).keys())
        except Exception:
            pass
        return []
    
    def send_test_notification(self, email: str, name: str) -> bool:
        """Send test notification via API."""
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/test-notification",
                json={"email": email, "name": name},
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("type") == "demo_mode":
                    st.info("📧 Demo Mode: Test notification simulated")
                else:
                    st.success("📧 Test notification sent!")
                return True
            else:
                st.error(f"Failed to send notification: {response.status_code}")
        except Exception as e:
            st.error(f"Error sending notification: {e}")
        return False
    
    def generate_time_slots(self) -> List[str]:
        """Generate time slots for selection."""
        slots = []
        for hour in range(6, 21):  # 6 AM to 8 PM
            for minute in [0, 30]:
                if hour == 20 and minute == 30:  # Don't go past 8:00 PM
                    break
                slots.append(f"{hour:02d}:{minute:02d}")
        return slots
    
    def show_profile_management(self):
        """Show profile loading/management section."""
        st.sidebar.markdown("### 👤 Profile Management")
        
        if not self.api_available:
            st.sidebar.error("Profile management requires API connection")
            return
        
        existing_users = self.get_existing_users()
        
        if existing_users:
            selected_user = st.sidebar.selectbox(
                "Quick Load Profile",
                [""] + existing_users,
                help="Select an existing profile to load"
            )
            
            if selected_user and st.sidebar.button("🔄 Load Profile"):
                preferences = self.load_user_preferences(selected_user)
                if preferences:
                    st.session_state.user_preferences = preferences
                    st.session_state.current_user_email = selected_user
                    st.success(f"✅ Loaded profile for {preferences.get('name', selected_user)}")
                    st.rerun()
        
        # Manual email input
        st.sidebar.markdown("---")
        email_to_load = st.sidebar.text_input(
            "Load by Email",
            placeholder="user@example.com"
        )
        
        if email_to_load and st.sidebar.button("📥 Load by Email"):
            preferences = self.load_user_preferences(email_to_load)
            if preferences:
                st.session_state.user_preferences = preferences
                st.session_state.current_user_email = email_to_load
                st.success(f"✅ Loaded profile for {preferences.get('name', email_to_load)}")
                st.rerun()
            else:
                st.warning(f"❌ No profile found for {email_to_load}")
        
        # Show current profile
        if st.session_state.get('current_user_email'):
            st.sidebar.markdown("#### Current Profile")
            current_prefs = st.session_state.get('user_preferences', {})
            st.sidebar.markdown(f"""
            <div style="background: #e3f2fd; padding: 1rem; border-radius: 8px;">
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
    
    # Initialize the UI
    ui = GolfMonitorUI()
    

    
    # Initialize session state
    if 'user_preferences' not in st.session_state:
        st.session_state.user_preferences = {}
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏌️ Golf Availability Monitor</h1>
        <p>Configure your personalized golf tee time notifications</p>
        <small>Golf Availability Monitor • Streamlit Interface</small>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    ui.show_connection_status()
    ui.show_profile_management()
    
    # Move service info to bottom of sidebar
    st.sidebar.markdown("---")
    ui.show_service_info()
    
    # Main content
    if not ui.api_available:
        st.error("🔴 **API Service Unavailable**")
        st.markdown("""
        The Golf Availability Monitor requires both services to be running:
        
        1. **API Service** (currently unavailable)
        2. **UI Service** (this service - running)
        
        Please ensure the API service is deployed and accessible.
        """)
        
        with st.expander("🔧 Troubleshooting"):
            st.markdown(f"""
            **Expected API URL:** `{API_BASE_URL}`
            
            **Common Issues:**
            - API service is still starting up (wait a few minutes)
            - API service deployment failed (check Render logs)
            - Incorrect API_BASE_URL environment variable
            - Network connectivity issues
            
            **Next Steps:**
            1. Check the API service status in Render dashboard
            2. Verify API service logs for errors
            3. Test API directly: {API_BASE_URL}/health
            """)
        
        return
    
    # Load current preferences
    preferences = st.session_state.get('user_preferences', {})
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 👤 User Information")
        
        name = st.text_input(
            "Full Name",
            value=preferences.get('name', ''),
            placeholder="Enter your full name"
        )
        
        email = st.text_input(
            "Email Address",
            value=preferences.get('email', ''),
            placeholder="your.email@example.com"
        )
        
        st.markdown("---")
        
        # Golf Course Selection
        st.markdown("### 🏌️ Golf Course Selection")
        
        available_courses = ui.get_available_courses()
        course_options = {course["name"]: course["key"] for course in available_courses}
        
        selected_course_names = st.multiselect(
            "Select Golf Courses",
            options=list(course_options.keys()),
            default=[
                name for name, course_key in course_options.items()
                if course_key in preferences.get('selected_courses', [])
            ]
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
                key=f"time_pref_{day_type}"
            )
            
            day_time_slots = []
            
            if time_preference == "Preset Ranges":
                preset_ranges = st.multiselect(
                    "Select Time Ranges",
                    ["Morning (06:00-12:00)", "Afternoon (12:00-17:00)", "Evening (17:00-20:00)"],
                    key=f"preset_{day_type}"
                )
                
                # Convert preset ranges to time slots
                for preset in preset_ranges:
                    if "Morning" in preset:
                        day_time_slots.extend([f"{h:02d}:00" for h in range(6, 12)])
                        day_time_slots.extend([f"{h:02d}:30" for h in range(6, 12)])
                    elif "Afternoon" in preset:
                        day_time_slots.extend([f"{h:02d}:00" for h in range(12, 17)])
                        day_time_slots.extend([f"{h:02d}:30" for h in range(12, 17)])
                    elif "Evening" in preset:
                        day_time_slots.extend([f"{h:02d}:00" for h in range(17, 21)])
                        day_time_slots.extend([f"{h:02d}:30" for h in range(17, 20)])
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
        
        # Monitoring Settings
        st.markdown("### ⚙️ Monitoring Settings")
        
        col_settings1, col_settings2 = st.columns(2)
        
        with col_settings1:
            min_players = st.selectbox(
                "Minimum Available Spots",
                [1, 2, 3, 4],
                index=preferences.get('min_players', 1) - 1
            )
            
            days_ahead = st.slider(
                "Days to Monitor Ahead",
                min_value=1,
                max_value=14,
                value=preferences.get('days_ahead', 4)
            )
        
        with col_settings2:
            # Removed notification frequency - not used anymore
            st.markdown("**Additional Settings**")
            st.info("Notifications are sent immediately when availability is found.")
        
        st.markdown("---")
        
        # Save section
        st.markdown("### 💾 Save Configuration")
        
        # Validate preferences
        validation_issues = []
        if not name:
            validation_issues.append("Enter your name")
        if not email:
            validation_issues.append("Enter your email")
        if not selected_courses:
            validation_issues.append("Select at least one course")
        
        # Validate time preferences using utility function
        time_validation_errors = validate_time_preferences({
            'time_preferences': all_preferences,
            'preference_type': day_type_preference
        })
        validation_issues.extend(time_validation_errors)
        
        is_valid = len(validation_issues) == 0
        
        if not is_valid:
            st.info(f"📝 Complete: {', '.join(validation_issues)}")
        
        col_save1, col_save2 = st.columns(2)
        
        with col_save1:
            if st.button("💾 Save Profile", disabled=not is_valid, use_container_width=True):
                # Prepare preferences with proper structure
                new_preferences = {
                    'name': name,
                    'email': email,
                    'selected_courses': selected_courses,
                    'time_preferences': all_preferences,
                    'preference_type': day_type_preference,
                    'min_players': min_players,
                    'days_ahead': days_ahead
                }
                
                # Save via API
                success, message = ui.save_user_preferences(new_preferences)
                
                if success:
                    st.session_state.user_preferences = new_preferences
                    st.session_state.current_user_email = email
                    st.success(f"✅ {message}")
                    
                    # Refresh system status
                    ui.system_status = ui._get_system_status()
                else:
                    st.error(f"❌ {message}")
        
        with col_save2:
            if st.button("🧪 Test Notification", disabled=not (name and email), use_container_width=True):
                ui.send_test_notification(email, name)
    
    with col2:
        # Summary panel
        st.markdown("### 📋 Configuration Summary")
        
        if name and email:
            st.markdown(f"**User:** {name}")
            st.markdown(f"**Email:** {email}")
        
        if selected_courses:
            st.markdown(f"**Courses:** {len(selected_courses)} selected")
            for course_name in selected_course_names[:3]:
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
        


if __name__ == "__main__":
    main()
