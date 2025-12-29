"""
Unit tests for persistence database connection.

Tests cover:
- Database configuration
- Connection handling
- Health checks
- Error handling
"""

import pytest
from unittest.mock import patch, MagicMock
import os
from persistence.db import DatabaseConfig, create_session, check_database_health


class TestDatabaseConfig:
    """Test DatabaseConfig class."""
    
    def test_get_db_url_from_full_url(self, monkeypatch):
        """Test getting DB URL from CROSSBRIDGE_DB_URL."""
        test_url = "postgresql://user:pass@localhost:5432/crossbridge"
        monkeypatch.setenv("CROSSBRIDGE_DB_URL", test_url)
        
        assert DatabaseConfig.get_db_url() == test_url
    
    def test_get_db_url_from_components(self, monkeypatch):
        """Test building DB URL from individual components."""
        monkeypatch.setenv("DB_HOST", "db.example.com")
        monkeypatch.setenv("DB_PORT", "5433")
        monkeypatch.setenv("DB_NAME", "testdb")
        monkeypatch.setenv("DB_USER", "testuser")
        monkeypatch.setenv("DB_PASSWORD", "testpass")
        monkeypatch.delenv("CROSSBRIDGE_DB_URL", raising=False)
        
        url = DatabaseConfig.get_db_url()
        
        assert "testuser:testpass" in url
        assert "db.example.com:5433" in url
        assert "/testdb" in url
    
    def test_get_db_url_not_configured(self, monkeypatch):
        """Test when database is not configured."""
        # Clear all DB environment variables
        for key in ["CROSSBRIDGE_DB_URL", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]:
            monkeypatch.delenv(key, raising=False)
        
        assert DatabaseConfig.get_db_url() is None
    
    def test_get_db_url_defaults(self, monkeypatch):
        """Test default values for components."""
        monkeypatch.setenv("DB_PASSWORD", "testpass")
        monkeypatch.delenv("CROSSBRIDGE_DB_URL", raising=False)
        
        url = DatabaseConfig.get_db_url()
        
        # Should use defaults: localhost:5432/crossbridge, user=crossbridge
        assert "localhost:5432" in url
        assert "/crossbridge" in url
        assert "crossbridge:testpass" in url
    
    def test_is_configured_true(self, monkeypatch):
        """Test is_configured returns True when DB URL is set."""
        monkeypatch.setenv("CROSSBRIDGE_DB_URL", "postgresql://localhost/test")
        
        assert DatabaseConfig.is_configured() is True
    
    def test_is_configured_false(self, monkeypatch):
        """Test is_configured returns False when not configured."""
        monkeypatch.delenv("CROSSBRIDGE_DB_URL", raising=False)
        monkeypatch.delenv("DB_PASSWORD", raising=False)
        
        assert DatabaseConfig.is_configured() is False


class TestCreateSession:
    """Test create_session function."""
    
    def test_create_session_not_configured(self, monkeypatch):
        """Test creating session when DB not configured."""
        monkeypatch.delenv("CROSSBRIDGE_DB_URL", raising=False)
        monkeypatch.delenv("DB_PASSWORD", raising=False)
        
        session = create_session()
        
        assert session is None
    
    @patch('persistence.db.create_engine')
    @patch('persistence.db.sessionmaker')
    def test_create_session_success(self, mock_sessionmaker, mock_create_engine, monkeypatch):
        """Test successful session creation."""
        monkeypatch.setenv("CROSSBRIDGE_DB_URL", "postgresql://localhost/test")
        
        # Mock engine and connection
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_create_engine.return_value = mock_engine
        
        # Mock session
        mock_session_class = MagicMock()
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_sessionmaker.return_value = mock_session_class
        
        session = create_session()
        
        assert session == mock_session
        mock_create_engine.assert_called_once()
        mock_conn.execute.assert_called_once()  # Connection test
    
    @patch('persistence.db.create_engine')
    def test_create_session_connection_failure(self, mock_create_engine, monkeypatch):
        """Test handling connection failure."""
        monkeypatch.setenv("CROSSBRIDGE_DB_URL", "postgresql://localhost/test")
        
        # Mock engine that raises on connect
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("Connection failed")
        mock_create_engine.return_value = mock_engine
        
        session = create_session()
        
        # Should return None on error
        assert session is None
    
    def test_create_session_with_explicit_url(self):
        """Test creating session with explicit URL (bypassing env)."""
        # This should fail gracefully with invalid URL
        session = create_session("invalid://url")
        
        # Should return None on invalid URL
        assert session is None


class TestCheckDatabaseHealth:
    """Test check_database_health function."""
    
    def test_health_check_not_configured(self, monkeypatch):
        """Test health check when DB not configured."""
        monkeypatch.delenv("CROSSBRIDGE_DB_URL", raising=False)
        monkeypatch.delenv("DB_PASSWORD", raising=False)
        
        health = check_database_health()
        
        assert health["configured"] is False
        assert health["connected"] is False
        assert "not configured" in health["message"].lower()
    
    @patch('persistence.db.create_session')
    def test_health_check_connection_failure(self, mock_create_session):
        """Test health check when connection fails."""
        mock_create_session.return_value = None
        
        health = check_database_health()
        
        assert health["configured"] is False
        assert health["connected"] is False
    
    @patch('persistence.db.create_session')
    def test_health_check_success(self, mock_create_session):
        """Test successful health check."""
        # Mock session
        mock_session = MagicMock()
        
        # Mock table count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5
        
        # Mock table exists queries
        mock_exists_result = MagicMock()
        mock_exists_result.scalar.return_value = True
        
        mock_session.execute.side_effect = [
            mock_count_result,  # SELECT 1 test
            mock_count_result,  # Table count
            mock_exists_result,  # discovery_run exists
            mock_exists_result,  # test_case exists
            mock_exists_result,  # page_object exists
            mock_exists_result,  # test_page_mapping exists
            mock_exists_result,  # discovery_test_case exists
        ]
        
        mock_create_session.return_value = mock_session
        
        health = check_database_health()
        
        assert health["configured"] is True
        assert health["connected"] is True
        assert health["table_count"] == 5
        assert health["schema_complete"] is True
        assert len(health["key_tables"]) == 5
        mock_session.close.assert_called_once()
    
    @patch('persistence.db.create_session')
    def test_health_check_incomplete_schema(self, mock_create_session):
        """Test health check with incomplete schema."""
        mock_session = MagicMock()
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2
        
        mock_exists_true = MagicMock()
        mock_exists_true.scalar.return_value = True
        
        mock_exists_false = MagicMock()
        mock_exists_false.scalar.return_value = False
        
        mock_session.execute.side_effect = [
            mock_count_result,  # SELECT 1 test
            mock_count_result,  # Table count
            mock_exists_true,   # discovery_run exists
            mock_exists_false,  # test_case missing
            mock_exists_false,  # page_object missing
            mock_exists_false,  # test_page_mapping missing
            mock_exists_false,  # discovery_test_case missing
        ]
        
        mock_create_session.return_value = mock_session
        
        health = check_database_health()
        
        assert health["schema_complete"] is False
        assert "incomplete" in health["message"].lower()
        assert len(health["key_tables"]) == 1  # Only discovery_run


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_db_url(self):
        """Test with empty DB URL."""
        session = create_session("")
        
        assert session is None
    
    def test_malformed_db_url(self):
        """Test with malformed DB URL."""
        session = create_session("not-a-valid-url")
        
        assert session is None
    
    @patch('persistence.db.create_session')
    def test_health_check_query_failure(self, mock_create_session):
        """Test health check when query fails."""
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("Query failed")
        mock_create_session.return_value = mock_session
        
        health = check_database_health()
        
        assert health["connected"] is False
        assert "error" in health
        mock_session.close.assert_called_once()


class TestContractStability:
    """Test that API contracts remain stable."""
    
    def test_health_check_returns_dict(self, monkeypatch):
        """Test that health check always returns a dict."""
        monkeypatch.delenv("CROSSBRIDGE_DB_URL", raising=False)
        
        health = check_database_health()
        
        assert isinstance(health, dict)
    
    def test_health_check_has_required_keys_not_configured(self, monkeypatch):
        """Test health check has required keys when not configured."""
        monkeypatch.delenv("CROSSBRIDGE_DB_URL", raising=False)
        monkeypatch.delenv("DB_PASSWORD", raising=False)
        
        health = check_database_health()
        
        assert "configured" in health
        assert "connected" in health
        assert "message" in health
    
    @patch('persistence.db.create_session')
    def test_health_check_has_required_keys_connected(self, mock_create_session):
        """Test health check has required keys when connected."""
        mock_session = MagicMock()
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5
        
        mock_exists_result = MagicMock()
        mock_exists_result.scalar.return_value = True
        
        mock_session.execute.side_effect = [
            mock_count_result,
            mock_count_result,
            mock_exists_result, mock_exists_result, mock_exists_result,
            mock_exists_result, mock_exists_result
        ]
        
        mock_create_session.return_value = mock_session
        
        health = check_database_health()
        
        assert "configured" in health
        assert "connected" in health
        assert "table_count" in health
        assert "key_tables" in health
        assert "schema_complete" in health
        assert "message" in health
