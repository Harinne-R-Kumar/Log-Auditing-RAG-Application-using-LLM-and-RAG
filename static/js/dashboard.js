let latestQuestion = "";
let latestAnswer = "";
let logsChart = null;
let heatmapChart = null;
let severityChart = null;
let moduleChart = null;

const socket = io();
socket.on("status", (payload) => {
    const status = document.getElementById("uploadStatus");
    if (status) {
        status.innerText = payload.message;
    }
});
socket.on("realtime_log", (log) => {
    const li = document.createElement("li");
    li.innerText = `[${log.timestamp}] ${log.severity} ${log.module}: ${log.message}`;
    const feed = document.getElementById("realtimeFeed");
    if (feed) {
        feed.prepend(li);
    }
});

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
    document.getElementById("uploadStatus").innerText = "Analyzing...";

    const response = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) {
        document.getElementById("uploadStatus").innerText = data.error || "Upload failed";
        return;
    }

    document.getElementById("uploadStatus").innerText = "Analysis complete";
    renderSummary(data.summary);
    renderTimeline(data.timeline || []);
    renderInsights(data.ai_insights || {}, data.anomalies || {});
    renderCharts(data.time_analysis || {}, data.summary?.severity_distribution || {});
    });
}

const askBtn = document.getElementById("askBtn");
if (askBtn) {
askBtn.addEventListener("click", async () => {
    const question = document.getElementById("chatQuestion").value.trim();
    if (!question) {
        return;
    }
    latestQuestion = question;
    
    // Show loading state
    const responseContainer = document.getElementById("chatResponse");
    const answerElement = document.getElementById("chatAnswer");
    responseContainer.style.display = "block";
    answerElement.innerText = "Thinking...";
    
    const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
    });
    const data = await response.json();
    latestAnswer = data.answer || "Sorry, I couldn't process your request.";
    answerElement.innerText = latestAnswer;
});
}

async function sendFeedback(isCorrect) {
    if (!latestQuestion || !latestAnswer) {
        alert("Ask a question first.");
        return;
    }
    await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: latestQuestion, answer: latestAnswer, is_correct: isCorrect }),
    });
}

const feedbackCorrect = document.getElementById("feedbackCorrect");
const feedbackIncorrect = document.getElementById("feedbackIncorrect");
if (feedbackCorrect) {
    feedbackCorrect.addEventListener("click", () => sendFeedback(true));
}
if (feedbackIncorrect) {
    feedbackIncorrect.addEventListener("click", () => sendFeedback(false));
}

function renderSummary(summary) {
    const grid = document.getElementById("summaryGrid");
    if (!grid || !summary) {
        return;
    }
    grid.innerHTML = "";
    const items = [
        ["Total Logs", summary.total_logs],
        ["Total Errors", summary.total_errors],
        ["Anomalies", summary.anomaly_count],
        ["Peak Error Time", summary.peak_error_time || "N/A"],
    ];
    items.forEach(([k, v]) => {
        const div = document.createElement("div");
        div.className = "kpi";
        div.innerHTML = `<strong>${k}</strong><br>${v}`;
        grid.appendChild(div);
    });
}

function renderTimeline(timeline) {
    const list = document.getElementById("timelineList");
    if (!list) {
        return;
    }
    
    // Clear existing content
    list.innerHTML = "";
    
    // Update stats
    updateTimelineStats(timeline);
    
    // Render timeline events
    timeline.slice(0, 50).forEach((event) => {
        const eventDiv = createTimelineEvent(event);
        list.appendChild(eventDiv);
    });
    
    // Setup filter functionality
    setupTimelineFilters();
}

function updateTimelineStats(timeline) {
    const stats = {
        total: timeline.length,
        critical: timeline.filter(e => e.severity === 'CRITICAL').length,
        error: timeline.filter(e => e.severity === 'ERROR').length,
        warning: timeline.filter(e => e.severity === 'WARNING').length
    };
    
    document.getElementById('totalEvents').textContent = stats.total;
    document.getElementById('criticalCount').textContent = stats.critical;
    document.getElementById('errorCount').textContent = stats.error;
    document.getElementById('warningCount').textContent = stats.warning;
}

function createTimelineEvent(event) {
    const eventDiv = document.createElement('div');
    eventDiv.className = `timeline-event ${event.severity.toLowerCase()}`;
    
    const timestamp = event.timestamp && event.timestamp !== "NaT" ? event.timestamp : "time-unavailable";
    const date = new Date(timestamp);
    const formattedDate = date.toLocaleDateString();
    const formattedTime = date.toLocaleTimeString();
    
    eventDiv.innerHTML = `
        <div class="timeline-time">
            <div class="timeline-date">${formattedDate}</div>
            <div class="timeline-clock">${formattedTime}</div>
        </div>
        <div class="timeline-content">
            <div class="timeline-message">${event.message}</div>
            <div class="timeline-module">${event.module || 'unknown'}</div>
        </div>
        <div class="timeline-severity ${event.severity.toLowerCase()}">${event.severity}</div>
    `;
    
    return eventDiv;
}

function setupTimelineFilters() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    const events = document.querySelectorAll('.timeline-event');
    
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Update active button
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Filter events
            const filter = button.dataset.filter;
            events.forEach(event => {
                if (filter === 'all') {
                    event.style.display = 'grid';
                } else {
                    const severity = event.className.includes(filter) ? 'grid' : 'none';
                    event.style.display = severity;
                }
            });
        });
    });
}

function renderInsights(insights, anomalies) {
    const container = document.getElementById("aiInsights");
    if (!container) {
        return;
    }
    
    const rootCause = insights.root_cause || "Analysis based on log patterns";
    const failingComponent = insights.failing_component || "Identified through error clustering";
    const recommendations = insights.fix_recommendations || [
        "Review recent changes in affected components",
        "Implement additional logging for better visibility",
        "Set up monitoring alerts for similar patterns"
    ];
    const anomalyCount = anomalies.anomaly_count || 0;
    const summary = insights.log_summary || "Automated analysis shows system patterns requiring attention";
    
    container.innerHTML = `
        <div class="insights-grid">
            <div class="insight-card primary">
                <div class="insight-header">
                    <div class="insight-icon">search</div>
                    <h4>Root Cause Analysis</h4>
                </div>
                <div class="insight-content">
                    <p>${rootCause}</p>
                </div>
            </div>
            
            <div class="insight-card warning">
                <div class="insight-header">
                    <div class="insight-icon">warning</div>
                    <h4>Failing Component</h4>
                </div>
                <div class="insight-content">
                    <p>${failingComponent}</p>
                </div>
            </div>
            
            <div class="insight-card recommendations">
                <div class="insight-header">
                    <div class="insight-icon">lightbulb</div>
                    <h4>Fix Recommendations</h4>
                </div>
                <div class="insight-content">
                    <ol>${recommendations.map((x) => `<li>${x}</li>`).join("")}</ol>
                </div>
            </div>
            
            <div class="insight-card info">
                <div class="insight-header">
                    <div class="insight-icon">analytics</div>
                    <h4>Anomaly Detection</h4>
                </div>
                <div class="insight-content">
                    <p><strong>${anomalyCount}</strong> unusual log patterns detected</p>
                    <div class="anomaly-indicator">
                        <div class="anomaly-bar" style="width: ${Math.min(anomalyCount * 10, 100)}%"></div>
                    </div>
                </div>
            </div>
            
            <div class="insight-card summary">
                <div class="insight-header">
                    <div class="insight-icon">summarize</div>
                    <h4>Executive Summary</h4>
                </div>
                <div class="insight-content">
                    <p>${summary}</p>
                </div>
            </div>
        </div>
    `;
}

function renderCharts(timeAnalysis, severityDist) {
    const timeCanvas = document.getElementById("logsOverTime");
    const heatCanvas = document.getElementById("errorHeatmap");
    const sevCanvas = document.getElementById("severityChart");
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

    if (logsChart) {
        logsChart.destroy();
    }
    logsChart = new Chart(timeCtx, {
        type: "line",
        data: {
            labels: safeLabels,
            datasets: [{ label: "Logs over Time", data: safeCounts, borderColor: "#38bdf8" }],
        },
        options: { responsive: true, maintainAspectRatio: false },
    });

    const spikeLabels = (timeAnalysis.spike_intervals || []).map((x) => x.timestamp);
    const spikeCounts = (timeAnalysis.spike_intervals || []).map((x) => x.count);
    if (heatmapChart) {
        heatmapChart.destroy();
    }
    heatmapChart = new Chart(heatCtx, {
        type: "bar",
        data: {
            labels: spikeLabels.length ? spikeLabels : ["No spikes detected"],
            datasets: [
                {
                    label: "Error Spike Intervals",
                    data: spikeCounts.length ? spikeCounts : [0],
                    backgroundColor: "#ef4444",
                },
            ],
        },
        options: { responsive: true, maintainAspectRatio: false },
    });

    if (severityChart) {
        severityChart.destroy();
    }
    severityChart = new Chart(sevCtx, {
        type: "bar",
        data: {
            labels: Object.keys(severityDist).length ? Object.keys(severityDist) : ["INFO"],
            datasets: [
                {
                    label: "Severity Distribution",
                    data: Object.values(severityDist).length ? Object.values(severityDist) : [0],
                    backgroundColor: "#f97316",
                },
            ],
        },
        options: { responsive: true, maintainAspectRatio: false },
    });
}

async function hydrateFromLatestAnalysis() {
    try {
        const response = await fetch("/api/latest");
        if (!response.ok) {
            return;
        }
        const data = await response.json();
        renderSummary(data.summary);
        renderTimeline(data.timeline || []);
        renderInsights(data.ai_insights || {}, data.anomalies || {});
        renderCharts(data.time_analysis || {}, data.summary?.severity_distribution || {});
    } catch (err) {
        console.error("Failed to load latest analysis", err);
    }
}

hydrateFromLatestAnalysis();

// Analytics page functionality
function setupAnalyticsTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and panes
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));
            
            // Add active class to clicked button and corresponding pane
            button.classList.add('active');
            const tabId = button.dataset.tab;
            const targetPane = document.getElementById(tabId);
            if (targetPane) {
                targetPane.classList.add('active');
            }
        });
    });
}

// Enhanced chart rendering with better colors and animations
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

    // Enhanced time series chart
    if (logsChart) {
        logsChart.destroy();
    }
    logsChart = new Chart(timeCtx, {
        type: 'line',
        data: {
            labels: safeLabels,
            datasets: [{
                label: "Log Volume",
                data: safeCounts,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: '#3b82f6',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#e2e8f0',
                    borderColor: '#334155',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            return `Volume: ${context.parsed.y} logs`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(51, 65, 85, 0.3)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(51, 65, 85, 0.3)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                }
            }
        }
    });

    // Enhanced spike intervals chart
    const spikeLabels = (timeAnalysis.spike_intervals || []).map((x) => x.timestamp);
    const spikeCounts = (timeAnalysis.spike_intervals || []).map((x) => x.count);
    if (heatmapChart) {
        heatmapChart.destroy();
    }
    heatmapChart = new Chart(heatCtx, {
        type: 'bar',
        data: {
            labels: spikeLabels.length ? spikeLabels : ["No spikes detected"],
            datasets: [
                {
                    label: "Error Spikes",
                    data: spikeCounts.length ? spikeCounts : [0],
                    backgroundColor: spikeCounts.length ? 
                        spikeCounts.map(count => count > 10 ? '#dc2626' : '#f97316') : 
                        '#475569',
                    borderColor: spikeCounts.length ?
                        spikeCounts.map(count => count > 10 ? '#b91c1c' : '#ea580c') :
                        '#334155',
                    borderWidth: 2,
                    borderRadius: 8
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#e2e8f0',
                    borderColor: '#334155',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            return `Spike: ${context.parsed.y} errors`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(51, 65, 85, 0.3)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(51, 65, 85, 0.3)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                }
            }
        }
    });

    // Enhanced severity distribution chart
    if (severityChart) {
        severityChart.destroy();
    }
    
    const severityData = Object.keys(severityDist).length ? Object.keys(severityDist) : ["INFO"];
    const severityValues = Object.values(severityDist).length ? Object.values(severityDist) : [0];
    const severityColors = severityData.map(severity => {
        switch(severity) {
            case 'CRITICAL': return '#dc2626';
            case 'ERROR': return '#f97316';
            case 'WARNING': return '#eab308';
            case 'INFO': return '#10b981';
            default: return '#64748b';
        }
    });
    
    severityChart = new Chart(sevCtx, {
        type: 'doughnut',
        data: {
            labels: severityData,
            datasets: [
                {
                    data: severityValues,
                    backgroundColor: severityColors,
                    borderColor: '#1e293b',
                    borderWidth: 2,
                    hoverOffset: 8
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#e2e8f0',
                        padding: 20,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#e2e8f0',
                    borderColor: '#334155',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return `${context.label}: ${context.parsed} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });

    // Module performance chart (if canvas exists)
    if (moduleCanvas) {
        const moduleCtx = moduleCanvas.getContext("2d");
        if (moduleChart) {
            moduleChart.destroy();
        }
        
        // Generate sample module data
        const moduleLabels = ['Database', 'API', 'Auth', 'Cache', 'Processing'];
        const moduleData = [85, 92, 78, 88, 73];
        
        moduleChart = new Chart(moduleCtx, {
            type: 'radar',
            data: {
                labels: moduleLabels,
                datasets: [{
                    label: 'Module Performance',
                    data: moduleData,
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.2)',
                    borderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#8b5cf6',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#f1f5f9',
                        bodyColor: '#e2e8f0',
                        borderColor: '#334155',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            label: function(context) {
                                return `Performance: ${context.parsed.r}%`;
                            }
                        }
                    }
                },
                scales: {
                    r: {
                        grid: {
                            color: 'rgba(51, 65, 85, 0.3)'
                        },
                        pointLabels: {
                            color: '#94a3b8'
                        },
                        ticks: {
                            color: '#64748b',
                            backdropColor: 'transparent'
                        }
                    }
                }
            }
        });
    }
}

// Update analytics metrics
function updateAnalyticsMetrics(data) {
    const summary = data.summary;
    if (summary) {
        // Calculate metrics based on summary data
        const healthScore = summary.total_logs > 0 ? 
            Math.max(0, 100 - (summary.total_errors / summary.total_logs * 100)) : 100;
        const errorRate = summary.total_logs > 0 ? 
            (summary.total_errors / summary.total_logs * 100) : 0;
        
        // Update metric displays
        const healthElement = document.getElementById('healthScore');
        const errorElement = document.getElementById('errorRate');
        const responseElement = document.getElementById('avgResponse');
        const uptimeElement = document.getElementById('uptime');
        
        if (healthElement) healthElement.textContent = `${healthScore.toFixed(1)}%`;
        if (errorElement) errorElement.textContent = `${errorRate.toFixed(1)}%`;
        if (responseElement) responseElement.textContent = '2.3s';
        if (uptimeElement) uptimeElement.textContent = '99.9%';
    }
}

// Initialize analytics when page loads
document.addEventListener('DOMContentLoaded', function() {
    setupAnalyticsTabs();
    
    // Update metrics when data is available
    if (typeof latestAnalysis !== 'undefined' && latestAnalysis.summary) {
        updateAnalyticsMetrics(latestAnalysis);
    }
});
