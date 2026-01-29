"""
Semantic Search Examples

Demonstrates how to use CrossBridge's Semantic Search system for intelligent
test discovery and similarity analysis.
"""

from core.ai.embeddings.semantic_service import SemanticSearchService
from core.config.loader import ConfigLoader


def example_1_index_single_test():
    """Example 1: Index a single test"""
    print("\n=== Example 1: Index Single Test ===\n")
    
    config_loader = ConfigLoader()
    service = SemanticSearchService(config_loader=config_loader)
    
    # Index a test
    service.index_entity(
        entity_id="test_user_login",
        entity_type="test",
        test_name="test_user_login",
        description="User login with valid credentials",
        framework="pytest",
        tags=["authentication", "smoke"],
        file_path="tests/test_auth.py"
    )
    
    print("✓ Indexed test: test_user_login")


def example_2_batch_indexing():
    """Example 2: Batch index multiple tests"""
    print("\n=== Example 2: Batch Indexing ===\n")
    
    config_loader = ConfigLoader()
    service = SemanticSearchService(config_loader=config_loader)
    
    # Batch index multiple tests
    entities = [
        {
            "entity_id": "test_login_timeout",
            "entity_type": "test",
            "test_name": "test_login_timeout",
            "description": "Verify login timeout handling",
            "framework": "pytest",
            "tags": ["authentication", "timeout"]
        },
        {
            "entity_id": "test_logout",
            "entity_type": "test",
            "test_name": "test_logout",
            "description": "User logout functionality",
            "framework": "pytest",
            "tags": ["authentication"]
        },
        {
            "entity_id": "test_api_validation",
            "entity_type": "test",
            "test_name": "test_api_validation",
            "description": "API response validation",
            "framework": "pytest",
            "tags": ["api", "validation"]
        }
    ]
    
    service.index_batch(entities)
    print(f"✓ Indexed {len(entities)} tests in batch")


def example_3_basic_search():
    """Example 3: Basic semantic search"""
    print("\n=== Example 3: Basic Search ===\n")
    
    config_loader = ConfigLoader()
    service = SemanticSearchService(config_loader=config_loader)
    
    # Search for tests related to login
    results = service.search("login timeout error", top_k=5)
    
    print(f"Found {len(results)} similar tests:")
    for i, result in enumerate(results, 1):
        print(f"{i}. Score: {result.score:.3f}")
        print(f"   ID: {result.id}")
        print(f"   Type: {result.entity_type}")
        print(f"   Preview: {result.text[:100]}...")
        print()


def example_4_filtered_search():
    """Example 4: Search with filters"""
    print("\n=== Example 4: Filtered Search ===\n")
    
    config_loader = ConfigLoader()
    service = SemanticSearchService(config_loader=config_loader)
    
    # Search only for tests (not scenarios or failures)
    results = service.search(
        query="authentication tests",
        top_k=10,
        entity_type="test",  # Filter by entity type
        min_score=0.75  # Only return high-confidence matches
    )
    
    print(f"Found {len(results)} authentication tests (score >= 0.75):")
    for result in results:
        print(f"- {result.id} (score: {result.score:.3f})")


def example_5_find_similar():
    """Example 5: Find similar entities"""
    print("\n=== Example 5: Find Similar Tests ===\n")
    
    config_loader = ConfigLoader()
    service = SemanticSearchService(config_loader=config_loader)
    
    # Find tests similar to a specific test
    similar = service.find_similar("test_user_login", top_k=5)
    
    print("Tests similar to 'test_user_login':")
    for result in similar:
        print(f"- {result.id} (similarity: {result.score:.3f})")


def example_6_statistics():
    """Example 6: Get system statistics"""
    print("\n=== Example 6: System Statistics ===\n")
    
    config_loader = ConfigLoader()
    service = SemanticSearchService(config_loader=config_loader)
    
    stats = service.get_statistics()
    
    print(f"Total Entities: {stats['total_entities']}")
    print(f"Entity Counts: {stats['entity_counts']}")
    print(f"Versions: {stats['versions']}")
    print(f"Provider: {stats['provider_type']} ({stats['provider_model']})")
    print(f"Dimensions: {stats['embedding_dimensions']}")


def example_7_metadata_filtering():
    """Example 7: Search with metadata filters"""
    print("\n=== Example 7: Metadata Filtering ===\n")
    
    config_loader = ConfigLoader()
    service = SemanticSearchService(config_loader=config_loader)
    
    # Search with metadata filters (framework-specific)
    results = service.search(
        query="API tests",
        top_k=10,
        filters={"framework": "pytest", "tags": ["api"]}
    )
    
    print(f"Found {len(results)} API tests in pytest framework:")
    for result in results:
        framework = result.metadata.get("framework", "unknown")
        tags = result.metadata.get("tags", [])
        print(f"- {result.id} [{framework}] {tags}")


def example_8_scenario_search():
    """Example 8: Search BDD scenarios"""
    print("\n=== Example 8: BDD Scenario Search ===\n")
    
    config_loader = ConfigLoader()
    service = SemanticSearchService(config_loader=config_loader)
    
    # Index BDD scenario
    service.index_entity(
        entity_id="scenario_user_authentication",
        entity_type="scenario",
        scenario_name="User logs in successfully",
        feature="User Authentication",
        given_steps=["user is on login page"],
        when_steps=["user enters valid credentials", "user clicks login button"],
        then_steps=["user should see dashboard"],
        tags=["authentication", "smoke"]
    )
    
    # Search for scenarios
    results = service.search("login flow", entity_type="scenario", top_k=5)
    
    print(f"Found {len(results)} similar scenarios:")
    for result in results:
        print(f"- {result.id} (score: {result.score:.3f})")


def example_9_failure_analysis():
    """Example 9: Index and search test failures"""
    print("\n=== Example 9: Failure Analysis ===\n")
    
    config_loader = ConfigLoader()
    service = SemanticSearchService(config_loader=config_loader)
    
    # Index a test failure
    service.index_entity(
        entity_id="failure_timeout_20240115",
        entity_type="failure",
        error_message="TimeoutError: Waiting for element to load",
        error_type="TimeoutError",
        stack_trace="at login_page.wait_for_element(...)",
        test_step="Wait for login button",
        test_id="test_user_login",
        framework="pytest"
    )
    
    # Search for similar failures
    results = service.search(
        "timeout waiting for element",
        entity_type="failure",
        top_k=5
    )
    
    print(f"Found {len(results)} similar failures:")
    for result in results:
        print(f"- {result.id} (score: {result.score:.3f})")
        print(f"  Error: {result.metadata.get('error_type', 'unknown')}")


def example_10_migration_assistance():
    """Example 10: Migration test discovery"""
    print("\n=== Example 10: Migration Test Discovery ===\n")
    
    config_loader = ConfigLoader()
    service = SemanticSearchService(config_loader=config_loader)
    
    # Search for equivalent tests during migration
    # (e.g., migrating from Selenium to Playwright)
    query = "user authentication with OAuth flow and session management"
    
    results = service.search(query, top_k=10, entity_type="test")
    
    print("Potential equivalent tests for migration:")
    for result in results:
        framework = result.metadata.get("framework", "unknown")
        print(f"- {result.id} [{framework}] (score: {result.score:.3f})")


def main():
    """Run all examples"""
    print("=" * 60)
    print("CrossBridge Semantic Search Examples")
    print("=" * 60)
    
    examples = [
        example_1_index_single_test,
        example_2_batch_indexing,
        example_3_basic_search,
        example_4_filtered_search,
        example_5_find_similar,
        example_6_statistics,
        example_7_metadata_filtering,
        example_8_scenario_search,
        example_9_failure_analysis,
        example_10_migration_assistance
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"❌ Error in {example.__name__}: {e}")
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
