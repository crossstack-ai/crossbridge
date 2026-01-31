"""
Robot Framework Static Parser for Fast Test Discovery.

This module provides static file parsing for Robot Framework test discovery,
replacing the slow --dryrun approach with direct file parsing.

This module addresses Gap 6.3 in the Framework Gap Analysis:
- Static parsing of .robot files for test discovery
- Extraction of test cases, keywords, and metadata
- Tag extraction without execution
- Significantly faster than --dryrun mode

Usage:
    from adapters.robot.static_parser import RobotStaticParser
    
    parser = RobotStaticParser(project_root="/path/to/tests")
    tests = parser.discover_tests()
    
    for test in tests:
        print(f"Test: {test['name']}")
        print(f"Tags: {test['tags']}")
        print(f"File: {test['file']}")
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class RobotSection(Enum):
    """Robot Framework file sections."""
    SETTINGS = "settings"
    VARIABLES = "variables"
    TEST_CASES = "test_cases"
    KEYWORDS = "keywords"
    COMMENTS = "comments"
    NONE = "none"


@dataclass
class RobotTest:
    """Represents a discovered Robot Framework test."""
    name: str
    suite_name: str
    file_path: str
    line_number: int
    tags: List[str] = field(default_factory=list)
    documentation: Optional[str] = None
    setup: Optional[str] = None
    teardown: Optional[str] = None
    template: Optional[str] = None
    timeout: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "suite_name": self.suite_name,
            "file": self.file_path,
            "line": self.line_number,
            "tags": self.tags,
            "documentation": self.documentation,
            "setup": self.setup,
            "teardown": self.teardown,
            "template": self.template,
            "timeout": self.timeout,
            "full_name": f"{self.suite_name}.{self.name}",
        }


@dataclass
class RobotSuite:
    """Represents a Robot Framework test suite."""
    name: str
    file_path: str
    tests: List[RobotTest] = field(default_factory=list)
    suite_setup: Optional[str] = None
    suite_teardown: Optional[str] = None
    default_tags: List[str] = field(default_factory=list)
    force_tags: List[str] = field(default_factory=list)
    documentation: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "file": self.file_path,
            "tests": [test.to_dict() for test in self.tests],
            "suite_setup": self.suite_setup,
            "suite_teardown": self.suite_teardown,
            "default_tags": self.default_tags,
            "force_tags": self.force_tags,
            "documentation": self.documentation,
        }


class RobotFileParser:
    """Parser for individual Robot Framework files."""
    
    # Section headers (case-insensitive)
    SECTION_PATTERNS = {
        RobotSection.SETTINGS: r'\*+\s*settings?\s*\*+',
        RobotSection.VARIABLES: r'\*+\s*variables?\s*\*+',
        RobotSection.TEST_CASES: r'\*+\s*test\s*cases?\s*\*+',
        RobotSection.KEYWORDS: r'\*+\s*(?:keywords?|user\s*keywords?)\s*\*+',
        RobotSection.COMMENTS: r'\*+\s*comments?\s*\*+',
    }
    
    def __init__(self, file_path: Path):
        """
        Initialize parser for a Robot file.
        
        Args:
            file_path: Path to .robot file
        """
        self.file_path = file_path
        self.suite_name = file_path.stem
        self.current_section = RobotSection.NONE
        self.suite = RobotSuite(
            name=self.suite_name,
            file_path=str(file_path)
        )
    
    def parse(self) -> RobotSuite:
        """
        Parse the Robot file and extract test information.
        
        Returns:
            RobotSuite with discovered tests
        """
        try:
            content = self.file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            
            i = 0
            while i < len(lines):
                line = lines[i]
                i += 1
                
                # Skip empty lines and comments
                if not line.strip() or line.strip().startswith('#'):
                    continue
                
                # Check for section headers
                section = self._detect_section(line)
                if section:
                    self.current_section = section
                    continue
                
                # Parse based on current section
                if self.current_section == RobotSection.SETTINGS:
                    self._parse_settings_line(line)
                elif self.current_section == RobotSection.TEST_CASES:
                    # Check if this is a test case name (not indented)
                    if line and not line[0].isspace():
                        test_name = self._extract_test_name(line)
                        if test_name:
                            # Parse test and its settings
                            test, lines_consumed = self._parse_test_case(
                                test_name, lines, i - 1
                            )
                            self.suite.tests.append(test)
                            i += lines_consumed
        
        except Exception as e:
            print(f"Warning: Error parsing {self.file_path}: {e}")
        
        return self.suite
    
    def _detect_section(self, line: str) -> Optional[RobotSection]:
        """Detect if line is a section header."""
        line_stripped = line.strip().lower()
        
        for section, pattern in self.SECTION_PATTERNS.items():
            if re.match(pattern, line_stripped, re.IGNORECASE):
                return section
        
        return None
    
    def _extract_test_name(self, line: str) -> Optional[str]:
        """Extract test name from line (remove trailing comments)."""
        # Remove comment if present
        if '#' in line:
            line = line[:line.index('#')]
        
        test_name = line.strip()
        
        # Test names shouldn't be empty or start with special characters
        if test_name and not test_name.startswith('['):
            return test_name
        
        return None
    
    def _parse_settings_line(self, line: str) -> None:
        """Parse settings section line."""
        line_stripped = line.strip()
        
        # Suite Setup
        if line_stripped.lower().startswith('suite setup'):
            self.suite.suite_setup = self._extract_setting_value(line_stripped)
        
        # Suite Teardown
        elif line_stripped.lower().startswith('suite teardown'):
            self.suite.suite_teardown = self._extract_setting_value(line_stripped)
        
        # Default Tags
        elif line_stripped.lower().startswith('default tags'):
            tags = self._extract_tags(line_stripped)
            self.suite.default_tags.extend(tags)
        
        # Force Tags
        elif line_stripped.lower().startswith('force tags'):
            tags = self._extract_tags(line_stripped)
            self.suite.force_tags.extend(tags)
        
        # Documentation
        elif line_stripped.lower().startswith('documentation'):
            self.suite.documentation = self._extract_setting_value(line_stripped)
    
    def _parse_test_case(
        self,
        test_name: str,
        lines: List[str],
        start_index: int
    ) -> Tuple[RobotTest, int]:
        """
        Parse a test case and its settings.
        
        Returns:
            Tuple of (RobotTest, number of lines consumed)
        """
        test = RobotTest(
            name=test_name,
            suite_name=self.suite_name,
            file_path=str(self.file_path),
            line_number=start_index + 1,
            tags=self.suite.default_tags.copy() + self.suite.force_tags.copy()
        )
        
        i = start_index + 1
        lines_consumed = 0
        
        # Parse test settings and steps
        while i < len(lines):
            line = lines[i]
            
            # Stop if we hit a new test case (non-indented line)
            if line and not line[0].isspace():
                break
            
            # Skip empty lines
            if not line.strip():
                i += 1
                lines_consumed += 1
                continue
            
            # Parse test settings (lines starting with [)
            line_stripped = line.strip()
            if line_stripped.startswith('['):
                self._parse_test_setting(test, line_stripped)
            
            i += 1
            lines_consumed += 1
        
        return test, lines_consumed
    
    def _parse_test_setting(self, test: RobotTest, line: str) -> None:
        """Parse test-level settings."""
        line_lower = line.lower()
        
        # [Tags]
        if line_lower.startswith('[tags]'):
            tags = self._extract_tags(line)
            test.tags.extend(tags)
        
        # [Documentation]
        elif line_lower.startswith('[documentation]'):
            test.documentation = self._extract_setting_value(line)
        
        # [Setup]
        elif line_lower.startswith('[setup]'):
            test.setup = self._extract_setting_value(line)
        
        # [Teardown]
        elif line_lower.startswith('[teardown]'):
            test.teardown = self._extract_setting_value(line)
        
        # [Template]
        elif line_lower.startswith('[template]'):
            test.template = self._extract_setting_value(line)
        
        # [Timeout]
        elif line_lower.startswith('[timeout]'):
            test.timeout = self._extract_setting_value(line)
    
    def _extract_setting_value(self, line: str) -> str:
        """Extract value from a setting line."""
        # Remove setting name and brackets
        # Example: "Suite Setup    Start Browser" -> "Start Browser"
        parts = re.split(r'\s{2,}', line, maxsplit=1)
        if len(parts) > 1:
            return parts[1].strip()
        
        # Try splitting by tabs
        parts = line.split('\t', maxsplit=1)
        if len(parts) > 1:
            return parts[1].strip()
        
        return ""
    
    def _extract_tags(self, line: str) -> List[str]:
        """Extract tags from a tags setting line."""
        # Remove setting name
        value = self._extract_setting_value(line)
        
        # Split tags by whitespace
        tags = value.split()
        
        return [tag.strip() for tag in tags if tag.strip()]


class RobotStaticParser:
    """Static parser for Robot Framework test discovery."""
    
    def __init__(self, project_root: str):
        """
        Initialize static parser.
        
        Args:
            project_root: Root directory containing Robot Framework tests
        """
        self.project_root = Path(project_root)
    
    def discover_tests(
        self,
        test_path: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Discover all tests using static parsing.
        
        Args:
            test_path: Optional specific path to search (relative to project_root)
            tags: Optional list of tags to filter tests
            
        Returns:
            List of test dictionaries
        """
        search_path = self.project_root / test_path if test_path else self.project_root
        
        if not search_path.exists():
            print(f"Warning: Test path does not exist: {search_path}")
            return []
        
        # Find all .robot files
        robot_files = list(search_path.rglob("*.robot"))
        
        all_tests = []
        
        for robot_file in robot_files:
            parser = RobotFileParser(robot_file)
            suite = parser.parse()
            
            # Convert tests to dictionaries and filter by tags
            for test in suite.tests:
                test_dict = test.to_dict()
                
                # Filter by tags if specified
                if tags and not self._matches_tags(test.tags, tags):
                    continue
                
                all_tests.append(test_dict)
        
        return all_tests
    
    def discover_suites(
        self,
        test_path: Optional[str] = None
    ) -> List[Dict]:
        """
        Discover all test suites using static parsing.
        
        Args:
            test_path: Optional specific path to search
            
        Returns:
            List of suite dictionaries
        """
        search_path = self.project_root / test_path if test_path else self.project_root
        
        if not search_path.exists():
            return []
        
        robot_files = list(search_path.rglob("*.robot"))
        
        suites = []
        
        for robot_file in robot_files:
            parser = RobotFileParser(robot_file)
            suite = parser.parse()
            suites.append(suite.to_dict())
        
        return suites
    
    def get_test_tags(self, test_path: Optional[str] = None) -> Set[str]:
        """
        Get all unique tags from tests.
        
        Args:
            test_path: Optional specific path to search
            
        Returns:
            Set of unique tag names
        """
        tests = self.discover_tests(test_path=test_path)
        
        tags = set()
        for test in tests:
            tags.update(test.get('tags', []))
        
        return tags
    
    def _matches_tags(self, test_tags: List[str], filter_tags: List[str]) -> bool:
        """Check if test tags match filter tags (OR logic)."""
        if not filter_tags:
            return True
        
        test_tags_lower = [tag.lower() for tag in test_tags]
        
        for filter_tag in filter_tags:
            if filter_tag.lower() in test_tags_lower:
                return True
        
        return False


def compare_with_dryrun(
    project_root: str,
    sample_size: int = 10
) -> Dict[str, Any]:
    """
    Compare static parser performance with --dryrun approach.
    
    Args:
        project_root: Root directory of Robot tests
        sample_size: Number of files to sample for comparison
        
    Returns:
        Comparison statistics
    """
    import time
    import subprocess
    import tempfile
    
    # Static parser
    start_static = time.time()
    static_parser = RobotStaticParser(project_root)
    static_tests = static_parser.discover_tests()
    static_time = time.time() - start_static
    
    # Dryrun approach
    start_dryrun = time.time()
    output_dir = tempfile.mkdtemp()
    
    try:
        subprocess.run(
            [
                "robot",
                "--dryrun",
                "--output", f"{output_dir}/output.xml",
                "--log", "NONE",
                "--report", "NONE",
                project_root
            ],
            capture_output=True,
            timeout=60
        )
        dryrun_time = time.time() - start_dryrun
    except Exception as e:
        dryrun_time = -1
        print(f"Dryrun failed: {e}")
    
    speedup = dryrun_time / static_time if dryrun_time > 0 else float('inf')
    
    return {
        "static_time": static_time,
        "dryrun_time": dryrun_time,
        "speedup": speedup,
        "tests_found": len(static_tests),
        "static_tests": static_tests,
    }
