# AI Module Unit Tests

This directory contains unit tests for AI-related functionality in CrossBridge.

## Test Files

### AI Transformation Tests
- **test_ai_transform.py** - Tests for AI-powered test transformation
- **test_ai_summary.py** - Tests for AI summary generation
- **test_ai_summary_quick.py** - Quick AI summary tests

### AI Configuration Tests
- **test_aiconfig_dict.py** - Tests for AI configuration dictionary handling

### AI Model Tests
- **test_model_selection.py** - Tests for AI model selection logic
- **test_fallback_integration.py** - Tests for fallback mechanisms when AI is unavailable

## Coverage Areas

- AI transformation pipeline
- OpenAI/Anthropic integration
- Model selection and fallback logic
- AI configuration management
- Cost tracking and token usage
- Prompt engineering and validation

## Running Tests

```bash
# Run all AI tests
pytest tests/unit/ai/ -v

# Run specific test file
pytest tests/unit/ai/test_ai_transform.py -v

# Run with coverage
pytest tests/unit/ai/ --cov=core.ai --cov-report=html
```
