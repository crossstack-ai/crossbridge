"""
Unit tests for LLM service integration features.

Tests:
- Azure OpenAI provider
- Translation context management
- Token usage tracking
- Response parsing and validation
- Prompt template system
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from core.ai.models import (
    AIExecutionContext,
    AIMessage,
    AIResponse,
    ModelConfig,
    ProviderType,
    TaskType,
    TokenUsage,
    ExecutionStatus,
)
from core.ai.providers import (
    AzureOpenAIProvider,
    get_provider,
    get_available_providers,
    AZURE_PROVIDER_KEY,
)
from core.ai.translation_context import (
    FrameworkInfo,
    TranslationPattern,
    TranslationContext,
    TranslationContextManager,
    get_common_patterns,
)
from core.ai.prompts.registry import PromptRegistry, PromptRenderer


class TestAzureOpenAIProvider:
    """Test Azure OpenAI provider integration."""
    
    def test_azure_provider_initialization(self):
        """Test Azure OpenAI provider can be initialized."""
        config = {
            "api_key": "test_key",
            "endpoint": "https://test.openai.azure.com",
            "deployment_name": "gpt-4-deployment",
            "api_version": "2024-02-15-preview",
        }
        
        provider = AzureOpenAIProvider(config)
        
        assert provider.api_key == "test_key"
        assert provider.endpoint == "https://test.openai.azure.com"
        assert provider.deployment_name == "gpt-4-deployment"
        assert provider.api_version == "2024-02-15-preview"
    
    def test_azure_provider_requires_deployment_name(self):
        """Test Azure provider fails without deployment name."""
        config = {
            "api_key": "test_key",
            "endpoint": "https://test.openai.azure.com",
        }
        
        provider = AzureOpenAIProvider(config)
        context = AIExecutionContext(task_type=TaskType.TEST_GENERATION)
        messages = [AIMessage(role="user", content="test")]
        model_config = ModelConfig(model="gpt-4")
        
        with pytest.raises(Exception) as exc:
            provider.complete(
                messages=messages,
                model_config=model_config,
                context=context,
            )
        
        assert "deployment_name" in str(exc.value).lower()
    
    def test_azure_provider_is_available(self):
        """Test Azure provider availability check."""
        # With all required fields
        config1 = {
            "api_key": "test",
            "endpoint": "https://test.azure.com",
            "deployment_name": "gpt-4",
        }
        provider1 = AzureOpenAIProvider(config1)
        assert provider1.is_available() is True
        
        # Missing deployment name
        config2 = {
            "api_key": "test",
            "endpoint": "https://test.azure.com",
        }
        provider2 = AzureOpenAIProvider(config2)
        assert provider2.is_available() is False
    
    def test_azure_provider_cost_estimation(self):
        """Test Azure provider cost estimation."""
        config = {
            "api_key": "test",
            "endpoint": "https://test.azure.com",
            "deployment_name": "gpt-4",
        }
        provider = AzureOpenAIProvider(config)
        
        # Same pricing as OpenAI
        cost = provider.estimate_cost(1000, 500)
        expected = (1000 / 1000 * 0.03) + (500 / 1000 * 0.06)
        assert cost == expected
    
    def test_get_provider_with_azure(self):
        """Test factory function can create Azure provider."""
        config = {
            "azure_openai": {
                "api_key": "test",
                "endpoint": "https://test.azure.com",
                "deployment_name": "gpt-4",
            }
        }
        
        provider = get_provider(ProviderType.OPENAI, config)
        
        assert isinstance(provider, AzureOpenAIProvider)
        assert provider.deployment_name == "gpt-4"


class TestTranslationContext:
    """Test translation context management."""
    
    def test_framework_info_creation(self):
        """Test framework info can be created."""
        framework = FrameworkInfo(
            name="pytest",
            version="7.0.0",
            language="python",
            conventions={"naming": "test_*"},
            patterns={"fixture": "@pytest.fixture"},
        )
        
        assert framework.name == "pytest"
        assert framework.version == "7.0.0"
        assert framework.language == "python"
        assert "naming" in framework.conventions
    
    def test_translation_pattern_creation(self):
        """Test translation pattern can be created."""
        pattern = TranslationPattern(
            source_pattern="@Test",
            target_pattern="def test_",
            description="JUnit to pytest",
            source_framework="junit",
            target_framework="pytest",
            confidence=0.95,
        )
        
        assert pattern.source_pattern == "@Test"
        assert pattern.target_pattern == "def test_"
        assert pattern.confidence == 0.95
    
    def test_translation_context_creation(self):
        """Test translation context can be created."""
        base_context = AIExecutionContext(task_type=TaskType.TEST_MIGRATION)
        source_fw = FrameworkInfo(name="junit", language="java")
        target_fw = FrameworkInfo(name="pytest", language="python")
        
        context = TranslationContext(
            execution_context=base_context,
            source_framework=source_fw,
            target_framework=target_fw,
            preserve_comments=True,
            preserve_structure=True,
        )
        
        assert context.source_framework.name == "junit"
        assert context.target_framework.name == "pytest"
        assert context.preserve_comments is True
    
    def test_translation_context_add_pattern(self):
        """Test adding patterns to translation context."""
        base_context = AIExecutionContext(task_type=TaskType.TEST_MIGRATION)
        source_fw = FrameworkInfo(name="junit", language="java")
        target_fw = FrameworkInfo(name="pytest", language="python")
        
        context = TranslationContext(
            execution_context=base_context,
            source_framework=source_fw,
            target_framework=target_fw,
        )
        
        pattern = TranslationPattern(
            source_pattern="@Before",
            target_pattern="@pytest.fixture",
            description="Setup method",
            source_framework="junit",
            target_framework="pytest",
        )
        
        context.add_pattern(pattern)
        
        assert len(context.custom_patterns) == 1
        assert context.custom_patterns[0].source_pattern == "@Before"
    
    def test_translation_context_record_translation(self):
        """Test recording translation history."""
        base_context = AIExecutionContext(task_type=TaskType.TEST_MIGRATION)
        source_fw = FrameworkInfo(name="junit", language="java")
        target_fw = FrameworkInfo(name="pytest", language="python")
        
        context = TranslationContext(
            execution_context=base_context,
            source_framework=source_fw,
            target_framework=target_fw,
        )
        
        context.record_translation(
            source_code="@Test public void test() {}",
            translated_code="def test_example(): pass",
            success=True,
            warnings=["Manual review recommended"],
        )
        
        assert len(context.previous_translations) == 1
        assert context.previous_translations[0]["success"] is True
        assert len(context.previous_translations[0]["warnings"]) == 1
    
    def test_translation_context_to_dict(self):
        """Test converting translation context to dict."""
        base_context = AIExecutionContext(task_type=TaskType.TEST_MIGRATION)
        source_fw = FrameworkInfo(name="junit", language="java")
        target_fw = FrameworkInfo(name="pytest", language="python")
        
        context = TranslationContext(
            execution_context=base_context,
            source_framework=source_fw,
            target_framework=target_fw,
            source_file_path=Path("tests/TestExample.java"),
            target_file_path=Path("tests/test_example.py"),
        )
        
        data = context.to_dict()
        
        assert data["source_framework"]["name"] == "junit"
        assert data["target_framework"]["name"] == "pytest"
        assert "TestExample.java" in data["source_file"]
        assert "test_example.py" in data["target_file"]


class TestTranslationContextManager:
    """Test translation context manager."""
    
    def test_context_manager_initialization(self, tmp_path):
        """Test context manager can be initialized."""
        manager = TranslationContextManager(storage_path=tmp_path)
        
        assert manager.storage_path == tmp_path
        assert manager.storage_path.exists()
    
    def test_create_context(self, tmp_path):
        """Test creating a translation context."""
        manager = TranslationContextManager(storage_path=tmp_path)
        
        context = manager.create_context(
            source_framework="junit",
            target_framework="pytest",
            source_language="java",
            target_language="python",
            preserve_comments=True,
        )
        
        assert context.source_framework.name == "junit"
        assert context.target_framework.name == "pytest"
        assert context.source_framework.language == "java"
        assert context.target_framework.language == "python"
        assert context.preserve_comments is True
    
    def test_add_pattern_to_library(self, tmp_path):
        """Test adding patterns to library."""
        manager = TranslationContextManager(storage_path=tmp_path)
        
        pattern = TranslationPattern(
            source_pattern="@Test",
            target_pattern="def test_",
            description="Test annotation",
            source_framework="junit",
            target_framework="pytest",
        )
        
        manager.add_pattern_to_library("junit", "pytest", pattern)
        
        patterns = manager.get_patterns("junit", "pytest")
        assert len(patterns) == 1
        assert patterns[0].source_pattern == "@Test"
    
    def test_save_and_load_context(self, tmp_path):
        """Test saving and loading contexts."""
        manager = TranslationContextManager(storage_path=tmp_path)
        
        # Create context
        context = manager.create_context(
            source_framework="junit",
            target_framework="pytest",
        )
        
        pattern = TranslationPattern(
            source_pattern="@Before",
            target_pattern="@pytest.fixture",
            description="Setup",
            source_framework="junit",
            target_framework="pytest",
        )
        context.add_pattern(pattern)
        
        # Save
        manager.save_context(context, "junit_to_pytest")
        
        # Load
        loaded = manager.load_context("junit_to_pytest")
        
        assert loaded.source_framework.name == "junit"
        assert loaded.target_framework.name == "pytest"
        assert len(loaded.custom_patterns) == 1
        assert loaded.custom_patterns[0].source_pattern == "@Before"


class TestCommonPatterns:
    """Test pre-defined common patterns."""
    
    def test_get_junit_to_pytest_patterns(self):
        """Test getting JUnit to pytest patterns."""
        patterns = get_common_patterns("junit", "pytest")
        
        assert len(patterns) > 0
        
        # Check for @Test pattern
        test_patterns = [p for p in patterns if "@Test" in p.source_pattern]
        assert len(test_patterns) > 0
    
    def test_get_selenium_to_playwright_patterns(self):
        """Test getting Selenium to Playwright patterns."""
        patterns = get_common_patterns("selenium_java", "playwright")
        
        assert len(patterns) > 0
        
        # Check for WebDriver pattern
        driver_patterns = [p for p in patterns if "WebDriver" in p.source_pattern]
        assert len(driver_patterns) > 0
    
    def test_get_unknown_framework_patterns(self):
        """Test getting patterns for unknown framework pair."""
        patterns = get_common_patterns("unknown", "framework")
        
        assert len(patterns) == 0  # Should return empty list


class TestTokenUsageTracking:
    """Test token usage tracking."""
    
    def test_token_usage_creation(self):
        """Test creating token usage object."""
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
    
    def test_token_usage_cost_estimate(self):
        """Test token usage cost estimation."""
        usage = TokenUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
        )
        
        cost = usage.cost_estimate
        
        # Default estimation
        expected = (1000 * 0.00001) + (500 * 0.00003)
        assert cost == expected


class TestResponseParsingValidation:
    """Test response parsing and validation."""
    
    def test_ai_response_creation(self):
        """Test creating AI response."""
        response = AIResponse(
            content="Test response",
            provider=ProviderType.OPENAI,
            model="gpt-4",
            token_usage=TokenUsage(100, 50, 150),
            cost=0.005,
            latency=1.5,
            status=ExecutionStatus.COMPLETED,
        )
        
        assert response.content == "Test response"
        assert response.provider == ProviderType.OPENAI
        assert response.token_usage.total_tokens == 150
        assert response.cost == 0.005
    
    def test_ai_response_to_dict(self):
        """Test converting AI response to dict."""
        response = AIResponse(
            content="Test",
            provider=ProviderType.OPENAI,
            model="gpt-4",
            token_usage=TokenUsage(100, 50, 150),
            cost=0.005,
        )
        
        data = response.to_dict()
        
        assert data["content"] == "Test"
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-4"
        assert data["token_usage"]["total_tokens"] == 150
        assert data["cost"] == 0.005
    
    def test_ai_message_creation(self):
        """Test creating AI message."""
        message = AIMessage(
            role="user",
            content="Test message",
            name="test_user",
        )
        
        assert message.role == "user"
        assert message.content == "Test message"
        assert message.name == "test_user"
    
    def test_ai_message_to_dict(self):
        """Test converting AI message to dict."""
        message = AIMessage(
            role="system",
            content="You are a helpful assistant",
        )
        
        data = message.to_dict()
        
        assert data["role"] == "system"
        assert data["content"] == "You are a helpful assistant"


class TestPromptTemplateSystem:
    """Test prompt engineering templates."""
    
    def test_prompt_renderer_initialization(self):
        """Test prompt renderer can be initialized."""
        renderer = PromptRenderer()
        
        assert renderer is not None
    
    def test_prompt_renderer_render_simple(self):
        """Test rendering simple template."""
        renderer = PromptRenderer()
        
        from core.ai.models import PromptTemplate
        
        template = PromptTemplate(
            template_id="test",
            version="v1",
            description="Test template",
            system_prompt="You are a test generator",
            user_prompt_template="Generate tests for: {{ code }}",
        )
        
        result = renderer.render(template, {"code": "def add(a, b): return a + b"})
        
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are a test generator"
        assert "def add(a, b): return a + b" in result[1]["content"]
    
    def test_prompt_registry_initialization(self):
        """Test prompt registry can be initialized."""
        registry = PromptRegistry()
        
        assert registry is not None


class TestModelSelection:
    """Test AI model selection and routing."""
    
    def test_model_config_creation(self):
        """Test creating model config."""
        config = ModelConfig(
            model="gpt-4",
            temperature=0.7,
            max_tokens=2000,
            top_p=0.9,
        )
        
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 2000
        assert config.top_p == 0.9
    
    def test_provider_selection_via_context(self):
        """Test provider can be selected via context."""
        context = AIExecutionContext(
            task_type=TaskType.TEST_GENERATION,
            provider=ProviderType.OPENAI,
            allow_external_ai=True,
        )
        
        assert context.provider == ProviderType.OPENAI
        assert context.allow_external_ai is True


class TestEndToEndIntegration:
    """Test end-to-end integration scenarios."""
    
    def test_translation_workflow(self, tmp_path):
        """Test complete translation workflow."""
        # 1. Create translation context
        manager = TranslationContextManager(storage_path=tmp_path)
        context = manager.create_context(
            source_framework="junit",
            target_framework="pytest",
        )
        
        # 2. Add custom patterns
        pattern = TranslationPattern(
            source_pattern="@Test",
            target_pattern="def test_",
            description="Test method",
            source_framework="junit",
            target_framework="pytest",
        )
        context.add_pattern(pattern)
        
        # 3. Record translation
        context.record_translation(
            source_code="@Test void test() {}",
            translated_code="def test_example(): pass",
            success=True,
        )
        
        # 4. Save context
        manager.save_context(context, "test_workflow")
        
        # 5. Verify saved
        loaded = manager.load_context("test_workflow")
        assert loaded.source_framework.name == "junit"
        assert len(loaded.custom_patterns) == 1
    
    def test_azure_provider_in_workflow(self):
        """Test Azure provider can be used in workflow."""
        config = {
            "azure_openai": {
                "api_key": "test",
                "endpoint": "https://test.azure.com",
                "deployment_name": "gpt-4",
            }
        }
        
        # Get provider
        provider = get_provider(ProviderType.OPENAI, config)
        
        # Verify it's Azure
        assert isinstance(provider, AzureOpenAIProvider)
        assert provider.is_available()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
