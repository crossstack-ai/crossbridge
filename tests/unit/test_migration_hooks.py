"""
Unit tests for automatic sidecar hook integration during migration.

Tests cover:
- MigrationHookConfig initialization
- MigrationHookIntegrator for all frameworks (Robot, pytest, Playwright, Cypress)
- File generation and content verification
- Enable/disable functionality
- Error handling
"""

import unittest
from pathlib import Path
import tempfile
import shutil

from core.translation.migration_hooks import (
    MigrationHookConfig,
    MigrationHookIntegrator,
    integrate_hooks_after_migration
)


class TestMigrationHookConfig(unittest.TestCase):
    """Test MigrationHookConfig class"""
    
    def test_default_initialization(self):
        """Test config with default values"""
        config = MigrationHookConfig()
        
        self.assertTrue(config.enable_hooks)
        self.assertEqual(config.db_host, "10.55.12.99")
        self.assertEqual(config.db_port, 5432)
        self.assertEqual(config.db_name, "udp-native-webservices-automation")
        self.assertEqual(config.application_version, "v1.0.0")
        self.assertIsNone(config.product_name)
        self.assertEqual(config.environment, "test")
    
    def test_custom_initialization(self):
        """Test config with custom values"""
        config = MigrationHookConfig(
            enable_hooks=False,
            db_host="custom-host.com",
            db_port=5433,
            db_name="custom_db",
            application_version="v2.5.0",
            product_name="CustomApp",
            environment="production"
        )
        
        self.assertFalse(config.enable_hooks)
        self.assertEqual(config.db_host, "custom-host.com")
        self.assertEqual(config.db_port, 5433)
        self.assertEqual(config.db_name, "custom_db")
        self.assertEqual(config.application_version, "v2.5.0")
        self.assertEqual(config.product_name, "CustomApp")
        self.assertEqual(config.environment, "production")


class TestMigrationHookIntegratorRobot(unittest.TestCase):
    """Test Robot Framework hook integration"""
    
    def setUp(self):
        """Create temporary directory for tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir)
        self.config = MigrationHookConfig(
            enable_hooks=True,
            db_host="test-host.com",
            application_version="v1.5.0"
        )
        self.integrator = MigrationHookIntegrator(self.config)
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_integrate_robot_framework(self):
        """Test complete Robot Framework integration"""
        # Create sample robot file
        robot_file = self.output_dir / "test_example.robot"
        robot_file.write_text("""*** Settings ***
Library    SeleniumLibrary

*** Test Cases ***
Test Example
    Log    Hello World
""")
        
        result = self.integrator.integrate_hooks(
            target_framework="robot",
            output_dir=self.output_dir,
            migrated_files=[robot_file]
        )
        
        # Check result structure
        self.assertTrue(result.get("enabled", False))
        self.assertEqual(result["framework"], "robot")
        self.assertIn("config_file", result)
        
        # Verify config file created
        self.assertTrue((self.output_dir / "robot_config.py").exists())
        
        # Verify robot file updated
        content = robot_file.read_text()
        self.assertIn("Listener    crossbridge.RobotListener", content)
    
    def test_robot_config_file_content(self):
        """Test robot_config.py content is correct"""
        result = self.integrator.integrate_hooks(
            target_framework="robot",
            output_dir=self.output_dir,
            migrated_files=[]
        )
        
        config_file = self.output_dir / "robot_config.py"
        content = config_file.read_text()
        
        self.assertIn("CROSSBRIDGE_ENABLED = True", content)
        self.assertIn("test-host.com", content)
        self.assertIn("v1.5.0", content)
        self.assertIn("RobotApp", content)


class TestMigrationHookIntegratorPytest(unittest.TestCase):
    """Test pytest hook integration"""
    
    def setUp(self):
        """Create temporary directory for tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir)
        self.config = MigrationHookConfig(
            enable_hooks=True,
            db_host="pytest-host.com",
            application_version="v2.0.0",
            product_name="PytestApp"
        )
        self.integrator = MigrationHookIntegrator(self.config)
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_integrate_pytest_plugin(self):
        """Test pytest integration creates conftest.py"""
        result = self.integrator.integrate_hooks(
            target_framework="pytest",
            output_dir=self.output_dir,
            migrated_files=[]
        )
        
        self.assertTrue(result.get("enabled", False))
        self.assertEqual(result["framework"], "pytest")
        
        # Verify conftest.py created
        conftest = self.output_dir / "conftest.py"
        self.assertTrue(conftest.exists())
        
        content = conftest.read_text()
        self.assertIn('pytest_plugins = ["crossbridge.pytest_plugin"]', content)
        self.assertIn("pytest-host.com", content)
        self.assertIn("v2.0.0", content)
    
    def test_pytest_ini_created(self):
        """Test that pytest.ini is created"""
        result = self.integrator.integrate_hooks(
            target_framework="pytest",
            output_dir=self.output_dir,
            migrated_files=[]
        )
        
        pytest_ini = self.output_dir / "pytest.ini"
        self.assertTrue(pytest_ini.exists())
        
        content = pytest_ini.read_text()
        self.assertIn("[pytest]", content)


class TestMigrationHookIntegratorPlaywright(unittest.TestCase):
    """Test Playwright hook integration"""
    
    def setUp(self):
        """Create temporary directory for tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir)
        self.config = MigrationHookConfig(
            enable_hooks=True,
            db_host="playwright-host.com",
            application_version="v3.0.0"
        )
        self.integrator = MigrationHookIntegrator(self.config)
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_integrate_playwright_python(self):
        """Test Playwright Python uses pytest integration"""
        result = self.integrator.integrate_hooks(
            target_framework="playwright-python",
            output_dir=self.output_dir,
            migrated_files=[]
        )
        
        self.assertTrue(result.get("enabled", False))
        self.assertEqual(result["framework"], "playwright-python")
        
        # Should create conftest.py for Python
        conftest = self.output_dir / "conftest.py"
        self.assertTrue(conftest.exists())
    
    def test_integrate_playwright_typescript(self):
        """Test Playwright TypeScript creates config"""
        result = self.integrator.integrate_hooks(
            target_framework="playwright-typescript",
            output_dir=self.output_dir,
            migrated_files=[]
        )
        
        self.assertTrue(result.get("enabled", False))
        self.assertEqual(result["framework"], "playwright-typescript")
        
        # Should create playwright.config.ts
        config_file = self.output_dir / "playwright.config.ts"
        self.assertTrue(config_file.exists())
        
        content = config_file.read_text()
        self.assertIn("import { defineConfig }", content)
        self.assertIn("'crossbridge'", content)
        self.assertIn("playwright-host.com", content)
        self.assertIn("v3.0.0", content)


class TestMigrationHookIntegratorCypress(unittest.TestCase):
    """Test Cypress hook integration"""
    
    def setUp(self):
        """Create temporary directory for tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir)
        self.config = MigrationHookConfig(
            enable_hooks=True,
            db_host="cypress-host.com",
            application_version="v4.0.0",
            product_name="CypressApp"
        )
        self.integrator = MigrationHookIntegrator(self.config)
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_integrate_cypress_plugin(self):
        """Test Cypress integration"""
        result = self.integrator.integrate_hooks(
            target_framework="cypress",
            output_dir=self.output_dir,
            migrated_files=[]
        )
        
        self.assertTrue(result.get("enabled", False))
        self.assertEqual(result["framework"], "cypress")
        
        # Verify cypress.config.js created
        config_file = self.output_dir / "cypress.config.js"
        self.assertTrue(config_file.exists())
        
        content = config_file.read_text()
        self.assertIn("defineConfig", content)
        self.assertIn("setupNodeEvents", content)
        self.assertIn("crossbridge.register", content)
    
    def test_cypress_support_file_created(self):
        """Test that support/e2e.js is created"""
        result = self.integrator.integrate_hooks(
            target_framework="cypress",
            output_dir=self.output_dir,
            migrated_files=[]
        )
        
        support_file = self.output_dir / "cypress" / "support" / "e2e.js"
        self.assertTrue(support_file.exists())


class TestMigrationHookIntegratorMain(unittest.TestCase):
    """Test main integration logic"""
    
    def setUp(self):
        """Create temporary directory for tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir)
        self.config = MigrationHookConfig(enable_hooks=True)
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_integrate_hooks_disabled(self):
        """Test that hooks can be disabled"""
        config = MigrationHookConfig(enable_hooks=False)
        integrator = MigrationHookIntegrator(config)
        
        result = integrator.integrate_hooks(
            target_framework="robot",
            output_dir=self.output_dir,
            migrated_files=[]
        )
        
        self.assertFalse(result.get("enabled", True))
        self.assertEqual(result.get("reason"), "disabled_by_config")
    
    def test_integrate_hooks_unsupported_framework(self):
        """Test handling of unsupported framework"""
        integrator = MigrationHookIntegrator(self.config)
        
        result = integrator.integrate_hooks(
            target_framework="unsupported-framework",
            output_dir=self.output_dir,
            migrated_files=[]
        )
        
        self.assertFalse(result.get("enabled", True))
        self.assertEqual(result.get("reason"), "unsupported_framework")
    
    def test_all_supported_frameworks(self):
        """Test that all advertised frameworks are supported"""
        integrator = MigrationHookIntegrator(self.config)
        
        frameworks = [
            "robot",
            "pytest",
            "playwright-python",
            "playwright-typescript",
            "cypress"
        ]
        
        for framework in frameworks:
            with self.subTest(framework=framework):
                # Create fresh temp dir for each framework
                temp_dir = tempfile.mkdtemp()
                try:
                    result = integrator.integrate_hooks(
                        target_framework=framework,
                        output_dir=Path(temp_dir),
                        migrated_files=[]
                    )
                    
                    self.assertTrue(
                        result.get("enabled", False),
                        f"Framework {framework} should be supported"
                    )
                finally:
                    shutil.rmtree(temp_dir)


class TestIntegrateHooksAfterMigration(unittest.TestCase):
    """Test convenience function"""
    
    def setUp(self):
        """Create temporary directory for tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)
    
    def test_convenience_function_robot(self):
        """Test convenience function for Robot"""
        config = MigrationHookConfig(
            enable_hooks=True,
            db_host="test-host.com",
            application_version="v1.0.0"
        )
        
        result = integrate_hooks_after_migration(
            target_framework="robot",
            output_dir=self.output_dir,
            migrated_files=[],
            config=config
        )
        
        self.assertTrue(result.get("enabled", False))
        self.assertTrue((self.output_dir / "robot_config.py").exists())
    
    def test_convenience_function_disabled(self):
        """Test convenience function with hooks disabled"""
        result = integrate_hooks_after_migration(
            target_framework="robot",
            output_dir=self.output_dir,
            migrated_files=[],
            enable_hooks=False
        )
        
        self.assertFalse(result.get("enabled", True))


class TestDisableInstructions(unittest.TestCase):
    """Test disable instructions generation"""
    
    def test_generate_disable_instructions_robot(self):
        """Test disable instructions for Robot"""
        config = MigrationHookConfig()
        integrator = MigrationHookIntegrator(config)
        
        instructions = integrator.generate_disable_instructions("robot")
        
        # Should contain useful instructions
        self.assertGreater(len(instructions), 20)
        self.assertIn("Listener", instructions)
        self.assertIn("robot_config.py", instructions)
    
    def test_generate_disable_instructions_pytest(self):
        """Test disable instructions for pytest"""
        config = MigrationHookConfig()
        integrator = MigrationHookIntegrator(config)
        
        instructions = integrator.generate_disable_instructions("pytest")
        
        # Should contain useful instructions
        self.assertGreater(len(instructions), 20)
        self.assertIn("conftest.py", instructions)
        self.assertIn("crossbridge_enabled", instructions)
    
    def test_generate_disable_instructions_cypress(self):
        """Test disable instructions for Cypress"""
        config = MigrationHookConfig()
        integrator = MigrationHookIntegrator(config)
        
        instructions = integrator.generate_disable_instructions("cypress")
        
        # Should contain useful instructions
        self.assertGreater(len(instructions), 20)
        self.assertIn("cypress.config.js", instructions)
        self.assertIn("crossbridge.register", instructions)


if __name__ == "__main__":
    unittest.main()
