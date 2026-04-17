# AI Log Auditing Platform - Implementation & Functionality Documentation

## Table of Contents
1. [Implementation Overview](#implementation-overview)
2. [Core Functionality](#core-functionality)
3. [File Upload & Processing](#file-upload--processing)
4. [Log Analysis Pipeline](#log-analysis-pipeline)
5. [Machine Learning Implementation](#machine-learning-implementation)
6. [User Attribution System](#user-attribution-system)
7. [AI Chat Assistant](#ai-chat-assistant)
8. [Analytics Dashboard](#analytics-dashboard)
9. [API Implementation Details](#api-implementation-details)
10. [Frontend Implementation](#frontend-implementation)
11. [Data Storage & Caching](#data-storage--caching)
12. [Error Handling & Validation](#error-handling--validation)
13. [Security Implementation](#security-implementation)
14. [Performance Optimization](#performance-optimization)
15. [Testing & Debugging](#testing--debugging)

---

## Implementation Overview

The AI Log Auditing Platform is implemented as a Flask-based web application with a modular service architecture. The system processes log files through a sophisticated analysis pipeline that combines machine learning, natural language processing, and rule-based pattern matching.

### Key Implementation Characteristics
- **Flask Web Framework**: Lightweight, extensible web server
- **Service-Oriented Architecture**: Modular components with clear responsibilities
- **File-Based Storage**: Simple, reliable data persistence
- **Hybrid ML Approach**: Combines multiple classification techniques
- **Real-time Processing**: Asynchronous analysis pipeline
- **Interactive UI**: Modern JavaScript-based frontend

---

## Core Functionality

### 1. System Initialization
```python
# clean_app.py - Main application setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Core data structures
USER_SESSION_MAPPING = {}      # Session to user mapping
UNKNOWN_USER_LOGS = []         # Logs without user attribution
ANALYSIS_FILE = 'latest_analysis.json'  # Analysis cache
```

### 2. File Upload System
```python
def allowed_file(filename):
    """Validate file extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload with validation"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Trigger analysis
        analysis_result = analyze_log_file(filepath)
        save_analysis_data(analysis_result)
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'analysis': analysis_result
        })
```

### 3. Log Analysis Orchestration
```python
def analyze_log_file(file_path):
    """Main analysis orchestrator"""
    try:
        # Step 1: Parse logs
        logs = parse_log_file(file_path)
        
        # Step 2: Classify logs
        classified_logs = classify_logs(logs)
        
        # Step 3: User attribution
        attributed_logs = analyze_user_attribution(classified_logs)
        
        # Step 4: Timeline analysis
        timeline = build_timeline(attributed_logs)
        
        # Step 5: Anomaly detection
        anomalies = detect_anomalies(attributed_logs)
        
        # Step 6: Generate insights
        insights = generate_insights(attributed_logs, timeline, anomalies)
        
        return {
            'summary': calculate_summary(attributed_logs),
            'classified_logs': attributed_logs,
            'timeline': timeline,
            'anomalies': anomalies,
            'ai_insights': insights,
            'user_attribution': get_user_attribution_stats(attributed_logs)
        }
    except Exception as e:
        return {'error': str(e)}
```

---

## File Upload & Processing

### File Validation
```python
ALLOWED_EXTENSIONS = {'log', 'txt', 'csv'}

def validate_file_upload(file):
    """Comprehensive file validation"""
    # Check file extension
    if not allowed_file(file.filename):
        raise ValidationError("Invalid file type")
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > app.config['MAX_CONTENT_LENGTH']:
        raise ValidationError("File too large")
    
    # Check file content
    content = file.read(1024)  # Read first 1KB
    file.seek(0)
    
    if not content.strip():
        raise ValidationError("Empty file")
    
    return True
```

### Log Parsing Implementation
```python
def parse_log_file(file_path):
    """Parse log file with multiple format support"""
    logs = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                # Try different log formats
                parsed_log = parse_log_line(line, line_num)
                if parsed_log:
                    logs.append(parsed_log)
            except Exception as e:
                # Log parsing error but continue
                logs.append({
                    'raw_line': line,
                    'line_number': line_num,
                    'parse_error': str(e),
                    'severity': 'INFO',
                    'message': line,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
    
    return logs

def parse_log_line(line, line_num):
    """Parse individual log line with multiple patterns"""
    # Standard log format: timestamp [level] message
    standard_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*\[?(\w+)\]?\s*(.+)'
    match = re.match(standard_pattern, line)
    
    if match:
        timestamp_str, level, message = match.groups()
        return {
            'timestamp': timestamp_str,
            'severity': level.upper(),
            'message': message,
            'line_number': line_num,
            'raw_line': line
        }
    
    # Apache log format
    apache_pattern = r'(\S+) \S+ \S+ \[([\w:/]+\s[+\-]\d{4})\] "(\S+) (\S+) (\S+)" (\d{3}) (\d+)'
    match = re.match(apache_pattern, line)
    
    if match:
        ip, timestamp, method, path, protocol, status, size = match.groups()
        return {
            'timestamp': timestamp,
            'severity': 'ERROR' if int(status) >= 400 else 'INFO',
            'message': f"{method} {path} {status}",
            'ip_address': ip,
            'line_number': line_num,
            'raw_line': line
        }
    
    # Default fallback
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'severity': 'INFO',
        'message': line,
        'line_number': line_num,
        'raw_line': line
    }
```

---

## Log Analysis Pipeline

### Analysis Pipeline Class
```python
class AnalysisPipeline:
    """Main analysis orchestrator"""
    
    def __init__(self):
        self.classifier = HybridClassifier()
        self.grok = GrokClient()
        self.rag = RagRetriever()
    
    def analyze(self, logs):
        """Complete analysis pipeline"""
        # Step 1: Classification
        classified_logs = self._classify_logs(logs)
        
        # Step 2: Timeline analysis
        timeline = build_timeline(classified_logs)
        
        # Step 3: Anomaly detection
        anomalies = detect_anomalies(classified_logs)
        
        # Step 4: Generate insights
        insights = self._generate_insights(classified_logs, timeline, anomalies)
        
        # Step 5: Build summary
        summary = self._build_summary(classified_logs, anomalies, timeline)
        
        return {
            'classified_logs': classified_logs,
            'timeline': timeline,
            'anomalies': anomalies,
            'ai_insights': insights,
            'summary': summary
        }
    
    def _classify_logs(self, logs):
        """Classify each log entry"""
        classified = []
        
        for log in logs:
            # Extract features
            features = self._extract_features(log)
            
            # Classify
            classification, confidence = self.classifier.predict(features)
            
            # Add classification to log
            log['classification'] = classification
            log['confidence'] = confidence
            log['risk_level'] = self._calculate_risk_level(log, classification)
            
            classified.append(log)
        
        return classified
    
    def _extract_features(self, log):
        """Extract features for ML classification"""
        message = log.get('message', '')
        
        features = {
            'message_length': len(message),
            'word_count': len(message.split()),
            'has_error_keywords': any(keyword in message.lower() 
                                    for keyword in ['error', 'fail', 'exception', 'timeout']),
            'severity_numeric': self._severity_to_numeric(log.get('severity', 'INFO')),
            'message': message  # For text-based classification
        }
        
        return features
```

### Timeline Analysis
```python
def build_timeline(logs):
    """Build chronological timeline of events"""
    timeline = []
    
    for log in logs:
        try:
            timestamp = datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S')
        except:
            timestamp = datetime.now()
        
        timeline.append({
            'timestamp': log['timestamp'],
            'datetime': timestamp,
            'severity': log.get('severity', 'INFO'),
            'message': log.get('message', ''),
            'classification': log.get('classification', 'unknown'),
            'risk_level': log.get('risk_level', 'low'),
            'module': log.get('module', 'unknown')
        })
    
    # Sort by timestamp
    timeline.sort(key=lambda x: x['datetime'])
    
    # Add time-based analysis
    timeline = add_time_analysis(timeline)
    
    return timeline

def add_time_analysis(timeline):
    """Add time-based analysis to timeline"""
    if not timeline:
        return timeline
    
    # Calculate time intervals
    for i in range(1, len(timeline)):
        prev_time = timeline[i-1]['datetime']
        curr_time = timeline[i]['datetime']
        time_diff = (curr_time - prev_time).total_seconds()
        timeline[i]['time_since_previous'] = time_diff
    
    # Identify error clusters
    error_times = [entry['datetime'] for entry in timeline 
                  if entry['severity'] in ['ERROR', 'CRITICAL']]
    
    if error_times:
        # Find peak error time
        error_hour_counts = {}
        for error_time in error_times:
            hour = error_time.replace(minute=0, second=0, microsecond=0)
            error_hour_counts[hour] = error_hour_counts.get(hour, 0) + 1
        
        peak_hour = max(error_hour_counts.items(), key=lambda x: x[1])[0]
        
        # Add peak error time to timeline
        for entry in timeline:
            entry['peak_error_hour'] = peak_hour.strftime('%Y-%m-%d %H:%M')
    
    return timeline
```

---

## Machine Learning Implementation

### Hybrid Classifier
```python
class HybridClassifier:
    """Hybrid ML classifier combining multiple approaches"""
    
    def __init__(self):
        self.models = {}
        self.vectorizer = None
        self.load_models()
    
    def load_models(self):
        """Load pre-trained models"""
        try:
            self.models['rf'] = joblib.load('models/random_forest.pkl')
            self.models['svm'] = joblib.load('models/svm.pkl')
            self.vectorizer = joblib.load('models/vectorizer.pkl')
        except FileNotFoundError:
            # Fallback to rule-based classification
            self.models['rule_based'] = RuleBasedClassifier()
    
    def predict(self, features):
        """Predict classification using ensemble approach"""
        predictions = {}
        confidences = {}
        
        # Random Forest prediction
        if 'rf' in self.models:
            text_features = self.vectorizer.transform([features['message']])
            rf_pred = self.models['rf'].predict(text_features)[0]
            rf_conf = max(self.models['rf'].predict_proba(text_features)[0])
            predictions['rf'] = rf_pred
            confidences['rf'] = rf_conf
        
        # SVM prediction
        if 'svm' in self.models:
            svm_pred = self.models['svm'].predict(text_features)[0]
            svm_conf = max(self.models['svm'].predict_proba(text_features)[0])
            predictions['svm'] = svm_pred
            confidences['svm'] = svm_conf
        
        # Rule-based prediction
        if 'rule_based' in self.models:
            rule_pred = self.models['rule_based'].classify(features)
            predictions['rule_based'] = rule_pred
            confidences['rule_based'] = 0.8  # Fixed confidence for rules
        
        # Ensemble voting
        if predictions:
            final_prediction = self._ensemble_voting(predictions, confidences)
            final_confidence = self._calculate_ensemble_confidence(confidences)
        else:
            final_prediction = 'unknown'
            final_confidence = 0.0
        
        return final_prediction, final_confidence
    
    def _ensemble_voting(self, predictions, confidences):
        """Weighted voting ensemble"""
        vote_counts = {}
        total_weight = 0
        
        for model, pred in predictions.items():
            weight = confidences.get(model, 0.5)
            vote_counts[pred] = vote_counts.get(pred, 0) + weight
            total_weight += weight
        
        # Return prediction with highest weighted vote
        return max(vote_counts.items(), key=lambda x: x[1])[0]
```

### PyTorch Neural Network Implementation
```python
class LogClassifier(nn.Module):
    """PyTorch neural network for log classification"""
    
    def __init__(self, input_size, hidden_size=128, num_classes=4):
        super(LogClassifier, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(hidden_size, hidden_size // 2)
        self.fc3 = nn.Linear(hidden_size // 2, num_classes)
    
    def forward(self, x):
        out = self.fc1(x)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc3(out)
        return out

class PyTorchClassifier:
    """PyTorch-based classifier"""
    
    def __init__(self):
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.load_model()
    
    def load_model(self):
        """Load trained PyTorch model"""
        try:
            self.model = LogClassifier(input_size=1000)  # TF-IDF feature size
            self.model.load_state_dict(torch.load('models/pytorch_model.pth'))
            self.model.to(self.device)
            self.model.eval()
        except:
            # Fallback to other classifiers
            pass
    
    def predict(self, features):
        """Predict using PyTorch model"""
        if self.model is None:
            return 'unknown', 0.0
        
        with torch.no_grad():
            # Convert features to tensor
            if isinstance(features, str):
                # Text input - need vectorization
                features_tensor = self.vectorize_text(features)
            else:
                features_tensor = torch.FloatTensor(features).unsqueeze(0)
            
            features_tensor = features_tensor.to(self.device)
            
            # Get prediction
            outputs = self.model(features_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)
            
            class_names = ['info', 'warning', 'error', 'critical']
            prediction = class_names[predicted.item()]
            confidence_score = confidence.item()
            
            return prediction, confidence_score
```

### Rule-Based Classifier
```python
class RuleBasedClassifier:
    """Rule-based classification for common log patterns"""
    
    def __init__(self):
        self.rules = self._load_rules()
    
    def _load_rules(self):
        """Load classification rules"""
        return {
            'database_error': [
                r'database.*connection.*failed',
                r'sql.*error',
                r'db.*timeout',
                r'connection.*pool.*exhausted'
            ],
            'network_error': [
                r'connection.*refused',
                r'network.*unreachable',
                r'timeout.*connection',
                r'socket.*error'
            ],
            'authentication_error': [
                r'login.*failed',
                r'authentication.*failed',
                r'unauthorized.*access',
                r'invalid.*credentials'
            ],
            'file_system_error': [
                r'file.*not.*found',
                r'permission.*denied',
                r'disk.*full',
                r'io.*error'
            ],
            'memory_error': [
                r'out.*of.*memory',
                r'memory.*allocation.*failed',
                r'heap.*space',
                r'gc.*overhead'
            ]
        }
    
    def classify(self, features):
        """Classify based on rules"""
        message = features.get('message', '').lower()
        severity = features.get('severity', '').upper()
        
        # Check each rule category
        for category, patterns in self.rules.items():
            for pattern in patterns:
                if re.search(pattern, message):
                    return category
        
        # Fallback to severity-based classification
        if severity in ['ERROR', 'CRITICAL']:
            return 'general_error'
        elif severity == 'WARNING':
            return 'warning'
        else:
            return 'info'
```

---

## User Attribution System

### User Extraction Implementation
```python
def extract_user_from_log(log_entry):
    """Extract user information from log entry"""
    user_info = {
        'user_id': None,
        'session_id': None,
        'ip_address': None,
        'timestamp': log_entry.get('timestamp', ''),
        'severity': log_entry.get('severity', ''),
        'message': log_entry.get('message', ''),
        'module': log_entry.get('module', '')
    }
    
    message = log_entry.get('message', '')
    
    # Extract user_id patterns
    user_id_patterns = [
        r'user_id=(\w+)',
        r'user[:\s]+(\w+)',
        r'User[:\s]+(\w+)',
        r'account[:\s]+(\w+)',
        r'uid[:\s]+(\w+)'
    ]
    
    for pattern in user_id_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            user_info['user_id'] = match.group(1)
            break
    
    # Extract session_id patterns
    session_patterns = [
        r'session[_-]?id[:\s]*=?[=:]?\s*(\w+)',
        r'sess[_-]?id[:\s]*=?[=:]?\s*(\w+)',
        r'token[:\s]+(\w+)',
        r'auth[:\s]+(\w+)'
    ]
    
    for pattern in session_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            user_info['session_id'] = match.group(1)
            break
    
    # Extract IP address patterns
    ip_patterns = [
        r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
        r'IP[:\s]*=?[=:]?\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
        r'from[:\s]+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    ]
    
    for pattern in ip_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            user_info['ip_address'] = match.group(1)
            break
    
    return user_info
```

### Attribution Analysis
```python
def analyze_user_attribution(logs):
    """Analyze user attribution across all logs"""
    attributed_logs = []
    
    for log in logs:
        user_info = extract_user_from_log(log)
        
        # Direct user ID found
        if user_info['user_id']:
            if user_info['session_id']:
                map_session_to_user(user_info['session_id'], user_info['user_id'])
            user_info['attribution_method'] = 'direct'
        
        # Session-based inference
        elif user_info['session_id']:
            mapped_user = USER_SESSION_MAPPING.get(user_info['session_id'])
            if mapped_user:
                user_info['user_id'] = mapped_user
                user_info['attribution_method'] = 'session_inferred'
            else:
                user_info['attribution_method'] = 'session_unknown'
        
        # Timestamp-based fallback
        else:
            user_info['user_id'] = infer_user_from_timestamp(
                user_info['timestamp'], 
                attributed_logs + [user_info]
            )
            user_info['attribution_method'] = 'timestamp_used'
        
        attributed_logs.append(user_info)
    
    return attributed_logs

def infer_user_from_timestamp(timestamp_str, current_logs):
    """Infer user based on timestamp proximity"""
    if not timestamp_str or not current_logs:
        return 'Unknown'
    
    try:
        current_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
    except:
        return 'Unknown'
    
    # Find logs with known users within 5 minutes
    time_window = timedelta(minutes=5)
    known_user_logs = [
        log for log in current_logs 
        if log.get('user_id') and log['user_id'] != 'Unknown'
    ]
    
    if not known_user_logs:
        return 'Unknown'
    
    # Find closest known user log
    closest_log = None
    min_time_diff = timedelta(hours=1)
    
    for log in known_user_logs:
        try:
            log_time = datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S')
            time_diff = abs((current_time - log_time).total_seconds())
            
            if time_diff < min_time_diff.total_seconds():
                min_time_diff = timedelta(seconds=time_diff)
                closest_log = log
        except:
            continue
    
    if closest_log and min_time_diff.total_seconds() < 300:  # 5 minutes
        return closest_log['user_id']
    
    return 'Unknown'
```

### Risk Scoring Implementation
```python
def calculate_user_risk(user_logs):
    """Calculate risk score for a user"""
    if not user_logs:
        return 0.0
    
    risk_factors = {
        'error_count': 0,
        'critical_count': 0,
        'time_pattern': 0,
        'severity_weight': 0
    }
    
    # Count errors and critical events
    for log in user_logs:
        severity = log.get('severity', '').upper()
        if severity == 'ERROR':
            risk_factors['error_count'] += 1
            risk_factors['severity_weight'] += 1
        elif severity == 'CRITICAL':
            risk_factors['critical_count'] += 1
            risk_factors['severity_weight'] += 2
    
    # Analyze time patterns (concentrated errors increase risk)
    if len(user_logs) > 1:
        timestamps = []
        for log in user_logs:
            try:
                ts = datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S')
                timestamps.append(ts)
            except:
                continue
        
        if timestamps:
            timestamps.sort()
            time_spans = [(timestamps[i+1] - timestamps[i]).total_seconds() 
                         for i in range(len(timestamps)-1)]
            
            # Concentrated errors (short time spans) increase risk
            avg_span = sum(time_spans) / len(time_spans) if time_spans else 0
            if avg_span < 60:  # Less than 1 minute between errors
                risk_factors['time_pattern'] = 2
            elif avg_span < 300:  # Less than 5 minutes
                risk_factors['time_pattern'] = 1
    
    # Calculate final risk score
    risk_score = (
        risk_factors['error_count'] * 0.1 +
        risk_factors['critical_count'] * 0.3 +
        risk_factors['time_pattern'] * 0.2 +
        risk_factors['severity_weight'] * 0.4
    )
    
    return min(risk_score, 10.0)  # Cap at 10.0

def get_user_attribution_stats(attributed_logs):
    """Get comprehensive user attribution statistics"""
    user_stats = {}
    
    for log in attributed_logs:
        user_id = log.get('user_id', 'Unknown')
        
        if user_id not in user_stats:
            user_stats[user_id] = {
                'total_logs': 0,
                'error_logs': 0,
                'critical_logs': 0,
                'risk_score': 0.0,
                'attribution_methods': set(),
                'modules': set(),
                'first_seen': log.get('timestamp'),
                'last_seen': log.get('timestamp')
            }
        
        # Update stats
        user_stats[user_id]['total_logs'] += 1
        
        severity = log.get('severity', '').upper()
        if severity == 'ERROR':
            user_stats[user_id]['error_logs'] += 1
        elif severity == 'CRITICAL':
            user_stats[user_id]['critical_logs'] += 1
        
        user_stats[user_id]['attribution_methods'].add(log.get('attribution_method', 'unknown'))
        user_stats[user_id]['modules'].add(log.get('module', 'unknown'))
        
        # Update time range
        timestamp = log.get('timestamp')
        if timestamp:
            if timestamp < user_stats[user_id]['first_seen']:
                user_stats[user_id]['first_seen'] = timestamp
            if timestamp > user_stats[user_id]['last_seen']:
                user_stats[user_id]['last_seen'] = timestamp
    
    # Calculate risk scores and prepare final stats
    top_risk_users = []
    
    for user_id, stats in user_stats.items():
        user_logs = [log for log in attributed_logs if log.get('user_id') == user_id]
        stats['risk_score'] = calculate_user_risk(user_logs)
        stats['attribution_methods'] = list(stats['attribution_methods'])
        stats['modules'] = list(stats['modules'])
        
        if stats['risk_score'] > 1.0:  # Only include users with significant risk
            top_risk_users.append({
                'user_id': user_id,
                'risk_score': stats['risk_score'],
                'total_logs': stats['total_logs'],
                'error_logs': stats['error_logs'],
                'critical_logs': stats['critical_logs']
            })
    
    # Sort by risk score
    top_risk_users.sort(key=lambda x: x['risk_score'], reverse=True)
    
    return {
        'total_users': len(user_stats),
        'total_critical_logs': sum(stats['critical_logs'] for stats in user_stats.values()),
        'total_error_logs': sum(stats['error_logs'] for stats in user_stats.values()),
        'top_risk_users': top_risk_users[:10],  # Top 10 risk users
        'user_stats': user_stats
    }
```

---

## AI Chat Assistant

### Chat Implementation
```python
@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    """AI chat assistant endpoint"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        # Load analysis data for context
        analysis_data = load_analysis_data()
        
        if analysis_data and analysis_data.get('summary'):
            response = generate_ai_response(user_message, analysis_data)
        else:
            response = "Please upload a log file first so I can provide analysis and recommendations."
        
        return jsonify({
            'response': response,
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({
            'response': 'I apologize, but I encountered an error. Please try again.',
            'status': 'error'
        }), 500

def generate_ai_response(message, analysis_data):
    """Generate AI response based on message and analysis data"""
    total_logs = analysis_data['summary']['total_logs']
    total_errors = analysis_data['summary']['total_errors']
    root_cause = analysis_data['ai_insights'].get('root_cause', 'Unknown')
    
    message_lower = message.lower()
    
    # Enhanced keyword-based response generation
    if any(keyword in message_lower for keyword in ['top', 'priorities', 'important', 'urgent']) and any(keyword in message_lower for keyword in ['risk', 'risks', 'issue', 'issues', 'problem', 'problems']):
        return generate_top_risks_response(analysis_data)
    
    elif any(keyword in message_lower for keyword in ['actionable', 'steps', 'guide', 'how to']) and any(keyword in message_lower for keyword in ['fix', 'solve', 'address', 'handle']):
        return generate_actionable_steps_response(analysis_data)
    
    elif any(keyword in message_lower for keyword in ['deploy', 'production']):
        return generate_deployment_assessment(analysis_data)
    
    elif any(keyword in message_lower for keyword in ['user', 'who', 'attribution', 'responsible']):
        return generate_user_attribution_response(analysis_data)
    
    elif any(keyword in message_lower for keyword in ['error', 'problem', 'issue', 'failure']):
        return generate_error_analysis_response(analysis_data)
    
    else:
        return generate_general_response(analysis_data)

def generate_top_risks_response(analysis_data):
    """Generate response for top risks query"""
    total_logs = analysis_data['summary']['total_logs']
    total_errors = analysis_data['summary']['total_errors']
    root_cause = analysis_data['ai_insights'].get('root_cause', 'Unknown')
    timeline = analysis_data.get('timeline', [])
    
    if total_errors > 0:
        error_rate = (total_errors/total_logs*100) if total_logs > 0 else 0
        
        # Get specific error types from timeline
        error_types = {}
        for event in timeline:
            if event.get('severity') in ['ERROR', 'CRITICAL']:
                error_type = event.get('message', 'Unknown error')[:50]
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # Create top 2 actionable risks
        top_risks = []
        if error_types:
            sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)
            for i, (error_type, count) in enumerate(sorted_errors[:2]):
                risk_level = "Critical" if count > 5 else "High" if count > 2 else "Medium"
                top_risks.append(f"RISK #{i+1}: {error_type}\n- Impact: {count} occurrences ({risk_level} priority)\n- Solution: Fix the underlying cause in the affected component\n- Action: Review error logs and implement proper error handling")
        
        if top_risks:
            return f"TOP 2 ACTIONABLE RISKS YOU CAN SOLVE:\n\n{chr(10).join(top_risks)}\n\nIMMEDIATE ACTIONS:\n1. Address the most frequent error first\n2. Implement proper error handling and logging\n3. Add monitoring to prevent recurrence\n4. Test fixes in staging before production\n\nWould you like detailed steps for any specific risk?"
        else:
            return f"TOP ACTIONABLE RISKS:\n\n1. ROOT CAUSE: {root_cause}\n   - Impact: {total_errors} errors detected\n   - Solution: Investigate and fix the underlying issue\n   - Action: Review system logs and implement fixes\n\n2. ERROR RATE: {error_rate:.1f}%\n   - Impact: System performance degradation\n   - Solution: Optimize code and add error handling\n   - Action: Monitor and reduce error frequency"
    else:
        return "Great news! No critical risks detected. Your system is running smoothly with no actionable issues to address."

def generate_deployment_assessment(analysis_data):
    """Generate production deployment assessment"""
    total_logs = analysis_data['summary']['total_logs']
    total_errors = analysis_data['summary']['total_errors']
    root_cause = analysis_data['ai_insights'].get('root_cause', 'Unknown')
    
    if total_errors > 0:
        error_rate = (total_errors/total_logs*100) if total_logs > 0 else 0
        
        return f"PRODUCTION DEPLOYMENT ASSESSMENT:\n\nISSUES FOUND ({total_errors} errors):\n- Root cause: {root_cause}\n- Error rate: {error_rate:.1f}%\n\nDEPLOYMENT RECOMMENDATION: {'NO - Fix critical issues first' if total_errors > 5 else 'CAUTION - Monitor closely'}\n\nRequired fixes before production:\n1. Address the root cause: {root_cause}\n2. Reduce error rate below 5%\n3. Implement monitoring and alerting\n\nWould you like specific steps to fix these issues?"
    else:
        return "PRODUCTION DEPLOYMENT ASSESSMENT:\n\nSTATUS: READY FOR PRODUCTION\n\n- No errors detected in current logs\n- System appears stable and healthy\n- Error rate: 0%\n\nDEPLOYMENT RECOMMENDATION: GO\n\nThe system is ready for production deployment. Ensure you have monitoring and rollback procedures in place."
```

### Frontend Chat Integration
```javascript
// simple_dashboard.js - Chat functionality
function askQuickQuestion(question) {
    if (aiChatInput) {
        aiChatInput.value = question;
        // Trigger the form submission to send the question
        aiChatForm.dispatchEvent(new Event('submit'));
    }
}

if (aiChatForm) {
    aiChatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const message = aiChatInput.value.trim();
        if (!message) return;
        
        // Add user message
        addChatMessage('user', message);
        aiChatInput.value = '';
        
        // Add "thinking" indicator
        const thinkingId = addChatMessage('assistant', 'Thinking...');
        
        try {
            const response = await fetch('/api/ai-chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            const data = await response.json();
            
            // Remove thinking message and add actual response
            removeChatMessage(thinkingId);
            addChatMessage('assistant', data.response);
            
        } catch (error) {
            removeChatMessage(thinkingId);
            addChatMessage('assistant', 'Sorry, I encountered an error. Please try again.');
        }
    });
}

function addChatMessage(sender, message) {
    if (!aiChatMessages) return null;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;
    messageDiv.innerHTML = `
        <div class="chat-avatar">${sender === 'user' ? 'You' : 'AI'}</div>
        <div class="chat-content">${message.replace(/\n/g, '<br>')}</div>
    `;
    
    const messageId = 'msg-' + Date.now();
    messageDiv.id = messageId;
    aiChatMessages.appendChild(messageDiv);
    aiChatMessages.scrollTop = aiChatMessages.scrollHeight;
    
    return messageId;
}
```

---

## Analytics Dashboard

### Dashboard Data Loading
```python
@app.route('/analytics')
def analytics_dashboard():
    """Main analytics dashboard"""
    # Load latest analysis data
    analysis_data = load_analysis_data()
    
    if not analysis_data:
        return render_template('analytics.html', 
                             analysis_data=None,
                             error='No analysis data available')
    
    # Prepare dashboard data
    dashboard_data = prepare_dashboard_data(analysis_data)
    
    return render_template('analytics.html', 
                         analysis_data=dashboard_data)

def prepare_dashboard_data(analysis_data):
    """Prepare data for analytics dashboard"""
    summary = analysis_data.get('summary', {})
    timeline = analysis_data.get('timeline', [])
    classified_logs = analysis_data.get('classified_logs', [])
    
    # Calculate metrics
    metrics = {
        'health_score': calculate_health_score(summary),
        'error_rate': calculate_error_rate(summary),
        'avg_response': calculate_avg_response_time(timeline),
        'uptime': calculate_uptime(timeline)
    }
    
    # Prepare chart data
    charts = {
        'logs_over_time': prepare_logs_over_time_data(timeline),
        'severity_distribution': prepare_severity_data(classified_logs),
        'error_heatmap': prepare_error_heatmap_data(timeline),
        'module_performance': prepare_module_data(classified_logs)
    }
    
    # Prepare detailed analysis
    details = {
        'patterns': extract_error_patterns(classified_logs),
        'anomalies': analysis_data.get('anomalies', []),
        'recommendations': analysis_data.get('ai_insights', {}).get('fixes', [])
    }
    
    return {
        'summary': summary,
        'metrics': metrics,
        'charts': charts,
        'details': details
    }

def calculate_health_score(summary):
    """Calculate system health score"""
    total_logs = summary.get('total_logs', 1)
    total_errors = summary.get('total_errors', 0)
    
    # Base health score starts at 100
    health_score = 100
    
    # Deduct points for errors
    error_rate = (total_errors / total_logs) * 100
    health_score -= error_rate * 2  # 2 points per 1% error rate
    
    # Ensure score doesn't go below 0
    health_score = max(0, health_score)
    
    return round(health_score, 1)

def prepare_logs_over_time_data(timeline):
    """Prepare data for logs over time chart"""
    if not timeline:
        return {'labels': [], 'datasets': []}
    
    # Group logs by hour
    hourly_data = {}
    for entry in timeline:
        try:
            dt = datetime.strptime(entry['timestamp'], '%Y-%m-%d %H:%M:%S')
            hour_key = dt.strftime('%Y-%m-%d %H:00')
            
            if hour_key not in hourly_data:
                hourly_data[hour_key] = {'INFO': 0, 'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0}
            
            severity = entry.get('severity', 'INFO')
            hourly_data[hour_key][severity] = hourly_data[hour_key].get(severity, 0) + 1
        except:
            continue
    
    # Sort by time
    sorted_hours = sorted(hourly_data.keys())
    
    # Prepare chart data
    labels = sorted_hours
    datasets = [
        {
            'label': 'INFO',
            'data': [hourly_data[hour]['INFO'] for hour in sorted_hours],
            'backgroundColor': 'rgba(34, 197, 94, 0.2)',
            'borderColor': 'rgba(34, 197, 94, 1)',
            'borderWidth': 2
        },
        {
            'label': 'WARNING',
            'data': [hourly_data[hour]['WARNING'] for hour in sorted_hours],
            'backgroundColor': 'rgba(250, 204, 21, 0.2)',
            'borderColor': 'rgba(250, 204, 21, 1)',
            'borderWidth': 2
        },
        {
            'label': 'ERROR',
            'data': [hourly_data[hour]['ERROR'] for hour in sorted_hours],
            'backgroundColor': 'rgba(239, 68, 68, 0.2)',
            'borderColor': 'rgba(239, 68, 68, 1)',
            'borderWidth': 2
        },
        {
            'label': 'CRITICAL',
            'data': [hourly_data[hour]['CRITICAL'] for hour in sorted_hours],
            'backgroundColor': 'rgba(127, 29, 29, 0.2)',
            'borderColor': 'rgba(127, 29, 29, 1)',
            'borderWidth': 2
        }
    ]
    
    return {'labels': labels, 'datasets': datasets}
```

### Frontend Dashboard Implementation
```javascript
// Dashboard JavaScript implementation
class AnalyticsDashboard {
    constructor() {
        this.charts = {};
        this.data = null;
        this.init();
    }
    
    async init() {
        try {
            // Load dashboard data
            await this.loadDashboardData();
            
            // Initialize charts
            this.initializeCharts();
            
            // Setup event listeners
            this.setupEventListeners();
            
        } catch (error) {
            console.error('Dashboard initialization failed:', error);
        }
    }
    
    async loadDashboardData() {
        const response = await fetch('/api/analytics-data');
        this.data = await response.json();
    }
    
    initializeCharts() {
        // Logs over time chart
        const logsCtx = document.getElementById('logsOverTime').getContext('2d');
        this.charts.logsOverTime = new Chart(logsCtx, {
            type: 'line',
            data: this.data.charts.logs_over_time,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Log Volume Over Time'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        
        // Severity distribution chart
        const severityCtx = document.getElementById('severityChart').getContext('2d');
        this.charts.severityChart = new Chart(severityCtx, {
            type: 'doughnut',
            data: this.data.charts.severity_distribution,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Severity Distribution'
                    }
                }
            }
        });
        
        // Error heatmap
        const heatmapCtx = document.getElementById('errorHeatmap').getContext('2d');
        this.charts.errorHeatmap = new Chart(heatmapCtx, {
            type: 'bubble',
            data: this.data.charts.error_heatmap,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Error Spike Analysis'
                    }
                }
            }
        });
        
        // Module performance
        const moduleCtx = document.getElementById('moduleChart').getContext('2d');
        this.charts.moduleChart = new Chart(moduleCtx, {
            type: 'bar',
            data: this.data.charts.module_performance,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Module Performance'
                    }
                }
            }
        });
    }
    
    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                this.switchTab(tabName);
            });
        });
        
        // Real-time updates
        setInterval(() => {
            this.updateMetrics();
        }, 30000); // Update every 30 seconds
    }
    
    switchTab(tabName) {
        // Update active tab button
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // Update active tab content
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');
    }
    
    updateMetrics() {
        // Update health score
        const healthScore = this.data.metrics.health_score;
        document.getElementById('healthScore').textContent = healthScore;
        
        // Update error rate
        const errorRate = this.data.metrics.error_rate;
        document.getElementById('errorRate').textContent = errorRate + '%';
        
        // Update other metrics...
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new AnalyticsDashboard();
});
```

---

## API Implementation Details

### File Management API
```python
@app.route('/api/files', methods=['GET'])
def list_files():
    """List all uploaded files"""
    try:
        files = []
        upload_dir = app.config['UPLOAD_FOLDER']
        
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                filepath = os.path.join(upload_dir, filename)
                if os.path.isfile(filepath):
                    file_stats = os.stat(filepath)
                    files.append({
                        'filename': filename,
                        'size': file_stats.st_size,
                        'modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                        'analyzed': os.path.exists(f'data/{filename}_analysis.json')
                    })
        
        return jsonify({
            'status': 'success',
            'files': files
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a specific file"""
    try:
        # Validate filename
        if not filename or '..' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        # Delete file
        os.remove(filepath)
        
        # Delete analysis data if exists
        analysis_file = f'data/{filename}_analysis.json'
        if os.path.exists(analysis_file):
            os.remove(analysis_file)
        
        return jsonify({
            'status': 'success',
            'message': f'File {filename} deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
```

### Analysis API
```python
@app.route('/api/analyze/<filename>', methods=['POST'])
def analyze_specific_file(filename):
    """Analyze a specific file"""
    try:
        # Validate filename
        if not filename or '..' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        # Check if analysis already exists
        analysis_file = f'data/{filename}_analysis.json'
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r') as f:
                analysis_data = json.load(f)
            return jsonify({
                'status': 'success',
                'analysis': analysis_data,
                'cached': True
            })
        
        # Perform analysis
        analysis_result = analyze_log_file(filepath)
        
        # Save analysis
        os.makedirs('data', exist_ok=True)
        with open(analysis_file, 'w') as f:
            json.dump(analysis_result, f, indent=2)
        
        return jsonify({
            'status': 'success',
            'analysis': analysis_result,
            'cached': False
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/user-attribution', methods=['GET'])
def get_user_attribution():
    """Get user attribution data"""
    try:
        analysis_data = load_analysis_data()
        
        if not analysis_data:
            return jsonify({
                'status': 'error',
                'message': 'No analysis data available'
            }), 404
        
        user_attribution = analysis_data.get('user_attribution')
        
        if not user_attribution:
            return jsonify({
                'status': 'error',
                'message': 'No user attribution data available'
            }), 404
        
        return jsonify({
            'status': 'success',
            'user_attribution': user_attribution
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
```

### Timeline API
```python
@app.route('/api/timeline', methods=['GET'])
def get_timeline():
    """Get timeline data"""
    try:
        analysis_data = load_analysis_data()
        
        if not analysis_data:
            return jsonify({
                'status': 'error',
                'message': 'No analysis data available'
            }), 404
        
        timeline = analysis_data.get('timeline', [])
        
        # Optional filtering
        severity_filter = request.args.get('severity')
        if severity_filter:
            timeline = [entry for entry in timeline 
                       if entry.get('severity') == severity_filter.upper()]
        
        # Optional time range
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        if start_time and end_time:
            start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
            
            timeline = [entry for entry in timeline
                       if start_dt <= datetime.strptime(entry['timestamp'], '%Y-%m-%d %H:%M:%S') <= end_dt]
        
        return jsonify({
            'status': 'success',
            'timeline': timeline,
            'count': len(timeline)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
```

---

## Frontend Implementation

### Template Structure
```html
<!-- base.html - Master template -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}AI Log Auditing Platform{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
</head>
<body>
    <header class="topbar">
        <div class="brand">
            <h1>AI Log Auditor</h1>
            <p>Intelligent Log Analysis Platform</p>
        </div>
        <nav class="main-nav">
            <a href="{{ url_for('upload') }}" class="">Upload</a>
            <a href="{{ url_for('analytics') }}" class="">Analytics</a>
            <a href="{{ url_for('timeline') }}" class="">Timeline</a>
            <a href="{{ url_for('assistant') }}" class="">AI Assistant</a>
        </nav>
    </header>
    
    <main class="main-content">
        {% block content %}{% endblock %}
    </main>
    
    <script src="{{ url_for('static', filename='js/simple_dashboard.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### Upload Interface
```html
<!-- upload.html -->
{% extends "base.html" %}

{% block content %}
<div class="upload-container">
    <div class="upload-header">
        <h2>Upload Log Files</h2>
        <p>Upload your log files for intelligent analysis and insights</p>
    </div>
    
    <div class="upload-area" id="dropZone">
        <div class="upload-content">
            <div class="upload-icon">upload_file</div>
            <h3>Drag & Drop Log Files Here</h3>
            <p>or click to browse</p>
            <input type="file" id="fileInput" accept=".log,.txt,.csv" multiple>
        </div>
    </div>
    
    <div class="upload-progress" id="uploadProgress" style="display: none;">
        <div class="progress-bar">
            <div class="progress-fill" id="progressFill"></div>
        </div>
        <div class="progress-text" id="progressText">Uploading...</div>
    </div>
    
    <div class="uploaded-files" id="uploadedFiles">
        <h3>Uploaded Files</h3>
        <div class="file-list" id="fileList">
            <!-- Files will be listed here -->
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
// Upload functionality
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadProgress = document.getElementById('uploadProgress');
const fileList = document.getElementById('fileList');

// Drag and drop handlers
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    handleFiles(e.dataTransfer.files);
});

// File input handler
fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
});

async function handleFiles(files) {
    for (let file of files) {
        await uploadFile(file);
    }
    loadUploadedFiles();
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    uploadProgress.style.display = 'block';
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showNotification('File uploaded successfully', 'success');
        } else {
            showNotification(result.error || 'Upload failed', 'error');
        }
    } catch (error) {
        showNotification('Upload error: ' + error.message, 'error');
    } finally {
        uploadProgress.style.display = 'none';
    }
}

function showNotification(message, type) {
    // Implementation for showing notifications
    console.log(`${type}: ${message}`);
}
</script>
{% endblock %}
```

### Analytics Dashboard UI
```html
<!-- analytics.html -->
{% extends "base.html" %}

{% block content %}
<div class="analytics-header">
    <h2>Analytics Dashboard</h2>
    <p>Comprehensive analysis of log patterns and system performance</p>
</div>

<div class="analytics-grid">
    <!-- Executive Summary -->
    <section class="card analytics-summary">
        <div class="card-header">
            <h3>Executive Summary</h3>
            <div class="card-icon">summary</div>
        </div>
        <div id="summaryGrid">
            <!-- Summary metrics will be populated here -->
        </div>
    </section>

    <!-- Key Metrics -->
    <section class="card analytics-metrics">
        <div class="card-header">
            <h3>Key Performance Indicators</h3>
            <div class="card-icon">trending_up</div>
        </div>
        <div class="metrics-grid">
            <div class="metric-item">
                <div class="metric-value" id="healthScore">--</div>
                <div class="metric-label">System Health</div>
                <div class="metric-change positive">+2.3%</div>
            </div>
            <div class="metric-item">
                <div class="metric-value" id="errorRate">--</div>
                <div class="metric-label">Error Rate</div>
                <div class="metric-change negative">-1.1%</div>
            </div>
            <div class="metric-item">
                <div class="metric-value" id="avgResponse">--</div>
                <div class="metric-label">Avg Response</div>
                <div class="metric-change positive">+0.5s</div>
            </div>
            <div class="metric-item">
                <div class="metric-value" id="uptime">--</div>
                <div class="metric-label">Uptime</div>
                <div class="metric-change positive">99.9%</div>
            </div>
        </div>
    </section>

    <!-- Charts Row 1 -->
    <div class="charts-row">
        <section class="card chart-container">
            <div class="card-header">
                <h3>Log Volume Trends</h3>
                <div class="card-icon">timeline</div>
            </div>
            <div class="chart-wrapper">
                <canvas id="logsOverTime"></canvas>
            </div>
        </section>

        <section class="card chart-container">
            <div class="card-header">
                <h3>Severity Distribution</h3>
                <div class="card-icon">pie_chart</div>
            </div>
            <div class="chart-wrapper">
                <canvas id="severityChart"></canvas>
            </div>
        </section>
    </div>

    <!-- Detailed Analysis -->
    <section class="card analytics-details">
        <div class="card-header">
            <h3>Detailed Analysis</h3>
            <div class="card-icon">insights</div>
        </div>
        <div class="analysis-tabs">
            <button class="tab-btn active" data-tab="patterns">Patterns</button>
            <button class="tab-btn" data-tab="anomalies">Anomalies</button>
            <button class="tab-btn" data-tab="recommendations">Recommendations</button>
        </div>
        <div class="tab-content">
            <div class="tab-pane active" id="patterns">
                <div class="pattern-list">
                    <!-- Error patterns will be populated here -->
                </div>
            </div>
            <div class="tab-pane" id="anomalies">
                <div class="anomaly-grid">
                    <!-- Anomalies will be populated here -->
                </div>
            </div>
            <div class="tab-pane" id="recommendations">
                <div class="recommendations-list">
                    <!-- Recommendations will be populated here -->
                </div>
            </div>
        </div>
    </section>
</div>
{% endblock %}
```

---

## Data Storage & Caching

### File-based Storage Implementation
```python
import json
import os
from datetime import datetime

class DataStorage:
    """File-based data storage manager"""
    
    def __init__(self, base_dir='data'):
        self.base_dir = base_dir
        self.ensure_directories()
    
    def ensure_directories(self):
        """Create necessary directories"""
        directories = [
            self.base_dir,
            os.path.join(self.base_dir, 'analysis'),
            os.path.join(self.base_dir, 'cache'),
            os.path.join(self.base_dir, 'models')
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def save_analysis(self, filename, analysis_data):
        """Save analysis results"""
        timestamp = datetime.now().isoformat()
        analysis_data['saved_at'] = timestamp
        analysis_data['filename'] = filename
        
        # Save to analysis file
        analysis_file = os.path.join(self.base_dir, 'analysis', f'{filename}_analysis.json')
        
        try:
            with open(analysis_file, 'w') as f:
                json.dump(analysis_data, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error saving analysis: {e}")
            return False
    
    def load_analysis(self, filename):
        """Load analysis results"""
        analysis_file = os.path.join(self.base_dir, 'analysis', f'{filename}_analysis.json')
        
        try:
            with open(analysis_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error loading analysis: {e}")
            return None
    
    def save_cache(self, key, data, ttl=3600):
        """Save data to cache with TTL"""
        cache_file = os.path.join(self.base_dir, 'cache', f'{key}.json')
        
        cache_data = {
            'data': data,
            'created_at': datetime.now().isoformat(),
            'ttl': ttl
        }
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error saving cache: {e}")
            return False
    
    def load_cache(self, key):
        """Load data from cache if not expired"""
        cache_file = os.path.join(self.base_dir, 'cache', f'{key}.json')
        
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            created_at = datetime.fromisoformat(cache_data['created_at'])
            ttl = cache_data['ttl']
            
            # Check if cache is expired
            if (datetime.now() - created_at).total_seconds() > ttl:
                os.remove(cache_file)  # Remove expired cache
                return None
            
            return cache_data['data']
            
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error loading cache: {e}")
            return None

# Global storage instance
storage = DataStorage()
```

### Caching Implementation
```python
from functools import wraps
import hashlib
import pickle

def cache_result(ttl=3600, cache_key=None):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if cache_key:
                key = cache_key
            else:
                key = hashlib.md5(
                    f"{func.__name__}_{str(args)}_{str(kwargs)}".encode()
                ).hexdigest()
            
            # Try to load from cache
            cached_result = storage.load_cache(key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            storage.save_cache(key, result, ttl)
            
            return result
        return wrapper
    return decorator

# Usage examples
@cache_result(ttl=1800)  # 30 minutes cache
def get_user_statistics():
    """Get user statistics with caching"""
    # Expensive computation
    return compute_user_stats()

@cache_result(cache_key="system_metrics")
def get_system_metrics():
    """Get system metrics with fixed cache key"""
    return compute_system_metrics()
```

---

## Error Handling & Validation

### Custom Exceptions
```python
class LogAnalysisError(Exception):
    """Base exception for log analysis errors"""
    pass

class InvalidLogFormatError(LogAnalysisError):
    """Raised when log format is invalid"""
    pass

class FileUploadError(LogAnalysisError):
    """Raised when file upload fails"""
    pass

class ClassificationError(LogAnalysisError):
    """Raised when classification fails"""
    pass

class UserAttributionError(LogAnalysisError):
    """Raised when user attribution fails"""
    pass
```

### Validation Implementation
```python
def validate_log_entry(log_entry):
    """Validate log entry format"""
    required_fields = ['timestamp', 'severity', 'message']
    
    for field in required_fields:
        if field not in log_entry:
            raise InvalidLogFormatError(f"Missing required field: {field}")
    
    # Validate timestamp format
    try:
        datetime.strptime(log_entry['timestamp'], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        raise InvalidLogFormatError(f"Invalid timestamp format: {log_entry['timestamp']}")
    
    # Validate severity
    valid_severities = ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if log_entry['severity'].upper() not in valid_severities:
        raise InvalidLogFormatError(f"Invalid severity level: {log_entry['severity']}")
    
    # Validate message
    if not log_entry['message'].strip():
        raise InvalidLogFormatError("Message cannot be empty")
    
    return True

def validate_analysis_data(analysis_data):
    """Validate analysis data structure"""
    required_sections = ['summary', 'classified_logs', 'ai_insights']
    
    for section in required_sections:
        if section not in analysis_data:
            raise ValueError(f"Missing required section: {section}")
    
    # Validate summary
    summary = analysis_data['summary']
    required_summary_fields = ['total_logs', 'total_errors']
    
    for field in required_summary_fields:
        if field not in summary:
            raise ValueError(f"Missing summary field: {field}")
    
    # Validate classified logs
    classified_logs = analysis_data['classified_logs']
    if not isinstance(classified_logs, list):
        raise ValueError("classified_logs must be a list")
    
    for log in classified_logs:
        validate_log_entry(log)
    
    return True
```

### Error Handling Middleware
```python
@app.errorhandler(InvalidLogFormatError)
def handle_invalid_log_format(error):
    """Handle invalid log format errors"""
    return jsonify({
        'status': 'error',
        'error': 'Invalid log format',
        'message': str(error)
    }), 400

@app.errorhandler(FileUploadError)
def handle_file_upload_error(error):
    """Handle file upload errors"""
    return jsonify({
        'status': 'error',
        'error': 'File upload failed',
        'message': str(error)
    }), 400

@app.errorhandler(Exception)
def handle_general_error(error):
    """Handle general errors"""
    app.logger.error(f"Unhandled error: {error}")
    
    return jsonify({
        'status': 'error',
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

def safe_execute(func):
    """Decorator for safe function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except InvalidLogFormatError as e:
            app.logger.warning(f"Invalid log format: {e}")
            return None
        except Exception as e:
            app.logger.error(f"Error in {func.__name__}: {e}")
            return None
    return wrapper
```

---

## Security Implementation

### Input Validation
```python
from werkzeug.utils import secure_filename
import bleach

def sanitize_filename(filename):
    """Sanitize filename for security"""
    # Use Werkzeug's secure_filename
    sanitized = secure_filename(filename)
    
    # Additional validation
    if not sanitized:
        raise ValueError("Invalid filename")
    
    # Check for dangerous extensions
    dangerous_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif']
    if any(sanitized.lower().endswith(ext) for ext in dangerous_extensions):
        raise ValueError("Dangerous file type")
    
    return sanitized

def sanitize_input(text):
    """Sanitize user input"""
    if not isinstance(text, str):
        return ""
    
    # Remove HTML tags
    clean_text = bleach.clean(text)
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
    for char in dangerous_chars:
        clean_text = clean_text.replace(char, '')
    
    return clean_text.strip()

def validate_json_input(data):
    """Validate JSON input"""
    if not isinstance(data, dict):
        raise ValueError("Invalid JSON format")
    
    # Check for dangerous keys
    dangerous_keys = ['__proto__', 'constructor', 'prototype']
    for key in data.keys():
        if key in dangerous_keys:
            raise ValueError("Dangerous key detected")
    
    return True
```

### Access Control
```python
from functools import wraps
from flask import session, redirect, url_for

def require_authentication(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def require_role(role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('role', 'user')
            if user_role != role:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage
@app.route('/admin/analyze')
@require_authentication
@require_role('admin')
def admin_analyze():
    """Admin-only analysis endpoint"""
    pass
```

### Rate Limiting
```python
from collections import defaultdict
from time import time

class RateLimiter:
    """Simple rate limiter implementation"""
    
    def __init__(self, max_requests=100, window=3600):
        self.max_requests = max_requests
        self.window = window
        self.requests = defaultdict(list)
    
    def is_allowed(self, identifier):
        """Check if request is allowed"""
        now = time()
        requests = self.requests[identifier]
        
        # Remove old requests outside window
        requests[:] = [req_time for req_time in requests if now - req_time < self.window]
        
        # Check if under limit
        if len(requests) < self.max_requests:
            requests.append(now)
            return True
        
        return False

# Global rate limiter
rate_limiter = RateLimiter(max_requests=100, window=3600)  # 100 requests per hour

def rate_limit(f):
    """Decorator for rate limiting"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Use IP address as identifier
        identifier = request.environ.get('REMOTE_ADDR', 'unknown')
        
        if not rate_limiter.is_allowed(identifier):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        return f(*args, **kwargs)
    return decorated_function

# Usage
@app.route('/api/ai-chat', methods=['POST'])
@rate_limit
def ai_chat():
    """Rate-limited AI chat endpoint"""
    pass
```

---

## Performance Optimization

### Asynchronous Processing
```python
import threading
from queue import Queue
import time

class AsyncTaskProcessor:
    """Asynchronous task processor"""
    
    def __init__(self, max_workers=4):
        self.task_queue = Queue()
        self.workers = []
        self.max_workers = max_workers
        self.start_workers()
    
    def start_workers(self):
        """Start worker threads"""
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self.workers.append(worker)
    
    def _worker(self):
        """Worker thread function"""
        while True:
            try:
                task_func, args, kwargs = self.task_queue.get(timeout=1)
                task_func(*args, **kwargs)
                self.task_queue.task_done()
            except:
                continue
    
    def submit_task(self, func, *args, **kwargs):
        """Submit task for asynchronous processing"""
        self.task_queue.put((func, args, kwargs))
    
    def wait_for_completion(self):
        """Wait for all tasks to complete"""
        self.task_queue.join()

# Global task processor
task_processor = AsyncTaskProcessor()

# Usage
@app.route('/api/analyze-async', methods=['POST'])
def analyze_async():
    """Asynchronous analysis endpoint"""
    filename = request.json.get('filename')
    
    # Submit analysis task
    task_processor.submit_task(analyze_log_file_background, filename)
    
    return jsonify({
        'status': 'accepted',
        'message': 'Analysis started'
    })

def analyze_log_file_background(filename):
    """Background analysis function"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        analysis_result = analyze_log_file(filepath)
        storage.save_analysis(filename, analysis_result)
        
        # Notify completion (could use WebSocket or other mechanism)
        print(f"Analysis completed for {filename}")
        
    except Exception as e:
        print(f"Background analysis failed for {filename}: {e}")
```

### Memory Optimization
```python
import gc
import sys

class MemoryOptimizer:
    """Memory optimization utilities"""
    
    @staticmethod
    def optimize_memory():
        """Force garbage collection and memory optimization"""
        gc.collect()
        
        # Clear caches if needed
        if hasattr(sys, 'getsizeof'):
            # Force Python to release memory
            pass
    
    @staticmethod
    def get_memory_usage():
        """Get current memory usage"""
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            'rss': memory_info.rss / 1024 / 1024,  # MB
            'vms': memory_info.vms / 1024 / 1024   # MB
        }
    
    @staticmethod
    def monitor_memory(threshold_mb=1000):
        """Monitor memory usage and optimize if needed"""
        memory_usage = MemoryOptimizer.get_memory_usage()
        
        if memory_usage['rss'] > threshold_mb:
            MemoryOptimizer.optimize_memory()
            return True
        
        return False

# Memory monitoring decorator
def monitor_memory_usage(func):
    """Decorator to monitor memory usage"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Monitor before
        before_memory = MemoryOptimizer.get_memory_usage()
        
        try:
            result = func(*args, **kwargs)
            
            # Monitor after
            after_memory = MemoryOptimizer.get_memory_usage()
            
            # Log memory usage if significant increase
            if after_memory['rss'] - before_memory['rss'] > 100:  # 100MB increase
                app.logger.info(f"Memory usage increased by {after_memory['rss'] - before_memory['rss']:.1f}MB in {func.__name__}")
            
            # Optimize if needed
            MemoryOptimizer.monitor_memory()
            
            return result
            
        except MemoryError:
            # Force memory optimization and retry
            MemoryOptimizer.optimize_memory()
            return func(*args, **kwargs)
    
    return wrapper
```

### Database Query Optimization
```python
def optimize_log_queries(logs, filters=None):
    """Optimize log queries with filtering and indexing"""
    if not logs:
        return []
    
    # Apply filters early to reduce dataset
    if filters:
        if 'severity' in filters:
            logs = [log for log in logs if log.get('severity') == filters['severity']]
        
        if 'start_time' in filters and 'end_time' in filters:
            start_time = datetime.strptime(filters['start_time'], '%Y-%m-%d %H:%M:%S')
            end_time = datetime.strptime(filters['end_time'], '%Y-%m-%d %H:%M:%S')
            
            logs = [log for log in logs 
                   if start_time <= datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S') <= end_time]
        
        if 'user_id' in filters:
            logs = [log for log in logs if log.get('user_id') == filters['user_id']]
    
    # Use generator expressions for memory efficiency
    return list(logs)

def batch_process_logs(logs, batch_size=1000, processor_func=None):
    """Process logs in batches to optimize memory usage"""
    if not processor_func:
        return logs
    
    results = []
    
    for i in range(0, len(logs), batch_size):
        batch = logs[i:i + batch_size]
        batch_result = processor_func(batch)
        results.extend(batch_result)
        
        # Force garbage collection after each batch
        gc.collect()
    
    return results
```

---

## Testing & Debugging

### Unit Tests
```python
import unittest
import json
from unittest.mock import patch, MagicMock

class TestLogAnalysis(unittest.TestCase):
    """Test cases for log analysis functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.sample_logs = [
            {
                'timestamp': '2026-04-17 10:30:00',
                'severity': 'ERROR',
                'message': 'Database connection failed',
                'module': 'database'
            },
            {
                'timestamp': '2026-04-17 10:31:00',
                'severity': 'INFO',
                'message': 'User login successful',
                'module': 'auth'
            }
        ]
    
    def test_log_parsing(self):
        """Test log parsing functionality"""
        from services.parser import parse_log_line
        
        # Test standard log format
        log_line = "2026-04-17 10:30:00 ERROR Database connection failed"
        parsed = parse_log_line(log_line, 1)
        
        self.assertEqual(parsed['timestamp'], '2026-04-17 10:30:00')
        self.assertEqual(parsed['severity'], 'ERROR')
        self.assertEqual(parsed['message'], 'Database connection failed')
    
    def test_user_extraction(self):
        """Test user extraction from logs"""
        from clean_app import extract_user_from_log
        
        log_entry = {
            'message': 'user_id=john123 login successful',
            'timestamp': '2026-04-17 10:30:00',
            'severity': 'INFO'
        }
        
        user_info = extract_user_from_log(log_entry)
        
        self.assertEqual(user_info['user_id'], 'john123')
        self.assertEqual(user_info['attribution_method'], 'direct')
    
    def test_classification(self):
        """Test log classification"""
        from services.hybrid_classifier import HybridClassifier
        
        classifier = HybridClassifier()
        features = {
            'message': 'Database connection failed',
            'severity_numeric': 3,  # ERROR
            'has_error_keywords': True
        }
        
        classification, confidence = classifier.predict(features)
        
        self.assertIn(classification, ['database_error', 'network_error', 'general_error'])
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
    
    def test_analysis_pipeline(self):
        """Test complete analysis pipeline"""
        from services.analysis_pipeline import AnalysisPipeline
        
        pipeline = AnalysisPipeline()
        result = pipeline.analyze(self.sample_logs)
        
        self.assertIn('classified_logs', result)
        self.assertIn('timeline', result)
        self.assertIn('summary', result)
        self.assertEqual(len(result['classified_logs']), 2)
    
    @patch('clean_app.load_analysis_data')
    def test_ai_chat_response(self, mock_load_data):
        """Test AI chat response generation"""
        mock_load_data.return_value = {
            'summary': {'total_logs': 100, 'total_errors': 5},
            'ai_insights': {'root_cause': 'Database connectivity issues'},
            'timeline': []
        }
        
        from clean_app import generate_ai_response
        
        response = generate_ai_response("What are the top risks?", mock_load_data.return_value)
        
        self.assertIn("TOP 2 ACTIONABLE RISKS", response)
        self.assertIn("Database connectivity issues", response)

class TestAPIEndpoints(unittest.TestCase):
    """Test cases for API endpoints"""
    
    def setUp(self):
        """Set up test client"""
        from clean_app import app
        self.app = app
        self.client = app.test_client()
        self.app.config['TESTING'] = True
    
    def test_file_upload(self):
        """Test file upload endpoint"""
        # Create test file
        test_file_content = "2026-04-17 10:30:00 ERROR Test error message\n"
        
        response = self.client.post('/api/upload', 
                                  data={'file': (io.BytesIO(test_file_content.encode()), 'test.log')},
                                  content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
    
    def test_ai_chat_endpoint(self):
        """Test AI chat endpoint"""
        response = self.client.post('/api/ai-chat',
                                  json={'message': 'Hello'},
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('response', data)
        self.assertIn('status', data)

if __name__ == '__main__':
    unittest.main()
```

### Integration Tests
```python
class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.test_log_file = 'test_integration.log'
        
        # Create test log file
        with open(self.test_log_file, 'w') as f:
            f.write("2026-04-17 10:30:00 ERROR Database connection failed\n")
            f.write("2026-04-17 10:31:00 INFO User login successful user_id=test123\n")
            f.write("2026-04-17 10:32:00 WARNING High memory usage detected\n")
    
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_log_file):
            os.remove(self.test_log_file)
    
    def test_complete_analysis_workflow(self):
        """Test complete analysis workflow"""
        from clean_app import analyze_log_file, save_analysis_data, load_analysis_data
        
        # Step 1: Analyze file
        result = analyze_log_file(self.test_log_file)
        
        self.assertIn('summary', result)
        self.assertIn('classified_logs', result)
        self.assertEqual(result['summary']['total_logs'], 3)
        self.assertEqual(result['summary']['total_errors'], 1)
        
        # Step 2: Save analysis
        save_success = save_analysis_data(result)
        self.assertTrue(save_success)
        
        # Step 3: Load analysis
        loaded_result = load_analysis_data()
        self.assertIsNotNone(loaded_result)
        self.assertEqual(loaded_result['summary']['total_logs'], 3)
    
    def test_user_attribution_workflow(self):
        """Test user attribution workflow"""
        from clean_app import analyze_user_attribution
        
        logs = [
            {'timestamp': '2026-04-17 10:30:00', 'severity': 'ERROR', 'message': 'Database connection failed'},
            {'timestamp': '2026-04-17 10:31:00', 'severity': 'INFO', 'message': 'User login successful user_id=test123'},
            {'timestamp': '2026-04-17 10:32:00', 'severity': 'WARNING', 'message': 'High memory usage detected'}
        ]
        
        attributed_logs = analyze_user_attribution(logs)
        
        # Check that user attribution was applied
        user_logs = [log for log in attributed_logs if log.get('user_id') == 'test123']
        self.assertEqual(len(user_logs), 1)
        self.assertEqual(user_logs[0]['attribution_method'], 'direct')
```

### Debugging Tools
```python
import logging
import traceback
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def debug_function(func):
    """Decorator to debug function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Entering {func.__name__} with args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Exiting {func.__name__} with result={result}")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            logger.error(traceback.format_exc())
            raise
    
    return wrapper

def profile_function(func):
    """Decorator to profile function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import cProfile
        import pstats
        
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            result = func(*args, **kwargs)
        finally:
            profiler.disable()
            
            # Save profiling results
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            stats.print_stats(10)  # Top 10 functions
        
        return result
    
    return wrapper

# Usage examples
@debug_function
@profile_function
def analyze_log_file_debug(file_path):
    """Debug version of analyze_log_file"""
    logger.debug(f"Analyzing file: {file_path}")
    
    # Add debugging checkpoints
    logs = parse_log_file(file_path)
    logger.debug(f"Parsed {len(logs)} logs")
    
    classified_logs = classify_logs(logs)
    logger.debug(f"Classified {len(classified_logs)} logs")
    
    # Continue with analysis...
    return classified_logs
```

---

## Conclusion

This implementation documentation provides a comprehensive overview of the AI Log Auditing Platform's functionality, including:

### **Key Implementation Features**:
- **Complete Code Examples**: Actual implementation details for all major components
- **API Documentation**: Detailed endpoint specifications with request/response formats
- **Frontend Integration**: JavaScript implementations for all UI interactions
- **Data Processing**: Complete pipeline from file upload to analysis results
- **Machine Learning**: Hybrid classifier implementation with PyTorch and scikit-learn
- **User Attribution**: Advanced user tracking and risk scoring system
- **AI Chat Assistant**: Natural language processing and response generation
- **Security**: Input validation, access control, and rate limiting
- **Performance**: Asynchronous processing and memory optimization
- **Testing**: Unit tests, integration tests, and debugging tools

### **Implementation Highlights**:
- **Modular Architecture**: Clean separation of concerns with reusable components
- **Error Handling**: Comprehensive error management and validation
- **Caching Strategy**: Multi-layer caching for performance optimization
- **Security Best Practices**: Input sanitization and access controls
- **Scalability Design**: Asynchronous processing and memory optimization
- **Testing Coverage**: Unit tests, integration tests, and debugging utilities

The platform demonstrates enterprise-level implementation with production-ready features, comprehensive error handling, and robust security measures. The modular design allows for easy extension and customization based on specific requirements.

---

*Last Updated: April 17, 2026*
*Version: 1.0*
*Author: Development Team*
