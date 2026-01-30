"""
Unified Embedding System for CrossBridge

Consolidates the separate Memory and Execution Intelligence embedding systems
into a single, coherent architecture.

Usage:
    from core.embeddings import (
        create_provider,
        create_store,
        Embedding,
        EmbeddingConfig
    )
    
    # Create provider
    provider = create_provider('sentence-transformers', model='all-MiniLM-L6-v2')
    
    # Create store
    store = create_store('memory')  # or 'pgvector' for persistence
    
    # Generate and store embeddings
    vector = provider.embed("Test login with valid credentials")
    embedding = Embedding(
        entity_id="test_login_valid",
        entity_type="test",
        text="Test login with valid credentials",
        vector=vector,
        model=provider.get_model_name()
    )
    store.add(embedding)
    
    # Find similar
    results = store.find_similar(embedding, top_k=5)
"""

from core.embeddings.interface import (
    IEmbeddingProvider,
    IEmbeddingStore,
    IFrameworkAdapter,
    Embedding,
    EmbeddingConfig,
    EmbeddingDimension,
)

from core.embeddings.providers import (
    OpenAIProvider,
    SentenceTransformerProvider,
    HashBasedProvider,
    create_provider,
)

from core.embeddings.stores import (
    InMemoryStore,
    PgVectorStore,
    create_store,
)

from core.embeddings.adapters import (
    CucumberAdapter,
    RobotAdapter,
    PytestAdapter,
)

__all__ = [
    # Interfaces
    'IEmbeddingProvider',
    'IEmbeddingStore',
    'IFrameworkAdapter',
    'Embedding',
    'EmbeddingConfig',
    'EmbeddingDimension',
    
    # Providers
    'OpenAIProvider',
    'SentenceTransformerProvider',
    'HashBasedProvider',
    'create_provider',
    
    # Stores
    'InMemoryStore',
    'PgVectorStore',
    'create_store',
    
    # Adapters
    'CucumberAdapter',
    'RobotAdapter',
    'PytestAdapter',
]


def get_provider_from_config(config: EmbeddingConfig) -> IEmbeddingProvider:
    """Create provider from configuration"""
    return create_provider(
        provider_type=config.provider_type,
        model=config.model,
        api_key=config.api_key,
        dimension=config.dimension or 384
    )


def get_store_from_config(config: EmbeddingConfig) -> IEmbeddingStore:
    """Create store from configuration"""
    return create_store(
        store_type=config.storage_type,
        connection_string=config.connection_string,
        dimension=config.dimension or 384
    )
