// CrumbBob Dashboard JavaScript

// API Base URL
const API_BASE = '/api';

// Global state
const state = {
    currentView: 'overview',
    sessions: [],
    stats: null,
    charts: {},
    theme: localStorage.getItem('theme') || 'light',
};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    initializeNavigation();
    initializeEventListeners();
    checkHealth();
    loadOverviewData();
    startAutoRefresh();
});

// Theme Management
function initializeTheme() {
    document.documentElement.setAttribute('data-theme', state.theme);
    updateThemeIcon();
}

function toggleTheme() {
    state.theme = state.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', state.theme);
    document.documentElement.setAttribute('data-theme', state.theme);
    updateThemeIcon();
}

function updateThemeIcon() {
    const icon = document.getElementById('theme-icon');
    if (!icon) return;
    icon.textContent = state.theme === 'light' ? '🌙' : '☀️';
}

// Navigation
function initializeNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.dataset.view;
            switchView(view);
        });
    });
}

function switchView(viewName) {
    // Update navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.view === viewName);
    });

    // Update views
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });
    document.getElementById(`${viewName}-view`).classList.add('active');

    // Update page title
    const titles = {
        overview: 'Dashboard Overview',
        sessions: 'Sessions',
        insights: 'Insights',
        patterns: 'Patterns',
        risks: 'Risks',
        trends: 'Trends',
        query: 'Query',
    };
    document.getElementById('page-title').textContent = titles[viewName] || 'Dashboard';

    // Load view data
    state.currentView = viewName;
    loadViewData(viewName);
}

function loadViewData(viewName) {
    switch (viewName) {
        case 'overview':
            loadOverviewData();
            break;
        case 'sessions':
            loadSessions();
            break;
        case 'insights':
            loadInsights();
            break;
        case 'patterns':
            loadPatterns();
            break;
        case 'risks':
            loadRisks();
            break;
        case 'trends':
            loadTrends();
            break;
    }
}

// Event Listeners
function initializeEventListeners() {
    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', () => {
        loadViewData(state.currentView);
    });

    // Theme toggle
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);

    // Query submit
    document.getElementById('query-submit').addEventListener('click', executeQuery);
    document.getElementById('query-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') executeQuery();
    });

    // Example queries
    document.querySelectorAll('.example-query').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('query-input').value = btn.dataset.query;
            executeQuery();
        });
    });

    // Session detail close
    const closeBtn = document.getElementById('close-session-detail');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            document.getElementById('session-detail').style.display = 'none';
        });
    }

    // Filters
    document.getElementById('insights-severity-filter')?.addEventListener('change', loadInsights);
    document.getElementById('risks-status-filter')?.addEventListener('change', loadRisks);
    document.getElementById('trends-period')?.addEventListener('change', loadTrends);
}

// API Functions
async function apiGet(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showError(`Failed to fetch data: ${error.message}`);
        return null;
    }
}

async function apiPost(endpoint, data) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showError(`Failed to post data: ${error.message}`);
        return null;
    }
}

// Health Check
async function checkHealth() {
    const health = await apiGet('/health');
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    
    if (health) {
        statusDot.classList.add('connected');
        statusText.textContent = 'Connected';
    } else {
        statusDot.classList.remove('connected');
        statusText.textContent = 'Disconnected';
    }
}

// Overview Data
async function loadOverviewData() {
    showLoading('overview-view');
    
    // Load stats
    const stats = await apiGet('/stats');
    if (stats) {
        state.stats = stats;
        updateStatsCards(stats);
    }

    // Load recent sessions
    const sessionsData = await apiGet('/sessions?limit=5');
    if (sessionsData) {
        displayRecentSessions(sessionsData.sessions);
    }

    // Load trends for charts
    const trends = await apiGet('/trends?days=30');
    if (trends) {
        createSessionTimelineChart(trends.sessions);
        createRiskDistributionChart(stats);
    }

    hideLoading('overview-view');
}

function updateStatsCards(stats) {
    document.getElementById('stat-sessions').textContent = stats.total_sessions.toLocaleString();
    document.getElementById('stat-files').textContent = stats.total_files.toLocaleString();
    document.getElementById('stat-risks').textContent = stats.open_risks.toLocaleString();
    document.getElementById('stat-tasks').textContent = stats.pending_tasks.toLocaleString();
}

function displayRecentSessions(sessions) {
    const container = document.getElementById('recent-sessions-list');
    
    if (!sessions || sessions.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📭</div><div class="empty-state-text">No sessions found</div></div>';
        return;
    }

    container.innerHTML = sessions.map(session => `
        <div class="list-item" onclick="showSessionDetail(${session.id})">
            <div class="list-item-header">
                <div class="list-item-title">${session.session_name || `Session #${session.id}`}</div>
                <div class="list-item-meta">${formatDate(session.timestamp)}</div>
            </div>
            <div class="list-item-content">
                ${session.git_branch ? `<span class="badge badge-info">${session.git_branch}</span>` : ''}
                <span class="badge badge-success">${session.file_count} files</span>
                <span class="badge badge-warning">${session.risk_count} risks</span>
            </div>
        </div>
    `).join('');
}

// Sessions
async function loadSessions() {
    showLoading('sessions-view');
    const data = await apiGet('/sessions?limit=50');
    
    if (data && data.sessions) {
        state.sessions = data.sessions;
        displaySessions(data.sessions);
    }
    
    hideLoading('sessions-view');
}

function displaySessions(sessions) {
    const container = document.getElementById('sessions-list');
    
    if (!sessions || sessions.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📭</div><div class="empty-state-text">No sessions found</div></div>';
        return;
    }

    container.innerHTML = sessions.map(session => `
        <div class="list-item" onclick="showSessionDetail(${session.id})">
            <div class="list-item-header">
                <div>
                    <div class="list-item-title">${session.session_name || `Session #${session.id}`}</div>
                    <div class="list-item-meta">
                        ${formatDate(session.timestamp)}
                        ${session.git_author ? ` • ${session.git_author}` : ''}
                    </div>
                </div>
                <div>
                    ${session.git_branch ? `<span class="badge badge-info">${session.git_branch}</span>` : ''}
                </div>
            </div>
            <div class="list-item-content">
                <span class="badge badge-success">${session.file_count} files</span>
                <span class="badge badge-info">${session.command_count} commands</span>
                <span class="badge badge-warning">${session.risk_count} risks</span>
                <span class="badge badge-info">${session.task_count} tasks</span>
            </div>
        </div>
    `).join('');
}

async function showSessionDetail(sessionId) {
    const data = await apiGet(`/sessions/${sessionId}`);
    if (!data) return;

    const panel = document.getElementById('session-detail');
    const content = document.getElementById('session-detail-content');
    
    content.innerHTML = `
        <h2>${data.session.session_name || `Session #${data.session.id}`}</h2>
        <div class="detail-section">
            <h4>Information</h4>
            <p><strong>Timestamp:</strong> ${formatDate(data.session.timestamp)}</p>
            <p><strong>Branch:</strong> ${data.session.git_branch || 'N/A'}</p>
            <p><strong>Commit:</strong> ${data.session.git_commit || 'N/A'}</p>
            <p><strong>Author:</strong> ${data.session.git_author || 'N/A'}</p>
        </div>
        
        <div class="detail-section">
            <h4>Files (${data.files.length})</h4>
            ${data.files.slice(0, 10).map(f => `<p>📄 ${f.path} <span class="badge badge-info">${f.mention_count}x</span></p>`).join('')}
        </div>
        
        <div class="detail-section">
            <h4>Risks (${data.risks.length})</h4>
            ${data.risks.map(r => `<p>⚠️ ${r.description} <span class="badge badge-${r.status === 'open' ? 'danger' : 'success'}">${r.status}</span></p>`).join('')}
        </div>
        
        <div class="detail-section">
            <h4>Tasks (${data.tasks.length})</h4>
            ${data.tasks.map(t => `<p>✓ ${t.description} <span class="badge badge-${t.status === 'completed' ? 'success' : 'warning'}">${t.status}</span></p>`).join('')}
        </div>
    `;
    
    panel.style.display = 'block';
}

// Insights
async function loadInsights() {
    showLoading('insights-view');
    const severity = document.getElementById('insights-severity-filter').value;
    const url = severity ? `/insights?severity=${severity}` : '/insights';
    const data = await apiGet(url);
    
    if (data && data.insights) {
        displayInsights(data.insights);
    }
    
    hideLoading('insights-view');
}

function displayInsights(insights) {
    const container = document.getElementById('insights-list');
    
    if (!insights || insights.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">💡</div><div class="empty-state-text">No insights available</div></div>';
        return;
    }

    container.innerHTML = insights.map(insight => `
        <div class="insight-card ${insight.severity}">
            <div class="insight-header">
                <div class="insight-title">${insight.title}</div>
                <span class="badge badge-${getSeverityBadgeClass(insight.severity)}">${insight.severity}</span>
            </div>
            <div class="insight-description">${insight.description}</div>
            <div class="insight-meta">
                <span class="badge badge-info">${insight.insight_type}</span>
                <span>Confidence: ${(insight.confidence * 100).toFixed(0)}%</span>
            </div>
            ${insight.recommendations && insight.recommendations.length > 0 ? `
                <div class="insight-recommendations">
                    <strong>Recommendations:</strong>
                    <ul>
                        ${insight.recommendations.map(r => `<li>${r}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        </div>
    `).join('');
}

// Patterns
async function loadPatterns() {
    showLoading('patterns-view');
    const data = await apiGet('/patterns');
    
    if (data && data.patterns) {
        displayPatterns(data.patterns);
    }
    
    hideLoading('patterns-view');
}

function displayPatterns(patterns) {
    const container = document.getElementById('patterns-list');
    
    if (!patterns || patterns.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔍</div><div class="empty-state-text">No patterns detected</div></div>';
        return;
    }

    container.innerHTML = patterns.map(pattern => `
        <div class="pattern-card">
            <div class="pattern-header">
                <span class="pattern-type">${pattern.pattern_type}</span>
                <span class="badge badge-${getSeverityBadgeClass(pattern.severity)}">${pattern.severity}</span>
            </div>
            <div class="pattern-description">${pattern.description}</div>
            <div class="pattern-meta">
                Frequency: ${pattern.frequency} • Confidence: ${(pattern.confidence * 100).toFixed(0)}%
            </div>
        </div>
    `).join('');
}

// Risks
async function loadRisks() {
    showLoading('risks-view');
    const status = document.getElementById('risks-status-filter').value;
    const url = status ? `/risks?status=${status}` : '/risks';
    const data = await apiGet(url);
    
    if (data && data.risks) {
        displayRisks(data.risks);
    }
    
    hideLoading('risks-view');
}

function displayRisks(risks) {
    const container = document.getElementById('risks-list');
    
    if (!risks || risks.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">✅</div><div class="empty-state-text">No risks found</div></div>';
        return;
    }

    container.innerHTML = risks.map(risk => `
        <div class="list-item">
            <div class="list-item-header">
                <div>
                    <div class="list-item-title">${risk.description}</div>
                    <div class="list-item-meta">
                        ${risk.session_name || `Session #${risk.session_id}`} • ${formatDate(risk.timestamp)}
                    </div>
                </div>
                <span class="badge badge-${risk.status === 'open' ? 'danger' : 'success'}">${risk.status}</span>
            </div>
        </div>
    `).join('');
}

// Trends
async function loadTrends() {
    showLoading('trends-view');
    const days = document.getElementById('trends-period').value;
    const data = await apiGet(`/trends?days=${days}`);
    
    if (data) {
        createTrendsChart(data);
    }
    
    hideLoading('trends-view');
}

// Query
async function executeQuery() {
    const input = document.getElementById('query-input');
    const question = input.value.trim();
    
    if (!question) return;

    const resultsContainer = document.getElementById('query-results');
    resultsContainer.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    const data = await apiPost('/query', { question, limit: 50 });
    
    if (data && data.results) {
        displayQueryResults(data);
    } else {
        resultsContainer.innerHTML = '<div class="empty-state"><div class="empty-state-icon">❌</div><div class="empty-state-text">Query failed</div></div>';
    }
}

function displayQueryResults(data) {
    const container = document.getElementById('query-results');
    
    if (!data.results || data.results.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <div class="empty-state-text">${data.explanation || 'No results found'}</div>
            </div>
        `;
        return;
    }

    const keys = Object.keys(data.results[0]);
    
    container.innerHTML = `
        <h4>Results (${data.row_count})</h4>
        <p style="color: var(--text-secondary); margin-bottom: 16px;">${data.explanation}</p>
        <table>
            <thead>
                <tr>${keys.map(key => `<th>${key}</th>`).join('')}</tr>
            </thead>
            <tbody>
                ${data.results.map(row => `
                    <tr>${keys.map(key => `<td>${formatValue(row[key])}</td>`).join('')}</tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// Charts
function createSessionTimelineChart(data) {
    const ctx = document.getElementById('session-timeline-chart');
    if (!ctx) return;

    if (state.charts.sessionTimeline) {
        state.charts.sessionTimeline.destroy();
    }

    state.charts.sessionTimeline = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.date),
            datasets: [{
                label: 'Sessions',
                data: data.map(d => d.count),
                borderColor: 'rgb(11, 107, 203)',
                backgroundColor: 'rgba(11, 107, 203, 0.1)',
                tension: 0.4,
                fill: true,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function createRiskDistributionChart(stats) {
    const ctx = document.getElementById('risk-distribution-chart');
    if (!ctx || !stats) return;

    if (state.charts.riskDistribution) {
        state.charts.riskDistribution.destroy();
    }

    state.charts.riskDistribution = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Open', 'Mitigated', 'Total'],
            datasets: [{
                data: [stats.open_risks, stats.total_risks - stats.open_risks, stats.total_risks],
                backgroundColor: [
                    'rgb(220, 38, 38)',
                    'rgb(21, 115, 71)',
                    'rgb(139, 149, 161)',
                ],
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

function createTrendsChart(data) {
    const ctx = document.getElementById('trends-chart');
    if (!ctx) return;

    if (state.charts.trends) {
        state.charts.trends.destroy();
    }

    const labels = data.sessions.map(d => d.date);

    state.charts.trends = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Sessions',
                    data: data.sessions.map(d => d.count),
                    borderColor: 'rgb(11, 107, 203)',
                    backgroundColor: 'rgba(11, 107, 203, 0.1)',
                },
                {
                    label: 'Risks',
                    data: data.risks.map(d => d.count),
                    borderColor: 'rgb(220, 38, 38)',
                    backgroundColor: 'rgba(220, 38, 38, 0.1)',
                },
                {
                    label: 'Files',
                    data: data.files.map(d => d.count),
                    borderColor: 'rgb(21, 115, 71)',
                    backgroundColor: 'rgba(21, 115, 71, 0.1)',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'bottom' }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

// Utility Functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

function formatValue(value) {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'boolean') return value ? '✓' : '✗';
    if (typeof value === 'number') return value.toLocaleString();
    return value;
}

function getSeverityBadgeClass(severity) {
    const map = {
        critical: 'danger',
        high: 'warning',
        medium: 'info',
        low: 'success',
    };
    return map[severity] || 'info';
}

function showLoading(viewId) {
    const view = document.getElementById(viewId);
    if (!view) return;

    view.classList.add('is-loading');
    if (view.querySelector('.loading-overlay')) return;

    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';

    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    spinner.setAttribute('aria-label', 'Loading');

    overlay.appendChild(spinner);
    view.appendChild(overlay);
}

function hideLoading(viewId) {
    const view = document.getElementById(viewId);
    if (!view) return;

    view.classList.remove('is-loading');
    view.querySelector('.loading-overlay')?.remove();
}

function showError(message) {
    console.error(message);
    // Could add toast notification here
}

// Auto-refresh
function startAutoRefresh() {
    setInterval(() => {
        checkHealth();
        if (state.currentView === 'overview') {
            loadOverviewData();
        }
    }, 30000); // Refresh every 30 seconds
}

// Made with Bob
