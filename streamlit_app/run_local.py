#!/usr/bin/env python3
"""
Local Development Server for Golf Availability Monitor Web Interface

This script starts both the FastAPI backend and Streamlit frontend for local development.
"""

import subprocess
import sys
import time
import os
from pathlib import Path
import signal

def install_dependencies():
    """Install required dependencies if not already installed."""
    print("📦 Installing dependencies with uv...")
    
    try:
        # Check if uv is available
        try:
            subprocess.run(["uv", "--version"], check=True, capture_output=True)
            print("✅ uv found!")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ uv not found. Installing uv first...")
            subprocess.run([sys.executable, "-m", "pip", "install", "uv"], check=True)
            print("✅ uv installed!")
        
        # Install streamlit app dependencies with uv
        subprocess.run([
            "uv", "pip", "install", "-r", 
            str(Path(__file__).parent / "requirements.txt")
        ], check=True)
        
        print("✅ Dependencies installed successfully with uv!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ uv failed: {e}")
        print("🔄 Falling back to regular pip...")
        
        try:
            # Fallback to regular pip
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", 
                str(Path(__file__).parent / "requirements.txt")
            ], check=True)
            
            print("✅ Dependencies installed with pip!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Both uv and pip failed: {e}")
            return False

def start_api_server():
    """Start the FastAPI backend server."""
    print("🚀 Starting enhanced API server...")
    
    try:
        # Change to the streamlit_app directory
        os.chdir(Path(__file__).parent)
        
        # Choose the enhanced API server if available
        api_file = "enhanced_api_server.py" if Path("enhanced_api_server.py").exists() else "api_server.py"
        
        # Start the API server
        process = subprocess.Popen([
            sys.executable, api_file
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"✅ Started {api_file}")
        return process
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        return None

def start_streamlit_app():
    """Start the Streamlit frontend."""
    print("🌐 Starting enhanced Streamlit app...")
    
    try:
        # Choose the enhanced app if available
        app_file = "enhanced_app.py" if Path("enhanced_app.py").exists() else "app.py"
        
        # Start Streamlit
        process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", app_file,
            "--server.address", "0.0.0.0",
            "--server.port", "8501",
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"✅ Started {app_file}")
        return process
    except Exception as e:
        print(f"❌ Failed to start Streamlit app: {e}")
        return None

def check_process_health(process, name):
    """Check if a process is still running."""
    if process.poll() is None:
        return True
    else:
        print(f"⚠️ {name} process has stopped")
        return False

def main():
    """Main function to start both services."""
    print("🏌️ Golf Availability Monitor - Enhanced Local Development Server")
    print("=" * 65)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Start API server
    api_process = start_api_server()
    if not api_process:
        sys.exit(1)
    
    # Wait a moment for API to start
    print("⏳ Waiting for API server to start...")
    time.sleep(3)
    
    # Start Streamlit app
    streamlit_process = start_streamlit_app()
    if not streamlit_process:
        if api_process:
            api_process.terminate()
        sys.exit(1)
    
    # Wait a moment for Streamlit to start
    print("⏳ Waiting for Streamlit app to start...")
    time.sleep(5)
    
    print("\n✅ Both services are running!")
    print("📱 Enhanced Streamlit App: http://localhost:8501")
    print("🔗 Enhanced API Documentation: http://localhost:8000/docs")
    print("� System Status: http://localhost:8000/api/status")
    print("�💾 API Health Check: http://localhost:8000/health")
    print("\n🔧 Features:")
    print("  • Robust JSON data storage with automatic backups")
    print("  • Enhanced error handling and recovery")
    print("  • Improved user interface with profile management")
    print("  • Comprehensive system monitoring")
    print("\nPress Ctrl+C to stop all services")
    
    def signal_handler(sig, frame):
        print("\n🛑 Stopping services...")
        if api_process:
            api_process.terminate()
        if streamlit_process:
            streamlit_process.terminate()
        print("Services stopped")
        sys.exit(0)
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Monitor both processes
        while True:
            if not check_process_health(api_process, "Enhanced API Server"):
                break
            if not check_process_health(streamlit_process, "Enhanced Streamlit App"):
                break
            time.sleep(5)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()
