#!/usr/bin/env python3
"""Test email configuration for Golf Availability Monitor."""

import os
from dotenv import load_dotenv
from golf_utils import send_email_notification

def main():
    # Load environment variables
    load_dotenv()
    
    print("🧪 Testing Email Configuration")
    print("=" * 40)
    
    # Check if email is enabled
    email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() in ("1", "true", "yes")
    print(f"EMAIL_ENABLED: {email_enabled}")
    
    if not email_enabled:
        print("\n❌ Email is disabled. Set EMAIL_ENABLED=true in your .env file")
        return
    
    # Check environment variables
    required_vars = [
        "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", 
        "EMAIL_FROM", "EMAIL_TO"
    ]
    
    print("\n📋 Environment Variables:")
    missing = []
    for var in required_vars:
        value = os.getenv(var, "").strip()
        if value:
            if var == "SMTP_PASS":
                print(f"{var}: {'*' * len(value)} (hidden)")
            else:
                print(f"{var}: {value}")
        else:
            print(f"{var}: ❌ NOT SET")
            missing.append(var)
    
    if missing:
        print(f"\n❌ Missing variables: {', '.join(missing)}")
        print("\nFor Gmail users, make sure to:")
        print("1. Enable 2-factor authentication")
        print("2. Generate an App Password: https://myaccount.google.com/apppasswords")
        print("3. Use the App Password (not your regular password) in SMTP_PASS")
        return
    
    # Test sending email
    print("\n📧 Sending test email...")
    try:
        send_email_notification(
            "🧪 Golf Monitor Email Test", 
            """This is a test email from your Golf Availability Monitor.

If you received this email, your email configuration is working correctly!

Configuration tested:
- SMTP connection
- Authentication
- Message delivery

Happy golfing! ⛳

--- Golf Availability Monitor ---
"""
        )
        print("✅ Test email sent successfully!")
        print("Check your inbox (and spam folder) for the test email.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()
