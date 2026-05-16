"""Configuration management for CrumbBob."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = {
    "database_path": "~/.crumdbob/memory.db",
    "auto_record": False,
    "git_integration": True,
    "team_mode": False,
}


def get_config_path() -> Path:
    """Get the configuration file path."""
    return Path.home() / ".crumdbob" / "config.json"


def load_config() -> dict[str, Any]:
    """Load configuration from file or return defaults."""
    config_path = get_config_path()

    if not config_path.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with config_path.open(encoding="utf-8") as f:
            config = json.load(f)

        # Merge with defaults to ensure all keys exist
        merged = DEFAULT_CONFIG.copy()
        merged.update(config)
        return merged
    except (json.JSONDecodeError, OSError):
        return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_config_value(key: str) -> Any:
    """Get a single configuration value."""
    config = load_config()
    return config.get(key)


def set_config_value(key: str, value: Any) -> None:
    """Set a single configuration value."""
    config = load_config()

    # Validate key
    if key not in DEFAULT_CONFIG:
        raise ValueError(f"Unknown configuration key: {key}")

    # Type validation
    expected_type = type(DEFAULT_CONFIG[key])
    if not isinstance(value, expected_type):
        # Try to convert
        if expected_type is bool:
            if isinstance(value, str):
                value = value.lower() in ("true", "yes", "1", "on")
            else:
                value = bool(value)
        elif expected_type is str:
            value = str(value)

    config[key] = value
    save_config(config)


def get_database_path() -> Path:
    """Get the configured database path, expanding ~ if needed."""
    db_path = get_config_value("database_path")
    if isinstance(db_path, str):
        return Path(db_path).expanduser()
    return Path(db_path)


def should_auto_record() -> bool:
    """Check if auto-recording is enabled."""
    return bool(get_config_value("auto_record"))


def is_git_integration_enabled() -> bool:
    """Check if Git integration is enabled."""
    return bool(get_config_value("git_integration"))


def is_team_mode_enabled() -> bool:
    """Check if team mode is enabled."""
    return bool(get_config_value("team_mode"))


# Made with Bob
