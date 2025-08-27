# 💾 Offline Caching System - Implementation Guide

## Overview

Your golf availability monitor now includes a robust **offline caching system** that saves the latest availability results to your PostgreSQL database. This ensures users can see recent results even when your local computer is offline.

## 🏗️ Architecture

```
┌─────────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Local Computer    │    │   PostgreSQL     │    │   Web Users     │
│   (Your Machine)    │    │   Database       │    │                 │
│                     │    │                  │    │                 │
│ ┌─────────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │ Golf Monitor    │─┼────┤ │ cached_      │ │    │ │ Web UI      │ │
│ │ (Scheduled)     │ │    │ │ availability │◄┼────┤ │ Shows Cache │ │
│ └─────────────────┘ │    │ │ Table        │ │    │ │ When Offline│ │
│                     │    │ └──────────────┘ │    │ └─────────────┘ │
│ ┌─────────────────┐ │    └──────────────────┘    └─────────────────┘
│ │ Immediate       │ │
│ │ Checks          │ │
│ └─────────────────┘ │
└─────────────────────┘
```

## 📊 Database Schema

### New Table: `cached_availability`

```sql
CREATE TABLE cached_availability (
    id SERIAL PRIMARY KEY,
    check_type VARCHAR(50) NOT NULL,           -- 'scheduled', 'immediate', 'manual'
    check_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_email VARCHAR(255) REFERENCES user_preferences(email),
    availability_data JSONB NOT NULL,         -- Full availability results
    courses_checked TEXT[] NOT NULL,          -- List of course names
    date_range_start DATE NOT NULL,           -- First date checked
    date_range_end DATE NOT NULL,             -- Last date checked
    total_courses INTEGER DEFAULT 0,          -- Number of courses checked
    total_availability_slots INTEGER DEFAULT 0, -- Total available slots found
    new_availability_count INTEGER DEFAULT 0, -- New slots since last check
    check_duration_seconds NUMERIC(8,2),     -- How long the check took
    success BOOLEAN DEFAULT TRUE,             -- Whether check succeeded
    error_message TEXT,                       -- Error if check failed
    metadata JSONB DEFAULT '{}'::jsonb        -- Additional data (new availability list, etc.)
);
```

### Indexes for Performance:
- `idx_cached_availability_timestamp` - Fast retrieval by date
- `idx_cached_availability_user_email` - User-specific queries
- `idx_cached_availability_check_type` - Filter by check type
- `idx_cached_availability_date_range` - Date range queries

## ⚙️ How It Works

### 1. **Automatic Result Caching**

Every time your golf monitor runs (scheduled or immediate), it automatically saves results:

```python
# After each availability check
await save_results_to_database(results, check_type="scheduled")
```

**What Gets Saved:**
- Complete availability data (courses, dates, times, capacities)
- Check metadata (duration, courses checked, date range)
- Statistics (total slots, new availability count)
- Success/failure status and any error messages

### 2. **Smart Cache Retrieval**

The system provides multiple ways to access cached data:

#### **Latest Results** (within 24 hours by default):
```
GET /api/cached-availability?user_email=user@example.com&hours_limit=24
```

#### **History** (last 10 checks):
```
GET /api/cached-availability/history?user_email=user@example.com&limit=10
```

### 3. **Offline UI Experience**

When your local computer is offline, the web UI automatically shows cached results:

- **📊 Latest Availability (Cached)** section appears
- Shows availability by date with timestamps
- Displays cache information (age, check type, statistics)
- Clear messaging about data freshness

## 🎯 User Experience

### **When Your Computer IS Online:**
1. **Real-time checks** work as normal
2. **Results are cached** automatically in background
3. **Fresh data** is always displayed

### **When Your Computer IS Offline:**
1. **Web UI remains functional** for profile management
2. **Cached results** are displayed with clear timestamps
3. **Users know** they're seeing cached data
4. **Cache age** is clearly indicated (e.g., "2 hours ago")

### **Cache Freshness Indicators:**
```
💾 Showing cached results from 2024-01-15 14:30:25
💾 No recent cached results available. Results will be cached when your local computer runs a check.
⚠️ Cannot connect to API to retrieve cached results.
```

## 📋 API Endpoints

### **Get Cached Availability**
```http
GET /api/cached-availability
Query Parameters:
  - user_email: string (optional) - Filter by user
  - hours_limit: integer (default: 24) - Cache age limit in hours

Response:
{
  "success": true,
  "cached": true,
  "check_timestamp": "2024-01-15T14:30:25+00:00",
  "check_type": "scheduled",
  "availability": { ... },
  "courses_checked": ["oslo_golfklubb", "baerum_gk"],
  "total_courses": 2,
  "total_availability_slots": 15,
  "new_availability": ["Oslo Golfklubb on 2024-01-16 at 08:00: 2 spots"],
  "date_range": {
    "start": "2024-01-15",
    "end": "2024-01-18"
  },
  "cache_age_hours": 24,
  "message": "Showing cached results from 2024-01-15 14:30:25"
}
```

### **Get Cache History**
```http
GET /api/cached-availability/history
Query Parameters:
  - user_email: string (optional) - Filter by user
  - limit: integer (default: 10) - Number of results

Response:
{
  "success": true,
  "history": [
    {
      "id": 123,
      "check_timestamp": "2024-01-15T14:30:25+00:00",
      "check_type": "scheduled",
      "total_courses": 2,
      "total_availability_slots": 15,
      "new_availability_count": 3,
      "success": true,
      "check_duration_seconds": 45.2,
      "date_range": { ... }
    }
  ],
  "count": 1
}
```

## 🔧 Configuration & Management

### **Cache Retention**
- **Default retention**: 30 days
- **Automatic cleanup**: Runs with regular database maintenance
- **Configurable**: Can be adjusted in cleanup settings

### **Cache Types**
- **`scheduled`**: Results from 9am, 12pm, 9pm automatic checks
- **`immediate`**: Results from on-demand "Check Now" requests
- **`manual`**: Results from manual script runs

### **Storage Optimization**
- **JSONB format**: Efficient storage and querying
- **Indexed fields**: Fast retrieval by timestamp, user, type
- **Compressed data**: PostgreSQL handles compression automatically

## 🚀 Benefits

### **For Users:**
- ✅ **Always available data** - see results even when your computer is off
- ✅ **Clear timestamps** - know exactly when data was last updated
- ✅ **Graceful degradation** - system works partially even offline
- ✅ **No data loss** - all checks are preserved for reference

### **For System:**
- ✅ **Resilient architecture** - continues working in failure scenarios
- ✅ **Historical tracking** - complete audit trail of all checks
- ✅ **Performance insights** - track check duration and success rates
- ✅ **Debugging support** - detailed error information when checks fail

### **For Maintenance:**
- ✅ **Automatic cleanup** - old data is removed automatically
- ✅ **Health monitoring** - track system performance over time
- ✅ **Backup friendly** - all data is in PostgreSQL for easy backup

## 📈 Monitoring & Analytics

The cached data provides valuable insights:

### **System Performance:**
- Average check duration
- Success/failure rates
- Most active time periods
- Course availability patterns

### **User Behavior:**
- Most requested courses
- Peak usage times
- Immediate vs scheduled check patterns

### **Data Quality:**
- Availability trend analysis
- New availability frequency
- Course-specific availability patterns

## 🛠️ Troubleshooting

### **No Cached Results Showing:**
1. Check if PostgreSQL is connected
2. Verify your computer has run at least one check
3. Check cache age limits (default: 24 hours)

### **Old Cached Results:**
1. Run a manual check: `python golf_availability_monitor.py --immediate`
2. Check your scheduled monitoring is running
3. Verify database connectivity

### **API Errors:**
1. Check PostgreSQL connection health
2. Verify database schema is up to date
3. Check API server logs for specific errors

## 🎯 Best Practices

### **For Optimal Caching:**
1. **Run scheduled monitoring** regularly (9am, 12pm, 9pm)
2. **Keep PostgreSQL healthy** - monitor connection and performance
3. **Set appropriate cache limits** - balance freshness vs availability
4. **Monitor cache usage** - track how often cached data is served

### **For Users:**
1. **Check timestamps** - always verify data freshness
2. **Understand cache indicators** - know when you're seeing cached data
3. **Plan accordingly** - cached data is great for reference but not real-time booking

This offline caching system ensures your golf availability monitor provides value to users even when your local computer isn't running! 🏌️💾
