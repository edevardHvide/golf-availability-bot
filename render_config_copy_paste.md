# Render Configuration Copy-Paste Guide

## API Service Configuration

**Service Name:** `golf-availability-api`

**Build Command:**
```
pip install -r requirements.txt && pip install -r streamlit_app/requirements.txt
```

**Start Command:**
```
cd streamlit_app && python render_api_server_postgresql.py
```

**Environment Variables:**
```
API_MODE=production
DATA_STORAGE_MODE=postgresql
```

**Database:** Connect `golf-availability-db` (adds DATABASE_URL automatically)

---

## UI Service Configuration

**Service Name:** `golf-availability-ui`

**Build Command:**
```
pip install -r streamlit_app/requirements.txt
```

**Start Command:**
```
cd streamlit_app && streamlit run render_streamlit_app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true
```

**Environment Variables:**
```
API_BASE_URL=https://golf-availability-api.onrender.com
```
(Replace with your actual API service URL)

---

## Test URLs

After deployment, test these URLs:

**API Health:**
```
https://golf-availability-api.onrender.com/health
```

**Database Health:**
```
https://golf-availability-api.onrender.com/api/database/health
```

**UI Application:**
```
https://golf-availability-ui.onrender.com
```

**API Documentation:**
```
https://golf-availability-api.onrender.com/docs
```
