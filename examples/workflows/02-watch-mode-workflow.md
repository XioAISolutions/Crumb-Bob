# Watch Mode Workflow

## Overview

Watch mode monitors your input directory for changes and automatically regenerates the CrumbBob pack when files are modified. This eliminates stale packs during active development and maintains continuous memory updates.

**Key Benefit**: Zero manual regeneration - packs stay current automatically.

---

## Prerequisites

- CrumbBob installed: `pip install -e .`
- Watchdog package installed: `pip install watchdog`
- Input directory with `bob-report.md` and optional artifacts

---

## Basic Usage

### Step 1: Prepare Input Directory

```bash
# Create input directory with initial files
mkdir -p crumdbob-input
cp bob-report.md crumdbob-input/
```

### Step 2: Start Watch Mode

```bash
crumdbob watch ./crumdbob-input --out ./generated
```

### Step 3: See Live Status

```
Watching: ./crumdbob-input
Output: ./generated
Debounce: 2.0s

[12:34:56] 🔄 Initial pack generation...
[12:35:00] ✓ Pack generated successfully (4.2s)
[12:35:00] 👀 Watching for changes... (Ctrl+C to stop)
```

### Step 4: Work Normally

Edit files in your editor - watch mode detects changes automatically:

```
[12:36:15] ⚡ Change detected: bob-report.md modified
[12:36:15] ⏳ Waiting for changes to settle...
[12:36:17] 🔄 Regenerating pack...
[12:36:21] ✓ Pack regenerated successfully (4.1s)
[12:36:21] 👀 Watching for changes... (Ctrl+C to stop)
```

### Step 5: Stop Watch Mode

Press `Ctrl+C` to gracefully shutdown:

```
^C
[12:40:30] 🛑 Shutting down watch mode...
[12:40:30] ✓ Watch mode stopped
```

---

## Advanced Usage

### Custom Debounce Period

Control how long to wait after the last change before regenerating:

```bash
# Wait 5 seconds (useful for rapid edits)
crumdbob watch ./crumdbob-input --out ./generated --debounce 5.0

# Wait 1 second (faster feedback)
crumdbob watch ./crumdbob-input --out ./generated --debounce 1.0
```

**Recommendation**: Use 2-3 seconds for most workflows.

### Watch Multiple Artifact Types

Watch mode monitors all relevant files:

```bash
# Add artifacts to input directory
cp git-diff.patch crumdbob-input/
cp test-output.txt crumdbob-input/
cp repo-notes.md crumdbob-input/

# Start watching - all files monitored
crumdbob watch ./crumdbob-input --out ./generated
```

Changes to any file trigger regeneration:
- `bob-report.md` - Main report
- `*.patch` - Git diffs
- `*.txt` - Test outputs
- `*.md` - Additional notes

---

## What Gets Monitored

### File Events

**Triggers Regeneration**:
- File modified (content changed)
- File created (new artifact added)
- File deleted (artifact removed)

**Ignored**:
- Hidden files (`.git/`, `.DS_Store`)
- Temporary files (`*.tmp`, `*.swp`)
- Output directory (prevents infinite loops)
- Editor backup files (`*~`, `*.bak`)

### Debouncing Logic

Watch mode uses intelligent debouncing to prevent regeneration storms:

```
Edit 1: bob-report.md changed at 12:00:00
        → Start 2s timer

Edit 2: bob-report.md changed at 12:00:01
        → Reset 2s timer

Edit 3: bob-report.md changed at 12:00:02
        → Reset 2s timer

No more changes...
        → Timer expires at 12:00:04
        → Regenerate pack
```

This ensures:
- Multiple rapid edits trigger only one regeneration
- No wasted CPU on incomplete changes
- Smooth development experience

---

## Complete Example: Active Development Session

### Scenario

You're actively developing a new feature and want the CrumbBob pack to stay current as you work.

### Setup (One-Time)

**1. Create input directory**:
```bash
mkdir -p crumdbob-input
```

**2. Copy initial files**:
```bash
cp bob-report.md crumdbob-input/
git diff HEAD > crumdbob-input/git-diff.patch
pytest -v > crumdbob-input/test-output.txt 2>&1
```

**3. Start watch mode in a dedicated terminal**:
```bash
# Terminal 1: Watch mode
crumdbob watch ./crumdbob-input --out ./generated
```

### Development Loop

**Terminal 2: Your normal workflow**:

```bash
# Edit code
vim src/auth.py

# Run tests
pytest tests/test_auth.py -v > crumdbob-input/test-output.txt 2>&1

# Update Bob report
vim crumdbob-input/bob-report.md

# Update git diff
git add src/auth.py tests/test_auth.py
git diff --cached > crumdbob-input/git-diff.patch
```

**Terminal 1: Automatic updates**:

```
[13:15:23] ⚡ Change detected: test-output.txt modified
[13:15:23] ⏳ Waiting for changes to settle...
[13:15:25] 🔄 Regenerating pack...
[13:15:29] ✓ Pack regenerated successfully (4.1s)

[13:18:45] ⚡ Change detected: bob-report.md modified
[13:18:45] ⏳ Waiting for changes to settle...
[13:18:47] 🔄 Regenerating pack...
[13:18:51] ✓ Pack regenerated successfully (4.0s)

[13:22:10] ⚡ Change detected: git-diff.patch modified
[13:22:10] ⏳ Waiting for changes to settle...
[13:22:12] 🔄 Regenerating pack...
[13:22:16] ✓ Pack regenerated successfully (4.2s)
```

### Review Current Pack

**Terminal 3: Review anytime**:

```bash
# Check pack health
crumdbob doctor ./generated

# View replay prompt
cat ./generated/06_replay_prompt.md

# View risk register
cat ./generated/04_risk_register.crumb

# Compare with previous version
crumdbob diff ./generated-backup ./generated
```

---

## Integration Patterns

### Pattern 1: Dual Terminal Setup

**Terminal 1**: Watch mode (left side)
```bash
crumdbob watch ./crumdbob-input --out ./generated
```

**Terminal 2**: Development (right side)
```bash
# Your normal workflow
vim src/
pytest
git commit
```

**Benefit**: See pack updates in real-time while working.

### Pattern 2: Background Process

```bash
# Start watch mode in background
crumdbob watch ./crumdbob-input --out ./generated &
WATCH_PID=$!

# Work normally
vim src/auth.py
pytest

# Stop watch mode when done
kill $WATCH_PID
```

**Benefit**: Cleaner terminal, automatic updates.

### Pattern 3: tmux/screen Session

```bash
# Create tmux session
tmux new-session -d -s crumbbob

# Start watch mode in tmux
tmux send-keys -t crumbbob "crumdbob watch ./crumdbob-input --out ./generated" C-m

# Attach to see status
tmux attach -t crumbbob

# Detach and continue working
# Ctrl+B, then D

# Kill session when done
tmux kill-session -t crumbbob
```

**Benefit**: Persistent watch mode across terminal sessions.

### Pattern 4: IDE Integration

**VSCode Task** (`.vscode/tasks.json`):

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "CrumbBob Watch",
      "type": "shell",
      "command": "crumdbob watch ./crumdbob-input --out ./generated",
      "isBackground": true,
      "problemMatcher": [],
      "presentation": {
        "reveal": "always",
        "panel": "dedicated"
      }
    }
  ]
}
```

**Usage**: `Cmd+Shift+P` → "Tasks: Run Task" → "CrumbBob Watch"

**Benefit**: Integrated into IDE workflow.

---

## Troubleshooting

### Watch Mode Not Starting

**Problem**: "watchdog package not found"

**Solution**:
```bash
pip install watchdog
```

### No Changes Detected

**Problem**: Files change but pack doesn't regenerate

**Solutions**:
1. Check file is in input directory: `ls -la crumdbob-input/`
2. Verify file extension is monitored (`.md`, `.patch`, `.txt`)
3. Check debounce period hasn't expired yet
4. Restart watch mode

### Too Many Regenerations

**Problem**: Pack regenerates constantly

**Solutions**:
1. Increase debounce period: `--debounce 5.0`
2. Check for auto-save in editor (disable or increase interval)
3. Exclude temporary files from input directory
4. Use `.gitignore` patterns

### High CPU Usage

**Problem**: Watch mode uses excessive CPU

**Solutions**:
1. Ensure output directory is not inside input directory
2. Check for infinite loops (output triggering input changes)
3. Reduce file system events (close unused editors)
4. Increase debounce period

### Pack Generation Fails

**Problem**: Regeneration fails with errors

**Solutions**:
1. Check error message in watch mode output
2. Validate input files manually: `crumdbob validate crumdbob-input/`
3. Ensure `bob-report.md` is valid
4. Check file permissions
5. Stop watch mode, fix issues, restart

---

## Best Practices

### 1. Dedicated Input Directory

```bash
# Good: Dedicated directory
crumdbob-input/
  bob-report.md
  git-diff.patch
  test-output.txt

# Bad: Mixed with source code
src/
  auth.py
  bob-report.md  # Don't do this
```

### 2. Separate Output Directory

```bash
# Good: Separate output
crumdbob watch ./input --out ./generated

# Bad: Output inside input
crumdbob watch ./input --out ./input/generated  # Infinite loop!
```

### 3. Reasonable Debounce Period

```bash
# Too short: Many regenerations
crumdbob watch ./input --out ./generated --debounce 0.5

# Good: Balanced
crumdbob watch ./input --out ./generated --debounce 2.0

# Too long: Slow feedback
crumdbob watch ./input --out ./generated --debounce 10.0
```

### 4. Update Artifacts Atomically

```bash
# Good: Write to temp, then move
pytest -v > /tmp/test-output.txt 2>&1
mv /tmp/test-output.txt crumdbob-input/test-output.txt

# Bad: Direct write (triggers multiple events)
pytest -v > crumdbob-input/test-output.txt 2>&1
```

### 5. Use Version Control

```bash
# Commit generated packs periodically
git add generated/
git commit -m "Update CrumbBob pack - auth feature progress"
```

---

## Performance Characteristics

### Resource Usage

**Idle State**:
- CPU: <0.1%
- Memory: ~10 MB
- Disk I/O: Minimal (file system events only)

**During Regeneration**:
- CPU: 20-40% (brief spike)
- Memory: ~50 MB
- Disk I/O: Moderate (reading/writing pack files)

**Typical Regeneration Time**:
- Small packs (<10 files): 2-3 seconds
- Medium packs (10-50 files): 3-5 seconds
- Large packs (50+ files): 5-10 seconds

### Scalability

Watch mode scales well:
- ✅ Handles hundreds of file changes per hour
- ✅ Minimal overhead when idle
- ✅ Efficient debouncing prevents storms
- ✅ Graceful degradation under load

---

## Comparison: Manual vs Watch Mode

### Manual Regeneration

```bash
# Every time you make changes:
vim bob-report.md
crumdbob pack crumdbob-input --out generated  # Manual!

vim src/auth.py
pytest > crumdbob-input/test-output.txt
crumdbob pack crumdbob-input --out generated  # Manual!

git diff > crumdbob-input/git-diff.patch
crumdbob pack crumdbob-input --out generated  # Manual!
```

**Pain Points**:
- Must remember to regenerate
- Context switching overhead
- Stale packs between regenerations
- Easy to forget

### Watch Mode

```bash
# Start once:
crumdbob watch ./crumdbob-input --out ./generated

# Then work normally:
vim bob-report.md          # Auto-regenerates
vim src/auth.py            # No action needed
pytest > crumdbob-input/test-output.txt  # Auto-regenerates
git diff > crumdbob-input/git-diff.patch # Auto-regenerates
```

**Benefits**:
- Zero manual regeneration
- Always-current packs
- No context switching
- Impossible to forget

---

## When to Use Watch Mode

### ✅ Use Watch Mode When:

1. **Active Development**: Making frequent changes
2. **Iterative Work**: Testing and refining
3. **Long Sessions**: Working for hours
4. **Team Collaboration**: Multiple people updating
5. **Live Demos**: Showing real-time updates

### ❌ Don't Use Watch Mode When:

1. **One-Time Generation**: Just need a single pack
2. **Batch Processing**: Generating many packs
3. **CI/CD Pipelines**: Use `auto-collect` instead
4. **Resource Constrained**: Limited CPU/memory
5. **Unstable Input**: Files change unpredictably

---

## Next Steps

- **Initial Setup**: Use [auto-collect workflow](01-auto-collect-workflow.md) to create input directory
- **PR Review**: Use [diff workflow](03-diff-workflow.md) to compare pack versions
- **Team Sharing**: Commit generated packs to version control

---

## Summary

Watch mode workflow:
1. ✅ Eliminates manual regeneration
2. ✅ Maintains always-current packs
3. ✅ Intelligent debouncing prevents storms
4. ✅ Minimal resource usage when idle
5. ✅ Integrates with any development workflow
6. ✅ Graceful shutdown and error handling

**Key Command**:
```bash
crumdbob watch ./crumdbob-input --out ./generated
```

Set it and forget it - your CrumbBob pack stays current automatically!