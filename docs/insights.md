# Insights System Guide

CrumbBob's insights engine automatically generates actionable insights from your development patterns, helping you identify and address issues proactively.

## Overview

The insights system:
- **Automatically analyzes** your session history
- **Detects patterns** across multiple sessions
- **Generates insights** with actionable recommendations
- **Prioritizes** by severity and confidence
- **Tracks trends** over time

## Generating Insights

### Generate New Insights

```bash
crumdbob insights generate
```

This analyzes your entire database and generates insights from:
- Detected patterns
- Trend analysis
- Health metrics
- Anomalies

**Output:**
```
Generating insights from database...
✓ Generated 12 insights

Top Insights:
🔴 [CRITICAL] High percentage of open risks
   Confidence: 90%
   → Prioritize risk mitigation

🟠 [HIGH] Risk count increasing
   Confidence: 85%
   → Review recent changes for quality issues

🟡 [MEDIUM] Files always change together: src/auth/login.py ↔ src/auth/session.py
   Confidence: 87%
   → Consider refactoring to reduce coupling
```

## Viewing Insights

### List All Insights

```bash
crumdbob insights list
```

Shows all generated insights with severity, type, and confidence.

### Filter by Category

```bash
crumdbob insights list --category trend_risk_increase
crumdbob insights list --category health_high_open_risks
crumdbob insights list --category recurring_risk
```

### Top Insights

Get the most important insights:

```bash
crumdbob insights top 10
```

Shows top 10 insights ranked by:
- Severity (critical > high > medium > low)
- Confidence score
- Combined importance score

### Actionable Insights

Get insights that require immediate action:

```bash
crumdbob insights actionable
```

Shows only high-severity or high-confidence insights that need attention.

## Insight Types

### 1. Recurring Risk Insights

**Pattern:** Risks that appear across multiple sessions

**Example:**
```
🔴 [CRITICAL] Risk appears in 5 sessions: Authentication token expiration not handled
   Confidence: 90%
   
   Recommendations:
     • Review and address this recurring risk
     • Add mitigation steps to your workflow
     • Consider creating a checklist to prevent this risk
     • Document the root cause and solution
```

**Action:** Address the underlying issue causing the risk to recur.

### 2. File Coupling Insights

**Pattern:** Files that always change together

**Example:**
```
🟡 [MEDIUM] Files always change together: src/auth/login.py ↔ src/auth/session.py
   Confidence: 87%
   
   Recommendations:
     • Consider refactoring to reduce coupling
     • Review architectural boundaries
     • Add integration tests for these files
     • Document the relationship between these files
```

**Action:** Evaluate if the coupling is necessary or should be reduced.

### 3. Abandoned Task Insights

**Pattern:** Tasks that appear repeatedly but are never completed

**Example:**
```
🟠 [HIGH] Task never completed (5x): Refactor database layer
   Confidence: 90%
   
   Recommendations:
     • Break down this task into smaller steps
     • Reassess task priority and feasibility
     • Consider if this task is still relevant
     • Assign clear ownership and deadline
```

**Action:** Either complete the task or remove it if no longer relevant.

### 4. Long-Running Task Insights

**Pattern:** Tasks in progress for unusually long periods

**Example:**
```
🟠 [HIGH] Task in progress for 45 days: Migrate to new authentication system
   Confidence: 80%
   
   Recommendations:
     • Review task progress and blockers
     • Consider breaking into smaller tasks
     • Set intermediate milestones
     • Reassess scope and requirements
```

**Action:** Review and potentially break down the task.

### 5. Trend Insights

**Pattern:** Changes in metrics over time

**Example:**
```
🟠 [HIGH] Risk count increasing
   Average risks per session increased 35% over last 30 days
   Confidence: 85%
   
   Recommendations:
     • Review recent changes for quality issues
     • Increase code review rigor
     • Add more automated testing
     • Consider technical debt sprint
```

**Action:** Investigate cause of trend and take corrective action.

### 6. Health Insights

**Pattern:** Overall project health indicators

**Example:**
```
🟠 [HIGH] High percentage of open risks
   82% of risks are still open (41/50)
   Confidence: 90%
   
   Recommendations:
     • Prioritize risk mitigation
     • Review and close resolved risks
     • Create action plan for open risks
     • Consider risk review meeting
```

**Action:** Improve risk management process.

### 7. Anomaly Insights

**Pattern:** Unusual sessions or behaviors

**Example:**
```
🟠 [HIGH] Session with unusually high risk count (15 vs avg 3.2)
   Confidence: 80%
   
   Recommendations:
     • Investigate the cause of this anomaly
     • Review session details for unusual activity
     • Consider if this indicates a problem
```

**Action:** Investigate the anomaly to understand if it's a problem.

## Insight Severity Levels

Insights are categorized by severity:

- 🔴 **Critical**: Requires immediate attention
  - High-frequency recurring issues
  - Severe health problems
  - Major anomalies

- 🟠 **High**: Should be addressed soon
  - Moderate recurring issues
  - Negative trends
  - Significant coupling

- 🟡 **Medium**: Worth investigating
  - Minor patterns
  - Potential improvements
  - Informational trends

- 🟢 **Low**: Informational
  - Positive trends
  - Minor observations
  - General information

## Confidence Scores

Each insight has a confidence score (0-100%):

- **90-100%**: Very high confidence, act on it
- **70-89%**: High confidence, likely accurate
- **50-69%**: Medium confidence, investigate further
- **Below 50%**: Low confidence, use with caution

## Using Insights

### Daily Workflow

```bash
# Morning: Check for new insights
crumdbob insights generate
crumdbob insights actionable

# Act on critical insights immediately
# Plan to address high-severity insights this week
```

### Weekly Review

```bash
# Generate fresh insights
crumdbob insights generate

# Review top insights
crumdbob insights top 20

# Track progress on previous insights
# Document actions taken
```

### Sprint Planning

```bash
# Generate insights before planning
crumdbob insights generate

# Review actionable insights
crumdbob insights actionable

# Include insight-driven tasks in sprint:
# - Address recurring risks
# - Refactor coupled files
# - Complete abandoned tasks
```

### Team Meetings

```bash
# Prepare insights for discussion
crumdbob insights top 10 > team_insights.txt

# Discuss:
# - Critical and high-severity insights
# - Trends over time
# - Action plans
```

## Integration with Other Features

### With Pattern Detection

```bash
# Patterns feed into insights
crumdbob patterns detect --type all
crumdbob insights generate

# Insights are based on detected patterns
```

### With Predictions

```bash
# Use insights to inform predictions
crumdbob insights actionable
crumdbob predict risks "Planned change based on insights"
```

### With Dashboard

```bash
# View insights in context
crumdbob dashboard

# Shows top insights alongside other metrics
```

### With Queries

```bash
# Query for specific insight types
crumdbob query sql "SELECT * FROM insights WHERE insight_type = 'recurring_risk'"

# Analyze insight trends
crumdbob query sql "SELECT DATE(created_at), COUNT(*) FROM insights GROUP BY DATE(created_at)"
```

## Best Practices

### 1. Generate Regularly

```bash
# Weekly or after major changes
crumdbob insights generate
```

### 2. Act on Critical Insights

```bash
# Always address critical insights
crumdbob insights actionable | grep "CRITICAL"
```

### 3. Track Progress

```bash
# Document actions taken
echo "$(date): Addressed insight #123 - refactored auth coupling" >> insights_log.txt
```

### 4. Share with Team

```bash
# Export for team review
crumdbob insights top 10 > weekly_insights.md
```

### 5. Monitor Trends

```bash
# Compare insights over time
crumdbob insights generate > insights_$(date +%Y%m%d).txt
```

## Advanced Usage

### Custom Insight Analysis

```bash
# Query insights by severity
crumdbob query sql "
  SELECT insight_type, COUNT(*) as count
  FROM insights
  WHERE json_extract(content, '$.severity') = 'critical'
  GROUP BY insight_type
"
```

### Insight Metrics

```bash
# Track insight generation over time
crumdbob query sql "
  SELECT DATE(created_at) as date, COUNT(*) as insights
  FROM insights
  GROUP BY DATE(created_at)
  ORDER BY date DESC
  LIMIT 30
"
```

### Export for Reporting

```bash
# Export all insights to JSON
crumdbob query sql "SELECT * FROM insights" --format json > insights_report.json

# Generate markdown report
crumdbob insights top 20 > weekly_report.md
```

## Insight Lifecycle

1. **Generation**: Insights are generated from patterns and trends
2. **Storage**: Stored in database with timestamp
3. **Review**: Team reviews and prioritizes insights
4. **Action**: Tasks created to address insights
5. **Tracking**: Progress monitored over time
6. **Resolution**: Insight addressed, pattern should disappear

## Examples

### Example 1: Addressing Recurring Risks

```bash
# Generate insights
crumdbob insights generate

# Find recurring risk insights
crumdbob insights list --category recurring_risk

# For each recurring risk:
# 1. Create task to address root cause
# 2. Add to sprint backlog
# 3. Document mitigation steps
# 4. Update workflow to prevent recurrence
```

### Example 2: Reducing File Coupling

```bash
# Find coupling insights
crumdbob insights list --category file_coupling

# For each coupled pair:
# 1. Review architectural boundaries
# 2. Plan refactoring if needed
# 3. Add integration tests
# 4. Document relationship
```

### Example 3: Improving Task Completion

```bash
# Find task-related insights
crumdbob insights list --category abandoned_task
crumdbob insights list --category long_running_task

# For each task:
# 1. Break down into smaller tasks
# 2. Reassess priority
# 3. Assign ownership
# 4. Set realistic deadlines
```

## Next Steps

- View insights in the [Dashboard](../README.md#dashboard)
- Use [Pattern Detection](pattern-detection.md) to understand insights
- Make [Predictions](predictions.md) based on insights
- Query insights with [Intelligent Queries](intelligent-queries.md)