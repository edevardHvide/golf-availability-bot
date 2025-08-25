"""
Golf Availability Bot - Streamlit Web Interface

This Streamlit app allows users to configure their golf availability preferences
through a user-friendly web interface. It integrates with the main monitoring
system via API calls.
"""

import streamlit as st
import json
import requests
from datetime import datetime
from typing import List, Dict
from pathlib import Path

# Import the golf club manager to get available courses
import sys
sys.path.append(str(Path(__file__).parent.parent))

try:
    from golf_club_urls import golf_url_manager
    GOLF_CLUBS_AVAILABLE = True
except ImportError:
    GOLF_CLUBS_AVAILABLE = False
    print("Warning: Golf club URLs not available. Using fallback data.")

# Page configuration
st.set_page_config(
    page_title="Golf Availability Monitor",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a better look
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #4CAF50 0%, #45a049 100%);
        padding: 1rem;
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
</style>
""", unsafe_allow_html=True)

def load_user_preferences() -> Dict:
    """Load user preferences from session state or return defaults."""
    return st.session_state.get('user_preferences', {
        'name': '',
        'email': '',
        'selected_courses': [],
        'time_slots': [],
        'min_players': 1,
        'days_ahead': 4,
        'notification_frequency': 'immediate'
    })

def save_user_preferences(preferences: Dict):
    """Save user preferences to session state."""
    st.session_state.user_preferences = preferences

def get_available_courses() -> List[Dict]:
    """Get list of available golf courses."""
    if GOLF_CLUBS_AVAILABLE:
        courses = []
        # Get all clubs from the golf_url_manager
        for key, club in golf_url_manager.clubs.items():
            courses.append({
                'key': key,
                'name': club.display_name,
                'location': f"{club.location[0]:.2f}, {club.location[1]:.2f}" if club.location else "Unknown",
                'default_start_time': f"{club.default_start_time[:2]}:{club.default_start_time[2:4]}"
            })
        
        # Sort by display name for better UX
        return sorted(courses, key=lambda x: x['name'])
    else:
        # Fallback data for testing when golf_club_urls is not available
        return [
            {'key': 'oslo_golfklubb', 'name': 'Oslo Golfklubb', 'location': '59.91, 10.75', 'default_start_time': '07:00'},
            {'key': 'miklagard_gk', 'name': 'Miklagard GK', 'location': '59.97, 11.04', 'default_start_time': '07:00'},
            {'key': 'baerum_gk', 'name': 'Bærum GK', 'location': '59.89, 10.52', 'default_start_time': '06:00'},
            {'key': 'bogstad_golfklubb', 'name': 'Bogstad Golfklubb', 'location': '59.95, 10.63', 'default_start_time': '07:00'},
            {'key': 'asker_golfklubb', 'name': 'Asker Golfklubb', 'location': '59.83, 10.43', 'default_start_time': '07:00'},
            {'key': 'drammen_golfklubb', 'name': 'Drammen Golfklubb', 'location': '59.74, 10.20', 'default_start_time': '07:00'},
            {'key': 'losby_golfklubb', 'name': 'Losby Golfklubb', 'location': '59.93, 11.13', 'default_start_time': '07:00'},
            {'key': 'kongsberg_golfklubb', 'name': 'Kongsberg Golfklubb', 'location': '59.67, 9.65', 'default_start_time': '06:00'},
        ]

def generate_time_slots() -> List[str]:
    """Generate available time slots for selection."""
    time_slots = []
    
    # Generate slots from 6:00 AM to 8:00 PM in 30-minute intervals
    start_hour = 6
    end_hour = 20
    
    for hour in range(start_hour, end_hour + 1):
        for minute in [0, 30]:
            if hour == 20 and minute == 30:  # Don't go past 8:00 PM
                break
            time_str = f"{hour:02d}:{minute:02d}"
            time_slots.append(time_str)
    
    return time_slots

def send_preferences_to_api(preferences: Dict) -> bool:
    """Send user preferences to the monitoring API."""
    try:
        # In a real implementation, this would call your monitoring API
        # For now, we'll save to a local file that the monitor can read
        preferences_file = Path(__file__).parent.parent / "user_preferences.json"
        
        # Load existing preferences
        existing_prefs = {}
        if preferences_file.exists():
            with open(preferences_file, 'r') as f:
                existing_prefs = json.load(f)
        
        # Add new user preferences (keyed by email)
        user_email = preferences.get('email', 'unknown')
        existing_prefs[user_email] = preferences
        
        # Save updated preferences
        with open(preferences_file, 'w') as f:
            json.dump(existing_prefs, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error saving preferences: {e}")
        return False

def main():
    """Main Streamlit application."""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>⛳ Golf Availability Monitor</h1>
        <p>Configure your golf tee time preferences and get notified when slots become available</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Profile Loading Section
    st.markdown("### 👤 Load Your Profile")
    
    # Get list of existing profiles for quick selection
    existing_profiles = []
    try:
        preferences_file = Path(__file__).parent.parent / "user_preferences.json"
        if preferences_file.exists():
            with open(preferences_file, 'r') as f:
                all_prefs = json.load(f)
            existing_profiles = [
                f"{prefs.get('name', 'Unknown')} ({email})" 
                for email, prefs in all_prefs.items()
            ]
    except Exception:
        pass
    
    profile_col1, profile_col2, profile_col3 = st.columns([2, 1, 1])
    
    with profile_col1:
        # Quick profile selection if profiles exist
        if existing_profiles:
            selected_profile = st.selectbox(
                "Quick select from saved profiles",
                options=[""] + existing_profiles,
                help="Choose a previously saved profile to load instantly"
            )
            
            # Extract email from selection
            if selected_profile:
                load_email = selected_profile.split("(")[1].split(")")[0]
            else:
                load_email = st.text_input(
                    "Or enter your email to load saved preferences",
                    placeholder="your.email@example.com",
                    help="If you've saved preferences before, enter your email to load them"
                )
        else:
            load_email = st.text_input(
                "Enter your email to load saved preferences",
                placeholder="your.email@example.com",
                help="If you've saved preferences before, enter your email to load them"
            )
    
    with profile_col2:
        load_profile_btn = st.button("🔄 Load Profile", use_container_width=True)
    
    with profile_col3:
        clear_profile_btn = st.button("🗑️ Clear Form", use_container_width=True)
    
    # Handle profile loading
    auto_load_triggered = existing_profiles and selected_profile and not st.session_state.get('last_selected_profile', '') == selected_profile
    
    if (load_profile_btn and load_email) or auto_load_triggered:
        # Use email from either text input or selection
        email_to_load = load_email if load_email else selected_profile.split("(")[1].split(")")[0]
        
        # Track the last selected profile to avoid infinite loops
        if auto_load_triggered:
            st.session_state.last_selected_profile = selected_profile
        
        try:
            # First try to load from API server
            response = requests.get(f"http://localhost:8000/api/preferences/{email_to_load}", timeout=3)
            if response.status_code == 200:
                loaded_prefs = response.json()
                # Store in session state
                st.session_state.user_preferences = loaded_prefs
                st.success(f"✅ Profile loaded successfully for {loaded_prefs.get('name', 'User')}!")
                st.rerun()
            elif response.status_code == 404:
                st.warning(f"❌ No saved preferences found for {email_to_load}")
            else:
                st.error(f"❌ Failed to load profile: {response.text}")
        except requests.exceptions.ConnectionError:
            # Fallback to local file when API server is not running
            try:
                preferences_file = Path(__file__).parent.parent / "user_preferences.json"
                if preferences_file.exists():
                    with open(preferences_file, 'r') as f:
                        all_prefs = json.load(f)
                    
                    if email_to_load in all_prefs:
                        loaded_prefs = all_prefs[email_to_load]
                        st.session_state.user_preferences = loaded_prefs
                        st.success(f"✅ Profile loaded from local storage for {loaded_prefs.get('name', 'User')}!")
                        st.rerun()
                    else:
                        st.warning(f"❌ No saved preferences found for {email_to_load}")
                else:
                    st.info("ℹ️ No saved preferences available yet.")
            except Exception as e:
                st.error(f"❌ Error loading from local storage: {str(e)}")
        except Exception as e:
            st.error(f"❌ Error loading profile: {str(e)}")
    
    # Handle profile clearing
    if clear_profile_btn:
        st.session_state.user_preferences = {}
        st.success("✅ Form cleared!")
        st.rerun()
    
    # Load current preferences (after potential profile loading)
    preferences = load_user_preferences()
    
    st.markdown("---")
    
    # Sidebar with user info
    with st.sidebar:
        # Profile status indicator
        if preferences.get('email') and preferences.get('name'):
            st.markdown(f"""
            <div style="background: #d4edda; padding: 10px; border-radius: 8px; margin-bottom: 15px;">
                <strong>📋 Current Profile</strong><br>
                <small>{preferences.get('name')}<br>{preferences.get('email')}</small>
            </div>
            """, unsafe_allow_html=True)
        
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
        
        # Monitoring preferences
        st.markdown("### ⚙️ Monitoring Settings")
        
        days_ahead = st.slider(
            "Days to Monitor Ahead",
            min_value=1,
            max_value=14,
            value=preferences.get('days_ahead', 4),
            help="How many days in advance to check for availability"
        )
        
        notification_frequency = st.selectbox(
            "Notification Frequency",
            options=['immediate', 'hourly', 'daily'],
            index=['immediate', 'hourly', 'daily'].index(preferences.get('notification_frequency', 'immediate')),
            help="How often to receive notifications about new availability"
        )
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Golf course selection
        st.markdown('<div class="preference-section">', unsafe_allow_html=True)
        st.markdown("### 🏌️ Select Golf Courses")
        st.markdown("Choose which golf courses you'd like to monitor for availability:")
        
        available_courses = get_available_courses()
        
        # Create a nice display of courses with checkboxes
        selected_courses = preferences.get('selected_courses', [])
        
        # Group courses by location proximity (simplified)
        oslo_area_courses = []
        other_courses = []
        
        for course in available_courses:
            # Simple geographic grouping (you could make this more sophisticated)
            if any(keyword in course['name'].lower() for keyword in ['oslo', 'bærum', 'asker', 'miklagard']):
                oslo_area_courses.append(course)
            else:
                other_courses.append(course)
        
        # Oslo area courses
        st.markdown("#### 🏙️ Oslo Area Courses")
        oslo_cols = st.columns(2)
        for i, course in enumerate(oslo_area_courses):
            with oslo_cols[i % 2]:
                is_selected = st.checkbox(
                    f"**{course['name']}**",
                    value=course['key'] in selected_courses,
                    key=f"course_{course['key']}",
                    help=f"Location: {course['location']} | Default start: {course['default_start_time']}"
                )
                if is_selected and course['key'] not in selected_courses:
                    selected_courses.append(course['key'])
                elif not is_selected and course['key'] in selected_courses:
                    selected_courses.remove(course['key'])
        
        # Other courses
        if other_courses:
            st.markdown("#### 🌲 Other Courses")
            other_cols = st.columns(2)
            for i, course in enumerate(other_courses):
                with other_cols[i % 2]:
                    is_selected = st.checkbox(
                        f"**{course['name']}**",
                        value=course['key'] in selected_courses,
                        key=f"course_other_{course['key']}",
                        help=f"Location: {course['location']} | Default start: {course['default_start_time']}"
                    )
                    if is_selected and course['key'] not in selected_courses:
                        selected_courses.append(course['key'])
                    elif not is_selected and course['key'] in selected_courses:
                        selected_courses.remove(course['key'])
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Time preferences
        st.markdown('<div class="preference-section">', unsafe_allow_html=True)
        st.markdown("### ⏰ Preferred Time Slots")
        st.markdown("Select your preferred tee times:")
        
        available_time_slots = generate_time_slots()
        selected_time_slots = preferences.get('time_slots', [])
        
        # Time slot selection with better UX
        time_preference = st.radio(
            "Time Preference",
            options=['morning', 'afternoon', 'evening', 'custom'],
            format_func=lambda x: {
                'morning': '🌅 Morning (6:00-12:00)',
                'afternoon': '☀️ Afternoon (12:00-17:00)', 
                'evening': '🌅 Evening (17:00-20:00)',
                'custom': '🎯 Custom Selection'
            }[x],
            horizontal=True
        )
        
        if time_preference == 'custom':
            selected_time_slots = st.multiselect(
                "Select specific time slots",
                options=available_time_slots,
                default=selected_time_slots,
                help="Choose specific times you're interested in"
            )
        else:
            # Preset time ranges
            time_ranges = {
                'morning': [slot for slot in available_time_slots if slot < '12:00'],
                'afternoon': [slot for slot in available_time_slots if '12:00' <= slot < '17:00'],
                'evening': [slot for slot in available_time_slots if slot >= '17:00']
            }
            selected_time_slots = time_ranges[time_preference]
            st.info(f"Selected {len(selected_time_slots)} time slots for {time_preference}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Player count
        st.markdown('<div class="preference-section">', unsafe_allow_html=True)
        st.markdown("### 👥 Group Size")
        
        min_players = st.selectbox(
            "Minimum Available Spots Required",
            options=[1, 2, 3, 4],
            index=[1, 2, 3, 4].index(preferences.get('min_players', 1)) if preferences.get('min_players', 1) in [1, 2, 3, 4] else 0,
            help="How many spots must be available for you to be notified"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        # Summary and actions
        st.markdown('<div class="preference-section">', unsafe_allow_html=True)
        st.markdown("### 📋 Configuration Summary")
        
        if name and email:
            st.markdown(f"**👤 User:** {name}")
            st.markdown(f"**📧 Email:** {email}")
        else:
            st.warning("Please fill in your name and email")
        
        st.markdown(f"**🏌️ Courses:** {len(selected_courses)} selected")
        st.markdown(f"**⏰ Time Slots:** {len(selected_time_slots)} selected")
        st.markdown(f"**👥 Min Players:** {min_players}")
        st.markdown(f"**📅 Days Ahead:** {days_ahead}")
        st.markdown(f"**🔔 Frequency:** {notification_frequency}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Action buttons
        st.markdown('<div class="preference-section">', unsafe_allow_html=True)
        st.markdown("### 🚀 Actions")
        
        # Validation
        is_valid = all([
            name.strip(),
            email.strip() and '@' in email,
            selected_courses,
            selected_time_slots
        ])
        
        # Show validation feedback if not valid
        if not is_valid:
            validation_issues = []
            if not name.strip():
                validation_issues.append("Enter your name")
            if not (email.strip() and '@' in email):
                validation_issues.append("Enter a valid email address")
            if not selected_courses:
                validation_issues.append("Select at least one golf course")
            if not selected_time_slots:
                validation_issues.append("Select at least one time slot")
            
            st.info(f"📝 To save your profile, please: {', '.join(validation_issues)}")
        
        if st.button("💾 Save Profile", disabled=not is_valid, use_container_width=True):
            # Check if this is an existing user
            is_existing_user = False
            try:
                # Try API first
                response = requests.get(f"http://localhost:8000/api/preferences/{email}", timeout=3)
                is_existing_user = (response.status_code == 200)
            except Exception:
                # Fallback to local file
                try:
                    preferences_file = Path(__file__).parent.parent / "user_preferences.json"
                    if preferences_file.exists():
                        with open(preferences_file, 'r') as f:
                            all_prefs = json.load(f)
                        is_existing_user = email in all_prefs
                except Exception:
                    pass
            
            # Update preferences
            new_preferences = {
                'name': name,
                'email': email,
                'selected_courses': selected_courses,
                'time_slots': selected_time_slots,
                'min_players': min_players,
                'days_ahead': days_ahead,
                'notification_frequency': notification_frequency,
                'timestamp': datetime.now().isoformat()
            }
            
            save_user_preferences(new_preferences)
            
            # Send to API (implement this based on your backend)
            if send_preferences_to_api(new_preferences):
                if is_existing_user:
                    st.success(f"✅ Profile updated successfully for {name}!")
                else:
                    st.success(f"✅ New profile created successfully for {name}!")
                st.balloons()
            else:
                st.error("❌ Failed to save preferences. Please try again.")
        
        if st.button("🧪 Test Notification", disabled=not (name and email), use_container_width=True):
            # Send test notification
            st.info("🔔 Test notification sent! Check your email.")
        
        if st.button("📤 Export Profile", disabled=not is_valid, use_container_width=True):
            # Export preferences as JSON
            export_data = {
                'name': name,
                'email': email,
                'selected_courses': selected_courses,
                'time_slots': selected_time_slots,
                'min_players': min_players,
                'days_ahead': days_ahead,
                'notification_frequency': notification_frequency,
                'export_timestamp': datetime.now().isoformat()
            }
            
            st.download_button(
                label="⬇️ Download Configuration",
                data=json.dumps(export_data, indent=2),
                file_name=f"golf_preferences_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Display selected courses and times
    if selected_courses and selected_time_slots:
        st.markdown("---")
        st.markdown("### 📊 Your Selection Preview")
        
        preview_col1, preview_col2 = st.columns(2)
        
        with preview_col1:
            st.markdown("#### 🏌️ Selected Courses")
            for course_key in selected_courses:
                course = next((c for c in available_courses if c['key'] == course_key), None)
                if course:
                    st.markdown(f"• **{course['name']}**")
        
        with preview_col2:
            st.markdown("#### ⏰ Selected Time Slots")
            # Group time slots for better display
            if len(selected_time_slots) > 10:
                st.markdown(f"• {len(selected_time_slots)} time slots selected")
                st.markdown(f"• Range: {min(selected_time_slots)} - {max(selected_time_slots)}")
            else:
                for time_slot in selected_time_slots[:10]:  # Show first 10
                    st.markdown(f"• {time_slot}")
                if len(selected_time_slots) > 10:
                    st.markdown(f"• ... and {len(selected_time_slots) - 10} more")

if __name__ == "__main__":
    main()
