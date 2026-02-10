"""
Unit tests for CrossBridge Run Commands
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import subprocess
import os

from cli.commands.run_commands import CrossBridgeRunner


class TestCrossBridgeRunner:
    """Tests for CrossBridgeRunner class."""
    
    def test_init_default_values(self):
        """Test initialization with default env values."""
        with patch.dict(os.environ, {}, clear=True):
            runner = CrossBridgeRunner()
            
            assert runner.sidecar_host == "localhost"
            assert runner.sidecar_port == "8765"
            assert runner.enabled == True
            assert "/.crossbridge/adapters" in runner.adapter_dir or "\\.crossbridge\\adapters" in runner.adapter_dir
    
    def test_init_custom_values(self):
        """Test initialization with custom env values."""
        custom_env = {
            "CROSSBRIDGE_SIDECAR_HOST": "customhost",
            "CROSSBRIDGE_SIDECAR_PORT": "9999",
            "CROSSBRIDGE_ENABLED": "false",
            "CROSSBRIDGE_ADAPTER_DIR": "/custom/path"
        }
        
        with patch.dict(os.environ, custom_env):
            runner = CrossBridgeRunner()
            
            assert runner.sidecar_host == "customhost"
            assert runner.sidecar_port == "9999"
            assert runner.enabled == False
            assert runner.adapter_dir == "/custom/path"
    
    def test_backward_compatibility_env_vars(self):
        """Test backward compatibility with CROSSBRIDGE_API_* variables."""
        custom_env = {
            "CROSSBRIDGE_API_HOST": "oldhost",
            "CROSSBRIDGE_API_PORT": "8888"
        }
        
        with patch.dict(os.environ, custom_env):
            runner = CrossBridgeRunner()
            
            assert runner.sidecar_host == "oldhost"
            assert runner.sidecar_port == "8888"
    
    def test_detect_framework_robot(self):
        """Test framework detection for Robot Framework."""
        runner = CrossBridgeRunner()
        
        assert runner.detect_framework("robot") == "robot"
        assert runner.detect_framework("pybot") == "robot"
    
    def test_detect_framework_pytest(self):
        """Test framework detection for Pytest."""
        runner = CrossBridgeRunner()
        
        assert runner.detect_framework("pytest") == "pytest"
        assert runner.detect_framework("py.test") == "pytest"
    
    def test_detect_framework_jest(self):
        """Test framework detection for Jest."""
        runner = CrossBridgeRunner()
        
        assert runner.detect_framework("jest") == "jest"
    
    def test_detect_framework_mocha(self):
        """Test framework detection for Mocha."""
        runner = CrossBridgeRunner()
        
        assert runner.detect_framework("mocha") == "mocha"
        assert runner.detect_framework("_mocha") == "mocha"
    
    def test_detect_framework_maven(self):
        """Test framework detection for Maven/JUnit."""
        runner = CrossBridgeRunner()
        
        assert runner.detect_framework("mvn") == "junit"
        assert runner.detect_framework("maven") == "junit"
    
    def test_detect_framework_unknown(self):
        """Test framework detection for unknown command."""
        runner = CrossBridgeRunner()
        
        assert runner.detect_framework("unknown-cmd") == "unknown"
    
    @patch("requests.get")
    def test_check_sidecar_success(self, mock_get):
        """Test sidecar health check when successful."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        runner = CrossBridgeRunner()
        result = runner.check_sidecar()
        
        assert result == True
        assert runner.enabled == True
        mock_get.assert_called_once()
    
    @patch("requests.get")
    def test_check_sidecar_failure(self, mock_get):
        """Test sidecar health check when unreachable."""
        mock_get.side_effect = Exception("Connection refused")
        
        runner = CrossBridgeRunner()
        result = runner.check_sidecar()
        
        assert result == False
        assert runner.enabled == False
    
    @patch("requests.get")
    def test_download_adapter_success(self, mock_get):
        """Test successful adapter download."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake tar data"
        mock_get.return_value = mock_response
        
        runner = CrossBridgeRunner()
        
        with patch("pathlib.Path.mkdir"), \
             patch("pathlib.Path.write_bytes"), \
             patch("pathlib.Path.unlink"), \
             patch("tarfile.open"):
            
            result = runner.download_adapter("pytest")
            assert result == True
    
    @patch("requests.get")
    def test_download_adapter_failure(self, mock_get):
        """Test failed adapter download."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        runner = CrossBridgeRunner()
        result = runner.download_adapter("unknown-framework")
        
        assert result == False
    
    def test_setup_robot(self):
        """Test Robot Framework setup."""
        runner = CrossBridgeRunner()
        adapter_path = Path("/fake/path/robot")
        
        with patch.object(adapter_path, "exists", return_value=True):
            config = runner.setup_robot(adapter_path)
            
            assert "env" in config
            assert "PYTHONPATH" in config["env"]
            assert "args_prefix" in config
            assert "--listener" in config["args_prefix"]
    
    def test_setup_pytest(self):
        """Test Pytest setup."""
        runner = CrossBridgeRunner()
        adapter_path = Path("/fake/path/pytest")
        
        with patch.object(adapter_path, "exists", return_value=True):
            config = runner.setup_pytest(adapter_path)
            
            assert "env" in config
            assert "PYTHONPATH" in config["env"]
            assert "PYTEST_PLUGINS" in config["env"]
    
    def test_setup_jest_without_reporters(self):
        """Test Jest setup when no reporters specified."""
        runner = CrossBridgeRunner()
        adapter_path = Path("/fake/path/jest")
        args = ["tests/"]
        
        with patch.object(adapter_path, "exists", return_value=True):
            config = runner.setup_jest(adapter_path, args)
            
            assert "args_suffix" in config
            assert any("--reporters" in arg for arg in config["args_suffix"])
    
    def test_setup_jest_with_reporters(self):
        """Test Jest setup when reporters already specified."""
        runner = CrossBridgeRunner()
        adapter_path = Path("/fake/path/jest")
        args = ["--reporters=custom", "tests/"]
        
        with patch.object(adapter_path, "exists", return_value=True):
            config = runner.setup_jest(adapter_path, args)
            
            assert "args_suffix" in config
            assert len(config["args_suffix"]) == 0
    
    @patch("subprocess.call")
    @patch("requests.get")
    def test_run_tests_without_sidecar(self, mock_get, mock_call):
        """Test running tests when sidecar is unavailable."""
        mock_get.side_effect = Exception("Connection refused")
        mock_call.return_value = 0
        
        runner = CrossBridgeRunner()
        exit_code = runner.run_tests(["pytest", "tests/"])
        
        assert exit_code == 0
        # Should run without CrossBridge monitoring
        mock_call.assert_called_once()
        # Command should be unchanged
        call_args = mock_call.call_args[0][0]
        assert call_args == ["pytest", "tests/"]
    
    @patch("subprocess.call")
    @patch("requests.get")
    def test_run_tests_with_robot(self, mock_get, mock_call):
        """Test running Robot Framework tests with CrossBridge."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        mock_call.return_value = 0
        
        runner = CrossBridgeRunner()
        adapter_path = Path(runner.adapter_dir) / "robot"
        
        with patch.object(adapter_path, "exists", return_value=True):
            exit_code = runner.run_tests(["robot", "tests/"])
            
            assert exit_code == 0
            # Should add listener args
            call_args = mock_call.call_args[0][0]
            assert "--listener" in call_args


class TestRunCommandIntegration:
    """Integration tests for run command."""
    
    @patch("cli.commands.run_commands.subprocess.call")
    @patch("cli.commands.run_commands.requests.get")
    def test_run_command_basic(self, mock_get, mock_call):
        """Test basic run command execution."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        mock_call.return_value = 0
        
        from cli.commands.run_commands import CrossBridgeRunner
        
        runner = CrossBridgeRunner()
        exit_code = runner.run_tests(["pytest", "tests/"])
        
        assert exit_code == 0
    
    def test_empty_command(self):
        """Test run command with no arguments."""
        runner = CrossBridgeRunner()
        exit_code = runner.run_tests([])
        
        assert exit_code == 1
