#!/usr/bin/env python3
"""
Test all possible API endpoints for your Render deployment
"""

import requests
import os
from dotenv import load_dotenv
from rich.console import Console

load_dotenv(override=True)
console = Console()

def test_endpoints():
    """Test various endpoint configurations."""
    base_url = os.getenv("API_URL", "").strip()
    
    if not base_url:
        console.print("❌ API_URL not set", style="red")
        return
    
    console.print(f"🧪 Testing API endpoints for: {base_url}")
    console.print("=" * 60)
    
    # Test different endpoint combinations
    endpoints_to_test = [
        # Direct API calls
        (f"{base_url}/health", "Main health endpoint"),
        (f"{base_url}/api/health", "API health through main port"),
        (f"{base_url}/api/preferences", "User preferences through main port"),
        
        # Port 8000 (background API server)
        (f"{base_url}:8000/health", "API health on port 8000"),
        (f"{base_url}:8000/api/health", "API health endpoint on port 8000"),
        (f"{base_url}:8000/api/preferences", "User preferences on port 8000"),
        
        # Test main Streamlit
        (f"{base_url}/", "Main Streamlit app"),
    ]
    
    working_endpoints = []
    
    for url, description in endpoints_to_test:
        try:
            console.print(f"🔗 Testing: {description}")
            console.print(f"   URL: {url}")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                try:
                    # Try to parse as JSON
                    data = response.json()
                    console.print(f"   ✅ SUCCESS (JSON): {response.status_code}", style="green")
                    
                    # Show relevant data
                    if 'status' in data:
                        console.print(f"   📊 Status: {data.get('status')}")
                    if 'user_count' in data:
                        console.print(f"   👥 Users: {data.get('user_count')}")
                    if 'preferences' in data:
                        prefs = data.get('preferences', {})
                        console.print(f"   📋 Preferences: {len(prefs)} users")
                        
                    working_endpoints.append((url, description, 'json'))
                    
                except:
                    # Not JSON, but still successful
                    console.print(f"   ✅ SUCCESS (HTML): {response.status_code}", style="green")
                    console.print(f"   📄 Content length: {len(response.text)} chars")
                    working_endpoints.append((url, description, 'html'))
            else:
                console.print(f"   ⚠️ HTTP {response.status_code}", style="yellow")
                
        except requests.exceptions.Timeout:
            console.print(f"   ⏰ Timeout", style="red")
        except requests.exceptions.ConnectionError:
            console.print(f"   ❌ Connection failed", style="red")
        except Exception as e:
            console.print(f"   ❌ Error: {str(e)[:50]}...", style="red")
        
        console.print("")  # Empty line for readability
    
    # Summary
    console.print("📋 SUMMARY", style="bold blue")
    console.print("=" * 30)
    
    if working_endpoints:
        console.print("✅ Working endpoints:", style="green")
        for url, desc, content_type in working_endpoints:
            console.print(f"  • {desc}: {url} ({content_type})")
        
        # Check for API endpoints specifically
        api_endpoints = [ep for ep in working_endpoints if 'api' in ep[0] and ep[2] == 'json']
        if api_endpoints:
            console.print(f"\n🎯 Found {len(api_endpoints)} working API endpoints!", style="bold green")
            console.print("Your local monitoring can now retrieve user profiles!")
        else:
            console.print(f"\n⚠️ No API endpoints found. Streamlit is running but API server might not be.", style="yellow")
    else:
        console.print("❌ No working endpoints found", style="red")
        console.print("\n💡 Check your Render deployment logs")

if __name__ == "__main__":
    test_endpoints()
