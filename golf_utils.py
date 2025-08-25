#!/usr/bin/env python3
"""Utility functions for Golf Availability Monitor."""

import datetime
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse


def create_html_email_template(subject: str, new_availability: list, all_availability: dict, time_window: str, config_info: dict = None, club_order: list = None, user_preferences: dict = None) -> str:
    """Create a beautiful HTML email template for golf availability notifications."""
    current_date = datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')
    
    if config_info is None:
        config_info = {}
    
    # Group data by date for better organization
    def group_by_date(availability_dict):
        """Group availability data by date."""
        grouped = {}
        for state_key, times in availability_dict.items():
            if times:  # Only include courses with availability
                parts = state_key.rsplit('_', 1)
                if len(parts) == 2:
                    course_name, date_str = parts
                    if date_str not in grouped:
                        grouped[date_str] = {}
                    grouped[date_str][course_name] = times
        return grouped
    
    def format_date_header(date_str):
        """Format date string for display."""
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            today = datetime.date.today()
            if date_obj == today:
                return f"Today ({date_obj.strftime('%A, %B %d')})"
            elif date_obj == today + datetime.timedelta(days=1):
                return f"Tomorrow ({date_obj.strftime('%A, %B %d')})"
            else:
                return date_obj.strftime('%A, %B %d, %Y')
        except Exception:
            return date_str
    
    # Create new availability HTML - structured by date
    new_availability_html = ""
    if new_availability:
        # Group new availability by date
        new_by_date = {}
        for item in new_availability:
            # Extract date from item string (format: "Course on YYYY-MM-DD at HH:MM: X spots")
            import re
            match = re.search(r'(\w+.*?) on (\d{4}-\d{2}-\d{2}) at (\d{2}:\d{2}): (\d+) spot', item)
            if match:
                course, date_str, time_str, spots = match.groups()
                if date_str not in new_by_date:
                    new_by_date[date_str] = []
                new_by_date[date_str].append({
                    'course': course,
                    'time': time_str,
                    'spots': spots
                })
        
        new_availability_html = """
        <div style="background: linear-gradient(135deg, #e8f5e8 0%, #f0f9f0 100%); padding: 20px; border-radius: 12px; margin-bottom: 30px; border-left: 5px solid #4CAF50;">
            <h2 style="color: #2e7d32; margin: 0 0 15px 0; font-size: 20px; display: flex; align-items: center;">
                🚨 New Availability Detected!
            </h2>
        """
        
        # Sort dates
        for date_str in sorted(new_by_date.keys()):
            date_header = format_date_header(date_str)
            new_availability_html += f"""
            <div style="margin-bottom: 15px;">
                <h3 style="color: #1b5e20; margin: 0 0 8px 0; font-size: 16px; padding: 8px 12px; background: rgba(76, 175, 80, 0.1); border-radius: 6px;">
                    📅 {date_header}
                </h3>
            """
            
            # Group by course for this date
            courses_on_date = {}
            for item in new_by_date[date_str]:
                course = item['course']
                if course not in courses_on_date:
                    courses_on_date[course] = []
                courses_on_date[course].append(f"{item['time']} ({item['spots']} spots)")
            
            # Display each course in the specified order
            if club_order:
                # Sort courses by the provided order
                courses_sorted = []
                for club_name in club_order:
                    if club_name in courses_on_date:
                        courses_sorted.append((club_name, courses_on_date[club_name]))
                # Add any courses not in the order list at the end
                for course, times_list in sorted(courses_on_date.items()):
                    if course not in club_order:
                        courses_sorted.append((course, times_list))
            else:
                courses_sorted = sorted(courses_on_date.items())
            
            for course, times_list in courses_sorted:
                times_str = ', '.join(times_list)
                new_availability_html += f"""
                <div style="background: white; padding: 10px 14px; margin: 4px 0 4px 15px; border-radius: 6px; border-left: 3px solid #4CAF50; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <strong style="color: #2e7d32;">{course}:</strong>
                    <span style="color: #424242; margin-left: 8px;">{times_str}</span>
                </div>
                """
            
            new_availability_html += "</div>"
        
        new_availability_html += "</div>"
    
    # Create configuration section
    config_section = ""
    if config_info:
        config_section = """
        <div style="background: linear-gradient(135deg, #e3f2fd 0%, #ffffff 100%); padding: 20px; border-radius: 12px; margin-top: 20px; border-left: 5px solid #2196F3;">
            <h3 style="color: #1976d2; margin: 0 0 15px 0; font-size: 16px; display: flex; align-items: center;">
                ⚙️ Monitor Configuration
            </h3>
            <div style="color: #424242; font-size: 14px;">
        """
        
        # Add configuration details
        if 'courses' in config_info:
            config_section += f"""
                <div style="margin-bottom: 10px;">
                    <strong>📊 Courses:</strong> {config_info['courses']} golf courses
                </div>
            """
        
        if 'time_window' in config_info:
            config_section += f"""
                <div style="margin-bottom: 10px;">
                    <strong>⏰ Time Window:</strong> {config_info['time_window']}
                </div>
            """
        
        if 'interval' in config_info:
            config_section += f"""
                <div style="margin-bottom: 10px;">
                    <strong>🔄 Check Interval:</strong> {config_info['interval']} seconds ({config_info['interval']//60} minutes)
                </div>
            """
        
        if 'min_players' in config_info:
            config_section += f"""
                <div style="margin-bottom: 10px;">
                    <strong>👥 Min. Spots Required:</strong> {config_info['min_players']}
                </div>
            """
        
        if 'days' in config_info:
            config_section += f"""
                <div style="margin-bottom: 10px;">
                    <strong>📅 Days to Check:</strong> {config_info['days']} days from today
                </div>
            """
        
        config_section += """
            </div>
        </div>
        """
    # Create personalized greeting
    personalized_greeting = ""
    if user_preferences:
        user_name = user_preferences.get('name', 'Golf Enthusiast')
        courses_count = len(user_preferences.get('selected_courses', []))
        times_count = len(user_preferences.get('time_slots', []))
        personalized_greeting = f"""
        <div style="background: #f8f9fa; padding: 20px; border-radius: 12px; margin-bottom: 20px; border-left: 4px solid #007bff;">
            <h3 style="color: #343a40; margin: 0 0 10px 0; font-size: 18px;">
                👋 Hello {user_name}!
            </h3>
            <p style="color: #6c757d; margin: 0; font-size: 14px;">
                This personalized alert is based on your preferences:<br>
                • Monitoring {courses_count} golf course(s)<br>
                • Looking for times in {times_count} preferred slot(s)<br>
                • Minimum {user_preferences.get('min_players', 1)} player(s)
            </p>
        </div>
        """
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f7fa; line-height: 1.6;">
        <div style="max-width: 600px; margin: 20px auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); color: white; padding: 30px 20px; text-align: center;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                    ⛳ Golf Availability Alert
                </h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">
                    Time Window: {time_window}
                </p>
                <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.8;">
                    {current_date}
                </p>
            </div>
            
            <!-- Content -->
            <div style="padding: 30px 20px;">
                {personalized_greeting}
                {new_availability_html}
                
                <!-- Call to Action -->
                <div style="text-align: center; margin: 30px 0 20px 0;">
                    <div style="background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%); color: white; padding: 15px 25px; border-radius: 25px; display: inline-block; font-weight: 600; font-size: 16px; text-decoration: none; box-shadow: 0 4px 15px rgba(255, 107, 53, 0.3);">
                        🏌️ Happy Golfing!
                    </div>
                </div>
                
                <!-- Configuration Info Section -->
                {config_section}
                
                <!-- Tips Section -->
                <div style="background: #f8f9fa; padding: 20px; border-radius: 12px; margin-top: 20px; border-left: 5px solid #6c757d;">
                    <h3 style="color: #495057; margin: 0 0 10px 0; font-size: 16px;">💡 Quick Tips:</h3>
                    <ul style="margin: 0; padding-left: 20px; color: #6c757d; font-size: 14px;">
                        <li>Book quickly - popular times fill up fast!</li>
                        <li>Check the golf course website for any weather updates</li>
                        <li>Don't forget to confirm your booking details</li>
                    </ul>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e9ecef;">
                <p style="margin: 0; color: #6c757d; font-size: 12px;">
                    🤖 Automated by Golf Availability Monitor
                </p>
                <p style="margin: 5px 0 0 0; color: #adb5bd; font-size: 11px;">
                    This is an automated notification. Please do not reply to this email.
                </p>
            </div>
        </div>
        
        <!-- Mobile Responsive Styles -->
        <style>
            @media only screen and (max-width: 600px) {{
                .email-container {{
                    margin: 10px !important;
                    border-radius: 8px !important;
                }}
                .header-padding {{
                    padding: 20px 15px !important;
                }}
                .content-padding {{
                    padding: 20px 15px !important;
                }}
                .header-title {{
                    font-size: 24px !important;
                }}
            }}
        </style>
    </body>
    </html>
    """
    
    return html_template


def send_email_notification(subject: str, new_availability: list = None, all_availability: dict = None, time_window: str = "08:00-17:00", config_info: dict = None, club_order: list = None, user_preferences: dict = None) -> None:
    """Send beautiful HTML email notification using SMTP settings from environment variables.
    
    Args:
        subject: Email subject line
        new_availability: List of newly available time slots
        all_availability: Dictionary of all current availability 
        time_window: Time window being monitored
        config_info: Dictionary with startup configuration info
    
    For Gmail users:
    1. Enable 2-factor authentication on your Google account
    2. Generate an App Password: https://myaccount.google.com/apppasswords
    3. Use the App Password (not your regular password) in SMTP_PASS
    
    Environment variables needed:
    - EMAIL_ENABLED=true
    - SMTP_HOST=smtp.gmail.com (for Gmail)
    - SMTP_PORT=587 (for Gmail)
    - SMTP_USER=your-email@gmail.com
    - SMTP_PASS=your-app-password (16-character app password for Gmail)
    - EMAIL_FROM=your-email@gmail.com
    - EMAIL_TO=recipient@example.com
    """
    # Default to empty lists/dicts if not provided
    if new_availability is None:
        new_availability = []
    if all_availability is None:
        all_availability = {}
    if config_info is None:
        config_info = {}
        
    # Check if email is enabled
    email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() in ("1", "true", "yes")
    if not email_enabled:
        print("[EMAIL] Email notifications disabled (set EMAIL_ENABLED=true to enable)")
        return
    
    try:
        smtp_host = os.getenv("SMTP_HOST", "").strip()
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_ssl = os.getenv("SMTP_SSL", "false").lower() in ("1", "true", "yes")
        smtp_user = os.getenv("SMTP_USER", "").strip()
        smtp_pass = os.getenv("SMTP_PASS", "").strip()
        email_from = os.getenv("EMAIL_FROM", "").strip()
        
        # Use user's email if provided, otherwise fall back to environment variable
        if user_preferences and user_preferences.get('email'):
            email_to = user_preferences['email'].strip()
        else:
            email_to = os.getenv("EMAIL_TO", "").strip()
        
        if not all([smtp_host, smtp_user, smtp_pass, email_from, email_to]):
            missing = []
            if not smtp_host:
                missing.append("SMTP_HOST")
            if not smtp_user:
                missing.append("SMTP_USER") 
            if not smtp_pass:
                missing.append("SMTP_PASS")
            if not email_from:
                missing.append("EMAIL_FROM")
            if not email_to:
                missing.append("EMAIL_TO")
            print(f"[EMAIL] Missing required environment variables: {', '.join(missing)}")
            return
        
        # Parse multiple recipients (comma-separated) - but for personalized emails, use single recipient
        if user_preferences:
            recipients = [email_to]  # Single recipient for personalized emails
        else:
            recipients = [email.strip() for email in email_to.split(',') if email.strip()]
        if not recipients:
            print("[EMAIL] No valid recipients found")
            return
        
        # Create HTML email content
        html_body = create_html_email_template(subject, new_availability, all_availability, time_window, config_info, club_order, user_preferences)
        
        # Create plain text fallback
        plain_text_body = f"""Golf Availability Alert
Time Window: {time_window}

"""
        if new_availability:
            plain_text_body += "New availability:\n"
            for item in new_availability:
                plain_text_body += f"• {item}\n"
            plain_text_body += "\n"
        
        plain_text_body += "\nHappy golfing! ⛳\n\n--- Golf Availability Monitor ---"
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = email_from
        msg['To'] = email_from  # Send to self to hide recipients
        msg['Bcc'] = ', '.join(recipients)  # Use BCC for actual recipients
        msg['Subject'] = subject
        
        # Attach plain text and HTML versions
        msg.attach(MIMEText(plain_text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email with debugging and retry logic
        print(f"[EMAIL] Connecting to {smtp_host}:{smtp_port} (SSL={smtp_ssl})")
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                if smtp_ssl:
                    server = smtplib.SMTP_SSL(smtp_host, smtp_port)
                else:
                    server = smtplib.SMTP(smtp_host, smtp_port)
                    server.starttls()
                
                print(f"[EMAIL] Authenticating as {smtp_user} (attempt {attempt + 1})")
                server.login(smtp_user, smtp_pass)
                
                print(f"[EMAIL] Sending to {len(recipients)} recipients")
                server.send_message(msg, to_addrs=recipients)
                server.quit()
                
                print(f"[EMAIL] ✅ Sent successfully: {subject}")
                return
                
            except smtplib.SMTPAuthenticationError as e:
                if attempt < max_retries - 1:
                    print(f"[EMAIL] Authentication failed on attempt {attempt + 1}, retrying...")
                    import time
                    time.sleep(2)
                    continue
                else:
                    raise e
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL] Authentication failed: {e}")
        if "gmail.com" in smtp_host.lower():
            print("[EMAIL] Gmail users: Make sure you're using an App Password, not your regular password!")
            print("[EMAIL] Steps to fix:")
            print("[EMAIL] 1. Enable 2-factor authentication: https://myaccount.google.com/security")
            print("[EMAIL] 2. Generate App Password: https://myaccount.google.com/apppasswords")
            print("[EMAIL] 3. Use the 16-character App Password in SMTP_PASS environment variable")
        else:
            print(f"[EMAIL] Check your SMTP_USER and SMTP_PASS for {smtp_host}")
    except smtplib.SMTPServerDisconnected as e:
        print(f"[EMAIL] Server disconnected: {e}")
        print("[EMAIL] Check your SMTP_HOST and SMTP_PORT settings")
    except smtplib.SMTPRecipientsRefused as e:
        print(f"[EMAIL] Recipients refused: {e}")
        print("[EMAIL] Check your EMAIL_TO addresses")
    except Exception as e:
        print(f"[EMAIL] Failed to send: {e}")
        if "gmail.com" in smtp_host.lower() and "Password not accepted" in str(e):
            print("[EMAIL] Gmail users: You need an App Password! See instructions above.")
        print(f"[EMAIL] SMTP settings: {smtp_host}:{smtp_port}, SSL={smtp_ssl}, User={smtp_user}")
        print("[EMAIL] Make sure all email environment variables are set correctly.")


def rewrite_url_for_day(u: str, day: datetime.date) -> str:
    """Rewrite common date params to target day while preserving time if present.

    - Booking_Start=YYYYMMDDTHHMMSS → replace date part, keep time
    - SelectedDate=YYYYMMDDTHHMMSS → replace date part, keep time
    - date/dato/resdate/selectedDate=YYYY-MM-DD → set to target
    """
    try:
        parsed = urlparse(u)
        qs = dict(parse_qsl(parsed.query))
        # Booking_Start
        if "Booking_Start" in qs and re.search(r"T\d{6}$", qs["Booking_Start"]):
            time_part = qs["Booking_Start"].split("T", 1)[1]
            qs["Booking_Start"] = f"{day.strftime('%Y%m%d')}T{time_part}"
        # SelectedDate with time format
        if "SelectedDate" in qs and re.search(r"T\d{6}$", qs["SelectedDate"]):
            time_part = qs["SelectedDate"].split("T", 1)[1]
            qs["SelectedDate"] = f"{day.strftime('%Y%m%d')}T{time_part}"
        # Generic date keys (YYYY-MM-DD format)
        date_keys = ["date", "dato", "resdate"]
        for k in date_keys:
            if k in qs:
                qs[k] = day.strftime("%Y-%m-%d")
        # Handle lowercase selectedDate (YYYY-MM-DD format)
        if "selectedDate" in qs and not re.search(r"T\d{6}$", qs["selectedDate"]):
            qs["selectedDate"] = day.strftime("%Y-%m-%d")
        new_query = urlencode(qs)
        return urlunparse((parsed.scheme or "https", parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    except Exception:
        return u
