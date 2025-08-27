#!/usr/bin/env python3
"""
Enhanced Streamlit Frontend for Golf Availability Monitor

This provides a modern, user-friendly interface for configuring golf monitoring preferences
with robust API integration and error handling.
"""

import streamlit as st
import requests
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging

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
            st.sidebar.markdown("#### System Info")
            st.sidebar.metric("Active Users", self.system_status.get("user_count", 0))
            st.sidebar.metric("Backups Available", self.system_status.get("backup_count", 0))
            
            golf_status = "✅ Available" if self.system_status.get("golf_system_available") else "🔶 Demo Mode"
            st.sidebar.markdown(f"**Golf System:** {golf_status}")
    
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
                
                # Handle both old and new format
                if isinstance(data, dict):
                    if "users" in data:
                        return data["users"].get(email, {})
                    else:
                        return data.get(email, {})
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
            existing_data = {}
            if FALLBACK_PREFERENCES_FILE.exists():
                with open(FALLBACK_PREFERENCES_FILE, 'r') as f:
                    existing_data = json.load(f)
            
            # Handle both old and new format
            if "users" not in existing_data and existing_data:
                # Old format - convert
                users_data = existing_data
            else:
                users_data = existing_data.get("users", {})
            
            # Add new preferences
            users_data[preferences['email']] = preferences
            
            # Save in new format
            new_data = {
                "_metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "version": "2.0",
                    "source": "streamlit_fallback"
                },
                "users": users_data
            }
            
            FALLBACK_PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(FALLBACK_PREFERENCES_FILE, 'w') as f:
                json.dump(new_data, f, indent=2)
        
        return True
    except Exception as e:
            logger.error(f"Fallback save failed: {e}")
        return False

    def get_available_courses(self) -> List[Dict]:
        """Get list of available golf courses."""
        try:
            if self.api_available:
                response = requests.get(f"{API_BASE_URL}/api/courses", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    courses = data.get("courses", [])
                    # Ensure consistent format
                    return [
                        course if isinstance(course, dict) 
                        else {"id": course, "name": course, "location": "Unknown"}
                        for course in courses
                    ]
        except Exception as e:
            logger.warning(f"Failed to get courses from API: {e}")
        
        # Fallback courses
        return [
            {"id": "oslo_golfklubb", "name": "Oslo Golfklubb", "location": "Oslo"},
            {"id": "miklagard_gk", "name": "Miklagard Golf Club", "location": "Bærum"},
            {"id": "bogstad_golfklubb", "name": "Bogstad Golfklubb", "location": "Oslo"},
            {"id": "drammen_golfklubb", "name": "Drammen Golfklubb", "location": "Drammen"},
            {"id": "holmestrand_golfklubb", "name": "Holmestrand Golfklubb", "location": "Holmestrand"},
            {"id": "kongsberg_golfklubb", "name": "Kongsberg Golfklubb", "location": "Kongsberg"}
        ]
    
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
                else:
                    return list(data.keys())
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
        course_options = {course["name"]: course["id"] for course in available_courses}
        
        selected_course_names = st.multiselect(
            "Select Golf Courses",
            options=list(course_options.keys()),
            default=[
                name for name, course_id in course_options.items()
                if course_id in preferences.get('selected_courses', [])
            ],
            help="Choose the golf courses you want to monitor"
        )
        
        selected_courses = [course_options[name] for name in selected_course_names]
        
        st.markdown("---")
        
        # Time Preferences
        st.markdown("### ⏰ Time Preferences")
        
        time_preference = st.radio(
            "Time Selection Method",
            ["Preset Ranges", "Custom Time Slots"],
            help="Choose how you want to specify your preferred times"
        )
        
        time_slots = []
        
        if time_preference == "Preset Ranges":
            preset_ranges = st.multiselect(
                "Select Time Ranges",
                ["Morning (07:00-11:00)", "Afternoon (11:00-15:00)", "Evening (15:00-19:00)"],
                help="Select your preferred time ranges"
            )
            
            # Convert preset ranges to time slots
            for preset in preset_ranges:
                if "Morning" in preset:
                    time_slots.extend([f"{h:02d}:00" for h in range(7, 11)])
                    time_slots.extend([f"{h:02d}:30" for h in range(7, 11)])
                elif "Afternoon" in preset:
                    time_slots.extend([f"{h:02d}:00" for h in range(11, 15)])
                    time_slots.extend([f"{h:02d}:30" for h in range(11, 15)])
                elif "Evening" in preset:
                    time_slots.extend([f"{h:02d}:00" for h in range(15, 19)])
                    time_slots.extend([f"{h:02d}:30" for h in range(15, 19)])
        
        else:
            available_slots = app.generate_time_slots()
            time_slots = st.multiselect(
                "Select Specific Time Slots",
                available_slots,
                default=preferences.get('time_slots', []),
                help="Choose specific time slots you prefer"
        )
        
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
        notification_frequency = st.selectbox(
            "Notification Frequency",
                ["immediate", "hourly", "daily"],
                index=["immediate", "hourly", "daily"].index(
                    preferences.get('notification_frequency', 'immediate')
                ),
                help="How often to send notifications"
            )
        
        st.markdown("---")
        
        # Validation and save
        st.markdown("### 💾 Save Configuration")
        
        is_valid = bool(name and email and selected_courses and time_slots)
        
        if not is_valid:
            validation_issues = []
            if not name:
                validation_issues.append("Enter your name")
            if not email:
                validation_issues.append("Enter your email")
            if not selected_courses:
                validation_issues.append("Select at least one golf course")
            if not time_slots:
                validation_issues.append("Select at least one time slot")
            
            st.info(f"📝 To save your profile, please: {', '.join(validation_issues)}")
        
        col_save1, col_save2, col_save3 = st.columns(3)
        
        with col_save1:
        if st.button("💾 Save Profile", disabled=not is_valid, use_container_width=True):
            # Check if this is an existing user
                existing_prefs = app.load_preferences_from_api(email)
                is_existing_user = bool(existing_prefs)
                
                # Create preferences object
            new_preferences = {
                'name': name,
                'email': email,
                'selected_courses': selected_courses,
                    'time_slots': time_slots,
                'min_players': min_players,
                'days_ahead': days_ahead,
                'notification_frequency': notification_frequency,
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
            st.markdown(f"**Frequency:** {notification_frequency}")
            st.markdown(f"**Min Players:** {min_players}")
        
        # Show API status
        st.markdown("---")
        st.markdown("### 🔧 System Status")
        
        if app.api_available:
            st.success("🟢 API Server Online")
            if app.system_status.get("golf_system_available"):
                st.success("🟢 Golf System Available")
            else:
                st.warning("🔶 Golf System in Demo Mode")
            else:
            st.warning("🟡 API Offline - Local Mode")
            st.info("💡 Data will be saved locally")

if __name__ == "__main__":
    main()
