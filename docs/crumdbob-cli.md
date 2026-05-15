# CrumbBob CLI

CrumbBob turns an exported IBM Bob report into a replayable memory pack.

## Quickstart

```bash
pip install -e .
crumdbob pack examples/compliance-ai --out examples/compliance-ai/generated
crumdbob validate examples/compliance-ai/generated
crumdbob doctor examples/compliance-ai/generated
crumdbob replay examples/compliance-ai/generated
```

## Commands

### Core Pack Generation

#### `crumdbob pack <input-dir> --out <output-dir>`

Generates a full pack from a directory containing:

- `bob-report.md` required
- `git-diff.patch` optional
- `test-output.txt` optional
- `repo-notes.md` optional

Output files:

- `00_repo_genome.crumb`
- `01_session_flight_recorder.crumb`
- `02_next_task.crumb`
- `03_test_plan.crumb`
- `04_risk_register.crumb`
- `05_agent_passport.crumb`
- `06_replay_prompt.md`
- `07_pr_summary.md`
- `08_proof_chain.json`

#### `crumdbob import <bob-report.md> --out <output-dir>`

Compatibility command for generating a pack from a single Bob report file.

### Quick Win Commands

#### `crumdbob auto-collect --out <output-dir>`

**Auto-artifact collection** - Eliminates manual artifact gathering.

Automatically:
1. Scans the current Git repository for relevant artifacts
2. Detects and collects:
   - Git diffs (staged, unstaged, or combined)
   - Recent test output files
   - CI logs
3. Prompts user to select which artifacts to include (interactive mode)
4. Creates the input directory structure
5. Generates the pack in one command

**Options:**
- `--report <path>` - Path to existing bob-report.md (optional)
- `--input-dir <path>` - Input directory to create (default: ./crumdbob-input)
- `--out <path>` - Output directory for generated pack (required)
- `--no-interactive` - Skip interactive artifact selection, collect all

**Example:**
```bash
# Interactive mode (prompts for artifact selection)
crumdbob auto-collect --out ./generated

# With existing bob-report.md
crumdbob auto-collect --report ./bob-report.md --out ./generated

# Non-interactive (collect all artifacts)
crumdbob auto-collect --no-interactive --out ./generated
```

#### `crumdbob watch <input-dir> --out <output-dir>`

**Watch mode** - Eliminates stale packs during active development.

Monitors the input directory for changes and automatically regenerates the pack when:
- `bob-report.md` is modified
- Artifact files are added, modified, or deleted (git-diff.patch, test-output.txt, etc.)

**Features:**
- Live status indicator showing detected changes
- Debounces rapid changes (waits 2 seconds after last change by default)
- Clear feedback on what triggered regeneration
- Graceful shutdown with Ctrl+C

**Options:**
- `<input-dir>` - Directory to watch (required)
- `--out <path>` - Output directory for generated pack (required)
- `--debounce <seconds>` - Seconds to wait after last change (default: 2.0)

**Example:**
```bash
# Basic watch mode
crumdbob watch ./crumdbob-input --out ./generated

# Custom debounce period
crumdbob watch ./crumdbob-input --out ./generated --debounce 5.0
```

**Requirements:**
Watch mode requires the `watchdog` package:
```bash
pip install watchdog
```

#### `crumdbob diff <pack-dir-1> <pack-dir-2>`

**Pack comparison** - Compare two pack directories to understand what changed.

Compares two pack directories and shows differences in:
- Extracted counts (files, commands, risks, tests, next_steps)
- CRUMB content changes (added/removed/modified sections)
- Proof chain differences (source hash changes, new artifacts)
- File additions and removals

**Output Formats:**
- `--format=summary` (default) - High-level overview with color-coded changes
- `--format=detailed` - Section-by-section comparison with unified diffs
- `--format=json` - Machine-readable output for CI/CD integration

**Options:**
- `<pack-dir-1>` - First pack directory (baseline)
- `<pack-dir-2>` - Second pack directory (comparison target)
- `--format <type>` - Output format: summary, detailed, or json (default: summary)
- `--no-color` - Disable colored output (useful for CI logs)

**Exit Codes:**
- `0` - Packs are identical
- `1` - Packs differ

**Use Cases:**

1. **Before/After Bob Session**: See what changed after running Bob again
   ```bash
   crumdbob diff ./pack-before ./pack-after
   ```

2. **PR Review**: Compare packs between branches to understand impact
   ```bash
   git checkout main
   crumdbob pack ./input --out ./pack-main
   git checkout feature-branch
   crumdbob pack ./input --out ./pack-feature
   crumdbob diff ./pack-main ./pack-feature --format=detailed
   ```

3. **Regression Detection**: Ensure pack quality doesn't degrade
   ```bash
   # In CI pipeline
   crumdbob diff ./expected-pack ./generated-pack --format=json > diff.json
   if [ $? -ne 0 ]; then
     echo "Pack regression detected!"
     exit 1
   fi
   ```

4. **Team Sync**: Quickly understand what another developer's Bob session discovered
   ```bash
   crumdbob diff ./my-pack ./teammate-pack --format=summary
   ```

**Example Output:**

Summary format:
```
Pack Diff: ./pack1 -> ./pack2

✗ Packs differ

+ 1 file(s) added
~ 2 CRUMB file(s) modified

Proof Chain Changes:
  • Extracted counts changed:
    - files: 12 -> 15 (+3)
    - commands: 9 -> 11 (+2)
  • 1 file hash(es) changed
```

Detailed format shows section-by-section diffs with unified diff output for modified CRUMB sections.

JSON format provides structured data for programmatic consumption:
```json
{
  "pack1": "./pack1",
  "pack2": "./pack2",
  "identical": false,
  "summary": {
    "added_files": 1,
    "removed_files": 0,
    "modified_crumbs": 2,
    "modified_files": 0
  },
  "proof_chain": {
    "count_changes": {
      "files": {"old": 12, "new": 15, "delta": 3}
    }
  }
}
```

### Validation & Inspection

#### `crumdbob validate <pack-dir-or-file>`

Validates CrumbBob's CRUMB v1.4 subset:

- required headers: `v=1.4`, `kind=`, `title=`, `source=`
- required sections by kind
- `[checks]` lines in `name :: status` format
- `[handoff]` and `[workflow]` dependency references

#### `crumdbob doctor <pack-dir>`

Prints a judge-friendly health report covering file presence, CRUMB validation, replay prompt, PR summary, proof chain, and source report availability.

It also recomputes proof-chain hashes and exits non-zero when generated files no longer match `08_proof_chain.json`.

#### `crumdbob graph <pack-dir>`

Prints refs, handoff, and workflow edges as a simple dependency graph.

### Output Commands

#### `crumdbob replay <pack-dir>`

Prints the replay prompt for the next Bob, Claude, Cursor, Codex, or agent session.

#### `crumdbob pr <pack-dir>`

Prints the generated PR summary.

#### `crumdbob init-bob-skill --out skills/crumdbob/SKILL.md`

Writes a small skill file that teaches another agent how to use CrumbBob packs.

### Multi-Session Memory Commands

CrumbBob includes a persistent memory database for tracking sessions across time. See [Multi-Session Memory Getting Started](./multi-session-memory-getting-started.md) for detailed usage.

#### `crumdbob init-db [--path <db-path>]`

Initialize the memory database with schema and indexes.

```bash
# Use default location (~/.crumdbob/memory.db)
crumdbob init-db

# Use custom location
crumdbob init-db --path ./project-memory.db
```

#### `crumdbob record <pack-dir> [--db <db-path>] [--session-name <name>]`

Record a pack directory to the memory database.

```bash
# Record with auto-detected Git context
crumdbob record ./pack-dir

# Record with custom session name
crumdbob record ./pack-dir --session-name "API v2 implementation"

# Use custom database
crumdbob record ./pack-dir --db ./project-memory.db
```

Automatically extracts:
- Files, commands, risks, and tasks from the pack
- Git context (branch, commit, author) if available
- Proof chain hash for verification
- Timestamps for historical tracking

#### `crumdbob list-sessions [--db <db-path>] [--format json|table]`

List all recorded sessions with optional filters.

```bash
# Table format (default)
crumdbob list-sessions

# JSON format for programmatic access
crumdbob list-sessions --format json

# Filter by Git branch
crumdbob list-sessions --branch main

# Filter by author
crumdbob list-sessions --author "Alice"

# Limit results
crumdbob list-sessions --limit 20
```

Output includes:
- Session ID, timestamp, name
- Git context (branch, commit, author)
- Entity counts (files, commands, risks, tasks)

#### `crumdbob show-session <session-id> [--db <db-path>]`

Show detailed information about a specific session.

```bash
crumdbob show-session 1
```

Displays:
- Complete session metadata
- Git context
- Source report path and pack directory
- All files (first 20)
- All commands (first 10)
- All risks with status (first 10)
- All tasks with status (first 10)

#### `crumdbob migrate-to-db <pack-dirs...> [--db <db-path>]`

Migrate existing file-based packs to the memory database.

```bash
# Migrate single pack
crumdbob migrate-to-db ./pack-dir

# Migrate multiple packs
crumdbob migrate-to-db ./pack1 ./pack2 ./pack3

# Batch migration with custom database
crumdbob migrate-to-db ./packs/* --db ./team-memory.db
```

Shows progress and summary:
- Success count
- Error count
- Session IDs for successful migrations

#### `crumdbob config <get|set|list|reset>`

Manage CrumbBob configuration.

```bash
# List all configuration
crumdbob config list

# Get a specific value
crumdbob config get database_path

# Set a value
crumdbob config set auto_record true

# Reset to defaults
crumdbob config reset
```

Available settings:
- `database_path`: Database location (default: `~/.crumdbob/memory.db`)
- `auto_record`: Auto-record packs (default: `false`)
- `git_integration`: Enable Git context extraction (default: `true`)
- `team_mode`: Enable team collaboration features (default: `false`)

### Auto-Recording Integration

The `pack` and `auto-collect` commands support automatic recording with the `--record` flag:

```bash
# Generate and record in one command
crumdbob pack ./input --out ./pack --record

# Auto-collect and record
crumdbob auto-collect --out ./pack --record

# Or enable globally
crumdbob config set auto_record true
crumdbob pack ./input --out ./pack  # Automatically records
```
