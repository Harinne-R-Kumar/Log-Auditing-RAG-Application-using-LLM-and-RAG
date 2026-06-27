# Agentic AI Log Auditing & Analysis Platform

Production-ready Flask + AI system for real-time and offline log intelligence:
- Real-time browser-extension log stream ingestion.
- Upload-based full log analysis pipeline.
- Hybrid ML + LLM classification and anomaly detection.
- RAG-enhanced root cause insights with actionable recommendations.

## Features

### Core Pipeline (Auto-run on file upload)
1. **Log parsing**: timestamp, message, severity, module extraction.
2. **Time-based analysis**: logs/hour/day, peak error time, spike windows.
3. **Hybrid severity classification**:
   - Regex rules
   - TF-IDF + Logistic Regression
   - Grok fallback classifier
4. **Anomaly detection**: Isolation Forest with anomaly score.
5. **Incident timeline reconstruction**.
6. **Root cause and chain-of-events analysis** (heuristic + Grok context).
7. **Fix recommendation generation**.
8. **Log summarization**.
9. **Severity distribution and peak-time detection**.
10. **RAG contextual retrieval using FAISS**.

### Dashboard
- Summary KPIs (total logs, errors, anomalies, peak time)
- Logs-over-time and severity charts
- Ordered timeline
- AI insights panel
- Chat assistant for natural language incident Q&A
- User feedback loop (correct/incorrect) for model improvement

### Additional System Capabilities
- Flask-SocketIO real-time monitoring path
- Dataset creation (`data/past_logs.jsonl`, `data/feedback.jsonl`)
- Model evaluation metrics (Accuracy, F1-score)
- Time-series analysis for incident spike detection

## Project Structure

```text
.
|-- app.py
|-- config.py
|-- requirements.txt
|-- services/
|   |-- parser.py
|   |-- classifier.py
|   |-- model_training.py
|   |-- anomaly.py
|   |-- timeline.py
|   |-- rag.py
|   |-- grok_client.py
|   `-- analysis_pipeline.py
|-- templates/
|   `-- index.html
`-- static/
    |-- css/styles.css
    `-- js/dashboard.js
```

## Setup Instructions

1. Create virtual environment:
   - Windows PowerShell:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Configure environment variables:
   ```powershell
   $env:GROK_API_KEY="your_grok_key"
   $env:GROK_API_URL="https://api.x.ai/v1/chat/completions"
   $env:GROK_MODEL="grok-2-latest"
   $env:SECRET_KEY="replace-this"
   ```
4. Run the app:
   ```powershell
   python app.py
   ```
5. Open dashboard:
   - [http://localhost:5000](http://localhost:5000)

## API Endpoints

- `POST /api/upload`  
  Upload `.log`, `.txt`, `.csv` and trigger full analysis.

- `POST /api/chat`  
  Ask questions against latest uploaded analysis context.

- `POST /api/feedback`  
  Save user correctness feedback for continuous improvement.

- `POST /api/realtime/log`  
  Ingest real-time logs from browser extension or agents.

## Browser Extension Integration (Real-time)

Send JSON to:
```http
POST /api/realtime/log
Content-Type: application/json

{
  "timestamp": "2026-04-17T10:25:00Z",
  "message": "Auth timeout on token refresh",
  "severity": "ERROR",
  "module": "auth-client"
}
```

## Notes for Production Hardening

- Add authentication and RBAC.
- Move feedback/past logs to PostgreSQL or object storage.
- Add Celery/RQ background jobs for large files.
- Add model retraining scheduler from feedback data.
- Containerize with Docker and deploy via Kubernetes.
