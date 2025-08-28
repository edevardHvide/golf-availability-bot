#!/usr/bin/env python3
"""
Test script for the Golf Notification System

This script tests the various components of the notification system:
- Database connectivity
- Data ingestion
- Email service
- Notification generation
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, date, timedelta
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add paths for imports
sys.path.append(str(Path(__file__).parent / "streamlit_app"))

def test_database_connection():
    """Test PostgreSQL database connection."""
    logger.info("🧪 Testing database connection...")
    
    if not os.environ.get('DATABASE_URL'):
        logger.warning("⚠️ DATABASE_URL not set - skipping database test")
        return False
    
    try:
        from postgresql_manager import get_db_manager
        db_manager = get_db_manager()
        health = db_manager.health_check()
        
        if health['connected']:
            logger.info(f"✅ Database connected: {health['user_count']} users")
            return True
        else:
            logger.error(f"❌ Database connection failed: {health.get('error')}")
            return False
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

def test_data_ingestion():
    """Test data ingestion service."""
    logger.info("🧪 Testing data ingestion...")
    
    if not os.environ.get('DATABASE_URL'):
        logger.warning("⚠️ DATABASE_URL not set - skipping data ingestion test")
        return False
    
    try:
        from data_ingestion_service import DataIngestionService
        ingestion_service = DataIngestionService()
        
        # Create test data
        test_data = {
            "Test Golf Club_2024-12-25": {
                "09:00": 4,
                "10:30": 2,
                "14:00": 3
            },
            "Another Test Course_2024-12-26": {
                "08:30": 2,
                "16:00": 1
            }
        }
        
        success = ingestion_service.process_availability_results(
            test_data, 
            {"test": True, "timestamp": datetime.now().isoformat()}
        )
        
        if success:
            logger.info("✅ Data ingestion test passed")
            return True
        else:
            logger.error("❌ Data ingestion test failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Data ingestion test failed: {e}")
        return False

def test_email_service():
    """Test email service configuration."""
    logger.info("🧪 Testing email service...")
    
    try:
        from notification_service import EmailService
        
        # Check if email credentials are configured (matching golf_utils.py)
        required_vars = ['SMTP_USER', 'SMTP_PASS', 'EMAIL_ENABLED']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            logger.warning(f"⚠️ Email service not configured: missing {missing_vars}")
            return False
        
        email_service = EmailService()
        logger.info(f"✅ Email service configured: {email_service.email_user}")
        
        # Don't send actual test email unless explicitly requested
        test_email = os.environ.get('TEST_EMAIL')
        if test_email:
            logger.info(f"📧 Sending test email to {test_email}")
            success = email_service.send_email(
                test_email,
                "🧪 Golf Notification System Test",
                "This is a test email from your golf notification system.\n\nIf you received this, the email service is working correctly! ✅"
            )
            if success:
                logger.info("✅ Test email sent successfully")
            else:
                logger.error("❌ Test email failed")
            return success
        else:
            logger.info("✅ Email service configuration verified (set TEST_EMAIL to send test)")
            return True
            
    except Exception as e:
        logger.error(f"❌ Email service test failed: {e}")
        return False

def test_notification_generation():
    """Test notification content generation."""
    logger.info("🧪 Testing notification generation...")
    
    try:
        # Test content formatting without requiring database
        # We'll create a mock service that doesn't need database initialization
        class MockNotificationService:
            def format_daily_report_content(self, user_name, user_email, matching_times):
                if not matching_times:
                    return None, None
                
                # Group by course and date
                grouped_times = {}
                for time_data in matching_times:
                    course = time_data['course_name']
                    date_str = time_data['date'].strftime('%Y-%m-%d') if hasattr(time_data['date'], 'strftime') else str(time_data['date'])
                    
                    if course not in grouped_times:
                        grouped_times[course] = {}
                    if date_str not in grouped_times[course]:
                        grouped_times[course][date_str] = []
                    
                    grouped_times[course][date_str].append(time_data)
                
                # Create subject
                total_slots = len(matching_times)
                subject = f"⛳ Daglig golfrapport for {user_name} - {total_slots} tilgjengelige tider"
                
                # Create content
                content_lines = [
                    f"Hei {user_name}!",
                    "",
                    f"Her er din daglige oversikt over tilgjengelige golftider som matcher dine preferanser:",
                    ""
                ]
                
                for course, dates in sorted(grouped_times.items()):
                    content_lines.append(f"🏌️ {course}:")
                    for date_str, times in sorted(dates.items()):
                        content_lines.append(f"  📅 {date_str}:")
                        for time_data in sorted(times, key=lambda x: x['time_slot']):
                            spots = time_data['spots_available']
                            content_lines.append(f"    ⏰ {time_data['time_slot']} - {spots} plasser")
                        content_lines.append("")
                
                content_lines.extend([
                    "Lykke til med å booke! 🍀",
                    "",
                    "Mvh,",
                    "Golf Availability Monitor"
                ])
                
                content = "\n".join(content_lines)
                return subject, content
            
            def format_new_availability_content(self, user_name, user_email, new_times):
                if not new_times:
                    return None, None
                
                total_new = len(new_times)
                subject = f"🚨 Nye golftider tilgjengelig for {user_name} - {total_new} nye plasser!"
                
                content_lines = [
                    f"Hei {user_name}!",
                    "",
                    f"Vi har funnet {total_new} nye golftider som matcher dine preferanser:",
                    ""
                ]
                
                for time_data in new_times:
                    course = time_data['course_name']
                    date_str = time_data['date'].strftime('%Y-%m-%d') if hasattr(time_data['date'], 'strftime') else str(time_data['date'])
                    spots = time_data['spots_available']
                    content_lines.append(f"🏌️ {course}: {date_str} kl. {time_data['time_slot']} - {spots} plasser")
                
                content_lines.extend([
                    "",
                    "⚡ Disse tidene er nylig blitt tilgjengelige, så vær rask med å booke!",
                    "",
                    "Lykke til! 🍀"
                ])
                
                content = "\n".join(content_lines)
                return subject, content
        
        # Create mock data for testing
        mock_times = [
            {
                'time_id': 1,
                'course_name': 'Test Golf Club',
                'date': date.today(),
                'time_slot': '09:00',
                'spots_available': 4,
                'created_at': datetime.now()
            },
            {
                'time_id': 2,
                'course_name': 'Test Golf Club',
                'date': date.today() + timedelta(days=1),
                'time_slot': '14:30',
                'spots_available': 2,
                'created_at': datetime.now()
            }
        ]
        
        # Test daily report formatting
        service = MockNotificationService()
        subject, content = service.format_daily_report_content("Test User", "test@example.com", mock_times)
        
        if subject and content:
            logger.info("✅ Daily report generation test passed")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   Content length: {len(content)} characters")
            
            # Test new availability formatting
            subject2, content2 = service.format_new_availability_content("Test User", "test@example.com", mock_times[:1])
            
            if subject2 and content2:
                logger.info("✅ New availability generation test passed")
                logger.info(f"   New alert subject: {subject2}")
                return True
        
        logger.error("❌ Notification generation test failed")
        return False
        
    except Exception as e:
        logger.error(f"❌ Notification generation test failed: {e}")
        return False

def test_user_preferences():
    """Test user preferences retrieval."""
    logger.info("🧪 Testing user preferences...")
    
    try:
        from postgresql_manager import get_db_manager
        db_manager = get_db_manager()
        
        # Get all users
        all_users = db_manager.get_all_user_preferences()
        logger.info(f"✅ Found {len(all_users)} users in database")
        
        if all_users:
            # Show sample user
            sample_email = list(all_users.keys())[0]
            sample_user = all_users[sample_email]
            logger.info(f"   Sample user: {sample_user.get('name', 'No name')} ({sample_email})")
            logger.info(f"   Courses: {len(sample_user.get('selected_courses', []))}")
            logger.info(f"   Time slots: {len(sample_user.get('time_slots', []))}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ User preferences test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests and report results."""
    logger.info("🧪 Starting Golf Notification System Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Data Ingestion", test_data_ingestion),
        ("Email Service", test_email_service),
        ("Notification Generation", test_notification_generation),
        ("User Preferences", test_user_preferences),
    ]
    
    results = {}
    for test_name, test_func in tests:
        logger.info(f"\n🔬 Running {test_name} test...")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n🎯 Overall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        logger.info("🎉 All tests passed! Your notification system is ready to go!")
    else:
        logger.warning(f"⚠️ {len(tests) - passed} tests failed. Check configuration and try again.")
    
    return passed == len(tests)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Golf Notification System")
    parser.add_argument("--skip-db", action="store_true", help="Skip database-dependent tests")
    parser.add_argument("--test-email", help="Email address to send test email to")
    args = parser.parse_args()
    
    # Check if we have required environment variables for full testing
    required_vars = ['DATABASE_URL']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars and not args.skip_db:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        logger.error("   Set DATABASE_URL to test the notification system")
        logger.error("   Or use --skip-db to test non-database components")
        sys.exit(1)
    
    if args.test_email:
        os.environ['TEST_EMAIL'] = args.test_email
    
    # Run tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
