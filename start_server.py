#!/usr/bin/env python3
"""
Stable server startup script with port detection and conflict resolution
"""
import os
import sys
import socket
import warnings
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Suppress all warnings for clean startup
warnings.filterwarnings("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'

def is_port_available(host, port):
    """Check if a port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0
    except:
        return False

def find_available_port(host, start_port=8080, max_port=8090):
    """Find an available port starting from start_port"""
    for port in range(start_port, max_port + 1):
        if is_port_available(host, port):
            return port
    return None

def main():
    try:
        print("Initializing server...")
        
        # Set environment variables for stability
        os.environ['FLASK_ENV'] = 'development'
        os.environ['FLASK_DEBUG'] = '1'
        
        # Find available port
        host = "127.0.0.1"
        port = find_available_port(host, 8080, 8090)
        
        if not port:
            print("No available ports found in range 8080-8090")
            return
        
        print(f"Using port {port}...")
        
        # Import and run the main app
        from app import app, socketio
        
        print("=" * 50)
        print("Starting Flask Server...")
        print(f"Access the application at: http://localhost:{port}")
        print("=" * 50)
        
        # Run with stable configuration
        socketio.run(
            app,
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
            log_output=False
        )
        
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        print("Attempting fallback startup...")
        
        try:
            # Find available port for fallback
            fallback_port = find_available_port("127.0.0.1", 8080, 8090)
            if not fallback_port:
                print("No available ports for fallback server")
                return
            
            # Fallback to basic Flask
            from flask import Flask, redirect, render_template
            from config import SECRET_KEY
            
            fallback_app = Flask(__name__)
            fallback_app.config['SECRET_KEY'] = SECRET_KEY
            
            @fallback_app.route('/')
            def home():
                return redirect('/upload')
                
            @fallback_app.route('/upload')
            def upload():
                return render_template("upload.html", active_page="upload")
            
            @fallback_app.route('/analytics')
            def analytics():
                return render_template("analytics.html", active_page="analytics")
            
            @fallback_app.route('/timeline')
            def timeline():
                return render_template("timeline.html", active_page="timeline")
            
            @fallback_app.route('/insights')
            def insights():
                return render_template("insights.html", active_page="insights")
            
            @fallback_app.route('/assistant')
            def assistant():
                return render_template("assistant.html", active_page="assistant")
            
            @fallback_app.route('/realtime')
            def realtime():
                return render_template("realtime.html", active_page="realtime")
            
            print(f"Fallback server starting on port {fallback_port}...")
            print(f"Access the application at: http://localhost:{fallback_port}")
            fallback_app.run(host="127.0.0.1", port=fallback_port, debug=False)
            
        except Exception as fallback_error:
            print(f"Fallback also failed: {fallback_error}")
            sys.exit(1)

if __name__ == "__main__":
    main()
