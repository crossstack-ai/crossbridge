"""
Selenium BDD Java test extractor.

Parses Cucumber/Gherkin .feature files to extract test metadata.
"""

from pathlib import Path
import re
from typing import List
import logging

from adapters.common.extractor import BaseTestExtractor
from adapters.common.models import TestMetadata
from .config import SeleniumBDDJavaConfig
from .patterns import (
    FEATURE_PATTERN,
    SCENARIO_PATTERN,
    SCENARIO_OUTLINE_PATTERN,
    TAG_PATTERN,
    COMMENT_PATTERN,
)

logger = logging.getLogger(__name__)


class SeleniumBDDJavaExtractor(BaseTestExtractor):
    """
    Extracts test metadata from Cucumber/Gherkin feature files.
    
    Supports:
    - Feature declarations
    - Scenario and Scenario Outline
    - Feature-level and scenario-level tags
    - Multiple .feature files
    
    Example:
        >>> config = SeleniumBDDJavaConfig(features_dir="src/test/resources/features")
        >>> extractor = SeleniumBDDJavaExtractor(config)
        >>> tests = extractor.extract_tests()
        >>> for test in tests:
        ...     print(f"{test.test_name} - Tags: {test.tags}")
    """
    
    def __init__(self, config: SeleniumBDDJavaConfig = None):
        """
        Initialize the extractor.
        
        Args:
            config: Configuration for feature file discovery. If None, uses defaults.
        """
        self.config = config or SeleniumBDDJavaConfig()
        
    def extract_tests(self) -> List[TestMetadata]:
        """
        Extract all test scenarios from feature files.
        
        Returns:
            List of TestMetadata objects, one per Scenario/Scenario Outline.
            
        Example output:
            TestMetadata(
                framework="selenium-bdd-java",
                test_name="Login Feature::Valid login",
                file_path="src/test/resources/features/login.feature",
                tags=["auth", "smoke", "positive"],
                test_type="ui",
                language="java"
            )
        """
        results = []
        features_path = Path(self.config.features_dir)
        
        if not features_path.exists():
            logger.warning(f"Features directory not found: {self.config.features_dir}")
            return results
            
        # Find all .feature files
        feature_files = list(features_path.rglob("*.feature"))
        
        # Apply ignore patterns
        if self.config.ignore_patterns:
            feature_files = self._filter_ignored_files(feature_files)
            
        logger.info(f"Found {len(feature_files)} feature files in {self.config.features_dir}")
        
        for feature_file in feature_files:
            try:
                tests = self._extract_from_file(feature_file)
                results.extend(tests)
            except Exception as e:
                logger.error(f"Error parsing {feature_file}: {e}")
                
        logger.info(f"Extracted {len(results)} scenarios from {len(feature_files)} feature files")
        return results
    
    def _extract_from_file(self, feature_file: Path) -> List[TestMetadata]:
        """
        Extract scenarios from a single feature file.
        
        Args:
            feature_file: Path to the .feature file
            
        Returns:
            List of TestMetadata for scenarios in this file
        """
        content = feature_file.read_text(encoding=self.config.encoding, errors="ignore")
        
        # Extract feature name (required)
        feature_name = self._extract_feature_name(content)
        
        # Extract feature-level tags
        feature_tags = self._extract_feature_tags(content)
        
        # Extract all scenarios
        scenarios = self._extract_scenarios(content)
        
        # Build TestMetadata for each scenario
        results = []
        for scenario in scenarios:
            # Combine feature-level and scenario-level tags
            all_tags = list(set(feature_tags + scenario["tags"]))
            
            results.append(
                TestMetadata(
                    framework="selenium-bdd-java",
                    test_name=f"{feature_name}::{scenario['name']}",
                    file_path=str(feature_file),
                    tags=all_tags,
                    test_type="ui",
                    language="java",
                )
            )
            
        return results
    
    def _extract_feature_name(self, content: str) -> str:
        """
        Extract the feature name from feature file content.
        
        Args:
            content: Feature file content
            
        Returns:
            Feature name or "UnknownFeature" if not found
        """
        for line in content.splitlines():
            # Skip comments
            if re.match(COMMENT_PATTERN, line):
                continue
                
            match = re.match(FEATURE_PATTERN, line)
            if match:
                return match.group(1).strip()
                
        return "UnknownFeature"
    
    def _extract_feature_tags(self, content: str) -> List[str]:
        """
        Extract tags that appear before the Feature declaration.
        
        Args:
            content: Feature file content
            
        Returns:
            List of feature-level tags
        """
        tags = []
        
        for line in content.splitlines():
            # Skip comments
            if re.match(COMMENT_PATTERN, line):
                continue
                
            # If we hit Feature declaration, stop
            if re.match(FEATURE_PATTERN, line):
                break
                
            # Collect tags
            if line.strip().startswith("@"):
                tags.extend(re.findall(TAG_PATTERN, line))
                
        return tags
    
    def _extract_scenarios(self, content: str) -> List[dict]:
        """
        Extract all scenarios and scenario outlines from feature content.
        
        Args:
            content: Feature file content
            
        Returns:
            List of dicts with 'name' and 'tags' keys
        """
        scenarios = []
        lines = content.splitlines()
        
        current_tags = []
        in_feature = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip comments
            if re.match(COMMENT_PATTERN, line_stripped):
                continue
            
            # Track when we're inside Feature block
            if re.match(FEATURE_PATTERN, line_stripped):
                in_feature = True
                continue
            
            # Only process scenarios inside Feature block
            if not in_feature:
                continue
            
            # Collect tags (can be multiple on one line: @tag1 @tag2)
            if line_stripped.startswith("@"):
                current_tags.extend(re.findall(TAG_PATTERN, line_stripped))
                continue
            
            # Match Scenario or Scenario Outline
            scenario_match = re.match(SCENARIO_PATTERN, line_stripped)
            outline_match = re.match(SCENARIO_OUTLINE_PATTERN, line_stripped)
            
            if scenario_match or outline_match:
                name = (scenario_match or outline_match).group(1).strip()
                
                scenarios.append({
                    "name": name,
                    "tags": current_tags.copy(),
                })
                
                # Reset tags for next scenario
                current_tags = []
        
        return scenarios
    
    def _filter_ignored_files(self, files: List[Path]) -> List[Path]:
        """
        Filter out files matching ignore patterns.
        
        Args:
            files: List of feature file paths
            
        Returns:
            Filtered list excluding ignored patterns
        """
        filtered = []
        
        for file in files:
            should_ignore = False
            
            for pattern in self.config.ignore_patterns:
                if file.match(pattern):
                    should_ignore = True
                    logger.debug(f"Ignoring {file} (matches pattern: {pattern})")
                    break
                    
            if not should_ignore:
                filtered.append(file)
                
        return filtered
