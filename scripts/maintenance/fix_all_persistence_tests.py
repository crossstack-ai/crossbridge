"""
Comprehensive fix for all persistence unit tests.
Converts integer ID expectations to UUID expectations.
"""

import re
import uuid

def fix_test_file(filepath):
    """Fix a single test file."""
    print(f"Processing {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add uuid import if not present
    if 'import uuid' not in content:
        content = content.replace('import pytest', 'import pytest\nimport uuid')
    
    # Fix all integer ID usages in function calls - use UUID
    # Pattern: function_name(mock_session, 123) -> function_name(mock_session, uuid.uuid4())
    content = re.sub(
        r'(get_discovery_run|get_mapping_by_id|find_page_object|find_test_case)\(([^,]+),\s*\d+\)',
        r'\1(\2, uuid.uuid4())',
        content
    )
    
    # Fix isinstance checks from int to uuid.UUID
    content = re.sub(
        r'assert isinstance\(([^,]+),\s*int\)',
        r'assert isinstance(\1, uuid.UUID)',
        content
    )
    
    # Fix test method names from *_returns_int to *_returns_uuid
    content = re.sub(
        r'def (test_\w+_returns)_int\(',
        r'def \1_uuid(',
        content
    )
    
    # Fix docstrings mentioning "integer"
    content = re.sub(
        r'returns an integer',
        'returns a UUID',
        content,
        flags=re.IGNORECASE
    )
    
    content = re.sub(
        r'returns int',
        'returns UUID',
        content
    )
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✓ Fixed {filepath}")

def main():
    """Fix all persistence test files."""
    test_files = [
        'tests/unit/persistence/test_discovery_repo.py',
        'tests/unit/persistence/test_mapping_repo.py',
        'tests/unit/persistence/test_page_object_repo.py',
        'tests/unit/persistence/test_test_case_repo.py',
        'tests/unit/persistence/test_orchestrator.py'
    ]
    
    for filepath in test_files:
        try:
            fix_test_file(filepath)
        except Exception as e:
            print(f"  ✗ Error fixing {filepath}: {e}")
    
    print("\n✓ All files processed!")

if __name__ == "__main__":
    main()
