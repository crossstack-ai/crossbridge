"""
Unit tests for AI License Management.

Tests license validation, token tracking, cost calculation,
and usage limits with fake API keys.
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from core.ai.license import (
    AILicense,
    LicenseStatus,
    LicenseTier,
    LicenseValidator,
    get_cost_estimate,
    format_cost_summary,
    AIUsageStats
)


class TestAILicense:
    """Test AILicense model."""
    
    def test_create_license(self):
        """Test creating a basic license."""
        license = AILicense(
            license_key="TEST-KEY-001",
            customer_id="customer123",
            tier=LicenseTier.BASIC,
            provider="openai",
            model="gpt-3.5-turbo",
            status=LicenseStatus.ACTIVE,
            valid_from="2026-01-01",
            monthly_token_limit=100000,
            daily_token_limit=10000
        )
        
        assert license.license_key == "TEST-KEY-001"
        assert license.customer_id == "customer123"
        assert license.tier == LicenseTier.BASIC
        assert license.provider == "openai"
        assert license.status == LicenseStatus.ACTIVE
        assert license.monthly_token_limit == 100000
        assert license.daily_token_limit == 10000
    
    def test_license_with_features(self):
        """Test license with feature flags."""
        license = AILicense(
            license_key="TEST-KEY-002",
            customer_id="customer456",
            tier=LicenseTier.PROFESSIONAL,
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            status=LicenseStatus.ACTIVE,
            valid_from="2026-01-01",
            features_enabled={
                "log_analysis": True,
                "transformation": True,
                "test_generation": False
            }
        )
        
        assert license.features_enabled["log_analysis"] is True
        assert license.features_enabled["transformation"] is True
        assert license.features_enabled["test_generation"] is False
    
    def test_license_unlimited_tier(self):
        """Test unlimited tier license."""
        license = AILicense(
            license_key="TEST-KEY-UNLIMITED",
            customer_id="enterprise_customer",
            tier=LicenseTier.UNLIMITED,
            provider="openai",
            model="gpt-4",
            status=LicenseStatus.ACTIVE,
            valid_from="2026-01-01",
            monthly_token_limit=None,  # Unlimited
            daily_token_limit=None  # Unlimited
        )
        
        assert license.tier == LicenseTier.UNLIMITED
        assert license.monthly_token_limit is None
        assert license.daily_token_limit is None


class TestLicenseValidator:
    """Test LicenseValidator."""
    
    @pytest.fixture
    def temp_license_dir(self):
        """Create temporary directory for license files."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def validator(self, temp_license_dir):
        """Create validator with temp license file."""
        license_file = temp_license_dir / "test_license.json"
        return LicenseValidator(license_file=license_file)
    
    def test_create_demo_license(self, validator):
        """Test creating a demo license."""
        license = validator.create_demo_license(
            customer_id="test_user",
            provider="openai",
            model="gpt-3.5-turbo",
            tier=LicenseTier.BASIC,
            days_valid=30
        )
        
        assert license.customer_id == "test_user"
        assert license.provider == "openai"
        assert license.model == "gpt-3.5-turbo"
        assert license.tier == LicenseTier.BASIC
        assert license.status == LicenseStatus.ACTIVE
        
        # Check limits for BASIC tier
        assert license.daily_token_limit == 10000
        assert license.monthly_token_limit == 100000
        
        # Check features
        assert license.features_enabled["log_analysis"] is True
        assert license.features_enabled.get("transformation", False) is False
    
    def test_save_and_load_license(self, validator):
        """Test saving and loading license."""
        # Create license
        original = validator.create_demo_license(
            customer_id="save_test",
            tier=LicenseTier.PROFESSIONAL
        )
        
        # Load it back
        loaded = validator.load_license()
        
        assert loaded is not None
        assert loaded.customer_id == "save_test"
        assert loaded.tier == LicenseTier.PROFESSIONAL
        assert loaded.provider == original.provider
    
    def test_validate_active_license(self, validator):
        """Test validating an active license."""
        # Create active license
        validator.create_demo_license(
            customer_id="active_test",
            provider="openai",
            tier=LicenseTier.BASIC
        )
        
        # Validate
        is_valid, message, license = validator.validate_license("openai", "log_analysis")
        
        assert is_valid is True
        assert "valid" in message.lower()
        assert license is not None
        assert license.status == LicenseStatus.ACTIVE
    
    def test_validate_wrong_provider(self, validator):
        """Test validation fails for wrong provider."""
        # Create OpenAI license
        validator.create_demo_license(
            customer_id="provider_test",
            provider="openai"
        )
        
        # Try to validate for Anthropic
        is_valid, message, license = validator.validate_license("anthropic", "log_analysis")
        
        assert is_valid is False
        assert "openai" in message.lower()
        assert "anthropic" in message.lower()
    
    def test_validate_expired_license(self, validator, temp_license_dir):
        """Test validation fails for expired license."""
        # Create expired license manually
        today = datetime.now().date()
        expired_date = today - timedelta(days=10)
        
        license = AILicense(
            license_key="EXPIRED-KEY",
            customer_id="expired_test",
            tier=LicenseTier.BASIC,
            provider="openai",
            model="gpt-3.5-turbo",
            status=LicenseStatus.ACTIVE,
            valid_from="2025-01-01",
            valid_until=expired_date.strftime("%Y-%m-%d"),
            monthly_token_limit=100000,
            daily_token_limit=10000,
            features_enabled={"log_analysis": True}
        )
        
        validator.save_license(license)
        
        # Validate
        is_valid, message, _ = validator.validate_license("openai", "log_analysis")
        
        assert is_valid is False
        assert "expired" in message.lower()
    
    def test_validate_feature_not_enabled(self, validator):
        """Test validation fails for disabled feature."""
        # Create FREE tier license (transformation not enabled)
        validator.create_demo_license(
            customer_id="feature_test",
            tier=LicenseTier.FREE
        )
        
        # Try to use transformation feature
        is_valid, message, _ = validator.validate_license("openai", "transformation")
        
        assert is_valid is False
        assert "transformation" in message.lower()
        assert "not enabled" in message.lower()
    
    def test_validate_no_license(self, validator):
        """Test validation fails when no license exists."""
        # Don't create any license
        is_valid, message, license = validator.validate_license("openai", "log_analysis")
        
        assert is_valid is False
        assert "no" in message.lower() and "license" in message.lower()
        assert license is None
    
    def test_track_usage_daily_limit(self, validator):
        """Test tracking usage respects daily limits."""
        # Create license with low daily limit
        license = validator.create_demo_license(
            customer_id="daily_limit_test",
            tier=LicenseTier.FREE  # 1000 daily tokens
        )
        
        # Use 500 tokens
        success, message = validator.track_usage(500, 0.001)
        assert success is True
        
        # Check updated license
        license = validator.load_license()
        assert license.tokens_used_today == 500
        
        # Use another 600 tokens (total 1100, exceeds 1000 limit)
        validator.track_usage(600, 0.0012)
        
        # Validation should fail now
        is_valid, message, _ = validator.validate_license("openai", "log_analysis")
        assert is_valid is False
        assert "daily" in message.lower() and "limit" in message.lower()
    
    def test_track_usage_monthly_limit(self, validator):
        """Test tracking usage respects monthly limits."""
        # Create license with low monthly limit
        license = AILicense(
            license_key="MONTHLY-TEST",
            customer_id="monthly_limit_test",
            tier=LicenseTier.FREE,
            provider="openai",
            model="gpt-3.5-turbo",
            status=LicenseStatus.ACTIVE,
            valid_from="2026-01-01",
            monthly_token_limit=5000,  # Low limit
            daily_token_limit=2000,
            tokens_used_month=4500,  # Already used 4500
            features_enabled={"log_analysis": True}
        )
        validator.save_license(license)
        
        # Try to use 600 more tokens (total 5100, exceeds 5000)
        validator.track_usage(600, 0.0012)
        
        # Validation should fail
        is_valid, message, _ = validator.validate_license("openai", "log_analysis")
        assert is_valid is False
        assert "monthly" in message.lower() and "limit" in message.lower()
    
    def test_usage_reset_daily(self, validator):
        """Test daily usage counter resets."""
        license = validator.create_demo_license(
            customer_id="reset_test",
            tier=LicenseTier.BASIC
        )
        
        # Use some tokens
        validator.track_usage(100, 0.0002)
        
        # Manually set last used to yesterday
        license = validator.load_license()
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        license.last_used_date = yesterday
        license.tokens_used_today = 5000
        validator.save_license(license)
        
        # Track new usage (should reset counter first)
        validator.track_usage(100, 0.0002)
        
        # Check that counter was reset and now shows only new usage
        license = validator.load_license()
        assert license.tokens_used_today == 100  # Should be 100, not 5100
    
    def test_different_tiers(self, validator):
        """Test different license tiers have correct limits."""
        tiers_expected = {
            LicenseTier.FREE: (1000, 10000),
            LicenseTier.BASIC: (10000, 100000),
            LicenseTier.PROFESSIONAL: (50000, 1000000),
            LicenseTier.ENTERPRISE: (None, None),
            LicenseTier.UNLIMITED: (None, None),
        }
        
        for tier, (expected_daily, expected_monthly) in tiers_expected.items():
            license = validator.create_demo_license(
                customer_id=f"tier_test_{tier.value}",
                tier=tier
            )
            
            assert license.daily_token_limit == expected_daily
            assert license.monthly_token_limit == expected_monthly


class TestCostEstimation:
    """Test cost estimation functions."""
    
    def test_openai_gpt35_cost(self):
        """Test OpenAI GPT-3.5 cost estimation."""
        cost = get_cost_estimate("openai", "gpt-3.5-turbo", 10000)
        
        # Should be around $0.015 for 10K tokens
        assert 0.01 < cost < 0.02
    
    def test_openai_gpt4_cost(self):
        """Test OpenAI GPT-4 cost estimation."""
        cost = get_cost_estimate("openai", "gpt-4", 10000)
        
        # Should be much higher than GPT-3.5 (around $0.45)
        assert 0.4 < cost < 0.5
    
    def test_anthropic_claude_cost(self):
        """Test Anthropic Claude cost estimation."""
        cost = get_cost_estimate("anthropic", "claude-3-sonnet-20240229", 10000)
        
        # Should be around $0.06
        assert 0.05 < cost < 0.07
    
    def test_cost_scaling(self):
        """Test cost scales linearly with tokens."""
        cost_1k = get_cost_estimate("openai", "gpt-3.5-turbo", 1000)
        cost_10k = get_cost_estimate("openai", "gpt-3.5-turbo", 10000)
        
        # 10K should cost ~10x more than 1K
        assert abs(cost_10k / cost_1k - 10.0) < 0.1
    
    def test_unknown_model_fallback(self):
        """Test unknown models use fallback pricing."""
        cost = get_cost_estimate("unknown_provider", "unknown_model", 10000)
        
        # Should return some cost (fallback pricing)
        assert cost > 0


class TestCostSummaryFormatting:
    """Test cost summary formatting."""
    
    def test_format_basic_summary(self):
        """Test formatting basic cost summary."""
        summary = format_cost_summary(
            provider="openai",
            model="gpt-3.5-turbo",
            total_tokens=10000,
            prompt_tokens=7000,
            completion_tokens=3000,
            total_cost=0.015,
            item_count=5,
            item_type="logs"
        )
        
        assert "openai" in summary.lower()
        assert "gpt-3.5-turbo" in summary
        assert "10,000" in summary  # Formatted tokens
        assert "$0.015" in summary.lower()
        assert "5" in summary  # Item count
    
    def test_summary_with_cost_comparison(self):
        """Test summary includes cost comparison for GPT-3.5."""
        summary = format_cost_summary(
            provider="openai",
            model="gpt-3.5-turbo",
            total_tokens=10000,
            prompt_tokens=7000,
            completion_tokens=3000,
            total_cost=0.015,
            item_count=5
        )
        
        # Should include GPT-4 comparison
        assert "gpt-4" in summary.lower()
        assert "savings" in summary.lower()
    
    def test_summary_averages(self):
        """Test summary includes per-item averages."""
        summary = format_cost_summary(
            provider="openai",
            model="gpt-3.5-turbo",
            total_tokens=10000,
            prompt_tokens=7000,
            completion_tokens=3000,
            total_cost=0.020,
            item_count=10
        )
        
        # Should include averages
        assert "avg" in summary.lower()
        # 10000/10 = 1000 tokens per item
        assert "1000" in summary


class TestFakeAPIKeys:
    """Test with fake/invalid API keys to ensure proper validation."""
    
    @pytest.fixture
    def temp_license_dir(self):
        """Create temporary directory for license files."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_fake_openai_key_detection(self, temp_license_dir):
        """Test that fake OpenAI keys are properly handled."""
        validator = LicenseValidator(license_file=temp_license_dir / "fake.json")
        
        # Create license with fake key
        license = AILicense(
            license_key="FAKE-KEY-123",
            customer_id="sk-fake_api_key_123456789",  # Fake OpenAI format
            tier=LicenseTier.BASIC,
            provider="openai",
            model="gpt-3.5-turbo",
            status=LicenseStatus.ACTIVE,
            valid_from="2026-01-01",
            features_enabled={"log_analysis": True}
        )
        validator.save_license(license)
        
        # Validation should pass (we validate license, not API key)
        is_valid, message, _ = validator.validate_license("openai", "log_analysis")
        assert is_valid is True
        
        # Note: Actual API calls with fake keys would fail at provider level
        # This is intentional - license validation is separate from API key validation
    
    def test_fake_anthropic_key_detection(self, temp_license_dir):
        """Test that fake Anthropic keys are properly handled."""
        validator = LicenseValidator(license_file=temp_license_dir / "fake.json")
        
        # Create license with fake key
        license = AILicense(
            license_key="FAKE-KEY-456",
            customer_id="sk-ant-fake_key_abc123",  # Fake Anthropic format
            tier=LicenseTier.PROFESSIONAL,
            provider="anthropic",
            model="claude-3-sonnet-20240229",
            status=LicenseStatus.ACTIVE,
            valid_from="2026-01-01",
            features_enabled={"log_analysis": True, "transformation": True}
        )
        validator.save_license(license)
        
        # Validation should pass
        is_valid, message, _ = validator.validate_license("anthropic", "log_analysis")
        assert is_valid is True
    
    def test_empty_api_key(self, temp_license_dir):
        """Test handling of empty API keys."""
        validator = LicenseValidator(license_file=temp_license_dir / "empty.json")
        
        # Create license with empty customer_id (API key)
        license = AILicense(
            license_key="EMPTY-KEY",
            customer_id="",  # Empty
            tier=LicenseTier.FREE,
            provider="openai",
            model="gpt-3.5-turbo",
            status=LicenseStatus.ACTIVE,
            valid_from="2026-01-01",
            features_enabled={"log_analysis": True}
        )
        validator.save_license(license)
        
        # License validation should still pass
        # (empty key will fail at provider instantiation, not here)
        is_valid, _, _ = validator.validate_license("openai", "log_analysis")
        assert is_valid is True


class TestUsageStatistics:
    """Test usage statistics tracking."""
    
    @pytest.fixture
    def temp_license_dir(self):
        """Create temporary directory for license files."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_get_usage_stats(self, temp_license_dir):
        """Test getting usage statistics."""
        validator = LicenseValidator(license_file=temp_license_dir / "stats.json")
        
        # Create license and use some tokens
        validator.create_demo_license("stats_test", tier=LicenseTier.BASIC)
        validator.track_usage(5000, 0.01)
        
        # Get stats
        stats = validator.get_usage_stats()
        
        assert stats is not None
        assert stats.total_tokens == 5000
    
    def test_stats_no_license(self, temp_license_dir):
        """Test stats when no license exists."""
        validator = LicenseValidator(license_file=temp_license_dir / "none.json")
        
        stats = validator.get_usage_stats()
        assert stats is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
