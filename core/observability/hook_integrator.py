"""
CrossBridge Hook Auto-Integration

Automatically configures CrossBridge hooks during migration to enable
day-1 continuous intelligence and monitoring.

This module adds hook configuration to migrated test projects so that
CrossBridge can immediately start collecting execution metadata for:
- Coverage intelligence
- Flakiness detection  
- AI-powered insights
- Post-migration monitoring
"""

import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class HookIntegrator:
    """
    Integrates CrossBridge hooks into migrated test projects.
    
    Key principles:
    - Enabled by default during migration
    - Can be disabled via flag
    - Non-intrusive (doesn't modify test logic)
    - User-friendly messaging
    """
    
    # Hook configuration templates for different frameworks
    PYTEST_CONFTEST = """# CrossBridge Observability Hook
# This enables continuous intelligence and monitoring post-migration.
# 
# What it does:
#   - Tracks test execution (pass/fail/duration)
#   - Monitors API calls and UI interactions
#   - Detects flaky tests automatically
#   - Powers AI-driven insights
#
# Impact: Minimal (<5ms per test)
# Privacy: Only execution metadata, no sensitive data
# Control: Set CROSSBRIDGE_HOOKS_ENABLED=false to disable
#
# Learn more: docs/POST_MIGRATION_INTELLIGENCE.md

pytest_plugins = ['crossbridge.hooks.pytest_hooks']
"""
    
    ROBOT_LISTENER_COMMENT = """# CrossBridge Continuous Intelligence
# 
# To enable post-migration monitoring, run tests with:
#   robot --listener crossbridge.hooks.robot_hooks.CrossBridgeListener tests/
#
# Or add to your CI/CD pipeline configuration.
# 
# Benefits:
#   ✓ Automatic coverage tracking
#   ✓ Flaky test detection
#   ✓ AI-powered test insights
#   ✓ Historical trend analysis
#
# Disable: Set CROSSBRIDGE_HOOKS_ENABLED=false
# Learn more: docs/POST_MIGRATION_INTELLIGENCE.md
"""
    
    PLAYWRIGHT_CONFIG_SNIPPET = """// CrossBridge Observability Hook (TypeScript/JavaScript)
// 
// Uncomment to enable continuous intelligence:
// 
// import { crossbridgeReporter } from 'crossbridge/hooks/playwright_hooks';
// 
// export default defineConfig({
//   reporter: [
//     ['html'],
//     [crossbridgeReporter]  // CrossBridge monitoring
//   ]
// });
// 
// Learn more: docs/POST_MIGRATION_INTELLIGENCE.md
"""
    
    CROSSBRIDGE_CONFIG = """# CrossBridge Configuration
# Auto-generated during migration

crossbridge:
  # Observer mode: Continuous intelligence post-migration
  mode: observer
  
  # Application version tracking (for coverage across versions)
  application:
    product_name: ${PRODUCT_NAME:-MyApplication}
    version: ${APP_VERSION:-1.0.0}
    environment: ${ENVIRONMENT:-dev}
  
  # Hooks enabled by default for immediate monitoring
  hooks:
    enabled: true
  
  # Persistence configuration
  persistence:
    postgres:
      enabled: true
      host: ${CROSSBRIDGE_DB_HOST:-10.55.12.99}
      port: ${CROSSBRIDGE_DB_PORT:-5432}
      database: ${CROSSBRIDGE_DB_NAME:-udp-native-webservices-automation}
      user: ${CROSSBRIDGE_DB_USER:-postgres}
      password: ${CROSSBRIDGE_DB_PASSWORD:-admin}
  
  # Continuous intelligence features
  observer:
    auto_detect_new_tests: true
    update_coverage_graph: true
    detect_drift: true
    flaky_threshold: 0.15
  
  # AI-powered insights
  intelligence:
    ai_enabled: true
    detect_coverage_gaps: true
    detect_redundant_tests: true
"""
    
    README_CONTENT = """# CrossBridge Continuous Intelligence

## 🎯 What's This?

During migration, CrossBridge automatically configured hooks to enable continuous 
monitoring and intelligence. This is **completely optional** and can be disabled anytime.

## ✅ Benefits

- **Coverage Tracking**: Automatic test-to-feature mapping
- **Flaky Detection**: Identify unstable tests early
- **AI Insights**: Get smart recommendations
- **Trend Analysis**: Historical execution data
- **Risk Analysis**: Focus on high-risk areas

## 🔧 How It Works

CrossBridge hooks emit lightweight execution metadata (test name, status, duration) 
without affecting your tests. Think of it as lightweight telemetry.

**Performance Impact**: <5ms per test
**Data Collected**: Only execution metadata (no sensitive data)

## 🎛️ Control

### Enable (Default)
Hooks are enabled by default. Just run tests normally:

```bash
pytest tests/
robot tests/
npx playwright test
```

### Disable

Set environment variable:
```bash
export CROSSBRIDGE_HOOKS_ENABLED=false
```

Or edit `crossbridge.yaml`:
```yaml
crossbridge:
  hooks:
    enabled: false
```

### Remove Completely

Delete these files:
- `conftest.py` (pytest hook)
- `crossbridge.yaml` (configuration)
- This README

Your tests will work exactly as before.

## 📊 Viewing Insights

Access Grafana dashboards:
- Test execution trends
- Flaky test detection
- Coverage evolution
- AI recommendations

## 📚 Learn More

- **Architecture**: `docs/POST_MIGRATION_INTELLIGENCE.md`
- **Hook SDK**: `core/observability/hook_sdk.py`
- **Examples**: `examples/hooks/`

## 🆘 Support

If you have questions or want to disable hooks:
1. Set `CROSSBRIDGE_HOOKS_ENABLED=false`
2. See documentation above
3. Contact CrossBridge team

---

**Note**: This is a value-add feature from CrossBridge. Your tests are 100% independent 
and will work with or without hooks enabled.
"""
    
    @staticmethod
    def should_integrate_hooks(enable_hooks: bool = True, target_framework: str = None) -> bool:
        """
        Determine if hooks should be integrated.
        
        Args:
            enable_hooks: Flag from migration request (default: True)
            target_framework: Target framework name
            
        Returns:
            True if hooks should be integrated
        """
        # Respect explicit disable flag
        if not enable_hooks:
            return False
        
        # Only integrate for supported frameworks
        supported = ['pytest', 'robot', 'playwright']
        if target_framework and target_framework.lower() not in supported:
            logger.debug(f"Hook integration not supported for framework: {target_framework}")
            return False
        
        return True
    
    @staticmethod
    def integrate_pytest_hooks(output_dir: Path) -> Dict[str, str]:
        """
        Add pytest hooks to migrated project.
        
        Args:
            output_dir: Root directory of migrated project
            
        Returns:
            Dict with created files and their purposes
        """
        created_files = {}
        
        try:
            # 1. Create/update conftest.py
            conftest_path = output_dir / "conftest.py"
            
            if conftest_path.exists():
                # Append to existing conftest.py
                existing_content = conftest_path.read_text()
                if 'crossbridge.hooks.pytest_hooks' not in existing_content:
                    with open(conftest_path, 'a', encoding='utf-8') as f:
                        f.write(f"\n\n{HookIntegrator.PYTEST_CONFTEST}")
                    created_files[str(conftest_path)] = "Updated with CrossBridge hooks"
            else:
                # Create new conftest.py
                conftest_path.write_text(HookIntegrator.PYTEST_CONFTEST, encoding='utf-8')
                created_files[str(conftest_path)] = "Created with CrossBridge hooks"
            
            logger.info(f"✓ Pytest hooks configured: {conftest_path}")
            
        except Exception as e:
            logger.warning(f"Failed to integrate pytest hooks: {e}")
        
        return created_files
    
    @staticmethod
    def integrate_robot_hooks(output_dir: Path) -> Dict[str, str]:
        """
        Add Robot Framework hook instructions to migrated project.
        
        Args:
            output_dir: Root directory of migrated project
            
        Returns:
            Dict with created files and their purposes
        """
        created_files = {}
        
        try:
            # Create README with listener instructions
            readme_path = output_dir / "CROSSBRIDGE_ROBOT_SETUP.md"
            readme_path.write_text(HookIntegrator.ROBOT_LISTENER_COMMENT, encoding='utf-8')
            created_files[str(readme_path)] = "Robot Framework hook instructions"
            
            logger.info(f"✓ Robot Framework hook instructions: {readme_path}")
            
        except Exception as e:
            logger.warning(f"Failed to integrate Robot hooks: {e}")
        
        return created_files
    
    @staticmethod
    def integrate_playwright_hooks(output_dir: Path) -> Dict[str, str]:
        """
        Add Playwright hook instructions to migrated project.
        
        Args:
            output_dir: Root directory of migrated project
            
        Returns:
            Dict with created files and their purposes
        """
        created_files = {}
        
        try:
            # Create README with reporter instructions
            readme_path = output_dir / "CROSSBRIDGE_PLAYWRIGHT_SETUP.md"
            readme_path.write_text(HookIntegrator.PLAYWRIGHT_CONFIG_SNIPPET, encoding='utf-8')
            created_files[str(readme_path)] = "Playwright hook instructions"
            
            logger.info(f"✓ Playwright hook instructions: {readme_path}")
            
        except Exception as e:
            logger.warning(f"Failed to integrate Playwright hooks: {e}")
        
        return created_files
    
    @staticmethod
    def create_config_file(output_dir: Path) -> Dict[str, str]:
        """
        Create CrossBridge configuration file.
        
        Args:
            output_dir: Root directory of migrated project
            
        Returns:
            Dict with created files
        """
        created_files = {}
        
        try:
            config_path = output_dir / "crossbridge.yaml"
            
            # Only create if doesn't exist
            if not config_path.exists():
                config_path.write_text(HookIntegrator.CROSSBRIDGE_CONFIG, encoding='utf-8')
                created_files[str(config_path)] = "CrossBridge configuration"
                logger.info(f"✓ Configuration created: {config_path}")
            
        except Exception as e:
            logger.warning(f"Failed to create config file: {e}")
        
        return created_files
    
    @staticmethod
    def create_readme(output_dir: Path) -> Dict[str, str]:
        """
        Create informational README about hooks.
        
        Args:
            output_dir: Root directory of migrated project
            
        Returns:
            Dict with created files
        """
        created_files = {}
        
        try:
            readme_path = output_dir / "CROSSBRIDGE_INTELLIGENCE.md"
            readme_path.write_text(HookIntegrator.README_CONTENT, encoding='utf-8')
            created_files[str(readme_path)] = "Intelligence features documentation"
            logger.info(f"✓ README created: {readme_path}")
            
        except Exception as e:
            logger.warning(f"Failed to create README: {e}")
        
        return created_files
    
    @staticmethod
    def integrate_hooks(
        output_dir: Path,
        target_framework: str,
        enable_hooks: bool = True
    ) -> Dict[str, List[str]]:
        """
        Integrate CrossBridge hooks into migrated project.
        
        Args:
            output_dir: Root directory of migrated tests
            target_framework: Target framework (pytest, robot, playwright)
            enable_hooks: Whether to enable hooks (default: True)
            
        Returns:
            Dict with summary of integrated files by category
        """
        if not HookIntegrator.should_integrate_hooks(enable_hooks, target_framework):
            logger.info("Hook integration skipped (disabled or unsupported framework)")
            return {'status': 'skipped', 'files': []}
        
        logger.info(f"🔗 Integrating CrossBridge hooks for {target_framework}...")
        
        all_created_files = {}
        
        # Framework-specific integration
        framework_lower = target_framework.lower()
        
        if 'pytest' in framework_lower:
            all_created_files.update(HookIntegrator.integrate_pytest_hooks(output_dir))
        elif 'robot' in framework_lower:
            all_created_files.update(HookIntegrator.integrate_robot_hooks(output_dir))
        elif 'playwright' in framework_lower:
            all_created_files.update(HookIntegrator.integrate_playwright_hooks(output_dir))
        
        # Common files for all frameworks
        all_created_files.update(HookIntegrator.create_config_file(output_dir))
        all_created_files.update(HookIntegrator.create_readme(output_dir))
        
        return {
            'status': 'integrated',
            'files': all_created_files
        }
    
    @staticmethod
    def get_integration_message(target_framework: str, files_created: Dict[str, str]) -> str:
        """
        Generate user-friendly message about hook integration.
        
        Args:
            target_framework: Target framework name
            files_created: Dict of created files and their purposes
            
        Returns:
            Formatted message for display
        """
        if not files_created:
            return ""
        
        message = """
╔═══════════════════════════════════════════════════════════════════════════╗
║  🎯 CrossBridge Continuous Intelligence Enabled                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

CrossBridge has configured lightweight hooks to provide ongoing value after 
migration. This enables:

  ✓ Automatic coverage tracking       ✓ Historical trend analysis
  ✓ Flaky test detection             ✓ AI-powered insights
  ✓ Real-time monitoring             ✓ Risk-based recommendations

📋 What Was Added:
"""
        
        for file_path, purpose in files_created.items():
            file_name = Path(file_path).name
            message += f"\n  • {file_name:<35} - {purpose}"
        
        message += """

🎛️  Full Control - You Decide:
  
  ✓ Hooks are OPTIONAL and can be disabled anytime
  ✓ Zero impact on test execution (<5ms overhead)
  ✓ No sensitive data collected (only execution metadata)
  ✓ Tests work perfectly with or without hooks
  
  To disable: Set CROSSBRIDGE_HOOKS_ENABLED=false
  Learn more: See CROSSBRIDGE_INTELLIGENCE.md

💡 No Action Needed:
  
  Just run your tests normally. CrossBridge will quietly observe and provide
  insights through Grafana dashboards and CLI tools.

"""
        
        return message
