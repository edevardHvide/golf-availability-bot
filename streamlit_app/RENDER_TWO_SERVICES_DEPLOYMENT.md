# Render Two-Service Deployment Guide

## Overview

This deployment strategy uses two separate Render Web Services for maximum stability:

1. **API Service** (`golf-availability-api`) - FastAPI backend
2. **UI Service** (`golf-availability-ui`) - Streamlit frontend

## Architecture Benefits

- ✅ **Stability**: Each service can restart independently
- ✅ **Scaling**: Services can be scaled separately
- ✅ **Debugging**: Easier to isolate issues
- ✅ **CORS**: Simplified cross-origin configuration
- ✅ **Subdomain**: Clean URL structure (`api.` and `ui.`)

## Deployment Steps

### Step 1: Deploy API Service

1. **Create Web Service** in Render Dashboard
   - Name: `golf-availability-api`
   - Repository: Connect to your GitHub repo
   - Branch: `main`

2. **Build & Start Commands**
   ```bash
   # Build Command
   pip install -r requirements.txt
   
   # Start Command
   python streamlit_app/render_api_server.py
   ```

3. **Environment Variables**
   ```
   PYTHON_VERSION=3.11.0
   PORT=10000
   DATA_STORAGE_MODE=render
   API_MODE=production
   ```

4. **Deploy** and wait for completion
   - Note the URL (e.g., `https://golf-availability-api.onrender.com`)

### Step 2: Deploy UI Service

1. **Create Web Service** in Render Dashboard
   - Name: `golf-availability-ui`
   - Repository: Same GitHub repo
   - Branch: `main`

2. **Build & Start Commands**
   ```bash
   # Build Command
   pip install -r streamlit_app/requirements.txt
   
   # Start Command
   streamlit run streamlit_app/render_streamlit_app.py --server.port=$PORT --server.address=0.0.0.0
   ```

3. **Environment Variables**
   ```
   PYTHON_VERSION=3.11.0
   PORT=10000
   API_BASE_URL=https://golf-availability-api.onrender.com
   ```
   **⚠️ Important**: Replace with your actual API service URL from Step 1

4. **Deploy**

### Step 3: Verify Deployment

1. **Check API Service**
   - Visit: `https://your-api-service.onrender.com/health`
   - Should return: `{"status": "healthy"}`

2. **Check UI Service**
   - Visit: `https://your-ui-service.onrender.com`
   - Sidebar should show "🟢 API Connected"

3. **Test Integration**
   - Create a test profile
   - Verify data saves successfully
   - Check system status displays correctly

## Service URLs

After deployment, you'll have:
- **API**: `https://golf-availability-api.onrender.com`
- **UI**: `https://golf-availability-ui.onrender.com`

## Troubleshooting

### API Service Issues

1. **Health Check Fails**
   ```bash
   curl https://your-api-service.onrender.com/health
   ```

2. **Check Logs** in Render Dashboard
   - Look for Python import errors
   - Verify all dependencies installed

3. **Common Issues**
   - Missing dependencies in `requirements.txt`
   - Port binding issues (ensure using `$PORT`)
   - File permissions for data storage

### UI Service Issues

1. **API Connection Failed**
   - Verify `API_BASE_URL` environment variable
   - Check API service is running and accessible
   - Test API URL directly

2. **Streamlit Won't Start**
   - Check Streamlit version compatibility
   - Verify port binding configuration

3. **CORS Issues**
   - API service includes CORS middleware
   - Should allow all origins in production

### Common Solutions

1. **Environment Variables**
   ```bash
   # Check in Render Dashboard
   # API Service needs: PORT, DATA_STORAGE_MODE, API_MODE
   # UI Service needs: PORT, API_BASE_URL
   ```

2. **Dependencies**
   ```bash
   # Ensure both services have correct requirements.txt
   # API uses root requirements.txt
   # UI uses streamlit_app/requirements.txt
   ```

3. **Data Persistence**
   ```bash
   # API service creates /opt/render/project/src/data
   # Files persist between restarts
   # Check disk usage in Render dashboard
   ```

## Monitoring

### Health Endpoints

- **API Health**: `GET /health`
- **API Status**: `GET /api/status`
- **API Preferences**: `GET /api/preferences`

### Performance

- **Cold Starts**: Both services may have 30-60s cold start
- **Memory**: Monitor usage in Render dashboard
- **Response Times**: API typically <1s, UI <3s

### Logs

Check both services in Render Dashboard:
1. **Build Logs**: Dependency installation
2. **Runtime Logs**: Application errors and info
3. **Health Checks**: Automatic monitoring

## Scaling Considerations

- **Free Tier**: Both services sleep after 15min inactivity
- **Paid Tier**: Always-on, better performance
- **Database**: Consider external database for high usage

## Security

- **Environment Variables**: Sensitive data only in env vars
- **HTTPS**: Automatic with Render
- **CORS**: Configured for cross-service communication

## Updates

To update the deployment:
1. Push changes to GitHub
2. Render auto-deploys from `main` branch
3. Both services update independently
4. Zero-downtime if properly configured

## Cost Optimization

- **Free Tier**: $0/month (with sleep)
- **Paid Tier**: ~$14/month per service
- **Combined**: Two services more expensive but more reliable
- **Alternative**: Consider upgrading to unified service if cost is concern
