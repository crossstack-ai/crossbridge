"""
Auto-Migration Script for API Change Intelligence

This script automatically enables and configures API Change Intelligence
feature when running CrossBridge migrations.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class APIMigrationHelper:
    """Helper to auto-enable API Change Intelligence during migrations."""
    
    DEFAULT_CONFIG = {
        'enabled': True,
        'spec_source': {
            'type': 'file',
            'current': 'specs/openapi.yaml',
            'previous': 'specs/openapi_prev.yaml'
        },
        'intelligence': {
            'mode': 'hybrid',
            'rules': {'enabled': True},
            'ai': {'enabled': False}
        },
        'impact_analysis': {
            'enabled': True,
            'test_directories': ['tests/', 'test/'],
            'framework': 'pytest',
            'min_confidence': 0.5
        },
        'ci_integration': {
            'enabled': True,
            'min_confidence': 0.5,
            'max_tests': 0
        },
        'alerts': {
            'enabled': False,  # Disabled by default, user must configure
            'email': {'enabled': False},
            'slack': {'enabled': False}
        },
        'documentation': {
            'enabled': True,
            'output_dir': 'docs/api-changes',
            'formats': {
                'markdown': {
                    'enabled': True,
                    'mode': 'incremental'
                }
            }
        }
    }
    
    @staticmethod
    def load_config(config_path: str = 'crossbridge.yml') -> Dict[str, Any]:
        """Load existing configuration file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            logger.warning(f"Configuration file not found: {config_path}")
            return {}
        
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return {}
    
    @staticmethod
    def save_config(config: Dict[str, Any], config_path: str = 'crossbridge.yml', backup: bool = True) -> bool:
        """Save configuration file with optional backup."""
        config_file = Path(config_path)
        
        try:
            # Create backup if requested and file exists
            if backup and config_file.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = config_file.with_suffix(f'.{timestamp}.bak')
                config_file.rename(backup_path)
                logger.info(f"Created backup: {backup_path}")
            
            # Write new configuration
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)
            
            logger.info(f"Saved configuration to {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    @classmethod
    def enable_api_change_intelligence(
        cls,
        config_path: str = 'crossbridge.yml',
        force: bool = False,
        **overrides
    ) -> bool:
        """
        Enable API Change Intelligence in configuration.
        
        Args:
            config_path: Path to configuration file
            force: If True, overwrite existing configuration
            **overrides: Additional configuration overrides
        
        Returns:
            True if enabled successfully
        """
        logger.info("=" * 60)
        logger.info("API Change Intelligence Auto-Migration")
        logger.info("=" * 60)
        
        # Load existing config
        config = cls.load_config(config_path)
        
        # Initialize crossbridge section if missing
        if 'crossbridge' not in config:
            config['crossbridge'] = {}
            logger.info("Created 'crossbridge' configuration section")
        
        # Check if api_change already exists
        if 'api_change' in config['crossbridge'] and not force:
            if config['crossbridge']['api_change'].get('enabled', False):
                logger.info("✅ API Change Intelligence already enabled")
                return True
            else:
                logger.info("⚠️  API Change Intelligence exists but disabled")
        
        # Merge default config with overrides
        api_change_config = cls.DEFAULT_CONFIG.copy()
        api_change_config.update(overrides)
        
        # Add to configuration
        config['crossbridge']['api_change'] = api_change_config
        
        # Detect test framework if not specified
        if not overrides.get('framework'):
            framework = cls.detect_test_framework()
            if framework:
                config['crossbridge']['api_change']['impact_analysis']['framework'] = framework
                logger.info(f"Detected test framework: {framework}")
        
        # Save configuration
        if cls.save_config(config, config_path, backup=True):
            logger.info("✅ API Change Intelligence enabled successfully!")
            logger.info("")
            logger.info("Next steps:")
            logger.info("1. Configure spec sources in crossbridge.yml")
            logger.info("2. Run: crossbridge api-diff check-deps")
            logger.info("3. Run: crossbridge api-diff run")
            logger.info("")
            logger.info("For email/Slack alerts, configure:")
            logger.info("  - alerts.email settings")
            logger.info("  - alerts.slack settings")
            logger.info("")
            return True
        else:
            logger.error("❌ Failed to enable API Change Intelligence")
            return False
    
    @staticmethod
    def detect_test_framework() -> Optional[str]:
        """Auto-detect test framework from project structure."""
        cwd = Path.cwd()
        
        # Check for pytest
        if (cwd / 'pytest.ini').exists() or (cwd / 'pyproject.toml').exists():
            pyproject = cwd / 'pyproject.toml'
            if pyproject.exists():
                content = pyproject.read_text()
                if 'pytest' in content:
                    return 'pytest'
        
        # Check for Robot Framework
        if list(cwd.rglob('*.robot')):
            return 'robot'
        
        # Check for Selenium
        if list(cwd.rglob('**/test_*.py')):
            return 'selenium_pytest'
        
        # Check for Playwright
        if (cwd / 'playwright.config.js').exists() or (cwd / 'playwright.config.ts').exists():
            return 'playwright'
        
        # Check for Cypress
        if (cwd / 'cypress.json').exists() or (cwd / 'cypress.config.js').exists():
            return 'cypress'
        
        # Check for Java
        if (cwd / 'pom.xml').exists():
            pom_content = (cwd / 'pom.xml').read_text()
            if 'junit' in pom_content.lower():
                return 'junit'
            if 'testng' in pom_content.lower():
                return 'testng'
        
        logger.warning("Could not auto-detect test framework")
        return None
    
    @staticmethod
    def verify_dependencies() -> Dict[str, bool]:
        """Verify required dependencies are installed."""
        import subprocess
        
        results = {
            'oasdiff': False,
            'database': False,
            'python_packages': False
        }
        
        # Check oasdiff
        try:
            result = subprocess.run(['oasdiff', '--version'], capture_output=True, timeout=5)
            results['oasdiff'] = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Check Python packages
        try:
            import aiohttp
            import requests
            import yaml
            results['python_packages'] = True
        except ImportError:
            pass
        
        # Check database (optional)
        try:
            import psycopg2
            results['database'] = True
        except ImportError:
            pass
        
        return results
    
    @classmethod
    def create_sample_specs(cls, output_dir: str = 'specs') -> bool:
        """Create sample OpenAPI spec files for testing."""
        specs_dir = Path(output_dir)
        specs_dir.mkdir(parents=True, exist_ok=True)
        
        sample_spec = {
            'openapi': '3.0.0',
            'info': {
                'title': 'Sample API',
                'version': '1.0.0'
            },
            'paths': {
                '/api/users': {
                    'get': {
                        'summary': 'Get all users',
                        'responses': {
                            '200': {
                                'description': 'Success'
                            }
                        }
                    }
                }
            }
        }
        
        try:
            with open(specs_dir / 'openapi.yaml', 'w') as f:
                yaml.dump(sample_spec, f, default_flow_style=False)
            
            with open(specs_dir / 'openapi_prev.yaml', 'w') as f:
                yaml.dump(sample_spec, f, default_flow_style=False)
            
            logger.info(f"Created sample spec files in {specs_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to create sample specs: {e}")
            return False


def main():
    """Main migration function - called during CrossBridge setup."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    import argparse
    parser = argparse.ArgumentParser(description='Auto-enable API Change Intelligence')
    parser.add_argument('--config', default='crossbridge.yml', help='Configuration file path')
    parser.add_argument('--force', action='store_true', help='Force overwrite existing config')
    parser.add_argument('--create-samples', action='store_true', help='Create sample OpenAPI specs')
    parser.add_argument('--verify-deps', action='store_true', help='Verify dependencies')
    
    args = parser.parse_args()
    
    # Verify dependencies
    if args.verify_deps:
        logger.info("Verifying dependencies...")
        deps = APIMigrationHelper.verify_dependencies()
        for dep, status in deps.items():
            status_icon = "✅" if status else "❌"
            logger.info(f"  {status_icon} {dep}: {'installed' if status else 'missing'}")
        
        if not deps['oasdiff']:
            logger.warning("")
            logger.warning("oasdiff is not installed. Install with:")
            logger.warning("  go install github.com/tufin/oasdiff@latest")
            logger.warning("Or download from: https://github.com/tufin/oasdiff/releases")
        
        return
    
    # Create sample specs
    if args.create_samples:
        APIMigrationHelper.create_sample_specs()
        return
    
    # Enable API Change Intelligence
    success = APIMigrationHelper.enable_api_change_intelligence(
        config_path=args.config,
        force=args.force
    )
    
    if success:
        logger.info("=" * 60)
        logger.info("✨ Migration complete!")
        logger.info("=" * 60)
    else:
        logger.error("❌ Migration failed")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
