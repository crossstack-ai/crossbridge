"""
Unit tests for embedding providers.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.memory.embedding_provider import (
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    LocalEmbeddingProvider,
    HuggingFaceEmbeddingProvider,
    EmbeddingProviderError,
    create_embedding_provider,
)


class TestEmbeddingProviderInterface:
    """Tests for EmbeddingProvider abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that EmbeddingProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            EmbeddingProvider()

    def test_must_implement_embed(self):
        """Test that subclasses must implement embed method."""

        class InvalidProvider(EmbeddingProvider):
            def get_dimension(self):
                return 1536

            @property
            def model_name(self):
                return "test"

        with pytest.raises(TypeError):
            InvalidProvider()


class TestOpenAIEmbeddingProvider:
    """Tests for OpenAI embedding provider."""

    @pytest.mark.skip(reason="Requires OpenAI API - use unified core.embeddings.OpenAIProvider instead")
    def test_initialization(self):
        """Test OpenAI provider initialization."""
        # This test is deprecated - use core.embeddings.OpenAIProvider
        # from core.embeddings import OpenAIProvider
        # provider = OpenAIProvider(model="text-embedding-3-large", api_key="test-key")
        # assert provider.get_model_name() == "text-embedding-3-large"
        # assert provider.get_dimension() == 3072
        pass

    @pytest.mark.skip(reason="Requires OpenAI API - use unified core.embeddings.OpenAIProvider instead")
    def test_embed_single_batch(self):
        """Test embedding a single batch of texts."""
        # This test is deprecated - use core.embeddings.OpenAIProvider
        pass

    @pytest.mark.skip(reason="Requires OpenAI API - use unified core.embeddings.OpenAIProvider instead")
    def test_embed_multiple_batches(self):
        """Test embedding with multiple batches."""
        # This test is deprecated - use core.embeddings.OpenAIProvider
        pass

    @pytest.mark.skip(reason="Requires OpenAI API - use unified core.embeddings.OpenAIProvider instead")
    def test_embed_empty_list(self):
        """Test embedding empty list returns empty list."""
        # This test is deprecated - use core.embeddings.OpenAIProvider
        pass

    @pytest.mark.skip(reason="Requires OpenAI API - use unified core.embeddings.OpenAIProvider instead")
    def test_embed_error_handling(self):
        """Test error handling when API call fails."""
        # This test is deprecated - use core.embeddings.OpenAIProvider
        pass

    @pytest.mark.skip(reason="Requires OpenAI API - use unified core.embeddings.OpenAIProvider instead")
    def test_dimension_detection(self):
        """Test dimension detection for different models."""
        # This test is deprecated - use core.embeddings.OpenAIProvider
        pass


class TestLocalEmbeddingProvider:
    """Tests for local (Ollama) embedding provider."""

    @pytest.mark.skip(reason="Requires Ollama - deprecated in favor of unified API")
    def test_initialization(self):
        """Test local provider initialization."""
        # This test is deprecated - local provider no longer used
        pass

    @pytest.mark.skip(reason="Requires Ollama - deprecated in favor of unified API")
    def test_embed(self):
        """Test embedding with local model."""
        # This test is deprecated - local provider no longer used
        pass

    @pytest.mark.skip(reason="Requires Ollama - deprecated in favor of unified API")
    def test_embed_error_handling(self):
        """Test error handling for local provider."""
        # This test is deprecated - local provider no longer used
        pass


class TestHuggingFaceEmbeddingProvider:
    """Tests for HuggingFace embedding provider."""

    @pytest.mark.skip(reason="Use unified core.embeddings.SentenceTransformerProvider instead")
    def test_initialization(self):
        """Test HuggingFace provider initialization."""
        # This test is deprecated - use core.embeddings.SentenceTransformerProvider
        pass

    @pytest.mark.skip(reason="Use unified core.embeddings.SentenceTransformerProvider instead")
    def test_embed(self):
        """Test embedding with HuggingFace model."""
        # This test is deprecated - use core.embeddings.SentenceTransformerProvider
        pass

    @pytest.mark.skip(reason="Use unified core.embeddings.SentenceTransformerProvider instead")
    def test_embed_error_handling(self):
        """Test error handling for HuggingFace provider."""
        # This test is deprecated - use core.embeddings.SentenceTransformerProvider
        pass


class TestEmbeddingProviderFactory:
    """Tests for embedding provider factory function."""

    @pytest.mark.skip(reason="Use unified core.embeddings.create_provider instead")
    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        # This test is deprecated - use core.embeddings.create_provider
        pass

    @pytest.mark.skip(reason="Use unified core.embeddings.create_provider instead")
    def test_create_local_provider(self):
        """Test creating local provider."""
        # This test is deprecated - use core.embeddings.create_provider
        pass

    @pytest.mark.skip(reason="Use unified core.embeddings.create_provider instead")
    def test_create_huggingface_provider(self):
        """Test creating HuggingFace provider."""
        # This test is deprecated - use core.embeddings.create_provider
        pass

    def test_create_invalid_provider(self):
        """Test error when creating invalid provider type."""
        with pytest.raises(ValueError, match="Unknown provider type"):
            create_embedding_provider("invalid_type")
