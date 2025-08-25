#!/usr/bin/env python3
"""Utility functions for Golf Availability Monitor."""

import datetime
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse


def create_html_email_template(subject: str, new_availability: list, all_availability: dict, time_window: str) -> str:
    """Create a beautiful HTML email template for golf availability notifications."""
    current_date = datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')
    
    # Create new availability HTML
    new_availability_html = ""
    if new_availability:
        new_availability_html = """
        <div style="background: linear-gradient(135deg, #e8f5e8 0%, #f0f9f0 100%); padding: 20px; border-radius: 12px; margin-bottom: 30px; border-left: 5px solid #4CAF50;">
            <h2 style="color: #2e7d32; margin: 0 0 15px 0; font-size: 20px; display: flex; align-items: center;">
                🚨 New Availability Detected!
            </h2>
        """
        for item in new_availability:
            new_availability_html += f"""
            <div style="background: white; padding: 12px 16px; margin: 8px 0; border-radius: 8px; border-left: 4px solid #4CAF50; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <span style="color: #2e7d32; font-weight: 600;">• {item}</span>
            </div>
            """
        new_availability_html += "</div>"
    
    # Create all availability HTML
    all_availability_html = """
    <div style="background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%); padding: 20px; border-radius: 12px; border-left: 5px solid #2196F3;">
        <h2 style="color: #1976d2; margin: 0 0 15px 0; font-size: 20px; display: flex; align-items: center;">
            📊 Current Availability Summary
        </h2>
    """
    
    if all_availability:
        for state_key, times in all_availability.items():
            if times:  # Only show courses with availability
                course_name = state_key.rsplit('_', 1)[0]  # Remove date suffix
                times_str = ', '.join([f'{t} ({c} spots)' for t, c in times.items()])
                all_availability_html += f"""
                <div style="background: white; padding: 12px 16px; margin: 8px 0; border-radius: 8px; border-left: 4px solid #2196F3; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <strong style="color: #1976d2;">{course_name}:</strong>
                    <span style="color: #424242; margin-left: 8px;">{times_str}</span>
                </div>
                """
    else:
        all_availability_html += """
        <div style="background: white; padding: 12px 16px; margin: 8px 0; border-radius: 8px; border-left: 4px solid #ff9800; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <span style="color: #ef6c00;">No availability found in the monitored time window.</span>
        </div>
        """
    
    all_availability_html += "</div>"
    
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
                {new_availability_html}
                
                {all_availability_html}
                
                <!-- Call to Action -->
                <div style="text-align: center; margin: 30px 0 20px 0;">
                    <div style="background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%); color: white; padding: 15px 25px; border-radius: 25px; display: inline-block; font-weight: 600; font-size: 16px; text-decoration: none; box-shadow: 0 4px 15px rgba(255, 107, 53, 0.3);">
                        🏌️ Happy Golfing!
                    </div>
                </div>
                
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


def send_email_notification(subject: str, new_availability: list = None, all_availability: dict = None, time_window: str = "08:00-17:00") -> None:
    """Send beautiful HTML email notification using SMTP settings from environment variables.
    
    Args:
        subject: Email subject line
        new_availability: List of newly available time slots
        all_availability: Dictionary of all current availability 
        time_window: Time window being monitored
    
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
        
        # Parse multiple recipients (comma-separated)
        recipients = [email.strip() for email in email_to.split(',') if email.strip()]
        if not recipients:
            print("[EMAIL] No valid recipients found")
            return
        
        # Create HTML email content
        html_body = create_html_email_template(subject, new_availability, all_availability, time_window)
        
        # Create plain text fallback
        plain_text_body = f"""Golf Availability Alert
Time Window: {time_window}

"""
        if new_availability:
            plain_text_body += "New availability:\n"
            for item in new_availability:
                plain_text_body += f"• {item}\n"
            plain_text_body += "\n"
        
        if all_availability:
            plain_text_body += "All current availability:\n"
            for state_key, times in all_availability.items():
                if times:
                    course_name = state_key.rsplit('_', 1)[0]
                    times_str = ', '.join([f'{t}({c} spots)' for t, c in times.items()])
                    plain_text_body += f"• {course_name}: {times_str}\n"
        
        plain_text_body += "\nHappy golfing! ⛳\n\n--- Golf Availability Monitor ---"
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = email_from
        msg['To'] = ', '.join(recipients)
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
