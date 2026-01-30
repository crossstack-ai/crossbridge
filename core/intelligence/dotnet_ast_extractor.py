# Copyright (c) 2025 Vikas Verma
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
.NET AST Extractor for CrossBridge Intelligence.

Extracts structural signals from C# test files for NUnit, SpecFlow, MSTest, xUnit.
Uses regex-based parsing (no external C# parser dependencies).
"""

import logging
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from core.intelligence.models import (
    StructuralSignals,
    APICall,
    Assertion,
)

logger = logging.getLogger(__name__)


@dataclass
class DotNetTestMethod:
    """Represents a .NET test method."""
    name: str
    attributes: List[str]  # [Test], [Fact], [Theory], etc.
    parameters: List[Dict[str, str]]  # Parameter name and type
    body: str
    line_number: int
    is_async: bool = False
    test_framework: str = "nunit"  # nunit, xunit, mstest, specflow


@dataclass
class DotNetTestClass:
    """Represents a .NET test class."""
    name: str
    namespace: str
    attributes: List[str]  # [TestFixture], [TestClass], etc.
    methods: List[DotNetTestMethod]
    setup_methods: List[str]
    teardown_methods: List[str]


class DotNetASTExtractor:
    """
    Extract AST-like structural signals from .NET C# test code.
    
    Supports:
    - NUnit ([Test], [TestFixture], Assert.That, Should)
    - xUnit ([Fact], [Theory], Assert.Equal)
    - MSTest ([TestMethod], [TestClass], Assert.AreEqual)
    - SpecFlow (Gherkin step bindings)
    """
    
    # Test framework attribute patterns
    TEST_FRAMEWORKS = {
        'nunit': {
            'test_attrs': ['Test', 'TestCase', 'TestCaseSource'],
            'class_attrs': ['TestFixture'],
            'setup_attrs': ['SetUp', 'OneTimeSetUp'],
            'teardown_attrs': ['TearDown', 'OneTimeTearDown'],
            'asserts': ['Assert.That', 'Assert.AreEqual', 'Assert.IsTrue', 'Assert.IsFalse', 
                       'Assert.IsNull', 'Assert.IsNotNull', 'Should.Be', 'Should.Equal'],
        },
        'xunit': {
            'test_attrs': ['Fact', 'Theory', 'InlineData'],
            'class_attrs': [],  # xUnit doesn't require class attributes
            'setup_attrs': [],  # Uses constructor
            'teardown_attrs': [],  # Uses IDisposable
            'asserts': ['Assert.Equal', 'Assert.True', 'Assert.False', 'Assert.Null', 
                       'Assert.NotNull', 'Assert.Throws', 'Assert.Contains'],
        },
        'mstest': {
            'test_attrs': ['TestMethod'],
            'class_attrs': ['TestClass'],
            'setup_attrs': ['TestInitialize', 'ClassInitialize'],
            'teardown_attrs': ['TestCleanup', 'ClassCleanup'],
            'asserts': ['Assert.AreEqual', 'Assert.IsTrue', 'Assert.IsFalse', 
                       'Assert.IsNull', 'Assert.IsNotNull', 'Assert.ThrowsException'],
        },
        'specflow': {
            'test_attrs': ['Given', 'When', 'Then', 'And', 'But'],
            'class_attrs': ['Binding'],
            'setup_attrs': ['BeforeScenario', 'BeforeFeature'],
            'teardown_attrs': ['AfterScenario', 'AfterFeature'],
            'asserts': ['Assert.That', 'Should.Be', 'Assert.AreEqual'],
        }
    }
    
    def __init__(self):
        self.framework = None
    
    def extract_signals(self, file_path: str, test_name: str) -> StructuralSignals:
        """
        Extract structural signals from .NET test file.
        
        Args:
            file_path: Path to .cs test file
            test_name: Name of test method
            
        Returns:
            StructuralSignals with API calls, assertions, setup/teardown
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Detect framework
            self.framework = self._detect_framework(content)
            logger.info(f"Detected .NET framework: {self.framework}")
            
            # Parse test class
            test_class = self._parse_test_class(content)
            
            # Find specific test method
            test_method = self._find_test_method(test_class, test_name)
            if not test_method:
                logger.warning(f"Test method '{test_name}' not found in {file_path}")
                return StructuralSignals()
            
            # Extract signals from test method
            signals = self._extract_method_signals(test_method, content)
            
            # Add setup/teardown info
            signals.has_setup = len(test_class.setup_methods) > 0
            signals.has_teardown = len(test_class.teardown_methods) > 0
            
            return signals
            
        except Exception as e:
            logger.error(f"Failed to extract signals from {file_path}: {e}")
            return StructuralSignals()
    
    def _detect_framework(self, content: str) -> str:
        """Detect .NET test framework from imports/attributes."""
        content_lower = content.lower()
        
        if 'using nunit.framework' in content_lower or '[test]' in content_lower:
            return 'nunit'
        elif 'using xunit' in content_lower or '[fact]' in content_lower:
            return 'xunit'
        elif 'using microsoft.visualstudio.testtools' in content_lower or '[testmethod]' in content_lower:
            return 'mstest'
        elif 'using techTalk.specflow' in content_lower or '[given' in content_lower:
            return 'specflow'
        else:
            # Default to NUnit (most common)
            return 'nunit'
    
    def _parse_test_class(self, content: str) -> DotNetTestClass:
        """Parse .NET test class structure."""
        # Extract namespace
        namespace_match = re.search(r'namespace\s+([\w.]+)', content)
        namespace = namespace_match.group(1) if namespace_match else 'Unknown'
        
        # Extract class name and attributes
        class_pattern = r'(\[[\w\s,()]+\]\s*)*public\s+class\s+(\w+)'
        class_match = re.search(class_pattern, content)
        
        if not class_match:
            logger.warning("Could not find test class definition")
            return DotNetTestClass(
                name='Unknown',
                namespace=namespace,
                attributes=[],
                methods=[],
                setup_methods=[],
                teardown_methods=[]
            )
        
        class_name = class_match.group(2)
        class_attrs_text = class_match.group(1) or ''
        class_attributes = self._extract_attributes(class_attrs_text)
        
        # Extract all methods
        methods = self._extract_test_methods(content)
        
        # Identify setup/teardown
        fw_config = self.TEST_FRAMEWORKS.get(self.framework, self.TEST_FRAMEWORKS['nunit'])
        setup_methods = [m.name for m in methods if any(attr in fw_config['setup_attrs'] for attr in m.attributes)]
        teardown_methods = [m.name for m in methods if any(attr in fw_config['teardown_attrs'] for attr in m.attributes)]
        
        return DotNetTestClass(
            name=class_name,
            namespace=namespace,
            attributes=class_attributes,
            methods=methods,
            setup_methods=setup_methods,
            teardown_methods=teardown_methods
        )
    
    def _extract_attributes(self, attr_text: str) -> List[str]:
        """Extract attribute names from attribute text."""
        attributes = []
        attr_pattern = r'\[(\w+)(?:\([^\]]*\))?\]'
        matches = re.finditer(attr_pattern, attr_text)
        for match in matches:
            attributes.append(match.group(1))
        return attributes
    
    def _extract_test_methods(self, content: str) -> List[DotNetTestMethod]:
        """Extract all test methods from content."""
        methods = []
        
        # Pattern to match methods with attributes and optional body
        # Use [^\]]+ to match any characters except closing bracket in attributes
        method_pattern = r'((?:\[[^\]]+\]\s*)*)(public|private|protected)?\s*(async\s+)?(\w+)\s+(\w+)\s*\(([^)]*)\)\s*(\{[^}]*\})?'
        
        matches = re.finditer(method_pattern, content, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            attrs_text = match.group(1)
            is_async = match.group(3) is not None
            return_type = match.group(4)
            method_name = match.group(5)
            params_text = match.group(6)
            body = match.group(7) if match.group(7) else ""
            
            # Extract attributes
            attributes = self._extract_attributes(attrs_text)
            
            # Check if this is a test method
            fw_config = self.TEST_FRAMEWORKS.get(self.framework, self.TEST_FRAMEWORKS['nunit'])
            is_test = any(attr in fw_config['test_attrs'] for attr in attributes)
            is_setup = any(attr in fw_config['setup_attrs'] for attr in attributes)
            is_teardown = any(attr in fw_config['teardown_attrs'] for attr in attributes)
            
            if is_test or is_setup or is_teardown:
                # Parse parameters
                parameters = self._parse_parameters(params_text)
                
                # Find line number (approximate)
                line_number = content[:match.start()].count('\n') + 1
                
                methods.append(DotNetTestMethod(
                    name=method_name,
                    attributes=attributes,
                    parameters=parameters,
                    body=body,
                    line_number=line_number,
                    is_async=is_async,
                    test_framework=self.framework
                ))
        
        return methods
    
    def _parse_parameters(self, params_text: str) -> List[Dict[str, str]]:
        """Parse method parameters."""
        parameters = []
        if not params_text.strip():
            return parameters
        
        # Split by comma (simple parsing, doesn't handle complex generics)
        param_parts = params_text.split(',')
        for part in param_parts:
            part = part.strip()
            if part:
                # Extract type and name
                param_match = re.match(r'(\w+(?:<[\w,\s]+>)?)\s+(\w+)', part)
                if param_match:
                    parameters.append({
                        'type': param_match.group(1),
                        'name': param_match.group(2)
                    })
        
        return parameters
    
    def _find_test_method(self, test_class: DotNetTestClass, test_name: str) -> Optional[DotNetTestMethod]:
        """Find specific test method by name."""
        for method in test_class.methods:
            if method.name == test_name or method.name.lower() == test_name.lower():
                return method
        return None
    
    def _extract_method_signals(self, method: DotNetTestMethod, full_content: str) -> StructuralSignals:
        """Extract structural signals from test method body."""
        signals = StructuralSignals()
        body = method.body
        
        # Extract API calls (HTTP, Database, etc.)
        api_calls = self._extract_api_calls(body)
        signals.api_calls.extend(api_calls)
        
        # Extract assertions
        assertions = self._extract_assertions(body)
        signals.assertions.extend(assertions)
        
        # Extract test steps (for SpecFlow)
        if self.framework == 'specflow':
            steps = self._extract_specflow_steps(method)
            signals.test_steps = steps
        
        # Calculate complexity
        signals.cyclomatic_complexity = self._calculate_complexity(body)
        signals.lines_of_code = body.count('\n') + 1
        
        return signals
    
    def _extract_api_calls(self, body: str) -> List[APICall]:
        """Extract API/HTTP calls from method body."""
        api_calls = []
        
        # HTTP client calls
        http_patterns = [
            r'(Get|Post|Put|Delete|Patch)Async\s*\(\s*["\']([^"\']+)["\']',
            r'SendAsync\s*\(',
            r'RestClient\s*\(["\']([^"\']+)["\']',
            r'HttpClient\.[Get|Post]',
        ]
        
        for pattern in http_patterns:
            matches = re.finditer(pattern, body, re.IGNORECASE)
            for match in matches:
                method = match.group(1) if match.lastindex >= 1 else 'HTTP'
                endpoint = match.group(2) if match.lastindex >= 2 else 'unknown'
                
                api_calls.append(APICall(
                    method=method,
                    endpoint=endpoint
                ))
        
        # Database calls
        db_patterns = [
            r'ExecuteQuery',
            r'ExecuteNonQuery',
            r'ExecuteScalar',
            r'\.Query<',
            r'\.Execute\(',
        ]
        
        for pattern in db_patterns:
            if re.search(pattern, body):
                api_calls.append(APICall(
                    method='Database',
                    endpoint='query'
                ))
                break
        
        return api_calls
    
    def _extract_assertions(self, body: str) -> List[Assertion]:
        """Extract assertions from method body."""
        assertions = []
        
        fw_config = self.TEST_FRAMEWORKS.get(self.framework, self.TEST_FRAMEWORKS['nunit'])
        assert_patterns = fw_config['asserts']
        
        for assert_type in assert_patterns:
            # Find all occurrences
            escaped_assert = re.escape(assert_type)
            pattern = f'{escaped_assert}\\s*\\(([^;]+)\\)'
            matches = re.finditer(pattern, body)
            
            for match in matches:
                assertion_text = match.group(1).strip()
                
                # Try to extract expected vs actual
                # Common patterns: (expected, actual) or (actual, expected)
                parts = assertion_text.split(',', 1)
                if len(parts) == 2:
                    expected = parts[0].strip()
                    actual = parts[1].strip()
                else:
                    expected = None
                    actual = assertion_text
                
                assertions.append(Assertion(
                    type=assert_type.replace('.', '_').lower(),
                    target=actual,
                    expected_value=expected
                ))
        
        # Fluent assertions (Should extensions)
        should_pattern = r'(\w+)\.Should\(\)\.(\w+)\(([^)]*)\)'
        should_matches = re.finditer(should_pattern, body)
        for match in should_matches:
            target = match.group(1)
            assertion_method = match.group(2)
            expected = match.group(3)
            
            assertions.append(Assertion(
                type=f'should_{assertion_method.lower()}',
                target=target,
                expected_value=expected if expected else None
            ))
        
        return assertions
    
    def _extract_specflow_steps(self, method: DotNetTestMethod) -> List[str]:
        """Extract SpecFlow step definitions."""
        steps = []
        
        # SpecFlow step attributes contain the step text
        step_attrs = ['Given', 'When', 'Then', 'And', 'But']
        
        for attr in method.attributes:
            if attr in step_attrs:
                # Find the attribute in the original method definition
                # Pattern: [Given("step text")]
                pattern = f'\\[{attr}\\(["\']([^"\']+)["\']\\)\\]'
                # This is simplified - in real code we'd need to parse the original source
                steps.append(f"{attr}: {method.name}")
        
        return steps
    
    def _calculate_complexity(self, body: str) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity
        
        # Count decision points
        keywords = ['if', 'else if', 'while', 'for', 'foreach', 'case', 'catch', '&&', '||', '?']
        
        for keyword in keywords:
            if keyword in ['&&', '||', '?']:
                complexity += body.count(keyword)
            else:
                # Count keyword followed by whitespace or (
                pattern = f'\\b{keyword}\\b[\\s(]'
                complexity += len(re.findall(pattern, body, re.IGNORECASE))
        
        return complexity


# ============================================================================
# Factory Integration
# ============================================================================

class ASTExtractorFactory:
    """Factory for creating AST extractors."""
    
    @staticmethod
    def create_extractor(language: str):
        """Create AST extractor for language."""
        if language.lower() in ['csharp', 'c#', 'dotnet', '.net']:
            return DotNetASTExtractor()
        else:
            raise ValueError(f"No AST extractor for language: {language}")


# ============================================================================
# Convenience Functions
# ============================================================================

def extract_dotnet_signals(file_path: str, test_name: str) -> StructuralSignals:
    """
    Convenience function to extract signals from .NET test.
    
    Args:
        file_path: Path to .cs test file
        test_name: Name of test method
        
    Returns:
        StructuralSignals object
    """
    extractor = DotNetASTExtractor()
    return extractor.extract_signals(file_path, test_name)


def parse_dotnet_test_file(file_path: str) -> DotNetTestClass:
    """
    Parse entire .NET test file.
    
    Args:
        file_path: Path to .cs test file
        
    Returns:
        DotNetTestClass with all methods
    """
    extractor = DotNetASTExtractor()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    extractor.framework = extractor._detect_framework(content)
    return extractor._parse_test_class(content)
