# 🔍 Where to Find Database Connection in Render

## 🎯 During Web Service Creation

When you're creating your API Web Service, look for this section:

### Method 1: In the Creation Form
1. **Fill in basic info** (name, repo, build/start commands)
2. **Scroll down** to find **"Environment Variables"** section
3. **Below Environment Variables**, look for **"Add Database"** button or **"Databases"** section
4. **Click "Add Database"**
5. **Select**: `golf-availability-db`

### Method 2: If You Miss It During Creation
1. **Create the Web Service** without database first
2. **Go to your service dashboard** 
3. **Click "Environment" tab** (left sidebar)
4. **Scroll down** past environment variables
5. **Look for "Databases" section**
6. **Click "Connect Database"** button

## 🖼️ Visual Clues to Look For

### During Creation:
```
Create Web Service Form
├── Service Name: golf-availability-api
├── Repository: golf-availability-bot  
├── Build Command: pip install...
├── Start Command: cd streamlit_app...
├── Environment Variables:
│   ├── API_MODE = production
│   └── DATA_STORAGE_MODE = postgresql
└── Databases: ← LOOK FOR THIS SECTION
    └── [Add Database] ← CLICK HERE
```

### After Creation:
```
Service Dashboard
├── Overview
├── Environment ← CLICK THIS TAB
│   ├── Environment Variables
│   │   ├── API_MODE = production
│   │   └── DATA_STORAGE_MODE = postgresql
│   └── Databases ← SCROLL DOWN TO FIND THIS
│       └── [Connect Database] ← CLICK HERE
└── Logs
```

## 🔍 Can't Find "Databases" Section?

### Try These Steps:
1. **Make sure you're in the RIGHT service** (API service, not database service)
2. **Refresh the page** - sometimes it takes a moment to load
3. **Check you're on "Environment" tab** (not "Settings" or "Overview")
4. **Scroll all the way down** - it's usually at the bottom
5. **Look for different wordings**:
   - "Add Database"
   - "Connect Database" 
   - "Link Database"
   - "Databases"

## 🚨 Still Can't Find It?

### Alternative Method:
1. **Go to your PostgreSQL database** (`golf-availability-db`)
2. **Look for "Connected Services"** or "Connections" tab
3. **Click "Connect to Service"**
4. **Select your API service**: `golf-availability-api`

## 📱 Mobile/Small Screen?

If you're on a small screen, the database section might be:
- **Hidden in a collapsible menu**
- **In a different tab** called "Resources" or "Add-ons"
- **Accessible via a "+" button**

## 🎯 What You're Looking For

You want to see:
```
✅ DATABASE_URL = postgresql://golfdb_li04_user:***@***:5432/golfdb_li04
```

This should appear automatically in your environment variables after connecting!

## 🆘 Last Resort

If you absolutely can't find the database connection:
1. **Contact Render Support** (they're very helpful!)
2. **Or manually add DATABASE_URL** as an environment variable
3. **Get the connection string** from your database's "Info" tab

The connection should be automatic though - keep looking for that "Databases" section! 🔍
