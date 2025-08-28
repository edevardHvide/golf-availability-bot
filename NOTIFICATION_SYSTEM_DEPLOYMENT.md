# 🔔 Golf Notification System - Complete Deployment Guide

## 🎯 System Overview

Your new notification system implements all the Norwegian acceptance criteria:

### ✅ A. Database
- **User Profiles Table**: `user_preferences` (user_id, email, preferences JSON)
- **Scraped Times Table**: `scraped_times` (time_id, date, spots_available, created_at)
- **Sent Notifications Table**: `sent_notifications` (notification_id, user_id, time_id, type, sent_at)

### ✅ B. Daily Email Reports (Morning Reports)
- **Cron Job**: Runs daily at 07:00 UTC
- **Personalized**: Fetches matching times for each user's preferences
- **Smart**: Only sends emails if there are matching times
- **Tracked**: Records all sent reports to prevent duplicates

### ✅ C. New Availability Notifications
- **Frequency**: Runs every 10 minutes
- **Smart Detection**: Finds times not previously notified to each user
- **Immediate**: Sends email for each matching new availability
- **Duplicate Prevention**: Uses database tracking to avoid repeat notifications

### ✅ D. Email Content
- **Personalized**: User's name and preferences-based content
- **Norwegian Language**: All templates in Norwegian
- **Clear Format**: Simple, concise plain text emails
- **Proper Headers**: Configured sender and reply-to addresses

### ✅ E. Robustness
- **Error Handling**: Graceful failures with logging
- **Service Resilience**: Continues with next user if one fails
- **Email Service Tolerance**: Logs errors without crashing
- **No Duplicates**: Database-enforced uniqueness constraints

### ✅ F. Operations
- **Render Background Worker**: Dedicated service for notifications
- **Environment Variables**: DATABASE_URL, EMAIL_API_KEY configuration
- **Logging**: All output to stdout/stderr for Render visibility

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Golf Monitor  │───▶│   PostgreSQL     │◀───│  Notification       │
│   (Local/Cloud) │    │   Database       │    │  Worker (Render)    │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                              │                           │
                              ▼                           ▼
                    ┌──────────────────┐         ┌─────────────────┐
                    │  User Profiles   │         │  Email Service  │
                    │  (Streamlit)     │         │  (SMTP/Gmail)   │
                    └──────────────────┘         └─────────────────┘
```

## 🚀 Deployment Steps

### Step 1: Update Database Schema

Your PostgreSQL database will automatically create the new tables when you deploy. The system includes:

- `scraped_times` - Stores all golf availability data
- `sent_notifications` - Tracks what notifications have been sent
- Enhanced `user_preferences` - Links to notification tracking

### Step 2: Deploy Notification Worker on Render

1. **Create Background Worker Service**:
   ```bash
   Service Type: Background Worker
   Name: golf-notification-worker
   Build Command: pip install -r requirements.txt
   Start Command: bash render_worker_start.sh
   ```

2. **Environment Variables**:
   ```bash
   # Database (link your existing PostgreSQL database)
   DATABASE_URL=postgresql://user:password@host:port/database
   
   # Email Configuration (Gmail recommended)
   EMAIL_USER=your-email@gmail.com
   EMAIL_PASSWORD=your-gmail-app-password
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   FROM_EMAIL=your-email@gmail.com
   REPLY_TO_EMAIL=your-email@gmail.com
   ```

3. **Connect Database**:
   - Link your existing `golf-availability-db` PostgreSQL database
   - Render will automatically provide the `DATABASE_URL`

### Step 3: Configure Email Service

**For Gmail (Recommended)**:
1. Enable 2-Factor Authentication on your Gmail account
2. Generate an **App Password** (not your regular password)
3. Use the App Password as `EMAIL_PASSWORD`

**For Other Providers**:
- Update `SMTP_SERVER` and `SMTP_PORT` accordingly
- Ensure the email provider supports SMTP

### Step 4: Update Golf Monitor Integration

Your existing golf monitoring system has been enhanced to save data to the database:

```python
# This is now automatically handled in golf_availability_monitor.py
# The system will save scraped data for the notification service
```

### Step 5: Test the System

1. **Deploy the notification worker**
2. **Check worker logs** for successful startup
3. **Add test users** via your Streamlit app
4. **Run golf monitor** to populate scraped data
5. **Wait for notifications** (daily at 07:00 UTC, new availability every 10 minutes)

## 📧 Email Templates

### Daily Report (Norwegian)
```
Hei [User Name]!

Her er din daglige oversikt over tilgjengelige golftider som matcher dine preferanser:

🏌️ Oslo Golf Club:
  📅 I dag (2024-01-15):
    ⏰ 09:00 - 4 plasser
    ⏰ 14:00 - 2 plasser

Lykke til med å booke! 🍀

Mvh,
Golf Availability Monitor
```

### New Availability Alert (Norwegian)
```
Hei [User Name]!

Vi har funnet 3 nye golftider som matcher dine preferanser:

🏌️ Bergen Golf Course:
  📅 I dag kl. 15:30 - 2 plasser
  📅 Fredag 19.01 kl. 09:00 - 4 plasser

⚡ Disse tidene er nylig blitt tilgjengelige, så vær rask med å booke!

Lykke til! 🍀

Mvh,
Golf Availability Monitor
```

## 🔧 Configuration

### Notification Timing
- **Daily Reports**: 07:00 UTC (08:00 CET in winter, 09:00 CEST in summer)
- **New Availability**: Every 10 minutes
- **Data Retention**: Configurable (default 30 days)

### User Preferences Integration
The system automatically uses existing user preferences:
- `selected_courses` - Which courses to monitor
- `time_slots` - Preferred time windows
- `min_players` - Minimum group size
- `days_ahead` - How far in advance to look

### Email Personalization
Each user receives emails customized to their:
- Name and email address
- Course preferences
- Time slot preferences
- Minimum player requirements

## 🐛 Troubleshooting

### Common Issues

1. **Worker Won't Start**
   - Check all environment variables are set
   - Verify database connection string
   - Check email credentials

2. **No Emails Sent**
   - Verify users exist in database
   - Check scraped data is being populated
   - Verify email credentials and SMTP settings

3. **Duplicate Emails**
   - System prevents duplicates automatically
   - Check database constraints are working

4. **Missing Notifications**
   - Check user preferences match available courses
   - Verify golf monitor is running and populating data
   - Check notification history in database

### Monitoring Queries

```sql
-- Check recent notifications
SELECT * FROM sent_notifications ORDER BY sent_at DESC LIMIT 20;

-- Daily notification stats
SELECT 
    DATE(sent_at) as date,
    notification_type,
    COUNT(*) as count
FROM sent_notifications 
WHERE sent_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(sent_at), notification_type;

-- User activity
SELECT 
    user_email,
    COUNT(*) as notifications_received,
    MAX(sent_at) as last_notification
FROM sent_notifications 
GROUP BY user_email;
```

## 📊 System Health Checks

### Database Health
```python
# Test database connection
python -c "from streamlit_app.postgresql_manager import get_db_manager; print(get_db_manager().health_check())"
```

### Email Service Health
```python
# Test email sending
python -c "from notification_service import EmailService; EmailService().send_email('test@example.com', 'Test', 'Test message')"
```

### Data Ingestion Test
```python
# Test data ingestion
python data_ingestion_service.py --test
```

## 🎉 Success Criteria

Your system is working correctly when:

1. ✅ **Daily reports sent** at 07:00 UTC to users with matching availability
2. ✅ **New availability notifications** sent within 10 minutes of data updates
3. ✅ **No duplicate notifications** for the same time slot to the same user
4. ✅ **Norwegian email content** with proper formatting
5. ✅ **Error handling** logs issues without crashing
6. ✅ **Database tracking** records all sent notifications
7. ✅ **User preferences** correctly filter notifications

## 🚀 Go Live!

1. **Deploy notification worker** to Render
2. **Configure email credentials**
3. **Link PostgreSQL database**
4. **Monitor logs** for successful startup
5. **Test with a few users** first
6. **Scale up** to all users

Your personalized golf notification system is now ready to keep your users informed of available tee times! 🏌️⛳
