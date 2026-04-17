let latestQuestion = "";
let latestAnswer = "";
let logsChart = null;
let heatmapChart = null;
let severityChart = null;
let moduleChart = null;

// Simple dashboard for clean Flask app (no SocketIO)
const analyzeBtn = document.getElementById("analyzeBtn");
if (analyzeBtn) {
    analyzeBtn.addEventListener("click", async () => {
        const fileInput = document.getElementById("logFile");
        if (!fileInput.files.length) {
            alert("Please select a log file.");
            return;
        }
        const formData = new FormData();
        formData.append("file", fileInput.files[0]);
        
        const statusElement = document.getElementById("uploadStatus");
        if (statusElement) {
            statusElement.innerText = "Analyzing...";
            statusElement.className = "upload-status processing";
        }

        try {
            const response = await fetch("/api/upload", { method: "POST", body: formData });
            const data = await response.json();
            
            if (!response.ok) {
                if (statusElement) {
                    statusElement.innerText = data.error || "Upload failed";
                    statusElement.className = "upload-status error";
                }
                return;
            }

            if (statusElement) {
                statusElement.innerText = `Analysis complete: ${data.message}`;
                statusElement.className = "upload-status success";
            }
            
            // Show file preview
            if (data.file_preview) {
                showFilePreview(data.filename, data.file_preview);
            }
            
            // Use the analysis data directly from the upload response
            if (data.analysis) {
                renderSummary(data.analysis.summary);
                renderTimeline(data.analysis.timeline || []);
                renderInsights(data.analysis.ai_insights || {}, data.analysis.anomalies || {});
                renderCharts(data.analysis.time_analysis || {}, data.analysis.summary?.severity_distribution || {});
            }
            
        } catch (error) {
            if (statusElement) {
                statusElement.innerText = `Error: ${error.message}`;
                statusElement.className = "upload-status error";
            }
        }
    });
}

// Load latest analysis data
async function loadLatestAnalysis() {
    try {
        const response = await fetch("/api/latest");
        const data = await response.json();
        
        if (response.ok) {
            renderSummary(data.summary);
            renderTimeline(data.timeline || []);
            renderInsights(data.ai_insights || {}, data.anomalies || {});
            renderCharts(data.time_analysis || {}, data.summary?.severity_distribution || {});
        }
    } catch (error) {
        console.error("Failed to load latest analysis", error);
    }
}

// Render summary
function renderSummary(summary) {
    const container = document.getElementById("summaryGrid");
    if (!container) return;
    
    container.innerHTML = `
        <div class="metric-card">
            <h4>Total Logs</h4>
            <div class="metric-value">${summary.total_logs || 0}</div>
        </div>
        <div class="metric-card">
            <h4>Total Errors</h4>
            <div class="metric-value">${summary.total_errors || 0}</div>
        </div>
        <div class="metric-card">
            <h4>Anomalies</h4>
            <div class="metric-value">${summary.anomaly_count || 0}</div>
        </div>
        <div class="metric-card">
            <h4>Health Score</h4>
            <div class="metric-value">${Math.max(0, 100 - (summary.total_errors / summary.total_logs * 100)).toFixed(1)}%</div>
        </div>
    `;
}

// Render timeline
function renderTimeline(timeline) {
    const container = document.getElementById("timelineList");
    if (!container) return;
    
    container.innerHTML = timeline.map(event => `
        <li class="timeline-event ${event.severity.toLowerCase()}">
            <div class="timeline-time">${event.timestamp}</div>
            <div class="timeline-content">
                <div class="timeline-severity">${event.severity}</div>
                <div class="timeline-message">${event.message}</div>
                <div class="timeline-module">${event.module}</div>
            </div>
        </li>
    `).join('');
}

// Render insights
function renderInsights(insights, anomalies) {
    const container = document.getElementById("aiInsights");
    if (!container) return;
    
    container.innerHTML = `
        <div class="insights-grid">
            <div class="insight-card primary">
                <div class="insight-header">
                    <div class="insight-icon">search</div>
                    <h4>Root Cause Analysis</h4>
                </div>
                <div class="insight-content">
                    <p>${insights.root_cause || "Analysis based on log patterns"}</p>
                </div>
            </div>
            
            <div class="insight-card warning">
                <div class="insight-header">
                    <div class="insight-icon">warning</div>
                    <h4>Failing Component</h4>
                </div>
                <div class="insight-content">
                    <p>${insights.failing_component || "Identified through error clustering"}</p>
                </div>
            </div>
            
            <div class="insight-card recommendations">
                <div class="insight-header">
                    <div class="insight-icon">lightbulb</div>
                    <h4>Fix Recommendations</h4>
                </div>
                <div class="insight-content">
                    <ol>${(insights.fix_recommendations || []).map((x) => `<li>${x}</li>`).join("")}</ol>
                </div>
            </div>
            
            <div class="insight-card info">
                <div class="insight-header">
                    <div class="insight-icon">analytics</div>
                    <h4>Anomaly Detection</h4>
                </div>
                <div class="insight-content">
                    <p><strong>${anomalies.anomaly_count || 0}</strong> unusual log patterns detected</p>
                    <div class="anomaly-indicator">
                        <div class="anomaly-bar" style="width: ${Math.min((anomalies.anomaly_count || 0) * 10, 100)}%"></div>
                    </div>
                </div>
            </div>
            
            <div class="insight-card summary">
                <div class="insight-header">
                    <div class="insight-icon">summarize</div>
                    <h4>Executive Summary</h4>
                </div>
                <div class="insight-content">
                    <p>${insights.log_summary || "Automated analysis shows system patterns requiring attention"}</p>
                </div>
            </div>
        </div>
    `;
}

// Render charts
function renderCharts(timeAnalysis, severityDist) {
    const timeCanvas = document.getElementById("logsOverTime");
    const heatCanvas = document.getElementById("errorHeatmap");
    const sevCanvas = document.getElementById("severityChart");
    const moduleCanvas = document.getElementById("moduleChart");
    
    if (!timeCanvas || !heatCanvas || !sevCanvas) {
        return;
    }
    
    const timeCtx = timeCanvas.getContext("2d");
    const heatCtx = heatCanvas.getContext("2d");
    const sevCtx = sevCanvas.getContext("2d");

    const labels = (timeAnalysis.logs_per_hour || []).map((x) => x.timestamp);
    const counts = (timeAnalysis.logs_per_hour || []).map((x) => x.count);
    const safeLabels = labels.length ? labels : ["No time data"];
    const safeCounts = counts.length ? counts : [0];

    // Simple chart rendering (without Chart.js for now)
    timeCanvas.width = timeCanvas.offsetWidth;
    timeCanvas.height = timeCanvas.offsetHeight;
    timeCtx.fillStyle = "#3b82f6";
    timeCtx.fillRect(10, 10, 100, 50);
    timeCtx.fillStyle = "#f1f5f9";
    timeCtx.fillText("Logs Over Time", 20, 40);
    
    heatCanvas.width = heatCanvas.offsetWidth;
    heatCanvas.height = heatCanvas.offsetHeight;
    heatCtx.fillStyle = "#f97316";
    heatCtx.fillRect(10, 10, 100, 50);
    heatCtx.fillStyle = "#f1f5f9";
    heatCtx.fillText("Error Spikes", 20, 40);
    
    sevCanvas.width = sevCanvas.offsetWidth;
    sevCanvas.height = sevCanvas.offsetHeight;
    sevCtx.fillStyle = "#10b981";
    sevCtx.fillRect(10, 10, 100, 50);
    sevCtx.fillStyle = "#f1f5f9";
    sevCtx.fillText("Severity Distribution", 20, 40);
}

// Show file preview
function showFilePreview(filename, filePreview) {
    const previewContainer = document.getElementById('filePreview');
    if (!previewContainer) return;
    
    const contentHtml = filePreview.content.map(line => 
        `<div class="preview-line">${escapeHtml(line)}</div>`
    ).join('');
    
    previewContainer.innerHTML = `
        <div class="file-preview-container">
            <div class="preview-header">
                <h4>File Preview: ${filename}</h4>
                <span class="preview-info">Showing ${filePreview.showing_lines} of ${filePreview.total_lines} lines</span>
            </div>
            <div class="preview-content">
                ${contentHtml}
            </div>
        </div>
    `;
    
    previewContainer.style.display = 'block';
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// AI Assistant Chat functionality
const aiChatForm = document.getElementById('aiChatForm');
const aiChatInput = document.getElementById('aiChatInput');
const aiChatMessages = document.getElementById('aiChatMessages');

// Quick question function for the quick question buttons
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

function removeChatMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}

// File Management functionality
let uploadedFiles = [];

async function loadUploadedFiles() {
    try {
        const response = await fetch('/api/files');
        const data = await response.json();
        
        if (data.status === 'success') {
            uploadedFiles = data.files;
            renderFileList();
        }
    } catch (error) {
        console.error('Error loading files:', error);
    }
}

function renderFileList() {
    const fileListContainer = document.getElementById('fileList');
    if (!fileListContainer) return;
    
    if (uploadedFiles.length === 0) {
        fileListContainer.innerHTML = '<p class="no-files">No files uploaded yet</p>';
        return;
    }
    
    fileListContainer.innerHTML = uploadedFiles.map(file => `
        <div class="file-item" data-filename="${file.filename}">
            <div class="file-checkbox">
                <input type="checkbox" id="file-${file.filename}" value="${file.filename}" onchange="toggleFileSelection('${file.filename}')">
                <label for="file-${file.filename}" class="checkbox-label">
                    <span class="checkmark"></span>
                </label>
            </div>
            <div class="file-info">
                <div class="file-name">${file.filename}</div>
                <div class="file-details">${formatFileSize(file.size)} - ${file.uploaded_at}</div>
            </div>
            <div class="file-actions">
                <button class="btn-delete" onclick="deleteFile('${file.filename}')">Delete</button>
            </div>
        </div>
    `).join('');
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function toggleFileSelection(filename) {
    const checkbox = document.getElementById(`file-${filename}`);
    const fileItem = checkbox.closest('.file-item');
    
    if (checkbox.checked) {
        fileItem.classList.add('selected');
    } else {
        fileItem.classList.remove('selected');
    }
    
    updateSelectedCount();
}

function updateSelectedCount() {
    const selectedCount = document.querySelectorAll('.file-item input:checked').length;
    const countElement = document.getElementById('selectedCount');
    if (countElement) {
        countElement.textContent = `${selectedCount} file${selectedCount !== 1 ? 's' : ''} selected`;
    }
}

async function deleteFile(filename) {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) return;
    
    try {
        const response = await fetch(`/api/files/${filename}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            uploadedFiles = uploadedFiles.filter(f => f.filename !== filename);
            renderFileList();
            showNotification('File deleted successfully', 'success');
        } else {
            showNotification(data.error || 'Error deleting file', 'error');
        }
    } catch (error) {
        showNotification('Error deleting file', 'error');
    }
}

function showNotification(message, type) {
    // Simple notification system
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : '#dc2626'};
        color: white;
        border-radius: 8px;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function selectAllFiles() {
    const checkboxes = document.querySelectorAll('.file-item input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
        const fileItem = checkbox.closest('.file-item');
        fileItem.classList.add('selected');
    });
    updateSelectedCount();
}

function deselectAllFiles() {
    const checkboxes = document.querySelectorAll('.file-item input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
        const fileItem = checkbox.closest('.file-item');
        fileItem.classList.remove('selected');
    });
    updateSelectedCount();
}

// Load analysis on page load
document.addEventListener('DOMContentLoaded', function() {
    loadLatestAnalysis();
    loadUploadedFiles();
});
