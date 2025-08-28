# 🏌️ Local Golf Monitor Running Guide

## 🚨 Database Connection Issue Solved!

The golf availability monitor was trying to connect to PostgreSQL, but since you're running locally without a database server, this was causing connection errors.

## ✅ Solution: Use No-Database Mode

I've created scripts that will run the monitor without attempting database connections:

### Windows Batch File (Recommended)
```cmd
run_golf_monitor_no_db.bat
```
Just double-click this file to run the monitor without database issues.

### PowerShell Script
```powershell
.\run_golf_monitor_no_db.ps1
```

### Manual Command Line
```cmd
set DATABASE_ENABLED=false
python golf_availability_monitor.py --local --immediate
```

## 🔧 What These Scripts Do

1. **Set `DATABASE_ENABLED=false`** - Tells the monitor to skip database operations
2. **Use `--local` flag** - Runs in local mode without trying to connect to external APIs
3. **Use `--immediate` flag** - Runs a single check and exits (good for testing)

## 📁 Where Results Are Saved

When running without a database:
- **Availability results** → `availability_cache.json` in the main directory
- **User preferences** → `user_preferences.json` (if any exist)
- **No database errors** → Clean console output

## 🎯 Available Command Line Options

```cmd
python golf_availability_monitor.py --help
```

Common options:
- `--time-window "16:00-18:00"` - Set time range to monitor
- `--players 3` - Minimum players required
- `--days 2` - Number of days ahead to check
- `--interval 300` - Check every 5 minutes (300 seconds)

## 🚀 For Production Use

When you're ready to use the database:
1. **Set up PostgreSQL** locally or use your Render database
2. **Set `DATABASE_ENABLED=true`** (default)
3. **Configure `DATABASE_URL`** environment variable

## 💡 Pro Tips

- **Test first**: Use `--immediate` flag to test without continuous monitoring
- **Check logs**: Look for "✅ Results saved to JSON storage" messages
- **Monitor files**: Check `availability_cache.json` for saved results
- **Environment variables**: You can set `SELECTED_CLUBS` to monitor specific courses only

## 🆘 Still Having Issues?

If you encounter other problems:
1. Check that Python and required packages are installed
2. Verify your `user_preferences.json` file exists and is valid
3. Make sure you have the correct golf course URLs configured

Happy golfing! ⛳
