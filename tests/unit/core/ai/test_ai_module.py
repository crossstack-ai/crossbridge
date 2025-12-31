"""
Comprehensive unit tests for CrossBridge AI Module.

Tests all components with mocked AI providers (public and on-prem).
"""

import json
import pytest
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock, MagicMock, patch, PropertyMock

from core.ai.base import (
    AISkill,
    LLMProvider,
    ProviderError,
    RateLimitError,
    AuthenticationError,
)
from core.ai.models import (
    AIExecutionContext,
    AIMessage,
    AIResponse,
    AuditEntry,
    CreditBalance,
    ExecutionStatus,
    ModelConfig,
    PromptTemplate,
    ProviderType,
    SafetyLevel,
    TaskType,
    TokenUsage,
)
from core.ai.providers import (
    OpenAIProvider,
    AnthropicProvider,
    VLLMProvider,
    OllamaProvider,
    get_provider,
)
from core.ai.prompts import PromptRegistry, PromptRenderer
from core.ai.skills import (
    FlakyAnalyzer,
    TestGenerator,
    TestMigrator,
    CoverageReasoner,
    RootCauseAnalyzer,
)
from core.ai.orchestrator import (
    AIOrchestrator,
    ExecutionPolicy,
    ProviderSelector,
)
from core.ai.governance import (
    CostTracker,
    AuditLog,
    CreditManager,
    SafetyValidator,
)


# Mock Provider Implementations

class MockOpenAIProvider(LLMProvider):
    """Mock OpenAI provider for testing."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.call_count = 0
        self.should_fail = False
        self.fail_with = None
    
    def complete(self, *, messages, model_config, context):
        self.call_count += 1
        
        if self.should_fail:
            if self.fail_with == "rate_limit":
                raise RateLimitError("Rate limit exceeded")
            elif self.fail_with == "auth":
                raise AuthenticationError("Invalid API key")
            else:
                raise ProviderError("Provider error")
        
        # Generate mock response based on task
        content = self._generate_mock_response(messages, context)
        
        return AIResponse(
            content=content,
            provider=ProviderType.OPENAI,
            model=model_config.model,
            execution_id=context.execution_id,
            token_usage=TokenUsage(
                prompt_tokens=100,
                completion_tokens=200,
                total_tokens=300,
            ),
            cost=0.001,
            latency=0.5,
            status=ExecutionStatus.COMPLETED,
        )
    
    def _generate_mock_response(self, messages, context):
        """Generate appropriate mock response based on task type."""
        if context.task_type == TaskType.FLAKY_ANALYSIS:
            return json.dumps({
                "is_flaky": True,
                "confidence": 0.85,
                "flaky_score": 0.75,
                "explanation": "Test shows intermittent failures with timeout errors",
                "root_causes": ["Network latency", "Race condition"],
                "recommendations": ["Add retry logic", "Increase timeout"],
            })
        elif context.task_type == TaskType.TEST_GENERATION:
            return """```python
def test_calculate_discount():
    assert calculate_discount(100, 10) == 90
    
def test_calculate_discount_negative():
    with pytest.raises(ValueError):
        calculate_discount(-100, 10)
```"""
        elif context.task_type == TaskType.TEST_MIGRATION:
            return json.dumps({
                "migrated_code": "# Migrated Playwright code",
                "changes": ["Updated imports", "Changed selectors"],
                "warnings": [],
                "confidence": 0.9,
            })
        else:
            return "Mock AI response"
    
    def supports_tools(self):
        return True
    
    def supports_streaming(self):
        return True
    
    def name(self):
        return ProviderType.OPENAI
    
    def is_available(self):
        return True
    
    def estimate_cost(self, prompt_tokens, completion_tokens):
        return (prompt_tokens * 0.00003) + (completion_tokens * 0.00006)


class MockVLLMProvider(LLMProvider):
    """Mock vLLM provider for testing (on-prem)."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.call_count = 0
    
    def complete(self, *, messages, model_config, context):
        self.call_count += 1
        
        # Simulate slower on-prem response
        time.sleep(0.1)
        
        return AIResponse(
            content=json.dumps({"result": "Mock vLLM response"}),
            provider=ProviderType.VLLM,
            model=model_config.model,
            execution_id=context.execution_id,
            token_usage=TokenUsage(
                prompt_tokens=150,
                completion_tokens=250,
                total_tokens=400,
            ),
            cost=0.0,  # On-prem has no cost
            latency=0.8,
            status=ExecutionStatus.COMPLETED,
        )
    
    def supports_tools(self):
        return True
    
    def supports_streaming(self):
        return True
    
    def name(self):
        return ProviderType.VLLM
    
    def is_available(self):
        return True
    
    def estimate_cost(self, prompt_tokens, completion_tokens):
        return 0.0  # No cost for self-hosted


# Test Fixtures

@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage directory."""
    storage = tmp_path / "ai_test"
    storage.mkdir()
    return storage


@pytest.fixture
def mock_openai_provider():
    """Create mock OpenAI provider."""
    return MockOpenAIProvider()


@pytest.fixture
def mock_vllm_provider():
    """Create mock vLLM provider."""
    return MockVLLMProvider()


@pytest.fixture
def execution_context():
    """Create test execution context."""
    return AIExecutionContext(
        task_type=TaskType.FLAKY_ANALYSIS,
        user="test_user",
        project_id="test_project",
        allow_external_ai=True,  # Allow public AI services like OpenAI
        allow_self_hosted=True,
        max_cost=1.0,
    )


@pytest.fixture
def prompt_template(tmp_path):
    """Create test prompt template."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    
    template_content = """id: test_template
version: v1
description: Test template

system_prompt: You are a test assistant.

user_prompt: |
  Analyze: {{ input_data }}

input_schema:
  required:
    - input_data

output_schema:
  result:
    type: string

model_config:
  model: gpt-4o-mini
  temperature: 0.3
  max_tokens: 1024
"""
    
    template_file = templates_dir / "test_template_v1.yaml"
    template_file.write_text(template_content)
    
    return templates_dir


# Test Models

class TestModels:
    """Test AI data models."""
    
    def test_token_usage(self):
        """Test TokenUsage model."""
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
        )
        
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 200
        assert usage.total_tokens == 300
        assert usage.cost_estimate > 0
    
    def test_model_config(self):
        """Test ModelConfig."""
        config = ModelConfig(
            model="gpt-4",
            temperature=0.7,
            max_tokens=2048,
        )
        
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
    
    def test_execution_context(self):
        """Test AIExecutionContext."""
        context = AIExecutionContext(
            task_type=TaskType.TEST_GENERATION,
            user="john",
            project_id="proj1",
            max_cost=0.5,
        )
        
        assert context.task_type == TaskType.TEST_GENERATION
        assert context.user == "john"
        assert context.max_cost == 0.5
        
        context.start()
        assert context.started_at is not None
        
        context.complete()
        assert context.completed_at is not None
        assert context.duration > 0
    
    def test_ai_response(self):
        """Test AIResponse model."""
        response = AIResponse(
            content="Test response",
            provider=ProviderType.OPENAI,
            model="gpt-4",
            token_usage=TokenUsage(100, 200, 300),
            cost=0.01,
            latency=1.5,
        )
        
        assert response.content == "Test response"
        assert response.provider == ProviderType.OPENAI
        assert response.cost == 0.01
        
        data = response.to_dict()
        assert "content" in data
        assert "provider" in data
        assert "cost" in data
    
    def test_credit_balance(self):
        """Test CreditBalance model."""
        balance = CreditBalance(
            user_id="user1",
            total_credits=100.0,
            used_credits=30.0,
            daily_limit=10.0,
        )
        
        assert balance.available_credits == 70.0
        assert not balance.is_exhausted
        assert balance.can_consume(5.0)
        assert not balance.can_consume(15.0)  # Exceeds daily limit
        
        balance.consume(5.0)
        assert balance.used_credits == 35.0
        assert balance.daily_used == 5.0


# Test Providers

class TestProviders:
    """Test AI provider implementations."""
    
    def test_mock_openai_provider(self, mock_openai_provider, execution_context):
        """Test mock OpenAI provider."""
        messages = [AIMessage(role="user", content="Test")]
        config = ModelConfig(model="gpt-4")
        
        response = mock_openai_provider.complete(
            messages=messages,
            model_config=config,
            context=execution_context,
        )
        
        assert response.provider == ProviderType.OPENAI
        assert response.status == ExecutionStatus.COMPLETED
        assert response.token_usage.total_tokens > 0
        assert response.cost > 0
        assert mock_openai_provider.call_count == 1
    
    def test_mock_vllm_provider(self, mock_vllm_provider, execution_context):
        """Test mock vLLM provider (on-prem)."""
        messages = [AIMessage(role="user", content="Test")]
        config = ModelConfig(model="deepseek-coder")
        
        response = mock_vllm_provider.complete(
            messages=messages,
            model_config=config,
            context=execution_context,
        )
        
        assert response.provider == ProviderType.VLLM
        assert response.cost == 0.0  # On-prem has no cost
        assert mock_vllm_provider.call_count == 1
    
    def test_provider_rate_limit(self, mock_openai_provider, execution_context):
        """Test provider rate limiting."""
        mock_openai_provider.should_fail = True
        mock_openai_provider.fail_with = "rate_limit"
        
        messages = [AIMessage(role="user", content="Test")]
        config = ModelConfig(model="gpt-4")
        
        with pytest.raises(RateLimitError):
            mock_openai_provider.complete(
                messages=messages,
                model_config=config,
                context=execution_context,
            )
    
    def test_provider_authentication_error(self, mock_openai_provider, execution_context):
        """Test provider authentication failure."""
        mock_openai_provider.should_fail = True
        mock_openai_provider.fail_with = "auth"
        
        messages = [AIMessage(role="user", content="Test")]
        config = ModelConfig(model="gpt-4")
        
        with pytest.raises(AuthenticationError):
            mock_openai_provider.complete(
                messages=messages,
                model_config=config,
                context=execution_context,
            )
    
    def test_provider_supports_features(self, mock_openai_provider, mock_vllm_provider):
        """Test provider feature support."""
        assert mock_openai_provider.supports_tools()
        assert mock_openai_provider.supports_streaming()
        assert mock_vllm_provider.supports_tools()
    
    def test_provider_cost_estimation(self, mock_openai_provider, mock_vllm_provider):
        """Test cost estimation."""
        openai_cost = mock_openai_provider.estimate_cost(1000, 2000)
        vllm_cost = mock_vllm_provider.estimate_cost(1000, 2000)
        
        assert openai_cost > 0
        assert vllm_cost == 0.0  # On-prem is free


# Test Prompts

class TestPrompts:
    """Test prompt system."""
    
    def test_prompt_registry(self, prompt_template):
        """Test prompt registry."""
        registry = PromptRegistry(templates_dir=prompt_template)
        
        templates = registry.list_templates()
        assert "test_template" in templates
        
        template = registry.get("test_template", "v1")
        assert template.template_id == "test_template"
        assert template.version == "v1"
    
    def test_prompt_renderer(self, prompt_template):
        """Test prompt rendering."""
        registry = PromptRegistry(templates_dir=prompt_template)
        template = registry.get("test_template", "v1")
        
        renderer = PromptRenderer()
        messages = renderer.render(
            template,
            {"input_data": "Test data"}
        )
        
        assert len(messages) == 2  # System + user
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Test data" in messages[1]["content"]
    
    def test_prompt_validation(self, prompt_template):
        """Test prompt input validation."""
        registry = PromptRegistry(templates_dir=prompt_template)
        template = registry.get("test_template", "v1")
        
        renderer = PromptRenderer()
        
        # Missing required input
        with pytest.raises(ValueError):
            renderer.render(template, {})


# Test Skills

class TestSkills:
    """Test AI skills."""
    
    def test_flaky_analyzer(self):
        """Test FlakyAnalyzer skill."""
        analyzer = FlakyAnalyzer()
        
        # Test input preparation
        inputs = analyzer.prepare_inputs(
            test_name="test_login",
            test_file="tests/test_auth.py",
            execution_history=[
                {"status": "passed", "duration": 0.5},
                {"status": "failed", "duration": 0.6, "error": "Timeout"},
            ]
        )
        
        assert "test_name" in inputs
        assert "execution_history" in inputs
        assert "execution_count" in inputs
        
        # Test response parsing
        mock_response = AIResponse(
            content=json.dumps({
                "is_flaky": True,
                "confidence": 0.85,
                "flaky_score": 0.75,
                "explanation": "Test is flaky",
                "root_causes": ["timeout"],
                "recommendations": ["fix"],
            }),
            provider=ProviderType.OPENAI,
            model="gpt-4",
        )
        
        parsed = analyzer.parse_response(mock_response)
        
        assert parsed["is_flaky"] is True
        assert parsed["confidence"] == 0.85
        assert analyzer.validate_output(parsed)
    
    def test_test_generator(self):
        """Test TestGenerator skill."""
        generator = TestGenerator()
        
        inputs = generator.prepare_inputs(
            source_file="utils.py",
            source_code="def add(a, b): return a + b",
            language="python",
            test_framework="pytest",
        )
        
        assert "source_file" in inputs
        assert "source_code" in inputs
        
        mock_response = AIResponse(
            content="```python\ndef test_add():\n    assert add(1, 2) == 3\n```",
            provider=ProviderType.OPENAI,
            model="gpt-4",
        )
        
        parsed = generator.parse_response(mock_response)
        
        assert "test_code" in parsed
        assert "def test_add()" in parsed["test_code"]
        assert generator.validate_output(parsed)
    
    def test_test_migrator(self):
        """Test TestMigrator skill."""
        migrator = TestMigrator()
        
        inputs = migrator.prepare_inputs(
            source_framework="Selenium",
            target_framework="Playwright",
            language="python",
            source_test_code="# Selenium test",
        )
        
        assert "source_framework" in inputs
        assert "target_framework" in inputs
        
        mock_response = AIResponse(
            content=json.dumps({
                "migrated_code": "# Playwright test",
                "changes": ["Updated imports"],
                "warnings": [],
                "confidence": 0.9,
            }),
            provider=ProviderType.OPENAI,
            model="gpt-4",
        )
        
        parsed = migrator.parse_response(mock_response)
        
        assert "migrated_code" in parsed
        assert migrator.validate_output(parsed)
    
    def test_coverage_reasoner(self):
        """Test CoverageReasoner skill."""
        reasoner = CoverageReasoner()
        
        inputs = reasoner.prepare_inputs(
            source_file="payment.py",
            source_code="def process_payment(): pass",
            language="python",
        )
        
        assert "source_file" in inputs
    
    def test_root_cause_analyzer(self):
        """Test RootCauseAnalyzer skill."""
        analyzer = RootCauseAnalyzer()
        
        inputs = analyzer.prepare_inputs(
            test_name="test_checkout",
            test_file="tests/test_checkout.py",
            failure_info="Assertion failed",
        )
        
        assert "test_name" in inputs
        assert "failure_info" in inputs


# Test Governance

class TestGovernance:
    """Test governance components."""
    
    def test_cost_tracker(self, temp_storage, execution_context):
        """Test cost tracking."""
        tracker = CostTracker(storage_path=temp_storage)
        
        response = AIResponse(
            content="Test",
            provider=ProviderType.OPENAI,
            model="gpt-4",
            cost=0.01,
        )
        
        initial_cost = tracker.get_total_cost()
        tracker.record_cost(0.01, execution_context, response)
        
        assert tracker.get_total_cost() == initial_cost + 0.01
        assert tracker.get_daily_cost() == 0.01
        
        summary = tracker.get_cost_summary()
        assert summary["total"] >= 0.01
        assert summary["today"] == 0.01
    
    def test_cost_budget_enforcement(self, temp_storage, execution_context):
        """Test budget enforcement."""
        tracker = CostTracker(storage_path=temp_storage)
        
        execution_context.max_cost = 0.01
        
        # Should pass
        assert tracker.check_budget(execution_context, 0.005)
        
        # Should fail
        assert not tracker.check_budget(execution_context, 0.02)
        
        with pytest.raises(Exception):  # CostLimitExceededError
            tracker.enforce_budget(execution_context, 0.02)
    
    def test_audit_log(self, temp_storage, execution_context):
        """Test audit logging."""
        audit = AuditLog(storage_path=temp_storage)
        
        response = AIResponse(
            content="Test",
            provider=ProviderType.OPENAI,
            model="gpt-4",
            execution_id=execution_context.execution_id,
            cost=0.01,
            latency=1.0,
        )
        
        audit.log(execution_context, response, "v1")
        
        # Query logs
        entries = audit.query(
            user="test_user",
            project_id="test_project",
        )
        
        assert len(entries) >= 1
        assert any(e.execution_id == execution_context.execution_id for e in entries)
    
    def test_audit_usage_stats(self, temp_storage, execution_context):
        """Test usage statistics."""
        audit = AuditLog(storage_path=temp_storage)
        
        # Log multiple operations
        for i in range(3):
            response = AIResponse(
                content="Test",
                provider=ProviderType.OPENAI,
                model="gpt-4",
                cost=0.01,
                latency=1.0,
                token_usage=TokenUsage(100, 200, 300),
            )
            audit.log(execution_context, response, "v1")
        
        stats = audit.get_usage_stats()
        
        assert stats["total_operations"] >= 3
        assert stats["total_cost"] >= 0.03
        assert stats["total_tokens"] >= 900
    
    def test_credit_manager(self, temp_storage):
        """Test credit management."""
        manager = CreditManager(storage_path=temp_storage)
        
        # Add credits
        manager.add_credits("user1", 10.0, "proj1")
        
        balance = manager.get_balance("user1", "proj1")
        assert balance.available_credits == 10.0
        
        # Consume credits
        manager.consume_credits("user1", 2.0, "proj1")
        
        balance = manager.get_balance("user1", "proj1")
        assert balance.available_credits == 8.0
        assert balance.used_credits == 2.0
    
    def test_credit_exhaustion(self, temp_storage):
        """Test credit exhaustion."""
        manager = CreditManager(storage_path=temp_storage)
        
        manager.add_credits("user1", 1.0)
        
        # Should fail - insufficient credits
        with pytest.raises(Exception):  # CreditExhaustedError
            manager.consume_credits("user1", 2.0)
    
    def test_safety_validator(self, execution_context):
        """Test safety validation."""
        from core.ai.base import SafetyViolationError
        from core.ai.governance import SafetyValidator
        
        validator = SafetyValidator(SafetyLevel.STRICT)
        
        # Test input validation - should detect secrets (contains "password" keyword + "sk-" pattern)
        with pytest.raises(SafetyViolationError):
            validator.validate_input(
                {"user_password": "my_password_sk-abc123"},  # Contains both keyword and pattern
                execution_context,
            )
        
        # Test output validation - should detect leaks
        response = AIResponse(
            content="Here's the API key: sk-abc123",
            provider=ProviderType.OPENAI,
            model="gpt-4",
        )
        
        with pytest.raises(SafetyViolationError):
            validator.validate_output(response, execution_context)


# Test Orchestrator

class TestOrchestrator:
    """Test AI orchestration."""
    
    def test_execution_policy(self):
        """Test execution policy."""
        policy = ExecutionPolicy({
            "allow_external_ai": False,
            "allow_self_hosted": True,
            "max_cost_per_operation": 0.5,
        })
        
        context = AIExecutionContext(
            allow_external_ai=False,
            max_cost=0.3,
        )
        
        # Should fail - external AI not allowed
        with pytest.raises(PermissionError):
            policy.validate(context, ProviderType.OPENAI)
        
        # Should pass - self-hosted allowed
        policy.validate(context, ProviderType.VLLM)
    
    def test_provider_selector(self):
        """Test provider selection."""
        selector = ProviderSelector({
            "provider_preferences": ["vllm", "ollama", "openai"]
        })
        
        context = AIExecutionContext(allow_self_hosted=True)
        
        # Mock available providers
        with patch("core.ai.orchestrator.get_available_providers") as mock_available:
            mock_available.return_value = [
                ProviderType.VLLM,
                ProviderType.OPENAI,
            ]
            
            selected = selector.select(context)
            assert selected == ProviderType.VLLM  # Preferred
    
    @patch("core.ai.orchestrator.get_available_providers")
    @patch("core.ai.orchestrator.get_provider")
    @patch("core.ai.orchestrator.get_prompt")
    def test_orchestrator_execute_skill(
        self,
        mock_get_prompt,
        mock_get_provider,
        mock_get_available_providers,
        temp_storage,
        execution_context,
        mock_openai_provider,
    ):
        """Test orchestrator skill execution."""
        # Setup mocks
        mock_get_available_providers.return_value = [ProviderType.OPENAI]
        mock_get_provider.return_value = mock_openai_provider
        
        mock_template = PromptTemplate(
            template_id="flaky_analysis",
            version="v1",
            description="Test",
            system_prompt="You are a test assistant.",
            user_prompt_template="Analyze: {{ test_name }}",
        )
        mock_get_prompt.return_value = mock_template
        
        # Create orchestrator
        orchestrator = AIOrchestrator(
            config={
                "policy": {"allow_self_hosted": True},
                "providers": {"openai": {"api_key": "test"}},
            },
            storage_path=temp_storage,
        )
        
        # Add credits for test user
        orchestrator.credit_manager.add_credits("test_user", 10.0, "test_project")
        
        # Execute skill
        analyzer = FlakyAnalyzer()
        
        result = orchestrator.execute_skill(
            skill=analyzer,
            inputs={
                "test_name": "test_login",
                "test_file": "tests/test_auth.py",
                "execution_history": [
                    {"status": "passed"},
                    {"status": "failed", "error": "Timeout"},
                ],
            },
            context=execution_context,
        )
        
        assert "is_flaky" in result
        assert mock_openai_provider.call_count == 1
    
    def test_orchestrator_cost_tracking(self, temp_storage):
        """Test orchestrator tracks costs."""
        orchestrator = AIOrchestrator(storage_path=temp_storage)
        
        summary = orchestrator.get_cost_summary()
        assert "total" in summary
        assert "today" in summary
    
    def test_orchestrator_usage_stats(self, temp_storage):
        """Test orchestrator usage statistics."""
        orchestrator = AIOrchestrator(storage_path=temp_storage)
        
        stats = orchestrator.get_usage_stats()
        assert "total_operations" in stats


# Integration Tests

class TestIntegration:
    """Integration tests across components."""
    
    @patch("core.ai.orchestrator.get_available_providers")
    @patch("core.ai.orchestrator.get_provider")
    @patch("core.ai.orchestrator.get_prompt")
    def test_end_to_end_flaky_analysis(
        self,
        mock_get_prompt,
        mock_get_provider,
        mock_get_available_providers,
        temp_storage,
        mock_openai_provider,
    ):
        """Test complete flaky analysis workflow."""
        # Setup
        mock_get_available_providers.return_value = [ProviderType.OPENAI]
        mock_get_provider.return_value = mock_openai_provider
        mock_template = PromptTemplate(
            template_id="flaky_analysis",
            version="v1",
            description="Flaky analysis",
            system_prompt="You are an expert.",
            user_prompt_template="Analyze test: {{ test_name }}",
        )
        mock_get_prompt.return_value = mock_template
        
        orchestrator = AIOrchestrator(storage_path=temp_storage)
        
        # Add credits
        orchestrator.credit_manager.add_credits("test_user", 10.0, "test_proj")
        
        # Execute
        analyzer = FlakyAnalyzer()
        context = AIExecutionContext(
            task_type=TaskType.FLAKY_ANALYSIS,  # Set task type for proper mocking
            user="test_user",
            project_id="test_proj",
            max_cost=0.5,
            allow_external_ai=True,  # Allow public AI
        )
        
        result = orchestrator.execute_skill(
            skill=analyzer,
            inputs={
                "test_name": "test_checkout",
                "test_file": "tests/e2e/test_checkout.py",
                "execution_history": [
                    {"status": "passed", "duration": 1.0},
                    {"status": "failed", "duration": 1.2, "error": "Timeout"},
                    {"status": "passed", "duration": 0.9},
                ],
            },
            context=context,
        )
        
        # Verify result
        assert result["is_flaky"] is True
        assert result["confidence"] > 0
        
        # Verify cost tracking
        assert orchestrator.cost_tracker.get_total_cost() > 0
        
        # Verify credits consumed
        balance = orchestrator.credit_manager.get_balance("test_user", "test_proj")
        assert balance.used_credits > 0
        
        # Verify audit log
        entries = orchestrator.audit_log.query(user="test_user")
        assert len(entries) > 0
    
    @patch("core.ai.orchestrator.get_provider")
    def test_multi_provider_fallback(
        self,
        mock_get_provider,
        temp_storage,
        mock_openai_provider,
        mock_vllm_provider,
    ):
        """Test fallback between providers."""
        call_count = {"count": 0}
        
        def provider_factory(provider_type, config):
            call_count["count"] += 1
            if provider_type == ProviderType.VLLM:
                return mock_vllm_provider
            return mock_openai_provider
        
        mock_get_provider.side_effect = provider_factory
        
        orchestrator = AIOrchestrator(
            config={
                "provider_preferences": ["vllm", "openai"],
            },
            storage_path=temp_storage,
        )
        
        # vLLM should be preferred
        with patch("core.ai.orchestrator.get_available_providers") as mock_available:
            mock_available.return_value = [ProviderType.VLLM, ProviderType.OPENAI]
            
            selector = ProviderSelector({"provider_preferences": ["vllm", "openai"]})
            context = AIExecutionContext(allow_self_hosted=True)
            
            selected = selector.select(context)
            assert selected == ProviderType.VLLM


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
