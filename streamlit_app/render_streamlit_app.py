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
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        padding: 2.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        position: relative;
        overflow: hidden;
    }
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, rgba(255,255,255,0.1) 0%, transparent 50%, rgba(255,255,255,0.1) 100%);
        animation: shimmer 3s infinite;
    }
    @keyframes shimmer {
        0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
        100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
    }
    .main-header h1 {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        position: relative;
        z-index: 1;
    }
    .main-header p {
        font-size: 1.2rem;
        margin-bottom: 0;
        opacity: 0.9;
        position: relative;
        z-index: 1;
    }
    .intro-section {
        background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c8 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        border-left: 5px solid #4CAF50;
    }
    .intro-step {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-top: 3px solid #4CAF50;
        margin-bottom: 1rem;
    }
    .hero-image {
        border-radius: 15px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.2);
        transition: transform 0.3s ease;
    }
    .hero-image:hover {
        transform: scale(1.02);
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
        """Get available golf courses - using static data for efficiency."""
        # Golf courses rarely change, so we keep them static for better performance
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
    
    # Enhanced Header with hero image
    col_header_text, col_header_image = st.columns([2, 1])
    
    with col_header_text:
        st.markdown("""
        <div class="main-header">
            <h1 style="margin-bottom: 0.5rem;">🏌️ Golf Availability Monitor</h1>
            <p style="margin-bottom: 0.5rem;">Smart tee time notifications with instant availability checking</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_header_image:
        try:
            # Display the golf image using proper Streamlit image parameters
            st.image(
                "assets/907d8ed5-d913-4739-8b1e-c66e7231793b.jpg",
                caption="Founder - Edevard Hvide",
                width=200,  # Smaller width to fit better on side
                use_container_width=False,  # Updated deprecated parameter
                clamp=False  # Don't clamp pixel values
            )
        except FileNotFoundError:
            # Fallback if image not found
            st.markdown("""
            <div style="background: #f0f0f0; padding: 2rem; border-radius: 10px; text-align: center;">
                <h3>🏌️</h3>
                <p>Golf Image</p>
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            # Other errors
            st.markdown("""
            <div style="background: #f0f0f0; padding: 2rem; border-radius: 10px; text-align: center;">
                <h3>🏌️</h3>
                <p>Golf Image</p>
                <small>Error loading image</small>
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
            pass
        
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
        
        # Smart availability check section - shows cached data instantly
        if name and email and selected_courses and time_slots:
            st.markdown("---")
            st.markdown("### 📊 Smart Availability Check")
            st.info("⚡ **Instant Results:** Shows latest cached data filtered for your preferences.")
            
            col_check1, col_check2 = st.columns(2)
            
            with col_check1:
                if st.button("📊 Check Now", use_container_width=True, type="primary"):
                    # Show filtered cached results instantly
                    st.session_state.show_smart_results = True
                    st.rerun()
            
            with col_check2:
                if st.button("🔄 Refresh", use_container_width=True):
                    st.rerun()
            
            # Show smart filtered results
            if st.session_state.get('show_smart_results', False):
                user_preferences = new_preferences if 'new_preferences' in locals() else preferences
                show_smart_availability_results(email, user_preferences, selected_courses)
    
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

def show_cached_availability_offline(user_email: str):
    """Show cached availability results when local computer is offline"""
    try:
        # Try to get cached results from API
        response = requests.get(f"{API_BASE_URL}/api/cached-availability", 
                               params={"user_email": user_email, "hours_limit": 48}, 
                               timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success") and data.get("cached"):
                st.markdown("---")
                st.markdown("### 📊 Latest Availability (Cached)")
                st.info(f"💾 {data.get('message', 'Showing cached results')}")
                
                availability = data.get("availability", {})
                new_availability = data.get("new_availability", [])
                
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
                        st.markdown("**🎆 Recent New Availability:**")
                        for item in new_availability:
                            st.success(f"✨ {item}")
                else:
                    st.info("🚫 No cached availability data found.")
                    
                # Show cache info
                with st.expander("📋 Cache Information"):
                    st.write(f"**Check Type:** {data.get('check_type', 'unknown')}")
                    st.write(f"**Total Courses:** {data.get('total_courses', 0)}")
                    st.write(f"**Total Slots:** {data.get('total_availability_slots', 0)}")
                    date_range = data.get('date_range', {})
                    st.write(f"**Date Range:** {date_range.get('start', 'unknown')} to {date_range.get('end', 'unknown')}")
            else:
                st.info("💾 No recent cached results available. Results will be cached when your local computer runs a check.")
        
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ Cannot connect to API to retrieve cached results.")
    except Exception as e:
        st.error(f"❌ Error retrieving cached results: {e}")

def filter_availability_for_user(availability_data: Dict, user_preferences: Dict, selected_courses: List[str], target_date: str) -> Dict:
    """Filter availability data based on user preferences and selected courses for a specific date"""
    try:
        from datetime import date
        from time_utils import get_time_slots_for_date
        
        # Parse target date string to date object
        target_date_obj = date.fromisoformat(target_date)
        
        # Get user's time preferences for this specific date
        user_time_slots = get_time_slots_for_date(user_preferences, target_date_obj)
        
        if not user_time_slots:
            return {}
        
        filtered_availability = {}
        
        # Look for availability data for the target date
        for state_key, times in availability_data.items():
            # Check if this state key is for the target date
            if not state_key.endswith(f"_{target_date}"):
                continue
                
            # Extract course name from state key (remove date suffix)
            course_name = state_key.replace(f"_{target_date}", "")
            
            # Check if this course is in user's selected courses
            if course_name not in selected_courses:
                continue
            
            # Filter time slots based on user preferences
            filtered_times = {}
            for time_slot, capacity in times.items():
                if time_slot in user_time_slots:
                    # Check minimum players requirement
                    min_players = user_preferences.get('min_players', 1)
                    if capacity >= min_players:
                        filtered_times[time_slot] = capacity
            
            if filtered_times:
                filtered_availability[state_key] = filtered_times
        
        return filtered_availability
        
    except Exception as e:
        logger.error(f"Error filtering availability for user: {e}")
        return {}

def show_smart_availability_results(user_email: str, user_preferences: Dict, selected_courses: List[str]):
    """Show cached availability results filtered for user's specific preferences"""
    try:
        # Get cached availability from API
        response = requests.get(f"{API_BASE_URL}/api/cached-availability", 
                               params={"hours_limit": 48}, timeout=5)
        
        if response.status_code != 200:
            st.error("❌ Cannot retrieve cached availability data.")
            return
        
        data = response.json()
        
        if not data.get("cached"):
            st.info(data.get("message", "💾 No recent cached results available. Data will be available after your local computer runs a check."))
            
            # Show instructions if available
            instructions = data.get("instructions", [])
            if instructions:
                with st.expander("💡 How to get cached data"):
                    for instruction in instructions:
                        st.write(instruction)
            return
        
        # Display header with cache info
        st.markdown("#### 📊 Smart Availability Results")
        
        cache_time = data.get('check_timestamp', '')
        if cache_time:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(cache_time.replace('Z', '+00:00'))
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                hours_ago = (datetime.now() - dt).total_seconds() / 3600
                
                if hours_ago < 1:
                    freshness = f"{int(hours_ago * 60)} minutes ago"
                else:
                    freshness = f"{hours_ago:.1f} hours ago"
                    
                st.caption(f"📅 Data from: {time_str} ({freshness})")
            except:
                st.caption(f"📅 Data from: {cache_time}")
        
        # Get availability data
        availability = data.get("availability", {})
        
        if not availability:
            st.info("🚫 No availability data in cache.")
            return
        
        # Get unique dates from the cached data
        dates_found = set()
        for key in availability.keys():
            if '_' in key:
                date_part = key.split('_')[-1]
                if len(date_part) == 10:  # YYYY-MM-DD format
                    dates_found.add(date_part)
        
        if not dates_found:
            st.info("🚫 No valid dates found in cached data.")
            return
        
        # Show results for each date with user filtering
        total_matches = 0
        
        for date_str in sorted(dates_found):
            # Filter availability for this user and date
            filtered_availability = filter_availability_for_user(
                availability, user_preferences, selected_courses, date_str
            )
            
            if filtered_availability:
                # Display date header
                try:
                    from datetime import datetime, date
                    date_obj = date.fromisoformat(date_str)
                    day_name = date_obj.strftime('%A')
                    
                    # Check if it's today, tomorrow, etc.
                    today = date.today()
                    days_diff = (date_obj - today).days
                    
                    if days_diff == 0:
                        date_display = f"Today ({day_name}, {date_str})"
                    elif days_diff == 1:
                        date_display = f"Tomorrow ({day_name}, {date_str})"
                    elif days_diff == -1:
                        date_display = f"Yesterday ({day_name}, {date_str})"
                    else:
                        date_display = f"{day_name}, {date_str}"
                        
                except:
                    date_display = date_str
                
                st.markdown(f"### 📅 {date_display}")
                
                # Group by course and display
                course_results = {}
                for state_key, times in filtered_availability.items():
                    course_name = state_key.replace(f"_{date_str}", "")
                    if course_name not in course_results:
                        course_results[course_name] = []
                    
                    for time_slot, capacity in sorted(times.items()):
                        course_results[course_name].append((time_slot, capacity))
                        total_matches += 1
                
                # Display results by course
                for course_name, time_slots in course_results.items():
                    # Get course display name
                    course_display = course_name.replace('_', ' ').title()
                    
                    times_str = ", ".join([f"{t} ({c} spots)" for t, c in time_slots])
                    st.success(f"⛳ **{course_display}**: {times_str}")
        
        # Summary
        if total_matches > 0:
            st.markdown("---")
            st.success(f"🎯 **Found {total_matches} available time slots** matching your preferences!")
            
            # Show filtering summary
            with st.expander("🔍 Filtering Details"):
                st.write(f"**Selected Courses:** {len(selected_courses)} courses")
                for course in selected_courses:
                    course_display = course.replace('_', ' ').title()
                    st.write(f"• {course_display}")
                
                st.write(f"**Time Preferences:** {user_preferences.get('preference_type', 'Same for all days')}")
                
                # Show time preference summary
                from time_utils import format_preferences_summary
                time_summary = format_preferences_summary(user_preferences)
                st.text(time_summary)
                
                st.write(f"**Minimum Players:** {user_preferences.get('min_players', 1)}")
                st.write(f"**Days Ahead:** {user_preferences.get('days_ahead', 4)}")
        else:
            st.info("🚫 No availability found matching your specific preferences.")
            st.markdown("**Your filters:**")
            st.write(f"• **Courses:** {', '.join([c.replace('_', ' ').title() for c in selected_courses])}")
            st.write(f"• **Time Preferences:** {user_preferences.get('preference_type', 'Same for all days')}")
            st.write(f"• **Minimum Players:** {user_preferences.get('min_players', 1)}")
            
            with st.expander("💡 Tips to find more availability"):
                st.write("• Try selecting more golf courses")
                st.write("• Expand your preferred time ranges")
                st.write("• Check if your weekday/weekend preferences are too restrictive")
                st.write("• Reduce minimum player requirements if possible")
    
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API to retrieve cached results.")
    except Exception as e:
        st.error(f"❌ Error displaying smart results: {e}")
        logger.error(f"Smart results error: {e}")

if __name__ == "__main__":
    main()