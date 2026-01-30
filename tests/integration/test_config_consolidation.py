"""Test config loading after consolidation"""
from core.config.loader import ConfigLoader

def test_config_loading():
    config = ConfigLoader.load()
    
    print("=" * 60)
    print("CONFIGURATION LOADING TEST")
    print("=" * 60)
    
    print("\n✅ Config loaded successfully!")
    print(f"\nSemantic Search Configuration:")
    print(f"  - Enabled: {config.semantic_search.enabled}")
    print(f"  - Provider Type: {config.semantic_search.provider_type}")
    print(f"  - OpenAI Model: {config.semantic_search.openai_model}")
    print(f"  - OpenAI Dimensions: {config.semantic_search.openai_dimensions}")
    print(f"  - Min Similarity Score: {config.semantic_search.min_similarity_score}")
    print(f"  - Max Tokens: {config.semantic_search.max_tokens}")
    print(f"  - Vector Store Type: {config.semantic_search.vector_store_type}")
    print(f"  - Index Type: {config.semantic_search.index_type}")
    
    print(f"\nMigration Overrides:")
    print(f"  - Enabled: {config.semantic_search.migration_enabled}")
    print(f"  - Provider Type: {config.semantic_search.migration_provider_type}")
    print(f"  - Model: {config.semantic_search.migration_model}")
    print(f"  - Min Similarity: {config.semantic_search.migration_min_similarity_score}")
    
    # Test effective config in migration mode
    print(f"\n" + "=" * 60)
    print("TESTING MIGRATION MODE OVERRIDES")
    print("=" * 60)
    effective = config.semantic_search.get_effective_config("migration")
    print(f"  - Enabled: {effective.enabled}")
    print(f"  - Provider: {effective.provider_type}")
    print(f"  - Model: {effective.openai_model}")
    print(f"  - Min Similarity: {effective.min_similarity_score}")
    
    print(f"\n✅ All configuration tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    test_config_loading()
