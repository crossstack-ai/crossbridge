"""
Script to fix all persistence test mocks to use tuple structures.

This script systematically updates all persistence test files to use proper tuple structures
instead of MagicMock objects with attributes.
"""

import re
import sys
from pathlib import Path

def main():
    """Fix all persistence test mocks."""
    test_dir = Path("tests/unit/persistence")
    
    # Files to fix (discovery_repo is already mostly done)
    files_to_fix = [
        test_dir / "test_mapping_repo.py",
        test_dir / "test_page_object_repo.py",
        test_dir / "test_test_case_repo.py",
        test_dir / "test_orchestrator.py",
    ]
    
    summary = {
        "total_files": len(files_to_fix),
        "fixed_files": 0,
        "failed_files": [],
    }
    
    for file_path in files_to_fix:
        if not file_path.exists():
            print(f"⚠️  Skipping {file_path} - does not exist")
            continue
            
        print(f"\n📝 Processing {file_path.name}...")
        
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            
            # Fix patterns will go here
            # For now, just report what needs fixing
            
            # Check what kind of mocks are being used
            has_magic_mock_rows = "MagicMock(" in content and "id=" in content
            has_fetchone = "fetchone" in content
            has_fetchall = "fetchall" in content
            has_scalar = "scalar" in content
            
            print(f"  - Has MagicMock rows: {has_magic_mock_rows}")
            print(f"  - Has fetchone: {has_fetchone}")
            print(f"  - Has fetchall: {has_fetchall}")
            print(f"  - Has scalar: {has_scalar}")
            
            if content != original_content:
                file_path.write_text(content, encoding='utf-8')
                print(f"✅ Fixed {file_path.name}")
                summary["fixed_files"] += 1
            else:
                print(f"ℹ️  No changes needed for {file_path.name}")
                
        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")
            summary["failed_files"].append(str(file_path))
    
    # Print summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"Total files: {summary['total_files']}")
    print(f"Fixed files: {summary['fixed_files']}")
    print(f"Failed files: {len(summary['failed_files'])}")
    
    if summary["failed_files"]:
        print("\n❌ Failed files:")
        for failed in summary["failed_files"]:
            print(f"  - {failed}")
    
    return 0 if not summary["failed_files"] else 1

if __name__ == "__main__":
    sys.exit(main())
