# How to Connect PostgreSQL Database in Render

## 📍 You're Here: API Service Database Connection

After you've created your API service with the build/start commands, you need to connect your existing PostgreSQL database.

## 🔗 Step-by-Step Database Connection

### Method 1: During API Service Creation

1. **While creating the API service**, scroll down to the **"Environment"** section
2. **Click "Add Database"** button
3. **Select your existing database**: `golf-availability-db`
4. **Click "Connect"**
5. ✅ Render automatically adds `DATABASE_URL` environment variable

### Method 2: After API Service is Created

1. **Go to your API service dashboard**
2. **Click "Environment" tab** (in the left sidebar)
3. **Scroll down to "Databases" section**
4. **Click "Connect Database"** button
5. **Select**: `golf-availability-db` from the dropdown
6. **Click "Connect Database"**
7. ✅ `DATABASE_URL` appears automatically in environment variables

## 🖼️ Visual Guide

```
Render Dashboard → Your API Service → Environment Tab
                                        ↓
                              [Environment Variables]
                              [Databases] ← Click here
                                        ↓
                              [Connect Database] ← Click this button
                                        ↓
                              Select: golf-availability-db
                                        ↓
                              [Connect Database] ← Confirm
                                        ↓
                              ✅ DATABASE_URL automatically added
```

## 🎯 What Happens When You Connect

1. **Render adds `DATABASE_URL`** environment variable automatically
2. **Format**: `postgresql://username:password@host:port/database`
3. **Your API service can now access the database**
4. **No manual configuration needed** - it just works!

## 🔍 Verify Connection

After connecting, you should see:

**In Environment Variables section:**
```
DATABASE_URL = postgresql://golfdb_li04_user:***@***:5432/golfdb_li04
API_MODE = production
DATA_STORAGE_MODE = postgresql
```

## 🚨 Important Notes

- **Connect the database BEFORE deploying** the API service
- **The DATABASE_URL is automatic** - don't add it manually
- **Your database service ID**: `dpg-d2mne7ogjchc73cs6650-a`
- **Database name in dropdown**: `golf-availability-db`

## 🎉 You're Done!

Once connected:
1. ✅ DATABASE_URL is automatically available to your API service
2. ✅ Your `postgresql_manager.py` will use this URL
3. ✅ No additional configuration needed
4. ✅ Deploy your API service and it will connect to PostgreSQL

The connection is secure, automatic, and managed by Render!
