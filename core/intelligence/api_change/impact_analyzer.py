"""
Impact Analyzer - Maps API changes to potentially affected tests.

This module provides intelligent test-to-endpoint mapping by analyzing:
1. Static code analysis (import patterns, string literals)
2. Runtime coverage data (if available)
3. Test naming conventions
4. Configuration-based mappings
"""

import re
from typing import List, Dict, Set, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from core.intelligence.api_change.models.api_change import APIChangeEvent, EntityType
from core.intelligence.api_change.models.test_impact import TestImpact, CoverageType


class ConfidenceLevel(str, Enum):
    """Confidence level for test impact prediction."""
    HIGH = "high"          # >80% - Direct reference found
    MEDIUM = "medium"      # 40-80% - Indirect reference or pattern match
    LOW = "low"            # <40% - Weak correlation


@dataclass
class TestMapping:
    """Represents a test-to-endpoint mapping."""
    test_file: str
    test_name: Optional[str]
    endpoint_path: str
    method: str
    confidence: ConfidenceLevel
    evidence: List[str]  # Why we think this test is affected
    line_numbers: List[int]  # Where the endpoint is referenced


class ImpactAnalyzer:
    """
    Analyzes API changes and identifies potentially affected tests.
    
    This analyzer uses multiple strategies:
    1. Static analysis: Parse test files for endpoint references
    2. Coverage data: Use runtime coverage if available
    3. Convention-based: Match test names to endpoint patterns
    4. Configuration: User-provided test-to-API mappings
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the impact analyzer.
        
        Args:
            config: Optional configuration with:
                - test_directories: List of test directories to scan
                - coverage_file: Path to coverage data file
                - custom_mappings: User-defined test-to-endpoint mappings
                - framework: Test framework (pytest, robot, etc.)
        """
        self.config = config or {}
        self.test_directories = self.config.get('test_directories', ['tests/', 'test/'])
        self.coverage_file = self.config.get('coverage_file')
        self.custom_mappings = self.config.get('custom_mappings', {})
        self.framework = self.config.get('framework', 'pytest')
        
        # Cache for parsed test files
        self._test_file_cache: Dict[str, str] = {}
        # Coverage data cache
        self._coverage_data: Optional[Dict] = None
    
    def analyze_impact(
        self,
        changes: List[APIChangeEvent],
        workspace_root: Optional[Path] = None
    ) -> List[TestImpact]:
        """
        Analyze API changes and identify affected tests.
        
        Args:
            changes: List of API change events
            workspace_root: Root directory of the workspace
        
        Returns:
            List of TestImpact objects with affected tests
        """
        impacts: List[TestImpact] = []
        workspace_root = workspace_root or Path.cwd()
        
        # Load coverage data if available
        if self.coverage_file:
            self._load_coverage_data(workspace_root / self.coverage_file)
        
        for change in changes:
            # Skip non-endpoint changes for now
            if change.entity_type not in [EntityType.ENDPOINT, EntityType.PARAMETER, EntityType.RESPONSE]:
                continue
            
            # Get endpoint path from change
            endpoint_path = self._extract_endpoint_path(change)
            if not endpoint_path:
                continue
            
            method = change.method or "GET"
            
            # Find affected tests using multiple strategies
            test_mappings = self._find_affected_tests(
                endpoint_path=endpoint_path,
                method=method,
                workspace_root=workspace_root
            )
            
            # Convert mappings to TestImpact objects
            for mapping in test_mappings:
                impact = TestImpact(
                    test_file=mapping.test_file,
                    test_name=mapping.test_name,
                    endpoint=endpoint_path,
                    method=method,
                    coverage_type=self._determine_coverage_type(mapping),
                    confidence=float(self._confidence_to_score(mapping.confidence)),
                    reason=f"Test likely affected by {change.change_type} change. Evidence: {', '.join(mapping.evidence)}"
                )
                impacts.append(impact)
        
        # Deduplicate impacts
        return self._deduplicate_impacts(impacts)
    
    def _find_affected_tests(
        self,
        endpoint_path: str,
        method: str,
        workspace_root: Path
    ) -> List[TestMapping]:
        """Find tests that might be affected by an endpoint change."""
        mappings: List[TestMapping] = []
        
        # Strategy 1: Check custom mappings
        custom = self._check_custom_mappings(endpoint_path, method)
        mappings.extend(custom)
        
        # Strategy 2: Static code analysis
        static = self._analyze_static_references(endpoint_path, method, workspace_root)
        mappings.extend(static)
        
        # Strategy 3: Coverage data analysis
        if self._coverage_data:
            coverage = self._analyze_coverage_data(endpoint_path, method)
            mappings.extend(coverage)
        
        # Strategy 4: Convention-based matching
        convention = self._match_by_convention(endpoint_path, method, workspace_root)
        mappings.extend(convention)
        
        return mappings
    
    def _check_custom_mappings(self, endpoint_path: str, method: str) -> List[TestMapping]:
        """Check user-provided custom test-to-endpoint mappings."""
        mappings = []
        key = f"{method} {endpoint_path}"
        
        if key in self.custom_mappings:
            for test_info in self.custom_mappings[key]:
                mappings.append(TestMapping(
                    test_file=test_info['test_file'],
                    test_name=test_info.get('test_name'),
                    endpoint_path=endpoint_path,
                    method=method,
                    confidence=ConfidenceLevel.HIGH,
                    evidence=["Custom mapping configured"],
                    line_numbers=[]
                ))
        
        return mappings
    
    def _analyze_static_references(
        self,
        endpoint_path: str,
        method: str,
        workspace_root: Path
    ) -> List[TestMapping]:
        """Analyze test files for static references to the endpoint."""
        mappings = []
        
        # Find all test files
        test_files = self._find_test_files(workspace_root)
        
        for test_file in test_files:
            # Read file content
            content = self._read_test_file(test_file)
            if not content:
                continue
            
            # Look for endpoint references
            evidence = []
            line_numbers = []
            
            # Pattern 1: Direct string literal "/api/users"
            if endpoint_path in content:
                evidence.append(f"Direct endpoint reference: '{endpoint_path}'")
                line_numbers.extend(self._find_line_numbers(content, endpoint_path))
            
            # Pattern 2: Method reference "GET /api/users"
            method_ref = f"{method.upper()} {endpoint_path}"
            if method_ref in content:
                evidence.append(f"Method+endpoint reference: '{method_ref}'")
                line_numbers.extend(self._find_line_numbers(content, method_ref))
            
            # Pattern 3: URL construction patterns
            url_patterns = self._extract_url_patterns(endpoint_path)
            for pattern in url_patterns:
                if pattern in content:
                    evidence.append(f"URL pattern match: '{pattern}'")
                    line_numbers.extend(self._find_line_numbers(content, pattern))
            
            # Pattern 4: Common API client patterns
            api_patterns = [
                f'"{endpoint_path}"',
                f"'{endpoint_path}'",
                f'url="{endpoint_path}"',
                f"url='{endpoint_path}'",
                f'path="{endpoint_path}"',
                f"path='{endpoint_path}'",
                f'endpoint="{endpoint_path}"',
                f"endpoint='{endpoint_path}'"
            ]
            for pattern in api_patterns:
                if pattern in content:
                    evidence.append(f"API client pattern: {pattern}")
                    line_numbers.extend(self._find_line_numbers(content, pattern))
            
            if evidence:
                # Determine confidence based on evidence strength
                confidence = ConfidenceLevel.HIGH if len(evidence) >= 2 else ConfidenceLevel.MEDIUM
                
                # Try to extract test function names
                test_names = self._extract_test_names(content, self.framework)
                
                if test_names:
                    for test_name in test_names:
                        mappings.append(TestMapping(
                            test_file=str(test_file),
                            test_name=test_name,
                            endpoint_path=endpoint_path,
                            method=method,
                            confidence=confidence,
                            evidence=evidence,
                            line_numbers=line_numbers
                        ))
                else:
                    # Add file-level mapping if no specific tests found
                    mappings.append(TestMapping(
                        test_file=str(test_file),
                        test_name=None,
                        endpoint_path=endpoint_path,
                        method=method,
                        confidence=confidence,
                        evidence=evidence,
                        line_numbers=line_numbers
                    ))
        
        return mappings
    
    def _analyze_coverage_data(self, endpoint_path: str, method: str) -> List[TestMapping]:
        """Analyze runtime coverage data to find affected tests."""
        mappings = []
        
        if not self._coverage_data:
            return mappings
        
        # Look for endpoint in coverage data
        # This would need to be implemented based on coverage data format
        # For now, return empty list
        
        return mappings
    
    def _match_by_convention(
        self,
        endpoint_path: str,
        method: str,
        workspace_root: Path
    ) -> List[TestMapping]:
        """Match tests based on naming conventions."""
        mappings = []
        
        # Extract key parts from endpoint
        # e.g., "/api/v1/users/{id}" -> ["users", "id"]
        path_parts = [p for p in endpoint_path.split('/') if p and not p.startswith('{')]
        
        if not path_parts:
            return mappings
        
        # Find test files that might match
        test_files = self._find_test_files(workspace_root)
        
        for test_file in test_files:
            file_name = Path(test_file).stem.lower()
            
            # Check if any path part is in the test file name
            matches = [part.lower() for part in path_parts if part.lower() in file_name]
            
            if matches:
                mappings.append(TestMapping(
                    test_file=str(test_file),
                    test_name=None,
                    endpoint_path=endpoint_path,
                    method=method,
                    confidence=ConfidenceLevel.LOW,
                    evidence=[f"File name matches endpoint components: {', '.join(matches)}"],
                    line_numbers=[]
                ))
        
        return mappings
    
    def _find_test_files(self, workspace_root: Path) -> List[Path]:
        """Find all test files in the workspace."""
        test_files = []
        
        for test_dir in self.test_directories:
            test_path = workspace_root / test_dir
            if not test_path.exists():
                continue
            
            # Find test files based on framework
            if self.framework == 'pytest':
                test_files.extend(test_path.rglob('test_*.py'))
                test_files.extend(test_path.rglob('*_test.py'))
            elif self.framework == 'robot':
                test_files.extend(test_path.rglob('*.robot'))
            elif self.framework in ['selenium', 'playwright', 'cypress']:
                test_files.extend(test_path.rglob('*.spec.js'))
                test_files.extend(test_path.rglob('*.spec.ts'))
                test_files.extend(test_path.rglob('*.test.js'))
                test_files.extend(test_path.rglob('*.test.ts'))
            else:
                # Generic: find common test file patterns
                test_files.extend(test_path.rglob('*test*.py'))
                test_files.extend(test_path.rglob('*test*.js'))
                test_files.extend(test_path.rglob('*test*.ts'))
        
        return list(set(test_files))
    
    def _read_test_file(self, test_file: Path) -> Optional[str]:
        """Read test file content with caching."""
        test_file_str = str(test_file)
        
        if test_file_str in self._test_file_cache:
            return self._test_file_cache[test_file_str]
        
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self._test_file_cache[test_file_str] = content
                return content
        except Exception:
            return None
    
    def _find_line_numbers(self, content: str, search_string: str) -> List[int]:
        """Find line numbers where a string appears in content."""
        lines = content.split('\n')
        return [i + 1 for i, line in enumerate(lines) if search_string in line]
    
    def _extract_url_patterns(self, endpoint_path: str) -> List[str]:
        """Extract possible URL pattern variations."""
        patterns = []
        
        # Remove leading/trailing slashes
        path = endpoint_path.strip('/')
        
        # Add with different bases
        patterns.append(f"/api/{path}")
        patterns.append(f"/v1/{path}")
        patterns.append(f"/api/v1/{path}")
        
        # Replace path parameters with common patterns
        if '{' in path:
            # Replace {id} with common patterns
            patterns.append(re.sub(r'\{[^}]+\}', r'\\d+', path))
            patterns.append(re.sub(r'\{[^}]+\}', r'[^/]+', path))
        
        return patterns
    
    def _extract_test_names(self, content: str, framework: str) -> List[str]:
        """Extract test function/method names from file content."""
        test_names = []
        
        if framework == 'pytest':
            # Match: def test_something(...)
            pattern = r'def\s+(test_\w+)\s*\('
            test_names.extend(re.findall(pattern, content))
        elif framework == 'robot':
            # Match: *** Test Cases *** section
            # This is simplified - real Robot parsing is more complex
            pattern = r'^\*\*\* Test Cases \*\*\*\s*\n(.*?)(?=\*\*\*|\Z)'
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            if matches:
                # Extract test case names (lines that don't start with spaces)
                for match in matches:
                    lines = match.split('\n')
                    test_names.extend([line.strip() for line in lines if line and not line.startswith(' ')])
        elif framework in ['selenium', 'playwright', 'cypress']:
            # Match: it('test name', ...) or test('test name', ...)
            patterns = [
                r'it\s*\(\s*["\']([^"\']+)["\']',
                r'test\s*\(\s*["\']([^"\']+)["\']'
            ]
            for pattern in patterns:
                test_names.extend(re.findall(pattern, content))
        
        return test_names
    
    def _extract_endpoint_path(self, change: APIChangeEvent) -> Optional[str]:
        """Extract endpoint path from change event."""
        if change.entity_type == EntityType.ENDPOINT:
            return change.path
        elif change.entity_type in [EntityType.PARAMETER, EntityType.RESPONSE]:
            # Extract path from operation_id or path field
            return change.path
        return None
    
    def _determine_coverage_type(self, mapping: TestMapping) -> CoverageType:
        """Determine coverage type based on mapping confidence."""
        if mapping.confidence == ConfidenceLevel.HIGH:
            return CoverageType.RUNTIME
        elif mapping.confidence == ConfidenceLevel.MEDIUM:
            return CoverageType.STATIC
        else:
            return CoverageType.INFERRED
    
    def _confidence_to_score(self, confidence: ConfidenceLevel) -> float:
        """Convert confidence level to numerical score."""
        mapping = {
            ConfidenceLevel.HIGH: 0.85,
            ConfidenceLevel.MEDIUM: 0.60,
            ConfidenceLevel.LOW: 0.35
        }
        return mapping.get(confidence, 0.5)
    
    def _deduplicate_impacts(self, impacts: List[TestImpact]) -> List[TestImpact]:
        """Remove duplicate test impacts, keeping highest confidence."""
        unique: Dict[tuple, TestImpact] = {}
        
        for impact in impacts:
            key = (impact.test_file, impact.test_name, impact.endpoint, impact.method)
            
            if key not in unique or impact.confidence > unique[key].confidence:
                unique[key] = impact
        
        return list(unique.values())
    
    def _load_coverage_data(self, coverage_file: Path) -> None:
        """Load coverage data from file (placeholder)."""
        # This would load actual coverage data
        # Format depends on the coverage tool used
        pass
    
    def get_test_selection_recommendations(
        self,
        impacts: List[TestImpact],
        min_confidence: float = 0.5
    ) -> Dict[str, List[str]]:
        """
        Get test selection recommendations grouped by confidence.
        
        Args:
            impacts: List of test impacts
            min_confidence: Minimum confidence threshold
        
        Returns:
            Dictionary with 'must_run', 'should_run', 'could_run' test lists
        """
        must_run = []
        should_run = []
        could_run = []
        
        for impact in impacts:
            if impact.confidence < min_confidence:
                continue
            
            test_ref = impact.test_name or impact.test_file
            
            if impact.confidence >= 0.75:
                must_run.append(test_ref)
            elif impact.confidence >= 0.50:
                should_run.append(test_ref)
            else:
                could_run.append(test_ref)
        
        return {
            'must_run': list(set(must_run)),
            'should_run': list(set(should_run)),
            'could_run': list(set(could_run))
        }
