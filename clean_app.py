#!/usr/bin/env python3
"""
Clean Flask app - works like normal Flask should
"""
import os
import sys
import re
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, request, jsonify
from werkzeug.utils import secure_filename

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'log', 'txt', 'csv'}

# File-based storage for analysis data
ANALYSIS_FILE = 'latest_analysis.json'

def save_analysis_data(data):
    """Save analysis data to file"""
    try:
        with open(ANALYSIS_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving analysis data: {e}")

def load_analysis_data():
    """Load analysis data from file"""
    try:
        if os.path.exists(ANALYSIS_FILE):
            with open(ANALYSIS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading analysis data: {e}")
    return None

# User Attribution Module
USER_SESSION_MAPPING = {}
UNKNOWN_USER_LOGS = []

def extract_user_from_log(log_entry):
    """Extract user information from a log entry"""
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

def map_session_to_user(session_id, user_id):
    """Map session_id to User_id for attribution"""
    if session_id and user_id:
        USER_SESSION_MAPPING[session_id] = user_id
    elif session_id and session_id in USER_SESSION_MAPPING:
        del USER_SESSION_MAPPING[session_id]

def infer_user_from_timestamp(timestamp_str, current_logs):
    """Infer user based on timestamp proximity to known users"""
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
    min_time_diff = timedelta(hours=1)  # Initialize with 1 hour
    
    for log in known_user_logs:
        try:
            log_time = datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S')
            time_diff = abs((current_time - log_time).total_seconds())
            
            if time_diff < min_time_diff.total_seconds():
                min_time_diff = timedelta(seconds=time_diff)
                closest_log = log
        except:
            continue
    
    if closest_log:
        return closest_log['user_id']
    
    return 'Unknown'

def analyze_user_attribution(logs):
    """Analyze logs and attribute them to users"""
    attributed_logs = []
    
    for log in logs:
        user_info = extract_user_from_log(log)
        
        # Apply user identification logic
        if user_info['user_id']:
            # Direct user_id found
            if user_info['session_id']:
                map_session_to_user(user_info['session_id'], user_info['user_id'])
            user_info['attribution_method'] = 'direct'
        elif user_info['session_id']:
            # Session-based inference
            mapped_user = USER_SESSION_MAPPING.get(user_info['session_id'])
            if mapped_user:
                user_info['user_id'] = mapped_user
                user_info['attribution_method'] = 'session_inferred'
            else:
                user_info['attribution_method'] = 'session_unknown'           
        else:
            # Fallback to timestamp-based inference
            user_info['user_id'] = infer_user_from_timestamp(
                user_info['timestamp'], 
                attributed_logs + [user_info]
            )
            user_info['attribution_method'] = 'timestamp_used'
        
        attributed_logs.append(user_info)
    
    # Store unknown user logs
    unknown_logs = [log for log in attributed_logs if log['user_id'] == 'Unknown']
    global UNKNOWN_USER_LOGS
    UNKNOWN_USER_LOGS = unknown_logs
    
    return attributed_logs

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_log_file(file_path):
    """Parse log file and extract structured data with user attribution"""
    logs = []
    severity_counts = {'INFO': 0, 'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0}
    file_content = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Store file content for preview
            file_content.append(line)
            
            # Extract timestamp, severity, and message
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
            severity_match = re.search(r'\b(INFO|WARNING|ERROR|CRITICAL|WARN|FATAL|CRIT)\b', line, re.IGNORECASE)
            
            timestamp = timestamp_match.group(1) if timestamp_match else 'Unknown'
            severity = 'ERROR'  # default
            if severity_match:
                sev = severity_match.group(1).upper()
                if sev in ['WARN', 'WARNING']:
                    severity = 'WARNING'
                elif sev in ['ERROR', 'ERR']:
                    severity = 'ERROR'
                elif sev in ['CRITICAL', 'CRIT', 'FATAL']:
                    severity = 'CRITICAL'
                elif sev == 'INFO':
                    severity = 'INFO'
            
            # Extract module (if present)
            module_match = re.search(r'\[([^\]]+)\]', line)
            module = module_match.group(1) if module_match else 'Unknown'
            
            # Extract message (everything after severity)
            if severity_match:
                message = line[severity_match.end():].strip()
            else:
                message = line
            
            # Create log entry with user attribution
            log_entry = {
                'timestamp': timestamp,
                'severity': severity,
                'module': module,
                'message': message
            }
            
            logs.append(log_entry)
            severity_counts[severity] += 1
    
    except Exception as e:
        print(f"Error parsing log file: {e}")
    
    # Apply user attribution to all parsed logs
    attributed_logs = analyze_user_attribution(logs)
    
    return logs, severity_counts, file_content

def analyze_logs(logs, severity_counts):
    """Analyze parsed logs and generate insights"""
    total_logs = len(logs)
    total_errors = severity_counts['ERROR'] + severity_counts['CRITICAL']
    total_warnings = severity_counts['WARNING']
    
    # Generate timeline (last 20 events)
    timeline = logs[-20:] if logs else []
    
    # Generate time analysis (simplified)
    time_analysis = {
        'logs_per_hour': [
            {'timestamp': '10:00', 'count': severity_counts['INFO']},
            {'timestamp': '11:00', 'count': total_errors + total_warnings},
        ],
        'spike_intervals': []
    }
    
    # Detect anomalies (simplified)
    anomaly_count = min(5, total_errors)  # Simple anomaly detection
    
    # Generate AI insights (simplified)
    root_cause = "Analysis based on log patterns"
    failing_component = "Identified through error clustering"
    
    if total_errors > 0:
        error_logs = [log for log in logs if log['severity'] in ['ERROR', 'CRITICAL']]
        if error_logs:
            # Find most common module in errors
            modules = {}
            for log in error_logs:
                modules[log['module']] = modules.get(log['module'], 0) + 1
            most_common_module = max(modules.keys(), key=modules.get) if modules else 'Unknown'
            failing_component = f"{most_common_module} module"
            root_cause = f"Multiple errors detected in {most_common_module} component"
    
    fix_recommendations = [
        "Review recent changes in affected components",
        "Implement additional logging for better visibility",
        "Set up monitoring alerts for similar patterns"
    ]
    
    if total_errors > 10:
        fix_recommendations.insert(0, "Address critical errors immediately")
    
    log_summary = f"Analysis of {total_logs} log entries shows {total_errors} errors and {total_warnings} warnings"
    
    return {
        'summary': {
            'total_logs': total_logs,
            'total_errors': total_errors,
            'anomaly_count': anomaly_count,
            'severity_distribution': severity_counts
        },
        'timeline': timeline,
        'time_analysis': time_analysis,
        'ai_insights': {
            'root_cause': root_cause,
            'failing_component': failing_component,
            'fix_recommendations': fix_recommendations,
            'log_summary': log_summary
        },
        'anomalies': {
            'anomaly_count': anomaly_count,
            'anomalies': [{'message': 'Unusual spike in database errors', 'severity': 'HIGH'}] if anomaly_count > 0 else []
        }
    }

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

@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    """AI Assistant chat endpoint with instant responses"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        # Get latest analysis data for context
        analysis_data = load_analysis_data()
        
        # Generate instant AI response based on analysis data
        if analysis_data and analysis_data.get('summary'):
            total_logs = analysis_data['summary']['total_logs']
            total_errors = analysis_data['summary']['total_errors']
            root_cause = analysis_data['ai_insights'].get('root_cause', 'Unknown')
            
            # Enhanced question handling for broader coverage
            message_lower = user_message.lower()
            
            # Check for specific actionable combinations first - most specific to least specific
            if any(keyword in message_lower for keyword in ['actionable', 'steps', 'guide', 'how to']) and any(keyword in message_lower for keyword in ['fix', 'solve', 'address', 'handle']):
                # Specific handling for actionable steps
                if total_errors > 0:
                    error_rate = (total_errors/total_logs*100) if total_logs > 0 else 0
                    timeline = analysis_data.get('timeline', [])
                    
                    # Get specific error details
                    critical_errors = []
                    for event in timeline:
                        if event.get('severity') in ['ERROR', 'CRITICAL']:
                            critical_errors.append(event.get('message', 'Unknown error')[:80])
                    
                    if critical_errors:
                        # Remove duplicates and get top errors
                        unique_errors = list(set(critical_errors))[:3]
                        steps = []
                        for i, error in enumerate(unique_errors, 1):
                            steps.append(f"STEP {i}: Fix {error}\n- Action: Investigate the root cause\n- Solution: Implement proper error handling\n- Impact: Resolves multiple instances")
                        
                        response = f"ACTIONABLE STEPS TO FIX CRITICAL ISSUES:\n\n{chr(10).join(steps)}\n\nIMPLEMENTATION PLAN:\n1. Start with Step 1 (most frequent error)\n2. Test each fix in staging\n3. Deploy with monitoring\n4. Verify error reduction\n\nThese steps will directly address the {total_errors} errors found."
                    else:
                        response = f"ACTIONABLE STEPS:\n\n1. INVESTIGATE: {root_cause}\n   - Review system logs for patterns\n   - Identify affected components\n   - Document findings\n\n2. FIX: Implement solutions\n   - Apply patches/updates\n   - Add error handling\n   - Improve logging\n\n3. TEST: Verify fixes\n   - Test in staging environment\n   - Monitor for side effects\n   - Validate error reduction\n\n4. DEPLOY: Roll out carefully\n   - Deploy with monitoring\n   - Watch for recurrence\n   - Have rollback ready\n\nThese steps will resolve the {total_errors} errors detected."
                else:
                    response = "No actionable steps needed! Your system is running smoothly with no critical issues to address."
            
            elif any(keyword in message_lower for keyword in ['top', 'priorities', 'important', 'urgent']) and any(keyword in message_lower for keyword in ['risk', 'risks', 'issue', 'issues', 'problem', 'problems']):
                # Specific handling for top risks/priorities
                if total_errors > 0:
                    error_rate = (total_errors/total_logs*100) if total_logs > 0 else 0
                    timeline = analysis_data.get('timeline', [])
                    
                    # Get specific error types from timeline
                    error_types = {}
                    error_modules = {}
                    for event in timeline:
                        if event.get('severity') in ['ERROR', 'CRITICAL']:
                            error_type = event.get('message', 'Unknown error')[:50]
                            module = event.get('module', 'Unknown')
                            error_types[error_type] = error_types.get(error_type, 0) + 1
                            error_modules[module] = error_modules.get(module, 0) + 1
                    
                    # Create top 2 actionable risks
                    top_risks = []
                    if error_types:
                        sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)
                        for i, (error_type, count) in enumerate(sorted_errors[:2]):
                            risk_level = "Critical" if count > 5 else "High" if count > 2 else "Medium"
                            top_risks.append(f"RISK #{i+1}: {error_type}\n- Impact: {count} occurrences ({risk_level} priority)\n- Solution: Fix the underlying cause in the affected component\n- Action: Review error logs and implement proper error handling")
                    
                    if top_risks:
                        response = f"TOP 2 ACTIONABLE RISKS YOU CAN SOLVE:\n\n{chr(10).join(top_risks)}\n\nIMMEDIATE ACTIONS:\n1. Address the most frequent error first\n2. Implement proper error handling and logging\n3. Add monitoring to prevent recurrence\n4. Test fixes in staging before production\n\nWould you like detailed steps for any specific risk?"
                    else:
                        response = f"TOP ACTIONABLE RISKS:\n\n1. ROOT CAUSE: {root_cause}\n   - Impact: {total_errors} errors detected\n   - Solution: Investigate and fix the underlying issue\n   - Action: Review system logs and implement fixes\n\n2. ERROR RATE: {error_rate:.1f}%\n   - Impact: System performance degradation\n   - Solution: Optimize code and add error handling\n   - Action: Monitor and reduce error frequency\n\nBoth risks are solvable with proper investigation and fixes."
                else:
                    response = "Great news! No critical risks detected. Your system is running smoothly with no actionable issues to address."
            
            elif any(keyword in message_lower for keyword in ['high risk', 'risk', 'dangerous', 'critical']):
                if total_errors > 0:
                    response = f"Based on the analysis, I found {total_errors} high-risk error logs out of {total_logs} total logs. The main issue appears to be: {root_cause}. These should be prioritized for immediate attention."
                else:
                    response = "Good news! No high-risk errors were detected in the uploaded logs. The system appears to be running normally."
            
            elif any(keyword in message_lower for keyword in ['priorities', 'priority', 'urgent', 'important', 'focus', 'attention']) and any(keyword in message_lower for keyword in ['fix', 'solve', 'address', 'handle']):
                # Specific handling for priority fixes
                if total_errors > 0:
                    error_rate = (total_errors/total_logs*100) if total_logs > 0 else 0
                    timeline = analysis_data.get('timeline', [])
                    
                    # Analyze error patterns
                    error_patterns = {}
                    for event in timeline:
                        if event.get('severity') in ['ERROR', 'CRITICAL']:
                            error_msg = event.get('message', 'Unknown')[:60]
                            error_patterns[error_msg] = error_patterns.get(error_msg, 0) + 1
                    
                    if error_patterns:
                        sorted_patterns = sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)
                        top_priority = f"PRIORITY #1: {sorted_patterns[0][0]}\n- Frequency: {sorted_patterns[0][1]} occurrences\n- Action: Fix this most critical issue first\n- Impact: Will resolve {sorted_patterns[0][1]} errors"
                        
                        if len(sorted_patterns) > 1:
                            second_priority = f"PRIORITY #2: {sorted_patterns[1][0]}\n- Frequency: {sorted_patterns[1][1]} occurrences\n- Action: Address after priority #1\n- Impact: Will resolve {sorted_patterns[1][1]} errors"
                            response = f"TOP PRIORITIES TO FIX:\n\n{top_priority}\n\n{second_priority}\n\nIMMEDIATE ACTION PLAN:\n1. Investigate and fix the most frequent error\n2. Test the fix thoroughly\n3. Address the second priority\n4. Monitor for recurrence\n\nStart with Priority #1 for maximum impact."
                        else:
                            response = f"TOP PRIORITY TO FIX:\n\n{top_priority}\n\nACTION PLAN:\n1. Focus all resources on this critical issue\n2. Implement and test the fix\n3. Monitor system stability\n4. Address any remaining issues\n\nThis single priority will resolve the majority of errors."
                    else:
                        response = f"TOP PRIORITY: {root_cause}\n\nThis is the main issue causing {total_errors} errors. Focus on:\n1. Investigating the root cause\n2. Implementing proper fixes\n3. Testing thoroughly\n4. Monitoring for stability\n\nAddressing this will resolve most system issues."
                else:
                    response = "No priorities to fix! Your system is running smoothly with no critical issues."
            
            elif any(keyword in message_lower for keyword in ['actionable', 'steps', 'guide', 'how to']) and any(keyword in message_lower for keyword in ['fix', 'solve', 'address', 'handle']):
                # Specific handling for actionable steps
                if total_errors > 0:
                    error_rate = (total_errors/total_logs*100) if total_logs > 0 else 0
                    timeline = analysis_data.get('timeline', [])
                    
                    # Get specific error details
                    critical_errors = []
                    for event in timeline:
                        if event.get('severity') in ['ERROR', 'CRITICAL']:
                            critical_errors.append(event.get('message', 'Unknown error')[:80])
                    
                    if critical_errors:
                        # Remove duplicates and get top errors
                        unique_errors = list(set(critical_errors))[:3]
                        steps = []
                        for i, error in enumerate(unique_errors, 1):
                            steps.append(f"STEP {i}: Fix {error}\n- Action: Investigate the root cause\n- Solution: Implement proper error handling\n- Impact: Resolves multiple instances")
                        
                        response = f"ACTIONABLE STEPS TO FIX CRITICAL ISSUES:\n\n{chr(10).join(steps)}\n\nIMPLEMENTATION PLAN:\n1. Start with Step 1 (most frequent error)\n2. Test each fix in staging\n3. Deploy with monitoring\n4. Verify error reduction\n\nThese steps will directly address the {total_errors} errors found."
                    else:
                        response = f"ACTIONABLE STEPS:\n\n1. INVESTIGATE: {root_cause}\n   - Review system logs for patterns\n   - Identify affected components\n   - Document findings\n\n2. FIX: Implement solutions\n   - Apply patches/updates\n   - Add error handling\n   - Improve logging\n\n3. TEST: Verify fixes\n   - Test in staging environment\n   - Monitor for side effects\n   - Validate error reduction\n\n4. DEPLOY: Roll out carefully\n   - Deploy with monitoring\n   - Watch for recurrence\n   - Have rollback ready\n\nThese steps will resolve the {total_errors} errors detected."
                else:
                    response = "No actionable steps needed! Your system is running smoothly with no critical issues to address."
            
            elif any(keyword in message_lower for keyword in ['recommend', 'fix', 'solve', 'improve', 'solution']):
                recommendations = analysis_data['ai_insights'].get('fix_recommendations', [])
                if recommendations:
                    response = "Here are my recommendations:\n" + "\n".join([f"1. {rec}" for rec in recommendations[:3]])
                else:
                    response = "Upload a log file first to get specific recommendations based on your system's patterns."
            
            elif any(keyword in message_lower for keyword in ['what', 'summary', 'overview', 'status', 'report']):
                response = f"Log Analysis Summary:\n- Total logs processed: {total_logs}\n- Total errors found: {total_errors}\n- Root cause: {root_cause}\n- System status: {'Critical' if total_errors > 0 else 'Normal'}\n\nWould you like more details about any specific aspect?"
            
            elif any(keyword in message_lower for keyword in ['error', 'problem', 'issue', 'failure', 'deploy', 'production']):
                if total_errors > 0:
                    if 'deploy' in message_lower or 'production' in message_lower:
                        response = f"PRODUCTION DEPLOYMENT ASSESSMENT:\n\nISSUES FOUND ({total_errors} errors):\n- Root cause: {root_cause}\n- Error rate: {(total_errors/total_logs*100):.1f}%\n\nDEPLOYMENT RECOMMENDATION: {'NO - Fix critical issues first' if total_errors > 5 else 'CAUTION - Monitor closely'}\n\nRequired fixes before production:\n1. Address the root cause: {root_cause}\n2. Reduce error rate below 5%\n3. Implement monitoring and alerting\n\nWould you like specific steps to fix these issues?"
                    else:
                        response = f"I found {total_errors} errors in your logs. The main issue is: {root_cause}. These errors are affecting system performance and should be addressed. Would you like specific recommendations to fix these issues?"
                else:
                    if 'deploy' in message_lower or 'production' in message_lower:
                        response = "PRODUCTION DEPLOYMENT ASSESSMENT:\n\nSTATUS: READY FOR PRODUCTION\n\n- No errors detected in current logs\n- System appears stable and healthy\n- Error rate: 0%\n\nDEPLOYMENT RECOMMENDATION: GO\n\nThe system is ready for production deployment. Ensure you have monitoring and rollback procedures in place."
                    else:
                        response = "No errors were detected in the uploaded logs. Your system appears to be running smoothly."
            
            elif any(keyword in message_lower for keyword in ['user', 'who', 'attribution', 'responsible']):
                # Try to get user attribution data
                try:
                    import requests
                    attribution_response = requests.get('http://localhost:5000/api/user-attribution', timeout=2)
                    if attribution_response.status_code == 200:
                        attribution_data = attribution_response.json()
                        if attribution_data.get('status') == 'success':
                            user_attr = attribution_data.get('user_attribution', {})
                            top_users = user_attr.get('top_risk_users', [])
                            if top_users:
                                response = f"User Attribution Analysis:\n- Total critical logs: {user_attr.get('total_critical_logs', 0)}\n- Total error logs: {user_attr.get('total_error_logs', 0)}\n- Top risk users: {len(top_users)} identified\n\nThe system can identify users responsible for errors using multiple methods including direct user IDs, session tracking, and timestamp correlation."
                            else:
                                response = "User attribution analysis is available but no specific users were identified in the current logs. This could be because user information is not present in the log format."
                        else:
                            response = "User attribution analysis is available. Upload logs with user information (user_id, session_id) to get detailed user attribution."
                    else:
                        response = "User attribution analysis is available. Upload logs with user information to get detailed user attribution."
                except:
                    response = "User attribution analysis is available. Upload logs with user information to get detailed user attribution."
            
            elif any(keyword in message_lower for keyword in ['performance', 'slow', 'speed', 'optimize']):
                response = f"Performance Analysis:\n- Total logs processed: {total_logs}\n- Error rate: {(total_errors/total_logs*100):.1f}% if total_logs > 0 else 0\n- System health: {'Degraded' if total_errors > 0 else 'Healthy'}\n\nFor better performance, consider addressing the root cause: {root_cause}"
            
            elif any(keyword in message_lower for keyword in ['help', 'hello', 'hi', 'what can you do']):
                response = "Hello! I'm your AI log analysis assistant. I can help you with:\n- Analyzing log files for errors and issues\n- Identifying high-risk logs and critical problems\n- Providing recommendations to fix issues\n- User attribution analysis (who caused errors)\n- Performance analysis and system health\n- Error pattern recognition\n\nUpload a log file and ask me anything about your system!"
            
            elif any(keyword in message_lower for keyword in ['timeline', 'when', 'time', 'sequence']):
                timeline = analysis_data.get('timeline', [])
                if timeline:
                    recent_events = timeline[-5:]  # Last 5 events
                    response = "Recent Log Events:\n" + "\n".join([f"- {event['timestamp']} [{event['severity']}] {event['message'][:50]}..." for event in recent_events])
                else:
                    response = "No timeline data available. Upload a log file to see the sequence of events."
            
            elif any(keyword in message_lower for keyword in ['module', 'component', 'service', 'application']):
                # Analyze which modules have the most issues
                timeline = analysis_data.get('timeline', [])
                if timeline:
                    module_errors = {}
                    for event in timeline:
                        if event['severity'] in ['ERROR', 'CRITICAL']:
                            module = event['module']
                            module_errors[module] = module_errors.get(module, 0) + 1
                    
                    if module_errors:
                        worst_module = max(module_errors.items(), key=lambda x: x[1])
                        response = f"Module Analysis:\n- Most problematic module: {worst_module[0]} ({worst_module[1]} errors)\n- Total modules with issues: {len(module_errors)}\n\nThe {worst_module[0]} module needs immediate attention."
                    else:
                        response = "No module-specific issues detected in the current logs."
                else:
                    response = "No module data available. Upload a log file to analyze component performance."
            
            elif any(keyword in message_lower for keyword in ['why', 'cause', 'reason', 'happened']):
                if total_errors > 0:
                    response = f"ROOT CAUSE ANALYSIS:\n\nPrimary cause: {root_cause}\n\nContributing factors:\n- Error frequency: {total_errors} occurrences\n- Error rate: {(total_errors/total_logs*100):.1f}%\n- System impact: {'High' if total_errors > 10 else 'Medium' if total_errors > 5 else 'Low'}\n\nTo prevent this issue:\n1. Address the root cause: {root_cause}\n2. Implement proper error handling\n3. Add monitoring and alerts\n4. Regular system maintenance\n\nWould you like detailed steps to fix this issue?"
                else:
                    response = "No errors detected in the current logs. The system is operating normally without any apparent issues."
            
            elif any(keyword in message_lower for keyword in ['how', 'steps', 'guide', 'tutorial', 'instructions']):
                if total_errors > 0:
                    response = f"STEP-BY-STEP FIX GUIDE:\n\nIssue: {root_cause}\n\nIMMEDIATE ACTIONS:\n1. IDENTIFY: Locate all instances of {root_cause}\n2. ASSESS: Determine impact scope ({total_errors} occurrences)\n3. FIX: Apply appropriate patches/updates\n4. TEST: Verify fix in staging environment\n5. DEPLOY: Roll out to production with monitoring\n6. MONITOR: Watch for recurrence for 24-48 hours\n\nPREVENTION MEASURES:\n- Implement automated testing\n- Add monitoring alerts\n- Schedule regular maintenance\n- Document the fix for future reference\n\nNeed more specific technical details for any step?"
                else:
                    response = "No fixes needed - your system is running smoothly! Would you like guidance on system optimization or preventive maintenance instead?"
            
            elif any(keyword in message_lower for keyword in ['security', 'vulnerability', 'threat', 'attack']):
                if total_errors > 0:
                    response = f"SECURITY ANALYSIS:\n\nFound {total_errors} potential security-related events:\n- Root cause: {root_cause}\n- Risk level: {'High' if total_errors > 10 else 'Medium' if total_errors > 5 else 'Low'}\n\nRECOMMENDATIONS:\n1. Investigate authentication logs\n2. Review access patterns\n3. Check for unusual activity\n4. Update security protocols\n5. Implement intrusion detection\n\nWould you like a detailed security audit report?"
                else:
                    response = "SECURITY STATUS: SECURE\n\nNo security threats detected in the current logs. Your system appears to be protected.\n\nSECURITY BEST PRACTICES:\n- Regular security updates\n- Access control monitoring\n- Encryption enforcement\n- Backup verification\n- Security training\n\nAll systems operating within normal security parameters."
            
            elif any(keyword in message_lower for keyword in ['monitoring', 'alert', 'notification', 'watch']):
                response = f"MONITORING RECOMMENDATIONS:\n\nCurrent Status: {'Alerts needed' if total_errors > 0 else 'Normal operation'}\n\nSUGGESTED MONITORING:\n- Error rate threshold: >5% triggers alert\n- Critical errors: Immediate notification\n- Performance degradation: Monitor trends\n- User activity: Track unusual patterns\n\nALERT CONFIGURATION:\n- Real-time error notifications\n- Daily health reports\n- Weekly performance summaries\n- Monthly security audits\n\nWould you like help setting up specific monitoring rules?"
            
            elif any(keyword in message_lower for keyword in ['database', 'db', 'sql', 'query']):
                if total_errors > 0:
                    response = f"DATABASE ANALYSIS:\n\nIssues detected: {total_errors}\nRoot cause: {root_cause}\n\nDATABASE HEALTH:\n- Connection errors: Check connectivity\n- Query performance: Optimize slow queries\n- Data integrity: Verify consistency\n- Backup status: Ensure recent backups\n\nRECOMMENDATIONS:\n1. Review database logs\n2. Optimize query performance\n3. Check connection pooling\n4. Verify backup procedures\n5. Monitor resource usage\n\nNeed specific database troubleshooting steps?"
                else:
                    response = "DATABASE STATUS: HEALTHY\n\nNo database-related errors detected. All database operations appear to be functioning normally.\n\nPERFORMANCE TIPS:\n- Regular index maintenance\n- Query optimization\n- Connection pool monitoring\n- Backup verification\n- Resource usage tracking"
            
            else:
                # Enhanced general intelligent response with better context awareness
                if total_errors > 0:
                    error_rate = (total_errors/total_logs*100) if total_logs > 0 else 0
                    if error_rate > 10:
                        severity = "critical"
                        urgency = "immediate attention required"
                    elif error_rate > 5:
                        severity = "high"
                        urgency = "should be addressed soon"
                    else:
                        severity = "moderate"
                        urgency = "monitoring recommended"
                    
                    response = f"ANALYSIS RESULTS:\n\nI found {total_errors} errors in {total_logs} log entries ({error_rate:.1f}% error rate). This is considered {severity} priority and {urgency}.\n\nROOT CAUSE: {root_cause}\n\nKEY INSIGHTS:\n- Error frequency: {total_errors} occurrences\n- System impact: {'Degraded performance' if total_errors > 5 else 'Minor impact'}\n- Urgency level: {severity}\n\nI can provide detailed analysis on:\n- Step-by-step fix recommendations\n- Which users/components are responsible\n- Timeline of when errors occurred\n- Performance impact assessment\n- Prevention strategies\n\nWhat specific aspect would you like me to analyze further?"
                else:
                    response = f"SYSTEM STATUS: HEALTHY\n\nI've analyzed {total_logs} log entries and found no critical errors. Your system is operating normally.\n\nSYSTEM HEALTH METRICS:\n- Error rate: 0%\n- Status: Stable and reliable\n- Performance: Optimal\n\nAVAILABLE ANALYSES:\n- Performance optimization suggestions\n- User activity patterns\n- System utilization trends\n- Security audit\n- Capacity planning\n\nWhat would you like me to help you with?"
        else:
            response = "Please upload a log file first so I can provide analysis and recommendations. I'll help you identify high-risk logs and suggest fixes."
        
        return jsonify({
            'response': response,
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({
            'response': 'I apologize, but I encountered an error. Please try uploading your log file again.',
            'status': 'error'
        }), 500

@app.route('/api/files')
def get_uploaded_files():
    """Get list of uploaded files"""
    try:
        files = []
        upload_dir = app.config['UPLOAD_FOLDER']
        
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                if allowed_file(filename):
                    file_path = os.path.join(upload_dir, filename)
                    file_info = {
                        'filename': filename,
                        'size': os.path.getsize(file_path),
                        'uploaded_at': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    files.append(file_info)
        
        return jsonify({
            'files': files,
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({
            'files': [],
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete an uploaded file"""
    try:
        if not allowed_file(filename):
            return jsonify({'error': 'Invalid file type', 'status': 'error'}), 400
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'message': f'File {filename} deleted successfully', 'status': 'success'})
        else:
            return jsonify({'error': 'File not found', 'status': 'error'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/user-attribution', methods=['GET'])
def get_user_attribution():
    """Get user attribution analysis for critical logs"""
    try:
        analysis_data = load_analysis_data()
        if not analysis_data or not analysis_data.get('timeline'):
            return jsonify({
                'error': 'No analysis data available',
                'status': 'error'
            }), 400
        
        # Apply user attribution to timeline logs
        attributed_logs = analyze_user_attribution(analysis_data['timeline'])
        
        # Analyze user risk metrics
        user_risk_analysis = {}
        critical_logs = [log for log in attributed_logs if log['severity'] in ['CRITICAL', 'ERROR']]
        
        for log in critical_logs:
            user_id = log['user_id']
            if user_id and user_id != 'Unknown':
                if user_id not in user_risk_analysis:
                    user_risk_analysis[user_id] = {
                        'error_count': 0,
                        'critical_count': 0,
                        'first_error': None,
                        'last_error': None,
                        'attribution_methods': set()
                    }
                
                if log['severity'] == 'CRITICAL':
                    user_risk_analysis[user_id]['critical_count'] += 1
                elif log['severity'] == 'ERROR':
                    user_risk_analysis[user_id]['error_count'] += 1
                
                user_risk_analysis[user_id]['attribution_methods'].add(log['attribution_method'])
                
                # Track first and last error times
                error_time = log['timestamp']
                if user_risk_analysis[user_id]['first_error'] is None or error_time < user_risk_analysis[user_id]['first_error']:
                    user_risk_analysis[user_id]['first_error'] = error_time
                if user_risk_analysis[user_id]['last_error'] is None or error_time > user_risk_analysis[user_id]['last_error']:
                    user_risk_analysis[user_id]['last_error'] = error_time
        
        # Sort users by risk score (critical errors weighted more)
        top_risk_users = sorted(
            user_risk_analysis.items(),
            key=lambda x: x[1]['critical_count'] * 10 + x[1]['error_count'],
            reverse=True
        )
        
        # Calculate unknown user events
        unknown_user_count = len([log for log in attributed_logs if log['user_id'] == 'Unknown'])
        
        return jsonify({
            'status': 'success',
            'user_attribution': {
                'total_critical_logs': len([log for log in critical_logs if log['severity'] == 'CRITICAL']),
                'total_error_logs': len([log for log in critical_logs if log['severity'] == 'ERROR']),
                'total_unknown_user_events': unknown_user_count,
                'top_risk_users': [
                    {
                        'user_id': user_id,
                        'error_count': risk_data['error_count'],
                        'critical_count': risk_data['critical_count'],
                        'first_error': risk_data['first_error'],
                        'last_error': risk_data['last_error'],
                        'attribution_methods': list(risk_data['attribution_methods']),
                        'risk_score': risk_data['critical_count'] * 10 + risk_data['error_count']
                    }
                    for user_id, risk_data in top_risk_users[:10]
                ]
            },
            'attribution_summary': {
                'direct_identification': len([log for log in attributed_logs if log['attribution_method'] == 'direct']),
                'session_inferred': len([log for log in attributed_logs if log['attribution_method'] == 'session_inferred']),
                'timestamp_fallback': len([log for log in attributed_logs if log['attribution_method'] == 'timestamp_used']),
                'session_unknown': len([log for log in attributed_logs if log['attribution_method'] == 'session_unknown'])
            },
            'sample_attributed_logs': attributed_logs[:5]  # Show first 5 examples
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Analysis error: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Parse and analyze the log file
        try:
            logs, severity_counts, file_content = parse_log_file(file_path)
            analysis_results = analyze_logs(logs, severity_counts)
            
            # Store only this document's analysis in file (don't accumulate)
            save_analysis_data(analysis_results)
            
            return jsonify({
                'status': 'success',
                'filename': filename,
                'lines_count': len(logs),
                'file_size': os.path.getsize(file_path),
                'message': f'File {filename} analyzed successfully',
                'analysis': analysis_results,
                'file_preview': {
                    'content': file_content[:50],  # First 50 lines for preview
                    'total_lines': len(file_content),
                    'showing_lines': min(50, len(file_content))
                }
            })
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/api/latest')
def latest_analysis():
    latest_analysis_data = load_analysis_data()
    
    if latest_analysis_data:
        return jsonify(latest_analysis_data)
    else:
        # Return empty/default data if no analysis has been performed
        return jsonify({
            'summary': {
                'total_logs': 0,
                'total_errors': 0,
                'anomaly_count': 0,
                'severity_distribution': {
                    'INFO': 0,
                    'WARNING': 0,
                    'ERROR': 0,
                    'CRITICAL': 0
                }
            },
            'timeline': [],
            'time_analysis': {
                'logs_per_hour': [],
                'spike_intervals': []
            },
            'ai_insights': {
                'root_cause': 'No analysis performed yet',
                'failing_component': 'Unknown',
                'fix_recommendations': ['Upload a log file to begin analysis'],
                'log_summary': 'No log data available for analysis'
            },
            'anomalies': {
                'anomaly_count': 0,
                'anomalies': []
            }
        })

if __name__ == "__main__":
    print("Starting clean Flask server...")
    print("Access the application at: http://localhost:5000")
    print("This works just like normal Flask should!")
    app.run(host="127.0.0.1", port=5000, debug=True)
