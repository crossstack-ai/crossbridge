"""
CrossBridge Migration Hook Integration

Automatically enables sidecar observability hooks during migration/transformation.
Can be disabled via configuration flag.

This module ensures that after transforming tests to a target framework,
the appropriate sidecar hook is automatically configured so tests are
observable without any additional manual setup.
"""

from pathlib import Path
from typing import Dict, Optional, List
import json
import logging

logger = logging.getLogger(__name__)


class MigrationHookConfig:
    """Configuration for automatic hook integration during migration"""
    
    def __init__(
        self,
        enable_hooks: bool = True,
        db_host: str = "10.55.12.99",
        db_port: int = 5432,
        db_name: str = "udp-native-webservices-automation",
        application_version: str = "v1.0.0",
        product_name: Optional[str] = None,
        environment: str = "test"
    ):
        self.enable_hooks = enable_hooks
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.application_version = application_version
        self.product_name = product_name
        self.environment = environment


class MigrationHookIntegrator:
    """
    Integrates sidecar hooks into migrated test frameworks.
    
    Supports all target frameworks:
    - Robot Framework (pytest plugin)
    - Playwright Python (pytest plugin)
    - Playwright TypeScript (playwright reporter)
    - Pytest (pytest plugin)
    - Cypress (cypress plugin)
    """
    
    # Framework hook mappings
    FRAMEWORK_HOOKS = {
        "robot": {
            "type": "robot_listener",
            "files": ["robot_listener.py"],
            "config_file": "robot_config.py",
            "enabled_by": "listener"
        },
        "playwright-python": {
            "type": "pytest_plugin",
            "files": ["conftest.py"],
            "config_file": "pytest.ini",
            "enabled_by": "plugin"
        },
        "playwright-typescript": {
            "type": "playwright_reporter",
            "files": ["playwright.config.ts"],
            "config_file": "playwright.config.ts",
            "enabled_by": "reporter"
        },
        "pytest": {
            "type": "pytest_plugin",
            "files": ["conftest.py"],
            "config_file": "pytest.ini",
            "enabled_by": "plugin"
        },
        "cypress": {
            "type": "cypress_plugin",
            "files": ["cypress.config.js", "cypress/support/e2e.js"],
            "config_file": "cypress.config.js",
            "enabled_by": "plugin"
        },
    }
    
    def __init__(self, config: MigrationHookConfig):
        self.config = config
    
    def integrate_hooks(
        self,
        target_framework: str,
        output_dir: Path,
        migrated_files: List[Path]
    ) -> Dict[str, any]:
        """
        Integrate sidecar hooks into migrated project.
        
        Args:
            target_framework: Target framework name
            output_dir: Root directory of migrated project
            migrated_files: List of migrated test files
            
        Returns:
            Dict with integration results
        """
        if not self.config.enable_hooks:
            logger.info("Hook integration disabled via configuration")
            return {
                "enabled": False,
                "reason": "disabled_by_config",
                "framework": target_framework
            }
        
        # Normalize framework name
        framework_key = target_framework.lower().replace("_", "-")
        
        if framework_key not in self.FRAMEWORK_HOOKS:
            logger.warning(f"No hook configuration for framework: {target_framework}")
            return {
                "enabled": False,
                "reason": "unsupported_framework",
                "framework": target_framework
            }
        
        hook_info = self.FRAMEWORK_HOOKS[framework_key]
        
        # Execute framework-specific integration
        method_name = f"_integrate_{hook_info['type']}"
        integration_method = getattr(self, method_name, None)
        
        if not integration_method:
            logger.error(f"Integration method not found: {method_name}")
            return {
                "enabled": False,
                "reason": "integration_method_missing",
                "framework": target_framework
            }
        
        try:
            result = integration_method(output_dir, hook_info)
            result["framework"] = target_framework
            result["enabled"] = True
            return result
        except Exception as e:
            logger.error(f"Hook integration failed: {e}", exc_info=True)
            return {
                "enabled": False,
                "reason": "integration_error",
                "error": str(e),
                "framework": target_framework
            }
    
    def _integrate_robot_listener(self, output_dir: Path, hook_info: Dict) -> Dict:
        """Integrate Robot Framework listener"""
        
        # Create robot_config.py with listener configuration
        config_file = output_dir / "robot_config.py"
        
        config_content = f'''"""
Robot Framework Configuration with CrossBridge Observer

Auto-generated during migration.
To disable, remove the Listener line from test files.
"""

# CrossBridge Configuration
CROSSBRIDGE_ENABLED = True
CROSSBRIDGE_DB_HOST = "{self.config.db_host}"
CROSSBRIDGE_DB_PORT = {self.config.db_port}
CROSSBRIDGE_DB_NAME = "{self.config.db_name}"
CROSSBRIDGE_APPLICATION_VERSION = "{self.config.application_version}"
CROSSBRIDGE_PRODUCT_NAME = "{self.config.product_name or 'RobotApp'}"
CROSSBRIDGE_ENVIRONMENT = "{self.config.environment}"
'''
        
        config_file.write_text(config_content)
        
        # Update all .robot files to include listener
        robot_files = list(output_dir.glob("**/*.robot"))
        updated_files = []
        
        for robot_file in robot_files:
            content = robot_file.read_text()
            
            # Check if listener already exists
            if "crossbridge.RobotListener" in content:
                continue
            
            # Add listener to Settings section
            lines = content.split("\n")
            settings_idx = -1
            
            for i, line in enumerate(lines):
                if line.strip().startswith("*** Settings ***"):
                    settings_idx = i
                    break
            
            if settings_idx >= 0:
                # Insert listener after Settings header
                lines.insert(settings_idx + 1, "Listener    crossbridge.RobotListener")
                robot_file.write_text("\n".join(lines))
                updated_files.append(robot_file)
        
        return {
            "type": "robot_listener",
            "config_file": str(config_file),
            "updated_files": [str(f) for f in updated_files],
            "instructions": "Listener auto-added to all Robot files. To disable: remove 'Listener' line."
        }
    
    def _integrate_pytest_plugin(self, output_dir: Path, hook_info: Dict) -> Dict:
        """Integrate pytest plugin"""
        
        # Create or update conftest.py
        conftest_file = output_dir / "conftest.py"
        
        conftest_content = f'''"""
pytest configuration with CrossBridge Observer

Auto-generated during migration.
To disable, set crossbridge_enabled = False or remove this section.
"""

import pytest

# CrossBridge Configuration
def pytest_configure(config):
    """Configure CrossBridge observer for pytest"""
    config.option.crossbridge_enabled = True
    config.option.crossbridge_db_host = "{self.config.db_host}"
    config.option.crossbridge_db_port = {self.config.db_port}
    config.option.crossbridge_db_name = "{self.config.db_name}"
    config.option.crossbridge_application_version = "{self.config.application_version}"
    config.option.crossbridge_product_name = "{self.config.product_name or 'PytestApp'}"
    config.option.crossbridge_environment = "{self.config.environment}"


# Load CrossBridge plugin
pytest_plugins = ["crossbridge.pytest_plugin"]
'''
        
        if conftest_file.exists():
            # Append to existing conftest
            existing = conftest_file.read_text()
            if "crossbridge" not in existing.lower():
                conftest_file.write_text(existing + "\n\n" + conftest_content)
        else:
            conftest_file.write_text(conftest_content)
        
        # Create pytest.ini
        pytest_ini = output_dir / "pytest.ini"
        
        ini_content = f'''[pytest]
# CrossBridge Observer Configuration (auto-generated)
# To disable, comment out or remove these lines

plugins = crossbridge

# Optional: Command line options
addopts = 
    --crossbridge-enabled=true
    --crossbridge-db-host={self.config.db_host}
    --crossbridge-application-version={self.config.application_version}
'''
        
        if not pytest_ini.exists():
            pytest_ini.write_text(ini_content)
        
        return {
            "type": "pytest_plugin",
            "config_file": str(conftest_file),
            "ini_file": str(pytest_ini),
            "instructions": "Plugin auto-configured in conftest.py. To disable: set crossbridge_enabled = False"
        }
    
    def _integrate_playwright_reporter(self, output_dir: Path, hook_info: Dict) -> Dict:
        """Integrate Playwright reporter"""
        
        config_file = output_dir / "playwright.config.ts"
        
        # TypeScript configuration
        config_content = f'''import {{ defineConfig }} from '@playwright/test';

/**
 * Playwright Configuration with CrossBridge Observer
 * Auto-generated during migration.
 * To disable, remove 'crossbridge' from reporters array.
 */
export default defineConfig({{
  testDir: './tests',
  
  // CrossBridge Reporter (auto-configured)
  reporter: [
    ['list'],
    ['html'],
    ['crossbridge', {{
      enabled: true,
      dbHost: '{self.config.db_host}',
      dbPort: {self.config.db_port},
      dbName: '{self.config.db_name}',
      applicationVersion: '{self.config.application_version}',
      productName: '{self.config.product_name or 'PlaywrightApp'}',
      environment: '{self.config.environment}'
    }}]
  ],
  
  // Other Playwright config...
  use: {{
    trace: 'on-first-retry',
  }},
}});
'''
        
        if config_file.exists():
            # TODO: Parse and merge with existing config
            logger.warning(f"playwright.config.ts exists, manual merge required")
        else:
            config_file.write_text(config_content)
        
        return {
            "type": "playwright_reporter",
            "config_file": str(config_file),
            "instructions": "Reporter auto-configured in playwright.config.ts. To disable: remove from reporters."
        }
    
    def _integrate_cypress_plugin(self, output_dir: Path, hook_info: Dict) -> Dict:
        """Integrate Cypress plugin"""
        
        config_file = output_dir / "cypress.config.js"
        
        config_content = f'''const {{ defineConfig }} = require('cypress');
const crossbridge = require('crossbridge-cypress');

/**
 * Cypress Configuration with CrossBridge Observer
 * Auto-generated during migration.
 * To disable, remove crossbridge.register() call.
 */
module.exports = defineConfig({{
  e2e: {{
    setupNodeEvents(on, config) {{
      // CrossBridge Plugin (auto-configured)
      crossbridge.register(on, {{
        enabled: true,
        dbHost: '{self.config.db_host}',
        dbPort: {self.config.db_port},
        dbName: '{self.config.db_name}',
        applicationVersion: '{self.config.application_version}',
        productName: '{self.config.product_name or 'CypressApp'}',
        environment: '{self.config.environment}'
      }});
      
      return config;
    }},
  }},
}});
'''
        
        if not config_file.exists():
            config_file.write_text(config_content)
        
        # Create support file for automatic tracking
        support_dir = output_dir / "cypress" / "support"
        support_dir.mkdir(parents=True, exist_ok=True)
        
        support_file = support_dir / "e2e.js"
        support_content = '''/**
 * CrossBridge Automatic Test Tracking
 * Auto-generated during migration.
 */

beforeEach(function() {
  const test = {
    title: Cypress.currentTest.title,
    titlePath: Cypress.currentTest.titlePath,
    invocationDetails: {
      relativeFile: Cypress.spec.relative
    },
    file: Cypress.spec.absolute
  };
  
  cy.task('crossbridge:testStart', test, { log: false });
});

afterEach(function() {
  const test = {
    title: Cypress.currentTest.title,
    titlePath: Cypress.currentTest.titlePath,
    invocationDetails: {
      relativeFile: Cypress.spec.relative
    },
    file: Cypress.spec.absolute,
    err: this.test?.err
  };
  
  const state = this.test?.state || 'passed';
  cy.task('crossbridge:testEnd', { test, state }, { log: false });
});
'''
        
        if not support_file.exists():
            support_file.write_text(support_content)
        
        return {
            "type": "cypress_plugin",
            "config_file": str(config_file),
            "support_file": str(support_file),
            "instructions": "Plugin auto-configured. To disable: remove crossbridge.register() from config."
        }
    
    def generate_disable_instructions(self, target_framework: str) -> str:
        """Generate instructions for disabling hooks"""
        
        framework_key = target_framework.lower().replace("_", "-")
        
        if framework_key not in self.FRAMEWORK_HOOKS:
            return "No hook configuration available"
        
        hook_type = self.FRAMEWORK_HOOKS[framework_key]["type"]
        
        instructions = {
            "robot_listener": """
To disable CrossBridge observer in Robot Framework:
1. Remove 'Listener    crossbridge.RobotListener' from *** Settings ***
2. Or delete robot_config.py
""",
            "pytest_plugin": """
To disable CrossBridge observer in pytest:
1. Set crossbridge_enabled = False in conftest.py
2. Or remove 'pytest_plugins = ["crossbridge.pytest_plugin"]' line
3. Or remove --crossbridge-enabled flag from pytest.ini
""",
            "playwright_reporter": """
To disable CrossBridge observer in Playwright:
1. Remove ['crossbridge', {{ ... }}] from reporters array in playwright.config.ts
2. Or set enabled: false in reporter config
""",
            "cypress_plugin": """
To disable CrossBridge observer in Cypress:
1. Remove crossbridge.register() call from cypress.config.js
2. Or set enabled: false in plugin config
3. Or delete cypress/support/e2e.js
"""
        }
        
        return instructions.get(hook_type, "No instructions available")


def integrate_hooks_after_migration(
    target_framework: str,
    output_dir: Path,
    migrated_files: List[Path],
    enable_hooks: bool = True,
    config: Optional[MigrationHookConfig] = None
) -> Dict:
    """
    Convenience function to integrate hooks after migration.
    
    Args:
        target_framework: Target framework name
        output_dir: Root directory of migrated project
        migrated_files: List of migrated test files
        enable_hooks: Whether to enable hooks (default: True)
        config: Optional custom configuration
        
    Returns:
        Integration results
    """
    if config is None:
        config = MigrationHookConfig(enable_hooks=enable_hooks)
    
    integrator = MigrationHookIntegrator(config)
    result = integrator.integrate_hooks(target_framework, output_dir, migrated_files)
    
    if result.get("enabled"):
        logger.info(f"✅ Sidecar hooks integrated for {target_framework}")
        logger.info(f"   Config: {result.get('config_file')}")
        logger.info(f"   Type: {result.get('type')}")
    else:
        logger.info(f"❌ Hooks not integrated: {result.get('reason')}")
    
    return result
