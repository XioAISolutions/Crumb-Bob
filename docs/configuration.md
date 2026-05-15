# Configuration Management

CrumbBob uses a JSON configuration file to manage persistent settings across sessions.

## Configuration File Location

```
~/.crumdbob/config.json
```

The configuration file is automatically created when you first set a value.

## Default Configuration

```json
{
  "database_path": "~/.crumdbob/memory.db",
  "auto_record": false,
  "git_integration": true,
  "team_mode": false
}
```

## Configuration Keys

### `database_path` (string)

Path to the SQLite database file for multi-session memory.

**Default**: `~/.crumdbob/memory.db`

**Example**:
```bash
crumdbob config set database_path ~/custom/path/memory.db
```

The `~` character is automatically expanded to your home directory.

### `auto_record` (boolean)

Automatically record packs to the database when generated.

**Default**: `false`

**Example**:
```bash
crumdbob config set auto_record true
```

When enabled, every `crumdbob pack` command automatically records the session to the database.

### `git_integration` (boolean)

Enable Git context extraction (branch, commit, author) when recording sessions.

**Default**: `true`

**Example**:
```bash
crumdbob config set git_integration false
```

When disabled, sessions are recorded without Git metadata.

### `team_mode` (boolean)

Enable team collaboration features (future feature).

**Default**: `false`

**Example**:
```bash
crumdbob config set team_mode true
```

## CLI Commands

### View All Configuration

```bash
crumdbob config list
```

Output:
```
database_path: ~/.crumdbob/memory.db
auto_record: false
git_integration: true
team_mode: false
```

### Get Single Value

```bash
crumdbob config get database_path
```

Output:
```
~/.crumdbob/memory.db
```

### Set Value

```bash
crumdbob config set <key> <value>
```

Examples:
```bash
crumdbob config set auto_record true
crumdbob config set database_path /custom/path/db.sqlite
crumdbob config set git_integration false
```

### Reset to Defaults

```bash
crumdbob config reset
```

This removes the configuration file and restores all default values.

## Type Coercion

CrumbBob automatically converts values to the correct type:

### Boolean Values

The following strings are converted to `true`:
- `true`, `True`, `TRUE`
- `yes`, `Yes`, `YES`
- `1`
- `on`, `On`, `ON`

All other strings are converted to `false`.

**Examples**:
```bash
crumdbob config set auto_record yes    # → true
crumdbob config set auto_record 1      # → true
crumdbob config set auto_record false  # → false
crumdbob config set auto_record 0      # → false
```

### String Values

Non-string values are automatically converted to strings:

```bash
crumdbob config set database_path 12345  # → "12345"
```

## Programmatic Access

### Python API

```python
from crumdbob import config

# Load configuration
cfg = config.load_config()
print(cfg["auto_record"])

# Get single value
db_path = config.get_config_value("database_path")

# Set value
config.set_config_value("auto_record", True)

# Get database path (with ~ expansion)
db_path = config.get_database_path()

# Boolean helpers
if config.should_auto_record():
    print("Auto-recording enabled")

if config.is_git_integration_enabled():
    print("Git integration enabled")

if config.is_team_mode_enabled():
    print("Team mode enabled")
```

## Configuration Workflow Examples

### Enable Auto-Recording

```bash
# Enable auto-recording
crumdbob config set auto_record true

# Now every pack is automatically recorded
crumdbob pack examples/compliance-ai --out ./generated
# → Pack generated AND recorded to database

# View recorded sessions
crumdbob list-sessions
```

### Custom Database Location

```bash
# Set custom database path
crumdbob config set database_path ~/projects/crumdbob-data/memory.db

# Initialize database at custom location
crumdbob init-db

# All subsequent commands use custom location
crumdbob record ./generated
crumdbob list-sessions
```

### Team Collaboration Setup

```bash
# Enable team mode
crumdbob config set team_mode true

# Use shared database on network drive
crumdbob config set database_path /mnt/shared/team-memory.db

# Initialize shared database
crumdbob init-db

# All team members can now query shared history
crumdbob query natural "Show me all authentication risks"
```

### Disable Git Integration

```bash
# Disable Git integration (for non-Git projects)
crumdbob config set git_integration false

# Sessions recorded without Git metadata
crumdbob record ./generated
```

## Configuration File Format

The configuration file is stored as formatted JSON:

```json
{
  "database_path": "~/.crumdbob/memory.db",
  "auto_record": true,
  "git_integration": true,
  "team_mode": false
}
```

You can manually edit this file, but using `crumdbob config set` is recommended for:
- Type validation
- Key validation
- Automatic formatting

## Troubleshooting

### Configuration Not Persisting

**Problem**: Changes don't persist across commands.

**Solution**: Check file permissions on `~/.crumdbob/config.json`:

```bash
ls -la ~/.crumdbob/config.json
chmod 644 ~/.crumdbob/config.json
```

### Invalid Configuration Key

**Problem**: `ValueError: Unknown configuration key: xyz`

**Solution**: Only these keys are valid:
- `database_path`
- `auto_record`
- `git_integration`
- `team_mode`

Check for typos in the key name.

### Malformed JSON

**Problem**: Configuration file is corrupted.

**Solution**: Reset to defaults:

```bash
crumdbob config reset
```

Or manually delete the file:

```bash
rm ~/.crumdbob/config.json
```

### Database Path Not Expanding

**Problem**: `~` in path not expanding to home directory.

**Solution**: Use `config.get_database_path()` in Python or the CLI commands, which automatically expand `~`.

## Best Practices

1. **Use Auto-Recording for Active Projects**
   ```bash
   crumdbob config set auto_record true
   ```
   This builds your memory database automatically without extra commands.

2. **Keep Git Integration Enabled**
   ```bash
   crumdbob config set git_integration true
   ```
   Git context makes pattern detection and insights more valuable.

3. **Use Shared Database for Teams**
   ```bash
   crumdbob config set database_path /shared/team-memory.db
   crumdbob config set team_mode true
   ```
   Enables collective learning across the team.

4. **Back Up Your Configuration**
   ```bash
   cp ~/.crumdbob/config.json ~/.crumdbob/config.json.backup
   ```
   Especially important before major changes.

5. **Document Team Configuration**
   
   Create a `CRUMDBOB_SETUP.md` in your project:
   ```markdown
   # CrumbBob Team Setup
   
   ```bash
   crumdbob config set database_path /mnt/shared/project-memory.db
   crumdbob config set auto_record true
   crumdbob config set team_mode true
   ```
   ```

## See Also

- [Multi-Session Memory Design](multi-session-memory-design.md)
- [Intelligent Queries](intelligent-queries.md)
- [Pattern Detection](pattern-detection.md)
- [CLI Reference](crumdbob-cli.md)