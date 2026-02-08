"""
AI License Management and Validation.

Handles AI service license validation, token tracking, and cost management
for CrossBridge AI features.
"""

import json
import os
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple

from pydantic import BaseModel, Field


class LicenseStatus(str, Enum):
    """AI license status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    INVALID = "invalid"
    NOT_FOUND = "not_found"


class LicenseTier(str, Enum):
    """AI license tier/plan."""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


class AILicense(BaseModel):
    """AI License model."""
    license_key: str = Field(..., description="License key")
    customer_id: str = Field(..., description="Customer/User ID")
    tier: LicenseTier = Field(default=LicenseTier.FREE, description="License tier")
    provider: str = Field(..., description="AI provider (openai, anthropic, azure)")
    model: str = Field(..., description="AI model name")
    status: LicenseStatus = Field(default=LicenseStatus.ACTIVE, description="License status")
    
    # Token limits
    monthly_token_limit: Optional[int] = Field(None, description="Monthly token limit (None = unlimited)")
    daily_token_limit: Optional[int] = Field(None, description="Daily token limit")
    
    # Usage tracking
    tokens_used_today: int = Field(default=0, description="Tokens used today")
    tokens_used_month: int = Field(default=0, description="Tokens used this month")
    last_used_date: Optional[str] = Field(None, description="Last usage date (YYYY-MM-DD)")
    last_reset_date: Optional[str] = Field(None, description="Last reset date (YYYY-MM-DD)")
    
    # Validity
    valid_from: str = Field(..., description="License valid from (YYYY-MM-DD)")
    valid_until: Optional[str] = Field(None, description="License valid until (YYYY-MM-DD, None = perpetual)")
    
    # Features
    features_enabled: Dict[str, bool] = Field(default_factory=dict, description="Feature flags")
    
    model_config = {"use_enum_values": True}


class AIUsageStats(BaseModel):
    """AI usage statistics."""
    total_tokens: int = Field(default=0, description="Total tokens used")
    prompt_tokens: int = Field(default=0, description="Prompt tokens")
    completion_tokens: int = Field(default=0, description="Completion tokens")
    total_cost: float = Field(default=0.0, description="Total cost in USD")
    requests_count: int = Field(default=0, description="Number of API requests")
    avg_tokens_per_request: float = Field(default=0.0, description="Average tokens per request")
    avg_cost_per_request: float = Field(default=0.0, description="Average cost per request")


class LicenseValidator:
    """AI License validator and manager."""
    
    def __init__(self, license_file: Optional[Path] = None):
        """
        Initialize license validator.
        
        Args:
            license_file: Path to license file. If None, uses default location.
        """
        if license_file is None:
            # Default location: ~/.crossbridge/ai_license.json
            home = Path.home()
            self.license_file = home / ".crossbridge" / "ai_license.json"
        else:
            self.license_file = Path(license_file)
        
        self.license_file.parent.mkdir(parents=True, exist_ok=True)
    
    def load_license(self) -> Optional[AILicense]:
        """
        Load license from file.
        
        Returns:
            AILicense if found, None otherwise
        """
        if not self.license_file.exists():
            return None
        
        try:
            with open(self.license_file, 'r') as f:
                data = json.load(f)
            return AILicense(**data)
        except Exception:
            return None
    
    def save_license(self, license: AILicense) -> None:
        """
        Save license to file.
        
        Args:
            license: License to save
        """
        with open(self.license_file, 'w') as f:
            json.dump(license.model_dump(), f, indent=2)
    
    def validate_license(self, provider: str, feature: str = "log_analysis") -> Tuple[bool, str, Optional[AILicense]]:
        """
        Validate AI license for a specific provider and feature.
        
        Args:
            provider: AI provider (openai, anthropic, azure, selfhosted)
            feature: Feature name (log_analysis, transformation, etc.)
        
        Returns:
            Tuple of (is_valid, message, license)
        """
        # Self-hosted AI doesn't require a license
        if provider.lower() == "selfhosted":
            return True, "Self-hosted AI - no license required", None
        
        license = self.load_license()
        
        # No license found
        if license is None:
            return False, "No AI license found. Please configure AI settings using 'crossbridge configure ai'", None
        
        # Check provider match
        if license.provider.lower() != provider.lower():
            return False, f"License is for {license.provider}, but {provider} provider requested", license
        
        # Check status
        if license.status != LicenseStatus.ACTIVE:
            return False, f"License status is {license.status}. Please contact support.", license
        
        # Check validity dates
        today = datetime.now().date()
        valid_from = datetime.strptime(license.valid_from, "%Y-%m-%d").date()
        
        if today < valid_from:
            return False, f"License is not yet valid. Valid from: {license.valid_from}", license
        
        if license.valid_until:
            valid_until = datetime.strptime(license.valid_until, "%Y-%m-%d").date()
            if today > valid_until:
                return False, f"License expired on {license.valid_until}", license
        
        # Check feature access
        if feature and not license.features_enabled.get(feature, False):
            return False, f"Feature '{feature}' is not enabled in your license tier ({license.tier})", license
        
        # Check token limits
        self._reset_usage_if_needed(license)
        
        if license.daily_token_limit and license.tokens_used_today >= license.daily_token_limit:
            return False, f"Daily token limit ({license.daily_token_limit:,}) exceeded. {license.tokens_used_today:,} tokens used today.", license
        
        if license.monthly_token_limit and license.tokens_used_month >= license.monthly_token_limit:
            return False, f"Monthly token limit ({license.monthly_token_limit:,}) exceeded. {license.tokens_used_month:,} tokens used this month.", license
        
        return True, "License valid", license
    
    def _reset_usage_if_needed(self, license: AILicense) -> None:
        """Reset daily/monthly usage counters if needed."""
        today = datetime.now().date()
        today_str = today.strftime("%Y-%m-%d")
        
        # Reset daily counter
        if license.last_used_date != today_str:
            license.tokens_used_today = 0
            license.last_used_date = today_str
        
        # Reset monthly counter (first day of month)
        if license.last_reset_date:
            last_reset = datetime.strptime(license.last_reset_date, "%Y-%m-%d").date()
            # If it's a new month, reset
            if today.month != last_reset.month or today.year != last_reset.year:
                license.tokens_used_month = 0
                license.last_reset_date = today_str
        else:
            # First time - set reset date
            license.last_reset_date = today_str
    
    def track_usage(self, tokens_used: int, cost: float) -> Tuple[bool, str]:
        """
        Track AI usage and update license.
        
        Args:
            tokens_used: Number of tokens consumed
            cost: Cost in USD
        
        Returns:
            Tuple of (success, message)
        """
        license = self.load_license()
        if not license:
            return False, "No license found"
        
        # Reset if needed
        self._reset_usage_if_needed(license)
        
        # Update usage
        license.tokens_used_today += tokens_used
        license.tokens_used_month += tokens_used
        license.last_used_date = datetime.now().strftime("%Y-%m-%d")
        
        # Save updated license
        self.save_license(license)
        
        # Check if limits exceeded
        remaining_daily = (license.daily_token_limit - license.tokens_used_today) if license.daily_token_limit else None
        remaining_monthly = (license.monthly_token_limit - license.tokens_used_month) if license.monthly_token_limit else None
        
        warnings = []
        if remaining_daily is not None and remaining_daily < 1000:
            warnings.append(f"Daily limit almost reached: {remaining_daily} tokens remaining")
        if remaining_monthly is not None and remaining_monthly < 10000:
            warnings.append(f"Monthly limit almost reached: {remaining_monthly} tokens remaining")
        
        if warnings:
            return True, " | ".join(warnings)
        
        return True, f"Usage tracked: {tokens_used:,} tokens, ${cost:.4f}"
    
    def get_usage_stats(self) -> Optional[AIUsageStats]:
        """Get current usage statistics."""
        license = self.load_license()
        if not license:
            return None
        
        # Calculate stats
        stats = AIUsageStats(
            total_tokens=license.tokens_used_month,
            requests_count=1,  # We don't track this separately yet
        )
        
        return stats
    
    def create_demo_license(
        self,
        customer_id: str,
        provider: str = "openai",
        model: str = "gpt-3.5-turbo",
        tier: LicenseTier = LicenseTier.BASIC,
        days_valid: int = 30
    ) -> AILicense:
        """
        Create a demo/test license.
        
        Args:
            customer_id: Customer ID
            provider: AI provider
            model: Model name
            tier: License tier
            days_valid: Number of days license is valid
        
        Returns:
            Created license
        """
        today = datetime.now().date()
        valid_until = today + timedelta(days=days_valid)
        
        # Set limits based on tier
        tier_limits = {
            LicenseTier.FREE: {"daily": 1000, "monthly": 10000},
            LicenseTier.BASIC: {"daily": 10000, "monthly": 100000},
            LicenseTier.PROFESSIONAL: {"daily": 50000, "monthly": 1000000},
            LicenseTier.ENTERPRISE: {"daily": None, "monthly": None},
            LicenseTier.UNLIMITED: {"daily": None, "monthly": None},
        }
        
        limits = tier_limits[tier]
        
        license = AILicense(
            license_key=f"CB-{customer_id.upper()[:4]}-{today.strftime('%Y%m')}-DEMO",
            customer_id=customer_id,
            tier=tier,
            provider=provider,
            model=model,
            status=LicenseStatus.ACTIVE,
            monthly_token_limit=limits["monthly"],
            daily_token_limit=limits["daily"],
            valid_from=today.strftime("%Y-%m-%d"),
            valid_until=valid_until.strftime("%Y-%m-%d"),
            features_enabled={
                "log_analysis": True,
                "transformation": tier in [LicenseTier.PROFESSIONAL, LicenseTier.ENTERPRISE, LicenseTier.UNLIMITED],
                "test_generation": tier in [LicenseTier.ENTERPRISE, LicenseTier.UNLIMITED],
            }
        )
        
        self.save_license(license)
        return license


def get_cost_estimate(provider: str, model: str, tokens: int) -> float:
    """
    Estimate cost for given provider, model, and token count.
    
    Args:
        provider: Provider name (openai, anthropic, azure)
        model: Model name
        tokens: Token count (total)
    
    Returns:
        Estimated cost in USD
    """
    # Cost per 1K tokens (rough estimates)
    pricing = {
        "openai": {
            "gpt-3.5-turbo": 0.0015,  # Average of input/output
            "gpt-4": 0.045,  # Average
            "gpt-4-turbo": 0.015,  # Average
            "gpt-4o": 0.005,  # Average
            "gpt-4o-mini": 0.0003,  # Average
        },
        "anthropic": {
            "claude-3-sonnet-20240229": 0.006,  # Average
            "claude-3-opus-20240229": 0.0375,  # Average
            "claude-3-haiku-20240307": 0.0005,  # Average
        },
        "azure": {
            "gpt-35-turbo": 0.0015,
            "gpt-4": 0.045,
        }
    }
    
    provider_pricing = pricing.get(provider.lower(), {})
    cost_per_1k = provider_pricing.get(model, 0.005)  # Default fallback
    
    return (tokens / 1000) * cost_per_1k


def format_cost_summary(
    provider: str,
    model: str,
    total_tokens: int,
    prompt_tokens: int,
    completion_tokens: int,
    total_cost: float,
    item_count: int = 0,
    item_type: str = "logs"
) -> str:
    """
    Format AI cost summary for display.
    
    Args:
        provider: Provider name
        model: Model name
        total_tokens: Total tokens used
        prompt_tokens: Prompt tokens
        completion_tokens: Completion tokens
        total_cost: Total cost
        item_count: Number of items processed
        item_type: Type of items (logs, files, tests)
    
    Returns:
        Formatted summary string
    """
    lines = [
        "╭─────────────────────────────────────────────────────────╮",
        "│            AI LOG ANALYSIS SUMMARY                      │",
        "╰─────────────────────────────────────────────────────────╯",
        "",
        "  AI Configuration:",
        f"  • Provider: {provider.title()}",
        f"  • Model: {model}",
        "",
        " AI Analysis Statistics:",
        f"  ✓ Total {item_type.title()} Analyzed: {item_count}",
        f"  ✓ AI-Enhanced Classifications: {item_count}",
        "",
        " Token Usage & Cost:",
        f"  • Prompt Tokens: {prompt_tokens:,}",
        f"  • Completion Tokens: {completion_tokens:,}",
        f"  • Total Tokens: {total_tokens:,}",
        f"  • Total Cost: ${total_cost:.4f}",
    ]
    
    if item_count > 0:
        avg_tokens = total_tokens / item_count
        avg_cost = total_cost / item_count
        lines.extend([
            f"  • Avg Tokens/Item: {avg_tokens:.0f}",
            f"  • Avg Cost/Item: ${avg_cost:.4f}",
        ])
    
    # Cost comparison
    if provider.lower() == "openai" and "gpt-3.5" in model.lower():
        gpt4_cost = total_cost * 30  # GPT-4 is ~30x more expensive
        savings = gpt4_cost - total_cost
        lines.extend([
            "",
            " Cost Savings:",
            f"  • Using {model}: ${total_cost:.4f}",
            f"  • Same with gpt-4: ~${gpt4_cost:.2f}",
            f"  • Savings: ~${savings:.2f} ({(savings/gpt4_cost*100):.0f}% reduction)",
        ])
    
    lines.append("╰─────────────────────────────────────────────────────────╯")
    
    return "\n".join(lines)
