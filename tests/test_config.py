"""Tests for configuration management."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from crumdbob import config


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """Create a temporary config directory."""
    config_dir = tmp_path / ".crumdbob"
    config_dir.mkdir()

    # Mock get_config_path to use temp directory
    def mock_get_config_path():
        return config_dir / "config.json"

    monkeypatch.setattr(config, "get_config_path", mock_get_config_path)
    return config_dir


class TestConfigPath:
    """Tests for configuration path functions."""

    def test_get_config_path_returns_path(self):
        """Test that get_config_path returns a Path object."""
        path = config.get_config_path()
        assert isinstance(path, Path)
        assert path.name == "config.json"
        assert ".crumdbob" in str(path)


class TestLoadConfig:
    """Tests for loading configuration."""

    def test_load_config_missing_file_returns_defaults(self, temp_config_dir):
        """Test loading config when file doesn't exist returns defaults."""
        cfg = config.load_config()
        assert cfg == config.DEFAULT_CONFIG
        assert cfg["database_path"] == "~/.crumdbob/memory.db"
        assert cfg["auto_record"] is False
        assert cfg["git_integration"] is True
        assert cfg["team_mode"] is False

    def test_load_config_valid_file(self, temp_config_dir):
        """Test loading valid config file."""
        config_path = temp_config_dir / "config.json"
        test_config = {
            "database_path": "/custom/path/db.sqlite",
            "auto_record": True,
            "git_integration": False,
            "team_mode": True,
        }
        config_path.write_text(json.dumps(test_config))

        cfg = config.load_config()
        assert cfg["database_path"] == "/custom/path/db.sqlite"
        assert cfg["auto_record"] is True
        assert cfg["git_integration"] is False
        assert cfg["team_mode"] is True

    def test_load_config_partial_file_merges_defaults(self, temp_config_dir):
        """Test that partial config merges with defaults."""
        config_path = temp_config_dir / "config.json"
        partial_config = {"auto_record": True}
        config_path.write_text(json.dumps(partial_config))

        cfg = config.load_config()
        assert cfg["auto_record"] is True
        assert cfg["database_path"] == "~/.crumdbob/memory.db"  # from defaults
        assert cfg["git_integration"] is True  # from defaults
        assert cfg["team_mode"] is False  # from defaults

    def test_load_config_malformed_json_returns_defaults(self, temp_config_dir):
        """Test that malformed JSON returns defaults."""
        config_path = temp_config_dir / "config.json"
        config_path.write_text("{invalid json")

        cfg = config.load_config()
        assert cfg == config.DEFAULT_CONFIG

    def test_load_config_io_error_returns_defaults(self, temp_config_dir):
        """Test that I/O errors return defaults."""
        config_path = temp_config_dir / "config.json"
        config_path.write_text("{}")
        config_path.chmod(0o000)  # Make unreadable

        try:
            cfg = config.load_config()
            assert cfg == config.DEFAULT_CONFIG
        finally:
            config_path.chmod(0o644)  # Restore permissions


class TestSaveConfig:
    """Tests for saving configuration."""

    def test_save_config_creates_directory(self, temp_config_dir):
        """Test that save_config creates parent directory."""
        config_path = temp_config_dir / "config.json"
        if config_path.exists():
            config_path.unlink()
        temp_config_dir.rmdir()

        test_config = {"database_path": "/test/path"}
        config.save_config(test_config)

        assert temp_config_dir.exists()
        assert config_path.exists()

    def test_save_config_writes_json(self, temp_config_dir):
        """Test that save_config writes valid JSON."""
        test_config = {
            "database_path": "/test/path",
            "auto_record": True,
            "git_integration": False,
            "team_mode": True,
        }
        config.save_config(test_config)

        config_path = temp_config_dir / "config.json"
        saved_data = json.loads(config_path.read_text())
        assert saved_data == test_config

    def test_save_config_formatted_json(self, temp_config_dir):
        """Test that saved JSON is formatted with indentation."""
        test_config = {"database_path": "/test/path"}
        config.save_config(test_config)

        config_path = temp_config_dir / "config.json"
        content = config_path.read_text()
        assert "\n" in content  # Multi-line
        assert "  " in content  # Indented


class TestGetConfigValue:
    """Tests for getting individual config values."""

    def test_get_config_value_existing_key(self, temp_config_dir):
        """Test getting an existing config value."""
        config_path = temp_config_dir / "config.json"
        config_path.write_text(json.dumps({"auto_record": True}))

        value = config.get_config_value("auto_record")
        assert value is True

    def test_get_config_value_missing_key_returns_none(self, temp_config_dir):
        """Test getting a non-existent key returns None."""
        value = config.get_config_value("nonexistent_key")
        assert value is None

    def test_get_config_value_default_key(self, temp_config_dir):
        """Test getting a default key when no config file exists."""
        value = config.get_config_value("database_path")
        assert value == "~/.crumdbob/memory.db"


class TestSetConfigValue:
    """Tests for setting individual config values."""

    def test_set_config_value_valid_key(self, temp_config_dir):
        """Test setting a valid config value."""
        config.set_config_value("auto_record", True)

        cfg = config.load_config()
        assert cfg["auto_record"] is True

    def test_set_config_value_invalid_key_raises(self, temp_config_dir):
        """Test that setting an invalid key raises ValueError."""
        with pytest.raises(ValueError, match="Unknown configuration key"):
            config.set_config_value("invalid_key", "value")

    def test_set_config_value_bool_type_coercion(self, temp_config_dir):
        """Test boolean type coercion from strings."""
        # Test truthy strings
        for truthy in ["true", "True", "TRUE", "yes", "YES", "1", "on", "ON"]:
            config.set_config_value("auto_record", truthy)
            assert config.get_config_value("auto_record") is True

        # Test falsy strings
        for falsy in ["false", "False", "FALSE", "no", "NO", "0", "off", "OFF"]:
            config.set_config_value("auto_record", falsy)
            assert config.get_config_value("auto_record") is False

    def test_set_config_value_bool_from_int(self, temp_config_dir):
        """Test boolean coercion from integers."""
        config.set_config_value("auto_record", 1)
        assert config.get_config_value("auto_record") is True

        config.set_config_value("auto_record", 0)
        assert config.get_config_value("auto_record") is False

    def test_set_config_value_string_coercion(self, temp_config_dir):
        """Test string type coercion."""
        config.set_config_value("database_path", 12345)
        value = config.get_config_value("database_path")
        assert value == "12345"
        assert isinstance(value, str)

    def test_set_config_value_preserves_other_values(self, temp_config_dir):
        """Test that setting one value doesn't affect others."""
        config.set_config_value("auto_record", True)
        config.set_config_value("team_mode", True)

        cfg = config.load_config()
        assert cfg["auto_record"] is True
        assert cfg["team_mode"] is True
        assert cfg["git_integration"] is True  # unchanged default


class TestGetDatabasePath:
    """Tests for database path retrieval."""

    def test_get_database_path_expands_tilde(self, temp_config_dir):
        """Test that ~ is expanded in database path."""
        config.set_config_value("database_path", "~/custom/db.sqlite")

        db_path = config.get_database_path()
        assert isinstance(db_path, Path)
        assert "~" not in str(db_path)
        assert str(db_path).startswith(str(Path.home()))

    def test_get_database_path_absolute_path(self, temp_config_dir):
        """Test absolute path is returned as-is."""
        config.set_config_value("database_path", "/absolute/path/db.sqlite")

        db_path = config.get_database_path()
        assert str(db_path) == "/absolute/path/db.sqlite"

    def test_get_database_path_default(self, temp_config_dir):
        """Test default database path."""
        db_path = config.get_database_path()
        assert isinstance(db_path, Path)
        assert db_path.name == "memory.db"
        assert ".crumdbob" in str(db_path)


class TestBooleanHelpers:
    """Tests for boolean helper functions."""

    def test_should_auto_record_default(self, temp_config_dir):
        """Test default auto_record is False."""
        assert config.should_auto_record() is False

    def test_should_auto_record_enabled(self, temp_config_dir):
        """Test auto_record when enabled."""
        config.set_config_value("auto_record", True)
        assert config.should_auto_record() is True

    def test_is_git_integration_enabled_default(self, temp_config_dir):
        """Test default git_integration is True."""
        assert config.is_git_integration_enabled() is True

    def test_is_git_integration_enabled_disabled(self, temp_config_dir):
        """Test git_integration when disabled."""
        config.set_config_value("git_integration", False)
        assert config.is_git_integration_enabled() is False

    def test_is_team_mode_enabled_default(self, temp_config_dir):
        """Test default team_mode is False."""
        assert config.is_team_mode_enabled() is False

    def test_is_team_mode_enabled_enabled(self, temp_config_dir):
        """Test team_mode when enabled."""
        config.set_config_value("team_mode", True)
        assert config.is_team_mode_enabled() is True


class TestConfigIntegration:
    """Integration tests for config workflow."""

    def test_full_config_workflow(self, temp_config_dir):
        """Test complete config workflow: load, modify, save, reload."""
        # Start with defaults
        cfg1 = config.load_config()
        assert cfg1["auto_record"] is False

        # Modify and save
        config.set_config_value("auto_record", True)
        config.set_config_value("database_path", "/custom/db.sqlite")

        # Reload and verify
        cfg2 = config.load_config()
        assert cfg2["auto_record"] is True
        assert cfg2["database_path"] == "/custom/db.sqlite"
        assert cfg2["git_integration"] is True  # unchanged

    def test_config_persists_across_loads(self, temp_config_dir):
        """Test that config persists across multiple load calls."""
        config.set_config_value("team_mode", True)

        # Load multiple times
        for _ in range(3):
            cfg = config.load_config()
            assert cfg["team_mode"] is True


# Made with Bob
