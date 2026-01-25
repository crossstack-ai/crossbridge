"""
TestNG listener extraction and transformation for Selenium Java tests.

Handles custom TestNG listeners, retry analyzers, and suite listeners.
"""

import re
from typing import List, Dict, Optional, Set
from pathlib import Path
from dataclasses import dataclass


@dataclass
class TestNGListener:
    """Represents a TestNG listener configuration."""
    listener_class: str
    listener_type: str  # 'test', 'suite', 'method', 'retry', 'reporter'
    methods: List[str]
    annotations: List[str]
    file_path: Path


class TestNGListenerExtractor:
    """Extract TestNG listeners from Java test projects."""
    
    def __init__(self):
        # Listener annotation patterns
        self.listeners_annotation = re.compile(
            r'@Listeners\s*\(\s*\{([^}]+)\}\s*\)',
            re.MULTILINE
        )
        self.listener_single = re.compile(
            r'@Listeners\s*\(\s*([^)]+?)\.class\s*\)',
            re.MULTILINE
        )
        
        # Listener interface patterns
        self.listener_interfaces = {
            'ITestListener': re.compile(r'implements\s+ITestListener'),
            'ISuiteListener': re.compile(r'implements\s+ISuiteListener'),
            'IInvokedMethodListener': re.compile(r'implements\s+IInvokedMethodListener'),
            'IRetryAnalyzer': re.compile(r'implements\s+IRetryAnalyzer'),
            'IReporter': re.compile(r'implements\s+IReporter'),
            'IAnnotationTransformer': re.compile(r'implements\s+IAnnotationTransformer'),
        }
        
        # Listener methods
        self.listener_methods = {
            'onTestStart': re.compile(r'public\s+void\s+onTestStart\s*\([^)]+\)'),
            'onTestSuccess': re.compile(r'public\s+void\s+onTestSuccess\s*\([^)]+\)'),
            'onTestFailure': re.compile(r'public\s+void\s+onTestFailure\s*\([^)]+\)'),
            'onTestSkipped': re.compile(r'public\s+void\s+onTestSkipped\s*\([^)]+\)'),
            'onStart': re.compile(r'public\s+void\s+onStart\s*\([^)]+\)'),
            'onFinish': re.compile(r'public\s+void\s+onFinish\s*\([^)]+\)'),
            'retry': re.compile(r'public\s+boolean\s+retry\s*\([^)]+\)'),
        }
    
    def extract_listener_annotations(
        self,
        java_file: Path
    ) -> List[str]:
        """
        Extract @Listeners annotations from Java file.
        
        Args:
            java_file: Path to Java test file
            
        Returns:
            List of listener class names
        """
        if not java_file.exists():
            return []
        
        content = java_file.read_text(encoding='utf-8')
        listeners = []
        
        # Multi-listener annotation: @Listeners({Listener1.class, Listener2.class})
        for match in self.listeners_annotation.finditer(content):
            listener_list = match.group(1)
            # Extract class names
            class_names = re.findall(r'(\w+)\.class', listener_list)
            listeners.extend(class_names)
        
        # Single listener annotation: @Listeners(MyListener.class)
        for match in self.listener_single.finditer(content):
            listener_class = match.group(1)
            listeners.append(listener_class)
        
        return listeners
    
    def detect_listener_implementations(
        self,
        java_file: Path
    ) -> List[TestNGListener]:
        """
        Detect listener interface implementations in Java file.
        
        Args:
            java_file: Path to Java file
            
        Returns:
            List of TestNGListener objects
        """
        if not java_file.exists():
            return []
        
        content = java_file.read_text(encoding='utf-8')
        listeners = []
        
        # Extract class name
        class_match = re.search(r'(?:public\s+)?class\s+(\w+)', content)
        class_name = class_match.group(1) if class_match else 'Unknown'
        
        # Check each listener interface
        for interface_name, pattern in self.listener_interfaces.items():
            if pattern.search(content):
                # Extract implemented methods
                methods = []
                for method_name, method_pattern in self.listener_methods.items():
                    if method_pattern.search(content):
                        methods.append(method_name)
                
                # Determine listener type
                listener_type = self._get_listener_type(interface_name)
                
                listeners.append(TestNGListener(
                    listener_class=class_name,
                    listener_type=listener_type,
                    methods=methods,
                    annotations=[f'@{interface_name}'],
                    file_path=java_file
                ))
        
        return listeners
    
    def _get_listener_type(self, interface_name: str) -> str:
        """Determine listener type from interface name."""
        type_map = {
            'ITestListener': 'test',
            'ISuiteListener': 'suite',
            'IInvokedMethodListener': 'method',
            'IRetryAnalyzer': 'retry',
            'IReporter': 'reporter',
            'IAnnotationTransformer': 'transformer',
        }
        return type_map.get(interface_name, 'unknown')
    
    def extract_from_testng_xml(
        self,
        testng_xml: Path
    ) -> List[str]:
        """
        Extract listeners from testng.xml configuration.
        
        Args:
            testng_xml: Path to testng.xml file
            
        Returns:
            List of listener class names
        """
        if not testng_xml.exists():
            return []
        
        content = testng_xml.read_text(encoding='utf-8')
        
        # Extract <listener> tags
        listener_pattern = re.compile(
            r'<listener\s+class-name="([^"]+)"',
            re.MULTILINE
        )
        
        listeners = []
        for match in listener_pattern.finditer(content):
            listener_class = match.group(1)
            listeners.append(listener_class)
        
        return listeners
    
    def extract_retry_analyzer(
        self,
        java_file: Path
    ) -> Optional[Dict[str, any]]:
        """
        Extract retry analyzer configuration.
        
        Args:
            java_file: Path to Java file with IRetryAnalyzer
            
        Returns:
            Dictionary with retry configuration or None
        """
        if not java_file.exists():
            return None
        
        content = java_file.read_text(encoding='utf-8')
        
        # Check if implements IRetryAnalyzer
        if not self.listener_interfaces['IRetryAnalyzer'].search(content):
            return None
        
        # Extract max retry count
        max_retry_pattern = re.compile(
            r'(?:private|public)\s+(?:static\s+)?(?:final\s+)?int\s+MAX_RETRY\w*\s*=\s*(\d+)',
            re.IGNORECASE
        )
        
        max_retry_match = max_retry_pattern.search(content)
        max_retry = int(max_retry_match.group(1)) if max_retry_match else 3
        
        # Extract retry counter
        counter_pattern = re.compile(
            r'(?:private|public)\s+int\s+(\w*count\w*)',
            re.IGNORECASE
        )
        
        counter_match = counter_pattern.search(content)
        counter_var = counter_match.group(1) if counter_match else 'retryCount'
        
        return {
            'max_retries': max_retry,
            'counter_variable': counter_var,
            'file': str(java_file)
        }
    
    def convert_to_pytest_plugin(
        self,
        listener: TestNGListener
    ) -> str:
        """
        Convert TestNG listener to pytest plugin equivalent.
        
        Args:
            listener: TestNGListener object
            
        Returns:
            Python pytest plugin code
        """
        if listener.listener_type == 'test':
            return self._convert_test_listener(listener)
        elif listener.listener_type == 'retry':
            return self._convert_retry_analyzer(listener)
        elif listener.listener_type == 'reporter':
            return self._convert_reporter(listener)
        else:
            return f"# Listener type '{listener.listener_type}' - manual implementation needed"
    
    def _convert_test_listener(self, listener: TestNGListener) -> str:
        """Convert ITestListener to pytest hooks."""
        code = "# pytest hooks equivalent to TestNG ITestListener\n\n"
        
        if 'onTestStart' in listener.methods:
            code += "def pytest_runtest_setup(item):\n"
            code += "    # Equivalent to onTestStart\n"
            code += "    pass\n\n"
        
        if 'onTestSuccess' in listener.methods:
            code += "def pytest_runtest_makereport(item, call):\n"
            code += "    if call.when == 'call' and call.excinfo is None:\n"
            code += "        # Equivalent to onTestSuccess\n"
            code += "        pass\n\n"
        
        if 'onTestFailure' in listener.methods:
            code += "def pytest_runtest_makereport(item, call):\n"
            code += "    if call.when == 'call' and call.excinfo is not None:\n"
            code += "        # Equivalent to onTestFailure\n"
            code += "        pass\n\n"
        
        return code
    
    def _convert_retry_analyzer(self, listener: TestNGListener) -> str:
        """Convert IRetryAnalyzer to pytest-rerunfailures."""
        return (
            "# Install: pip install pytest-rerunfailures\n"
            "# Usage: pytest --reruns 3 --reruns-delay 1\n\n"
            "# Or use conftest.py:\n"
            "def pytest_addoption(parser):\n"
            "    parser.addoption('--reruns', action='store', default=3)\n"
        )
    
    def _convert_reporter(self, listener: TestNGListener) -> str:
        """Convert IReporter to pytest-html or similar."""
        return (
            "# Install: pip install pytest-html\n"
            "# Usage: pytest --html=report.html --self-contained-html\n"
        )
    
    def has_custom_listeners(self, project_root: Path) -> bool:
        """Check if project has custom TestNG listeners."""
        for java_file in project_root.rglob("*.java"):
            listeners = self.detect_listener_implementations(java_file)
            if listeners:
                return True
        
        return False
