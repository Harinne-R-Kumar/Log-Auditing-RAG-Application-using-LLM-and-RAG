import json
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Suppress warnings for cleaner startup
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

from config import (
    ALLOWED_EXTENSIONS,
    FEEDBACK_DB,
    MAX_CONTENT_LENGTH,
    SECRET_KEY,
    UPLOAD_FOLDER,
    ensure_directories,
)
from services.analysis_pipeline import AnalysisPipeline
from services.parser import parse_log_file


ensure_directories()

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
socketio = SocketIO(app, cors_allowed_origins="*")

pipeline = AnalysisPipeline()
LATEST_ANALYSIS: Dict[str, Any] = {}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    return redirect(url_for("upload_page"))


@app.route("/upload")
def upload_page():
    return render_template("upload.html", active_page="upload")


@app.route("/analytics")
def analytics_page():
    return render_template("analytics.html", active_page="analytics")


@app.route("/timeline")
def timeline_page():
    return render_template("timeline.html", active_page="timeline")


@app.route("/insights")
def insights_page():
    return render_template("insights.html", active_page="insights")


@app.route("/assistant")
def assistant_page():
    return render_template("assistant.html", active_page="assistant")


@app.route("/realtime")
def realtime_page():
    return render_template("realtime.html", active_page="realtime")


@app.route("/api/upload", methods=["POST"])
def upload_log():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "No selected file"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Use .log, .txt, .csv"}), 400

    filename = secure_filename(file.filename)
    save_path = Path(app.config["UPLOAD_FOLDER"]) / filename
    file.save(save_path)

    parsed_logs = parse_log_file(save_path)
    if not parsed_logs:
        return jsonify({"error": "No parsable log entries found"}), 400

    analysis = pipeline.run_full_analysis(parsed_logs)
    analysis["file_name"] = filename
    analysis["uploaded_at"] = datetime.now(timezone.utc).isoformat()
    global LATEST_ANALYSIS
    LATEST_ANALYSIS = analysis

    return jsonify(analysis)


@app.route("/api/chat", methods=["POST"])
def chat_assistant():
    body = request.get_json(force=True)
    question = body.get("question", "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    if not LATEST_ANALYSIS:
        return jsonify({"answer": "Please upload logs first for context-aware answers."})

    timeline = LATEST_ANALYSIS.get("timeline", [])[:20]
    rag_context = LATEST_ANALYSIS.get("rag_context", [])[:5]
    prompt = (
        "Answer the user's question based on incident timeline and similar logs.\n"
        f"Question: {question}\n"
        f"Timeline: {timeline}\n"
        f"Related logs: {rag_context}\n"
        "Be concise and actionable."
    )
    response = pipeline.grok.generate(prompt) or (
        "LLM unavailable ("
        + (pipeline.grok.last_error or "unknown error")
        + "). Based on heuristics: inspect peak error window, review failing module, and correlate anomalies with deployment/config changes."
    )
    return jsonify({"answer": response})


@app.route("/api/latest", methods=["GET"])
def latest_analysis():
    if not LATEST_ANALYSIS:
        return jsonify({"error": "No analysis available. Upload logs first."}), 404
    return jsonify(LATEST_ANALYSIS)


@app.route("/api/feedback", methods=["POST"])
def feedback():
    body = request.get_json(force=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": body.get("question"),
        "answer": body.get("answer"),
        "is_correct": bool(body.get("is_correct")),
        "notes": body.get("notes", ""),
    }
    with FEEDBACK_DB.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")
    return jsonify({"status": "saved"})


@app.route("/api/realtime/log", methods=["POST"])
def realtime_log_ingest():
    body = request.get_json(force=True)
    message = body.get("message", "")
    if not message:
        return jsonify({"error": "message required"}), 400
    log = {
        "timestamp": body.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "message": message,
        "severity": body.get("severity"),
        "module": body.get("module", "browser-extension"),
    }
    parsed = pipeline.classifier.classify_logs([log])[0]
    socketio.emit("realtime_log", parsed)
    return jsonify({"status": "streamed", "log": parsed})


@socketio.on("connect")
def on_connect():
    emit("status", {"message": "Connected to Agentic Log Platform"})


if __name__ == "__main__":
    try:
        print("=" * 50)
        print("Starting Flask Server...")
        print("Access the application at: http://localhost:8080")
        print("=" * 50)
        
        # Configure for better stability
        app.config['DEBUG'] = True
        app.config['RELOADER'] = False  # Disable auto-reloader to prevent conflicts
        
        # Run with more stable configuration
        socketio.run(app, host="127.0.0.1", port=8080, debug=False, use_reloader=False)
        
    except Exception as e:
        print(f"Server startup error: {e}")
        print("Retrying with basic configuration...")
        # Fallback to basic Flask without SocketIO if needed
        from flask import Flask
        basic_app = Flask(__name__)
        basic_app.config['SECRET_KEY'] = SECRET_KEY
        
        @basic_app.route('/')
        def basic_home():
            return redirect('/upload')
            
        @basic_app.route('/upload')
        def basic_upload():
            return render_template("upload.html", active_page="upload")
        
        basic_app.run(host="127.0.0.1", port=8080, debug=False)
