# Pack Diff Workflow

## Overview

The diff workflow enables you to compare two CrumbBob pack directories to understand what changed between versions. This is essential for PR reviews, regression detection, team collaboration, and tracking how understanding evolves over time.

**Key Benefit**: Clear visibility into pack changes without manual inspection.

---

## Prerequisites

- CrumbBob installed: `pip install -e .`
- Two pack directories to compare

---

## Basic Usage

### Step 1: Generate Two Packs

```bash
# Generate baseline pack
crumdbob pack ./input-v1 --out ./pack-v1

# Make changes, then generate new pack
crumdbob pack ./input-v2 --out ./pack-v2
```

### Step 2: Compare Packs

```bash
crumdbob diff ./pack-v1 ./pack-v2
```

### Step 3: Review Output

**If Identical**:
```
Pack Diff: ./pack-v1 -> ./pack-v2

✓ Packs are identical
```

**If Different**:
```
Pack Diff: ./pack-v1 -> ./pack-v2

✗ Packs differ

+ 1 file(s) added
~ 2 CRUMB file(s) modified

Proof Chain Changes:
  • Extracted counts changed:
    - files: 12 -> 15 (+3)
    - commands: 9 -> 11 (+2)
  • 1 file hash(es) changed
```

---

## Output Formats

### Summary Format (Default)

High-level overview with color-coded changes:

```bash
crumdbob diff ./pack-v1 ./pack-v2 --format=summary
```

**Output**:
```
Pack Diff: ./pack-v1 -> ./pack-v2

✗ Packs differ

+ 1 file(s) added
- 0 file(s) removed
~ 2 CRUMB file(s) modified
~ 0 other file(s) modified

Modified CRUMBs:
  • 02_next_task.crumb
  • 04_risk_register.crumb

Proof Chain Changes:
  • Extracted counts changed:
    - files: 12 -> 15 (+3)
    - commands: 9 -> 11 (+2)
    - risks: 6 -> 8 (+2)
  • Source hash changed
  • 1 file hash(es) changed
```

### Detailed Format

Section-by-section comparison with unified diffs:

```bash
crumdbob diff ./pack-v1 ./pack-v2 --format=detailed
```

**Output**:
```
Pack Diff: ./pack-v1 -> ./pack-v2

✗ Packs differ

=== Modified: 04_risk_register.crumb ===

Section: [risks]
--- pack-v1/04_risk_register.crumb
+++ pack-v2/04_risk_register.crumb
@@ -1,6 +1,8 @@
 - Authentication bypass in login endpoint
 - SQL injection in search query
 - Missing rate limiting on API endpoints
+- XSS vulnerability in user profile
+- Insecure password reset flow
 - Insufficient input validation
 - Hardcoded credentials in config
 - Missing CSRF protection

Section: [mitigation]
--- pack-v1/04_risk_register.crumb
+++ pack-v2/04_risk_register.crumb
@@ -1,3 +1,5 @@
 - Implement OAuth2 authentication
 - Use parameterized queries
 - Add rate limiting middleware
+- Sanitize all user inputs
+- Implement secure token-based reset
```

### JSON Format

Machine-readable output for CI/CD integration:

```bash
crumdbob diff ./pack-v1 ./pack-v2 --format=json
```

**Output**:
```json
{
  "pack1": "./pack-v1",
  "pack2": "./pack-v2",
  "identical": false,
  "summary": {
    "added_files": 1,
    "removed_files": 0,
    "modified_crumbs": 2,
    "modified_files": 0
  },
  "added_files": [
    "09_security_checklist.crumb"
  ],
  "removed_files": [],
  "modified_crumbs": [
    {
      "file": "02_next_task.crumb",
      "sections_changed": ["[goal]", "[context]"]
    },
    {
      "file": "04_risk_register.crumb",
      "sections_changed": ["[risks]", "[mitigation]"]
    }
  ],
  "proof_chain": {
    "count_changes": {
      "files": {"old": 12, "new": 15, "delta": 3},
      "commands": {"old": 9, "new": 11, "delta": 2},
      "risks": {"old": 6, "new": 8, "delta": 2}
    },
    "source_hash_changed": true,
    "file_hashes_changed": 1
  }
}
```

---

## Use Cases

### Use Case 1: PR Review

**Scenario**: Compare packs between main and feature branch to understand impact.

**Workflow**:

```bash
# On main branch
git checkout main
crumdbob auto-collect --out ./pack-main

# On feature branch
git checkout feature/auth
crumdbob auto-collect --out ./pack-feature

# Compare
crumdbob diff ./pack-main ./pack-feature --format=detailed > pr-diff.txt

# Add to PR description
cat pr-diff.txt
```

**What You Learn**:
- New risks introduced
- Tasks added/completed
- Files affected
- Commands changed
- Test coverage impact

**Example PR Comment**:
```markdown
## CrumbBob Pack Analysis

**Changes Detected**:
- ✅ 3 new files added to repo genome
- ⚠️ 2 new security risks identified
- ✅ 4 tasks completed
- 📝 Test coverage increased

**New Risks**:
- XSS vulnerability in user profile
- Insecure password reset flow

**Recommendation**: Address security risks before merge.

<details>
<summary>Full Diff</summary>

[paste detailed diff output]

</details>
```

### Use Case 2: Before/After Bob Session

**Scenario**: See what Bob discovered during a session.

**Workflow**:

```bash
# Before Bob session
crumdbob pack ./input --out ./pack-before

# Run Bob session
bob --chat-mode ask "Review authentication implementation"

# Export new report
bob export-report bob-report-new.md
cp bob-report-new.md input/bob-report.md

# After Bob session
crumdbob pack ./input --out ./pack-after

# Compare
crumdbob diff ./pack-before ./pack-after --format=summary
```

**What You Learn**:
- What Bob discovered
- New risks identified
- Tasks Bob recommends
- Files Bob analyzed
- Commands Bob suggests

### Use Case 3: Regression Detection

**Scenario**: Ensure pack quality doesn't degrade over time.

**Workflow**:

```bash
# Establish baseline
crumdbob pack ./input --out ./pack-baseline
git add pack-baseline/
git commit -m "Add baseline CrumbBob pack"

# Later, after changes
crumdbob pack ./input --out ./pack-current

# Check for regressions
crumdbob diff ./pack-baseline ./pack-current --format=json > diff.json

# Parse results
python3 << 'EOF'
import json
with open('diff.json') as f:
    diff = json.load(f)
    
if diff['proof_chain']['count_changes'].get('risks', {}).get('delta', 0) > 0:
    print("⚠️ New risks detected!")
    exit(1)
    
if diff['proof_chain']['count_changes'].get('tests', {}).get('delta', 0) < 0:
    print("⚠️ Test coverage decreased!")
    exit(1)
    
print("✓ No regressions detected")
EOF
```

**CI/CD Integration**:
```yaml
# .github/workflows/pack-regression.yml
- name: Check for pack regressions
  run: |
    crumdbob diff ./baseline-pack ./current-pack --format=json > diff.json
    python3 scripts/check-regression.py diff.json
```

### Use Case 4: Team Sync

**Scenario**: Understand what a teammate discovered in their Bob session.

**Workflow**:

```bash
# Get teammate's pack
git fetch origin feature/teammate-work
git checkout origin/feature/teammate-work -- generated/

# Compare with your pack
crumdbob diff ./my-pack ./generated --format=detailed

# Review differences
less diff-output.txt
```

**What You Learn**:
- Different perspectives on same codebase
- Risks they found that you missed
- Alternative approaches to tasks
- Complementary insights

### Use Case 5: Evolution Tracking

**Scenario**: Track how understanding of a project evolves over time.

**Workflow**:

```bash
# Create timestamped packs
crumdbob pack ./input --out ./packs/pack-2024-05-01
crumdbob pack ./input --out ./packs/pack-2024-05-08
crumdbob pack ./input --out ./packs/pack-2024-05-15

# Compare week-over-week
crumdbob diff ./packs/pack-2024-05-01 ./packs/pack-2024-05-08 > week1-diff.txt
crumdbob diff ./packs/pack-2024-05-08 ./packs/pack-2024-05-15 > week2-diff.txt

# Analyze trends
grep "risks:" week*.txt
grep "files:" week*.txt
```

**Insights**:
- Risk resolution rate
- Code churn patterns
- Knowledge accumulation
- Project complexity growth

---

## Advanced Usage

### Comparing Specific Sections

Use detailed format and grep for specific sections:

```bash
# Compare only risks
crumdbob diff ./pack-v1 ./pack-v2 --format=detailed | grep -A 20 "Section: \[risks\]"

# Compare only tasks
crumdbob diff ./pack-v1 ./pack-v2 --format=detailed | grep -A 20 "Section: \[tasks\]"

# Compare only commands
crumdbob diff ./pack-v1 ./pack-v2 --format=detailed | grep -A 20 "Section: \[commands\]"
```

### Filtering by Change Type

```bash
# Show only additions
crumdbob diff ./pack-v1 ./pack-v2 --format=detailed | grep "^+"

# Show only deletions
crumdbob diff ./pack-v1 ./pack-v2 --format=detailed | grep "^-"

# Count changes
crumdbob diff ./pack-v1 ./pack-v2 --format=detailed | grep -c "^[+-]"
```

### Automated Reporting

```bash
#!/bin/bash
# generate-diff-report.sh

PACK1=$1
PACK2=$2
OUTPUT=$3

echo "# CrumbBob Pack Comparison Report" > $OUTPUT
echo "" >> $OUTPUT
echo "Generated: $(date)" >> $OUTPUT
echo "" >> $OUTPUT

echo "## Summary" >> $OUTPUT
crumdbob diff $PACK1 $PACK2 --format=summary >> $OUTPUT

echo "" >> $OUTPUT
echo "## Detailed Changes" >> $OUTPUT
crumdbob diff $PACK1 $PACK2 --format=detailed >> $OUTPUT

echo "" >> $OUTPUT
echo "## JSON Data" >> $OUTPUT
echo '```json' >> $OUTPUT
crumdbob diff $PACK1 $PACK2 --format=json >> $OUTPUT
echo '```' >> $OUTPUT
```

Usage:
```bash
./generate-diff-report.sh ./pack-v1 ./pack-v2 report.md
```

---

## Exit Codes

The diff command uses exit codes for automation:

- **0**: Packs are identical
- **1**: Packs differ

**Example Usage**:

```bash
# Check if packs differ
if crumdbob diff ./pack-v1 ./pack-v2 --format=summary; then
    echo "No changes detected"
else
    echo "Changes detected - review required"
fi

# In CI/CD
crumdbob diff ./expected-pack ./generated-pack --format=json > diff.json
if [ $? -ne 0 ]; then
    echo "Pack regression detected!"
    cat diff.json
    exit 1
fi
```

---

## Interpreting Diff Output

### File-Level Changes

**Added Files** (`+`):
- New CRUMBs generated
- New artifacts included
- Expanded pack scope

**Removed Files** (`-`):
- CRUMBs no longer generated
- Artifacts removed
- Reduced pack scope

**Modified Files** (`~`):
- Content changed
- Sections updated
- Metadata revised

### CRUMB-Level Changes

**Section Added**:
```
Section: [new_section]
+++ pack-v2/04_risk_register.crumb
+ [new_section]
+ New content here
```

**Section Removed**:
```
Section: [old_section]
--- pack-v1/04_risk_register.crumb
- [old_section]
- Old content here
```

**Section Modified**:
```
Section: [risks]
--- pack-v1/04_risk_register.crumb
+++ pack-v2/04_risk_register.crumb
@@ -1,3 +1,4 @@
 - Existing risk 1
 - Existing risk 2
+- New risk 3
```

### Proof Chain Changes

**Count Changes**:
- `files: 12 -> 15 (+3)` - 3 new files discovered
- `commands: 9 -> 11 (+2)` - 2 new commands found
- `risks: 6 -> 8 (+2)` - 2 new risks identified
- `tests: 15 -> 18 (+3)` - 3 new tests added

**Hash Changes**:
- `Source hash changed` - Input report modified
- `1 file hash(es) changed` - Generated file content changed

---

## Best Practices

### 1. Compare Related Packs

```bash
# Good: Same project, different versions
crumdbob diff ./pack-v1.0 ./pack-v1.1

# Good: Same branch, before/after changes
crumdbob diff ./pack-before ./pack-after

# Bad: Unrelated projects
crumdbob diff ./project-a-pack ./project-b-pack  # Not meaningful
```

### 2. Use Appropriate Format

```bash
# Quick check: Use summary
crumdbob diff ./pack-v1 ./pack-v2 --format=summary

# Detailed review: Use detailed
crumdbob diff ./pack-v1 ./pack-v2 --format=detailed

# Automation: Use json
crumdbob diff ./pack-v1 ./pack-v2 --format=json
```

### 3. Save Diff Output

```bash
# Save for later review
crumdbob diff ./pack-v1 ./pack-v2 --format=detailed > diff-$(date +%Y%m%d).txt

# Add to version control
git add diff-*.txt
git commit -m "Add pack diff analysis"
```

### 4. Combine with Other Tools

```bash
# Diff + validation
crumdbob diff ./pack-v1 ./pack-v2 --format=summary && \
  crumdbob validate ./pack-v2

# Diff + doctor
crumdbob diff ./pack-v1 ./pack-v2 --format=summary && \
  crumdbob doctor ./pack-v2

# Diff + replay
crumdbob diff ./pack-v1 ./pack-v2 --format=summary && \
  crumdbob replay ./pack-v2
```

### 5. Regular Comparisons

```bash
# Weekly comparison script
#!/bin/bash
WEEK=$(date +%Y-W%U)
crumdbob pack ./input --out ./packs/pack-$WEEK

if [ -d ./packs/pack-last ]; then
    crumdbob diff ./packs/pack-last ./packs/pack-$WEEK --format=detailed > ./diffs/diff-$WEEK.txt
fi

ln -sf pack-$WEEK ./packs/pack-last
```

---

## Troubleshooting

### Diff Shows No Changes But Files Differ

**Problem**: Diff reports identical but files have different timestamps.

**Solution**: Diff compares content, not metadata. This is expected behavior.

### Cannot Compare Packs

**Problem**: "Error: Pack directory not found"

**Solution**:
```bash
# Verify paths exist
ls -la ./pack-v1
ls -la ./pack-v2

# Use absolute paths if needed
crumdbob diff /full/path/to/pack-v1 /full/path/to/pack-v2
```

### Diff Output Too Large

**Problem**: Detailed diff is overwhelming

**Solutions**:
```bash
# Use summary format
crumdbob diff ./pack-v1 ./pack-v2 --format=summary

# Filter specific sections
crumdbob diff ./pack-v1 ./pack-v2 --format=detailed | grep -A 10 "Section: \[risks\]"

# Save to file and review in editor
crumdbob diff ./pack-v1 ./pack-v2 --format=detailed > diff.txt
vim diff.txt
```

### JSON Parsing Errors

**Problem**: Cannot parse JSON output

**Solution**:
```bash
# Validate JSON
crumdbob diff ./pack-v1 ./pack-v2 --format=json | python3 -m json.tool

# Pretty print
crumdbob diff ./pack-v1 ./pack-v2 --format=json | jq '.'
```

---

## Integration Examples

### GitHub Actions

```yaml
name: Pack Diff on PR
on: pull_request

jobs:
  diff-packs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Generate baseline pack
        run: |
          git checkout ${{ github.base_ref }}
          crumdbob auto-collect --no-interactive --out ./pack-base
      
      - name: Generate PR pack
        run: |
          git checkout ${{ github.head_ref }}
          crumdbob auto-collect --no-interactive --out ./pack-pr
      
      - name: Compare packs
        run: |
          crumdbob diff ./pack-base ./pack-pr --format=detailed > diff.txt
          
      - name: Comment on PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const diff = fs.readFileSync('diff.txt', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## CrumbBob Pack Diff\n\n\`\`\`\n${diff}\n\`\`\``
            });
```

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

if [ -d "./pack-baseline" ] && [ -d "./generated" ]; then
    echo "Checking for pack regressions..."
    
    if ! crumdbob diff ./pack-baseline ./generated --format=summary; then
        echo ""
        echo "⚠️ Pack changes detected. Review before committing."
        echo "Run: crumdbob diff ./pack-baseline ./generated --format=detailed"
        echo ""
        read -p "Continue with commit? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi
```

### Makefile Target

```makefile
.PHONY: pack-diff
pack-diff:
	@echo "Comparing packs..."
	@crumdbob diff ./pack-baseline ./generated --format=summary
	@echo ""
	@echo "For detailed diff, run: make pack-diff-detailed"

.PHONY: pack-diff-detailed
pack-diff-detailed:
	@crumdbob diff ./pack-baseline ./generated --format=detailed | less

.PHONY: pack-diff-json
pack-diff-json:
	@crumdbob diff ./pack-baseline ./generated --format=json | jq '.'
```

---

## Summary

Pack diff workflow:
1. ✅ Compare two pack directories
2. ✅ Multiple output formats (summary, detailed, json)
3. ✅ Clear visualization of changes
4. ✅ Exit codes for automation
5. ✅ Integrates with CI/CD pipelines
6. ✅ Essential for PR reviews and regression detection

**Key Commands**:
```bash
# Quick comparison
crumdbob diff ./pack-v1 ./pack-v2

# Detailed analysis
crumdbob diff ./pack-v1 ./pack-v2 --format=detailed

# Automation
crumdbob diff ./pack-v1 ./pack-v2 --format=json
```

Use diff workflow to maintain pack quality, track evolution, and collaborate effectively!