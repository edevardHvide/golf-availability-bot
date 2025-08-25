# Render.com Configuration for Golf Availability Monitor

## 🔧 **Render Dashboard Settings**

### **Service Configuration:**
- **Service Type:** Web Service
- **Name:** `golf-availability-monitor` (or your preferred name)
- **Runtime:** Python 3
- **Region:** Oregon (US West) or Frankfurt (Europe)
- **Branch:** main
- **Root Directory:** (leave empty - uses repository root)

### **Build & Deploy:**

**Build Command:**
```bash
pip install -r requirements.txt && pip install -r streamlit_app/requirements.txt
```

**Start Command:**
```bash
cd streamlit_app && python -m uvicorn api_server:app --host 0.0.0.0 --port $PORT --workers 1 & sleep 3 && streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.enableCORS false --server.enableXsrfProtection false --server.headless true --browser.gatherUsageStats false
```

### **Environment Variables:**

| Key | Value | Notes |
|-----|-------|-------|
| `PYTHON_VERSION` | `3.12.1` | Python version |
| `EMAIL_ENABLED` | `true` | Enable notifications |
| `SMTP_HOST` | `smtp.gmail.com` | Gmail SMTP |
| `SMTP_PORT` | `587` | Gmail port |
| `SMTP_USER` | `your-email@gmail.com` | Your Gmail |
| `SMTP_PASS` | `your-app-password` | Gmail app password |
| `EMAIL_FROM` | `your-email@gmail.com` | From address |

### **Health Check:**
- **Health Check Path:** `/health`

## 🎯 **Deployment URLs**

After deployment, your service will be available at:

- **Main App:** `https://golf-availability-monitor.onrender.com/`
- **API Health:** `https://golf-availability-monitor.onrender.com/health`
- **User Preferences:** `https://golf-availability-monitor.onrender.com/api/preferences`
- **Golf Courses:** `https://golf-availability-monitor.onrender.com/api/courses`

## ✅ **Verification Steps**

1. **Service Status:** Green "Live" indicator in Render dashboard
2. **Logs Show:** Both FastAPI and Streamlit starting successfully
3. **Health Check:** API responds at `/health` endpoint
4. **Main App:** Streamlit interface loads and shows golf courses

## 🐛 **Common Issues & Solutions**

### **Build Fails:**
```
Check: requirements.txt files exist and have correct dependencies
Solution: Verify both root and streamlit_app requirements.txt
```

### **Service Won't Start:**
```
Check: Logs for port conflicts or import errors
Solution: Verify start command syntax and file paths
```

### **502 Bad Gateway:**
```
Check: Service is listening on $PORT (provided by Render)
Solution: Ensure uvicorn uses --port $PORT
```

### **Streamlit Not Loading:**
```
Check: Both FastAPI and Streamlit processes are running
Solution: Verify start command runs both services
```

## 📊 **Resource Usage**

**Free Tier:**
- 512 MB RAM
- 0.1 CPU
- Sleeps after 15 minutes of inactivity
- Suitable for testing and small usage

**Paid Starter ($7/month):**
- 512 MB RAM
- 0.5 CPU
- Always-on service
- Recommended for production use

## 🔄 **Auto-Deploy Setup**

Render automatically deploys when you push to your connected branch:

1. **Connected Branch:** main
2. **Auto-Deploy:** Enabled by default
3. **Deploy Trigger:** Any push to main branch
4. **Build Time:** ~2-5 minutes typically
