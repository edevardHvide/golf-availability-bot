"""
Quick deployment test for your Render app

Run this after deploying to test all endpoints
"""

import requests
import time

def test_render_deployment():
    print("🧪 Testing Render Deployment")
    print("=" * 50)
    
    # Get your Render URL
    render_url = input("Enter your Render app URL (e.g., https://golf-availability-monitor.onrender.com): ").strip()
    
    if not render_url.startswith('http'):
        render_url = 'https://' + render_url
    
    # Remove trailing slash
    render_url = render_url.rstrip('/')
    
    print(f"\n🔍 Testing: {render_url}")
    
    tests = [
        ("Health Check", "/health"),
        ("Main App", "/"),
        ("API Preferences", "/api/preferences"),
        ("API Courses", "/api/courses"),
    ]
    
    results = []
    
    for test_name, endpoint in tests:
        print(f"\n📋 Testing {test_name}...")
        try:
            response = requests.get(f"{render_url}{endpoint}", timeout=30)
            
            if response.status_code == 200:
                print(f"   ✅ {test_name}: OK")
                
                # Show some data for API endpoints
                if endpoint.startswith("/api"):
                    try:
                        data = response.json()
                        if endpoint == "/api/preferences":
                            user_count = data.get("user_count", 0)
                            print(f"      📊 Found {user_count} user profiles")
                        elif endpoint == "/api/courses":
                            total = data.get("total", 0)
                            print(f"      🏌️ Found {total} golf courses")
                        elif endpoint == "/health":
                            status = data.get("status", "unknown")
                            print(f"      💚 Status: {status}")
                    except:
                        print(f"      📄 Response received (non-JSON)")
                        
                results.append((test_name, "✅ PASS"))
            else:
                print(f"   ⚠️ {test_name}: HTTP {response.status_code}")
                results.append((test_name, f"⚠️ HTTP {response.status_code}"))
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ {test_name}: Timeout (app might be sleeping)")
            results.append((test_name, "⏰ TIMEOUT"))
        except requests.exceptions.ConnectionError:
            print(f"   ❌ {test_name}: Connection failed")
            results.append((test_name, "❌ CONNECTION ERROR"))
        except Exception as e:
            print(f"   ❌ {test_name}: {str(e)[:50]}")
            results.append((test_name, f"❌ ERROR"))
    
    # Summary
    print(f"\n🎯 Test Summary for {render_url}")
    print("=" * 50)
    for test_name, result in results:
        print(f"{test_name:<20} {result}")
    
    # Check if app needs warming up
    passing_tests = [r for r in results if "✅" in r[1]]
    if len(passing_tests) < len(tests):
        print(f"\n💡 Tip: If some tests failed, your app might be 'sleeping'")
        print("   Try refreshing the main page a few times to wake it up.")
        print("   Free tier apps sleep after 15 minutes of inactivity.")
    
    return render_url

if __name__ == "__main__":
    url = test_render_deployment()
    
    print(f"\n📝 Next Steps:")
    print(f"1. Update your local .env file:")
    print(f"   API_URL={url}")
    print(f"2. Test local monitoring with cloud API:")
    print(f"   python golf_availability_monitor.py")
    print(f"3. Share this URL with your users! 🚀")
