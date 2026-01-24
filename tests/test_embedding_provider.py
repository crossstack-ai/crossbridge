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

    @patch("core.memory.embedding_provider.openai")
    def test_initialization(self, mock_openai):
        """Test OpenAI provider initialization."""
        provider = OpenAIEmbeddingProvider(
            model="text-embedding-3-large", api_key="test-key"
        )

        assert provider.model_name == "text-embedding-3-large"
        assert provider.get_dimension() == 3072
        assert provider.batch_size == 100

    @patch("core.memory.embedding_provider.openai")
    def test_embed_single_batch(self, mock_openai):
        """Test embedding a single batch of texts."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3]),
            Mock(embedding=[0.4, 0.5, 0.6]),
        ]
        mock_openai.OpenAI.return_value.embeddings.create.return_value = (
            mock_response
        )

        provider = OpenAIEmbeddingProvider(api_key="test-key")
        texts = ["test 1", "test 2"]
        embeddings = provider.embed(texts)

        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [0.4, 0.5, 0.6]

    @patch("core.memory.embedding_provider.openai")
    def test_embed_multiple_batches(self, mock_openai):
        """Test embedding with multiple batches."""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_openai.OpenAI.return_value.embeddings.create.return_value = (
            mock_response
        )

        provider = OpenAIEmbeddingProvider(api_key="test-key", batch_size=2)
        texts = ["test 1", "test 2", "test 3"]  # 2 batches
        embeddings = provider.embed(texts)

        # Should be called twice (2 batches)
        assert (
            mock_openai.OpenAI.return_value.embeddings.create.call_count == 2
        )
        assert len(embeddings) == 3

    @patch("core.memory.embedding_provider.openai")
    def test_embed_empty_list(self, mock_openai):
        """Test embedding empty list returns empty list."""
        provider = OpenAIEmbeddingProvider(api_key="test-key")
        embeddings = provider.embed([])

        assert embeddings == []
        mock_openai.OpenAI.return_value.embeddings.create.assert_not_called()

    @patch("core.memory.embedding_provider.openai")
    def test_embed_error_handling(self, mock_openai):
        """Test error handling when API call fails."""
        mock_openai.OpenAI.return_value.embeddings.create.side_effect = Exception(
            "API Error"
        )

        provider = OpenAIEmbeddingProvider(api_key="test-key")

        with pytest.raises(EmbeddingProviderError, match="OpenAI embedding failed"):
            provider.embed(["test"])

    def test_dimension_detection(self):
        """Test dimension detection for different models."""
        with patch("core.memory.embedding_provider.openai"):
            provider_large = OpenAIEmbeddingProvider(
                model="text-embedding-3-large"
            )
            assert provider_large.get_dimension() == 3072

            provider_small = OpenAIEmbeddingProvider(
                model="text-embedding-3-small"
            )
            assert provider_small.get_dimension() == 1536

            provider_ada = OpenAIEmbeddingProvider(
                model="text-embedding-ada-002"
            )
            assert provider_ada.get_dimension() == 1536


class TestLocalEmbeddingProvider:
    """Tests for local (Ollama) embedding provider."""

    @patch("core.memory.embedding_provider.ollama")
    def test_initialization(self, mock_ollama):
        """Test local provider initialization."""
        provider = LocalEmbeddingProvider(
            model="nomic-embed-text", base_url="http://localhost:11434"
        )

        assert provider.model_name == "nomic-embed-text"
        assert provider.base_url == "http://localhost:11434"
        assert provider.get_dimension() == 768

    @patch("core.memory.embedding_provider.ollama")
    def test_embed(self, mock_ollama):
        """Test embedding with local model."""
        mock_client = Mock()
        mock_client.embeddings.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_ollama.Client.return_value = mock_client

        provider = LocalEmbeddingProvider()
        texts = ["test 1", "test 2"]
        embeddings = provider.embed(texts)

        assert len(embeddings) == 2
        assert mock_client.embeddings.call_count == 2

    @patch("core.memory.embedding_provider.ollama")
    def test_embed_error_handling(self, mock_ollama):
        """Test error handling for local provider."""
        mock_client = Mock()
        mock_client.embeddings.side_effect = Exception("Connection error")
        mock_ollama.Client.return_value = mock_client

        provider = LocalEmbeddingProvider()

        with pytest.raises(EmbeddingProviderError, match="Local embedding failed"):
            provider.embed(["test"])


class TestHuggingFaceEmbeddingProvider:
    """Tests for HuggingFace embedding provider."""

    @patch("core.memory.embedding_provider.SentenceTransformer")
    def test_initialization(self, mock_st):
        """Test HuggingFace provider initialization."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_model

        provider = HuggingFaceEmbeddingProvider(
            model="sentence-transformers/all-MiniLM-L6-v2"
        )

        assert provider.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert provider.get_dimension() == 384

    @patch("core.memory.embedding_provider.SentenceTransformer")
    def test_embed(self, mock_st):
        """Test embedding with HuggingFace model."""
        import numpy as np

        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_st.return_value = mock_model

        provider = HuggingFaceEmbeddingProvider()
        texts = ["test 1", "test 2"]
        embeddings = provider.embed(texts)

        assert len(embeddings) == 2
        assert isinstance(embeddings, list)
        mock_model.encode.assert_called_once_with(texts, convert_to_numpy=True)

    @patch("core.memory.embedding_provider.SentenceTransformer")
    def test_embed_error_handling(self, mock_st):
        """Test error handling for HuggingFace provider."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.side_effect = Exception("Model error")
        mock_st.return_value = mock_model

        provider = HuggingFaceEmbeddingProvider()

        with pytest.raises(
            EmbeddingProviderError, match="HuggingFace embedding failed"
        ):
            provider.embed(["test"])


class TestEmbeddingProviderFactory:
    """Tests for embedding provider factory function."""

    @patch("core.memory.embedding_provider.openai")
    def test_create_openai_provider(self, mock_openai):
        """Test creating OpenAI provider."""
        provider = create_embedding_provider(
            "openai", model="text-embedding-3-large", api_key="test-key"
        )

        assert isinstance(provider, OpenAIEmbeddingProvider)
        assert provider.model_name == "text-embedding-3-large"

    @patch("core.memory.embedding_provider.ollama")
    def test_create_local_provider(self, mock_ollama):
        """Test creating local provider."""
        provider = create_embedding_provider("local", model="nomic-embed-text")

        assert isinstance(provider, LocalEmbeddingProvider)
        assert provider.model_name == "nomic-embed-text"

    @patch("core.memory.embedding_provider.SentenceTransformer")
    def test_create_huggingface_provider(self, mock_st):
        """Test creating HuggingFace provider."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_model

        provider = create_embedding_provider(
            "huggingface", model="sentence-transformers/all-MiniLM-L6-v2"
        )

        assert isinstance(provider, HuggingFaceEmbeddingProvider)

    def test_create_invalid_provider(self):
        """Test error when creating invalid provider type."""
        with pytest.raises(ValueError, match="Unknown provider type"):
            create_embedding_provider("invalid_type")
