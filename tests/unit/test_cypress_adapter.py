"""
Unit tests for Cypress adapter.

Tests cover:
- Cypress project detection (modern and legacy configs)
- Test file parsing (JavaScript and TypeScript)
- Test discovery
- Test execution
- Custom command extraction
- Fixture detection
- Page object detection
- Error handling
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from adapters.cypress import (
    CypressAdapter,
    CypressExtractor,
    CypressProjectDetector,
    CypressTestParser,
    CypressConfig,
    CypressTestType,
)


class TestCypressProjectDetector:
    """Test Cypress project detection."""
    
    def test_detect_modern_config_js(self, tmp_path):
        """Test detection of modern cypress.config.js."""
        config_file = tmp_path / "cypress.config.js"
        config_file.write_text("""
        const { defineConfig } = require('cypress')
        
        module.exports = defineConfig({
          e2e: {
            setupNodeEvents(on, config) {},
          },
        })
        """, encoding='utf-8')
        
        # Create e2e directory with test
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        (e2e_dir / "test.cy.js").write_text("it('test', () => {})", encoding='utf-8')
        
        detector = CypressProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.config_file.name == "cypress.config.js"
        assert config.test_type == CypressTestType.E2E
    
    def test_detect_modern_config_ts(self, tmp_path):
        """Test detection of modern cypress.config.ts."""
        config_file = tmp_path / "cypress.config.ts"
        config_file.write_text("""
        import { defineConfig } from 'cypress'
        
        export default defineConfig({
          e2e: {
            setupNodeEvents(on, config) {},
          },
        })
        """, encoding='utf-8')
        
        # Create TypeScript config
        tsconfig = tmp_path / "tsconfig.json"
        tsconfig.write_text('{"compilerOptions": {}}', encoding='utf-8')
        
        # Create e2e directory with test
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        (e2e_dir / "test.cy.ts").write_text("it('test', () => {})", encoding='utf-8')
        
        detector = CypressProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.config_file.name == "cypress.config.ts"
        assert config.has_typescript is True
    
    def test_detect_legacy_config(self, tmp_path):
        """Test detection of legacy cypress.json."""
        config_file = tmp_path / "cypress.json"
        config_file.write_text(json.dumps({
            "integrationFolder": "cypress/integration",
            "supportFile": "cypress/support/index.js"
        }), encoding='utf-8')
        
        # Create integration directory with test
        integration_dir = tmp_path / "cypress" / "integration"
        integration_dir.mkdir(parents=True)
        (integration_dir / "test.spec.js").write_text("it('test', () => {})", encoding='utf-8')
        
        detector = CypressProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.config_file.name == "cypress.json"
    
    def test_detect_component_testing(self, tmp_path):
        """Test detection of component testing setup."""
        config_file = tmp_path / "cypress.config.js"
        config_file.write_text("module.exports = {}", encoding='utf-8')
        
        # Create component directory with test
        component_dir = tmp_path / "cypress" / "component"
        component_dir.mkdir(parents=True)
        (component_dir / "Button.cy.js").write_text("it('test', () => {})", encoding='utf-8')
        
        detector = CypressProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.test_type == CypressTestType.COMPONENT
    
    def test_detect_support_files(self, tmp_path):
        """Test detection of support files."""
        config_file = tmp_path / "cypress.config.js"
        config_file.write_text("module.exports = {}", encoding='utf-8')
        
        # Create directory structure
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        (e2e_dir / "test.cy.js").write_text("it('test', () => {})", encoding='utf-8')
        
        support_dir = tmp_path / "cypress" / "support"
        support_dir.mkdir(parents=True)
        support_file = support_dir / "e2e.js"
        support_file.write_text("// support code", encoding='utf-8')
        
        detector = CypressProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.support_file is not None
        assert config.support_file.name == "e2e.js"
    
    def test_detect_fixtures(self, tmp_path):
        """Test detection of fixtures directory."""
        config_file = tmp_path / "cypress.config.js"
        config_file.write_text("module.exports = {}", encoding='utf-8')
        
        # Create directory structure
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        (e2e_dir / "test.cy.js").write_text("it('test', () => {})", encoding='utf-8')
        
        fixtures_dir = tmp_path / "cypress" / "fixtures"
        fixtures_dir.mkdir(parents=True)
        (fixtures_dir / "data.json").write_text('{}', encoding='utf-8')
        
        detector = CypressProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.fixtures_dir is not None
        assert config.fixtures_dir.name == "fixtures"
    
    def test_detect_cypress_version(self, tmp_path):
        """Test detection of Cypress version from package.json."""
        package_json = tmp_path / "package.json"
        package_json.write_text(json.dumps({
            "devDependencies": {
                "cypress": "^13.6.0"
            }
        }), encoding='utf-8')
        
        config_file = tmp_path / "cypress.config.js"
        config_file.write_text("module.exports = {}", encoding='utf-8')
        
        # Create e2e directory with test
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        (e2e_dir / "test.cy.js").write_text("it('test', () => {})", encoding='utf-8')
        
        detector = CypressProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is not None
        assert config.cypress_version == "13.6.0"
    
    def test_detect_no_cypress_project(self, tmp_path):
        """Test detection returns None for non-Cypress project."""
        detector = CypressProjectDetector(str(tmp_path))
        config = detector.detect()
        
        assert config is None


class TestCypressTestParser:
    """Test Cypress test file parsing."""
    
    def test_parse_simple_test(self, tmp_path):
        """Test parsing simple Cypress test."""
        test_file = tmp_path / "login.cy.js"
        test_file.write_text("""
        it('should log in successfully', () => {
          cy.visit('/login')
          cy.get('#username').type('testuser')
          cy.get('#password').type('password123')
          cy.get('button[type="submit"]').click()
          cy.url().should('include', '/dashboard')
        })
        """, encoding='utf-8')
        
        parser = CypressTestParser()
        tests = parser.parse_test_file(test_file)
        
        assert len(tests) == 1
        assert tests[0]['name'] == 'should log in successfully'
        assert tests[0]['full_name'] == 'should log in successfully'
    
    def test_parse_describe_block(self, tmp_path):
        """Test parsing describe blocks."""
        test_file = tmp_path / "auth.cy.js"
        test_file.write_text("""
        describe('Authentication', () => {
          it('should log in', () => {
            cy.visit('/login')
          })
          
          it('should log out', () => {
            cy.get('.logout').click()
          })
        })
        """, encoding='utf-8')
        
        parser = CypressTestParser()
        tests = parser.parse_test_file(test_file)
        
        assert len(tests) == 2
        assert tests[0]['describe'] == 'Authentication'
        assert tests[0]['full_name'] == 'Authentication > should log in'
        assert tests[1]['full_name'] == 'Authentication > should log out'
    
    def test_parse_nested_describes(self, tmp_path):
        """Test parsing nested describe blocks."""
        test_file = tmp_path / "nested.cy.js"
        test_file.write_text("""
        describe('User Management', () => {
          describe('Login', () => {
            it('should accept valid credentials', () => {})
          })
          
          describe('Registration', () => {
            it('should create new user', () => {})
          })
        })
        """, encoding='utf-8')
        
        parser = CypressTestParser()
        tests = parser.parse_test_file(test_file)
        
        assert len(tests) == 2
        # Parser finds the closest preceding describe
        assert 'should accept valid credentials' in tests[0]['name']
        assert 'should create new user' in tests[1]['name']
    
    def test_parse_typescript_test(self, tmp_path):
        """Test parsing TypeScript test file."""
        test_file = tmp_path / "test.cy.ts"
        test_file.write_text("""
        describe('TypeScript Test', () => {
          it('should work with types', () => {
            const name: string = 'test'
            cy.visit('/')
          })
        })
        """, encoding='utf-8')
        
        parser = CypressTestParser()
        tests = parser.parse_test_file(test_file)
        
        assert len(tests) == 1
        assert tests[0]['name'] == 'should work with types'
    
    def test_parse_ignores_comments(self, tmp_path):
        """Test parser ignores commented out tests."""
        test_file = tmp_path / "commented.cy.js"
        test_file.write_text("""
        describe('Active Tests', () => {
          it('active test', () => {})
          
          // it('commented test', () => {})
          
          /* 
          it('block commented test', () => {})
          */
        })
        """, encoding='utf-8')
        
        parser = CypressTestParser()
        tests = parser.parse_test_file(test_file)
        
        # Should only find the active test
        assert len(tests) == 1
        assert tests[0]['name'] == 'active test'
    
    def test_extract_custom_commands(self, tmp_path):
        """Test extracting custom Cypress commands."""
        support_file = tmp_path / "commands.js"
        support_file.write_text("""
        Cypress.Commands.add('login', (username, password) => {
          cy.visit('/login')
          cy.get('#username').type(username)
          cy.get('#password').type(password)
          cy.get('button').click()
        })
        
        Cypress.Commands.add('logout', () => {
          cy.get('.logout-btn').click()
        })
        """, encoding='utf-8')
        
        parser = CypressTestParser()
        commands = parser.extract_custom_commands(support_file)
        
        assert len(commands) == 2
        assert 'login' in commands
        assert 'logout' in commands


class TestCypressAdapter:
    """Test CypressAdapter."""
    
    def test_adapter_requires_valid_project(self, tmp_path):
        """Test adapter raises error for invalid project."""
        with pytest.raises(ValueError, match="Could not detect Cypress project"):
            CypressAdapter(str(tmp_path))
    
    def test_adapter_with_manual_config(self, tmp_path):
        """Test adapter accepts manual configuration."""
        config_file = tmp_path / "cypress.config.js"
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        
        config = CypressConfig(
            project_root=tmp_path,
            config_file=config_file,
            specs_dir=e2e_dir,
            test_type=CypressTestType.E2E,
            has_typescript=False
        )
        
        adapter = CypressAdapter(str(tmp_path), config=config)
        
        assert adapter.config == config
    
    def test_discover_tests(self, tmp_path):
        """Test discovering tests from spec files."""
        config_file = tmp_path / "cypress.config.js"
        config_file.write_text("module.exports = {}", encoding='utf-8')
        
        # Create test files
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        
        (e2e_dir / "login.cy.js").write_text("""
        describe('Login', () => {
          it('should login', () => {})
          it('should logout', () => {})
        })
        """, encoding='utf-8')
        
        (e2e_dir / "search.cy.js").write_text("""
        it('should search', () => {})
        """, encoding='utf-8')
        
        adapter = CypressAdapter(str(tmp_path))
        tests = adapter.discover_tests()
        
        assert len(tests) == 3
        assert 'Login > should login' in tests
        assert 'Login > should logout' in tests
        assert 'should search' in tests
    
    @patch("subprocess.run")
    def test_run_tests(self, mock_run, tmp_path):
        """Test running tests with Cypress."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Tests passed"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        config_file = tmp_path / "cypress.config.js"
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        (e2e_dir / "test.cy.js").write_text("it('test', () => {})", encoding='utf-8')
        
        config = CypressConfig(
            project_root=tmp_path,
            config_file=config_file,
            specs_dir=e2e_dir,
            test_type=CypressTestType.E2E
        )
        
        adapter = CypressAdapter(str(tmp_path), config=config)
        results = adapter.run_tests()
        
        assert mock_run.called
        assert len(results) >= 1
        
        # Verify command structure
        call_args = mock_run.call_args[0][0]
        assert "npx" in call_args or "cypress" in call_args
    
    @patch("subprocess.run")
    def test_run_tests_with_spec(self, mock_run, tmp_path):
        """Test running specific spec file."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        config_file = tmp_path / "cypress.config.js"
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        
        config = CypressConfig(
            project_root=tmp_path,
            config_file=config_file,
            specs_dir=e2e_dir,
            test_type=CypressTestType.E2E
        )
        
        adapter = CypressAdapter(str(tmp_path), config=config)
        results = adapter.run_tests(spec="cypress/e2e/login.cy.js")
        
        # Verify spec filter was applied
        call_args = mock_run.call_args[0][0]
        assert "--spec" in call_args
    
    @patch("subprocess.run")
    def test_run_tests_with_browser(self, mock_run, tmp_path):
        """Test running tests with specific browser."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        config_file = tmp_path / "cypress.config.js"
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        
        config = CypressConfig(
            project_root=tmp_path,
            config_file=config_file,
            specs_dir=e2e_dir,
            test_type=CypressTestType.E2E
        )
        
        adapter = CypressAdapter(str(tmp_path), config=config)
        results = adapter.run_tests(browser="chrome")
        
        # Verify browser was specified
        call_args = mock_run.call_args[0][0]
        assert "--browser" in call_args
        assert "chrome" in call_args
    
    def test_get_config_info(self, tmp_path):
        """Test getting configuration information."""
        config_file = tmp_path / "cypress.config.js"
        e2e_dir = tmp_path / "cypress" / "e2e"
        
        config = CypressConfig(
            project_root=tmp_path,
            config_file=config_file,
            specs_dir=e2e_dir,
            test_type=CypressTestType.E2E,
            has_typescript=True,
            cypress_version="13.6.0"
        )
        
        adapter = CypressAdapter(str(tmp_path), config=config)
        info = adapter.get_config_info()
        
        assert info['test_type'] == 'e2e'
        assert info['has_typescript'] == 'True'
        assert info['cypress_version'] == '13.6.0'


class TestCypressExtractor:
    """Test CypressExtractor."""
    
    def test_extractor_requires_valid_project(self, tmp_path):
        """Test extractor raises error for invalid project."""
        with pytest.raises(ValueError, match="Could not detect Cypress project"):
            CypressExtractor(str(tmp_path))
    
    def test_extract_tests(self, tmp_path):
        """Test extracting test metadata."""
        config_file = tmp_path / "cypress.config.js"
        config_file.write_text("module.exports = {}", encoding='utf-8')
        
        # Create test files
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        
        (e2e_dir / "login.cy.js").write_text("""
        describe('Login Tests', () => {
          it('valid login', () => {})
        })
        """, encoding='utf-8')
        
        extractor = CypressExtractor(str(tmp_path))
        tests = extractor.extract_tests()
        
        assert len(tests) == 1
        assert tests[0].test_name == 'valid login'
        assert tests[0].framework == 'cypress'
        assert 'e2e' in tests[0].tags
    
    def test_extract_custom_commands(self, tmp_path):
        """Test extracting custom commands."""
        config_file = tmp_path / "cypress.config.js"
        config_file.write_text("module.exports = {}", encoding='utf-8')
        
        # Create directory structure
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        (e2e_dir / "test.cy.js").write_text("it('test', () => {})", encoding='utf-8')
        
        support_dir = tmp_path / "cypress" / "support"
        support_dir.mkdir(parents=True)
        commands_file = support_dir / "commands.js"
        commands_file.write_text("""
        Cypress.Commands.add('login', () => {})
        Cypress.Commands.add('selectProduct', () => {})
        """, encoding='utf-8')
        
        # Create config with support file
        config = CypressConfig(
            project_root=tmp_path,
            config_file=config_file,
            specs_dir=e2e_dir,
            test_type=CypressTestType.E2E,
            support_file=commands_file
        )
        
        extractor = CypressExtractor(str(tmp_path), config=config)
        commands = extractor.extract_custom_commands()
        
        assert len(commands) == 2
        assert commands[0]['name'] == 'login'
        assert commands[1]['name'] == 'selectProduct'
    
    def test_extract_fixtures(self, tmp_path):
        """Test extracting fixtures."""
        config_file = tmp_path / "cypress.config.js"
        config_file.write_text("module.exports = {}", encoding='utf-8')
        
        # Create directory structure
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        (e2e_dir / "test.cy.js").write_text("it('test', () => {})", encoding='utf-8')
        
        fixtures_dir = tmp_path / "cypress" / "fixtures"
        fixtures_dir.mkdir(parents=True)
        (fixtures_dir / "users.json").write_text('{}', encoding='utf-8')
        (fixtures_dir / "products.json").write_text('{}', encoding='utf-8')
        
        # Create config with fixtures
        config = CypressConfig(
            project_root=tmp_path,
            config_file=config_file,
            specs_dir=e2e_dir,
            test_type=CypressTestType.E2E,
            fixtures_dir=fixtures_dir
        )
        
        extractor = CypressExtractor(str(tmp_path), config=config)
        fixtures = extractor.extract_fixtures()
        
        assert len(fixtures) == 2
        assert any(f['name'] == 'users' for f in fixtures)
        assert any(f['name'] == 'products' for f in fixtures)
    
    def test_extract_page_objects(self, tmp_path):
        """Test extracting page objects."""
        config_file = tmp_path / "cypress.config.js"
        config_file.write_text("module.exports = {}", encoding='utf-8')
        
        # Create directory structure
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        (e2e_dir / "test.cy.js").write_text("it('test', () => {})", encoding='utf-8')
        
        support_dir = tmp_path / "cypress" / "support"
        support_dir.mkdir(parents=True)
        
        # Create page object files
        (support_dir / "LoginPage.js").write_text("""
        class LoginPage {
          visit() {
            cy.visit('/login')
          }
          
          login(username, password) {
            cy.get('#username').type(username)
            cy.get('#password').type(password)
            cy.get('button').click()
          }
        }
        
        export default LoginPage
        """, encoding='utf-8')
        
        config = CypressConfig(
            project_root=tmp_path,
            config_file=config_file,
            specs_dir=e2e_dir,
            test_type=CypressTestType.E2E
        )
        
        extractor = CypressExtractor(str(tmp_path), config=config)
        page_objects = extractor.extract_page_objects()
        
        assert len(page_objects) == 1
        assert page_objects[0]['class_name'] == 'LoginPage'


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_parse_malformed_test_file(self, tmp_path):
        """Test parsing handles malformed test files."""
        test_file = tmp_path / "malformed.cy.js"
        test_file.write_text("this is { not valid javascript", encoding='utf-8')
        
        parser = CypressTestParser()
        tests = parser.parse_test_file(test_file)
        
        # Should return empty list, not crash
        assert tests == []
    
    def test_parse_empty_test_file(self, tmp_path):
        """Test parsing handles empty test files."""
        test_file = tmp_path / "empty.cy.js"
        test_file.write_text("", encoding='utf-8')
        
        parser = CypressTestParser()
        tests = parser.parse_test_file(test_file)
        
        assert tests == []
    
    @patch("subprocess.run")
    def test_adapter_handles_timeout(self, mock_run, tmp_path):
        """Test adapter handles subprocess timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("cypress", 300)
        
        config_file = tmp_path / "cypress.config.js"
        e2e_dir = tmp_path / "cypress" / "e2e"
        e2e_dir.mkdir(parents=True)
        
        config = CypressConfig(
            project_root=tmp_path,
            config_file=config_file,
            specs_dir=e2e_dir,
            test_type=CypressTestType.E2E
        )
        
        adapter = CypressAdapter(str(tmp_path), config=config)
        results = adapter.run_tests()
        
        # Should return error result, not crash
        assert len(results) == 1
        assert results[0].status == "fail"
        assert "timed out" in results[0].message.lower()
    
    def test_detector_handles_missing_specs(self, tmp_path):
        """Test detector handles config without spec files."""
        config_file = tmp_path / "cypress.config.js"
        config_file.write_text("module.exports = {}", encoding='utf-8')
        
        # Create cypress directory but no test files
        cypress_dir = tmp_path / "cypress" / "e2e"
        cypress_dir.mkdir(parents=True)
        
        detector = CypressProjectDetector(str(tmp_path))
        config = detector.detect()
        
        # Should return None if no test files found
        assert config is None
