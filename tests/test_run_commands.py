"""
Unit tests for CrossBridge Run Commands

Tests cover:
- Framework detection (Robot, Pytest, Jest, Mocha, Maven/JUnit)
- Sidecar health checking
- Adapter management (download, caching)
- Test execution workflows
- CLI option handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import subprocess
import os
import time

from cli.commands.run_commands import CrossBridgeRunner


class TestCrossBridgeRunner:
    """Tests for CrossBridgeRunner class."""
    
    def test_init_default_values(self):
        """Test initialization with default env values."""
        with patch.dict(os.environ, {"HOME": "/tmp"}, clear=False):
            runner = CrossBridgeRunner()
            
            assert runner.sidecar_host == "localhost"
            assert runner.sidecar_port == "8765"
            assert runner.enabled == True
            assert ".crossbridge" in runner.adapter_dir
    
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
        
        with patch("pathlib.Path.exists", return_value=True):
            config = runner.setup_robot(adapter_path)
            
            assert "env" in config
            assert "PYTHONPATH" in config["env"]
            assert "args_prefix" in config
            assert "--listener" in config["args_prefix"]
    
    def test_setup_pytest(self):
        """Test Pytest setup."""
        runner = CrossBridgeRunner()
        adapter_path = Path("/fake/path/pytest")
        
        with patch("pathlib.Path.exists", return_value=True):
            config = runner.setup_pytest(adapter_path)
            
            assert "env" in config
            assert "PYTHONPATH" in config["env"]
            assert "PYTEST_PLUGINS" in config["env"]
    
    def test_setup_jest_without_reporters(self):
        """Test Jest setup when no reporters specified."""
        runner = CrossBridgeRunner()
        adapter_path = Path("/fake/path/jest")
        args = ["tests/"]
        
        with patch("pathlib.Path.exists", return_value=True):
            config = runner.setup_jest(adapter_path, args)
            
            assert "args_suffix" in config
            assert any("--reporters" in arg for arg in config["args_suffix"])
    
    def test_setup_jest_with_reporters(self):
        """Test Jest setup when reporters already specified."""
        runner = CrossBridgeRunner()
        adapter_path = Path("/fake/path/jest")
        args = ["--reporters=custom", "tests/"]
        
        with patch("pathlib.Path.exists", return_value=True):
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
        
        with patch("pathlib.Path.exists", return_value=True):
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


class TestFrameworkSetup:
    """Test framework-specific setup configurations."""
    
    def test_setup_mocha(self):
        """Test Mocha setup configuration."""
        runner = CrossBridgeRunner()
        adapter_path = Path("/fake/path/mocha")
        args = ["tests/"]
        
        with patch("pathlib.Path.exists", return_value=True):
            config = runner.setup_mocha(adapter_path, args)
            
            assert "args_suffix" in config
            assert "--reporter" in config["args_suffix"]
    
    def test_setup_junit(self):
        """Test JUnit setup configuration."""
        runner = CrossBridgeRunner()
        adapter_path = Path("/fake/path/junit")
        
        with patch("pathlib.Path.exists", return_value=True):
            config = runner.setup_junit(adapter_path)
            
            # JUnit returns empty config (manual setup required)
            assert isinstance(config, dict)
    
    @patch.object(CrossBridgeRunner, "download_adapter")
    def test_setup_downloads_missing_adapter(self, mock_download):
        """Test that setup downloads adapter if missing."""
        mock_download.return_value = True
        
        runner = CrossBridgeRunner()
        adapter_path = Path("/fake/path/pytest")
        
        with patch("pathlib.Path.exists", return_value=False):
            config = runner.setup_pytest(adapter_path)
            
            mock_download.assert_called_once_with("pytest")
            assert "env" in config


class TestAdapterCaching:
    """Test adapter download and caching logic."""
    
    @patch("cli.commands.run_commands.tarfile.open")
    @patch("cli.commands.run_commands.requests.get")
    def test_adapter_cache_recent(self, mock_get, mock_tar):
        """Test that recent adapters are not re-downloaded."""
        runner = CrossBridgeRunner()
        adapter_path = Path(runner.adapter_dir) / "pytest"
        
        # Mock adapter exists and is recent (modified 1 hour ago)
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_mtime = time.time() - 3600  # 1 hour ago
            
            result = runner.download_adapter("pytest")
            
            assert result == True
            mock_get.assert_not_called()  # Should use cache
    
    @patch("cli.commands.run_commands.tarfile.open")
    @patch("cli.commands.run_commands.requests.get")
    def test_adapter_cache_old(self, mock_get, mock_tar):
        """Test that old adapters are re-downloaded."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake tar content"
        mock_get.return_value = mock_response
        
        runner = CrossBridgeRunner()
        adapter_path = Path(runner.adapter_dir) / "pytest"
        
        # Mock adapter exists but is old (modified 2 days ago)
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.stat") as mock_stat, \
             patch("pathlib.Path.mkdir"), \
             patch("pathlib.Path.write_bytes"), \
             patch("pathlib.Path.unlink"):
            mock_stat.return_value.st_mtime = time.time() - 172800  # 2 days ago
            mock_tar.return_value.__enter__ = Mock()
            mock_tar.return_value.__exit__ = Mock()
            
            result = runner.download_adapter("pytest")
            
            assert result == True
            mock_get.assert_called_once()  # Should re-download


class TestNpmYarnFrameworkDetection:
    """Test framework detection for npm/yarn commands."""
    
    @patch("pathlib.Path.exists")
    @patch("builtins.open", create=True)
    def test_npm_test_detects_jest(self, mock_open, mock_exists):
        """Test that npm test detects Jest from package.json."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__ = Mock(
            return_value=Mock(read=Mock(return_value='{"dependencies": {"jest": "^27.0.0"}}'))
        )
        
        runner = CrossBridgeRunner()
        framework = runner.detect_framework("npm", "test")
        
        assert framework == "jest"
    
    @patch("pathlib.Path.exists")  
    @patch("builtins.open", create=True)
    def test_yarn_test_detects_mocha(self, mock_open, mock_exists):
        """Test that yarn test detects Mocha from package.json."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__ = Mock(
            return_value=Mock(read=Mock(return_value='{"dependencies": {"mocha": "^9.0.0"}}'))
        )
        
        runner = CrossBridgeRunner()
        framework = runner.detect_framework("yarn", "test")
        
        assert framework == "mocha"


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @patch("cli.commands.run_commands.requests.get")
    def test_sidecar_timeout(self, mock_get):
        """Test handling of sidecar timeout."""
        import requests
        mock_get.side_effect = requests.Timeout("Connection timeout")
        
        runner = CrossBridgeRunner()
        result = runner.check_sidecar()
        
        assert result == False
        assert runner.enabled == False
    
    @patch("cli.commands.run_commands.requests.get")
    def test_adapter_download_network_error(self, mock_get):
        """Test handling network error during adapter download."""
        mock_get.side_effect = Exception("Network error")
        
        runner = CrossBridgeRunner()
        result = runner.download_adapter("pytest")
        
        assert result == False
    
    @patch("cli.commands.run_commands.subprocess.call")
    @patch("cli.commands.run_commands.requests.get")
    def test_test_execution_failure(self, mock_get, mock_call):
        """Test handling of test execution failure."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        mock_call.return_value = 1  # Test failure exit code
        
        runner = CrossBridgeRunner()
        
        with patch("pathlib.Path.exists", return_value=True):
            exit_code = runner.run_tests(["pytest", "tests/"])
            
            assert exit_code == 1


class TestLogging:
    """Test logging integration."""
    
    @patch("cli.commands.run_commands.logger")
    @patch("cli.commands.run_commands.requests.get")
    def test_sidecar_check_logs(self, mock_get, mock_logger):
        """Test that sidecar checks are logged properly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        runner = CrossBridgeRunner()
        runner.check_sidecar()
        
        # Verify logging calls
        assert mock_logger.debug.called or mock_logger.info.called
    
    @patch("cli.commands.run_commands.logger")
    @patch("cli.commands.run_commands.subprocess.call")
    @patch("cli.commands.run_commands.requests.get")
    def test_test_execution_logs(self, mock_get, mock_call, mock_logger):
        """Test that test execution is logged."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        mock_call.return_value = 0
        
        runner = CrossBridgeRunner()
        
        with patch("pathlib.Path.exists", return_value=True):
            runner.run_tests(["robot", "tests/"])
            
            # Verify framework detection logged
            assert any("robot" in str(call).lower() for call in mock_logger.info.call_args_list)
