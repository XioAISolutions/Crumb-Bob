# LLM Integration Guide

CrumbBob now includes AI-powered intelligent analysis using Large Language Models (LLMs). This feature provides automated insights, risk categorization, pattern explanations, and smart recommendations.

## Table of Contents

- [Overview](#overview)
- [Supported Providers](#supported-providers)
- [Setup Instructions](#setup-instructions)
- [Usage Examples](#usage-examples)
- [API Reference](#api-reference)
- [Cost Considerations](#cost-considerations)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The LLM integration adds intelligent analysis capabilities to CrumbBob:

- **Session Analysis**: Comprehensive analysis of development sessions
- **Risk Categorization**: Intelligent risk assessment and prioritization
- **Pattern Explanation**: Natural language explanations of detected patterns
- **Smart Recommendations**: Actionable recommendations based on session data
- **Trend Summarization**: Analysis of trends across multiple sessions

### Key Features

- ✅ Multi-provider support (OpenAI, Anthropic)
- ✅ Response caching to minimize API costs
- ✅ Graceful fallback when LLM unavailable
- ✅ Token counting and usage tracking
- ✅ CLI and Web API integration
- ✅ Configurable temperature and max tokens

## Supported Providers

### OpenAI

- **Models**: GPT-4, GPT-4 Turbo, GPT-3.5 Turbo
- **Recommended**: `gpt-4` for best results
- **API Key**: Requires `OPENAI_API_KEY` environment variable

### Anthropic

- **Models**: Claude 3 (Opus, Sonnet, Haiku)
- **Recommended**: `claude-3-sonnet-20240229` for balanced performance
- **API Key**: Requires `ANTHROPIC_API_KEY` environment variable

### Local Models (Coming Soon)

Support for local models via Ollama and LM Studio is planned for future releases.

## Setup Instructions

### 1. Install LLM Dependencies

```bash
# Install with LLM support
pip install -e .[llm]

# Or install all optional dependencies
pip install -e .[all]

# Or install specific packages
pip install openai anthropic tiktoken
```

### 2. Configure API Keys

#### OpenAI Setup

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# For persistence, add the export manually to a private shell profile
# or use your OS secret manager. Do not commit API keys.
```

Get your API key from: https://platform.openai.com/api-keys

#### Anthropic Setup

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."

# For persistence, add the export manually to a private shell profile
# or use your OS secret manager. Do not commit API keys.
```

Get your API key from: https://console.anthropic.com/

### 3. Configure CrumbBob

```bash
# Configure OpenAI
crumdbob llm setup openai --model gpt-4

# Or configure Anthropic
crumdbob llm setup anthropic --model claude-3-sonnet-20240229

# With custom settings
crumdbob llm setup openai \
  --model gpt-4 \
  --temperature 0.7 \
  --max-tokens 2000
```

### 4. Verify Configuration

```bash
# Check LLM status
crumdbob llm status
```

Expected output:
```
🤖 LLM Configuration
============================================================
Provider: openai
Model: gpt-4
API Key: $OPENAI_API_KEY
Temperature: 0.7
Max Tokens: 2000
Status: ✓ API key is set

📊 Cache Statistics
Cached responses: 0
Tokens saved: 0
```

## Usage Examples

### CLI Usage

#### Analyze a Session

```bash
# Analyze session with AI
crumdbob llm analyze 42

# Output:
# 🤖 Analyzing Session #42...
#
# This session focused on implementing user authentication...
# [Detailed AI analysis]
```

#### Explain a Pattern

```bash
# Get explanation of a pattern
crumdbob llm explain "Recurring SQL injection risks in API endpoints" \
  --pattern-type security \
  --frequency 5
```

#### Get Recommendations

```bash
# Get AI recommendations for a session
crumdbob llm recommend 42

# Output:
# 🤖 Generating recommendations for Session #42...
#
# Immediate Actions:
# 1. Address SQL injection vulnerability in api.py
# 2. Add input validation to user endpoints
# ...
```

#### Manage Cache

```bash
# Clear all cached responses
crumdbob llm clear-cache

# Clear responses older than 7 days
crumdbob llm clear-cache --older-than 7
```

### Web API Usage

#### Check LLM Status

```bash
curl http://localhost:8000/api/llm/status
```

Response:
```json
{
  "configured": true,
  "available": true,
  "config": {
    "provider": "openai",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "cache_stats": {
    "total_cached": 15,
    "total_tokens_saved": 12500,
    "by_provider": {
      "openai": 15
    }
  }
}
```

#### Analyze Session

```bash
curl -X POST http://localhost:8000/api/llm/analyze/42
```

Response:
```json
{
  "content": "This session focused on...",
  "provider": "openai",
  "model": "gpt-4",
  "tokens_used": 850,
  "cached": false,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Explain Pattern

```bash
curl -X POST http://localhost:8000/api/llm/explain \
  -H "Content-Type: application/json" \
  -d '{
    "pattern_type": "security",
    "description": "SQL injection risks",
    "frequency": 5,
    "evidence": ["api.py", "db.py"]
  }'
```

#### Get Recommendations

```bash
curl -X POST http://localhost:8000/api/llm/recommend/42
```

### Python API Usage

```python
from crumdbob.llm import create_llm_analyzer
from crumdbob.memory import MemoryDatabase

# Initialize
db = MemoryDatabase("~/.crumdbob/memory.db")
analyzer = create_llm_analyzer(db)

if analyzer:
    # Analyze session
    session_data = {
        "session_name": "Feature Implementation",
        "file_count": 10,
        "risk_count": 3,
        "files": ["api.py", "models.py"],
        "risks": ["SQL injection", "Missing auth"]
    }
    
    response = analyzer.analyze_session(session_data)
    print(response.content)
    print(f"Tokens used: {response.tokens_used}")
    print(f"Cached: {response.cached}")
    
    # Categorize risk
    risk_response = analyzer.categorize_risk(
        "SQL injection in user input",
        context={"files": ["api.py"]}
    )
    print(risk_response.content)
else:
    print("LLM not configured")

db.close()
```

## API Reference

### CLI Commands

- `crumdbob llm setup <provider>` - Configure LLM provider
- `crumdbob llm status` - Show configuration and stats
- `crumdbob llm analyze <session_id>` - Analyze session
- `crumdbob llm explain <description>` - Explain pattern
- `crumdbob llm recommend <session_id>` - Get recommendations
- `crumdbob llm clear-cache` - Clear response cache

### Web API Endpoints

- `GET /api/llm/status` - Get LLM status
- `POST /api/llm/analyze/{session_id}` - Analyze session
- `POST /api/llm/explain` - Explain pattern
- `POST /api/llm/recommend/{session_id}` - Get recommendations

### Python API

```python
from crumdbob.llm import (
    LLMConfig,
    LLMAnalyzer,
    create_llm_analyzer,
    get_llm_config,
    is_llm_available
)

# Create analyzer
analyzer = create_llm_analyzer(db)

# Analysis methods
analyzer.analyze_session(session_data)
analyzer.categorize_risk(risk_description, context)
analyzer.explain_pattern(pattern_data)
analyzer.generate_insights(data)
analyzer.recommend_actions(session_data)
analyzer.summarize_trends(trend_data)
```

## Cost Considerations

### Pricing (Approximate)

**OpenAI GPT-4:**
- Input: $0.03 per 1K tokens
- Output: $0.06 per 1K tokens
- Average session analysis: ~1000 tokens = $0.05

**Anthropic Claude 3 Sonnet:**
- Input: $0.003 per 1K tokens
- Output: $0.015 per 1K tokens
- Average session analysis: ~1000 tokens = $0.01

### Cost Optimization

1. **Response Caching**: Identical prompts return cached responses
   - Saves 100% of API costs for repeated queries
   - Cache persists across sessions

2. **Token Limits**: Configure `max_tokens` to control costs
   ```bash
   crumdbob llm setup openai --max-tokens 1000
   ```

3. **Selective Analysis**: Only analyze important sessions
   ```bash
   # Analyze high-risk sessions only
   crumdbob llm analyze $(crumdbob sessions list --format json | jq '.[] | select(.risk_count > 5) | .id')
   ```

4. **Cache Management**: Clear old cache entries
   ```bash
   # Clear cache older than 30 days
   crumdbob llm clear-cache --older-than 30
   ```

### Monitoring Costs

```bash
# Check cache stats to see savings
crumdbob llm status

# Output shows:
# Cached responses: 50
# Tokens saved: 45,000  # ~$2.25 saved with GPT-4
```

## Best Practices

### 1. Start with Caching Enabled

Caching is enabled by default and significantly reduces costs:

```python
config = LLMConfig(
    provider="openai",
    model="gpt-4",
    api_key=api_key,
    cache_enabled=True  # Default
)
```

### 2. Use Appropriate Models

- **GPT-4**: Best quality, higher cost - use for critical analysis
- **GPT-3.5 Turbo**: Good quality, lower cost - use for routine analysis
- **Claude 3 Sonnet**: Balanced performance and cost

### 3. Set Reasonable Token Limits

```bash
# For concise analysis
crumdbob llm setup openai --max-tokens 1000

# For detailed analysis
crumdbob llm setup openai --max-tokens 2000
```

### 4. Adjust Temperature

- **0.3-0.5**: More focused, deterministic responses
- **0.7**: Balanced (default)
- **0.9-1.0**: More creative, varied responses

```bash
crumdbob llm setup openai --temperature 0.5
```

### 5. Batch Analysis

Analyze multiple sessions efficiently:

```bash
# Analyze recent high-risk sessions
for id in $(crumdbob sessions list --format json | jq -r '.[] | select(.risk_count > 3) | .id'); do
  crumdbob llm analyze $id
done
```

## Troubleshooting

### LLM Not Configured

**Error**: `❌ LLM not configured`

**Solution**:
```bash
crumdbob llm setup openai --model gpt-4
export OPENAI_API_KEY="your-key"
```

### API Key Not Set

**Error**: `❌ API key not set`

**Solution**:
```bash
# Check which key is needed
crumdbob llm status

# Set the appropriate key
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Import Errors

**Error**: `ImportError: No module named 'openai'`

**Solution**:
```bash
pip install -e .[llm]
# or
pip install openai anthropic tiktoken
```

### Rate Limiting

**Error**: `Rate limit exceeded`

**Solution**:
- Wait and retry
- Use caching to reduce API calls
- Consider upgrading API tier
- Implement exponential backoff (built-in)

### Timeout Errors

**Error**: `Request timeout`

**Solution**:
```python
# Increase timeout in config
config = LLMConfig(
    provider="openai",
    model="gpt-4",
    api_key=api_key,
    timeout=60  # Default is 30 seconds
)
```

### Cache Issues

**Problem**: Cache not working

**Solution**:
```bash
# Check cache stats
crumdbob llm status

# Clear and rebuild cache
crumdbob llm clear-cache

# Verify database has llm_cache table
sqlite3 ~/.crumdbob/memory.db "SELECT name FROM sqlite_master WHERE type='table' AND name='llm_cache';"
```

## Security Considerations

### API Key Security

1. **Never commit API keys** to version control
2. **Use environment variables** for API keys
3. **Rotate keys regularly**
4. **Use separate keys** for development and production

### Data Privacy

1. **Session data is sent to LLM providers** for analysis
2. **Review provider privacy policies**:
   - OpenAI: https://openai.com/policies/privacy-policy
   - Anthropic: https://www.anthropic.com/privacy

3. **For sensitive projects**:
   - Use local models (when available)
   - Disable LLM features
   - Review and sanitize data before analysis

### Rate Limiting

Built-in rate limiting prevents API quota exhaustion:
- Automatic retry with exponential backoff
- Configurable timeout
- Error handling for rate limit errors

## Future Enhancements

Planned features for future releases:

- 🔄 Local model support (Ollama, LM Studio)
- 🔄 Streaming responses for real-time analysis
- 🔄 Custom prompt templates
- 🔄 Multi-model comparison
- 🔄 Cost tracking and budgets
- 🔄 Automated analysis triggers

## Support

For issues or questions:

1. Check this documentation
2. Review [GitHub Issues](https://github.com/yourusername/crumdbob/issues)
3. Join our community discussions
4. Contact support

## License

LLM integration is part of CrumbBob and follows the same MIT license.

---

**Made with ❤️ by the CrumbBob team**
