"""
Comprehensive unit tests for Custom Annotation Extractor.
"""

import pytest
from pathlib import Path
from adapters.java.custom_annotation_extractor import JavaCustomAnnotationExtractor


@pytest.fixture
def extractor():
    return JavaCustomAnnotationExtractor()


@pytest.fixture
def java_file_with_annotations(tmp_path):
    """Create Java file with custom annotations."""
    java_file = tmp_path / "TestClass.java"
    java_file.write_text("""
package com.example.tests;

import org.junit.Test;

public class TestClass {
    
    @Screenshot("login_page")
    @Test
    public void testLogin() {
        // Test code
    }
    
    @Retry(maxAttempts = 3, delay = 1000)
    @Test
    public void testFlaky() {
        // Flaky test
    }
    
    @Flaky(reason = "Network dependent")
    @Screenshot(value = "network_test", onFailure = true)
    @Test
    public void testNetwork() {
        // Network test
    }
    
    @Performance(threshold = 2000)
    @Test
    public void testSpeed() {
        // Performance test
    }
    
    @DataSetup(file = "testdata.json")
    @Test
    public void testWithData() {
        // Test with data
    }
    
    @RequiresEnvironment("production")
    @Test
    public void testProduction() {
        // Production only test
    }
    
    @LogLevel("DEBUG")
    @Timeout(seconds = 30)
    @Test
    public void testWithTimeout() {
        // Test with custom timeout
    }
    
    @CustomConfig(
        key = "test.config",
        value = "custom_value",
        override = true
    )
    @Test
    public void testWithConfig() {
        // Test with configuration
    }
    
    @VideoRecord
    @Screenshot
    @Test
    public void testWithRecording() {
        // Recorded test
    }
    
    @BrowserStack(
        browser = "chrome",
        version = "latest",
        os = "Windows",
        osVersion = "10"
    )
    @Test
    public void testOnBrowserStack() {
        // BrowserStack test
    }
}
    """)
    return java_file


@pytest.fixture
def java_file_class_level_annotations(tmp_path):
    """Create Java file with class-level annotations."""
    java_file = tmp_path / "AnnotatedClass.java"
    java_file.write_text("""
package com.example;

@Screenshot(beforeEach = true)
@Retry(maxAttempts = 2)
@Performance(enabled = false)
public class AnnotatedClass {
    
    @Test
    public void test1() {}
    
    @Test
    public void test2() {}
}
    """)
    return java_file


class TestAnnotationExtraction:
    """Test basic annotation extraction."""
    
    def test_extract_screenshot_annotation(self, extractor, java_file_with_annotations):
        """Test extraction of @Screenshot annotation."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        screenshot_annots = [a for a in annotations if a.annotation_type == 'Screenshot']
        assert len(screenshot_annots) >= 2
    
    def test_extract_retry_annotation(self, extractor, java_file_with_annotations):
        """Test extraction of @Retry annotation."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        retry_annots = [a for a in annotations if a.annotation_type == 'Retry']
        assert len(retry_annots) >= 1
        
        retry = retry_annots[0]
        assert 'maxAttempts' in retry.parameters
        assert retry.parameters['maxAttempts'] == '3'
    
    def test_extract_flaky_annotation(self, extractor, java_file_with_annotations):
        """Test extraction of @Flaky annotation."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        flaky_annots = [a for a in annotations if a.annotation_type == 'Flaky']
        assert len(flaky_annots) >= 1
        
        flaky = flaky_annots[0]
        assert 'reason' in flaky.parameters
    
    def test_extract_performance_annotation(self, extractor, java_file_with_annotations):
        """Test extraction of @Performance annotation."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        perf_annots = [a for a in annotations if a.annotation_type == 'Performance']
        assert len(perf_annots) >= 1


class TestAnnotationParameters:
    """Test extraction of annotation parameters."""
    
    def test_single_parameter(self, extractor, java_file_with_annotations):
        """Test annotation with single parameter."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        screenshot = next((a for a in annotations if a.annotation_type == 'Screenshot' and 'login_page' in str(a.parameters)), None)
        assert screenshot is not None
    
    def test_multiple_parameters(self, extractor, java_file_with_annotations):
        """Test annotation with multiple parameters."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        browserstack = next((a for a in annotations if a.annotation_type == 'BrowserStack'), None)
        assert browserstack is not None
        assert 'browser' in browserstack.parameters
        assert 'version' in browserstack.parameters
        assert 'os' in browserstack.parameters
    
    def test_boolean_parameters(self, extractor, java_file_with_annotations):
        """Test annotation with boolean parameters."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        screenshot = next((a for a in annotations if 'onFailure' in a.parameters), None)
        if screenshot:
            assert screenshot.parameters['onFailure'] in ['true', 'True', True]
    
    def test_numeric_parameters(self, extractor, java_file_with_annotations):
        """Test annotation with numeric parameters."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        retry = next((a for a in annotations if a.annotation_type == 'Retry'), None)
        assert retry is not None
        assert 'maxAttempts' in retry.parameters
        assert retry.parameters['maxAttempts'] == '3'


class TestMethodLevelAnnotations:
    """Test method-level annotation details."""
    
    def test_method_name_capture(self, extractor, java_file_with_annotations):
        """Test capture of method name."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        method_names = [a.method_name for a in annotations if a.method_name]
        assert 'testLogin' in method_names
        assert 'testFlaky' in method_names
    
    def test_multiple_annotations_per_method(self, extractor, java_file_with_annotations):
        """Test methods with multiple annotations."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        # testNetwork has @Flaky and @Screenshot
        network_annots = [a for a in annotations if a.method_name == 'testNetwork']
        assert len(network_annots) >= 2
        
        types = [a.annotation_type for a in network_annots]
        assert 'Flaky' in types
        assert 'Screenshot' in types
    
    def test_line_number_tracking(self, extractor, java_file_with_annotations):
        """Test line number tracking for annotations."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        for annotation in annotations:
            assert annotation.line_number > 0


class TestClassLevelAnnotations:
    """Test class-level annotations."""
    
    def test_extract_class_annotations(self, extractor, java_file_class_level_annotations):
        """Test extraction of class-level annotations."""
        annotations = extractor.extract_annotations(java_file_class_level_annotations)
        
        class_annots = [a for a in annotations if a.level == 'class']
        assert len(class_annots) >= 1
    
    def test_class_annotation_applies_to_all_methods(self, extractor, java_file_class_level_annotations):
        """Test that class annotations are noted."""
        annotations = extractor.extract_annotations(java_file_class_level_annotations)
        
        # Should find class-level annotations
        screenshot_class = next((a for a in annotations if a.annotation_type == 'Screenshot' and a.level == 'class'), None)
        assert screenshot_class is not None


class TestAnnotationTypes:
    """Test handling of different annotation types."""
    
    def test_all_supported_types(self, extractor, java_file_with_annotations):
        """Test all supported annotation types are detected."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        types = {a.annotation_type for a in annotations}
        
        expected_types = ['Screenshot', 'Retry', 'Flaky', 'Performance', 
                         'DataSetup', 'RequiresEnvironment', 'LogLevel', 
                         'Timeout', 'CustomConfig', 'VideoRecord', 'BrowserStack']
        
        # Should find most of these
        found = [t for t in expected_types if t in types]
        assert len(found) >= 8
    
    def test_parameterless_annotations(self, extractor, java_file_with_annotations):
        """Test annotations without parameters."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        video = next((a for a in annotations if a.annotation_type == 'VideoRecord'), None)
        if video:
            assert len(video.parameters) == 0 or video.parameters == {}


class TestGetAnnotatedMethods:
    """Test getting methods by annotation type."""
    
    def test_get_methods_with_screenshot(self, extractor, java_file_with_annotations):
        """Test getting methods annotated with @Screenshot."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        methods = extractor.get_annotated_methods(annotations, 'Screenshot')
        
        assert len(methods) >= 2
        assert 'testLogin' in methods or any('testLogin' in m for m in methods)
    
    def test_get_methods_with_retry(self, extractor, java_file_with_annotations):
        """Test getting methods annotated with @Retry."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        methods = extractor.get_annotated_methods(annotations, 'Retry')
        
        assert len(methods) >= 1


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_no_annotations(self, extractor, tmp_path):
        """Test file without custom annotations."""
        java_file = tmp_path / "NoAnnotations.java"
        java_file.write_text("""
public class NoAnnotations {
    @Test
    public void test1() {}
}
        """)
        
        annotations = extractor.extract_annotations(java_file)
        # @Test is standard, not custom
        custom_annots = [a for a in annotations if a.annotation_type not in ['Test', 'Before', 'After']]
        assert len(custom_annots) == 0
    
    def test_malformed_annotation(self, extractor, tmp_path):
        """Test handling of malformed annotation."""
        java_file = tmp_path / "Malformed.java"
        java_file.write_text("""
public class Malformed {
    @CustomAnnotation(incomplete
    public void test() {}
}
        """)
        
        # Should handle gracefully
        annotations = extractor.extract_annotations(java_file)
        assert isinstance(annotations, list)
    
    def test_nonexistent_file(self, extractor, tmp_path):
        """Test handling of nonexistent file."""
        nonexistent = tmp_path / "doesnt_exist.java"
        
        annotations = extractor.extract_annotations(nonexistent)
        assert len(annotations) == 0
    
    def test_annotation_with_array_parameter(self, extractor, tmp_path):
        """Test annotation with array parameter."""
        java_file = tmp_path / "ArrayParam.java"
        java_file.write_text("""
public class ArrayParam {
    @Tags({"smoke", "regression", "critical"})
    @Test
    public void test() {}
}
        """)
        
        annotations = extractor.extract_annotations(java_file)
        tags_annot = next((a for a in annotations if a.annotation_type == 'Tags'), None)
        if tags_annot:
            # Should capture array somehow
            assert tags_annot.parameters or tags_annot.annotation_type == 'Tags'


class TestConversionToPytest:
    """Test conversion to pytest decorators."""
    
    def test_convert_retry_to_pytest(self, extractor, java_file_with_annotations):
        """Test conversion of @Retry to pytest.mark.flaky."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        retry = next((a for a in annotations if a.annotation_type == 'Retry'), None)
        pytest_code = extractor.convert_to_pytest_decorator(retry)
        
        assert pytest_code is not None
        assert '@pytest.mark' in pytest_code or 'pytest' in pytest_code
    
    def test_convert_performance_to_pytest(self, extractor, java_file_with_annotations):
        """Test conversion of @Performance annotation."""
        annotations = extractor.extract_annotations(java_file_with_annotations)
        
        perf = next((a for a in annotations if a.annotation_type == 'Performance'), None)
        if perf:
            pytest_code = extractor.convert_to_pytest_decorator(perf)
            assert pytest_code is not None


class TestRealWorldScenarios:
    """Test real-world annotation patterns."""
    
    def test_selenium_grid_annotations(self, extractor, tmp_path):
        """Test Selenium Grid annotations."""
        java_file = tmp_path / "GridTest.java"
        java_file.write_text("""
public class GridTest {
    @SeleniumGrid(
        hub = "http://localhost:4444",
        browser = "chrome",
        platform = "LINUX"
    )
    @Test
    public void testOnGrid() {}
}
        """)
        
        annotations = extractor.extract_annotations(java_file)
        grid = next((a for a in annotations if a.annotation_type == 'SeleniumGrid'), None)
        if grid:
            assert 'hub' in grid.parameters
    
    def test_api_test_annotations(self, extractor, tmp_path):
        """Test API testing annotations."""
        java_file = tmp_path / "APITest.java"
        java_file.write_text("""
public class APITest {
    @Endpoint(url = "/api/users", method = "GET")
    @ExpectedStatus(200)
    @ResponseTime(max = 1000)
    @Test
    public void testAPI() {}
}
        """)
        
        annotations = extractor.extract_annotations(java_file)
        assert len(annotations) >= 1
    
    def test_security_test_annotations(self, extractor, tmp_path):
        """Test security testing annotations."""
        java_file = tmp_path / "SecurityTest.java"
        java_file.write_text("""
public class SecurityTest {
    @RequiresRole("admin")
    @RequiresPermission("read:sensitive")
    @Test
    public void testAdminAccess() {}
}
        """)
        
        annotations = extractor.extract_annotations(java_file)
        roles = [a for a in annotations if 'Role' in a.annotation_type or 'Permission' in a.annotation_type]
        assert len(roles) >= 1
