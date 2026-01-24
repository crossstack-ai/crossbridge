"""
Cypress adapter implementation for CrossBridge.

Provides comprehensive support for Cypress E2E and component testing with both
JavaScript and TypeScript. Handles test discovery, execution, and metadata extraction.
"""

import subprocess
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from adapters.common.base import BaseTestAdapter, BaseTestExtractor, TestResult
from adapters.common.models import TestMetadata
from adapters.common.normalizer import UniversalTestNormalizer
from core.intelligence.models import UnifiedTestMemory


class CypressTestType(Enum):
    """Types of Cypress tests."""
    E2E = "e2e"
    COMPONENT = "component"


@dataclass
class CypressConfig:
    """Cypress project configuration."""
    project_root: Path
    config_file: Path  # cypress.config.js/ts or cypress.json
    specs_dir: Path  # e2e/ or integration/ directory
    test_type: CypressTestType
    support_file: Optional[Path] = None
    fixtures_dir: Optional[Path] = None
    has_typescript: bool = False
    cypress_version: Optional[str] = None


class CypressProjectDetector:
    """
    Detects and analyzes Cypress project configuration.
    
    Supports both legacy (cypress.json) and modern (cypress.config.js/ts) configurations.
    """
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
    
    def detect(self) -> Optional[CypressConfig]:
        """
        Detect Cypress project configuration.
        
        Returns:
            CypressConfig if valid Cypress project, None otherwise
        """
        # Check for Cypress config files
        config_file = self._find_config_file()
        if not config_file:
            return None
        
        # Detect TypeScript usage
        has_typescript = self._detect_typescript()
        
        # Find specs directory
        specs_dir = self._find_specs_directory()
        if not specs_dir:
            return None
        
        # Detect test type
        test_type = self._detect_test_type(specs_dir)
        
        # Find support and fixtures
        support_file = self._find_support_file()
        fixtures_dir = self._find_fixtures_directory()
        
        # Get Cypress version
        cypress_version = self._get_cypress_version()
        
        return CypressConfig(
            project_root=self.project_root,
            config_file=config_file,
            specs_dir=specs_dir,
            test_type=test_type,
            support_file=support_file,
            fixtures_dir=fixtures_dir,
            has_typescript=has_typescript,
            cypress_version=cypress_version
        )
    
    def _find_config_file(self) -> Optional[Path]:
        """Find Cypress configuration file."""
        # Modern config (Cypress 10+)
        for filename in ["cypress.config.ts", "cypress.config.js"]:
            config_path = self.project_root / filename
            if config_path.exists():
                return config_path
        
        # Legacy config (Cypress < 10)
        legacy_config = self.project_root / "cypress.json"
        if legacy_config.exists():
            return legacy_config
        
        # Check in package.json for cypress presence
        package_json = self.project_root / "package.json"
        if package_json.exists():
            try:
                content = json.loads(package_json.read_text(encoding='utf-8'))
                deps = {**content.get('dependencies', {}), **content.get('devDependencies', {})}
                if 'cypress' in deps:
                    # Cypress is installed but no config file - might be default config
                    return package_json
            except Exception:
                pass
        
        return None
    
    def _detect_typescript(self) -> bool:
        """Detect if project uses TypeScript."""
        # Check for tsconfig.json
        if (self.project_root / "tsconfig.json").exists():
            return True
        
        # Check for .ts files in cypress directory
        cypress_dir = self.project_root / "cypress"
        if cypress_dir.exists():
            ts_files = list(cypress_dir.rglob("*.ts"))
            if ts_files:
                return True
        
        return False
    
    def _find_specs_directory(self) -> Optional[Path]:
        """Find Cypress specs directory."""
        cypress_dir = self.project_root / "cypress"
        
        if not cypress_dir.exists():
            return None
        
        # Modern structure (Cypress 10+)
        for dirname in ["e2e", "integration", "component"]:
            specs_dir = cypress_dir / dirname
            if specs_dir.exists():
                # Check if it has test files
                test_files = list(specs_dir.rglob("*.cy.js")) + \
                           list(specs_dir.rglob("*.cy.ts")) + \
                           list(specs_dir.rglob("*.spec.js")) + \
                           list(specs_dir.rglob("*.spec.ts"))
                if test_files:
                    return specs_dir
        
        # Legacy structure - look for integration directory
        legacy_integration = cypress_dir / "integration"
        if legacy_integration.exists():
            return legacy_integration
        
        # Fallback - check cypress root for specs
        test_files = list(cypress_dir.rglob("*.cy.js")) + \
                    list(cypress_dir.rglob("*.cy.ts")) + \
                    list(cypress_dir.rglob("*.spec.js")) + \
                    list(cypress_dir.rglob("*.spec.ts"))
        if test_files:
            return cypress_dir
        
        return None
    
    def _detect_test_type(self, specs_dir: Path) -> CypressTestType:
        """Detect if tests are E2E or component tests."""
        if "component" in str(specs_dir).lower():
            return CypressTestType.COMPONENT
        return CypressTestType.E2E
    
    def _find_support_file(self) -> Optional[Path]:
        """Find Cypress support file."""
        cypress_dir = self.project_root / "cypress"
        support_dir = cypress_dir / "support"
        
        if support_dir.exists():
            for filename in ["e2e.ts", "e2e.js", "index.ts", "index.js", "commands.ts", "commands.js"]:
                support_file = support_dir / filename
                if support_file.exists():
                    return support_file
        
        return None
    
    def _find_fixtures_directory(self) -> Optional[Path]:
        """Find fixtures directory."""
        cypress_dir = self.project_root / "cypress"
        fixtures_dir = cypress_dir / "fixtures"
        
        if fixtures_dir.exists():
            return fixtures_dir
        
        return None
    
    def _get_cypress_version(self) -> Optional[str]:
        """Get Cypress version from package.json."""
        package_json = self.project_root / "package.json"
        
        if not package_json.exists():
            return None
        
        try:
            content = json.loads(package_json.read_text(encoding='utf-8'))
            deps = {**content.get('dependencies', {}), **content.get('devDependencies', {})}
            
            if 'cypress' in deps:
                version = deps['cypress']
                # Remove ^ or ~ prefix
                return version.lstrip('^~')
        except Exception:
            pass
        
        return None


class CypressTestParser:
    """
    Parses Cypress test files (JavaScript and TypeScript).
    
    Extracts test names, descriptions, and structure from spec files.
    """
    
    def parse_test_file(self, test_file: Path) -> List[Dict]:
        """
        Parse a Cypress test file and extract test information.
        
        Args:
            test_file: Path to .cy.js/.cy.ts or .spec.js/.spec.ts file
            
        Returns:
            List of test dictionaries with name, description, etc.
        """
        try:
            content = test_file.read_text(encoding='utf-8')
            tests = []
            
            # Remove comments to avoid false matches
            content = self._remove_comments(content)
            
            # Find describe blocks
            describe_pattern = r'describe\s*\(\s*[\'"`]([^\'"`]+)[\'"`]'
            describes = list(re.finditer(describe_pattern, content))
            
            # Find it/test blocks with their describe context
            # Match it( or test( followed by string and arrow/function
            test_pattern = r'(?:it|test)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]\s*,\s*(?:\(|\(\)|async\s*\(|function)'
            tests_matches = list(re.finditer(test_pattern, content))
            
            for test_match in tests_matches:
                test_name = test_match.group(1)
                test_pos = test_match.start()
                
                # Find the closest describe block before this test
                describe_name = ""
                for desc in describes:
                    if desc.start() < test_pos:
                        describe_name = desc.group(1)
                    else:
                        break
                
                # Create full test name
                full_name = f"{describe_name} > {test_name}" if describe_name else test_name
                
                tests.append({
                    'name': test_name,
                    'full_name': full_name,
                    'describe': describe_name,
                    'file': str(test_file)
                })
            
            return tests
        
        except Exception as e:
            print(f"Warning: Error parsing {test_file}: {e}")
            return []
    
    def _remove_comments(self, content: str) -> str:
        """Remove JavaScript/TypeScript comments."""
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        return content
    
    def extract_custom_commands(self, support_file: Path) -> List[str]:
        """
        Extract custom Cypress commands from support file.
        
        Args:
            support_file: Path to support/commands file
            
        Returns:
            List of custom command names
        """
        try:
            content = support_file.read_text(encoding='utf-8')
            
            # Find Cypress.Commands.add() calls
            pattern = r'Cypress\.Commands\.add\s*\(\s*[\'"`]([^\'"`]+)[\'"`]'
            matches = re.findall(pattern, content)
            
            return matches
        
        except Exception as e:
            print(f"Warning: Error extracting commands from {support_file}: {e}")
            return []


class CypressAdapter(BaseTestAdapter):
    """
    Main Cypress adapter for test discovery and execution.
    
    Supports both JavaScript and TypeScript projects, modern and legacy
    Cypress configurations, E2E and component testing.
    """
    
    def __init__(self, project_root: str, config: Optional[CypressConfig] = None):
        """
        Initialize Cypress adapter.
        
        Args:
            project_root: Path to Cypress project
            config: Optional pre-detected configuration
        """
        self.project_root = Path(project_root)
        
        if config is None:
            detector = CypressProjectDetector(project_root)
            config = detector.detect()
            
            if config is None:
                raise ValueError(
                    f"Could not detect Cypress project at {project_root}. "
                    "Ensure cypress.config.js/ts or cypress.json exists."
                )
        
        self.config = config
        self.parser = CypressTestParser()
    
    def discover_tests(self) -> List[str]:
        """
        Discover all Cypress tests.
        
        Returns:
            List of test identifiers (full test names)
        """
        tests = []
        
        try:
            # Find all spec files
            spec_patterns = ["*.cy.js", "*.cy.ts", "*.spec.js", "*.spec.ts"]
            
            for pattern in spec_patterns:
                spec_files = list(self.config.specs_dir.rglob(pattern))
                
                for spec_file in spec_files:
                    file_tests = self.parser.parse_test_file(spec_file)
                    
                    for test in file_tests:
                        tests.append(test['full_name'])
        
        except Exception as e:
            print(f"Warning: Error discovering tests: {e}")
        
        return tests
    
    def run_tests(
        self,
        tests: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        spec: Optional[str] = None,
        browser: str = "electron",
        headless: bool = True,
        timeout: int = 300
    ) -> List[TestResult]:
        """
        Run Cypress tests.
        
        Args:
            tests: Specific test names to run (not directly supported by Cypress CLI)
            tags: Tags to filter tests (requires cypress-grep plugin)
            spec: Specific spec file to run
            browser: Browser to use (electron, chrome, firefox, edge)
            headless: Run in headless mode
            timeout: Timeout in seconds
            
        Returns:
            List of TestResult objects
        """
        results = []
        
        try:
            # Build Cypress command
            cmd = ["npx", "cypress", "run"]
            
            # Add browser
            cmd.extend(["--browser", browser])
            
            # Add headless flag
            if headless:
                cmd.append("--headless")
            
            # Add spec filter
            if spec:
                cmd.extend(["--spec", spec])
            
            # Add config for test type
            if self.config.test_type == CypressTestType.COMPONENT:
                cmd.extend(["--component"])
            else:
                cmd.extend(["--e2e"])
            
            # Add grep for tags (if cypress-grep is installed)
            if tags:
                grep_pattern = "|".join(tags)
                cmd.extend(["--env", f"grep={grep_pattern}"])
            
            # Generate JSON report
            results_dir = self.config.project_root / "cypress" / "results"
            results_dir.mkdir(exist_ok=True)
            
            cmd.extend([
                "--reporter", "json",
                "--reporter-options", f"output={results_dir}/results.json"
            ])
            
            # Run tests
            result = subprocess.run(
                cmd,
                cwd=str(self.config.project_root),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Parse JSON results
            results_file = results_dir / "results.json"
            if results_file.exists():
                results = self._parse_json_results(results_file)
            else:
                # Fallback - create result from stdout
                status = "pass" if result.returncode == 0 else "fail"
                results.append(TestResult(
                    name="cypress tests",
                    status=status,
                    duration_ms=0,
                    message=result.stdout[:200] if result.stdout else ""
                ))
        
        except subprocess.TimeoutExpired:
            results.append(TestResult(
                name="cypress tests",
                status="fail",
                duration_ms=timeout * 1000,
                message="Test execution timed out"
            ))
        
        except FileNotFoundError:
            results.append(TestResult(
                name="cypress tests",
                status="fail",
                duration_ms=0,
                message="Cypress not found. Run 'npm install cypress' first."
            ))
        
        except Exception as e:
            results.append(TestResult(
                name="cypress tests",
                status="fail",
                duration_ms=0,
                message=f"Error executing tests: {str(e)}"
            ))
        
        return results
    
    def _parse_json_results(self, results_file: Path) -> List[TestResult]:
        """Parse Cypress JSON results."""
        try:
            content = json.loads(results_file.read_text(encoding='utf-8'))
            results = []
            
            # Cypress JSON format has runs array with tests
            runs = content.get('runs', [])
            
            for run in runs:
                tests = run.get('tests', [])
                
                for test in tests:
                    title = test.get('title', ['unknown'])
                    if isinstance(title, list):
                        test_name = ' > '.join(title)
                    else:
                        test_name = str(title)
                    
                    state = test.get('state', 'unknown')
                    duration_ms = test.get('duration', 0)
                    
                    # Map Cypress states to our states
                    status_map = {
                        'passed': 'pass',
                        'failed': 'fail',
                        'pending': 'skip',
                        'skipped': 'skip'
                    }
                    status = status_map.get(state, 'fail')
                    
                    # Get error message if failed
                    message = ""
                    if status == 'fail':
                        error = test.get('err', {})
                        message = error.get('message', '') or error.get('stack', '')
                    
                    results.append(TestResult(
                        name=test_name,
                        status=status,
                        duration_ms=duration_ms,
                        message=message[:500] if message else ""
                    ))
            
            return results
        
        except Exception as e:
            print(f"Warning: Error parsing results: {e}")
            return [TestResult(
                name="cypress tests",
                status="fail",
                duration_ms=0,
                message=f"Error parsing results: {str(e)}"
            )]
    
    def get_config_info(self) -> Dict[str, str]:
        """Get configuration information."""
        return {
            'test_type': self.config.test_type.value,
            'has_typescript': str(self.config.has_typescript),
            'cypress_version': self.config.cypress_version or 'unknown',
            'specs_dir': str(self.config.specs_dir),
            'config_file': str(self.config.config_file)
        }


class CypressExtractor(BaseTestExtractor):
    """
    Extracts metadata from Cypress tests.
    
    Provides detailed information about test structure, custom commands,
    and fixtures for migration and analysis purposes.
    """
    
    def __init__(self, project_root: str, config: Optional[CypressConfig] = None):
        """
        Initialize Cypress extractor.
        
        Args:
            project_root: Path to Cypress project
            config: Optional pre-detected configuration
        """
        self.project_root = Path(project_root)
        
        if config is None:
            detector = CypressProjectDetector(project_root)
            config = detector.detect()
            
            if config is None:
                raise ValueError(
                    f"Could not detect Cypress project at {project_root}"
                )
        
        self.config = config
        self.parser = CypressTestParser()
    
    def extract_tests(self) -> List[TestMetadata]:
        """
        Extract test metadata from all spec files.
        
        Returns:
            List of TestMetadata objects
        """
        tests = []
        
        try:
            # Find all spec files
            spec_patterns = ["*.cy.js", "*.cy.ts", "*.spec.js", "*.spec.ts"]
            
            for pattern in spec_patterns:
                spec_files = list(self.config.specs_dir.rglob(pattern))
                
                for spec_file in spec_files:
                    file_tests = self.parser.parse_test_file(spec_file)
                    
                    for test in file_tests:
                        # Determine language from file extension
                        language = "typescript" if spec_file.suffix == ".ts" else "javascript"
                        
                        metadata = TestMetadata(
                            test_name=test['name'],
                            file_path=str(spec_file),
                            framework="cypress",
                            tags=[self.config.test_type.value],
                            language=language
                        )
                        tests.append(metadata)
        
        except Exception as e:
            print(f"Warning: Error extracting tests: {e}")
        
        return tests
    
    def extract_tests_with_memory(self) -> List[UnifiedTestMemory]:
        """
        Extract tests and convert to UnifiedTestMemory format.
        
        Returns:
            List of UnifiedTestMemory objects with structural and semantic signals
        """
        tests = []
        normalizer = UniversalTestNormalizer()
        
        try:
            # Find all spec files
            spec_patterns = ["*.cy.js", "*.cy.ts", "*.spec.js", "*.spec.ts"]
            
            for pattern in spec_patterns:
                spec_files = list(self.config.specs_dir.rglob(pattern))
                
                for spec_file in spec_files:
                    # Read source code for AST extraction
                    try:
                        source_code = spec_file.read_text(encoding='utf-8')
                    except Exception:
                        source_code = None
                    
                    file_tests = self.parser.parse_test_file(spec_file)
                    
                    for test in file_tests:
                        # Determine language
                        language = "typescript" if spec_file.suffix == ".ts" else "javascript"
                        
                        # Create metadata
                        metadata = TestMetadata(
                            test_name=test['name'],
                            file_path=str(spec_file),
                            framework="cypress",
                            tags=[self.config.test_type.value, "e2e"],
                            test_type="e2e",
                            language=language
                        )
                        
                        # Normalize to UnifiedTestMemory
                        unified = normalizer.normalize(
                            metadata,
                            source_code=source_code,
                            generate_embedding=True
                        )
                        tests.append(unified)
        
        except Exception as e:
            print(f"Warning: Error extracting tests with memory: {e}")
        
        return tests
    
    def extract_custom_commands(self) -> List[Dict]:
        """
        Extract custom Cypress commands.
        
        Returns:
            List of dictionaries with command information
        """
        commands = []
        
        if self.config.support_file and self.config.support_file.exists():
            command_names = self.parser.extract_custom_commands(self.config.support_file)
            
            for cmd_name in command_names:
                commands.append({
                    'name': cmd_name,
                    'file': str(self.config.support_file),
                    'type': 'custom_command'
                })
        
        return commands
    
    def extract_fixtures(self) -> List[Dict]:
        """
        Extract fixture files.
        
        Returns:
            List of dictionaries with fixture information
        """
        fixtures = []
        
        if self.config.fixtures_dir and self.config.fixtures_dir.exists():
            fixture_files = list(self.config.fixtures_dir.rglob("*.json"))
            
            for fixture_file in fixture_files:
                fixtures.append({
                    'name': fixture_file.stem,
                    'path': str(fixture_file),
                    'type': 'json_fixture'
                })
        
        return fixtures
    
    def extract_page_objects(self) -> List[Dict]:
        """
        Extract page object patterns from Cypress project.
        
        Note: Cypress doesn't have a standard page object pattern,
        but we can detect common patterns in support files.
        
        Returns:
            List of dictionaries with page object information
        """
        page_objects = []
        
        try:
            support_dir = self.config.project_root / "cypress" / "support"
            
            if support_dir.exists():
                # Look for common page object patterns
                for js_file in support_dir.rglob("*.js"):
                    content = js_file.read_text(encoding='utf-8')
                    
                    # Look for class definitions
                    class_pattern = r'class\s+(\w+Page)\s*{'
                    classes = re.findall(class_pattern, content)
                    
                    for class_name in classes:
                        page_objects.append({
                            'class_name': class_name,
                            'file': str(js_file),
                            'type': 'page_object'
                        })
                
                for ts_file in support_dir.rglob("*.ts"):
                    content = ts_file.read_text(encoding='utf-8')
                    
                    class_pattern = r'class\s+(\w+Page)\s*{'
                    classes = re.findall(class_pattern, content)
                    
                    for class_name in classes:
                        page_objects.append({
                            'class_name': class_name,
                            'file': str(ts_file),
                            'type': 'page_object'
                        })
        
        except Exception as e:
            print(f"Warning: Error extracting page objects: {e}")
        
        return page_objects
