# Auto-Collect Workflow

## Overview

The auto-collect workflow eliminates manual artifact gathering by automatically discovering and collecting Git diffs, test outputs, and CI logs from your repository.

**Time Savings**: Reduces pack creation from 5-10 minutes to 30 seconds.

---

## Prerequisites

- Git repository initialized
- CrumbBob installed: `pip install -e .`
- Bob report available (or will be prompted to create one)

---

## Basic Usage

### Step 1: Navigate to Your Project

```bash
cd /path/to/your/project
```

### Step 2: Run Auto-Collect

```bash
crumdbob auto-collect --out ./generated
```

### Step 3: Interactive Artifact Selection

The command will scan your repository and present available artifacts:

```
Scanning repository for artifacts...

Found artifacts:
  [1] git-diff.patch (234 lines, staged + unstaged changes)
      Modified files: src/auth.py, tests/test_auth.py
  
  [2] pytest.log (1.2 KB, 5 minutes ago)
      15 passed, 2 failed
  
  [3] .github/workflows/test.yml (CI configuration)
      Last run: 2 hours ago, status: passed

Select artifacts to include (comma-separated, or 'all'): 
```

**Options**:
- Enter numbers: `1,2` - Select specific artifacts
- Enter `all` - Include all artifacts
- Press Enter - Skip artifact (use bob-report.md only)

### Step 4: Provide Bob Report (if needed)

If no `bob-report.md` is found, you'll be prompted:

```
No bob-report.md found in current directory.
Please provide path to Bob report: 
```

Enter the path to your Bob report file.

### Step 5: Pack Generation

The tool will:
1. Create input directory structure
2. Copy selected artifacts
3. Generate the complete pack
4. Display summary

```
Creating input directory: ./crumdbob-input
Copying artifacts...
  ✓ bob-report.md
  ✓ git-diff.patch
  ✓ pytest.log

Generating pack...
  ✓ 00_repo_genome.crumb
  ✓ 01_session_flight_recorder.crumb
  ✓ 02_next_task.crumb
  ✓ 03_test_plan.crumb
  ✓ 04_risk_register.crumb
  ✓ 05_agent_passport.crumb
  ✓ 06_replay_prompt.md
  ✓ 07_pr_summary.md
  ✓ 08_proof_chain.json

Pack generated successfully: ./generated
```

---

## Advanced Usage

### Non-Interactive Mode (CI/CD)

Skip interactive prompts and collect all artifacts:

```bash
crumdbob auto-collect --no-interactive --out ./generated
```

Perfect for automated pipelines where you want consistent behavior.

### Specify Existing Bob Report

If you already have a Bob report in a specific location:

```bash
crumdbob auto-collect --report ./docs/bob-session-2024-05-15.md --out ./generated
```

### Custom Input Directory

Specify where to create the input directory:

```bash
crumdbob auto-collect --input-dir ./my-crumdbob-input --out ./generated
```

---

## What Gets Collected

### 1. Git Diffs

**Staged Changes**:
```bash
git diff --cached
```

**Unstaged Changes**:
```bash
git diff
```

**Combined (Recommended)**:
```bash
git diff HEAD
```

The tool automatically selects the most relevant diff based on your repository state.

### 2. Test Outputs

**Supported Test Runners**:
- pytest: `pytest.log`, `.pytest_cache/`
- unittest: `test-results/`
- jest: `jest-results.json`
- mocha: `test-output.txt`

**Selection Criteria**:
- Most recent by timestamp
- Contains test results
- Readable format

### 3. CI Logs

**Supported CI Systems**:
- GitHub Actions: `.github/workflows/*.yml`
- GitLab CI: `.gitlab-ci.yml`
- Jenkins: `Jenkinsfile`
- CircleCI: `.circleci/config.yml`

**What's Extracted**:
- Configuration files
- Recent build logs (if available)
- Test results from CI runs

---

## Complete Example: New Feature Development

### Scenario

You've just completed a new authentication feature and want to create a CrumbBob pack for handoff.

### Step-by-Step

**1. Ensure changes are committed or staged**:
```bash
git add src/auth.py tests/test_auth.py
git status
```

**2. Run tests and capture output**:
```bash
pytest -v > pytest.log 2>&1
```

**3. Export Bob report**:
```bash
# In IBM Bob session
bob export-report bob-report.md
```

**4. Run auto-collect**:
```bash
crumdbob auto-collect --out ./generated
```

**5. Select artifacts**:
```
Found artifacts:
  [1] git-diff.patch (156 lines, staged changes)
  [2] pytest.log (2.3 KB, just now)

Select artifacts to include: all
```

**6. Verify pack**:
```bash
crumdbob doctor ./generated
crumdbob validate ./generated
```

**7. Review generated pack**:
```bash
ls -la ./generated/
cat ./generated/06_replay_prompt.md
```

**8. Share with team**:
```bash
git add generated/
git commit -m "Add CrumbBob pack for auth feature"
git push
```

---

## Troubleshooting

### No Artifacts Found

**Problem**: "No artifacts found in repository"

**Solutions**:
1. Ensure you're in a Git repository: `git status`
2. Make some changes: `git diff` should show output
3. Run tests to generate test output
4. Check if files are in `.gitignore`

### Git Diff Empty

**Problem**: Git diff is empty even though you made changes

**Solutions**:
1. Check if changes are committed: `git status`
2. Use `git diff HEAD` to see all changes
3. Ensure you're in the correct branch
4. Check if files are tracked: `git ls-files`

### Test Output Not Found

**Problem**: Test output files not detected

**Solutions**:
1. Run tests explicitly: `pytest -v > pytest.log 2>&1`
2. Check test output location: `find . -name "*.log"`
3. Ensure test runner is supported
4. Manually copy test output to input directory

### Permission Denied

**Problem**: Cannot create input directory or copy files

**Solutions**:
1. Check directory permissions: `ls -la`
2. Run with appropriate permissions
3. Specify different output directory: `--out ~/crumbbob-packs`

---

## Best Practices

### 1. Run After Significant Changes

Create packs after:
- Completing a feature
- Fixing a critical bug
- Major refactoring
- Before code review

### 2. Include Comprehensive Test Output

```bash
# Run full test suite with verbose output
pytest -v --tb=short > pytest.log 2>&1

# Then collect
crumdbob auto-collect --out ./generated
```

### 3. Clean Git State

```bash
# Commit or stage changes before collecting
git add .
git status

# Or use git stash if needed
git stash
crumdbob auto-collect --out ./generated
git stash pop
```

### 4. Descriptive Output Directories

```bash
# Use descriptive names
crumdbob auto-collect --out ./packs/auth-feature-2024-05-15

# Or use timestamps
crumdbob auto-collect --out ./packs/pack-$(date +%Y%m%d-%H%M%S)
```

### 5. Validate Immediately

```bash
# Always validate after generation
crumdbob auto-collect --out ./generated && \
  crumdbob validate ./generated && \
  crumdbob doctor ./generated
```

---

## Integration with Development Workflow

### Git Hooks

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Auto-generate pack before commit if bob-report.md exists

if [ -f "bob-report.md" ]; then
    echo "Generating CrumbBob pack..."
    crumdbob auto-collect --no-interactive --out ./generated
    git add generated/
fi
```

### Makefile Integration

```makefile
.PHONY: crumbbob-pack
crumbbob-pack:
	@echo "Generating CrumbBob pack..."
	@crumdbob auto-collect --no-interactive --out ./generated
	@crumdbob validate ./generated
	@echo "Pack ready: ./generated"

.PHONY: crumbbob-clean
crumbbob-clean:
	@rm -rf ./generated ./crumdbob-input
	@echo "Cleaned CrumbBob artifacts"
```

Usage:
```bash
make crumbbob-pack
make crumbbob-clean
```

### CI/CD Pipeline

**GitHub Actions** (`.github/workflows/crumbbob.yml`):

```yaml
name: Generate CrumbBob Pack
on:
  push:
    paths:
      - 'bob-report.md'
      - 'src/**'
      - 'tests/**'

jobs:
  generate-pack:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install CrumbBob
        run: pip install -e .
      
      - name: Generate pack
        run: crumdbob auto-collect --no-interactive --out ./generated
      
      - name: Validate pack
        run: |
          crumdbob validate ./generated
          crumdbob doctor ./generated
      
      - name: Upload pack
        uses: actions/upload-artifact@v3
        with:
          name: crumbbob-pack
          path: ./generated
```

---

## Comparison: Before vs After

### Before Auto-Collect

```bash
# Manual process (5-10 minutes)

# 1. Find and copy git diff
git diff HEAD > git-diff.patch

# 2. Find test output
find . -name "pytest.log" -o -name "test-results.txt"
cp tests/pytest.log test-output.txt

# 3. Create input directory
mkdir -p crumdbob-input
cp bob-report.md crumdbob-input/
cp git-diff.patch crumdbob-input/
cp test-output.txt crumdbob-input/

# 4. Generate pack
crumdbob pack crumdbob-input --out generated

# 5. Clean up
rm git-diff.patch test-output.txt
```

### After Auto-Collect

```bash
# Automated process (30 seconds)

crumdbob auto-collect --out ./generated
# Select artifacts interactively
# Done!
```

**Time Saved**: 95% reduction in manual work

---

## Next Steps

- **Active Development**: Use [watch mode](02-watch-mode-workflow.md) to keep packs current
- **PR Review**: Use [diff workflow](03-diff-workflow.md) to compare pack versions
- **Team Collaboration**: Share generated packs via Git or artifact storage

---

## Summary

Auto-collect workflow:
1. ✅ Eliminates manual artifact gathering
2. ✅ Discovers artifacts automatically
3. ✅ Interactive selection for control
4. ✅ Non-interactive mode for automation
5. ✅ Integrates with Git, CI/CD, and development tools
6. ✅ Reduces pack creation time by 95%

**Key Command**:
```bash
crumdbob auto-collect --out ./generated
```

That's it! You now have a complete CrumbBob pack ready for handoff, review, or replay.