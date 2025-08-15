#!/usr/bin/env python3
"""Test email notification functionality."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_email_notification():
    """Test the email notification function."""
    # Import the function from check_availability.py
    from check_availability import send_email_notification
    
    print("Testing email notification...")
    print(f"EMAIL_ENABLED: {os.getenv('EMAIL_ENABLED')}")
    print(f"SMTP_HOST: {os.getenv('SMTP_HOST')}")
    print(f"EMAIL_TO: {os.getenv('EMAIL_TO')}")
    
    # Send test email
    subject = "🏌️ Golf Bot Email Test"
    body = """This is a test email from your Golf Availability Bot.

If you received this email, your email notifications are working correctly!

Test details:
- Time: Now
- Course: Test Course
- Available times: 14:30, 15:00, 16:30

Happy golfing! ⛳"""
    
    send_email_notification(subject, body)
    print("Test email sent!")

if __name__ == "__main__":
    test_email_notification()
