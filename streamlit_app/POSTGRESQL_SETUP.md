# Getting Your PostgreSQL Connection String from Render

## 🐘 Your PostgreSQL Database

You've successfully created a PostgreSQL database on Render:

- **Service ID**: `dpg-d2mne7ogjchc73cs6650-a`
- **Name**: `golf-availability-db`
- **Database**: `golfdb_li04`
- **Username**: `golfdb_li04_user`
- **Port**: `5432`

## 🔑 Getting the DATABASE_URL

### From Render Dashboard:

1. **Go to Render Dashboard** → **Database Services**
2. **Click on `golf-availability-db`**
3. **Go to "Info" tab**
4. **Copy the "External Database URL"** or "Internal Database URL"

The URL will look like:
```
postgresql://golfdb_li04_user:password@hostname:5432/golfdb_li04
```

### For Local Testing:

Set the environment variable:

**Windows (PowerShell):**
```powershell
$env:DATABASE_URL = "postgresql://golfdb_li04_user:your_password@hostname:5432/golfdb_li04"
```

**Windows (Command Prompt):**
```cmd
set DATABASE_URL=postgresql://golfdb_li04_user:your_password@hostname:5432/golfdb_li04
```

**Linux/Mac:**
```bash
export DATABASE_URL="postgresql://golfdb_li04_user:your_password@hostname:5432/golfdb_li04"
```

## 🧪 Test Connection

Run the test script:
```bash
python streamlit_app/test_postgresql.py
```

## 📝 For Render Deployment

When you deploy your API service to Render:

1. **Environment Variables** → **Add Environment Variable**
2. **Key**: `DATABASE_URL`
3. **Value**: [Copy from your database info page]

Or better yet, **connect the database directly** in Render:
1. Go to your API service settings
2. **Environment** → **Add Database**
3. Select your `golf-availability-db`
4. Render automatically adds the `DATABASE_URL`

## 🔒 Security Note

Never commit the DATABASE_URL to Git! Always use environment variables.

## 🚀 Ready to Deploy

Once you have the DATABASE_URL:

1. **Test locally** with the test script
2. **Deploy API service** with PostgreSQL connection
3. **Deploy UI service** connecting to API
4. **Enjoy reliable data persistence!**

The PostgreSQL integration will give you:
- 🔒 **ACID compliance** and data safety
- 📈 **Scalability** for many users
- 🔍 **Rich querying** capabilities
- 🛡️ **Built-in backups** and recovery
- 📊 **Analytics** and reporting features
