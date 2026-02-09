# AI Integration Guide - CrossBridge

> **Complete guide to AI-enhanced log analysis with multi-provider support, license management, and cost transparency**

## Overview

CrossBridge supports **AI-enhanced test failure analysis** with multiple provider options (cloud and self-hosted), complete cost transparency, and license governance. This guide covers setup, usage, and best practices for all AI integrations.

**Supported Providers:**
- ☁️ **Cloud:** OpenAI (GPT-3.5, GPT-4), Anthropic (Claude), Azure OpenAI
- 🏠 **Self-hosted:** Ollama (deepseek-coder, llama3, mistral), vLLM (any HuggingFace model)

---

## 🚀 Quick Start

### 1. Cloud Provider (OpenAI/Anthropic)

```bash
# Basic usage (shows cost warning)
./bin/crossbridge-log output.xml --enable-ai

# Cost warning displayed:
⚠️  AI-ENHANCED ANALYSIS ENABLED (OpenAI)
Provider: Openai (gpt-3.5-turbo)
Cost: ~$0.002 per 1000 tokens
Using AI will incur additional costs:
  • OpenAI GPT-3.5: ~$0.002 per 1000 tokens
  • Typical analysis: $0.01-$0.10 per test run

# After analysis:
🤖 AI Usage Summary
  AI Configuration:
  • Provider: Openai
  • Model: gpt-3.5-turbo
  
  Token Usage & Cost:
  • Total Tokens: 1,500
  • Total Cost: $0.0023
  • Average per Test: 150 tokens ($0.0002)
  
✓ Total Time Taken: 3m 25s  ← Smart formatted duration!
```

### 2. Self-Hosted (Ollama) - NO LICENSE NEEDED 🆓

```bash
# 1. Install and start Ollama
ollama pull deepseek-coder:6.7b
ollama serve

# 2. Configure crossbridge.yml
intelligence:
  ai_provider: "ollama"
  ai_model: "deepseek-coder:6.7b"
  ollama:
    base_url: "http://localhost:11434"

# 3. Run analysis (no license required!)
./bin/crossbridge-log output.xml --enable-ai

# Green banner displayed:
🤖  AI-ENHANCED ANALYSIS ENABLED (Self-hosted)
Provider: Self-hosted (deepseek-coder:6.7b)
Cost: No additional costs (local inference)

# After analysis:
🤖 AI Usage Summary
  AI Configuration:
  • Provider: Self-hosted
  • Model: deepseek-coder:6.7b
  
  Token Usage:
  • Total Tokens: 1,500
  • Cost: No additional costs (local inference)
  
✓ Total Time Taken: 54h 2m  ← Auto-converted from 54 hours!
```

### 3. License Setup (Cloud Providers Only)

```bash
# Configure AI credentials (planned)
crossbridge configure ai

# Check license status
crossbridge license status
```

For now, license configuration is manual via `~/.crossbridge/ai_license.json`.

**Note:** Self-hosted providers (Ollama, vLLM) do NOT require licenses or API keys.

---

## 📋 Features

### AI-Enhanced Analysis

When `--enable-ai` is enabled, CrossBridge provides:

1. **Root Cause Analysis**
   - AI explains "why" the test failed
   - Context-aware reasoning
   - Links to similar historical failures

2. **Fix Recommendations**
   - Specific code-level suggestions
   - Locator improvements
   - Test refactoring advice

3. **Pattern Detection**
   - Identifies similar failures
   - Groups related issues
   - Trend analysis

4. **Business Impact Assessment**
   - Severity scoring
   - Urgency recommendations
   - Priority guidance

### Provider-Aware UI

Dynamic banners based on actual provider:

- ⚠️ **Yellow banner** - Cloud providers with cost warnings
- 🤖 **Green banner** - Self-hosted providers with "No cost" message
- 📊 **Smart duration** - Auto-formatted (45s, 3m 25s, 2h 15m, 3d 14h)

### Comprehensive Logging

All AI providers log detailed API call information:

**Pre-Request Logging:**
- 🤖 Model, endpoint, message count
- 📝 Prompt length and configuration
- 🔍 Execution ID for correlation

**Success Logging:**
- ✅ HTTP 200 status
- ⏱️ Latency (seconds)
- 💬 Tokens (prompt/completion/total)
- 💰 Cost calculation
- 📊 Response length

**Error Logging:**
- ❌ Timeouts with duration
- 🔴 HTTP errors with status codes
- ⚠️ Generic failures with context

**Provider-Specific:**
- Ollama: Performance metrics (tokens/sec, eval duration)
- OpenAI: Full request/response tracking
- Anthropic: Claude-specific with system messages
- vLLM: Self-hosted endpoint logging

### Cost Transparency

Every AI operation provides full transparency:

- **Before Processing:** Cost warning with estimated range (cloud only)
- **During Processing:** Real-time token tracking
- **After Processing:** Detailed breakdown with:
  - Prompt tokens used
  - Completion tokens used
  - Total tokens
  - Exact cost (cloud) or "No cost" (self-hosted)
  - Per-test averages
  - Cost comparison (GPT-3.5 vs GPT-4 savings)

### License Management (Cloud Providers Only)

**Tier-Based Limits:**

| Tier | Daily Limit | Monthly Limit | Use Case |
|------|-------------|---------------|----------|
| **FREE** | 1K tokens | 10K tokens | Testing & evaluation |
| **BASIC** | 10K tokens | 100K tokens | Small teams |
| **PROFESSIONAL** | 50K tokens | 1M tokens | Large teams |
| **ENTERPRISE** | 100K tokens | 5M tokens | Enterprise usage |
| **UNLIMITED** | No limit | No limit | Enterprise premium |

**Features:**
- Automatic daily/monthly usage reset
- Real-time limit enforcement
- Usage tracking and reporting
- License expiration handling
- Feature flags (log_analysis, transformation, test_generation)

---

## 🔧 Configuration

### Provider Configuration

CrossBridge supports multiple AI providers. Configure via `crossbridge.yml`:

#### OpenAI (Cloud)

```yaml
intelligence:
  ai_provider: "openai"
  ai_model: "gpt-3.5-turbo"  # or gpt-4, gpt-4o
  openai:
    api_key: "${OPENAI_API_KEY}"  # Or hardcode (not recommended)
    timeout: 30
```

**Environment Variables:**
```bash
export OPENAI_API_KEY="sk-proj-..."
./bin/crossbridge-log output.xml --enable-ai
```

#### Anthropic (Cloud)

```yaml
intelligence:
  ai_provider: "anthropic"
  ai_model: "claude-3-5-sonnet-20241022"
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    timeout: 30
```

**Environment Variables:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
./bin/crossbridge-log output.xml --enable-ai
```

#### Azure OpenAI (Cloud)

```yaml
intelligence:
  ai_provider: "azure"
  ai_model: "gpt-35-turbo"
  azure:
    api_key: "${AZURE_OPENAI_API_KEY}"
    endpoint: "https://your-resource.openai.azure.com/"
    deployment_name: "gpt-35-turbo"
    api_version: "2024-02-15-preview"
```

#### Ollama (Self-hosted) 🆓

```yaml
intelligence:
  ai_provider: "ollama"
  ai_model: "deepseek-coder:6.7b"  # or llama3, mistral, codellama
  ollama:
    base_url: "http://localhost:11434"
    timeout: 60  # Self-hosted may need longer timeout
```

**Setup:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull deepseek-coder:6.7b

# Start server
ollama serve

# Run analysis (no license needed!)
./bin/crossbridge-log output.xml --enable-ai
```

**Benefits:**
- ✅ No API costs
- ✅ No license required
- ✅ Full privacy (local inference)
- ✅ No internet required
- ⚡ Fast for small models (<10B params)

#### vLLM (Self-hosted) 🆓

```yaml
intelligence:
  ai_provider: "vllm"
  ai_model: "deepseek-ai/deepseek-coder-6.7b-instruct"
  vllm:
    base_url: "http://localhost:8000/v1"
    timeout: 60
```

**Setup:**
```bash
# Install vLLM
pip install vllm

# Start server
python -m vllm.entrypoints.openai.api_server \
  --model deepseek-ai/deepseek-coder-6.7b-instruct \
  --port 8000

# Run analysis (no license needed!)
./bin/crossbridge-log output.xml --enable-ai
```

**Benefits:**
- ✅ No API costs
- ✅ No license required
- ✅ Any HuggingFace model
- ✅ Optimized inference (faster than Ollama)
- 🔥 GPU acceleration support

### License File Format (Cloud Providers Only)

Location: `~/.crossbridge/ai_license.json`

```json
{
  "license_key": "LIC-XXXXX-XXXXX-XXXXX",
  "customer_id": "sk-proj-xxxxxxxxxxxxx",
  "tier": "PROFESSIONAL",
  "provider": "openai",
  "model": "gpt-3.5-turbo",
  "status": "ACTIVE",
  "valid_from": "2026-02-01T00:00:00",
  "valid_until": "2027-02-01T00:00:00",
  "monthly_token_limit": 1000000,
  "daily_token_limit": 50000,
  "tokens_used_today": 1500,
  "tokens_used_month": 15000,
  "last_reset_date": "2026-02-06",
  "last_reset_month": "2026-02",
  "features_enabled": {
    "log_analysis": true,
    "transformation": true,
    "test_generation": true
  }
}
```

### Creating a Demo License (Testing)

```python
from core.ai.license import LicenseValidator

# Create demo license for testing
validator = LicenseValidator()
license = validator.create_demo_license(
    provider="openai",
    model="gpt-3.5-turbo",
    tier="PROFESSIONAL",
    customer_id="sk-fake_test_key_xxxxx"
)

print(f"Demo license created: {license.license_key}")
```

---

## 💡 Usage Examples

### 1. Basic AI Analysis

```bash
./bin/crossbridge-log output.xml --enable-ai
```

**Output includes:**
- Standard failure classification
- AI-generated root cause analysis
- Specific fix recommendations
- Token usage and cost breakdown

### 2. AI Analysis with Correlation

```bash
./bin/crossbridge-log output.xml --enable-ai --correlation
```

AI analyzes failure groups instead of individual tests (faster and cheaper).

### 3. Selective AI Analysis (Cost Optimization)

```bash
# Only analyze product defects with AI
./bin/crossbridge-log output.xml --enable-ai --category PRODUCT_DEFECT

# Only analyze high-priority failures
./bin/crossbridge-log output.xml --enable-ai --test-name "Critical*"
```

### 4. Check License Status (Programmatic)

```python
from core.ai.license import LicenseValidator

validator = LicenseValidator()
is_valid, message, license = validator.validate_license("openai", "log_analysis")

if is_valid:
    print(f"License valid. Tier: {license.tier}")
    print(f"Daily limit: {license.daily_token_limit}")
    print(f"Used today: {license.tokens_used_today}")
    print(f"Remaining: {license.daily_token_limit - license.tokens_used_today}")
else:
    print(f"License invalid: {message}")
```

### 5. Track Usage

```python
from core.ai.license import LicenseValidator

validator = LicenseValidator()

# Track tokens used (called automatically by sidecar)
success, message = validator.track_usage(tokens_used=1500, cost=0.00225)

if success:
    print(f"Usage tracked successfully")
else:
    print(f"Usage tracking failed: {message}")
```

---

## 🎯 Best Practices

### Cost Optimization

1. **Use Correlation Analysis**
   ```bash
   # Analyze groups, not individual tests (70% faster, cheaper)
   ./bin/crossbridge-log output.xml --enable-ai --correlation
   ```

2. **Filter Before AI Analysis**
   ```bash
   # Only analyze failures (skip passing tests)
   ./bin/crossbridge-log output.xml --enable-ai --status FAIL
   
   # Focus on specific categories
   ./bin/crossbridge-log output.xml --enable-ai --category PRODUCT_DEFECT
   ```

3. **Choose Right Model**
   - **GPT-3.5-turbo** ($0.0015/1K): Fast, cost-effective, good quality
   - **GPT-4** ($0.045/1K): Better quality, 30x more expensive
   - **GPT-4-turbo** ($0.015/1K): Good balance, 10x more expensive than 3.5

4. **Use Free Tier for CI/CD**
   - Reserve AI analysis for production failures
   - Use deterministic analysis for PR checks
   - Enable AI only for critical/blocked issues

### License Management

1. **Monitor Usage**
   ```bash
   # Check remaining tokens before analysis
   python -c "from core.ai.license import LicenseValidator; \
              v = LicenseValidator(); \
              _, _, lic = v.validate_license('openai', 'log_analysis'); \
              print(f'Remaining: {lic.daily_token_limit - lic.tokens_used_today}')"
   ```

2. **Set Up Alerts**
   - Alert when 80% of daily limit used
   - Alert when 90% of monthly limit used
   - Alert 7 days before license expiration

3. **Upgrade Planning**
   - FREE → BASIC: When hitting daily limits
   - BASIC → PROFESSIONAL: For CI/CD integration
   - PROFESSIONAL → ENTERPRISE: For large-scale usage

### Security

1. **Protect API Keys**
   - License file is stored locally: `~/.crossbridge/ai_license.json`
   - Use file permissions: `chmod 600 ~/.crossbridge/ai_license.json`
   - Never commit license files to git
   - Use environment variables in CI/CD

2. **Rotate Keys Regularly**
   - Rotate OpenAI/Anthropic API keys every 90 days
   - Update license file with new keys
   - Track key usage separately per environment

---

## 🔍 Troubleshooting

### Issue: License Validation Failed

```
❌ AI License Validation Failed
License not found or invalid
```

**Solutions:**
1. Check license file exists: `~/.crossbridge/ai_license.json`
2. Verify license is active: `"status": "ACTIVE"`
3. Check expiration date: `"valid_until"`
4. Ensure provider matches: `"provider": "openai"`
5. Verify feature enabled: `"log_analysis": true`

### Issue: Daily/Monthly Limit Exceeded

```
❌ AI License Validation Failed
Daily token limit exceeded (10000/10000 used)
```

**Solutions:**
1. Wait for daily reset (midnight UTC)
2. Upgrade to higher tier
3. Use correlation to reduce token usage
4. Filter tests before AI analysis

### Issue: API Key Invalid

```
❌ AI License Validation Failed
Invalid API key or insufficient permissions
```

**Solutions:**
1. Verify API key format:
   - OpenAI: `sk-proj-...` or `sk-...`
   - Anthropic: `sk-ant-...`
2. Check API key has sufficient quota
3. Test key with provider directly
4. Rotate key if compromised

### Issue: High Costs

```
💰 Cost alert: $5.23 spent today (150K tokens)
```

**Solutions:**
1. Enable correlation analysis (reduces tokens by 70%)
2. Filter failed tests only
3. Switch to GPT-3.5-turbo instead of GPT-4
4. Use free deterministic analysis for non-critical runs
5. Set up cost alerts at 80% of budget
6. **Switch to self-hosted (Ollama/vLLM)** - Zero API costs! 🆓

### Issue: API Timeouts or 500 Errors

```
❌ HTTP Error (500) - Internal Server Error
❌ Request timeout after 30s
```

**Debugging with Comprehensive Logging:**

All AI providers now log detailed request/response information. Check container logs:

```bash
# View Ollama/OpenAI/Anthropic API calls
docker-compose logs -f crossbridge-sidecar | grep "🤖"

# Logs show:
# 🤖 Ollama API Call → http://localhost:11434/api/chat
#   Model: deepseek-coder:6.7b
#   Messages: 2 (prompt length: 1543 chars)
#   Temperature: 0.3, Max tokens: 2000
#   Execution ID: abc123-def456
#
# ✅ Ollama API Response (200 OK) - 2.45s
#   HTTP Status: 200 OK
#   Latency: 2.45s
#   Tokens: prompt=387, completion=234, total=621
#   Cost: $0.0009
#   Response length: 1234 chars
#   Performance: 253.47 tokens/sec
#
# ❌ HTTP Error (500) - http://localhost:11434/api/chat
#   Model: deepseek-coder:6.7b
#   Timeout: 30s
#   Status Code: 500
#   Error: Internal Server Error
```

**What the logs provide:**
- 🤖 Pre-request: Model, endpoint, config, execution_id
- ✅ Success: Latency, tokens, cost, performance metrics
- ❌ Errors: HTTP status, timeouts, full error context

**Solutions:**
1. Check model availability: `ollama list`
2. Verify endpoint accessibility: `curl http://localhost:11434/api/tags`
3. Increase timeout in crossbridge.yml: `timeout: 60`
4. Check system resources (RAM/GPU for self-hosted)
5. Correlate errors using execution_id across logs

### Issue: Provider Unknown or Auto-detecting

```
🔍 AI Provider Info: Auto-detecting...
```

**Cause:** Sidecar API doesn't have `/ai-provider-info` endpoint (old version)

**Solutions:**
1. Update sidecar container: `docker-compose pull`
2. Restart services: `docker-compose up -d`
3. Verify endpoint: `curl http://localhost:5001/ai-provider-info`

**Backward Compatibility:** CLI gracefully falls back to generic banner if endpoint is unavailable.

### Zero-Cost Alternative: Self-Hosted AI 🆓

**Want AI without API costs? Use self-hosted providers:**

| Provider | Setup Effort | Performance | Cost |
|----------|--------------|-------------|------|
| **Ollama** | Easy (5 min) | Good for <10B models | $0 |
| **vLLM** | Medium (15 min) | Excellent (GPU optimized) | $0 |

**Benefits:**
- ✅ No API keys needed
- ✅ No license required
- ✅ No monthly costs
- ✅ Full privacy (local inference)
- ✅ No internet dependency
- ✅ Green banner in UI (🤖)
- ✅ Comprehensive logging enabled

**See "Provider Configuration" section above for setup instructions.**

---

## 📊 Cost Estimation

### Pricing (as of Feb 2026)

**Cloud Providers:**

**OpenAI:**
- GPT-3.5-turbo: $0.0015 per 1K tokens (prompt + completion)
- GPT-4: $0.045 per 1K tokens
- GPT-4-turbo: $0.015 per 1K tokens

**Anthropic:**
- Claude-3-Sonnet: $0.006 per 1K tokens
- Claude-3-Opus: $0.0375 per 1K tokens

**Azure OpenAI:**
- Same as OpenAI prices (varies by region)

**Self-Hosted (FREE):** 🆓
- **Ollama:** $0 per token (local inference)
- **vLLM:** $0 per token (local inference)
- **Hardware cost:** One-time GPU cost (optional, can run on CPU)

### Typical Usage

| Scenario | Tests | Tokens/Test | Total Tokens | GPT-3.5 Cost | Ollama Cost |
|----------|-------|-------------|--------------|--------------|-------------|
| **Small run** | 10 failures | 150 | 1,500 | $0.002 | $0 🆓 |
| **Medium run** | 50 failures | 150 | 7,500 | $0.011 | $0 🆓 |
| **Large run** | 200 failures | 150 | 30,000 | $0.045 | $0 🆓 |
| **CI/CD daily** | 500 failures | 150 | 75,000 | $0.113 | $0 🆓 |
| **Monthly** | 10K failures | 150 | 1.5M | $2.25 | $0 🆓 |

**Annual Cost Comparison:**
- OpenAI GPT-3.5: **$27/year**
- Ollama/vLLM: **$0/year** 🎉

### Cost Optimization Examples

**Baseline: 1000 test failures/day**
- Without AI: $0
- With OpenAI GPT-3.5: ~$2.25/month
- **With Ollama (self-hosted): $0/month** 🆓
- With AI (all tests): $0.225/day = $6.75/month
- With correlation (70% reduction): $0.068/day = $2.03/month
- With filtering (50% reduction): $0.113/day = $3.38/month
- With correlation + filtering: $0.034/day = $1.01/month

---

## 🏗️ Architecture

### Components

```
┌─────────────────────────────────────────────────────┐
│                  CrossBridge Log                     │
│                   (CLI Tool)                         │
│  • Parse arguments                                   │
│  • Display cost warning                             │
│  • Call sidecar API                                 │
│  • Display results + AI usage                       │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│               Sidecar API                            │
│            (/analyze endpoint)                       │
│  • License validation                               │
│  • Framework detection                              │
│  • Classification                                   │
│  • AI enhancement (if enabled)                      │
│  • Token tracking                                   │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│           AI License Manager                         │
│          (core/ai/license.py)                        │
│  • License validation                               │
│  • Token limit enforcement                          │
│  • Usage tracking                                   │
│  • Cost calculation                                 │
│  • Automatic reset (daily/monthly)                  │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│            AI Provider                               │
│   (OpenAI / Anthropic)                              │
│  • Complete() API call                              │
│  • Token counting                                   │
│  • Error handling                                   │
└─────────────────────────────────────────────────────┘
```

### Data Flow

1. **User runs command:**
   ```bash
   ./bin/crossbridge-log output.xml --enable-ai
   ```

2. **CLI displays cost warning and gets confirmation**

3. **CLI calls sidecar API:**
   ```json
   POST /analyze
   {
     "data": {...},
     "framework": "robot",
     "enable_ai": true,
     "ai_provider": "openai",
     "ai_model": "gpt-3.5-turbo"
   }
   ```

4. **Sidecar validates license:**
   ```python
   validator = LicenseValidator()
   is_valid, msg, license = validator.validate_license("openai", "log_analysis")
   ```

5. **Sidecar processes with AI:**
   - For each failure, create prompt
   - Call AI provider
   - Track tokens (prompt + completion)
   - Add insights to classification

6. **Sidecar tracks usage:**
   ```python
   validator.track_usage(tokens_used=1500, cost=0.00225)
   ```

7. **Sidecar returns response:**
   ```json
   {
     "results": [...],
     "ai_usage": {
       "prompt_tokens": 1200,
       "completion_tokens": 300,
       "total_tokens": 1500,
       "cost": 0.00225,
       "provider": "openai",
       "model": "gpt-3.5-turbo"
     }
   }
   ```

8. **CLI displays AI usage summary**

---

## 🧪 Testing

### Unit Tests

```bash
# Test AI license system
pytest tests/unit/core/ai/test_ai_license.py -v

# Test AI module (backward compatibility)
pytest tests/unit/core/ai/test_ai_module.py -v

# Test transformation validator
pytest tests/unit/core/ai/test_transformation_validator.py -v

# All AI tests
pytest tests/unit/core/ai/ -v
```

**Current Status:**
- ✅ 27 AI license tests (100% passing)
- ✅ 33 AI module tests (100% passing)
- ✅ 36 transformation tests (100% passing)
- ✅ 180 total AI tests (100% passing)

### Integration Tests

```bash
# Test with fake API keys
export OPENAI_API_KEY="sk-fake_test_key_xxxxx"
./bin/crossbridge-log output.xml --enable-ai
# Should show license validation error (expected)

# Test with demo license
python -c "from core.ai.license import LicenseValidator; \
           v = LicenseValidator(); \
           v.create_demo_license('openai', 'gpt-3.5-turbo', 'PROFESSIONAL', 'sk-fake_test')"
./bin/crossbridge-log output.xml --enable-ai
# Should work but fail at API call (expected - fake key)
```

---

## 📚 Related Documentation

- [CrossBridge Log CLI Guide](../cli/CROSSBRIDGE_LOG.md) - Complete CLI reference
- [Execution Intelligence](../EXECUTION_INTELLIGENCE.md) - Classification system details
- [AI Module Documentation](../../core/ai/README.md) - AI architecture
- [Sidecar API Reference](../sidecar/SIDECAR_API.md) - API endpoints

---

## 🤝 Contributing

To contribute to AI integration:

1. **Add New AI Provider**
   - Implement provider in `core/ai/providers/`
   - Add cost estimation in `core/ai/license.py`
   - Update sidecar API
   - Add tests

2. **Add New License Tier**
   - Update `LicenseTier` enum
   - Add tier limits in `AILicense` model
   - Update documentation

3. **Improve AI Prompts**
   - Edit prompts in sidecar API
   - Test with multiple failure types
   - Validate cost impact

---

## 📝 License

Apache 2.0

---

## 💬 Support

- **Issues:** https://github.com/crossstack-ai/crossbridge/issues
- **Documentation:** https://docs.crossbridge.dev
- **Email:** support@crossbridge.dev
- **AI Integration Help:** ai-integration@crossbridge.dev
