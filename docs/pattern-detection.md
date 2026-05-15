# Pattern Detection Guide

CrumbBob automatically detects patterns across your development sessions to identify recurring issues, relationships, and anomalies.

## Overview

Pattern detection analyzes your session history to find:
- **Recurring Risks**: Issues that appear repeatedly
- **File Relationships**: Files that always change together
- **Task Patterns**: Tasks that are frequently abandoned or take too long
- **Command Patterns**: Frequently used commands and sequences
- **Anomalies**: Unusual sessions or behaviors

## Detecting Patterns

### Detect All Patterns

```bash
crumdbob patterns detect --type all
```

This runs all pattern detectors and shows results grouped by type.

### Detect Specific Pattern Types

```bash
# Recurring risks only
crumdbob patterns detect --type risks

# File relationships only
crumdbob patterns detect --type files

# Task patterns only
crumdbob patterns detect --type tasks

# Command patterns only
crumdbob patterns detect --type commands

# Anomalies only
crumdbob patterns detect --type anomalies
```

## Pattern Types

### 1. Recurring Risks

Identifies risks that appear across multiple sessions, indicating persistent problems.

**Example Output:**
```
Recurring Risk Patterns (3):
  🔴 Risk appears in 5 sessions: Authentication token expiration not handled
     Confidence: 90%, Frequency: 5
  🟠 Risk appears in 3 sessions: Database migration complexity
     Confidence: 70%, Frequency: 3
```

**What it means:**
- These risks keep coming up
- They may indicate systemic issues
- High frequency = more urgent to address

**Recommendations:**
- Review and address recurring risks
- Add mitigation steps to workflow
- Create checklists to prevent recurrence
- Document root cause and solution

### 2. File Coupling

Detects files that always change together, indicating architectural coupling.

**Example Output:**
```
File Coupling Patterns (4):
  🟠 Files always change together: src/auth/login.py ↔ src/auth/session.py
     Confidence: 85%, Frequency: 7
  🟡 Files always change together: src/models/user.py ↔ src/api/users.py
     Confidence: 75%, Frequency: 5
```

**What it means:**
- These files are tightly coupled
- Changes to one often require changes to the other
- May indicate need for refactoring

**Recommendations:**
- Consider refactoring to reduce coupling
- Review architectural boundaries
- Add integration tests for these files
- Document the relationship

### 3. Abandoned Tasks

Identifies tasks that appear repeatedly but are never completed.

**Example Output:**
```
Abandoned Task Patterns (2):
  🔴 Task never completed (5x): Refactor database layer
     Confidence: 90%, Frequency: 5
  🟠 Task never completed (3x): Add comprehensive error handling
     Confidence: 70%, Frequency: 3
```

**What it means:**
- These tasks are repeatedly deferred
- May be too large or unclear
- Could indicate blockers

**Recommendations:**
- Break down into smaller tasks
- Reassess priority and feasibility
- Consider if still relevant
- Assign clear ownership and deadline

### 4. Long-Running Tasks

Identifies tasks that have been in progress for unusually long periods.

**Example Output:**
```
Long Running Task Patterns (2):
  🟠 Task in progress for 45 days: Migrate to new authentication system
     Confidence: 80%
  🟡 Task in progress for 21 days: Update API documentation
     Confidence: 80%
```

**What it means:**
- These tasks are taking longer than expected
- May have blockers or scope creep
- Need attention

**Recommendations:**
- Review progress and blockers
- Break into smaller milestones
- Set intermediate checkpoints
- Reassess scope and requirements

### 5. Frequent Commands

Identifies commands used most often across sessions.

**Example Output:**
```
Frequent Command Patterns (3):
  Frequently used command (25x): pytest tests/
  Frequently used command (18x): git commit -m
  Frequently used command (15x): npm run build
```

**What it means:**
- These are your most common workflows
- Good candidates for automation
- Should be well-documented

**Recommendations:**
- Create aliases or scripts
- Add to automation workflow
- Document for team members
- Consider CI/CD integration

### 6. Command Sequences

Detects commands that often appear together, indicating workflows.

**Example Output:**
```
Command Sequence Patterns (2):
  Commands often used together (8x): git add . → git commit -m
  Commands often used together (6x): npm test → npm run build
```

**What it means:**
- These commands form common workflows
- Good candidates for scripting
- Should be standardized

**Recommendations:**
- Create script to automate sequence
- Add to CI/CD pipeline
- Document workflow
- Share with team

### 7. Anomalies

Detects unusual patterns that deviate from normal behavior.

**Example Output:**
```
Anomaly Patterns (2):
  🟠 Session with unusually high risk count (15 vs avg 3.2)
  🟡 Session touched unusually many files (45 vs avg 12.5)
```

**What it means:**
- These sessions are outliers
- May indicate problems or special circumstances
- Worth investigating

**Recommendations:**
- Investigate cause of anomaly
- Review session details
- Consider if indicates a problem
- Document if intentional

## Analyzing Specific Files

Get detailed pattern analysis for a specific file:

```bash
crumdbob patterns analyze src/auth/login.py
```

**Output:**
```
Pattern Analysis for: src/auth/login.py

Session count: 8
Total mentions: 12
First seen: 2024-01-10T10:30:00Z
Last seen: 2024-02-15T14:22:00Z

Related files (change together):
  • src/auth/session.py
    Co-changes: 7, Confidence: 87%
  • tests/test_auth.py
    Co-changes: 6, Confidence: 75%
  • src/models/user.py
    Co-changes: 4, Confidence: 50%
```

This shows:
- How often the file appears
- Which files it changes with
- Confidence in the relationships

## Pattern Confidence Scores

Each pattern has a confidence score (0-100%):

- **90-100%**: Very high confidence, strong pattern
- **70-89%**: High confidence, reliable pattern
- **50-69%**: Medium confidence, likely pattern
- **Below 50%**: Low confidence, possible pattern

Confidence is based on:
- Frequency of occurrence
- Consistency across sessions
- Statistical significance
- Data quality

## Pattern Severity Levels

Patterns are categorized by severity:

- 🔴 **Critical**: Requires immediate attention
- 🟠 **High**: Should be addressed soon
- 🟡 **Medium**: Worth investigating
- 🟢 **Low**: Informational

## Using Pattern Detection

### Daily Workflow

```bash
# Morning: Check for new patterns
crumdbob patterns detect --type all

# Before major changes: Analyze impact
crumdbob patterns analyze src/critical/file.py

# Weekly: Review recurring issues
crumdbob patterns detect --type risks
```

### Team Workflow

```bash
# Sprint planning: Review abandoned tasks
crumdbob patterns detect --type tasks

# Architecture review: Check file coupling
crumdbob patterns detect --type files

# Process improvement: Analyze commands
crumdbob patterns detect --type commands
```

### Integration with Other Tools

```bash
# Export patterns to JSON
crumdbob patterns detect --type all --format json > patterns.json

# Combine with insights
crumdbob insights generate
crumdbob patterns detect --type all

# Use with dashboard
crumdbob dashboard
```

## Best Practices

1. **Run regularly**: Detect patterns weekly or after major changes
2. **Act on high-severity patterns**: Address critical and high-severity patterns promptly
3. **Track improvements**: Monitor if patterns decrease over time
4. **Share with team**: Discuss patterns in team meetings
5. **Document decisions**: Record why patterns exist and how you're addressing them

## Advanced Usage

### Filtering by Confidence

Patterns with confidence >= 70% are generally reliable:

```bash
# In your scripts
crumdbob patterns detect --type all | grep "Confidence: [7-9][0-9]%"
```

### Tracking Pattern Changes

Compare patterns over time:

```bash
# Save current patterns
crumdbob patterns detect --type all > patterns_$(date +%Y%m%d).txt

# Compare with previous
diff patterns_20240101.txt patterns_20240201.txt
```

### Custom Analysis

Use SQL for custom pattern analysis:

```bash
# Files that change together
crumdbob query sql "
  SELECT f1.path, f2.path, COUNT(*) as co_changes
  FROM files f1
  JOIN files f2 ON f1.session_id = f2.session_id AND f1.path < f2.path
  GROUP BY f1.path, f2.path
  HAVING co_changes >= 3
  ORDER BY co_changes DESC
"
```

## Next Steps

- Generate [Insights](insights.md) from patterns
- Make [Predictions](predictions.md) based on patterns
- View patterns in the [Dashboard](../README.md#dashboard)
- Query patterns with [Intelligent Queries](intelligent-queries.md)