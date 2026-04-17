#!/usr/bin/env python3
print("=" * 50)
print("Starting Flask Server...")
print("Access the application at: http://localhost:5000")
print("=" * 50)

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, socketio
    print("Starting server on http://127.0.0.1:5000")
    socketio.run(app, host='127.0.0.1', port=5000, debug=False)
except Exception as e:
    print(f"Error starting server: {e}")
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
