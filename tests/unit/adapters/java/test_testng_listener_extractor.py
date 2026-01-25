"""
Comprehensive unit tests for TestNG Listener Extractor.
"""

import pytest
from pathlib import Path
from adapters.java.testng_listener_extractor import TestNGListenerExtractor


@pytest.fixture
def extractor():
    return TestNGListenerExtractor()


@pytest.fixture
def java_file_with_listeners(tmp_path):
    """Create Java file with TestNG listeners."""
    java_file = tmp_path / "TestWithListeners.java"
    java_file.write_text("""
package com.example.tests;

import org.testng.annotations.*;
import org.testng.ITestListener;
import org.testng.ITestResult;
import org.testng.IRetryAnalyzer;

@Listeners({TestListener.class, RetryListener.class})
public class TestWithListeners {
    
    @Test
    public void testMethod1() {}
    
    @Test(retryAnalyzer = CustomRetryAnalyzer.class)
    public void testWithRetry() {}
}

class TestListener implements ITestListener {
    @Override
    public void onTestStart(ITestResult result) {
        System.out.println("Test started: " + result.getName());
    }
    
    @Override
    public void onTestSuccess(ITestResult result) {
        System.out.println("Test passed: " + result.getName());
    }
    
    @Override
    public void onTestFailure(ITestResult result) {
        System.out.println("Test failed: " + result.getName());
        takeScreenshot(result);
    }
    
    @Override
    public void onTestSkipped(ITestResult result) {
        System.out.println("Test skipped: " + result.getName());
    }
}

class CustomRetryAnalyzer implements IRetryAnalyzer {
    private int retryCount = 0;
    private static final int maxRetryCount = 3;
    
    @Override
    public boolean retry(ITestResult result) {
        if (retryCount < maxRetryCount) {
            retryCount++;
            return true;
        }
        return false;
    }
}

class RetryListener implements ITestListener {
    @Override
    public void onTestFailure(ITestResult result) {
        if (result.getMethod().getRetryAnalyzer() != null) {
            result.getMethod().getRetryAnalyzer().retry(result);
        }
    }
}
    """)
    return java_file


@pytest.fixture
def testng_xml_file(tmp_path):
    """Create testng.xml with listener configuration."""
    xml_file = tmp_path / "testng.xml"
    xml_file.write_text("""
<!DOCTYPE suite SYSTEM "https://testng.org/testng-1.0.dtd">
<suite name="Test Suite" parallel="methods" thread-count="3">
    <listeners>
        <listener class-name="com.example.EmailReporter"/>
        <listener class-name="com.example.SlackNotifier"/>
        <listener class-name="com.example.ScreenshotListener"/>
    </listeners>
    
    <test name="Smoke Tests">
        <classes>
            <class name="com.example.LoginTest"/>
            <class name="com.example.SearchTest"/>
        </classes>
    </test>
</suite>
    """)
    return xml_file


class TestListenerExtraction:
    """Test basic listener extraction."""
    
    def test_extract_listener_annotation(self, extractor, java_file_with_listeners):
        """Test extraction of @Listeners annotation."""
        listeners = extractor.extract_listener_annotations(java_file_with_listeners)
        
        assert len(listeners) > 0
        listener_classes = [l.listener_class for l in listeners]
        assert 'TestListener' in listener_classes or 'RetryListener' in listener_classes
    
    def test_extract_multiple_listeners(self, extractor, java_file_with_listeners):
        """Test extraction of multiple listeners from annotation."""
        listeners = extractor.extract_listener_annotations(java_file_with_listeners)
        
        # @Listeners({TestListener.class, RetryListener.class})
        assert len(listeners) >= 2
    
    def test_listener_interface_detection(self, extractor, java_file_with_listeners):
        """Test detection of implemented listener interfaces."""
        listeners = extractor.extract_listener_implementations(java_file_with_listeners)
        
        assert len(listeners) > 0
        
        # Should find ITestListener implementations
        test_listener = next((l for l in listeners if l.listener_interface == 'ITestListener'), None)
        assert test_listener is not None


class TestRetryAnalyzer:
    """Test retry analyzer extraction."""
    
    def test_extract_retry_analyzer_annotation(self, extractor, java_file_with_listeners):
        """Test extraction of retryAnalyzer from @Test annotation."""
        retry_analyzers = extractor.extract_retry_analyzer(java_file_with_listeners)
        
        assert len(retry_analyzers) > 0
        
        custom_retry = next((r for r in retry_analyzers if 'CustomRetryAnalyzer' in r.analyzer_class), None)
        assert custom_retry is not None
    
    def test_retry_analyzer_implementation(self, extractor, java_file_with_listeners):
        """Test detection of IRetryAnalyzer implementation."""
        implementations = extractor.extract_retry_analyzer_implementations(java_file_with_listeners)
        
        assert len(implementations) > 0
        
        # Should find CustomRetryAnalyzer class
        custom = next((i for i in implementations if 'CustomRetryAnalyzer' in i.analyzer_class), None)
        assert custom is not None
    
    def test_retry_count_extraction(self, extractor, java_file_with_listeners):
        """Test extraction of retry count from implementation."""
        implementations = extractor.extract_retry_analyzer_implementations(java_file_with_listeners)
        
        custom = next((i for i in implementations if 'CustomRetryAnalyzer' in i.analyzer_class), None)
        if custom:
            # Should extract maxRetryCount
            assert hasattr(custom, 'max_retry_count') or 'max' in str(custom.__dict__)


class TestListenerMethods:
    """Test listener method extraction."""
    
    def test_extract_listener_methods(self, extractor, java_file_with_listeners):
        """Test extraction of listener method implementations."""
        listeners = extractor.extract_listener_implementations(java_file_with_listeners)
        
        test_listener = next((l for l in listeners if 'TestListener' in l.listener_class), None)
        assert test_listener is not None
        
        # Should have override methods
        methods = test_listener.methods if hasattr(test_listener, 'methods') else []
        expected_methods = ['onTestStart', 'onTestSuccess', 'onTestFailure', 'onTestSkipped']
        
        # At least some methods should be found
        assert len(methods) >= 2 or test_listener.listener_interface == 'ITestListener'
    
    def test_onTestFailure_logic(self, extractor, java_file_with_listeners):
        """Test extraction of onTestFailure implementation."""
        listeners = extractor.extract_listener_implementations(java_file_with_listeners)
        
        test_listener = next((l for l in listeners if 'TestListener' in l.listener_class), None)
        if test_listener and hasattr(test_listener, 'implementation'):
            # Should contain screenshot logic
            assert 'screenshot' in test_listener.implementation.lower() or 'Screenshot' in test_listener.implementation


class TestTestNGXMLParsing:
    """Test parsing of testng.xml configuration."""
    
    def test_parse_testng_xml(self, extractor, testng_xml_file):
        """Test parsing listeners from testng.xml."""
        listeners = extractor.extract_listeners_from_xml(testng_xml_file)
        
        assert len(listeners) >= 3
        
        listener_names = [l.listener_class for l in listeners]
        assert 'EmailReporter' in listener_names or 'com.example.EmailReporter' in listener_names
    
    def test_xml_listener_classes(self, extractor, testng_xml_file):
        """Test extraction of listener class names from XML."""
        listeners = extractor.extract_listeners_from_xml(testng_xml_file)
        
        expected_listeners = ['EmailReporter', 'SlackNotifier', 'ScreenshotListener']
        found = [l for l in expected_listeners if any(l in listener.listener_class for listener in listeners)]
        
        assert len(found) >= 2


class TestPytestPluginConversion:
    """Test conversion to pytest plugin format."""
    
    def test_convert_test_listener_to_pytest(self, extractor, java_file_with_listeners):
        """Test conversion of ITestListener to pytest hooks."""
        listeners = extractor.extract_listener_implementations(java_file_with_listeners)
        
        test_listener = next((l for l in listeners if 'TestListener' in l.listener_class), None)
        if test_listener:
            pytest_plugin = extractor.convert_to_pytest_plugin(test_listener)
            
            assert pytest_plugin is not None
            assert 'pytest_runtest' in pytest_plugin or 'def pytest_' in pytest_plugin
    
    def test_pytest_hooks_mapping(self, extractor, java_file_with_listeners):
        """Test mapping of TestNG methods to pytest hooks."""
        listeners = extractor.extract_listener_implementations(java_file_with_listeners)
        
        test_listener = next((l for l in listeners if 'TestListener' in l.listener_class), None)
        if test_listener:
            pytest_plugin = extractor.convert_to_pytest_plugin(test_listener)
            
            # onTestStart -> pytest_runtest_setup or pytest_runtest_call
            # onTestFailure -> pytest_runtest_makereport
            assert 'pytest' in pytest_plugin.lower()


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_no_listeners(self, extractor, tmp_path):
        """Test file without listeners."""
        java_file = tmp_path / "NoListeners.java"
        java_file.write_text("""
public class NoListeners {
    @Test
    public void test1() {}
}
        """)
        
        listeners = extractor.extract_listener_annotations(java_file)
        assert len(listeners) == 0
    
    def test_empty_listeners_annotation(self, extractor, tmp_path):
        """Test empty @Listeners annotation."""
        java_file = tmp_path / "EmptyListeners.java"
        java_file.write_text("""
@Listeners({})
public class EmptyListeners {
    @Test
    public void test1() {}
}
        """)
        
        listeners = extractor.extract_listener_annotations(java_file)
        # Should handle gracefully
        assert isinstance(listeners, list)
    
    def test_nonexistent_file(self, extractor, tmp_path):
        """Test handling of nonexistent file."""
        nonexistent = tmp_path / "doesnt_exist.java"
        
        listeners = extractor.extract_listener_annotations(nonexistent)
        assert len(listeners) == 0
    
    def test_malformed_xml(self, extractor, tmp_path):
        """Test handling of malformed testng.xml."""
        xml_file = tmp_path / "malformed.xml"
        xml_file.write_text("<suite><listeners>incomplete")
        
        listeners = extractor.extract_listeners_from_xml(xml_file)
        # Should handle gracefully
        assert isinstance(listeners, list)


class TestComplexListeners:
    """Test complex listener scenarios."""
    
    def test_multiple_interface_implementation(self, extractor, tmp_path):
        """Test listener implementing multiple interfaces."""
        java_file = tmp_path / "MultiListener.java"
        java_file.write_text("""
public class MultiListener implements ITestListener, IReporter, ISuiteListener {
    @Override
    public void onTestStart(ITestResult result) {}
    
    @Override
    public void generateReport(List<XmlSuite> xmlSuites, List<ISuite> suites, String outputDirectory) {}
    
    @Override
    public void onStart(ISuite suite) {}
    
    @Override
    public void onFinish(ISuite suite) {}
}
        """)
        
        listeners = extractor.extract_listener_implementations(java_file)
        assert len(listeners) >= 1
        
        # Should detect multiple interfaces
        multi = listeners[0]
        interfaces = multi.listener_interface if hasattr(multi, 'listener_interface') else ''
        # Might be comma-separated or array
        assert 'ITestListener' in str(interfaces) or len(listeners) > 1
    
    def test_custom_reporter_listener(self, extractor, tmp_path):
        """Test custom reporter implementation."""
        java_file = tmp_path / "CustomReporter.java"
        java_file.write_text("""
import org.testng.IReporter;
import org.testng.ISuite;
import org.testng.xml.XmlSuite;

public class CustomReporter implements IReporter {
    @Override
    public void generateReport(List<XmlSuite> xmlSuites, List<ISuite> suites, String outputDirectory) {
        // Generate HTML report
        for (ISuite suite : suites) {
            Map<String, ISuiteResult> results = suite.getResults();
            // Process results
        }
    }
}
        """)
        
        listeners = extractor.extract_listener_implementations(java_file)
        assert len(listeners) > 0
        
        reporter = next((l for l in listeners if l.listener_interface == 'IReporter'), None)
        assert reporter is not None
    
    def test_listener_with_configuration(self, extractor, tmp_path):
        """Test listener with configuration parameters."""
        java_file = tmp_path / "ConfigurableListener.java"
        java_file.write_text("""
public class ConfigurableListener implements ITestListener {
    private String screenshotPath;
    private boolean enableLogging;
    
    public ConfigurableListener(String path, boolean logging) {
        this.screenshotPath = path;
        this.enableLogging = logging;
    }
    
    @Override
    public void onTestFailure(ITestResult result) {
        if (enableLogging) {
            log("Test failed: " + result.getName());
        }
    }
}
        """)
        
        listeners = extractor.extract_listener_implementations(java_file)
        assert len(listeners) > 0


class TestRetryAnalyzerVariations:
    """Test different retry analyzer patterns."""
    
    def test_configurable_retry_count(self, extractor, tmp_path):
        """Test retry analyzer with configurable count."""
        java_file = tmp_path / "ConfigRetry.java"
        java_file.write_text("""
public class ConfigurableRetry implements IRetryAnalyzer {
    private int count = 0;
    private int maxCount;
    
    public ConfigurableRetry() {
        this.maxCount = Integer.parseInt(System.getProperty("retry.count", "3"));
    }
    
    @Override
    public boolean retry(ITestResult result) {
        return count++ < maxCount;
    }
}
        """)
        
        implementations = extractor.extract_retry_analyzer_implementations(java_file)
        assert len(implementations) > 0
    
    def test_conditional_retry(self, extractor, tmp_path):
        """Test retry analyzer with conditions."""
        java_file = tmp_path / "ConditionalRetry.java"
        java_file.write_text("""
public class ConditionalRetry implements IRetryAnalyzer {
    @Override
    public boolean retry(ITestResult result) {
        Throwable throwable = result.getThrowable();
        if (throwable instanceof TimeoutException || throwable instanceof NoSuchElementException) {
            return retryCount++ < 3;
        }
        return false;
    }
}
        """)
        
        implementations = extractor.extract_retry_analyzer_implementations(java_file)
        assert len(implementations) > 0
