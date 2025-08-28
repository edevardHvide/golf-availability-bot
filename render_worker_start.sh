#!/bin/bash

# Render Background Worker Start Script for Golf Notification Service
# This script runs the notification service as a background worker on Render

echo "🚀 Starting Golf Notification Worker on Render..."

# Set Python path to include current directory
export PYTHONPATH="${PYTHONPATH}:."

# Ensure we have required environment variables
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL environment variable is required"
    exit 1
fi

if [ -z "$SMTP_USER" ]; then
    echo "❌ ERROR: SMTP_USER environment variable is required"
    exit 1
fi

if [ -z "$SMTP_PASS" ]; then
    echo "❌ ERROR: SMTP_PASS environment variable is required"
    exit 1
fi

if [ -z "$EMAIL_ENABLED" ]; then
    echo "❌ ERROR: EMAIL_ENABLED environment variable is required (set to 'true')"
    exit 1
fi

echo "✅ Environment variables configured"
echo "📧 Email service: $SMTP_USER"
echo "🐘 Database: $(echo $DATABASE_URL | sed 's/:[^@]*@/:***@/')"

# Install any additional dependencies if needed
echo "📦 Installing dependencies..."
pip install --no-cache-dir -r requirements.txt

# Run the notification service
echo "🔔 Starting notification worker..."
python notification_service.py
