"""
Tests for Cypress plugin handler.
"""

import pytest
from pathlib import Path
from adapters.cypress.plugin_handler import (
    CypressPluginHandler,
    CypressPlugin
)


@pytest.fixture
def handler():
    return CypressPluginHandler()


@pytest.fixture
def sample_plugins_file(tmp_path):
    """Create a sample plugins file."""
    plugins_file = tmp_path / "cypress" / "plugins" / "index.js"
    plugins_file.parent.mkdir(parents=True, exist_ok=True)
    plugins_file.write_text("""
const cucumber = require('cypress-cucumber-preprocessor').default;
const mochawesome = require('cypress-mochawesome-reporter/plugin');
const fileUpload = require('cypress-file-upload');

module.exports = (on, config) => {
  // Cucumber preprocessor
  on('file:preprocessor', cucumber());
  
  // Mochawesome reporter
  mochawesome(on);
  
  // File upload
  on('task', {
    uploadFile(filePath) {
      return uploadHandler(filePath);
    }
  });
  
  // Before run hook
  on('before:run', async (details) => {
    console.log('Starting test run:', details);
    await setupDatabase();
  });
  
  // After run hook
  on('after:run', async (results) => {
    console.log('Test run complete:', results);
    await cleanupDatabase();
  });
  
  return config;
};
    """)
    return plugins_file


def test_detect_plugins(handler, sample_plugins_file):
    """Test plugin detection."""
    plugins = handler.detect_plugins(sample_plugins_file.parent.parent.parent)
    
    assert len(plugins) > 0
    
    plugin_names = [p.name for p in plugins]
    assert 'cypress-cucumber-preprocessor' in plugin_names
    assert 'cypress-mochawesome-reporter' in plugin_names


def test_extract_plugin_hooks(handler, sample_plugins_file):
    """Test extraction of plugin hooks."""
    plugins = handler.detect_plugins(sample_plugins_file.parent.parent.parent)
    
    # Find any plugin with hooks
    plugin_with_hooks = next((p for p in plugins if p.hooks), None)
    assert plugin_with_hooks is not None


def test_cucumber_plugin_detection(handler, sample_plugins_file):
    """Test cucumber preprocessor detection."""
    plugins = handler.detect_plugins(sample_plugins_file.parent.parent.parent)
    
    cucumber = next(
        (p for p in plugins if 'cucumber' in p.name.lower()),
        None
    )
    
    assert cucumber is not None
    assert cucumber.plugin_type == 'preprocessor'


def test_mochawesome_plugin_detection(handler, sample_plugins_file):
    """Test mochawesome reporter detection."""
    plugins = handler.detect_plugins(sample_plugins_file.parent.parent.parent)
    
    mochawesome = next(
        (p for p in plugins if 'mochawesome' in p.name.lower()),
        None
    )
    
    assert mochawesome is not None
    assert mochawesome.plugin_type == 'reporter'


def test_get_plugin_setup_code(handler, sample_plugins_file):
    """Test getting plugin setup code."""
    plugins = handler.detect_plugins(sample_plugins_file.parent.parent.parent)
    
    if plugins:
        plugin = plugins[0]
        setup_code = handler.get_plugin_setup_code(plugin)
        
        assert setup_code is not None
        assert len(setup_code) > 0


def test_convert_to_robot_framework(handler, sample_plugins_file):
    """Test conversion to Robot Framework."""
    plugins = handler.detect_plugins(sample_plugins_file.parent.parent.parent)
    
    if plugins:
        plugin = plugins[0]
        robot_code = handler.convert_to_robot_framework(plugin)
        
        assert robot_code is not None


def test_empty_plugins_directory(handler, tmp_path):
    """Test handling of empty plugins directory."""
    cypress_dir = tmp_path / "cypress"
    cypress_dir.mkdir()
    
    plugins = handler.detect_plugins(cypress_dir.parent)
    
    # Should handle gracefully
    assert isinstance(plugins, list)


def test_no_plugins_file(handler, tmp_path):
    """Test handling when no plugins file exists."""
    plugins = handler.detect_plugins(tmp_path)
    
    assert len(plugins) == 0
