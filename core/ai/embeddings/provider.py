"""
Embedding Provider Abstraction

Model-agnostic interface for generating embeddings.
Supports OpenAI, Anthropic, DeepSeek, and local models.
"""

import os
from abc import ABC, abstractmethod
from typing import List, Optional
import time

from core.logging import get_logger, LogCategory
from core.profiling.context import profile
from cli.errors import CrossBridgeError

logger = get_logger(__name__, category=LogCategory.AI)


class EmbeddingError(CrossBridgeError):
    """Embedding generation error"""
    pass


class EmbeddingProvider(ABC):
    """
    Abstract embedding provider interface
    
    All providers must implement:
    - embed(): Generate embedding vector
    - model_name(): Return model identifier
    - dimensions(): Return vector dimensions
    """
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding vector for text
        
        Args:
            text: Input text
        
        Returns:
            Embedding vector (list of floats)
        
        Raises:
            EmbeddingError: If embedding fails
        """
        pass
    
    @abstractmethod
    def model_name(self) -> str:
        """Return model name/identifier"""
        pass
    
    @abstractmethod
    def dimensions(self) -> int:
        """Return embedding vector dimensions"""
        pass
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Default implementation: embed one by one
        Override for batch-optimized providers
        
        Args:
            texts: List of input texts
        
        Returns:
            List of embedding vectors
        """
        return [self.embed(text) for text in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider
    
    Supports:
    - text-embedding-3-large (3072 dimensions)
    - text-embedding-3-small (1536 dimensions)
    - text-embedding-ada-002 (1536 dimensions, legacy)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-large",
        max_retries: int = 3,
        timeout: int = 30
    ):
        """
        Initialize OpenAI provider
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise EmbeddingError(
                "OpenAI API key not provided",
                suggestion="Set OPENAI_API_KEY environment variable or pass api_key parameter"
            )
        
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Lazy import to avoid dependency issues
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key, timeout=self.timeout)
        except ImportError:
            raise EmbeddingError(
                "OpenAI library not installed",
                suggestion="Install with: pip install openai"
            )
        
        logger.info(f"Initialized OpenAI embedding provider", model=self.model)
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API"""
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text")
        
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"HTTP Request: POST https://api.openai.com/v1/embeddings (model='{self.model}', text_length={len(text)})"
                )
                response = self.client.embeddings.create(
                    input=text,
                    model=self.model
                )
                
                embedding = response.data[0].embedding
                logger.info(f"Generated embedding using OpenAI (dimensions={len(embedding)})")
                logger.debug(f"Generated embedding", dimensions=len(embedding))
                return embedding
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Embedding attempt {attempt + 1} failed, retrying in {wait_time}s", error=str(e))
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to generate embedding after {self.max_retries} attempts", error=str(e))
                    raise EmbeddingError(f"OpenAI embedding failed: {e}")
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding (optimized for OpenAI)"""
        if not texts:
            return []
        
        # Filter empty texts
        non_empty_texts = [t for t in texts if t and t.strip()]
        if not non_empty_texts:
            raise EmbeddingError("Cannot embed batch with all empty texts")
        
        try:
            logger.info(
                f"HTTP Request: POST https://api.openai.com/v1/embeddings (model='{self.model}', batch_size={len(non_empty_texts)})"
            )
            response = self.client.embeddings.create(
                input=non_empty_texts,
                model=self.model
            )
            
            embeddings = [item.embedding for item in response.data]
            logger.info(f"Generated {len(embeddings)} embeddings using OpenAI")
            logger.debug(f"Generated batch embeddings", count=len(embeddings))
            return embeddings
            
        except Exception as e:
            logger.error(f"Batch embedding failed", error=str(e))
            raise EmbeddingError(f"OpenAI batch embedding failed: {e}")
    
    def model_name(self) -> str:
        """Return model name"""
        return self.model
    
    def dimensions(self) -> int:
        """Return embedding dimensions"""
        # OpenAI dimension mapping
        dimensions_map = {
            'text-embedding-3-large': 3072,
            'text-embedding-3-small': 1536,
            'text-embedding-ada-002': 1536,
        }
        return dimensions_map.get(self.model, 1536)


class AnthropicEmbeddingProvider(EmbeddingProvider):
    """
    Anthropic embedding provider (Voyage AI)
    
    Note: Anthropic uses Voyage AI for embeddings
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "voyage-large-2",
        max_retries: int = 3,
        timeout: int = 30
    ):
        """
        Initialize Anthropic/Voyage provider
        
        Args:
            api_key: Voyage API key (defaults to VOYAGE_API_KEY env var)
            model: Model name
            max_retries: Maximum retry attempts
            timeout: Request timeout
        """
        self.api_key = api_key or os.getenv('VOYAGE_API_KEY')
        if not self.api_key:
            raise EmbeddingError(
                "Voyage API key not provided",
                suggestion="Set VOYAGE_API_KEY environment variable"
            )
        
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        
        try:
            import voyageai
            self.client = voyageai.Client(api_key=self.api_key)
        except ImportError:
            raise EmbeddingError(
                "VoyageAI library not installed",
                suggestion="Install with: pip install voyageai"
            )
        
        logger.info(f"Initialized Voyage embedding provider", model=self.model)
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding using Voyage API"""
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text")
        
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"HTTP Request: POST https://api.voyageai.com/v1/embeddings (model='{self.model}', text_length={len(text)})"
                )
                result = self.client.embed(
                    texts=[text],
                    model=self.model
                )
                
                embedding = result.embeddings[0]
                logger.info(f"Generated embedding using Voyage (dimensions={len(embedding)})")
                logger.debug(f"Generated embedding", dimensions=len(embedding))
                return embedding
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Embedding attempt {attempt + 1} failed, retrying", error=str(e))
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to generate embedding", error=str(e))
                    raise EmbeddingError(f"Voyage embedding failed: {e}")
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding"""
        if not texts:
            return []
        
        non_empty_texts = [t for t in texts if t and t.strip()]
        if not non_empty_texts:
            raise EmbeddingError("Cannot embed batch with all empty texts")
        
        try:
            logger.info(
                f"HTTP Request: POST https://api.voyageai.com/v1/embeddings (model='{self.model}', batch_size={len(non_empty_texts)})"
            )
            result = self.client.embed(
                texts=non_empty_texts,
                model=self.model
            )
            
            embeddings = result.embeddings
            logger.info(f"Generated {len(embeddings)} embeddings using Voyage")
            logger.debug(f"Generated batch embeddings", count=len(embeddings))
            return embeddings
            
        except Exception as e:
            logger.error(f"Batch embedding failed", error=str(e))
            raise EmbeddingError(f"Voyage batch embedding failed: {e}")
    
    def model_name(self) -> str:
        """Return model name"""
        return self.model
    
    def dimensions(self) -> int:
        """Return embedding dimensions"""
        # Voyage dimension mapping
        dimensions_map = {
            'voyage-large-2': 1536,
            'voyage-code-2': 1536,
            'voyage-2': 1024,
        }
        return dimensions_map.get(self.model, 1536)


class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Local embedding provider using sentence-transformers
    
    Good for:
    - Development/testing
    - Air-gapped environments
    - Cost optimization
    """
    
    def __init__(
        self,
        model: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None
    ):
        """
        Initialize local embedding provider
        
        Args:
            model: Sentence-transformers model name
            device: Device (cpu, cuda, mps) - auto-detected if None
        """
        self.model_name_str = model
        self.device = device
        
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model, device=device)
        except ImportError:
            raise EmbeddingError(
                "sentence-transformers not installed",
                suggestion="Install with: pip install sentence-transformers"
            )
        
        logger.info(f"Initialized local embedding provider", model=model, device=self.model.device)
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding using local model"""
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text")
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Local embedding failed", error=str(e))
            raise EmbeddingError(f"Local embedding failed: {e}")
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding (optimized for local)"""
        if not texts:
            return []
        
        non_empty_texts = [t for t in texts if t and t.strip()]
        if not non_empty_texts:
            raise EmbeddingError("Cannot embed batch with all empty texts")
        
        try:
            embeddings = self.model.encode(non_empty_texts, convert_to_numpy=True)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Batch embedding failed", error=str(e))
            raise EmbeddingError(f"Local batch embedding failed: {e}")
    
    def model_name(self) -> str:
        """Return model name"""
        return self.model_name_str
    
    def dimensions(self) -> int:
        """Return embedding dimensions"""
        return self.model.get_sentence_embedding_dimension()


def create_embedding_provider(
    provider_type: str = "openai",
    **kwargs
) -> EmbeddingProvider:
    """
    Factory function to create embedding provider
    
    Args:
        provider_type: Provider type (openai, anthropic, local)
        **kwargs: Provider-specific parameters
    
    Returns:
        EmbeddingProvider instance
    
    Example:
        provider = create_embedding_provider("openai", model="text-embedding-3-large")
        embedding = provider.embed("Hello world")
    """
    providers = {
        'openai': OpenAIEmbeddingProvider,
        'anthropic': AnthropicEmbeddingProvider,
        'local': LocalEmbeddingProvider,
    }
    
    provider_class = providers.get(provider_type.lower())
    if not provider_class:
        raise EmbeddingError(
            f"Unknown provider type: {provider_type}",
            suggestion=f"Valid providers: {', '.join(providers.keys())}"
        )
    
    return provider_class(**kwargs)
