# 🔧 Render Background Worker - Environment Variables

## 📧 Email Configuration (Same as Golf Monitor)

The notification system uses the **same email environment variables** as your existing golf monitoring system.

### Required Variables:

```bash
# Enable email notifications
EMAIL_ENABLED=true

# SMTP Configuration (Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SSL=false
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-gmail-app-password

# Email Headers
EMAIL_FROM=your-email@gmail.com
```

### Optional Variables:

```bash
# Additional SMTP settings
SMTP_SSL=true  # Use if you want SSL instead of STARTTLS
EMAIL_TO=fallback-recipient@example.com  # Fallback recipient (not used for notifications)
```

## 🐘 Database Configuration

```bash
# PostgreSQL Connection (with SSL)
DATABASE_URL=postgresql://golfdb_li04_user:5ad86816cc79cb251b799165fa6cc37c@dpg-d2mne7ogjchc73cs6650-a.oregon-postgres.render.com:5432/golfdb_li04?sslmode=require
```

## 🚀 Complete Render Environment Variables

Copy and paste these into your Render Background Worker:

```bash
# Database
DATABASE_URL=postgresql://golfdb_li04_user:5ad86816cc79cb251b799165fa6cc37c@dpg-d2mne7ogjchc73cs6650-a.oregon-postgres.render.com:5432/golfdb_li04?sslmode=require

# Email Service (Gmail)
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SSL=false
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-16-character-gmail-app-password
EMAIL_FROM=your-email@gmail.com
```

## 📱 Gmail App Password Setup

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to [Google Account Settings](https://myaccount.google.com/)
   - Security → 2-Step Verification → App Passwords
   - Select "Mail" and generate password
3. **Use the 16-character app password** (not your regular Gmail password)

## ✅ Environment Variables Summary

| Variable | Example | Description |
|----------|---------|-------------|
| `EMAIL_ENABLED` | `true` | Enable email notifications |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_SSL` | `false` | Use SSL (false = use STARTTLS) |
| `SMTP_USER` | `your-email@gmail.com` | Your Gmail address |
| `SMTP_PASS` | `abcdefghijklmnop` | 16-character Gmail App Password |
| `EMAIL_FROM` | `your-email@gmail.com` | From address for emails |
| `DATABASE_URL` | `postgresql://...?sslmode=require` | PostgreSQL connection string |

## 🔍 Verification

After setting these variables, your Render worker should start successfully:

```
🚀 Starting Golf Notification Worker on Render...
✅ Environment variables configured
📧 Email service: your-email@gmail.com
🐘 Database: postgresql://golfdb_li04_user:***@dpg-...
📦 Installing dependencies...
🔔 Notification service initialized
```

## 🎯 Why These Variables?

These match exactly with your existing `golf_utils.py` email system, so:
- ✅ **Consistent configuration** across all services
- ✅ **Same Gmail setup** you already have
- ✅ **No duplicate email settings**
- ✅ **Easy maintenance**

The notification worker will now use the same email configuration as your golf monitoring system! 📧⛳
