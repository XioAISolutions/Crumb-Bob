"""LLM integration for intelligent analysis in CrumbBob.

Provides AI-powered insights, risk categorization, pattern explanations,
and smart recommendations using multiple LLM providers.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


LLMProvider = Literal["openai", "anthropic", "local"]
logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    provider: LLMProvider
    model: str
    api_key: str | None
    temperature: float = 0.7
    max_tokens: int = 2000
    cache_enabled: bool = True
    timeout: int = 30


@dataclass
class LLMResponse:
    """Response from LLM analysis."""

    content: str
    provider: str
    model: str
    tokens_used: int | None
    cached: bool
    timestamp: str


class LLMAnalyzer:
    """LLM-powered analysis engine for CrumbBob."""

    def __init__(self, config: LLMConfig, db=None):
        """Initialize LLM analyzer.

        Args:
            config: LLM configuration
            db: Optional MemoryDatabase instance for caching
        """
        self.config = config
        self.db = db
        self.client: Any = None

        # Initialize provider client
        if config.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package not installed. Install with: pip install openai")
            if not config.api_key:
                raise ValueError("OpenAI API key not provided")
            self.client = openai.OpenAI(api_key=config.api_key, timeout=config.timeout)

        elif config.provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError(
                    "anthropic package not installed. Install with: pip install anthropic"
                )
            if not config.api_key:
                raise ValueError("Anthropic API key not provided")
            self.client = anthropic.Anthropic(api_key=config.api_key, timeout=config.timeout)

        elif config.provider == "local":
            # For future local model support (Ollama, LM Studio, etc.)
            raise NotImplementedError("Local model support coming soon")

        else:
            raise ValueError(f"Unsupported provider: {config.provider}")

    def analyze_session(self, session_data: dict[str, Any]) -> LLMResponse:
        """Analyze a development session comprehensively.

        Args:
            session_data: Dictionary containing session information

        Returns:
            LLM analysis response
        """
        prompt = f"""Analyze this development session and provide insights:

Session: {session_data.get("session_name", "Unnamed")}
Branch: {session_data.get("git_branch", "N/A")}
Author: {session_data.get("git_author", "N/A")}
Files modified: {session_data.get("file_count", 0)}
Commands executed: {session_data.get("command_count", 0)}
Risks detected: {session_data.get("risk_count", 0)}
Tasks identified: {session_data.get("task_count", 0)}

Files: {json.dumps(session_data.get("files", [])[:10], indent=2)}
Commands: {json.dumps(session_data.get("commands", [])[:10], indent=2)}
Risks: {json.dumps(session_data.get("risks", [])[:5], indent=2)}

Provide a comprehensive analysis including:
1. Summary of what was accomplished
2. Key risks and concerns (prioritized)
3. Code quality observations
4. Recommendations for improvement
5. Potential technical debt introduced

Keep it concise but actionable (3-4 paragraphs)."""

        return self._call_llm(prompt)

    def categorize_risk(
        self,
        risk_description: str,
        context: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Categorize and assess a risk intelligently.

        Args:
            risk_description: Description of the risk
            context: Optional context (files, commands, etc.)

        Returns:
            LLM risk categorization response
        """
        context_str = ""
        if context:
            context_str = f"\nContext:\n{json.dumps(context, indent=2)}"

        prompt = f"""Categorize this development risk and assess its severity:

Risk: {risk_description}{context_str}

Provide:
1. Risk category (security, performance, maintainability, reliability, scalability, etc.)
2. Severity level (critical, high, medium, low) with justification
3. Potential impact on the system
4. Recommended mitigation steps (specific and actionable)
5. Urgency (immediate, short-term, long-term)

Format as JSON with keys: category, severity, impact, mitigation, urgency"""

        return self._call_llm(prompt)

    def explain_pattern(self, pattern_data: dict[str, Any]) -> LLMResponse:
        """Explain a detected code pattern in natural language.

        Args:
            pattern_data: Dictionary containing pattern information

        Returns:
            LLM pattern explanation response
        """
        prompt = f"""Explain this code pattern in natural language:

Pattern Type: {pattern_data.get("pattern_type")}
Description: {pattern_data.get("description")}
Frequency: {pattern_data.get("frequency")}
Severity: {pattern_data.get("severity", "N/A")}

Evidence:
{json.dumps(pattern_data.get("evidence", []), indent=2)}

Provide:
1. What this pattern represents
2. Why it might be occurring
3. Whether it's a good or bad practice
4. Suggestions for improvement if needed

Keep it concise and actionable (2-3 paragraphs)."""

        return self._call_llm(prompt)

    def generate_insights(self, data: dict[str, Any]) -> LLMResponse:
        """Generate automated insights from session data.

        Args:
            data: Dictionary containing various session metrics

        Returns:
            LLM insights response
        """
        prompt = f"""Generate insights from this development data:

{json.dumps(data, indent=2)}

Provide:
1. Key trends and patterns
2. Potential issues or concerns
3. Positive observations
4. Actionable recommendations

Focus on insights that would help improve development practices."""

        return self._call_llm(prompt)

    def recommend_actions(self, session_data: dict[str, Any]) -> LLMResponse:
        """Generate smart action recommendations.

        Args:
            session_data: Dictionary containing session information

        Returns:
            LLM recommendations response
        """
        prompt = f"""Based on this development session, recommend specific actions:

Session: {session_data.get("session_name", "Unnamed")}
Risks: {json.dumps(session_data.get("risks", []), indent=2)}
Tasks: {json.dumps(session_data.get("tasks", []), indent=2)}
Files: {json.dumps(session_data.get("files", [])[:10], indent=2)}

Provide:
1. Immediate actions (do now)
2. Short-term actions (this week)
3. Long-term actions (this month)
4. Preventive measures

Format as a prioritized list with clear action items."""

        return self._call_llm(prompt)

    def summarize_trends(self, trend_data: dict[str, Any]) -> LLMResponse:
        """Summarize trends across multiple sessions.

        Args:
            trend_data: Dictionary containing trend information

        Returns:
            LLM trend summary response
        """
        prompt = f"""Summarize these development trends:

{json.dumps(trend_data, indent=2)}

Provide:
1. Overall trajectory (improving, declining, stable)
2. Notable changes or shifts
3. Recurring issues
4. Recommendations for the team

Keep it concise and focused on actionable insights."""

        return self._call_llm(prompt)

    def _call_llm(self, prompt: str) -> LLMResponse:
        """Call LLM with prompt, using cache if available.

        Args:
            prompt: Prompt text

        Returns:
            LLM response
        """
        # Check cache first
        if self.config.cache_enabled and self.db:
            cached = self._get_cached_response(prompt)
            if cached:
                return cached

        # Call LLM
        timestamp = datetime.now(timezone.utc).isoformat()
        tokens_used = None

        try:
            if self.config.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                content = response.choices[0].message.content or ""
                tokens_used = response.usage.total_tokens if response.usage else None

            elif self.config.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.config.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                content = getattr(response.content[0], "text", "")
                if hasattr(response, "usage"):
                    tokens_used = response.usage.input_tokens + response.usage.output_tokens
                else:
                    tokens_used = None

            else:
                raise NotImplementedError(f"Provider {self.config.provider} not implemented")

            llm_response = LLMResponse(
                content=content,
                provider=self.config.provider,
                model=self.config.model,
                tokens_used=tokens_used,
                cached=False,
                timestamp=timestamp,
            )

            # Cache response
            if self.config.cache_enabled and self.db:
                self._cache_response(prompt, llm_response)

            return llm_response

        except Exception as e:
            # Return error response with fallback
            return LLMResponse(
                content=f"Error calling LLM: {e!s}",
                provider=self.config.provider,
                model=self.config.model,
                tokens_used=None,
                cached=False,
                timestamp=timestamp,
            )

    def _get_cached_response(self, prompt: str) -> LLMResponse | None:
        """Get cached LLM response if available.

        Args:
            prompt: Prompt text

        Returns:
            Cached response or None
        """
        if not self.db:
            return None

        prompt_hash = self._hash_prompt(prompt)

        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                SELECT response, provider, model, tokens_used, created_at
                FROM llm_cache
                WHERE prompt_hash = ?
            """,
                (prompt_hash,),
            )

            row = cursor.fetchone()
            if row:
                return LLMResponse(
                    content=row["response"],
                    provider=row["provider"],
                    model=row["model"],
                    tokens_used=row["tokens_used"],
                    cached=True,
                    timestamp=row["created_at"],
                )
        except sqlite3.Error as exc:
            logger.debug("Failed to read LLM cache", exc_info=exc)

        return None

    def _cache_response(self, prompt: str, response: LLMResponse) -> None:
        """Cache LLM response.

        Args:
            prompt: Prompt text
            response: LLM response to cache
        """
        if not self.db:
            return

        prompt_hash = self._hash_prompt(prompt)

        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO llm_cache
                (prompt_hash, prompt, response, provider, model, tokens_used, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    prompt_hash,
                    prompt,
                    response.content,
                    response.provider,
                    response.model,
                    response.tokens_used,
                    response.timestamp,
                ),
            )
            self.db.conn.commit()
        except sqlite3.Error as exc:
            logger.debug("Failed to write LLM cache", exc_info=exc)

    def _hash_prompt(self, prompt: str) -> str:
        """Generate hash for prompt caching.

        Args:
            prompt: Prompt text

        Returns:
            SHA256 hash of prompt
        """
        return hashlib.sha256(prompt.encode()).hexdigest()

    def count_tokens(self, text: str) -> int:
        """Count tokens in text (approximate if tiktoken not available).

        Args:
            text: Text to count tokens for

        Returns:
            Approximate token count
        """
        if TIKTOKEN_AVAILABLE and self.config.provider == "openai":
            try:
                encoding = tiktoken.encoding_for_model(self.config.model)
                return len(encoding.encode(text))
            except (KeyError, ValueError) as exc:
                logger.debug("Falling back to approximate token count", exc_info=exc)

        # Fallback: rough approximation (1 token ≈ 4 characters)
        return len(text) // 4


def get_llm_config(db=None) -> LLMConfig | None:
    """Get LLM configuration from database or environment.

    Args:
        db: Optional MemoryDatabase instance

    Returns:
        LLM configuration or None if not configured
    """
    # Try to get from database first
    if db:
        try:
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT provider, model, api_key_env, temperature, max_tokens, enabled
                FROM llm_config
                WHERE enabled = 1
                ORDER BY id DESC
                LIMIT 1
            """)
            row = cursor.fetchone()

            if row:
                api_key = os.getenv(row["api_key_env"])
                return LLMConfig(
                    provider=row["provider"],
                    model=row["model"],
                    api_key=api_key,
                    temperature=row["temperature"],
                    max_tokens=row["max_tokens"],
                )
        except sqlite3.Error as exc:
            logger.debug("Failed to read LLM config", exc_info=exc)

    # Fallback to environment variables
    if os.getenv("OPENAI_API_KEY"):
        return LLMConfig(
            provider="openai",
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
        )

    if os.getenv("ANTHROPIC_API_KEY"):
        return LLMConfig(
            provider="anthropic",
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
        )

    return None


def create_llm_analyzer(db=None) -> LLMAnalyzer | None:
    """Create LLM analyzer if configured.

    Args:
        db: Optional MemoryDatabase instance

    Returns:
        LLM analyzer or None if not configured
    """
    config = get_llm_config(db)
    if not config:
        return None

    try:
        return LLMAnalyzer(config, db)
    except (ImportError, ValueError, NotImplementedError):
        return None


def is_llm_available() -> bool:
    """Check if LLM is available and configured.

    Returns:
        True if LLM can be used
    """
    return get_llm_config() is not None


# Made with Bob
