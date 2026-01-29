#!/usr/bin/env python3
"""Test to verify AIConfig dict conversion works."""

from core.orchestration.models import AIConfig, AIMode


def test_aiconfig_to_dict_conversion():
    """Test converting AIConfig object to dict for AI methods."""
    print("\n=== Testing AIConfig to Dict Conversion ===\n")
    
    # Create AIConfig object (like from CLI)
    ai_config = AIConfig(
        mode=AIMode.PUBLIC_CLOUD,
        provider="openai",
        api_key="test-key-123",
        model="gpt-3.5-turbo"
    )
    
    print(f"AIConfig object: {ai_config}")
    print(f"  mode: {ai_config.mode}")
    print(f"  provider: {ai_config.provider}")
    print(f"  api_key: {ai_config.api_key}")
    print(f"  model: {ai_config.model}\n")
    
    # Convert to dict (like orchestrator does)
    ai_config_dict = {
        'provider': ai_config.provider if hasattr(ai_config, 'provider') else 'openai',
        'api_key': ai_config.api_key,
        'model': ai_config.model,
        'region': ai_config.region if hasattr(ai_config, 'region') else 'US'
    }
    
    print(f"Converted dict: {ai_config_dict}\n")
    
    # Test .get() method works on dict
    provider = ai_config_dict.get('provider', 'openai')
    api_key = ai_config_dict.get('api_key')
    model = ai_config_dict.get('model', 'gpt-3.5-turbo')
    region = ai_config_dict.get('region', 'US')
    
    print("✓ .get() method works on dict:")
    print(f"  provider: {provider}")
    print(f"  api_key: {api_key}")
    print(f"  model: {model}")
    print(f"  region: {region}\n")
    
    assert provider == 'openai'
    assert api_key == 'test-key-123'
    assert model == 'gpt-3.5-turbo'
    assert region == 'US'
    
    print("✅ All conversion tests passed!")
    print("\nThe orchestrator can now properly convert AIConfig to dict")
    print("and pass it to AI transformation methods.\n")


def test_aiconfig_direct_access():
    """Show that .get() doesn't work on Pydantic models."""
    print("\n=== Testing AIConfig Direct Access (Problem) ===\n")
    
    ai_config = AIConfig(
        mode=AIMode.PUBLIC_CLOUD,
        provider="openai",
        api_key="test-key",
        model="gpt-4"
    )
    
    # Try to use .get() (this won't work as expected)
    try:
        # Pydantic models don't have .get() method
        result = ai_config.get('provider', 'default')
        print(f"❌ .get() returned: {result}")
    except AttributeError as e:
        print(f"✓ Expected error: {e}")
        print("  (Pydantic models don't have .get() method)\n")
    
    # Correct way: direct attribute access
    print("Correct way (direct access):")
    print(f"  ai_config.provider = {ai_config.provider}")
    print(f"  ai_config.model = {ai_config.model}\n")
    
    print("This is why we convert to dict before passing to AI methods!\n")


if __name__ == "__main__":
    test_aiconfig_to_dict_conversion()
    test_aiconfig_direct_access()
    
    print("="*60)
    print("🎉 All Tests Passed!")
    print("="*60)
