# Render Deployment - Two Service Architecture with PostgreSQL

This setup uses two separate Render Web Services plus a PostgreSQL database for maximum stability and data reliability.

## 🏗️ Architecture Overview

```
Three-Component Render Architecture
├── 🐘 PostgreSQL Database (golf-availability-db)
│   ├── User preferences and profiles
│   ├── Monitoring session data
│   └── System status logs
│
├── 📡 API Service (api-golf-monitor.onrender.com)
│   ├── FastAPI backend
│   ├── Connects to PostgreSQL
│   └── All API endpoints
│
└── 🎨 UI Service (ui-golf-monitor.onrender.com)
    ├── Streamlit app only
    ├── Connects to API service
    └── User interface
```

## 🚀 Deployment Steps

### Step 0: Create PostgreSQL Database (COMPLETED ✅)

You've already created:
- **Service ID**: `dpg-d2mne7ogjchc73cs6650-a`
- **Name**: `golf-availability-db`
- **Database**: `golfdb_li04`
- **Username**: `golfdb_li04_user`
- **Port**: `5432`

Render provides the `DATABASE_URL` environment variable automatically.

### Step 1: Deploy API Service

1. **Go to Render Dashboard**
   - Click "New +" → "Web Service"
   - Connect your repository

2. **API Service Configuration:**
   ```
   Name: golf-monitor-api
   Environment: Python 3
   Build Command: pip install -r requirements.txt && pip install -r streamlit_app/requirements.txt
   Start Command: cd streamlit_app && python render_api_server_postgresql.py
   ```

3. **Environment Variables:**
   ```
   DATABASE_URL=<automatically provided by Render>
   API_MODE=production
   DATA_STORAGE_MODE=postgresql
   ```

4. **Connect Database:**
   - In service settings, go to "Environment"
   - Add the PostgreSQL database you created
   - Render will automatically add DATABASE_URL

### Step 2: Deploy UI Service

1. **Create Second Web Service**
   - Same repository, different configuration

2. **UI Service Configuration:**
   ```
   Name: golf-monitor-ui  
   Environment: Python 3
   Build Command: pip install -r streamlit_app/requirements.txt
   Start Command: cd streamlit_app && streamlit run render_streamlit_app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true
   ```

3. **Environment Variables:**
   ```
   API_BASE_URL=https://golf-monitor-api.onrender.com
   ```

## 🌐 Service URLs

- **UI**: https://golf-monitor-ui.onrender.com
- **API**: https://golf-monitor-api.onrender.com  
- **API Docs**: https://golf-monitor-api.onrender.com/docs
- **Database Health**: https://golf-monitor-api.onrender.com/api/database/health

## 🐘 PostgreSQL Benefits

- **🔒 Data Reliability**: ACID compliance, transactions, backups
- **📈 Scalability**: Handle thousands of users and monitoring sessions
- **🔍 Query Power**: Complex queries, JSON indexing, full-text search
- **🛡️ Security**: Built-in authentication, encryption, access control
- **📊 Analytics**: Rich querying for usage analytics and reporting
- **🔄 Backup & Recovery**: Automatic backups, point-in-time recovery

## ✅ Benefits

- **🔒 Stability**: Services can restart independently
- **💾 Data Persistence**: PostgreSQL ensures no data loss
- **📊 Monitoring**: Separate logs and metrics per service
- **🔧 Maintenance**: Update services separately  
- **⚡ Performance**: Database optimized for concurrent access
- **💰 Cost**: Scale services and database independently
- **🛠️ Development**: Separate development and testing environments
