# 🚀 Render.com Deployment Guide

## 📋 **Pre-Deployment Checklist**

✅ GitHub repository with your code  
✅ Streamlit app in `/streamlit_app/` folder  
✅ FastAPI backend (`api_server.py`)  
✅ Requirements files ready  

---

## 🌐 **Step 1: Create New Web Service on Render**

1. **Go to Render Dashboard:**
   - Visit [https://render.com/](https://render.com/)
   - Sign in with your GitHub account

2. **Create New Web Service:**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository: `golf-availability-bot`
   - Select the repository

3. **Configure Basic Settings:**
   ```
   Name: golf-availability-monitor
   Region: Oregon (US West) or Frankfurt (Europe)
   Branch: main
   Runtime: Python 3
   ```

---

## ⚙️ **Step 2: Configure Build & Start Commands**

### **Build Command:**
```bash
pip install -r streamlit_app/requirements.txt && pip install -r requirements.txt
```

### **WORKING Start Command (Both Services):**
```bash
cd streamlit_app && (python api_server.py &) && sleep 3 && streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false
```

### **Alternative (Streamlit Only):**
```bash
streamlit run streamlit_app/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false
```

### **Simple Fix (Manual Command):**
```bash
cd streamlit_app && python -c "import subprocess; subprocess.Popen(['python', 'api_server.py'])" && sleep 3 && streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false
```

---

## 🔧 **Step 3: Environment Variables**

Add these environment variables in Render dashboard:

| Variable | Value | Description |
|----------|-------|-------------|
| `PYTHON_VERSION` | `3.12.1` | Python version |
| `PORT` | `10000` | Main port (auto-set by Render) |
| `EMAIL_ENABLED` | `true` | Enable email notifications |
| `SMTP_HOST` | `smtp.gmail.com` | Email server |
| `SMTP_PORT` | `587` | Email port |
| `SMTP_USER` | `your-email@gmail.com` | Your email |
| `SMTP_PASS` | `your-app-password` | Gmail app password |
| `EMAIL_FROM` | `your-email@gmail.com` | From email |

---

## 📁 **Step 4: File Structure Check**

Make sure your repository has this structure:
```
golf-availability-bot/
├── streamlit_app/
│   ├── app.py              # Main Streamlit app
│   ├── api_server.py       # FastAPI backend
│   ├── requirements.txt    # Streamlit dependencies
│   └── user_preferences.json
├── requirements.txt        # Main project dependencies
├── golf_club_urls.py      # Golf courses data
├── golf_utils.py          # Email utilities
└── facilities.py          # Course facilities
```

---

## 🎯 **Step 5: Deploy & Test**

1. **Deploy:**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)

2. **Get Your URL:**
   - Your app will be at: `https://golf-availability-monitor.onrender.com`
   - (Replace `golf-availability-monitor` with your chosen name)

3. **Test Endpoints:**
   ```
   Main App: https://your-app.onrender.com/
   API Status: https://your-app.onrender.com/api/health
   Preferences: https://your-app.onrender.com/api/preferences
   Courses: https://your-app.onrender.com/api/courses
   ```

---

## 🔍 **Step 6: Update Local Configuration**

Once deployed, update your local `.env` file:

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with your actual Render URL
API_URL=https://your-actual-app-name.onrender.com
```

---

## 🐛 **Troubleshooting**

### **Common Issues:**

1. **Build Fails:**
   ```bash
   # Check requirements.txt has all dependencies
   # Verify Python version compatibility
   ```

2. **App Won't Start:**
   ```bash
   # Check logs in Render dashboard
   # Verify start command syntax
   ```

3. **API Not Working:**
   ```bash
   # Test: https://your-app.onrender.com/api/health
   # Check CORS settings in api_server.py
   ```

4. **Ports Conflict:**
   ```bash
   # FastAPI: Uses $PORT (from Render)
   # Streamlit: Uses 8501 (internal)
   ```

### **Check Logs:**
- Go to Render dashboard
- Click on your service
- View "Logs" tab for debugging

---

## 📧 **Step 7: Email Configuration**

For Gmail (recommended):

1. **Enable 2-Factor Authentication** on your Google account
2. **Generate App Password:**
   - Google Account → Security → 2-Step Verification → App passwords
   - Select "Mail" and your device
   - Copy the 16-character password

3. **Add to Render Environment Variables:**
   ```
   SMTP_USER=your-email@gmail.com
   SMTP_PASS=abcd-efgh-ijkl-mnop  # The app password
   ```

---

## ✅ **Verification Steps**

After deployment, verify:

1. ✅ **Main app loads:** `https://your-app.onrender.com/`
2. ✅ **API responds:** `https://your-app.onrender.com/api/health`
3. ✅ **Can save profiles:** Use the web interface
4. ✅ **Local monitoring connects:** Run local monitoring with cloud API

---

## 🔄 **Auto-Deploy from GitHub**

Render will automatically redeploy when you:
- Push to the `main` branch
- Make changes to your repository

---

## 💡 **Pro Tips**

1. **Free Tier Limitations:**
   - Apps sleep after 15 minutes of inactivity
   - Takes ~30 seconds to wake up
   - Upgrade to paid plan for always-on service

2. **Custom Domain:**
   - Add your own domain in Render dashboard
   - Configure DNS settings

3. **Monitoring:**
   - Check "Metrics" tab for performance
   - Set up alerts for downtime

---

## 🆘 **Need Help?**

If you encounter issues:

1. **Check Render Logs:** Dashboard → Your Service → Logs
2. **Test Locally First:** Make sure everything works locally
3. **Verify File Paths:** Ensure all imports work
4. **Check Environment Variables:** Verify all are set correctly

---

**Ready to deploy?** Follow the steps above and your golf monitoring system will be live! 🎯
