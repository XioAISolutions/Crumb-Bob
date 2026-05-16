"""Tests for LLM integration module."""

from __future__ import annotations

import os
from unittest.mock import Mock, patch

import pytest

from crumdbob.llm import (
    LLMAnalyzer,
    LLMConfig,
    LLMResponse,
    create_llm_analyzer,
    get_llm_config,
    is_llm_available,
)
from crumdbob.memory import MemoryDatabase


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary test database."""
    db_path = tmp_path / "test.db"
    db = MemoryDatabase(db_path)
    db.init_database()
    yield db
    db.close()


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Test analysis response"))]
    mock_response.usage = Mock(total_tokens=100)
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text="Test analysis response")]
    mock_response.usage = Mock(input_tokens=50, output_tokens=50)
    mock_client.messages.create.return_value = mock_response
    return mock_client


class TestLLMConfig:
    """Test LLM configuration."""

    def test_config_creation(self):
        """Test creating LLM config."""
        config = LLMConfig(
            provider="openai", model="gpt-4", api_key="test-key", temperature=0.7, max_tokens=2000
        )

        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.api_key == "test-key"
        assert config.temperature == 0.7
        assert config.max_tokens == 2000

    def test_config_defaults(self):
        """Test config default values."""
        config = LLMConfig(provider="openai", model="gpt-4", api_key="test-key")

        assert config.temperature == 0.7
        assert config.max_tokens == 2000
        assert config.cache_enabled is True


class TestLLMAnalyzer:
    """Test LLM analyzer functionality."""

    @patch("crumdbob.llm.openai")
    def test_analyzer_initialization_openai(self, mock_openai_module, temp_db):
        """Test initializing analyzer with OpenAI."""
        mock_openai_module.OpenAI = Mock(return_value=Mock())

        config = LLMConfig(provider="openai", model="gpt-4", api_key="test-key")

        analyzer = LLMAnalyzer(config, temp_db)

        assert analyzer.config == config
        assert analyzer.db == temp_db
        assert analyzer.client is not None

    @patch("crumdbob.llm.anthropic")
    def test_analyzer_initialization_anthropic(self, mock_anthropic_module, temp_db):
        """Test initializing analyzer with Anthropic."""
        mock_anthropic_module.Anthropic = Mock(return_value=Mock())

        config = LLMConfig(
            provider="anthropic", model="claude-3-sonnet-20240229", api_key="test-key"
        )

        analyzer = LLMAnalyzer(config, temp_db)

        assert analyzer.config == config
        assert analyzer.db == temp_db
        assert analyzer.client is not None

    def test_analyzer_missing_api_key(self, temp_db):
        """Test analyzer fails without API key."""
        config = LLMConfig(provider="openai", model="gpt-4", api_key=None)

        with pytest.raises(ValueError, match="API key not provided"):
            LLMAnalyzer(config, temp_db)

    def test_analyzer_unsupported_provider(self, temp_db):
        """Test analyzer fails with unsupported provider."""
        config = LLMConfig(provider="unsupported", model="test-model", api_key="test-key")

        with pytest.raises(ValueError, match="Unsupported provider"):
            LLMAnalyzer(config, temp_db)

    @patch("crumdbob.llm.openai")
    def test_analyze_session(self, mock_openai_module, temp_db, mock_openai_client):
        """Test session analysis."""
        mock_openai_module.OpenAI = Mock(return_value=mock_openai_client)

        config = LLMConfig(provider="openai", model="gpt-4", api_key="test-key")
        analyzer = LLMAnalyzer(config, temp_db)

        session_data = {
            "session_name": "Test Session",
            "git_branch": "main",
            "git_author": "test@example.com",
            "file_count": 5,
            "command_count": 10,
            "risk_count": 2,
            "task_count": 3,
            "files": ["file1.py", "file2.py"],
            "commands": ["git commit", "pytest"],
            "risks": ["Security risk", "Performance issue"],
            "tasks": ["Fix bug", "Add tests"],
        }

        response = analyzer.analyze_session(session_data)

        assert isinstance(response, LLMResponse)
        assert response.content == "Test analysis response"
        assert response.provider == "openai"
        assert response.model == "gpt-4"
        assert response.tokens_used == 100
        assert response.cached is False

    @patch("crumdbob.llm.openai")
    def test_categorize_risk(self, mock_openai_module, temp_db, mock_openai_client):
        """Test risk categorization."""
        mock_openai_module.OpenAI = Mock(return_value=mock_openai_client)

        config = LLMConfig(provider="openai", model="gpt-4", api_key="test-key")
        analyzer = LLMAnalyzer(config, temp_db)

        response = analyzer.categorize_risk(
            "SQL injection vulnerability", context={"files": ["api.py"]}
        )

        assert isinstance(response, LLMResponse)
        assert response.content == "Test analysis response"

    @patch("crumdbob.llm.openai")
    def test_explain_pattern(self, mock_openai_module, temp_db, mock_openai_client):
        """Test pattern explanation."""
        mock_openai_module.OpenAI = Mock(return_value=mock_openai_client)

        config = LLMConfig(provider="openai", model="gpt-4", api_key="test-key")
        analyzer = LLMAnalyzer(config, temp_db)

        pattern_data = {
            "pattern_type": "recurring_risk",
            "description": "Missing error handling",
            "frequency": 5,
            "evidence": ["file1.py", "file2.py"],
        }

        response = analyzer.explain_pattern(pattern_data)

        assert isinstance(response, LLMResponse)
        assert response.content == "Test analysis response"

    @patch("crumdbob.llm.openai")
    def test_caching(self, mock_openai_module, temp_db, mock_openai_client):
        """Test response caching."""
        mock_openai_module.OpenAI = Mock(return_value=mock_openai_client)

        config = LLMConfig(provider="openai", model="gpt-4", api_key="test-key", cache_enabled=True)
        analyzer = LLMAnalyzer(config, temp_db)

        session_data = {"session_name": "Test", "file_count": 1}

        # First call - not cached
        response1 = analyzer.analyze_session(session_data)
        assert response1.cached is False

        # Second call - should be cached
        response2 = analyzer.analyze_session(session_data)
        assert response2.cached is True
        assert response2.content == response1.content

    @patch("crumdbob.llm.openai")
    def test_error_handling(self, mock_openai_module, temp_db):
        """Test error handling in LLM calls."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_module.OpenAI = Mock(return_value=mock_client)

        config = LLMConfig(provider="openai", model="gpt-4", api_key="test-key")
        analyzer = LLMAnalyzer(config, temp_db)

        session_data = {"session_name": "Test"}
        response = analyzer.analyze_session(session_data)

        assert "Error calling LLM" in response.content
        assert response.tokens_used is None


class TestLLMHelpers:
    """Test LLM helper functions."""

    def test_get_llm_config_from_db(self, temp_db):
        """Test getting LLM config from database."""
        # Save config to database
        temp_db.save_llm_config(
            provider="openai",
            model="gpt-4",
            api_key_env="OPENAI_API_KEY",
            temperature=0.7,
            max_tokens=2000,
        )

        # Get config
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            config = get_llm_config(temp_db)

        assert config is not None
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.api_key == "test-key"

    def test_get_llm_config_from_env(self):
        """Test getting LLM config from environment."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            config = get_llm_config()

        assert config is not None
        assert config.provider == "openai"
        assert config.api_key == "test-key"

    def test_get_llm_config_not_configured(self):
        """Test getting config when not configured."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_llm_config()

        assert config is None

    @patch("crumdbob.llm.get_llm_config")
    @patch("crumdbob.llm.LLMAnalyzer")
    def test_create_llm_analyzer(self, mock_analyzer_class, mock_get_config):
        """Test creating LLM analyzer."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        analyzer = create_llm_analyzer()

        assert analyzer == mock_analyzer
        mock_analyzer_class.assert_called_once_with(mock_config, None)

    @patch("crumdbob.llm.get_llm_config")
    def test_create_llm_analyzer_not_configured(self, mock_get_config):
        """Test creating analyzer when not configured."""
        mock_get_config.return_value = None

        analyzer = create_llm_analyzer()

        assert analyzer is None

    @patch("crumdbob.llm.get_llm_config")
    def test_is_llm_available(self, mock_get_config):
        """Test checking if LLM is available."""
        mock_get_config.return_value = Mock()
        assert is_llm_available() is True

        mock_get_config.return_value = None
        assert is_llm_available() is False


class TestDatabaseIntegration:
    """Test LLM database integration."""

    def test_save_llm_config(self, temp_db):
        """Test saving LLM configuration."""
        config_id = temp_db.save_llm_config(
            provider="openai",
            model="gpt-4",
            api_key_env="OPENAI_API_KEY",
            temperature=0.8,
            max_tokens=1500,
        )

        assert config_id > 0

        config = temp_db.get_llm_config()
        assert config["provider"] == "openai"
        assert config["model"] == "gpt-4"
        assert config["temperature"] == 0.8
        assert config["max_tokens"] == 1500

    def test_get_llm_cache_stats(self, temp_db):
        """Test getting cache statistics."""
        stats = temp_db.get_llm_cache_stats()

        assert "total_cached" in stats
        assert "total_tokens_saved" in stats
        assert "by_provider" in stats
        assert stats["total_cached"] == 0

    def test_clear_llm_cache(self, temp_db):
        """Test clearing LLM cache."""
        deleted = temp_db.clear_llm_cache()
        assert deleted == 0  # No entries to delete

        # Test with age filter
        deleted = temp_db.clear_llm_cache(older_than_days=7)
        assert deleted == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
