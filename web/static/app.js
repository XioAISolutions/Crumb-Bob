// CrumbBob Dashboard JavaScript

// API Base URL
const API_BASE = "/api";

// XSS protection — escape any untrusted value before interpolating into HTML.
// All API responses include session-derived text (descriptions, names, paths)
// that originate from Bob reports, so they MUST be escaped.
function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// safeId coerces an id-like value to a finite integer for use in inline
// handlers. Non-numeric input becomes 0, which routes to a no-op endpoint.
function safeId(value) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : 0;
}

// el creates a DOM element. Attributes go in `attrs` (use `class` for CSS class,
// `onclick` etc. for event handlers, anything else becomes setAttribute).
// Children can be strings (auto-converted to text nodes — no HTML parsing,
// so XSS via interpolation is impossible) or Node instances. Nullish children
// are skipped. Returns the created element.
function el(tag, attrs, ...children) {
  const e = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") e.className = String(v);
      else if (k.startsWith("on") && typeof v === "function")
        e[k.toLowerCase()] = v;
      else if (k === "style" && typeof v === "object")
        Object.assign(e.style, v);
      else e.setAttribute(k, String(v));
    }
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    e.appendChild(
      child instanceof Node ? child : document.createTextNode(String(child)),
    );
  }
  return e;
}

// emptyState renders a centered icon + message block for empty data states.
function emptyState(icon, message) {
  return el(
    "div",
    { class: "empty-state" },
    el("div", { class: "empty-state-icon" }, icon),
    el("div", { class: "empty-state-text" }, message),
  );
}

// badge renders a styled <span class="badge badge-{kind}"> with text content.
function badge(kind, text) {
  return el("span", { class: `badge badge-${kind}` }, text);
}

// replaceChildrenWith clears a container and appends the given nodes.
// Use this instead of innerHTML for safe rendering of dynamic content.
function replaceChildrenWith(container, ...nodes) {
  container.replaceChildren(...nodes.flat().filter((n) => n));
}

// Global state
const state = {
  currentView: "overview",
  sessions: [],
  stats: null,
  charts: {},
  theme: localStorage.getItem("theme") || "light",
};

// Initialize dashboard
document.addEventListener("DOMContentLoaded", () => {
  initializeTheme();
  initializeNavigation();
  initializeEventListeners();
  checkHealth();
  loadOverviewData();
  startAutoRefresh();
});

// Theme Management
function initializeTheme() {
  document.documentElement.setAttribute("data-theme", state.theme);
  updateThemeIcon();
}

function toggleTheme() {
  state.theme = state.theme === "light" ? "dark" : "light";
  localStorage.setItem("theme", state.theme);
  document.documentElement.setAttribute("data-theme", state.theme);
  updateThemeIcon();
}

function updateThemeIcon() {
  const icon = document.getElementById("theme-icon");
  if (!icon) return;
  icon.textContent = state.theme === "light" ? "🌙" : "☀️";
}

// Navigation
function initializeNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const view = item.dataset.view;
      switchView(view);
    });
  });
}

function switchView(viewName) {
  // Update navigation
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.view === viewName);
  });

  // Update views
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.remove("active");
  });
  document.getElementById(`${viewName}-view`).classList.add("active");

  // Update page title
  const titles = {
    overview: "Dashboard Overview",
    sessions: "Sessions",
    insights: "Insights",
    patterns: "Patterns",
    risks: "Risks",
    trends: "Trends",
    query: "Query",
  };
  document.getElementById("page-title").textContent =
    titles[viewName] || "Dashboard";

  // Load view data
  state.currentView = viewName;
  loadViewData(viewName);
}

function loadViewData(viewName) {
  switch (viewName) {
    case "overview":
      loadOverviewData();
      break;
    case "sessions":
      loadSessions();
      break;
    case "insights":
      loadInsights();
      break;
    case "patterns":
      loadPatterns();
      break;
    case "risks":
      loadRisks();
      break;
    case "trends":
      loadTrends();
      break;
  }
}

// Event Listeners
function initializeEventListeners() {
  // Refresh button
  document.getElementById("refresh-btn").addEventListener("click", () => {
    loadViewData(state.currentView);
  });

  // Theme toggle
  document
    .getElementById("theme-toggle")
    .addEventListener("click", toggleTheme);

  // Query submit
  document
    .getElementById("query-submit")
    .addEventListener("click", executeQuery);
  document.getElementById("query-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") executeQuery();
  });

  // Example queries
  document.querySelectorAll(".example-query").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.getElementById("query-input").value = btn.dataset.query;
      executeQuery();
    });
  });

  // Session detail close
  const closeBtn = document.getElementById("close-session-detail");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      document.getElementById("session-detail").style.display = "none";
    });
  }

  // Filters
  document
    .getElementById("insights-severity-filter")
    ?.addEventListener("change", loadInsights);
  document
    .getElementById("risks-status-filter")
    ?.addEventListener("change", loadRisks);
  document
    .getElementById("trends-period")
    ?.addEventListener("change", loadTrends);
}

// API Functions
async function apiGet(endpoint) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("API Error:", error);
    showError(`Failed to fetch data: ${error.message}`);
    return null;
  }
}

async function apiPost(endpoint, data) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("API Error:", error);
    showError(`Failed to post data: ${error.message}`);
    return null;
  }
}

// Health Check
async function checkHealth() {
  const health = await apiGet("/health");
  const statusDot = document.getElementById("status-dot");
  const statusText = document.getElementById("status-text");

  if (health) {
    statusDot.classList.add("connected");
    statusText.textContent = "Connected";
  } else {
    statusDot.classList.remove("connected");
    statusText.textContent = "Disconnected";
  }
}

// Overview Data
async function loadOverviewData() {
  showLoading("overview-view");

  // Load stats
  const stats = await apiGet("/stats");
  if (stats) {
    state.stats = stats;
    updateStatsCards(stats);
  }

  // Load recent sessions
  const sessionsData = await apiGet("/sessions?limit=5");
  if (sessionsData) {
    displayRecentSessions(sessionsData.sessions);
  }

  // Load trends for charts
  const trends = await apiGet("/trends?days=30");
  if (trends) {
    createSessionTimelineChart(trends.sessions);
    createRiskDistributionChart(stats);
  }

  hideLoading("overview-view");
}

function updateStatsCards(stats) {
  document.getElementById("stat-sessions").textContent =
    stats.total_sessions.toLocaleString();
  document.getElementById("stat-files").textContent =
    stats.total_files.toLocaleString();
  document.getElementById("stat-risks").textContent =
    stats.open_risks.toLocaleString();
  document.getElementById("stat-tasks").textContent =
    stats.pending_tasks.toLocaleString();
}

function renderSessionListItem(session, { compact } = { compact: false }) {
  const id = safeId(session.id);
  const title = session.session_name || `Session #${id}`;
  const dateMeta = formatDate(session.timestamp);
  const branchBadge = session.git_branch
    ? badge("info", session.git_branch)
    : null;
  const headerLeft = el(
    "div",
    null,
    el("div", { class: "list-item-title" }, title),
    el(
      "div",
      { class: "list-item-meta" },
      compact
        ? dateMeta
        : `${dateMeta}${session.git_author ? ` • ${session.git_author}` : ""}`,
    ),
  );
  const headerRight = compact ? null : el("div", null, branchBadge);
  const content = compact
    ? el(
        "div",
        { class: "list-item-content" },
        branchBadge,
        badge("success", `${session.file_count} files`),
        badge("warning", `${session.risk_count} risks`),
      )
    : el(
        "div",
        { class: "list-item-content" },
        badge("success", `${session.file_count} files`),
        badge("info", `${session.command_count} commands`),
        badge("warning", `${session.risk_count} risks`),
        badge("info", `${session.task_count} tasks`),
      );
  return el(
    "div",
    {
      class: "list-item",
      onclick: () => showSessionDetail(id),
    },
    el("div", { class: "list-item-header" }, headerLeft, headerRight),
    content,
  );
}

function displayRecentSessions(sessions) {
  const container = document.getElementById("recent-sessions-list");
  if (!sessions || sessions.length === 0) {
    replaceChildrenWith(container, emptyState("📭", "No sessions found"));
    return;
  }
  replaceChildrenWith(
    container,
    sessions.map((s) => renderSessionListItem(s, { compact: true })),
  );
}

// Sessions
async function loadSessions() {
  showLoading("sessions-view");
  const data = await apiGet("/sessions?limit=50");

  if (data && data.sessions) {
    state.sessions = data.sessions;
    displaySessions(data.sessions);
  }

  hideLoading("sessions-view");
}

function displaySessions(sessions) {
  const container = document.getElementById("sessions-list");
  if (!sessions || sessions.length === 0) {
    replaceChildrenWith(container, emptyState("📭", "No sessions found"));
    return;
  }
  replaceChildrenWith(
    container,
    sessions.map((s) => renderSessionListItem(s, { compact: false })),
  );
}

function renderDetailSection(title, ...children) {
  return el(
    "div",
    { class: "detail-section" },
    el("h4", null, title),
    ...children,
  );
}

function renderInfoLine(label, value) {
  return el("p", null, el("strong", null, `${label}:`), ` ${value ?? "N/A"}`);
}

function renderFileLine(file) {
  return el(
    "p",
    null,
    "📄 ",
    file.path,
    " ",
    badge("info", `${file.mention_count}x`),
  );
}

function renderRiskLine(risk) {
  const kind = risk.status === "open" ? "danger" : "success";
  return el("p", null, "⚠️ ", risk.description, " ", badge(kind, risk.status));
}

function renderTaskLine(task) {
  const kind = task.status === "completed" ? "success" : "warning";
  return el("p", null, "✓ ", task.description, " ", badge(kind, task.status));
}

async function showSessionDetail(sessionId) {
  const data = await apiGet(`/sessions/${safeId(sessionId)}`);
  if (!data) return;

  const panel = document.getElementById("session-detail");
  const content = document.getElementById("session-detail-content");
  const heading =
    data.session.session_name || `Session #${safeId(data.session.id)}`;

  replaceChildrenWith(
    content,
    el("h2", null, heading),
    renderDetailSection(
      "Information",
      renderInfoLine("Timestamp", formatDate(data.session.timestamp)),
      renderInfoLine("Branch", data.session.git_branch),
      renderInfoLine("Commit", data.session.git_commit),
      renderInfoLine("Author", data.session.git_author),
    ),
    renderDetailSection(
      `Files (${data.files.length})`,
      ...data.files.slice(0, 10).map(renderFileLine),
    ),
    renderDetailSection(
      `Risks (${data.risks.length})`,
      ...data.risks.map(renderRiskLine),
    ),
    renderDetailSection(
      `Tasks (${data.tasks.length})`,
      ...data.tasks.map(renderTaskLine),
    ),
  );

  panel.style.display = "block";
}

// Insights
async function loadInsights() {
  showLoading("insights-view");
  const severity = document.getElementById("insights-severity-filter").value;
  const url = severity ? `/insights?severity=${severity}` : "/insights";
  const data = await apiGet(url);

  if (data && data.insights) {
    displayInsights(data.insights);
  }

  hideLoading("insights-view");
}

function renderInsightCard(insight) {
  const recs =
    insight.recommendations && insight.recommendations.length > 0
      ? el(
          "div",
          { class: "insight-recommendations" },
          el("strong", null, "Recommendations:"),
          el(
            "ul",
            null,
            ...insight.recommendations.map((r) => el("li", null, r)),
          ),
        )
      : null;
  return el(
    "div",
    { class: `insight-card ${insight.severity}` },
    el(
      "div",
      { class: "insight-header" },
      el("div", { class: "insight-title" }, insight.title),
      badge(getSeverityBadgeClass(insight.severity), insight.severity),
    ),
    el("div", { class: "insight-description" }, insight.description),
    el(
      "div",
      { class: "insight-meta" },
      badge("info", insight.insight_type),
      el("span", null, `Confidence: ${(insight.confidence * 100).toFixed(0)}%`),
    ),
    recs,
  );
}

function displayInsights(insights) {
  const container = document.getElementById("insights-list");
  if (!insights || insights.length === 0) {
    replaceChildrenWith(container, emptyState("💡", "No insights available"));
    return;
  }
  replaceChildrenWith(container, insights.map(renderInsightCard));
}

// Patterns
async function loadPatterns() {
  showLoading("patterns-view");
  const data = await apiGet("/patterns");

  if (data && data.patterns) {
    displayPatterns(data.patterns);
  }

  hideLoading("patterns-view");
}

function renderPatternCard(pattern) {
  return el(
    "div",
    { class: "pattern-card" },
    el(
      "div",
      { class: "pattern-header" },
      el("span", { class: "pattern-type" }, pattern.pattern_type),
      badge(getSeverityBadgeClass(pattern.severity), pattern.severity),
    ),
    el("div", { class: "pattern-description" }, pattern.description),
    el(
      "div",
      { class: "pattern-meta" },
      `Frequency: ${pattern.frequency} • Confidence: ${(pattern.confidence * 100).toFixed(0)}%`,
    ),
  );
}

function displayPatterns(patterns) {
  const container = document.getElementById("patterns-list");
  if (!patterns || patterns.length === 0) {
    replaceChildrenWith(container, emptyState("🔍", "No patterns detected"));
    return;
  }
  replaceChildrenWith(container, patterns.map(renderPatternCard));
}

// Risks
async function loadRisks() {
  showLoading("risks-view");
  const status = document.getElementById("risks-status-filter").value;
  const url = status ? `/risks?status=${status}` : "/risks";
  const data = await apiGet(url);

  if (data && data.risks) {
    displayRisks(data.risks);
  }

  hideLoading("risks-view");
}

function renderRiskListItem(risk) {
  const sessionLabel =
    risk.session_name || `Session #${safeId(risk.session_id)}`;
  const meta = `${sessionLabel} • ${formatDate(risk.timestamp)}`;
  const statusKind = risk.status === "open" ? "danger" : "success";
  return el(
    "div",
    { class: "list-item" },
    el(
      "div",
      { class: "list-item-header" },
      el(
        "div",
        null,
        el("div", { class: "list-item-title" }, risk.description),
        el("div", { class: "list-item-meta" }, meta),
      ),
      badge(statusKind, risk.status),
    ),
  );
}

function displayRisks(risks) {
  const container = document.getElementById("risks-list");
  if (!risks || risks.length === 0) {
    replaceChildrenWith(container, emptyState("✅", "No risks found"));
    return;
  }
  replaceChildrenWith(container, risks.map(renderRiskListItem));
}

// Trends
async function loadTrends() {
  showLoading("trends-view");
  const days = document.getElementById("trends-period").value;
  const data = await apiGet(`/trends?days=${days}`);

  if (data) {
    createTrendsChart(data);
  }

  hideLoading("trends-view");
}

// Query
async function executeQuery() {
  const input = document.getElementById("query-input");
  const question = input.value.trim();

  if (!question) return;

  const resultsContainer = document.getElementById("query-results");
  replaceChildrenWith(
    resultsContainer,
    el("div", { class: "loading" }, el("div", { class: "spinner" })),
  );

  const data = await apiPost("/query", { question, limit: 50 });

  if (data && data.results) {
    displayQueryResults(data);
  } else {
    replaceChildrenWith(resultsContainer, emptyState("❌", "Query failed"));
  }
}

function displayQueryResults(data) {
  const container = document.getElementById("query-results");

  if (!data.results || data.results.length === 0) {
    replaceChildrenWith(
      container,
      emptyState("🔍", data.explanation || "No results found"),
    );
    return;
  }

  const keys = Object.keys(data.results[0]);
  const headerRow = el("tr", null, ...keys.map((key) => el("th", null, key)));
  const bodyRows = data.results.map((row) =>
    el("tr", null, ...keys.map((key) => el("td", null, formatValue(row[key])))),
  );

  replaceChildrenWith(
    container,
    el("h4", null, `Results (${data.row_count})`),
    el(
      "p",
      { style: { color: "var(--text-secondary)", marginBottom: "16px" } },
      data.explanation,
    ),
    el(
      "table",
      null,
      el("thead", null, headerRow),
      el("tbody", null, ...bodyRows),
    ),
  );
}

// Charts
function createSessionTimelineChart(data) {
  const ctx = document.getElementById("session-timeline-chart");
  if (!ctx) return;

  if (state.charts.sessionTimeline) {
    state.charts.sessionTimeline.destroy();
  }

  state.charts.sessionTimeline = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.map((d) => d.date),
      datasets: [
        {
          label: "Sessions",
          data: data.map((d) => d.count),
          borderColor: "rgb(11, 107, 203)",
          backgroundColor: "rgba(11, 107, 203, 0.1)",
          tension: 0.4,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: { beginAtZero: true },
      },
    },
  });
}

function createRiskDistributionChart(stats) {
  const ctx = document.getElementById("risk-distribution-chart");
  if (!ctx || !stats) return;

  if (state.charts.riskDistribution) {
    state.charts.riskDistribution.destroy();
  }

  state.charts.riskDistribution = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Open", "Mitigated", "Total"],
      datasets: [
        {
          data: [
            stats.open_risks,
            stats.total_risks - stats.open_risks,
            stats.total_risks,
          ],
          backgroundColor: [
            "rgb(220, 38, 38)",
            "rgb(21, 115, 71)",
            "rgb(139, 149, 161)",
          ],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { position: "bottom" },
      },
    },
  });
}

function createTrendsChart(data) {
  const ctx = document.getElementById("trends-chart");
  if (!ctx) return;

  if (state.charts.trends) {
    state.charts.trends.destroy();
  }

  const labels = data.sessions.map((d) => d.date);

  state.charts.trends = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Sessions",
          data: data.sessions.map((d) => d.count),
          borderColor: "rgb(11, 107, 203)",
          backgroundColor: "rgba(11, 107, 203, 0.1)",
        },
        {
          label: "Risks",
          data: data.risks.map((d) => d.count),
          borderColor: "rgb(220, 38, 38)",
          backgroundColor: "rgba(220, 38, 38, 0.1)",
        },
        {
          label: "Files",
          data: data.files.map((d) => d.count),
          borderColor: "rgb(21, 115, 71)",
          backgroundColor: "rgba(21, 115, 71, 0.1)",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { position: "bottom" },
      },
      scales: {
        y: { beginAtZero: true },
      },
    },
  });
}

// Utility Functions
function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleString();
}

function formatValue(value) {
  if (value === null || value === undefined) return "-";
  if (typeof value === "boolean") return value ? "✓" : "✗";
  if (typeof value === "number") return value.toLocaleString();
  return value;
}

function getSeverityBadgeClass(severity) {
  const map = {
    critical: "danger",
    high: "warning",
    medium: "info",
    low: "success",
  };
  return map[severity] || "info";
}

function showLoading(viewId) {
  const view = document.getElementById(viewId);
  if (!view) return;

  view.classList.add("is-loading");
  if (view.querySelector(".loading-overlay")) return;

  const overlay = document.createElement("div");
  overlay.className = "loading-overlay";

  const spinner = document.createElement("div");
  spinner.className = "spinner";
  spinner.setAttribute("aria-label", "Loading");

  overlay.appendChild(spinner);
  view.appendChild(overlay);
}

function hideLoading(viewId) {
  const view = document.getElementById(viewId);
  if (!view) return;

  view.classList.remove("is-loading");
  view.querySelector(".loading-overlay")?.remove();
}

function showError(message) {
  console.error(message);
  // Could add toast notification here
}

// Auto-refresh
function startAutoRefresh() {
  setInterval(() => {
    checkHealth();
    if (state.currentView === "overview") {
      loadOverviewData();
    }
  }, 30000); // Refresh every 30 seconds
}

// Made with Bob
