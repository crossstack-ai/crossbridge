"""
Tests for multipart handler.
"""

import pytest
from pathlib import Path
from adapters.restassured_java.multipart_handler import (
    RestAssuredMultiPartHandler,
    MultiPartFormData
)


@pytest.fixture
def handler():
    return RestAssuredMultiPartHandler()


@pytest.fixture
def sample_test_file(tmp_path):
    """Create a sample test file with multipart requests."""
    java_file = tmp_path / "FileUploadTest.java"
    java_file.write_text("""
import io.restassured.RestAssured;
import io.restassured.specification.MultiPartSpecification;
import org.junit.Test;
import java.io.File;

public class FileUploadTest {
    
    @Test
    public void testSimpleFileUpload() {
        RestAssured.given()
            .multiPart("file", new File("test.pdf"))
            .when()
            .post("/upload")
            .then()
            .statusCode(200);
    }
    
    @Test
    public void testMultipartWithFields() {
        RestAssured.given()
            .multiPart("file", new File("document.pdf"), "application/pdf")
            .multiPart("description", "Important document")
            .multiPart("category", "legal")
            .when()
            .post("/upload")
            .then()
            .statusCode(201);
    }
    
    @Test
    public void testMultipleFileUpload() {
        RestAssured.given()
            .multiPart("files", new File("file1.txt"))
            .multiPart("files", new File("file2.txt"))
            .multiPart("files", new File("file3.txt"))
            .when()
            .post("/upload/multiple")
            .then()
            .statusCode(200);
    }
}
    """)
    return java_file


def test_extract_multipart_fields(handler, sample_test_file):
    """Test extraction of multipart fields."""
    multipart_data = handler.extract_multipart_fields(sample_test_file)
    
    assert len(multipart_data) >= 3  # Three test methods


def test_simple_file_upload(handler, sample_test_file):
    """Test simple file upload extraction."""
    multipart_data = handler.extract_multipart_fields(sample_test_file)
    
    simple_upload = next(
        (m for m in multipart_data if m.method_name == "testSimpleFileUpload"),
        None
    )
    
    assert simple_upload is not None
    assert len(simple_upload.fields) == 1
    assert simple_upload.fields[0]['field_name'] == 'file'
    assert simple_upload.fields[0]['field_type'] == 'file'


def test_multipart_with_fields(handler, sample_test_file):
    """Test multipart with both files and fields."""
    multipart_data = handler.extract_multipart_fields(sample_test_file)
    
    mixed_upload = next(
        (m for m in multipart_data if m.method_name == "testMultipartWithFields"),
        None
    )
    
    assert mixed_upload is not None
    assert len(mixed_upload.fields) == 3
    
    # Check file field
    file_field = next((f for f in mixed_upload.fields if f['field_name'] == 'file'), None)
    assert file_field is not None
    assert file_field['field_type'] == 'file'
    assert 'content_type' in file_field
    
    # Check text field
    text_field = next((f for f in mixed_upload.fields if f['field_name'] == 'description'), None)
    assert text_field is not None
    assert text_field['field_type'] == 'text'


def test_multiple_file_upload(handler, sample_test_file):
    """Test multiple file uploads."""
    multipart_data = handler.extract_multipart_fields(sample_test_file)
    
    multi_upload = next(
        (m for m in multipart_data if m.method_name == "testMultipleFileUpload"),
        None
    )
    
    assert multi_upload is not None
    assert len(multi_upload.fields) == 3
    
    # All should be file fields with same name
    for field in multi_upload.fields:
        assert field['field_name'] == 'files'
        assert field['field_type'] == 'file'


def test_convert_to_robot_keywords(handler, sample_test_file):
    """Test conversion to Robot Framework keywords."""
    multipart_data = handler.extract_multipart_fields(sample_test_file)
    
    simple_upload = next(
        (m for m in multipart_data if m.method_name == "testSimpleFileUpload"),
        None
    )
    
    robot_code = handler.convert_to_robot_keywords(simple_upload)
    
    assert "*** Keywords ***" in robot_code
    assert "Upload File" in robot_code or "POST" in robot_code
    assert "/upload" in robot_code


def test_generate_requests_library_code(handler, sample_test_file):
    """Test generation of Python requests library code."""
    multipart_data = handler.extract_multipart_fields(sample_test_file)
    
    simple_upload = next(
        (m for m in multipart_data if m.method_name == "testSimpleFileUpload"),
        None
    )
    
    requests_code = handler.generate_requests_library_code(simple_upload)
    
    assert "import requests" in requests_code
    assert "files =" in requests_code
    assert "requests.post" in requests_code


def test_get_content_type(handler):
    """Test content type detection."""
    assert handler._get_content_type("test.pdf") == "application/pdf"
    assert handler._get_content_type("image.jpg") == "image/jpeg"
    assert handler._get_content_type("document.txt") == "text/plain"
    assert handler._get_content_type("unknown.xyz") == "application/octet-stream"
