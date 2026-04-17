#!/usr/bin/env python3
"""
Simple Flask app - just like normal Flask should work
"""
from flask import Flask, render_template, redirect, url_for
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me-in-production'

@app.route('/')
def home():
    return redirect('/upload')

@app.route('/upload')
def upload():
    return render_template("upload.html", active_page="upload")

@app.route('/analytics')
def analytics():
    return render_template("analytics.html", active_page="analytics")

@app.route('/timeline')
def timeline():
    return render_template("timeline.html", active_page="timeline")

@app.route('/insights')
def insights():
    return render_template("insights.html", active_page="insights")

@app.route('/assistant')
def assistant():
    return render_template("assistant.html", active_page="assistant")

@app.route('/realtime')
def realtime():
    return render_template("realtime.html", active_page="realtime")

if __name__ == "__main__":
    print("Starting simple Flask server...")
    print("Access the application at: http://localhost:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
