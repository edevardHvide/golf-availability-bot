# Render Background Worker Setup for Golf Notifications

## 🔔 Notification Service Architecture

This setup creates a dedicated background worker on Render that handles:

1. **Daily Morning Reports** (07:00 UTC)
   - Sends personalized email summaries to all users
   - Includes all available times matching user preferences
   - Only sends if there are matching times

2. **New Availability Notifications** (Every 10 minutes)
   - Checks for newly scraped times not previously notified
   - Sends immediate notifications for new matches
   - Prevents duplicate notifications using database tracking

## 🚀 Render Deployment Steps

### 1. Create Background Worker Service

1. **Go to Render Dashboard** → **New** → **Background Worker**
2. **Connect your Git repository**
3. **Configure the service:**
   - **Name**: `golf-notification-worker`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `bash render_worker_start.sh`

### 2. Environment Variables

Add these environment variables to your worker service:

#### Required Variables:
```bash
# Database (connect your existing PostgreSQL database)
DATABASE_URL=postgresql://user:password@host:port/database

# Email Configuration
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SSL=false
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
EMAIL_FROM=your-email@gmail.com
```

#### Gmail Setup:
1. Enable 2-Factor Authentication on your Gmail account
2. Generate an **App Password** (not your regular password)
3. Use the App Password as `EMAIL_PASSWORD`

### 3. Connect Database

**Option A: Link Existing Database**
1. Go to worker service → **Environment** → **Add Database**
2. Select your existing `golf-availability-db`
3. Render automatically adds `DATABASE_URL`

**Option B: Manual Configuration**
1. Copy the DATABASE_URL from your existing database service
2. Add it as an environment variable to the worker

### 4. Deploy and Monitor

1. **Deploy** the service
2. **Check logs** to ensure it starts correctly
3. **Monitor** the worker in Render dashboard

## 📧 Email Templates

The notification service includes Norwegian email templates:

### Daily Report Example:
```
Hei John!

Her er din daglige oversikt over tilgjengelige golftider som matcher dine preferanser:

🏌️ Oslo Golf Club:
  📅 I dag (2024-01-15):
    ⏰ 09:00 - 4 plasser
    ⏰ 14:00 - 2 plasser

🏌️ Bergen Golf Course:
  📅 I morgen (2024-01-16):
    ⏰ 10:00 - 3 plasser

Lykke til med å booke! 🍀
```

### New Availability Example:
```
Hei John!

Vi har funnet 2 nye golftider som matcher dine preferanser:

🏌️ Oslo Golf Club:
  📅 I dag kl. 15:30 - 2 plasser
  📅 Fredag 19.01 kl. 09:00 - 4 plasser

⚡ Disse tidene er nylig blitt tilgjengelige, så vær rask med å booke!

Lykke til! 🍀
```

## 🔧 Configuration Options

### Timing Configuration

The worker runs continuously and checks:
- **Daily reports**: Every minute, triggers at 07:00 UTC
- **New notifications**: Every minute, triggers every 10 minutes

### Email Settings

Customize email behavior with environment variables:
```bash
# SMTP Configuration (defaults shown)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Email Headers
FROM_EMAIL=your-email@gmail.com
REPLY_TO_EMAIL=your-email@gmail.com
```

### Database Integration

The worker automatically:
- Reads user preferences from `user_preferences` table
- Queries scraped times from `scraped_times` table
- Tracks sent notifications in `sent_notifications` table
- Prevents duplicate notifications

## 🐛 Troubleshooting

### Worker Won't Start

1. **Check environment variables** - all required vars must be set
2. **Check database connection** - ensure DATABASE_URL is correct
3. **Check email credentials** - verify Gmail app password
4. **Check logs** in Render dashboard

### No Emails Being Sent

1. **Check user preferences** - users must be configured in database
2. **Check scraped data** - ensure golf monitor is populating database
3. **Check email logs** - look for SMTP errors in worker logs
4. **Test email credentials** - verify outside of application

### Duplicate Notifications

The system prevents duplicates by:
- Recording each sent notification in database
- Checking against sent history before sending
- Using composite keys (user + course + date + time)

## 📊 Monitoring

### Logs to Watch For:
```
✅ Daily reports completed: 5/10 sent successfully
🔔 New availability check completed: 3 notifications sent
❌ Failed to send email to user@example.com: SMTP error
```

### Database Queries for Monitoring:
```sql
-- Check recent notifications
SELECT * FROM sent_notifications ORDER BY sent_at DESC LIMIT 10;

-- Count notifications by type
SELECT notification_type, COUNT(*) FROM sent_notifications 
WHERE sent_at >= NOW() - INTERVAL '24 hours' 
GROUP BY notification_type;

-- Check user activity
SELECT user_email, COUNT(*) as notification_count 
FROM sent_notifications 
WHERE sent_at >= NOW() - INTERVAL '7 days'
GROUP BY user_email;
```

## 🚀 Ready to Deploy!

1. ✅ Create background worker service on Render
2. ✅ Set all required environment variables
3. ✅ Connect to your PostgreSQL database
4. ✅ Deploy and monitor logs
5. ✅ Test with a few users first

The notification system will automatically start sending personalized emails based on your users' preferences and the availability data from your golf monitoring system.
