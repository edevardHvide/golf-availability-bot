#!/usr/bin/env python3
"""
Golf Availability Notification Service

This service handles:
1. Daily morning reports (07:00 UTC)
2. New availability notifications (every 10 minutes)

Designed to run as a Render background worker.
"""

import os
import sys
import json
import asyncio
import logging
import smtplib
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the streamlit_app directory to the path for imports
sys.path.append(str(Path(__file__).parent / "streamlit_app"))

try:
    from postgresql_manager import get_db_manager
    DATABASE_AVAILABLE = True
    logger.info("✅ PostgreSQL database available")
except ImportError as e:
    DATABASE_AVAILABLE = False
    logger.error(f"❌ Database not available: {e}")

class EmailService:
    """Handles email notifications using SMTP."""
    
    def __init__(self):
        """Initialize email service with environment variables."""
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.email_user = os.environ.get('EMAIL_USER')
        self.email_password = os.environ.get('EMAIL_PASSWORD')
        self.from_email = os.environ.get('FROM_EMAIL', self.email_user)
        self.reply_to = os.environ.get('REPLY_TO_EMAIL', self.from_email)
        
        if not all([self.email_user, self.email_password]):
            logger.error("❌ Email credentials not configured. Set EMAIL_USER and EMAIL_PASSWORD environment variables.")
            raise ValueError("Email credentials not configured")
        
        logger.info(f"📧 Email service initialized with {self.smtp_server}:{self.smtp_port}")
    
    def send_email(self, to_email: str, subject: str, content: str, is_html: bool = False) -> bool:
        """Send an email to the specified recipient."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['Reply-To'] = self.reply_to
            
            # Add content
            if is_html:
                msg.attach(MIMEText(content, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            logger.info(f"✅ Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
            return False

class NotificationService:
    """Main notification service for golf availability."""
    
    def __init__(self):
        """Initialize the notification service."""
        if not DATABASE_AVAILABLE:
            raise RuntimeError("Database is required for notification service")
        
        self.db_manager = get_db_manager()
        self.email_service = EmailService()
        logger.info("🔔 Notification service initialized")
    
    def format_daily_report_content(self, user_name: str, user_email: str, matching_times: List[Dict]) -> tuple[str, str]:
        """Format the daily report email content."""
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
        
        # Create plain text content
        content_lines = [
            f"Hei {user_name}!",
            "",
            f"Her er din daglige oversikt over tilgjengelige golftider som matcher dine preferanser:",
            ""
        ]
        
        for course, dates in sorted(grouped_times.items()):
            content_lines.append(f"🏌️ {course}:")
            for date_str, times in sorted(dates.items()):
                # Format date nicely
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    if date_obj == date.today():
                        date_display = "I dag"
                    elif date_obj == date.today() + timedelta(days=1):
                        date_display = "I morgen"
                    else:
                        weekdays = ['Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lørdag', 'Søndag']
                        date_display = f"{weekdays[date_obj.weekday()]} {date_obj.strftime('%d.%m')}"
                except:
                    date_display = date_str
                
                content_lines.append(f"  📅 {date_display} ({date_str}):")
                for time_data in sorted(times, key=lambda x: x['time_slot']):
                    spots = time_data['spots_available']
                    content_lines.append(f"    ⏰ {time_data['time_slot']} - {spots} plasser")
                content_lines.append("")
        
        content_lines.extend([
            "Lykke til med å booke! 🍀",
            "",
            "Mvh,",
            "Golf Availability Monitor",
            "",
            f"---",
            f"Denne rapporten ble sendt til {user_email}",
            f"For å endre dine preferanser, besøk din Streamlit app."
        ])
        
        content = "\n".join(content_lines)
        return subject, content
    
    def format_new_availability_content(self, user_name: str, user_email: str, new_times: List[Dict]) -> tuple[str, str]:
        """Format the new availability notification content."""
        if not new_times:
            return None, None
        
        # Create subject
        total_new = len(new_times)
        subject = f"🚨 Nye golftider tilgjengelig for {user_name} - {total_new} nye plasser!"
        
        # Create content
        content_lines = [
            f"Hei {user_name}!",
            "",
            f"Vi har funnet {total_new} nye golftider som matcher dine preferanser:",
            ""
        ]
        
        # Group by course for better readability
        grouped_times = {}
        for time_data in new_times:
            course = time_data['course_name']
            if course not in grouped_times:
                grouped_times[course] = []
            grouped_times[course].append(time_data)
        
        for course, times in sorted(grouped_times.items()):
            content_lines.append(f"🏌️ {course}:")
            for time_data in sorted(times, key=lambda x: (x['date'], x['time_slot'])):
                date_str = time_data['date'].strftime('%Y-%m-%d') if hasattr(time_data['date'], 'strftime') else str(time_data['date'])
                spots = time_data['spots_available']
                
                # Format date
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    if date_obj == date.today():
                        date_display = "I dag"
                    elif date_obj == date.today() + timedelta(days=1):
                        date_display = "I morgen"
                    else:
                        weekdays = ['Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lørdag', 'Søndag']
                        date_display = f"{weekdays[date_obj.weekday()]} {date_obj.strftime('%d.%m')}"
                except:
                    date_display = date_str
                
                content_lines.append(f"  📅 {date_display} kl. {time_data['time_slot']} - {spots} plasser")
            content_lines.append("")
        
        content_lines.extend([
            "⚡ Disse tidene er nylig blitt tilgjengelige, så vær rask med å booke!",
            "",
            "Lykke til! 🍀",
            "",
            "Mvh,",
            "Golf Availability Monitor",
            "",
            f"---",
            f"Denne varslingen ble sendt til {user_email}",
            f"For å endre dine preferanser, besøk din Streamlit app."
        ])
        
        content = "\n".join(content_lines)
        return subject, content
    
    async def send_daily_reports(self) -> Dict[str, Any]:
        """Send daily morning reports to all users."""
        logger.info("📧 Starting daily report generation...")
        
        try:
            # Get all users
            all_users = self.db_manager.get_all_user_preferences()
            if not all_users:
                logger.info("No users found for daily reports")
                return {"success": True, "reports_sent": 0, "message": "No users configured"}
            
            reports_sent = 0
            errors = []
            
            for user_email, user_prefs in all_users.items():
                try:
                    user_name = user_prefs.get('name', user_email.split('@')[0])
                    days_ahead = user_prefs.get('days_ahead', 7)
                    
                    logger.info(f"📊 Generating daily report for {user_name} ({user_email})")
                    
                    # Get matching scraped times for this user
                    matching_times = self.db_manager.get_scraped_times_for_user(user_email, days_ahead)
                    
                    if matching_times:
                        # Format email content
                        subject, content = self.format_daily_report_content(user_name, user_email, matching_times)
                        
                        if subject and content:
                            # Send email
                            success = self.email_service.send_email(user_email, subject, content)
                            
                            if success:
                                reports_sent += 1
                                logger.info(f"✅ Daily report sent to {user_name} with {len(matching_times)} matching times")
                                
                                # Record the notification for each time slot
                                for time_data in matching_times:
                                    self.db_manager.record_sent_notification(
                                        user_email=user_email,
                                        time_id=time_data['time_id'],
                                        notification_type='daily_report',
                                        course_name=time_data['course_name'],
                                        date=str(time_data['date']),
                                        time_slot=time_data['time_slot'],
                                        email_subject=subject,
                                        email_content=content[:1000]  # Truncate for storage
                                    )
                            else:
                                errors.append(f"Failed to send email to {user_email}")
                        else:
                            logger.info(f"📭 No content generated for {user_name} - skipping email")
                    else:
                        logger.info(f"📭 No matching times found for {user_name} - no email sent")
                        
                except Exception as e:
                    error_msg = f"Error processing daily report for {user_email}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            result = {
                "success": True,
                "reports_sent": reports_sent,
                "total_users": len(all_users),
                "errors": errors,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📧 Daily reports completed: {reports_sent}/{len(all_users)} sent successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to send daily reports: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def send_new_availability_notifications(self) -> Dict[str, Any]:
        """Send notifications for new availability (every 10 minutes)."""
        logger.info("🔔 Checking for new availability notifications...")
        
        try:
            # Get all users
            all_users = self.db_manager.get_all_user_preferences()
            if not all_users:
                logger.info("No users found for new availability notifications")
                return {"success": True, "notifications_sent": 0, "message": "No users configured"}
            
            notifications_sent = 0
            errors = []
            
            for user_email, user_prefs in all_users.items():
                try:
                    user_name = user_prefs.get('name', user_email.split('@')[0])
                    
                    # Get new scraped times for this user (last 24 hours, not yet notified)
                    new_times = self.db_manager.get_new_scraped_times_for_user(user_email, hours_back=24)
                    
                    if new_times:
                        logger.info(f"🔔 Found {len(new_times)} new times for {user_name}")
                        
                        # Format email content
                        subject, content = self.format_new_availability_content(user_name, user_email, new_times)
                        
                        if subject and content:
                            # Send email
                            success = self.email_service.send_email(user_email, subject, content)
                            
                            if success:
                                notifications_sent += 1
                                logger.info(f"✅ New availability notification sent to {user_name}")
                                
                                # Record the notification for each time slot
                                for time_data in new_times:
                                    self.db_manager.record_sent_notification(
                                        user_email=user_email,
                                        time_id=time_data['time_id'],
                                        notification_type='new_availability',
                                        course_name=time_data['course_name'],
                                        date=str(time_data['date']),
                                        time_slot=time_data['time_slot'],
                                        email_subject=subject,
                                        email_content=content[:1000]  # Truncate for storage
                                    )
                            else:
                                errors.append(f"Failed to send notification to {user_email}")
                    else:
                        logger.debug(f"📭 No new times for {user_name}")
                        
                except Exception as e:
                    error_msg = f"Error processing new availability for {user_email}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            result = {
                "success": True,
                "notifications_sent": notifications_sent,
                "total_users": len(all_users),
                "errors": errors,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"🔔 New availability check completed: {notifications_sent} notifications sent")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to send new availability notifications: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

async def run_notification_worker():
    """Main worker function that runs the notification jobs."""
    logger.info("🚀 Starting Golf Notification Worker")
    
    try:
        # Initialize notification service
        notification_service = NotificationService()
        
        # Track last daily report time
        last_daily_report = None
        
        while True:
            try:
                current_time = datetime.now()
                
                # Check if it's time for daily report (07:00 UTC)
                if (current_time.hour == 7 and current_time.minute < 10 and 
                    (last_daily_report is None or 
                     last_daily_report.date() < current_time.date())):
                    
                    logger.info("🌅 Time for daily reports (07:00 UTC)")
                    result = await notification_service.send_daily_reports()
                    last_daily_report = current_time
                    
                    if result['success']:
                        logger.info(f"✅ Daily reports completed: {result.get('reports_sent', 0)} sent")
                    else:
                        logger.error(f"❌ Daily reports failed: {result.get('error')}")
                
                # Run new availability notifications (every 10 minutes)
                if current_time.minute % 10 == 0:
                    logger.info("🔔 Running new availability check")
                    result = await notification_service.send_new_availability_notifications()
                    
                    if result['success']:
                        if result.get('notifications_sent', 0) > 0:
                            logger.info(f"✅ New availability notifications: {result['notifications_sent']} sent")
                    else:
                        logger.error(f"❌ New availability notifications failed: {result.get('error')}")
                
                # Wait 1 minute before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Error in notification worker loop: {e}")
                # Wait 5 minutes on error to avoid rapid retries
                await asyncio.sleep(300)
                
    except KeyboardInterrupt:
        logger.info("👋 Notification worker stopped by user")
    except Exception as e:
        logger.error(f"💥 Notification worker crashed: {e}")
        raise

if __name__ == "__main__":
    # Check required environment variables
    required_vars = ['EMAIL_USER', 'EMAIL_PASSWORD', 'DATABASE_URL']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    # Run the notification worker
    asyncio.run(run_notification_worker())
