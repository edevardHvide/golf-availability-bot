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
    
    # Test notification function removed
    pass
    
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
    
    # Show enhanced header with hero image
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
                "Number of Players",
                [1, 2, 3, 4],
                index=preferences.get('min_players', 1) - 1,
                help="Number of players in your group"
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
            pass
        
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
            # Availability check button - always available
            if st.button("📊 Check Now", use_container_width=True, type="primary"):
                st.session_state.show_smart_results = True
                st.rerun()
        
        with col_save3:
            if st.button("🗑️ Clear Form", use_container_width=True):
                st.session_state.user_preferences = {}
                st.session_state.current_user_email = None
                st.rerun()
        
        # Availability check section - always available
        st.markdown("---")
        st.markdown("### 📊 Availability Check")
        st.info("⚡ **Instant Results:** Shows latest cached data filtered for your preferences.")
        
        col_check1, col_check2 = st.columns(2)
        
        with col_check1:
            if st.button("🌐 Get All Times", use_container_width=True, type="secondary"):
                # Show all times from database
                st.session_state.show_all_times = True
                st.rerun()
        
        with col_check2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        # Show smart filtered results
        if st.session_state.get('show_smart_results', False):
            user_preferences = new_preferences if 'new_preferences' in locals() else preferences
            show_smart_availability_results(email, user_preferences, selected_courses)
        
        # Show all times results
        if st.session_state.get('show_all_times', False):
            show_all_times_from_database()
    
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

def filter_availability_for_user(availability_data: Dict, user_preferences: Dict, selected_courses: List[str], target_date: str) -> Dict:
    """Filter availability data based on user's specific preferences"""
    try:
        from datetime import date
        from time_utils import get_time_slots_for_date
        
        # Parse target date
        target_date_obj = date.fromisoformat(target_date)
        
        # Get user's time slots for this specific date (respects weekday/weekend preferences)
        user_time_slots = get_time_slots_for_date(user_preferences, target_date_obj)
        
        filtered_availability = {}
        
        # Filter by selected courses and time preferences
        for state_key, times in availability_data.items():
            if '_' in state_key:
                course_name = state_key.split('_')[0]
                date_part = state_key.split('_')[-1]
                
                # Check if this course is in user's selected courses
                if course_name in selected_courses and date_part == target_date:
                    # Filter times based on user preferences
                    filtered_times = {}
                    for time_slot, capacity in times.items():
                        if time_slot in user_time_slots:
                            filtered_times[time_slot] = capacity
                    
                    if filtered_times:
                        filtered_availability[state_key] = filtered_times
        
        return filtered_availability
    
    except Exception as e:
        logger.warning(f"Error filtering availability for user: {e}")
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

def show_all_times_from_database():
    """Show all available times from the latest database entry."""
    try:
        # Get all times from API
        response = requests.get(f"{API_BASE_URL}/api/all-times", timeout=10)
        
        if response.status_code != 200:
            st.error("❌ Cannot retrieve all times data from database.")
            return
        
        data = response.json()
        
        if not data.get("cached"):
            st.info(data.get("message", "💾 No cached results available. Run the golf monitor to collect data."))
            return
        
        # Display header with comprehensive info
        st.markdown("#### 🌐 All Available Times (Database)")
        
        # Show cache info
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
        
        # Show summary statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Courses", data.get('total_courses', 0))
        with col2:
            st.metric("Courses with Data", data.get('courses_with_data', 0))
        with col3:
            st.metric("Total Time Slots", data.get('total_availability_slots', 0))
        with col4:
            st.metric("Dates Found", len(data.get('dates_found', [])))
        
        # Get availability data
        availability = data.get("availability", {})
        
        if not availability:
            st.info("🚫 No availability data in database.")
            return
        
        # Get unique dates from the data
        dates_found = data.get('dates_found', [])
        
        if not dates_found:
            st.info("🚫 No valid dates found in database.")
            return
        
        # Show results for each date
        for date_str in dates_found:
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
            for state_key, times in availability.items():
                if state_key.endswith(f"_{date_str}"):
                    course_name = state_key.replace(f"_{date_str}", "")
                    if course_name not in course_results:
                        course_results[course_name] = []
                    
                    for time_slot, capacity in sorted(times.items()):
                        course_results[course_name].append(f"{time_slot} ({capacity} spots)")
            
            # Display course results
            if course_results:
                for course_name, time_slots in sorted(course_results.items()):
                    st.markdown(f"**🏌️ {course_name}:** {', '.join(time_slots)}")
            else:
                st.info(f"No availability data for {date_str}")
        
        st.success(f"✅ Retrieved {len(availability)} course results with {data.get('total_availability_slots', 0)} total time slots")
            
    except Exception as e:
        st.error(f"❌ Error displaying all times: {e}")
        logger.error(f"Error in show_all_times_from_database: {e}")

if __name__ == "__main__":
    main()
