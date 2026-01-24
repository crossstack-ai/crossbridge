# Copyright (c) 2025 Vikas Verma
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Framework Adapters for CrossBridge Intelligent Test Assistance.

Normalize framework-specific test structures into UnifiedTestMemory format.
Language-agnostic through adapter pattern.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from core.intelligence.ast_extractor import ASTExtractorFactory
from core.intelligence.models import (
    UnifiedTestMemory,
    SemanticSignals,
    StructuralSignals,
    TestMetadata,
    TestType,
    Priority,
    APICall,
    Assertion,
)

logger = logging.getLogger(__name__)


class FrameworkAdapter(ABC):
    """
    Abstract base class for framework-specific adapters.
    
    Each adapter must:
    1. Discover tests in a project
    2. Extract test metadata (name, type, priority, etc.)
    3. Extract AST structural signals
    4. Normalize to UnifiedTestMemory format
    """
    
    @abstractmethod
    def discover_tests(self, project_path: str) -> List[str]:
        """
        Discover all test files in project.
        
        Args:
            project_path: Path to project root
            
        Returns:
            List of test file paths
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, test_file: str, test_name: str) -> TestMetadata:
        """
        Extract test metadata from test file.
        
        Args:
            test_file: Path to test file
            test_name: Name of test function/method
            
        Returns:
            TestMetadata object
        """
        pass
    
    @abstractmethod
    def extract_ast_signals(self, test_file: str, test_name: str) -> StructuralSignals:
        """
        Extract AST structural signals from test.
        
        Args:
            test_file: Path to test file
            test_name: Name of test function/method
            
        Returns:
            StructuralSignals object
        """
        pass
    
    @abstractmethod
    def normalize_to_core_model(
        self,
        test_file: str,
        test_name: str,
        semantic_signals: Optional[SemanticSignals] = None,
    ) -> UnifiedTestMemory:
        """
        Normalize test to UnifiedTestMemory format.
        
        Args:
            test_file: Path to test file
            test_name: Name of test function/method
            semantic_signals: Optional pre-computed semantic signals
            
        Returns:
            UnifiedTestMemory object
        """
        pass
    
    @abstractmethod
    def get_framework_name(self) -> str:
        """Return framework name."""
        pass
    
    @abstractmethod
    def get_language(self) -> str:
        """Return programming language."""
        pass


class PytestAdapter(FrameworkAdapter):
    """Adapter for pytest framework (Python)."""
    
    def __init__(self):
        self.framework = "pytest"
        self.language = "python"
        self.extractor = ASTExtractorFactory.get_extractor(self.language)
    
    def discover_tests(self, project_path: str) -> List[str]:
        """Discover pytest test files."""
        project = Path(project_path)
        
        # Pytest patterns: test_*.py or *_test.py
        test_files = []
        test_files.extend(project.rglob("test_*.py"))
        test_files.extend(project.rglob("*_test.py"))
        
        return [str(f) for f in test_files]
    
    def extract_metadata(self, test_file: str, test_name: str) -> TestMetadata:
        """Extract pytest test metadata."""
        # Read test file
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Extract metadata from decorators and docstrings
        test_type = self._infer_test_type(content, test_name)
        priority = self._extract_priority(content, test_name)
        tags = self._extract_pytest_marks(content, test_name)
        
        # Extract feature from file path
        feature = self._extract_feature_from_path(test_file)
        
        return TestMetadata(
            test_type=test_type,
            priority=priority,
            feature=feature,
            tags=tags,
            flakiness_score=0.0,  # TODO: Load from historical data
        )
    
    def extract_ast_signals(self, test_file: str, test_name: str) -> StructuralSignals:
        """Extract AST signals from pytest test."""
        if not self.extractor:
            return StructuralSignals()
        
        with open(test_file, "r", encoding="utf-8") as f:
            source_code = f.read()
        
        return self.extractor.extract(source_code, test_name)
    
    def normalize_to_core_model(
        self,
        test_file: str,
        test_name: str,
        semantic_signals: Optional[SemanticSignals] = None,
    ) -> UnifiedTestMemory:
        """Normalize pytest test to UnifiedTestMemory."""
        
        # Generate test ID
        test_id = f"pytest::{test_file}::{test_name}"
        
        # Extract metadata
        metadata = self.extract_metadata(test_file, test_name)
        
        # Extract structural signals
        structural = self.extract_ast_signals(test_file, test_name)
        
        # Use provided semantic signals or create empty
        semantic = semantic_signals or SemanticSignals()
        
        return UnifiedTestMemory(
            test_id=test_id,
            framework=self.framework,
            language=self.language,
            file_path=test_file,
            test_name=test_name,
            semantic=semantic,
            structural=structural,
            metadata=metadata,
        )
    
    def get_framework_name(self) -> str:
        return self.framework
    
    def get_language(self) -> str:
        return self.language
    
    def _infer_test_type(self, content: str, test_name: str) -> TestType:
        """Infer test type from name and content."""
        name_lower = test_name.lower()
        
        if any(keyword in name_lower for keyword in ["negative", "invalid", "error", "fail"]):
            return TestType.NEGATIVE
        elif any(keyword in name_lower for keyword in ["boundary", "edge", "limit"]):
            return TestType.BOUNDARY
        elif "integration" in name_lower:
            return TestType.INTEGRATION
        elif "unit" in name_lower:
            return TestType.UNIT
        elif any(keyword in name_lower for keyword in ["e2e", "end_to_end", "endtoend"]):
            return TestType.E2E
        else:
            return TestType.POSITIVE
    
    def _extract_priority(self, content: str, test_name: str) -> Priority:
        """Extract priority from pytest marks."""
        # Look for @pytest.mark.priority or similar
        if f"@pytest.mark.p0" in content or f"@pytest.mark.critical" in content:
            return Priority.P0
        elif f"@pytest.mark.p1" in content or f"@pytest.mark.high" in content:
            return Priority.P1
        elif f"@pytest.mark.p3" in content or f"@pytest.mark.low" in content:
            return Priority.P3
        else:
            return Priority.P2
    
    def _extract_pytest_marks(self, content: str, test_name: str) -> List[str]:
        """Extract pytest markers as tags."""
        tags = []
        
        # Common pytest marks
        marks = ["smoke", "regression", "slow", "fast", "skip", "xfail", "parametrize"]
        
        for mark in marks:
            if f"@pytest.mark.{mark}" in content:
                tags.append(mark)
        
        return tags
    
    def _extract_feature_from_path(self, test_file: str) -> str:
        """Extract feature name from file path."""
        # Get parent directory name as feature
        path = Path(test_file)
        if path.parent.name == "tests":
            return "general"
        return path.parent.name


class JUnitAdapter(FrameworkAdapter):
    """Adapter for JUnit framework (Java)."""
    
    def __init__(self):
        self.framework = "junit"
        self.language = "java"
        # Java extractor not implemented yet
        self.extractor = None
    
    def discover_tests(self, project_path: str) -> List[str]:
        """Discover JUnit test files."""
        project = Path(project_path)
        
        # JUnit patterns: *Test.java or Test*.java
        test_files = []
        test_files.extend(project.rglob("*Test.java"))
        test_files.extend(project.rglob("Test*.java"))
        
        return [str(f) for f in test_files]
    
    def extract_metadata(self, test_file: str, test_name: str) -> TestMetadata:
        """Extract JUnit test metadata."""
        # Simplified - in production, parse Java annotations
        return TestMetadata(
            test_type=TestType.POSITIVE,
            priority=Priority.P2,
            feature="unknown",
            tags=[],
            flakiness_score=0.0,
        )
    
    def extract_ast_signals(self, test_file: str, test_name: str) -> StructuralSignals:
        """Extract AST signals from JUnit test."""
        # TODO: Implement Java AST extraction
        return StructuralSignals()
    
    def normalize_to_core_model(
        self,
        test_file: str,
        test_name: str,
        semantic_signals: Optional[SemanticSignals] = None,
    ) -> UnifiedTestMemory:
        """Normalize JUnit test to UnifiedTestMemory."""
        
        test_id = f"junit::{test_file}::{test_name}"
        metadata = self.extract_metadata(test_file, test_name)
        structural = self.extract_ast_signals(test_file, test_name)
        semantic = semantic_signals or SemanticSignals()
        
        return UnifiedTestMemory(
            test_id=test_id,
            framework=self.framework,
            language=self.language,
            file_path=test_file,
            test_name=test_name,
            semantic=semantic,
            structural=structural,
            metadata=metadata,
        )
    
    def get_framework_name(self) -> str:
        return self.framework
    
    def get_language(self) -> str:
        return self.language


class RobotFrameworkAdapter(FrameworkAdapter):
    """Adapter for Robot Framework."""
    
    def __init__(self):
        self.framework = "robot"
        self.language = "robot"
        self.extractor = None  # Robot has its own parsing
    
    def discover_tests(self, project_path: str) -> List[str]:
        """Discover Robot Framework test files."""
        project = Path(project_path)
        
        # Robot patterns: *.robot
        test_files = list(project.rglob("*.robot"))
        
        return [str(f) for f in test_files]
    
    def extract_metadata(self, test_file: str, test_name: str) -> TestMetadata:
        """Extract Robot test metadata."""
        # Simplified - in production, parse Robot tags
        return TestMetadata(
            test_type=TestType.POSITIVE,
            priority=Priority.P2,
            feature="unknown",
            tags=[],
            flakiness_score=0.0,
        )
    
    def extract_ast_signals(self, test_file: str, test_name: str) -> StructuralSignals:
        """Extract signals from Robot test."""
        # TODO: Implement Robot parsing
        return StructuralSignals()
    
    def normalize_to_core_model(
        self,
        test_file: str,
        test_name: str,
        semantic_signals: Optional[SemanticSignals] = None,
    ) -> UnifiedTestMemory:
        """Normalize Robot test to UnifiedTestMemory."""
        
        test_id = f"robot::{test_file}::{test_name}"
        metadata = self.extract_metadata(test_file, test_name)
        structural = self.extract_ast_signals(test_file, test_name)
        semantic = semantic_signals or SemanticSignals()
        
        return UnifiedTestMemory(
            test_id=test_id,
            framework=self.framework,
            language=self.language,
            file_path=test_file,
            test_name=test_name,
            semantic=semantic,
            structural=structural,
            metadata=metadata,
        )
    
    def get_framework_name(self) -> str:
        return self.framework
    
    def get_language(self) -> str:
        return self.language


class NUnitAdapter(FrameworkAdapter):
    """Adapter for NUnit framework (C# .NET)."""
    
    def __init__(self):
        self.framework = "nunit"
        self.language = "csharp"
        # C# extractor not implemented yet
        self.extractor = None
    
    def discover_tests(self, project_path: str) -> List[str]:
        """Discover NUnit test files."""
        project = Path(project_path)
        
        # NUnit patterns: *Test.cs, *Tests.cs
        test_files = []
        test_files.extend(project.rglob("*Test.cs"))
        test_files.extend(project.rglob("*Tests.cs"))
        
        return [str(f) for f in test_files]
    
    def extract_metadata(self, test_file: str, test_name: str) -> TestMetadata:
        """Extract NUnit test metadata."""
        # Read test file
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            test_type = self._infer_test_type(content, test_name)
            priority = self._extract_priority(content, test_name)
            tags = self._extract_nunit_categories(content, test_name)
            feature = self._extract_feature_from_path(test_file)
            
            return TestMetadata(
                test_type=test_type,
                priority=priority,
                feature=feature,
                tags=tags,
                flakiness_score=0.0,
            )
        except Exception:
            return TestMetadata()
    
    def extract_ast_signals(self, test_file: str, test_name: str) -> StructuralSignals:
        """Extract AST signals from NUnit test."""
        # TODO: Implement C# AST extraction using Roslyn or similar
        return StructuralSignals()
    
    def normalize_to_core_model(
        self,
        test_file: str,
        test_name: str,
        semantic_signals: Optional[SemanticSignals] = None,
    ) -> UnifiedTestMemory:
        """Normalize NUnit test to UnifiedTestMemory."""
        
        test_id = f"nunit::{test_file}::{test_name}"
        metadata = self.extract_metadata(test_file, test_name)
        structural = self.extract_ast_signals(test_file, test_name)
        semantic = semantic_signals or SemanticSignals()
        
        return UnifiedTestMemory(
            test_id=test_id,
            framework=self.framework,
            language=self.language,
            file_path=test_file,
            test_name=test_name,
            semantic=semantic,
            structural=structural,
            metadata=metadata,
        )
    
    def get_framework_name(self) -> str:
        return self.framework
    
    def get_language(self) -> str:
        return self.language
    
    def _infer_test_type(self, content: str, test_name: str) -> TestType:
        """Infer test type from name and content."""
        name_lower = test_name.lower()
        
        if any(keyword in name_lower for keyword in ["negative", "invalid", "error", "fail", "exception"]):
            return TestType.NEGATIVE
        elif any(keyword in name_lower for keyword in ["boundary", "edge", "limit"]):
            return TestType.BOUNDARY
        elif "integration" in name_lower:
            return TestType.INTEGRATION
        elif "unit" in name_lower:
            return TestType.UNIT
        elif any(keyword in name_lower for keyword in ["e2e", "endtoend"]):
            return TestType.E2E
        else:
            return TestType.POSITIVE
    
    def _extract_priority(self, content: str, test_name: str) -> Priority:
        """Extract priority from NUnit attributes."""
        # Look for [Priority] or [Category] attributes
        if "[Priority(0)]" in content or "[Category(\"Critical\")]" in content:
            return Priority.P0
        elif "[Priority(1)]" in content or "[Category(\"High\")]" in content:
            return Priority.P1
        elif "[Priority(3)]" in content or "[Category(\"Low\")]" in content:
            return Priority.P3
        else:
            return Priority.P2
    
    def _extract_nunit_categories(self, content: str, test_name: str) -> List[str]:
        """Extract NUnit categories as tags."""
        tags = []
        
        # Common NUnit categories
        categories = ["Smoke", "Regression", "Integration", "Unit", "E2E"]
        
        for category in categories:
            if f'[Category("{category}")]' in content:
                tags.append(category.lower())
        
        return tags
    
    def _extract_feature_from_path(self, test_file: str) -> str:
        """Extract feature name from file path."""
        path = Path(test_file)
        # Get parent directory name as feature
        if path.parent.name.lower() in ["tests", "test"]:
            return "general"
        return path.parent.name


class TestNGAdapter(FrameworkAdapter):
    """Adapter for TestNG framework (Java)."""
    
    def __init__(self):
        self.framework = "testng"
        self.language = "java"
        # Java extractor not implemented yet
        self.extractor = None
    
    def discover_tests(self, project_path: str) -> List[str]:
        """Discover TestNG test files."""
        project = Path(project_path)
        
        # TestNG patterns: *Test.java, *Tests.java
        test_files = []
        test_files.extend(project.rglob("*Test.java"))
        test_files.extend(project.rglob("*Tests.java"))
        
        return [str(f) for f in test_files]
    
    def extract_metadata(self, test_file: str, test_name: str) -> TestMetadata:
        """Extract TestNG test metadata."""
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            test_type = self._infer_test_type(content, test_name)
            priority = self._extract_priority(content, test_name)
            tags = self._extract_testng_groups(content, test_name)
            feature = self._extract_feature_from_path(test_file)
            
            return TestMetadata(
                test_type=test_type,
                priority=priority,
                feature=feature,
                tags=tags,
                flakiness_score=0.0,
            )
        except Exception:
            return TestMetadata()
    
    def extract_ast_signals(self, test_file: str, test_name: str) -> StructuralSignals:
        """Extract AST signals from TestNG test."""
        # TODO: Implement Java AST extraction
        return StructuralSignals()
    
    def normalize_to_core_model(
        self,
        test_file: str,
        test_name: str,
        semantic_signals: Optional[SemanticSignals] = None,
    ) -> UnifiedTestMemory:
        """Normalize TestNG test to UnifiedTestMemory."""
        
        test_id = f"testng::{test_file}::{test_name}"
        metadata = self.extract_metadata(test_file, test_name)
        structural = self.extract_ast_signals(test_file, test_name)
        semantic = semantic_signals or SemanticSignals()
        
        return UnifiedTestMemory(
            test_id=test_id,
            framework=self.framework,
            language=self.language,
            file_path=test_file,
            test_name=test_name,
            semantic=semantic,
            structural=structural,
            metadata=metadata,
        )
    
    def get_framework_name(self) -> str:
        return self.framework
    
    def get_language(self) -> str:
        return self.language
    
    def _infer_test_type(self, content: str, test_name: str) -> TestType:
        """Infer test type from name and content."""
        name_lower = test_name.lower()
        
        if any(keyword in name_lower for keyword in ["negative", "invalid", "error", "exception"]):
            return TestType.NEGATIVE
        elif any(keyword in name_lower for keyword in ["boundary", "edge"]):
            return TestType.BOUNDARY
        elif "integration" in name_lower:
            return TestType.INTEGRATION
        elif "unit" in name_lower:
            return TestType.UNIT
        else:
            return TestType.POSITIVE
    
    def _extract_priority(self, content: str, test_name: str) -> Priority:
        """Extract priority from TestNG annotations."""
        # Look for @Test(priority=) annotation
        if "priority = 0" in content or "priority=0" in content:
            return Priority.P0
        elif "priority = 1" in content or "priority=1" in content:
            return Priority.P1
        elif "priority = 3" in content or "priority=3" in content:
            return Priority.P3
        else:
            return Priority.P2
    
    def _extract_testng_groups(self, content: str, test_name: str) -> List[str]:
        """Extract TestNG groups as tags."""
        tags = []
        
        # Common TestNG groups
        groups = ["smoke", "regression", "integration", "unit", "sanity"]
        
        for group in groups:
            if f'groups = "{group}"' in content.lower() or f"groups = '{group}'" in content.lower():
                tags.append(group)
        
        return tags
    
    def _extract_feature_from_path(self, test_file: str) -> str:
        """Extract feature name from file path."""
        path = Path(test_file)
        if path.parent.name.lower() in ["tests", "test"]:
            return "general"
        return path.parent.name


class SpecFlowAdapter(FrameworkAdapter):
    """Adapter for SpecFlow framework (C# BDD)."""
    
    def __init__(self):
        self.framework = "specflow"
        self.language = "csharp"
        self.extractor = None
    
    def discover_tests(self, project_path: str) -> List[str]:
        """Discover SpecFlow feature files."""
        project = Path(project_path)
        
        # SpecFlow uses .feature files
        test_files = list(project.rglob("*.feature"))
        
        return [str(f) for f in test_files]
    
    def extract_metadata(self, test_file: str, test_name: str) -> TestMetadata:
        """Extract SpecFlow test metadata."""
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            test_type = self._infer_test_type(content, test_name)
            priority = self._extract_priority(content, test_name)
            tags = self._extract_specflow_tags(content, test_name)
            feature = self._extract_feature_from_content(content)
            
            return TestMetadata(
                test_type=test_type,
                priority=priority,
                feature=feature,
                tags=tags,
                flakiness_score=0.0,
            )
        except Exception:
            return TestMetadata()
    
    def extract_ast_signals(self, test_file: str, test_name: str) -> StructuralSignals:
        """Extract signals from SpecFlow test."""
        # SpecFlow uses Gherkin syntax, parse steps
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            return self._parse_gherkin_steps(content, test_name)
        except Exception:
            return StructuralSignals()
    
    def normalize_to_core_model(
        self,
        test_file: str,
        test_name: str,
        semantic_signals: Optional[SemanticSignals] = None,
    ) -> UnifiedTestMemory:
        """Normalize SpecFlow test to UnifiedTestMemory."""
        
        test_id = f"specflow::{test_file}::{test_name}"
        metadata = self.extract_metadata(test_file, test_name)
        structural = self.extract_ast_signals(test_file, test_name)
        semantic = semantic_signals or SemanticSignals()
        
        return UnifiedTestMemory(
            test_id=test_id,
            framework=self.framework,
            language=self.language,
            file_path=test_file,
            test_name=test_name,
            semantic=semantic,
            structural=structural,
            metadata=metadata,
        )
    
    def get_framework_name(self) -> str:
        return self.framework
    
    def get_language(self) -> str:
        return self.language
    
    def _infer_test_type(self, content: str, test_name: str) -> TestType:
        """Infer test type from scenario name and content."""
        name_lower = test_name.lower()
        content_lower = content.lower()
        
        if any(keyword in name_lower for keyword in ["negative", "invalid", "error", "fail"]):
            return TestType.NEGATIVE
        elif any(keyword in name_lower for keyword in ["boundary", "edge"]):
            return TestType.BOUNDARY
        elif "integration" in name_lower or "integration" in content_lower:
            return TestType.INTEGRATION
        elif "e2e" in name_lower or "end to end" in name_lower:
            return TestType.E2E
        else:
            return TestType.POSITIVE
    
    def _extract_priority(self, content: str, test_name: str) -> Priority:
        """Extract priority from SpecFlow tags."""
        # Look for @priority tags
        if "@critical" in content.lower() or "@p0" in content.lower():
            return Priority.P0
        elif "@high" in content.lower() or "@p1" in content.lower():
            return Priority.P1
        elif "@low" in content.lower() or "@p3" in content.lower():
            return Priority.P3
        else:
            return Priority.P2
    
    def _extract_specflow_tags(self, content: str, test_name: str) -> List[str]:
        """Extract SpecFlow tags."""
        tags = []
        
        # Extract tags from content (lines starting with @)
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("@"):
                # Split by spaces and remove @ from each tag
                tag_tokens = line.split()
                for token in tag_tokens:
                    clean_tag = token.strip().lstrip("@")
                    if clean_tag:
                        tags.append(clean_tag)
        
        return tags
    
    def _extract_feature_from_content(self, content: str) -> str:
        """Extract feature name from Gherkin content."""
        # Look for Feature: line
        for line in content.split("\n"):
            if line.strip().startswith("Feature:"):
                feature_name = line.strip()[8:].strip()  # Remove "Feature:"
                return feature_name
        return "unknown"
    
    def _parse_gherkin_steps(self, content: str, scenario_name: str) -> StructuralSignals:
        """Parse Gherkin steps to extract structural signals."""
        signals = StructuralSignals()
        
        # Find the scenario
        in_scenario = False
        for line in content.split("\n"):
            line = line.strip()
            
            if scenario_name in line and ("Scenario:" in line or "Scenario Outline:" in line):
                in_scenario = True
                continue
            
            if in_scenario:
                # Stop at next scenario or feature end
                if line.startswith("Scenario") or line.startswith("Feature:"):
                    break
                
                # Parse steps
                if line.startswith(("Given", "When", "Then", "And", "But")):
                    # Check for API-like steps
                    if any(method in line for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]):
                        # Extract method and endpoint
                        for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                            if method in line:
                                signals.api_calls.append(
                                    APICall(method=method, endpoint="/api/endpoint")
                                )
                    
                    # Check for assertion-like steps
                    if any(word in line.lower() for word in ["should", "verify", "assert", "expect"]):
                        signals.assertions.append(
                            Assertion(type="gherkin_then", target=line)
                        )
        
        return signals


class AdapterFactory:
    """Factory for creating framework adapters."""
    
    _adapters = {
        "pytest": PytestAdapter,
        "junit": JUnitAdapter,
        "testng": TestNGAdapter,
        "nunit": NUnitAdapter,
        "specflow": SpecFlowAdapter,
        "robot": RobotFrameworkAdapter,
    }
    
    @classmethod
    def get_adapter(cls, framework: str) -> Optional[FrameworkAdapter]:
        """Get adapter for framework."""
        adapter_class = cls._adapters.get(framework.lower())
        if adapter_class:
            return adapter_class()
        return None
    
    @classmethod
    def register_adapter(cls, framework: str, adapter_class: type):
        """Register a new adapter."""
        cls._adapters[framework.lower()] = adapter_class
    
    @classmethod
    def list_supported_frameworks(cls) -> List[str]:
        """List all supported frameworks."""
        return list(cls._adapters.keys())


def normalize_test(
    test_file: str,
    test_name: str,
    framework: str,
    semantic_signals: Optional[SemanticSignals] = None,
) -> Optional[UnifiedTestMemory]:
    """
    Convenience function to normalize a test to UnifiedTestMemory.
    
    Args:
        test_file: Path to test file
        test_name: Name of test function/method
        framework: Framework name (pytest, junit, robot, etc.)
        semantic_signals: Optional pre-computed semantic signals
        
    Returns:
        UnifiedTestMemory object or None if framework not supported
    """
    adapter = AdapterFactory.get_adapter(framework)
    if not adapter:
        logger.error(f"No adapter available for framework: {framework}")
        return None
    
    return adapter.normalize_to_core_model(test_file, test_name, semantic_signals)


# ============================================================================
# RestAssured Adapter (Java REST API Testing)
# ============================================================================

class RestAssuredAdapter(FrameworkAdapter):
    """Adapter for RestAssured Java REST API testing framework."""
    
    def __init__(self):
        self.framework = "restassured"
        self.language = "java"
    
    def discover_tests(self, project_path: str) -> List[str]:
        """Discover RestAssured test files."""
        test_files = []
        project = Path(project_path)
        
        # RestAssured tests typically follow JUnit/TestNG patterns
        for pattern in ["*Test.java", "*Tests.java", "*IT.java"]:
            test_files.extend([str(f) for f in project.rglob(pattern)])
        
        return test_files
    
    def extract_metadata(self, test_file: str, test_name: str) -> TestMetadata:
        """Extract metadata from RestAssured test."""
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        test_type = self._infer_test_type(content, test_name)
        priority = self._extract_priority(content, test_name)
        tags = self._extract_restassured_tags(content, test_name)
        
        return TestMetadata(
            test_type=test_type,
            priority=priority,
            feature="api_testing",
            tags=tags,
        )
    
    def extract_ast_signals(self, test_file: str, test_name: str) -> StructuralSignals:
        """Extract structural signals (TODO: Java AST)."""
        # TODO: Implement Java AST extraction
        return StructuralSignals()
    
    def normalize_to_core_model(
        self,
        test_file: str,
        test_name: str,
        semantic_signals: Optional[SemanticSignals] = None,
    ) -> UnifiedTestMemory:
        """Normalize RestAssured test to UnifiedTestMemory."""
        test_id = f"{self.framework}::{test_file}::{test_name}"
        
        semantic = semantic_signals or SemanticSignals()
        structural = self.extract_ast_signals(test_file, test_name)
        metadata = self.extract_metadata(test_file, test_name)
        
        return UnifiedTestMemory(
            test_id=test_id,
            framework=self.framework,
            language=self.language,
            file_path=test_file,
            test_name=test_name,
            semantic=semantic,
            structural=structural,
            metadata=metadata,
        )
    
    def get_framework_name(self) -> str:
        return self.framework
    
    def get_language(self) -> str:
        return self.language
    
    def _infer_test_type(self, content: str, test_name: str) -> TestType:
        """Infer test type from method name."""
        name_lower = test_name.lower()
        
        if any(keyword in name_lower for keyword in ["negative", "invalid", "error", "fail", "unauthorized"]):
            return TestType.NEGATIVE
        elif any(keyword in name_lower for keyword in ["boundary", "edge"]):
            return TestType.BOUNDARY
        elif any(keyword in name_lower for keyword in ["integration", "e2e", "endtoend"]):
            return TestType.INTEGRATION
        
        return TestType.POSITIVE
    
    def _extract_priority(self, content: str, test_name: str) -> Priority:
        """Extract priority from annotations."""
        # Check for @Test(priority=n)
        if f"public void {test_name}" in content or f"public void test{test_name}" in content:
            method_section = content[max(0, content.find(test_name) - 200):content.find(test_name) + 50]
            
            if "@Test(priority = 0)" in method_section or "@Test(priority=0)" in method_section:
                return Priority.P0
            elif "@Test(priority = 1)" in method_section or "@Test(priority=1)" in method_section:
                return Priority.P1
            elif "@Test(priority = 3)" in method_section or "@Test(priority=3)" in method_section:
                return Priority.P3
        
        return Priority.P2
    
    def _extract_restassured_tags(self, content: str, test_name: str) -> List[str]:
        """Extract tags from annotations."""
        tags = []
        
        if f"public void {test_name}" in content:
            method_section = content[max(0, content.find(test_name) - 300):content.find(test_name) + 50]
            
            # Extract from @Tag or @Category
            for tag in ["smoke", "regression", "api", "integration"]:
                if f'"{tag}"' in method_section.lower() or f"'{tag}'" in method_section.lower():
                    tags.append(tag)
        
        return tags


# ============================================================================
# Playwright Adapter (JavaScript/TypeScript E2E Testing)
# ============================================================================

class PlaywrightAdapter(FrameworkAdapter):
    """Adapter for Playwright E2E testing framework."""
    
    def __init__(self):
        self.framework = "playwright"
        self.language = "javascript"
    
    def discover_tests(self, project_path: str) -> List[str]:
        """Discover Playwright test files."""
        test_files = []
        project = Path(project_path)
        
        # Playwright test patterns
        for pattern in ["*.spec.js", "*.spec.ts", "*.test.js", "*.test.ts", "*e2e*.js", "*e2e*.ts"]:
            test_files.extend([str(f) for f in project.rglob(pattern)])
        
        return test_files
    
    def extract_metadata(self, test_file: str, test_name: str) -> TestMetadata:
        """Extract metadata from Playwright test."""
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        test_type = self._infer_test_type(content, test_name)
        priority = self._extract_priority(content, test_name)
        tags = self._extract_playwright_tags(content, test_name)
        
        return TestMetadata(
            test_type=test_type,
            priority=priority,
            feature="e2e_testing",
            tags=tags,
        )
    
    def extract_ast_signals(self, test_file: str, test_name: str) -> StructuralSignals:
        """Extract structural signals (TODO: JavaScript AST)."""
        # TODO: Implement JavaScript AST extraction
        return StructuralSignals()
    
    def normalize_to_core_model(
        self,
        test_file: str,
        test_name: str,
        semantic_signals: Optional[SemanticSignals] = None,
    ) -> UnifiedTestMemory:
        """Normalize Playwright test to UnifiedTestMemory."""
        test_id = f"{self.framework}::{test_file}::{test_name}"
        
        semantic = semantic_signals or SemanticSignals()
        structural = self.extract_ast_signals(test_file, test_name)
        metadata = self.extract_metadata(test_file, test_name)
        
        return UnifiedTestMemory(
            test_id=test_id,
            framework=self.framework,
            language=self.language,
            file_path=test_file,
            test_name=test_name,
            semantic=semantic,
            structural=structural,
            metadata=metadata,
        )
    
    def get_framework_name(self) -> str:
        return self.framework
    
    def get_language(self) -> str:
        return self.language
    
    def _infer_test_type(self, content: str, test_name: str) -> TestType:
        """Infer test type from test name."""
        name_lower = test_name.lower()
        
        if any(keyword in name_lower for keyword in ["negative", "invalid", "error", "fail"]):
            return TestType.NEGATIVE
        elif any(keyword in name_lower for keyword in ["e2e", "end to end", "full flow"]):
            return TestType.E2E
        elif any(keyword in name_lower for keyword in ["integration"]):
            return TestType.INTEGRATION
        
        return TestType.POSITIVE
    
    def _extract_priority(self, content: str, test_name: str) -> Priority:
        """Extract priority from test tags."""
        test_section = self._get_test_section(content, test_name)
        
        if "@critical" in test_section or "@p0" in test_section:
            return Priority.P0
        elif "@high" in test_section or "@p1" in test_section:
            return Priority.P1
        elif "@low" in test_section or "@p3" in test_section:
            return Priority.P3
        
        return Priority.P2
    
    def _extract_playwright_tags(self, content: str, test_name: str) -> List[str]:
        """Extract tags from test annotations."""
        tags = []
        test_section = self._get_test_section(content, test_name)
        
        # Check for @tag annotations
        for tag in ["smoke", "regression", "e2e", "ui", "critical"]:
            if f"@{tag}" in test_section.lower():
                tags.append(tag)
        
        return tags
    
    def _get_test_section(self, content: str, test_name: str) -> str:
        """Get the section of content around the test."""
        if test_name in content:
            start = max(0, content.find(test_name) - 200)
            end = content.find(test_name) + 200
            return content[start:end].lower()
        return ""


# ============================================================================
# Selenium Python Adapter
# ============================================================================

class SeleniumPythonAdapter(FrameworkAdapter):
    """Adapter for Selenium Python testing."""
    
    def __init__(self):
        self.framework = "selenium_python"
        self.language = "python"
    
    def discover_tests(self, project_path: str) -> List[str]:
        """Discover Selenium Python test files."""
        test_files = []
        project = Path(project_path)
        
        # Selenium tests with pytest or unittest
        for pattern in ["test_*.py", "*_test.py", "test*.py"]:
            test_files.extend([str(f) for f in project.rglob(pattern)])
        
        return test_files
    
    def extract_metadata(self, test_file: str, test_name: str) -> TestMetadata:
        """Extract metadata from Selenium Python test."""
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        test_type = self._infer_test_type(content, test_name)
        priority = self._extract_priority(content, test_name)
        tags = self._extract_selenium_tags(content, test_name)
        
        return TestMetadata(
            test_type=test_type,
            priority=priority,
            feature="ui_testing",
            tags=tags,
        )
    
    def extract_ast_signals(self, test_file: str, test_name: str) -> StructuralSignals:
        """Extract structural signals using Python AST."""
        try:
            extractor = ASTExtractorFactory.get_extractor(self.language)
            with open(test_file, 'r', encoding='utf-8') as f:
                code = f.read()
            return extractor.extract(code, test_name)
        except Exception as e:
            logger.error(f"AST extraction failed for {test_file}: {e}")
            return StructuralSignals()
    
    def normalize_to_core_model(
        self,
        test_file: str,
        test_name: str,
        semantic_signals: Optional[SemanticSignals] = None,
    ) -> UnifiedTestMemory:
        """Normalize Selenium Python test to UnifiedTestMemory."""
        test_id = f"{self.framework}::{test_file}::{test_name}"
        
        semantic = semantic_signals or SemanticSignals()
        structural = self.extract_ast_signals(test_file, test_name)
        metadata = self.extract_metadata(test_file, test_name)
        
        return UnifiedTestMemory(
            test_id=test_id,
            framework=self.framework,
            language=self.language,
            file_path=test_file,
            test_name=test_name,
            semantic=semantic,
            structural=structural,
            metadata=metadata,
        )
    
    def get_framework_name(self) -> str:
        return self.framework
    
    def get_language(self) -> str:
        return self.language
    
    def _infer_test_type(self, content: str, test_name: str) -> TestType:
        """Infer test type from test name."""
        name_lower = test_name.lower()
        
        if any(keyword in name_lower for keyword in ["negative", "invalid", "error"]):
            return TestType.NEGATIVE
        elif any(keyword in name_lower for keyword in ["e2e", "endtoend", "full"]):
            return TestType.E2E
        elif any(keyword in name_lower for keyword in ["integration"]):
            return TestType.INTEGRATION
        
        return TestType.POSITIVE
    
    def _extract_priority(self, content: str, test_name: str) -> Priority:
        """Extract priority from pytest markers."""
        test_section = content[max(0, content.find(test_name) - 300):content.find(test_name) + 50] if test_name in content else ""
        
        if "@pytest.mark.p0" in test_section or "@pytest.mark.critical" in test_section:
            return Priority.P0
        elif "@pytest.mark.p1" in test_section or "@pytest.mark.high" in test_section:
            return Priority.P1
        elif "@pytest.mark.p3" in test_section or "@pytest.mark.low" in test_section:
            return Priority.P3
        
        return Priority.P2
    
    def _extract_selenium_tags(self, content: str, test_name: str) -> List[str]:
        """Extract tags from pytest markers."""
        tags = []
        test_section = content[max(0, content.find(test_name) - 300):content.find(test_name) + 50] if test_name in content else ""
        
        for tag in ["smoke", "regression", "ui", "e2e", "selenium"]:
            if f"@pytest.mark.{tag}" in test_section:
                tags.append(tag)
        
        return tags


# ============================================================================
# Selenium Java Adapter
# ============================================================================

class SeleniumJavaAdapter(FrameworkAdapter):
    """Adapter for Selenium Java testing."""
    
    def __init__(self):
        self.framework = "selenium_java"
        self.language = "java"
    
    def discover_tests(self, project_path: str) -> List[str]:
        """Discover Selenium Java test files."""
        test_files = []
        project = Path(project_path)
        
        for pattern in ["*Test.java", "*Tests.java", "*IT.java"]:
            test_files.extend([str(f) for f in project.rglob(pattern)])
        
        return test_files
    
    def extract_metadata(self, test_file: str, test_name: str) -> TestMetadata:
        """Extract metadata from Selenium Java test."""
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        test_type = self._infer_test_type(content, test_name)
        priority = self._extract_priority(content, test_name)
        tags = self._extract_selenium_tags(content, test_name)
        
        return TestMetadata(
            test_type=test_type,
            priority=priority,
            feature="ui_testing",
            tags=tags,
        )
    
    def extract_ast_signals(self, test_file: str, test_name: str) -> StructuralSignals:
        """Extract structural signals (TODO: Java AST)."""
        # TODO: Implement Java AST extraction
        return StructuralSignals()
    
    def normalize_to_core_model(
        self,
        test_file: str,
        test_name: str,
        semantic_signals: Optional[SemanticSignals] = None,
    ) -> UnifiedTestMemory:
        """Normalize Selenium Java test to UnifiedTestMemory."""
        test_id = f"{self.framework}::{test_file}::{test_name}"
        
        semantic = semantic_signals or SemanticSignals()
        structural = self.extract_ast_signals(test_file, test_name)
        metadata = self.extract_metadata(test_file, test_name)
        
        return UnifiedTestMemory(
            test_id=test_id,
            framework=self.framework,
            language=self.language,
            file_path=test_file,
            test_name=test_name,
            semantic=semantic,
            structural=structural,
            metadata=metadata,
        )
    
    def get_framework_name(self) -> str:
        return self.framework
    
    def get_language(self) -> str:
        return self.language
    
    def _infer_test_type(self, content: str, test_name: str) -> TestType:
        """Infer test type from method name."""
        name_lower = test_name.lower()
        
        if any(keyword in name_lower for keyword in ["negative", "invalid", "error"]):
            return TestType.NEGATIVE
        elif any(keyword in name_lower for keyword in ["e2e", "endtoend", "full"]):
            return TestType.E2E
        elif any(keyword in name_lower for keyword in ["integration"]):
            return TestType.INTEGRATION
        
        return TestType.POSITIVE
    
    def _extract_priority(self, content: str, test_name: str) -> Priority:
        """Extract priority from annotations."""
        test_section = content[max(0, content.find(test_name) - 200):content.find(test_name) + 50] if test_name in content else ""
        
        if "@Test(priority = 0)" in test_section or "@Test(priority=0)" in test_section:
            return Priority.P0
        elif "@Test(priority = 1)" in test_section or "@Test(priority=1)" in test_section:
            return Priority.P1
        elif "@Test(priority = 3)" in test_section or "@Test(priority=3)" in test_section:
            return Priority.P3
        
        return Priority.P2
    
    def _extract_selenium_tags(self, content: str, test_name: str) -> List[str]:
        """Extract tags from annotations."""
        tags = []
        test_section = content[max(0, content.find(test_name) - 300):content.find(test_name) + 50] if test_name in content else ""
        
        for tag in ["smoke", "regression", "ui", "e2e", "selenium"]:
            if f'"{tag}"' in test_section.lower():
                tags.append(tag)
        
        return tags


# ============================================================================
# Cucumber Adapter (BDD for Java/JavaScript)
# ============================================================================

class CucumberAdapter(FrameworkAdapter):
    """Adapter for Cucumber BDD testing framework."""
    
    def __init__(self):
        self.framework = "cucumber"
        self.language = "gherkin"
    
    def discover_tests(self, project_path: str) -> List[str]:
        """Discover Cucumber feature files."""
        test_files = []
        project = Path(project_path)
        
        test_files.extend([str(f) for f in project.rglob("*.feature")])
        
        return test_files
    
    def extract_metadata(self, test_file: str, test_name: str) -> TestMetadata:
        """Extract metadata from Cucumber feature."""
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        test_type = self._infer_test_type(content, test_name)
        priority = self._extract_priority(content, test_name)
        tags = self._extract_cucumber_tags(content, test_name)
        feature = self._extract_feature_from_content(content)
        
        return TestMetadata(
            test_type=test_type,
            priority=priority,
            feature=feature or "bdd_testing",
            tags=tags,
        )
    
    def extract_ast_signals(self, test_file: str, test_name: str) -> StructuralSignals:
        """Extract structural signals from Gherkin."""
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self._parse_gherkin_steps(content, test_name)
    
    def normalize_to_core_model(
        self,
        test_file: str,
        test_name: str,
        semantic_signals: Optional[SemanticSignals] = None,
    ) -> UnifiedTestMemory:
        """Normalize Cucumber scenario to UnifiedTestMemory."""
        test_id = f"{self.framework}::{test_file}::{test_name}"
        
        semantic = semantic_signals or SemanticSignals()
        structural = self.extract_ast_signals(test_file, test_name)
        metadata = self.extract_metadata(test_file, test_name)
        
        return UnifiedTestMemory(
            test_id=test_id,
            framework=self.framework,
            language=self.language,
            file_path=test_file,
            test_name=test_name,
            semantic=semantic,
            structural=structural,
            metadata=metadata,
        )
    
    def get_framework_name(self) -> str:
        return self.framework
    
    def get_language(self) -> str:
        return self.language
    
    def _infer_test_type(self, content: str, test_name: str) -> TestType:
        """Infer test type from scenario name."""
        name_lower = test_name.lower()
        
        if any(keyword in name_lower for keyword in ["negative", "invalid", "error", "fail"]):
            return TestType.NEGATIVE
        elif any(keyword in name_lower for keyword in ["e2e", "end to end"]):
            return TestType.E2E
        elif any(keyword in name_lower for keyword in ["integration"]):
            return TestType.INTEGRATION
        
        return TestType.POSITIVE
    
    def _extract_priority(self, content: str, test_name: str) -> Priority:
        """Extract priority from tags."""
        scenario_section = self._get_scenario_section(content, test_name)
        
        if any(tag in scenario_section.lower() for tag in ["@critical", "@p0"]):
            return Priority.P0
        elif any(tag in scenario_section.lower() for tag in ["@high", "@p1"]):
            return Priority.P1
        elif any(tag in scenario_section.lower() for tag in ["@low", "@p3"]):
            return Priority.P3
        
        return Priority.P2
    
    def _extract_cucumber_tags(self, content: str, test_name: str) -> List[str]:
        """Extract tags from Gherkin."""
        tags = []
        scenario_section = self._get_scenario_section(content, test_name)
        
        for line in scenario_section.split("\n"):
            line = line.strip()
            if line.startswith("@"):
                tag_tokens = line.split()
                for token in tag_tokens:
                    clean_tag = token.strip().lstrip("@")
                    if clean_tag:
                        tags.append(clean_tag)
        
        return tags
    
    def _extract_feature_from_content(self, content: str) -> str:
        """Extract feature name from Gherkin."""
        for line in content.split("\n"):
            if line.strip().startswith("Feature:"):
                return line.strip()[8:].strip()
        return ""
    
    def _parse_gherkin_steps(self, content: str, scenario_name: str) -> StructuralSignals:
        """Parse Gherkin steps and extract structural signals."""
        api_calls = []
        assertions = []
        
        scenario_section = self._get_scenario_section(content, scenario_name)
        
        for line in scenario_section.split("\n"):
            line_stripped = line.strip()
            
            # Detect API calls
            for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                if method in line_stripped.upper():
                    api_calls.append(APICall(method=method, endpoint=""))
            
            # Detect assertions in Then steps
            if line_stripped.startswith("Then") or line_stripped.startswith("And"):
                if any(keyword in line_stripped.lower() for keyword in ["should", "verify", "assert", "expect", "must"]):
                    assertions.append(Assertion(type="gherkin_assertion", target="step", expected_value=line_stripped))
        
        return StructuralSignals(api_calls=api_calls, assertions=assertions)
    
    def _get_scenario_section(self, content: str, scenario_name: str) -> str:
        """Get the section of content for a specific scenario."""
        lines = content.split("\n")
        scenario_lines = []
        in_scenario = False
        
        for i, line in enumerate(lines):
            if f"Scenario: {scenario_name}" in line or f"Scenario Outline: {scenario_name}" in line:
                # Include tags before scenario
                for j in range(max(0, i-5), i):
                    if lines[j].strip().startswith("@"):
                        scenario_lines.append(lines[j])
                in_scenario = True
                scenario_lines.append(line)
            elif in_scenario:
                if line.strip().startswith("Scenario"):
                    break
                scenario_lines.append(line)
        
        return "\n".join(scenario_lines)


# ============================================================================
# Behave Adapter (BDD for Python)
# ============================================================================

class BehaveAdapter(FrameworkAdapter):
    """Adapter for Behave BDD testing framework (Python)."""
    
    def __init__(self):
        self.framework = "behave"
        self.language = "python"
    
    def discover_tests(self, project_path: str) -> List[str]:
        """Discover Behave feature files."""
        test_files = []
        project = Path(project_path)
        
        # Behave features are usually in features/ directory
        test_files.extend([str(f) for f in project.rglob("*.feature")])
        
        return test_files
    
    def extract_metadata(self, test_file: str, test_name: str) -> TestMetadata:
        """Extract metadata from Behave feature."""
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        test_type = self._infer_test_type(content, test_name)
        priority = self._extract_priority(content, test_name)
        tags = self._extract_behave_tags(content, test_name)
        feature = self._extract_feature_from_content(content)
        
        return TestMetadata(
            test_type=test_type,
            priority=priority,
            feature=feature or "bdd_testing",
            tags=tags,
        )
    
    def extract_ast_signals(self, test_file: str, test_name: str) -> StructuralSignals:
        """Extract structural signals from Gherkin."""
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self._parse_gherkin_steps(content, test_name)
    
    def normalize_to_core_model(
        self,
        test_file: str,
        test_name: str,
        semantic_signals: Optional[SemanticSignals] = None,
    ) -> UnifiedTestMemory:
        """Normalize Behave scenario to UnifiedTestMemory."""
        test_id = f"{self.framework}::{test_file}::{test_name}"
        
        semantic = semantic_signals or SemanticSignals()
        structural = self.extract_ast_signals(test_file, test_name)
        metadata = self.extract_metadata(test_file, test_name)
        
        return UnifiedTestMemory(
            test_id=test_id,
            framework=self.framework,
            language=self.language,
            file_path=test_file,
            test_name=test_name,
            semantic=semantic,
            structural=structural,
            metadata=metadata,
        )
    
    def get_framework_name(self) -> str:
        return self.framework
    
    def get_language(self) -> str:
        return self.language
    
    def _infer_test_type(self, content: str, test_name: str) -> TestType:
        """Infer test type from scenario name."""
        name_lower = test_name.lower()
        
        if any(keyword in name_lower for keyword in ["negative", "invalid", "error", "fail"]):
            return TestType.NEGATIVE
        elif any(keyword in name_lower for keyword in ["e2e", "end to end"]):
            return TestType.E2E
        elif any(keyword in name_lower for keyword in ["integration"]):
            return TestType.INTEGRATION
        
        return TestType.POSITIVE
    
    def _extract_priority(self, content: str, test_name: str) -> Priority:
        """Extract priority from tags."""
        scenario_section = self._get_scenario_section(content, test_name)
        
        if any(tag in scenario_section.lower() for tag in ["@critical", "@p0"]):
            return Priority.P0
        elif any(tag in scenario_section.lower() for tag in ["@high", "@p1"]):
            return Priority.P1
        elif any(tag in scenario_section.lower() for tag in ["@low", "@p3"]):
            return Priority.P3
        
        return Priority.P2
    
    def _extract_behave_tags(self, content: str, test_name: str) -> List[str]:
        """Extract tags from Gherkin."""
        tags = []
        scenario_section = self._get_scenario_section(content, test_name)
        
        for line in scenario_section.split("\n"):
            line = line.strip()
            if line.startswith("@"):
                tag_tokens = line.split()
                for token in tag_tokens:
                    clean_tag = token.strip().lstrip("@")
                    if clean_tag:
                        tags.append(clean_tag)
        
        return tags
    
    def _extract_feature_from_content(self, content: str) -> str:
        """Extract feature name from Gherkin."""
        for line in content.split("\n"):
            if line.strip().startswith("Feature:"):
                return line.strip()[8:].strip()
        return ""
    
    def _parse_gherkin_steps(self, content: str, scenario_name: str) -> StructuralSignals:
        """Parse Gherkin steps and extract structural signals."""
        api_calls = []
        assertions = []
        
        scenario_section = self._get_scenario_section(content, scenario_name)
        
        for line in scenario_section.split("\n"):
            line_stripped = line.strip()
            
            # Detect API calls
            for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                if method in line_stripped.upper():
                    api_calls.append(APICall(method=method, endpoint=""))
            
            # Detect assertions in Then steps
            if line_stripped.startswith("Then") or line_stripped.startswith("And"):
                if any(keyword in line_stripped.lower() for keyword in ["should", "verify", "assert", "expect", "must"]):
                    assertions.append(Assertion(type="gherkin_assertion", target="step", expected_value=line_stripped))
        
        return StructuralSignals(api_calls=api_calls, assertions=assertions)
    
    def _get_scenario_section(self, content: str, scenario_name: str) -> str:
        """Get the section of content for a specific scenario."""
        lines = content.split("\n")
        scenario_lines = []
        in_scenario = False
        
        for line in lines:
            if f"Scenario: {scenario_name}" in line or f"Scenario Outline: {scenario_name}" in line:
                in_scenario = True
                scenario_lines.append(line)
            elif in_scenario:
                if line.strip().startswith("Scenario") or line.strip().startswith("Feature"):
                    break
                scenario_lines.append(line)
        
        # Include tags before scenario
        if scenario_name in content:
            idx = content.find(f"Scenario: {scenario_name}")
            if idx == -1:
                idx = content.find(f"Scenario Outline: {scenario_name}")
            if idx > 0:
                # Get lines before scenario for tags
                before = content[:idx].split("\n")
                tags_lines = []
                for line in reversed(before):
                    if line.strip().startswith("@"):
                        tags_lines.insert(0, line)
                    elif line.strip() and not line.strip().startswith("#"):
                        break
                scenario_lines = tags_lines + scenario_lines
        
        return "\n".join(scenario_lines)


# ============================================================================
# Adapter Factory Updates
# ============================================================================

class AdapterFactory:
    """Factory for creating framework-specific adapters."""
    
    _adapters = {
        "pytest": PytestAdapter,
        "junit": JUnitAdapter,
        "testng": TestNGAdapter,
        "nunit": NUnitAdapter,
        "specflow": SpecFlowAdapter,
        "robot": RobotFrameworkAdapter,
        "restassured": RestAssuredAdapter,
        "playwright": PlaywrightAdapter,
        "selenium_python": SeleniumPythonAdapter,
        "selenium_java": SeleniumJavaAdapter,
        "cucumber": CucumberAdapter,
        "behave": BehaveAdapter,
    }
    
    @staticmethod
    def get_adapter(framework: str) -> Optional[FrameworkAdapter]:
        """Get adapter for specified framework (case-insensitive)."""
        framework_lower = framework.lower()
        adapter_class = AdapterFactory._adapters.get(framework_lower)
        
        if adapter_class:
            return adapter_class()
        
        logger.warning(f"No adapter available for framework: {framework}")
        return None
    
    @staticmethod
    def list_supported_frameworks() -> List[str]:
        """List all supported frameworks."""
        return list(AdapterFactory._adapters.keys())
    
    @staticmethod
    def register_adapter(framework: str, adapter_class: Type[FrameworkAdapter]):
        """Register a custom adapter."""
        AdapterFactory._adapters[framework.lower()] = adapter_class
        logger.info(f"Registered adapter for framework: {framework}")
