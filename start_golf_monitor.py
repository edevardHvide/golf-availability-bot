#!/usr/bin/env python3
"""
Golf Monitor Startup Script

This script helps you start the golf monitoring system in different modes.
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

def print_banner():
    print("🏌️" + "=" * 60)
    print("  Golf Availability Monitor - Startup Script")
    print("=" * 62)
    print()

def start_scheduled_monitoring():
    """Start the scheduled monitoring (9am, 12pm, 9pm)"""
    print("⏰ Starting SCHEDULED monitoring...")
    print("   • Notifications at 9am, 12pm, and 9pm")
    print("   • Press Ctrl+C to stop")
    print()
    
    cmd = [sys.executable, "golf_availability_monitor.py", "--scheduled"]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Scheduled monitoring stopped.")

def start_local_api():
    """Start the local API server for immediate checks"""
    print("🌐 Starting LOCAL API server...")
    print("   • Enables immediate checks from web UI")
    print("   • Running on http://localhost:5000")
    print("   • Press Ctrl+C to stop")
    print()
    
    cmd = [sys.executable, "local_api_server.py"]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Local API server stopped.")

def start_continuous_monitoring():
    """Start continuous monitoring (legacy mode)"""
    print("🔄 Starting CONTINUOUS monitoring...")
    print("   • Checks every 5 minutes")
    print("   • Press Ctrl+C to stop")
    print()
    
    cmd = [sys.executable, "golf_availability_monitor.py"]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Continuous monitoring stopped.")

def run_immediate_check():
    """Run a single immediate check"""
    print("⚡ Running IMMEDIATE check...")
    print("   • Single check and exit")
    print()
    
    cmd = [sys.executable, "golf_availability_monitor.py", "--immediate"]
    
    try:
        result = subprocess.run(cmd)
        if result.returncode == 0:
            print("✅ Immediate check completed successfully!")
        else:
            print("❌ Immediate check failed!")
    except KeyboardInterrupt:
        print("\n⏹️ Immediate check interrupted.")

def main():
    print_banner()
    
    parser = argparse.ArgumentParser(description="Golf Monitor Startup Script")
    parser.add_argument("mode", choices=["scheduled", "api", "continuous", "immediate"], 
                       help="Mode to run the golf monitor")
    
    args = parser.parse_args()
    
    if args.mode == "scheduled":
        start_scheduled_monitoring()
    elif args.mode == "api":
        start_local_api()
    elif args.mode == "continuous":
        start_continuous_monitoring()
    elif args.mode == "immediate":
        run_immediate_check()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments provided, show interactive menu
        print_banner()
        print("Choose a mode:")
        print("1. 📅 Scheduled monitoring (9am, 12pm, 9pm)")
        print("2. 🌐 Local API server (for immediate checks)")
        print("3. 🔄 Continuous monitoring (every 5 minutes)")
        print("4. ⚡ Single immediate check")
        print()
        
        try:
            choice = input("Enter choice (1-4): ").strip()
            
            if choice == "1":
                start_scheduled_monitoring()
            elif choice == "2":
                start_local_api()
            elif choice == "3":
                start_continuous_monitoring()
            elif choice == "4":
                run_immediate_check()
            else:
                print("❌ Invalid choice. Use 1-4.")
                sys.exit(1)
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
    else:
        main()
