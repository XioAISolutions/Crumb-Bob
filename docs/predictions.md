# Predictions Guide

CrumbBob's prediction engine uses historical data to predict future outcomes, helping you make informed decisions before making changes.

## Overview

The prediction engine can predict:
- **Impact**: Which files will be affected by a change
- **Risks**: Potential risks for planned changes
- **Complexity**: How long a task will take
- **Tests**: Which tests should be run for file changes

## Prediction Types

### 1. Impact Prediction

Predict which files will be affected when you change a file.

```bash
crumdbob predict impact src/auth/login.py
```

**Output:**
```
Impact Prediction for: src/auth/login.py
Confidence: 87%
Reasoning: Based on 7 historical co-change patterns

Likely to be affected:
  • src/auth/session.py (confidence: 92%, 7 co-changes)
  • tests/test_auth.py (confidence: 85%, 6 co-changes)
  • src/models/user.py (confidence: 67%, 4 co-changes)
  • docs/auth.md (confidence: 50%, 3 co-changes)
```

**Use cases:**
- Before refactoring: Know what else needs updating
- Code review: Verify all related files were changed
- Testing: Know which areas to test
- Documentation: Update related docs

**How it works:**
- Analyzes historical co-change patterns
- Calculates probability based on frequency
- Ranks by confidence score
- Shows top 10 most likely files

### 2. Risk Prediction

Predict potential risks for a planned change based on similar past changes.

```bash
crumdbob predict risks "Refactor authentication system"
```

**Output:**
```
Risk Prediction for: Refactor authentication system
Confidence: 82%
Reasoning: Based on 5 similar past risks

Potential risks based on similar past changes:
  • [open] Authentication token expiration not handled
    Occurred 5x in history
  • [open] Session management race conditions
    Occurred 3x in history
  • [mitigated] Breaking changes to API
    Occurred 4x in history
```

**Use cases:**
- Sprint planning: Estimate risk before committing
- Architecture decisions: Compare alternatives
- Risk assessment: Proactive risk management
- Team communication: Set expectations

**How it works:**
- Extracts keywords from description
- Finds similar past risks
- Ranks by frequency and relevance
- Shows status (open/mitigated/accepted)

### 3. Complexity Prediction

Estimate how long a task will take based on similar past tasks.

```bash
crumdbob predict complexity "Add OAuth support"
```

**Output:**
```
Complexity Prediction for: Add OAuth support
Confidence: 78%
Reasoning: Based on 4 similar completed tasks

Estimated duration: 3-5 days
Based on average: 4.2 days
Range: 2.5-6.8 days
Similar tasks analyzed: 4
```

**Use cases:**
- Sprint planning: Accurate time estimates
- Resource allocation: Plan team capacity
- Deadline setting: Realistic commitments
- Progress tracking: Compare actual vs predicted

**How it works:**
- Finds similar completed tasks
- Calculates average duration
- Provides confidence range
- Adjusts for task complexity

**Confidence levels:**
- **High (>80%)**: Many similar tasks, reliable estimate
- **Medium (50-80%)**: Some similar tasks, reasonable estimate
- **Low (<50%)**: Few similar tasks, rough estimate

### 4. Test Recommendations

Recommend which tests to run based on file changes.

```bash
crumdbob predict tests src/auth/login.py src/auth/session.py
```

**Output:**
```
Test Recommendations for: src/auth/login.py, src/auth/session.py
Confidence: 85%
Reasoning: Based on 8 historical test patterns

Recommended tests:
  • tests/test_auth.py
    Reason: Historically changes with modified files
  • tests/integration/test_login_flow.py
    Reason: Historically changes with modified files
  • tests/test_session_management.py
    Reason: Conventional test file location
```

**Use cases:**
- Pre-commit: Run relevant tests
- CI/CD: Optimize test selection
- Code review: Verify test coverage
- TDD: Know what to test

**How it works:**
- Analyzes historical test patterns
- Finds tests that changed with these files
- Suggests conventional test locations
- Ranks by relevance

## Using Predictions

### Before Making Changes

```bash
# 1. Predict impact
crumdbob predict impact src/critical/file.py

# 2. Predict risks
crumdbob predict risks "Your planned change"

# 3. Get test recommendations
crumdbob predict tests src/file1.py src/file2.py

# 4. Estimate complexity
crumdbob predict complexity "Your task description"
```

### During Code Review

```bash
# Check if all impacted files were changed
crumdbob predict impact src/changed/file.py

# Verify appropriate tests were run
crumdbob predict tests src/changed/file.py
```

### Sprint Planning

```bash
# Estimate task durations
crumdbob predict complexity "Implement feature X"
crumdbob predict complexity "Refactor module Y"

# Assess risks
crumdbob predict risks "Major refactoring"
```

## Confidence Scores

All predictions include confidence scores:

- **90-100%**: Very high confidence, strong historical data
- **70-89%**: High confidence, good historical data
- **50-69%**: Medium confidence, some historical data
- **Below 50%**: Low confidence, limited historical data

**Factors affecting confidence:**
- Amount of historical data
- Consistency of patterns
- Similarity to past situations
- Data quality

## Improving Prediction Accuracy

### 1. Record More Sessions

More data = better predictions:

```bash
# Always record sessions
crumdbob pack input/ --out pack/ --record

# Or configure auto-recording
crumdbob config set auto_record true
```

### 2. Use Descriptive Names

Better descriptions = better matching:

```bash
# Good: Specific and descriptive
crumdbob predict complexity "Add OAuth 2.0 authentication with Google provider"

# Less good: Too vague
crumdbob predict complexity "Add auth"
```

### 3. Track Task Completion

Complete tasks to improve complexity predictions:

```bash
# Update task status in database
crumdbob query sql "UPDATE tasks SET status='completed' WHERE id=123"
```

### 4. Review Predictions

Compare predictions with actual outcomes:

```bash
# Before change
crumdbob predict impact src/file.py > predicted_impact.txt

# After change (compare with actual changes)
git diff --name-only HEAD~1 > actual_changes.txt
diff predicted_impact.txt actual_changes.txt
```

## Advanced Usage

### Batch Predictions

Predict for multiple files:

```bash
# Create script
for file in src/auth/*.py; do
  echo "=== $file ==="
  crumdbob predict impact "$file"
done
```

### Integration with CI/CD

```bash
# In your CI pipeline
changed_files=$(git diff --name-only HEAD~1)
crumdbob predict tests $changed_files > recommended_tests.txt

# Run recommended tests
cat recommended_tests.txt | xargs pytest
```

### Prediction Tracking

Track prediction accuracy over time:

```bash
# Save predictions
crumdbob predict impact src/file.py > predictions/$(date +%Y%m%d)_impact.txt

# Compare with actual
# (implement your own comparison logic)
```

## Limitations

**Predictions are not guarantees:**
- Based on historical patterns only
- Cannot account for new situations
- Confidence scores indicate reliability
- Always use human judgment

**Best practices:**
- Use predictions as guidance, not rules
- Combine with code review and testing
- Update predictions as you learn
- Track accuracy to improve over time

## Examples

### Example 1: Refactoring

```bash
# Before refactoring auth system
crumdbob predict impact src/auth/login.py
crumdbob predict risks "Refactor authentication to use JWT"
crumdbob predict tests src/auth/*.py

# Use predictions to:
# - Update all related files
# - Mitigate predicted risks
# - Run recommended tests
```

### Example 2: Sprint Planning

```bash
# Estimate all sprint tasks
crumdbob predict complexity "Implement user profile page"
crumdbob predict complexity "Add email notifications"
crumdbob predict complexity "Fix authentication bug"

# Use estimates for:
# - Sprint capacity planning
# - Task prioritization
# - Resource allocation
```

### Example 3: Code Review

```bash
# Review PR changes
git diff --name-only main...feature-branch > changed_files.txt

# Check predictions
for file in $(cat changed_files.txt); do
  crumdbob predict impact "$file"
done

# Verify:
# - All impacted files were changed
# - Appropriate tests were added
# - Risks were addressed
```

## Next Steps

- View predictions in the [Dashboard](../README.md#dashboard)
- Generate [Insights](insights.md) from predictions
- Detect [Patterns](pattern-detection.md) to improve predictions
- Use [Intelligent Queries](intelligent-queries.md) to analyze prediction accuracy