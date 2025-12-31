"""
Comprehensive unit tests for MCP and Memory systems.

Tests MCP client, MCP server, embeddings, vector store, and context retrieval.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from core.ai.mcp.client import MCPClient, MCPToolRegistry, MCPTool
from core.ai.mcp.server import MCPServer, MCPServerConfig, ToolDefinition
from core.ai.memory.embeddings import EmbeddingEngine, Embedding
from core.ai.memory.vector_store import VectorStore, SearchResult
from core.ai.memory.retrieval import ContextRetriever, RetrievalConfig


# Fixtures

@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage directory."""
    storage = tmp_path / "test_storage"
    storage.mkdir()
    return storage


@pytest.fixture
def mcp_config(tmp_path):
    """Create MCP server configuration file."""
    config_path = tmp_path / "mcp_servers.json"
    config = {
        "servers": {
            "jira_server": {
                "url": "https://jira.example.com",
                "authentication": {
                    "type": "bearer",
                    "token": "test-token"
                }
            },
            "github_server": {
                "url": "https://api.github.com",
                "authentication": {
                    "type": "token",
                    "token": "ghp_test"
                }
            }
        }
    }
    config_path.write_text(json.dumps(config))
    return config_path


# MCP Client Tests

class TestMCPClient:
    """Tests for MCP client."""
    
    def test_tool_registry_initialization(self, mcp_config):
        """Test tool registry initialization."""
        registry = MCPToolRegistry(config_path=mcp_config)
        assert len(registry._servers) == 2
        assert "jira_server" in registry._servers
        assert "github_server" in registry._servers
    
    def test_discover_jira_tools(self, mcp_config):
        """Test discovering Jira tools."""
        registry = MCPToolRegistry(config_path=mcp_config)
        tools = registry.discover_tools("jira_server")
        
        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "jira_create_issue" in tool_names
        assert "jira_search_issues" in tool_names
        
        # Verify tool details
        create_tool = next(t for t in tools if t.name == "jira_create_issue")
        assert create_tool.server_url == "https://jira.example.com"
        assert "project" in create_tool.input_schema["properties"]
    
    def test_discover_github_tools(self, mcp_config):
        """Test discovering GitHub tools."""
        registry = MCPToolRegistry(config_path=mcp_config)
        tools = registry.discover_tools("github_server")
        
        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "github_create_pr" in tool_names
        assert "github_get_pr_status" in tool_names
    
    def test_get_tool(self, mcp_config):
        """Test getting a registered tool."""
        registry = MCPToolRegistry(config_path=mcp_config)
        registry.discover_tools("jira_server")
        
        tool = registry.get_tool("jira_create_issue")
        assert tool is not None
        assert tool.name == "jira_create_issue"
        
        # Non-existent tool
        assert registry.get_tool("nonexistent") is None
    
    def test_list_tools(self, mcp_config):
        """Test listing tools."""
        registry = MCPToolRegistry(config_path=mcp_config)
        registry.discover_tools("jira_server")
        registry.discover_tools("github_server")
        
        all_tools = registry.list_tools()
        assert len(all_tools) == 4
        
        # Filter by server
        jira_tools = registry.list_tools(server_name="jira")
        assert len(jira_tools) == 2
    
    def test_client_call_tool(self, mcp_config):
        """Test calling a tool via MCP client."""
        registry = MCPToolRegistry(config_path=mcp_config)
        registry.discover_tools("jira_server")
        
        client = MCPClient(registry=registry)
        
        result = client.call_tool(
            tool_name="jira_create_issue",
            inputs={
                "project": "TEST",
                "summary": "Test issue",
                "issue_type": "Bug",
            },
        )
        
        assert "issue_key" in result
        assert result["issue_key"] == "PROJ-123"
    
    def test_client_tool_not_found(self, mcp_config):
        """Test calling non-existent tool."""
        registry = MCPToolRegistry(config_path=mcp_config)
        client = MCPClient(registry=registry)
        
        with pytest.raises(ValueError, match="Tool not found"):
            client.call_tool("nonexistent_tool", {})
    
    def test_client_missing_required_field(self, mcp_config):
        """Test calling tool with missing required field."""
        registry = MCPToolRegistry(config_path=mcp_config)
        registry.discover_tools("jira_server")
        
        client = MCPClient(registry=registry)
        
        with pytest.raises(ValueError, match="Required field missing"):
            client.call_tool(
                tool_name="jira_create_issue",
                inputs={"project": "TEST"},  # Missing summary and issue_type
            )
    
    def test_client_call_history(self, mcp_config):
        """Test client call history tracking."""
        registry = MCPToolRegistry(config_path=mcp_config)
        registry.discover_tools("github_server")
        
        client = MCPClient(registry=registry)
        
        client.call_tool(
            tool_name="github_create_pr",
            inputs={
                "repo": "owner/repo",
                "title": "Test PR",
                "head": "feature-branch",
            },
        )
        
        history = client.get_call_history()
        assert len(history) == 1
        assert history[0]["tool"] == "github_create_pr"


# MCP Server Tests

class TestMCPServer:
    """Tests for MCP server."""
    
    def test_server_initialization(self):
        """Test server initialization."""
        server = MCPServer()
        
        # Should have 5 built-in tools
        tools = server.list_tools()
        assert len(tools) >= 5
        
        tool_names = [t["name"] for t in tools]
        assert "run_tests" in tool_names
        assert "analyze_flaky_tests" in tool_names
        assert "migrate_tests" in tool_names
    
    def test_server_custom_config(self):
        """Test server with custom configuration."""
        config = MCPServerConfig(
            host="0.0.0.0",
            port=9090,
            auth_enabled=False,
        )
        server = MCPServer(config=config)
        
        assert server.config.host == "0.0.0.0"
        assert server.config.port == 9090
        assert server.config.auth_enabled is False
    
    def test_register_tool(self):
        """Test registering a custom tool."""
        server = MCPServer()
        
        def handler(inputs):
            return {"result": "success"}
        
        tool = ToolDefinition(
            name="custom_tool",
            description="A custom tool",
            handler=handler,
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
        )
        
        server.register_tool(tool)
        
        tools = server.list_tools()
        assert any(t["name"] == "custom_tool" for t in tools)
    
    def test_register_duplicate_tool(self):
        """Test registering duplicate tool name."""
        server = MCPServer()
        
        def handler(inputs):
            return {}
        
        tool = ToolDefinition(
            name="run_tests",  # Already exists
            description="Duplicate",
            handler=handler,
            input_schema={},
            output_schema={},
        )
        
        with pytest.raises(ValueError, match="already registered"):
            server.register_tool(tool)
    
    def test_unregister_tool(self):
        """Test unregistering a tool."""
        server = MCPServer()
        
        initial_count = len(server.list_tools())
        
        # Unregister existing tool
        assert server.unregister_tool("run_tests") is True
        assert len(server.list_tools()) == initial_count - 1
        
        # Unregister non-existent tool
        assert server.unregister_tool("nonexistent") is False
    
    def test_list_tools_by_category(self):
        """Test listing tools by category."""
        server = MCPServer()
        
        testing_tools = server.list_tools(category="testing")
        assert len(testing_tools) >= 1
        assert all(t["category"] == "testing" for t in testing_tools)
        
        analysis_tools = server.list_tools(category="analysis")
        assert len(analysis_tools) >= 2
    
    def test_execute_tool(self):
        """Test executing a tool."""
        config = MCPServerConfig(auth_enabled=False)
        server = MCPServer(config=config)
        
        result = server.execute_tool(
            tool_name="run_tests",
            inputs={
                "project_path": "/test/path",
                "framework": "pytest",
            },
        )
        
        assert result["total"] == 100
        assert result["passed"] == 95
        assert result["failed"] == 3
    
    def test_execute_tool_not_found(self):
        """Test executing non-existent tool."""
        server = MCPServer()
        
        with pytest.raises(ValueError, match="Tool not found"):
            server.execute_tool("nonexistent_tool", {})
    
    def test_execute_tool_with_auth(self):
        """Test tool execution with authentication."""
        config = MCPServerConfig(
            auth_enabled=True,
            api_key="secret-key",
        )
        server = MCPServer(config=config)
        
        # Valid auth
        result = server.execute_tool(
            tool_name="run_tests",
            inputs={"project_path": "/test", "framework": "pytest"},
            auth_token="secret-key",
        )
        assert "total" in result
        
        # Invalid auth
        with pytest.raises(PermissionError, match="Invalid or missing"):
            server.execute_tool(
                tool_name="run_tests",
                inputs={"project_path": "/test", "framework": "pytest"},
                auth_token="wrong-key",
            )
    
    def test_execute_tool_missing_input(self):
        """Test tool execution with missing required input."""
        config = MCPServerConfig(auth_enabled=False)
        server = MCPServer(config=config)
        
        result = server.execute_tool(
            tool_name="run_tests",
            inputs={},  # Missing required fields
        )
        
        # Server catches the validation error and returns error dict
        assert "error" in result
        assert result["success"] is False
        assert "Required field missing" in result["error"]
    
    def test_request_history(self):
        """Test request history logging."""
        config = MCPServerConfig(
            auth_enabled=False,
            log_requests=True,
        )
        server = MCPServer(config=config)
        
        server.execute_tool(
            tool_name="run_tests",
            inputs={"project_path": "/test", "framework": "pytest"},
        )
        
        history = server.get_request_history()
        assert len(history) == 1
        assert history[0]["tool"] == "run_tests"
    
    def test_to_mcp_spec(self):
        """Test MCP specification export."""
        server = MCPServer()
        
        spec = server.to_mcp_spec()
        
        assert spec["name"] == "CrossBridge MCP Server"
        assert "version" in spec
        assert "tools" in spec
        assert len(spec["tools"]) >= 5
        assert "capabilities" in spec


# Embeddings Tests

class TestEmbeddings:
    """Tests for embedding engine."""
    
    def test_embedding_creation(self):
        """Test creating an embedding."""
        engine = EmbeddingEngine()
        
        embedding = engine.embed("Test text")
        
        assert embedding.content == "Test text"
        assert len(embedding.vector) == 384  # MiniLM dimension
        assert embedding.embedding_id is not None
        assert embedding.model == "sentence-transformers/all-MiniLM-L6-v2"
    
    def test_embedding_with_metadata(self):
        """Test embedding with metadata."""
        engine = EmbeddingEngine()
        
        metadata = {"type": "test", "source": "unit_test"}
        embedding = engine.embed("Test", metadata=metadata)
        
        assert embedding.metadata == metadata
    
    def test_embed_batch(self):
        """Test batch embedding generation."""
        engine = EmbeddingEngine()
        
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = engine.embed_batch(texts)
        
        assert len(embeddings) == 3
        assert embeddings[0].content == "Text 1"
        assert embeddings[2].content == "Text 3"
    
    def test_embedding_similarity(self):
        """Test similarity computation."""
        engine = EmbeddingEngine()
        
        emb1 = engine.embed("Python programming")
        emb2 = engine.embed("Python programming")  # Same text
        emb3 = engine.embed("JavaScript development")  # Different
        
        # Same text should have high similarity
        sim_same = engine.similarity(emb1, emb2)
        assert sim_same > 0.9
        
        # Different texts should have lower similarity
        sim_diff = engine.similarity(emb1, emb3)
        assert sim_diff < sim_same
    
    def test_embedding_caching(self):
        """Test embedding cache."""
        engine = EmbeddingEngine()
        
        # Generate embedding
        text = "Cached text"
        emb1 = engine.embed(text)
        cache_size_1 = engine.get_cache_size()
        
        # Generate same embedding (should use cache)
        emb2 = engine.embed(text)
        cache_size_2 = engine.get_cache_size()
        
        assert cache_size_2 == cache_size_1  # No new cache entry
        assert emb1.vector == emb2.vector
    
    def test_embedding_persistence(self, temp_storage):
        """Test saving and loading cache."""
        cache_path = temp_storage / "embeddings_cache.json"
        
        engine = EmbeddingEngine(cache_path=cache_path)
        engine.embed("Test 1")
        engine.embed("Test 2")
        
        engine.save_cache()
        assert cache_path.exists()
        
        # Load in new engine
        engine2 = EmbeddingEngine(cache_path=cache_path)
        assert engine2.get_cache_size() == 2


# Vector Store Tests

class TestVectorStore:
    """Tests for vector store."""
    
    def test_add_embedding(self):
        """Test adding content to store."""
        store = VectorStore()
        
        embedding = store.add("Test content", metadata={"type": "test"})
        
        assert store.count() == 1
        assert embedding.content == "Test content"
    
    def test_add_batch(self):
        """Test adding multiple contents."""
        store = VectorStore()
        
        contents = ["Content 1", "Content 2", "Content 3"]
        embeddings = store.add_batch(contents)
        
        assert len(embeddings) == 3
        assert store.count() == 3
    
    def test_search(self):
        """Test semantic search."""
        store = VectorStore()
        
        # Add similar contents
        store.add("Python test automation", metadata={"type": "test"})
        store.add("JavaScript unit testing", metadata={"type": "test"})
        store.add("Database migration", metadata={"type": "migration"})
        
        # Search for test-related content
        results = store.search("automated testing", top_k=2)
        
        assert len(results) <= 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(r.score >= 0 and r.score <= 1 for r in results)
    
    def test_search_with_threshold(self):
        """Test search with similarity threshold."""
        store = VectorStore()
        
        store.add("Python programming")
        store.add("Python coding")
        
        # High threshold
        results = store.search("Python", threshold=0.95)
        assert len(results) >= 0  # May filter out some results
        
        # Low threshold
        results = store.search("Python", threshold=0.0)
        assert len(results) == 2
    
    def test_search_with_metadata_filter(self):
        """Test search with metadata filtering."""
        store = VectorStore()
        
        store.add("Test failure 1", metadata={"type": "failure"})
        store.add("Test failure 2", metadata={"type": "failure"})
        store.add("Test success", metadata={"type": "success"})
        
        # Filter by type
        results = store.search(
            "test",
            filter_metadata={"type": "failure"}
        )
        
        assert all(r.embedding.metadata["type"] == "failure" for r in results)
    
    def test_get_embedding(self):
        """Test getting embedding by ID."""
        store = VectorStore()
        
        embedding = store.add("Test content")
        
        retrieved = store.get(embedding.embedding_id)
        assert retrieved is not None
        assert retrieved.content == "Test content"
        
        # Non-existent ID
        assert store.get("nonexistent") is None
    
    def test_delete_embedding(self):
        """Test deleting an embedding."""
        store = VectorStore()
        
        embedding = store.add("Test content")
        assert store.count() == 1
        
        deleted = store.delete(embedding.embedding_id)
        assert deleted is True
        assert store.count() == 0
        
        # Delete non-existent
        assert store.delete("nonexistent") is False
    
    def test_clear_store(self):
        """Test clearing all embeddings."""
        store = VectorStore()
        
        store.add_batch(["Content 1", "Content 2", "Content 3"])
        assert store.count() == 3
        
        store.clear()
        assert store.count() == 0
    
    def test_persistence(self, temp_storage):
        """Test saving and loading embeddings."""
        storage_path = temp_storage / "vectors.json"
        
        # Create and save
        store = VectorStore(storage_path=storage_path)
        store.add("Test 1", metadata={"id": 1})
        store.add("Test 2", metadata={"id": 2})
        store.save_embeddings()
        
        assert storage_path.exists()
        
        # Load in new store
        store2 = VectorStore(storage_path=storage_path)
        assert store2.count() == 2
    
    def test_statistics(self):
        """Test getting store statistics."""
        store = VectorStore()
        
        store.add_batch(["Content 1", "Content 2"])
        
        stats = store.get_statistics()
        
        assert stats["total_embeddings"] == 2
        assert stats["embedding_dimensions"] == 384
        assert "models" in stats
        assert len(stats["models"]) >= 1


# Context Retrieval Tests

class TestContextRetrieval:
    """Tests for context retrieval system."""
    
    def test_retriever_initialization(self):
        """Test retriever initialization."""
        retriever = ContextRetriever()
        
        assert retriever.store is not None
        assert retriever.config is not None
        assert retriever.config.max_results == 10
    
    def test_index_test_failures(self):
        """Test indexing test failures."""
        retriever = ContextRetriever()
        
        failures = [
            {
                "test_name": "test_login",
                "error_message": "Timeout",
                "timestamp": "2025-01-01T10:00:00Z",
            },
            {
                "test_name": "test_checkout",
                "error_message": "Element not found",
                "timestamp": "2025-01-01T11:00:00Z",
            },
        ]
        
        retriever.index_test_failures(failures)
        
        assert retriever.store.count() == 2
    
    def test_index_test_cases(self):
        """Test indexing test cases."""
        retriever = ContextRetriever()
        
        test_cases = [
            {
                "name": "test_authentication",
                "description": "Test user authentication",
                "framework": "pytest",
            },
            {
                "name": "test_authorization",
                "description": "Test user permissions",
                "framework": "pytest",
            },
        ]
        
        retriever.index_test_cases(test_cases)
        
        assert retriever.store.count() == 2
    
    def test_retrieve_similar_failures(self):
        """Test retrieving similar failures."""
        retriever = ContextRetriever()
        
        failures = [
            {"test_name": "test_login", "error_message": "Network timeout"},
            {"test_name": "test_api", "error_message": "Connection timeout"},
            {"test_name": "test_db", "error_message": "Database error"},
        ]
        retriever.index_test_failures(failures)
        
        # Search for timeout-related failures
        results = retriever.retrieve_similar_failures("timeout error", max_results=2)
        
        assert len(results) <= 2
        assert all(isinstance(r, SearchResult) for r in results)
    
    def test_retrieve_related_tests(self):
        """Test retrieving related test cases."""
        retriever = ContextRetriever()
        
        test_cases = [
            {"name": "test_login", "description": "User login test"},
            {"name": "test_logout", "description": "User logout test"},
            {"name": "test_payment", "description": "Payment processing test"},
        ]
        retriever.index_test_cases(test_cases)
        
        # Search for authentication tests
        results = retriever.retrieve_related_tests("user authentication", max_results=2)
        
        assert len(results) <= 2
    
    def test_retrieve_context(self):
        """Test retrieving mixed context."""
        retriever = ContextRetriever()
        
        # Index different types
        retriever.index_test_failures([
            {"test_name": "test1", "error_message": "Error"}
        ])
        retriever.index_test_cases([
            {"name": "test2", "description": "Description"}
        ])
        
        # Retrieve mixed context
        context = retriever.retrieve_context(
            query="test error",
            context_types=["test_failure", "test_case"],
            max_per_type=5,
        )
        
        assert "test_failure" in context
        assert "test_case" in context
    
    def test_retrieval_config(self):
        """Test custom retrieval configuration."""
        config = RetrievalConfig(
            max_results=5,
            similarity_threshold=0.8,
            deduplicate=True,
        )
        
        retriever = ContextRetriever(config=config)
        
        assert retriever.config.max_results == 5
        assert retriever.config.similarity_threshold == 0.8
    
    def test_get_statistics(self):
        """Test retrieval statistics."""
        retriever = ContextRetriever()
        
        retriever.index_test_failures([{"test_name": "test1"}])
        retriever.index_test_cases([{"name": "test2"}])
        
        stats = retriever.get_statistics()
        
        assert stats["total_embeddings"] == 2
        assert "indexed_by_type" in stats
        assert stats["indexed_by_type"]["test_failure"] == 1
        assert stats["indexed_by_type"]["test_case"] == 1
    
    def test_save_and_load(self, temp_storage):
        """Test persisting indexed context."""
        storage_path = temp_storage / "context.json"
        
        retriever = ContextRetriever()
        retriever.index_test_failures([
            {"test_name": "test1", "error_message": "Error"}
        ])
        
        retriever.save(storage_path)
        assert storage_path.exists()
        
        # Load in new retriever
        retriever2 = ContextRetriever()
        retriever2.load(storage_path)
        
        assert retriever2.store.count() == 1
