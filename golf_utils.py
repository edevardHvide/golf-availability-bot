#!/usr/bin/env python3
"""Utility functions for Golf Availability Monitor."""

import datetime
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse


def send_email_notification(subject: str, body: str) -> None:
    """Send email notification using SMTP settings from environment variables.
    
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
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = ', '.join(recipients)  # Display all recipients in header
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
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
