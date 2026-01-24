#!/usr/bin/env python3
"""Quick test to verify model selection in AIConfig."""

from core.orchestration.models import AIConfig, AIMode


def test_model_defaults():
    """Test that AIConfig defaults to gpt-3.5-turbo."""
    print("\n=== Testing AIConfig Model Defaults ===\n")
    
    # Test 1: Default model
    config = AIConfig(
        mode=AIMode.PUBLIC_CLOUD,
        provider="openai",
        api_key="test-key"
    )
    print(f"✓ Default model: {config.model}")
    assert config.model == "gpt-3.5-turbo", f"Expected gpt-3.5-turbo but got {config.model}"
    
    # Test 2: Custom model
    config_custom = AIConfig(
        mode=AIMode.PUBLIC_CLOUD,
        provider="openai",
        api_key="test-key",
        model="gpt-4"
    )
    print(f"✓ Custom model: {config_custom.model}")
    assert config_custom.model == "gpt-4", f"Expected gpt-4 but got {config_custom.model}"
    
    # Test 3: Anthropic model
    config_anthropic = AIConfig(
        mode=AIMode.PUBLIC_CLOUD,
        provider="anthropic",
        api_key="test-key",
        model="claude-3-sonnet-20240229"
    )
    print(f"✓ Anthropic model: {config_anthropic.model}")
    assert config_anthropic.model == "claude-3-sonnet-20240229"
    
    print("\n✅ All AIConfig model tests passed!")
    print(f"\nDefault economical model: gpt-3.5-turbo")
    print("Available OpenAI models: gpt-3.5-turbo, gpt-4, gpt-4-turbo")
    print("Available Anthropic models: claude-3-sonnet-20240229, claude-3-opus-20240229")


if __name__ == "__main__":
    test_model_defaults()
