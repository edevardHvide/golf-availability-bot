# Local vs Render Command Differences

## 🏠 For Local Testing

**PowerShell:**
```powershell
$env:API_BASE_URL = "http://localhost:8000"
streamlit run render_streamlit_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
```

**Command Prompt:**
```cmd
set API_BASE_URL=http://localhost:8000
streamlit run render_streamlit_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
```

## ☁️ For Render Deployment

**Start Command (exactly as in config):**
```bash
cd streamlit_app && streamlit run render_streamlit_app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true
```

## 🔍 The Difference

- **Local**: `--server.port 8501` (specific port number)
- **Render**: `--server.port $PORT` (Render provides the PORT variable)

## 🧪 To Test Locally

1. **First, start your API server:**
```powershell
# In one terminal
C:/Users/pt1004/git/golf-availability-bot/.venv/Scripts/python.exe streamlit_app/render_api_server_postgresql.py
```

2. **Then start Streamlit (in another terminal):**
```powershell
# In second terminal
$env:API_BASE_URL = "http://localhost:8000"
streamlit run render_streamlit_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
```

3. **Visit:** http://localhost:8501

## ✅ Your Render Configuration is Correct

The command in your config file is perfect for Render deployment - don't change it! The issue is just that `$PORT` isn't set in your local environment.
