#!/usr/bin/env python3
"""
Golf Availability Bot - Main Entry Point

This is the main entry point for the golf availability monitoring system.
It provides a command-line interface for monitoring golf course availability.
"""

import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from golf_availability_monitor import main as monitor_main
from golf_utils import test_notifications


def main():
    """Main entry point for the golf availability bot."""
    parser = argparse.ArgumentParser(
        description="Golf Availability Bot - Monitor tee times at Norwegian golf courses"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Start monitoring golf availability')
    monitor_parser.add_argument('--days-ahead', type=int, default=2, 
                               help='Number of days ahead to monitor (default: 2)')
    monitor_parser.add_argument('--start-date', type=str,
                               help='Start monitoring from specific date (YYYY-MM-DD)')
    monitor_parser.add_argument('--dates', type=str,
                               help='Monitor specific dates only (comma-separated YYYY-MM-DD)')
    monitor_parser.add_argument('--between', type=str,
                               help='Filter tee times within time range (e.g., 14-18)')
    monitor_parser.add_argument('--email', type=str,
                               help='Golfbox account email')
    monitor_parser.add_argument('--password', type=str,
                               help='Golfbox account password')
    monitor_parser.add_argument('--debug', action='store_true',
                               help='Show detailed scraping information')
    monitor_parser.add_argument('--cookie', type=str,
                               help='Manual cookie authentication')
    monitor_parser.add_argument('--course-id', type=str, action='append',
                               help='Override course name to GolfBox numeric id (NAME=ID)')
    monitor_parser.add_argument('--course-grid', type=str, action='append',
                               help='Use GolfBox legacy grid URL for this course (NAME=URL)')
    
    # Test notifications command
    test_parser = subparsers.add_parser('test-notifications', 
                                       help='Test desktop notifications')
    
    args = parser.parse_args()
    
    if args.command == 'monitor':
        print("🏌️ Starting Golf Availability Monitor...")
        print("Note: This will use the enhanced monitoring system with user preferences.")
        print("To configure preferences, run the web interface: streamlit_app/run_local.py")
        print()
        
        # Run the main monitoring function
        import asyncio
        asyncio.run(monitor_main())
        
    elif args.command == 'test-notifications':
        print("🔔 Testing desktop notifications...")
        test_notifications()
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
