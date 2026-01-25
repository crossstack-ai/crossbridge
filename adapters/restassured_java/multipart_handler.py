"""
Multi-part form data handling for RestAssured tests.

Handles file uploads and complex form submissions.
"""

import re
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass


@dataclass
class MultiPartFormData:
    """Represents a multi-part form field."""
    field_name: str
    value: Optional[str] = None
    file_path: Optional[str] = None
    content_type: Optional[str] = None
    file_name: Optional[str] = None


class RestAssuredMultiPartHandler:
    """Extract and transform multi-part form data from RestAssured tests."""
    
    def __init__(self):
        # Patterns for multi-part form data
        self.multipart_pattern = re.compile(
            r'\.multiPart\s*\(\s*([^)]+)\s*\)',
            re.DOTALL
        )
        self.file_multipart_pattern = re.compile(
            r'\.multiPart\s*\(\s*"([^"]+)"\s*,\s*new\s+File\s*\(\s*"([^"]+)"\s*\)\s*\)',
            re.DOTALL
        )
        self.contenttype_multipart_pattern = re.compile(
            r'\.multiPart\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)',
            re.DOTALL
        )
    
    def extract_multipart_fields(self, code: str) -> List[MultiPartFormData]:
        """
        Extract multi-part form fields from RestAssured code.
        
        Args:
            code: RestAssured test code
            
        Returns:
            List of MultiPartFormData objects
        """
        fields = []
        
        # Extract file multiparts: .multiPart("file", new File("path/to/file"))
        for match in self.file_multipart_pattern.finditer(code):
            field_name = match.group(1)
            file_path = match.group(2)
            
            fields.append(MultiPartFormData(
                field_name=field_name,
                file_path=file_path
            ))
        
        # Extract multiparts with content type: .multiPart("field", "value", "content/type")
        for match in self.contenttype_multipart_pattern.finditer(code):
            field_name = match.group(1)
            value = match.group(2)
            content_type = match.group(3)
            
            fields.append(MultiPartFormData(
                field_name=field_name,
                value=value,
                content_type=content_type
            ))
        
        return fields
    
    def has_multipart_upload(self, code: str) -> bool:
        """
        Check if code contains multi-part form upload.
        
        Args:
            code: RestAssured test code
            
        Returns:
            True if multi-part upload is present
        """
        return bool(self.multipart_pattern.search(code))
    
    def extract_from_test_method(
        self, 
        method_code: str,
        test_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract multi-part configuration from a test method.
        
        Args:
            method_code: Source code of test method
            test_name: Name of the test
            
        Returns:
            Dictionary with multi-part configuration or None
        """
        if not self.has_multipart_upload(method_code):
            return None
        
        fields = self.extract_multipart_fields(method_code)
        
        if not fields:
            return None
        
        return {
            'test_name': test_name,
            'fields': [
                {
                    'field_name': f.field_name,
                    'value': f.value,
                    'file_path': f.file_path,
                    'content_type': f.content_type,
                    'file_name': f.file_name
                }
                for f in fields
            ],
            'has_file_upload': any(f.file_path for f in fields)
        }
    
    def convert_to_robot_keywords(
        self, 
        multipart_config: Dict[str, Any]
    ) -> List[str]:
        """
        Convert multi-part configuration to Robot Framework keywords.
        
        Args:
            multipart_config: Multi-part configuration dictionary
            
        Returns:
            List of Robot Framework keyword lines
        """
        keywords = []
        
        for field in multipart_config['fields']:
            if field['file_path']:
                # File upload
                keywords.append(
                    f"    Upload File    {field['field_name']}    "
                    f"{field['file_path']}"
                )
            elif field['content_type']:
                # Field with content type
                keywords.append(
                    f"    Set Multipart Field    {field['field_name']}    "
                    f"{field['value']}    content_type={field['content_type']}"
                )
            else:
                # Simple field
                keywords.append(
                    f"    Set Multipart Field    {field['field_name']}    "
                    f"{field['value']}"
                )
        
        return keywords
    
    def generate_requests_library_code(
        self, 
        multipart_config: Dict[str, Any]
    ) -> str:
        """
        Generate Python requests library code for multi-part upload.
        
        Args:
            multipart_config: Multi-part configuration
            
        Returns:
            Python code string
        """
        files_dict = []
        data_dict = []
        
        for field in multipart_config['fields']:
            if field['file_path']:
                # File field
                files_dict.append(
                    f"    '{field['field_name']}': open('{field['file_path']}', 'rb')"
                )
            else:
                # Data field
                data_dict.append(
                    f"    '{field['field_name']}': '{field['value']}'"
                )
        
        code_parts = []
        if files_dict:
            code_parts.append(f"files = {{\n{',\\n'.join(files_dict)}\n}}")
        if data_dict:
            code_parts.append(f"data = {{\n{',\\n'.join(data_dict)}\n}}")
        
        return '\n'.join(code_parts)
