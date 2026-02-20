"""
Embedding provider abstraction for CrossBridge Memory system.

This module provides a pluggable interface for generating embeddings
from different providers (OpenAI, local models, etc.).
"""

import os
from abc import ABC, abstractmethod
from typing import List, Optional

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.AI)


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.
    
    This allows CrossBridge to remain AI-provider-agnostic while
    supporting multiple embedding backends.
    """

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (one per input text)
            
        Raises:
            EmbeddingProviderError: If embedding generation fails
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Return the dimensionality of embeddings produced by this provider."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name of the embedding model being used."""
        pass


class EmbeddingProviderError(Exception):
    """Exception raised when embedding generation fails."""

    pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider using text-embedding-3-large or text-embedding-ada-002.
    
    Requires OPENAI_API_KEY environment variable to be set.
    """

    def __init__(
        self,
        model: str = "text-embedding-3-large",
        api_key: Optional[str] = None,
        batch_size: int = 100,
    ):
        """
        Initialize OpenAI embedding provider.
        
        Args:
            model: Model name (text-embedding-3-large, text-embedding-3-small, text-embedding-ada-002)
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            batch_size: Maximum number of texts to embed in one API call
        """
        self._model = model
        self.batch_size = batch_size

        try:
            import openai
        except ImportError:
            raise EmbeddingProviderError(
                "openai package not installed. Install with: pip install openai"
            )

        self.client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self._dimension = self._detect_dimension()

        logger.info(f"Initialized OpenAI embedding provider with model: {model}")

    def _detect_dimension(self) -> int:
        """Detect embedding dimension based on model."""
        dimension_map = {
            "text-embedding-3-large": 3072,
            "text-embedding-3-small": 1536,
            "text-embedding-ada-002": 1536,
        }
        return dimension_map.get(self._model, 1536)

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        if not texts:
            return []

        try:
            # Process in batches to respect API limits
            all_embeddings = []
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i : i + self.batch_size]
                response = self.client.embeddings.create(
                    model=self._model, input=batch
                )
                all_embeddings.extend([item.embedding for item in response.data])

            logger.info(f"Generated {len(all_embeddings)} embeddings using OpenAI")
            return all_embeddings

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise EmbeddingProviderError(f"OpenAI embedding failed: {e}")

    def get_dimension(self) -> int:
        """Return embedding dimension."""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Return model name."""
        return self._model


class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Local embedding provider using Ollama or other local models.
    
    Requires Ollama to be installed and running locally.
    """

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
    ):
        """
        Initialize local embedding provider.
        
        Args:
            model: Model name (nomic-embed-text, mxbai-embed-large, etc.)
            base_url: Ollama server URL
        """
        self._model = model
        self.base_url = base_url

        try:
            import ollama
        except ImportError:
            raise EmbeddingProviderError(
                "ollama package not installed. Install with: pip install ollama"
            )

        self.client = ollama.Client(host=base_url)
        self._dimension = 768  # Default for most local models

        logger.info(
            f"Initialized local embedding provider with model: '{model}' at {base_url}",
            category=LogCategory.AI
        )
        
        # Validate model is not empty
        if not model or model.isspace():
            raise EmbeddingProviderError(
                f"Model name cannot be empty. Received: '{model}'"
            )

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local Ollama model."""
        if not texts:
            return []

        try:
            embeddings = []
            for text in texts:
                logger.debug(
                    f"Generating embedding with model='{self._model}' for text of length {len(text)}",
                    category=LogCategory.AI
                )
                response = self.client.embeddings(model=self._model, prompt=text)
                embeddings.append(response["embedding"])

            logger.info(
                f"Generated {len(embeddings)} embeddings using local model '{self._model}'",
                category=LogCategory.AI
            )
            return embeddings

        except Exception as e:
            logger.error(
                f"Failed to generate embeddings with model '{self._model}': {e}",
                category=LogCategory.AI
            )
            # Check if it's a model-specific error
            if "model is required" in str(e).lower() or "400" in str(e):
                raise EmbeddingProviderError(
                    f"Failed to generate embeddings. Model '{self._model}' may not support embeddings. "
                    f"Ollama requires embedding-specific models like 'nomic-embed-text', 'mxbai-embed-large', "
                    f"or 'all-minilm'. Text generation models like 'deepseek-coder' cannot be used for embeddings. "
                    f"Original error: {e}"
                )
            raise EmbeddingProviderError(f"Local embedding failed: {e}")

    def get_dimension(self) -> int:
        """Return embedding dimension."""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Return model name."""
        return self._model


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """
    HuggingFace embedding provider using sentence-transformers.
    
    Runs models locally without external API calls.
    """

    def __init__(
        self,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: Optional[str] = None,
    ):
        """
        Initialize HuggingFace embedding provider.
        
        Args:
            model: HuggingFace model name or path
            device: Device to run on ('cpu', 'cuda', or None for auto-detect)
        """
        self._model_name = model

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise EmbeddingProviderError(
                "sentence-transformers not installed. Install with: pip install sentence-transformers"
            )

        self.model = SentenceTransformer(model, device=device)
        self._dimension = self.model.get_sentence_embedding_dimension()

        logger.info(
            f"Initialized HuggingFace embedding provider with model: {model}"
        )

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using HuggingFace model."""
        if not texts:
            return []

        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            logger.info(
                f"Generated {len(embeddings)} embeddings using HuggingFace model"
            )
            return embeddings.tolist()

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise EmbeddingProviderError(f"HuggingFace embedding failed: {e}")

    def get_dimension(self) -> int:
        """Return embedding dimension."""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Return model name."""
        return self._model_name


def create_embedding_provider(
    provider_type: str = "openai", **kwargs
) -> EmbeddingProvider:
    """
    Factory function to create embedding providers.
    
    Args:
        provider_type: Type of provider ('openai', 'local', 'huggingface', 'dummy')
        **kwargs: Provider-specific configuration
        
    Returns:
        Configured EmbeddingProvider instance
        
    Example:
        >>> provider = create_embedding_provider('openai', model='text-embedding-3-large')
        >>> embeddings = provider.embed(['test text'])
    """
    providers = {
        "openai": OpenAIEmbeddingProvider,
        "local": LocalEmbeddingProvider,
        "huggingface": HuggingFaceEmbeddingProvider,
        "dummy": DummyEmbeddingProvider,
    }

    if provider_type not in providers:
        raise ValueError(
            f"Unknown provider type: {provider_type}. Available: {list(providers.keys())}"
        )

    return providers[provider_type](**kwargs)


class DummyEmbeddingProvider(EmbeddingProvider):
    """
    Dummy embedding provider for testing purposes.
    
    Generates random normalized vectors without external dependencies.
    Useful for testing infrastructure without API costs.
    """

    def __init__(self, dimension: int = 1536):
        """
        Initialize dummy provider.
        
        Args:
            dimension: Embedding dimension to generate
        """
        self._dimension = dimension
        logger.info(f"Initialized DummyEmbeddingProvider with dimension {dimension}")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate random normalized embeddings."""
        import numpy as np
        
        if not texts:
            return []

        embeddings = []
        for _ in texts:
            # Generate random vector and normalize
            vec = np.random.randn(self._dimension).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            embeddings.append(vec.tolist())

        logger.info(f"Generated {len(embeddings)} dummy embeddings")
        return embeddings

    def get_dimension(self) -> int:
        """Return embedding dimension."""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Return model name."""
        return "dummy-test-model"

