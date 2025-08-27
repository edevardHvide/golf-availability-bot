#!/usr/bin/env python3
"""
Local API Server for Golf Availability Monitor

This server runs on your local machine and provides API endpoints
for the Streamlit web app to trigger immediate availability checks.
"""

import asyncio
import json
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for Streamlit integration

# Global state
last_check_result = None
check_in_progress = False
server_start_time = datetime.now()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "server_start": server_start_time.isoformat(),
        "check_in_progress": check_in_progress,
        "last_check": last_check_result.get("timestamp") if last_check_result else None
    })

@app.route('/api/immediate-check', methods=['POST'])
def trigger_immediate_check():
    """Trigger an immediate availability check"""
    global check_in_progress, last_check_result
    
    if check_in_progress:
        return jsonify({
            "success": False,
            "error": "Check already in progress",
            "estimated_completion": "1-2 minutes"
        }), 429
    
    try:
        # Get request parameters
        data = request.get_json() or {}
        user_email = data.get('user_email')
        time_window = data.get('time_window', '16:00-18:00')
        days = data.get('days', 2)
        players = data.get('players', 1)
        
        # Start the check in a background thread
        check_thread = threading.Thread(
            target=run_immediate_check_background,
            args=(user_email, time_window, days, players)
        )
        check_thread.daemon = True
        check_thread.start()
        
        return jsonify({
            "success": True,
            "message": "Immediate check started",
            "estimated_completion": "1-2 minutes",
            "check_id": f"check_{int(time.time())}",
            "user_email": user_email
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/check-status', methods=['GET'])
def get_check_status():
    """Get the status of the current or last check"""
    global check_in_progress, last_check_result
    
    return jsonify({
        "check_in_progress": check_in_progress,
        "last_result": last_check_result,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/check-result', methods=['GET'])
def get_last_check_result():
    """Get the result of the last availability check"""
    global last_check_result
    
    if last_check_result is None:
        return jsonify({
            "success": False,
            "error": "No check results available"
        }), 404
    
    return jsonify(last_check_result)

def run_immediate_check_background(user_email: str, time_window: str, days: int, players: int):
    """Run the immediate check in the background"""
    global check_in_progress, last_check_result
    
    check_in_progress = True
    start_time = datetime.now()
    
    try:
        print(f"🚀 Starting immediate check for {user_email}")
        
        # Build command to run the golf monitor
        cmd = [
            sys.executable,
            "golf_availability_monitor.py",
            "--immediate",
            "--time-window", time_window,
            "--days", str(days),
            "--players", str(players)
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        
        # Run the command and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if result.returncode == 0:
            print(f"✅ Check completed successfully in {duration:.1f} seconds")
            
            # Try to parse the output for structured results
            # The immediate check should return JSON results
            try:
                # Look for JSON in the output
                output_lines = result.stdout.split('\n')
                json_result = None
                for line in output_lines:
                    if line.strip().startswith('{') and 'success' in line:
                        json_result = json.loads(line.strip())
                        break
                
                if json_result:
                    last_check_result = {
                        "success": True,
                        "timestamp": end_time.isoformat(),
                        "duration_seconds": duration,
                        "user_email": user_email,
                        "results": json_result,
                        "raw_output": result.stdout
                    }
                else:
                    # Fallback to text parsing
                    last_check_result = {
                        "success": True,
                        "timestamp": end_time.isoformat(),
                        "duration_seconds": duration,
                        "user_email": user_email,
                        "raw_output": result.stdout,
                        "message": "Check completed - see raw output for details"
                    }
                    
            except json.JSONDecodeError:
                last_check_result = {
                    "success": True,
                    "timestamp": end_time.isoformat(),
                    "duration_seconds": duration,
                    "user_email": user_email,
                    "raw_output": result.stdout,
                    "message": "Check completed - see raw output for details"
                }
        else:
            print(f"❌ Check failed with return code {result.returncode}")
            last_check_result = {
                "success": False,
                "timestamp": end_time.isoformat(),
                "duration_seconds": duration,
                "user_email": user_email,
                "error": f"Process failed with return code {result.returncode}",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
    except subprocess.TimeoutExpired:
        print("⏰ Check timed out after 5 minutes")
        last_check_result = {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "user_email": user_email,
            "error": "Check timed out after 5 minutes"
        }
        
    except Exception as e:
        print(f"💥 Check failed with exception: {e}")
        last_check_result = {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "user_email": user_email,
            "error": str(e)
        }
    
    finally:
        check_in_progress = False
        print(f"🏁 Check completed for {user_email}")

if __name__ == "__main__":
    print("🚀 Starting Local Golf Monitor API Server")
    print("This server enables immediate availability checks from the Streamlit web app")
    print("=" * 60)
    print(f"Server starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Endpoints:")
    print("  GET  /health - Health check")
    print("  POST /api/immediate-check - Trigger immediate check")
    print("  GET  /api/check-status - Get check status")
    print("  GET  /api/check-result - Get last check result")
    print("=" * 60)
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )
