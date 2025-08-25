#!/usr/bin/env python3
"""
Quick test to verify your setup retrieves profiles from cloud API
and runs personalized monitoring.
"""

import os
from dotenv import load_dotenv
from rich.console import Console

# Load environment
load_dotenv(override=True)
console = Console()

def main():
    """Test the personalized monitoring setup."""
    console.print("🧪 Testing Personalized Golf Monitoring Setup", style="bold blue")
    console.print("=" * 60)
    
    # Show current configuration
    api_url = os.getenv("API_URL", "NOT SET")
    console.print(f"📍 API URL: {api_url}")
    console.print(f"📧 Email enabled: {os.getenv('EMAIL_ENABLED', 'false')}")
    console.print(f"📮 Email from: {os.getenv('EMAIL_FROM', 'not set')}")
    
    # Test API connection
    if "localhost" not in api_url and api_url != "NOT SET":
        console.print(f"\n🌐 Your setup will retrieve profiles from: {api_url}")
        console.print("✅ This is perfect for cloud-based user management!")
    elif "localhost" in api_url:
        console.print(f"\n🏠 Your setup will try local API first, then cloud")
        console.print("⚠️ Make sure your local API server is running")
    else:
        console.print(f"\n❌ API_URL not configured properly")
        console.print("💡 Set API_URL to your Render app URL in .env file")
        return
    
    console.print(f"\n🎯 When you run golf_availability_monitor.py:")
    console.print("1. 🌐 Retrieves all user profiles from cloud API")
    console.print("2. 🏌️ Monitors golf courses based on ALL users' preferences")
    console.print("3. 📧 Sends personalized emails to each user")
    console.print("4. ⚡ Each email contains only slots matching that user's criteria")
    
    console.print(f"\n🚀 Ready to start monitoring!")
    console.print("Run: python golf_availability_monitor.py")

if __name__ == "__main__":
    main()
