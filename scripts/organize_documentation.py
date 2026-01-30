"""
Script to organize root .md files into appropriate docs/ subdirectories.

This script moves implementation summaries, status docs, and other
documentation from the project root to organized folders under docs/.
"""

import os
import shutil
from pathlib import Path


# Define the organization structure
FILE_MAPPING = {
    # PostgreSQL and Database docs
    'POSTGRESQL_INTEGRATION_COMPLETE.md': 'docs/database/',
    
    # Intelligence system docs
    'EXECUTION_INTELLIGENCE_*.md': 'docs/intelligence/',
    'EXPLAINABILITY_IMPLEMENTATION_COMPLETE.md': 'docs/intelligence/',
    
    # Implementation status and summaries
    '*_IMPLEMENTATION_*.md': 'docs/project/implementation/',
    '*_COMPLETE*.md': 'docs/project/implementation/',
    '*_SUMMARY*.md': 'docs/project/summaries/',
    'FINAL_SUMMARY.md': 'docs/project/summaries/',
    
    # Configuration docs
    'UNIFIED_*.md': 'docs/configuration/',
    'CONFIG_*.md': 'docs/configuration/',
    'COMMON_INFRASTRUCTURE.md': 'docs/configuration/',
    
    # Profiling docs
    'PROFILING_*.md': 'docs/profiling/',
    
    # Framework support docs
    'FRAMEWORK_*.md': 'docs/frameworks/',
    
    # Project organization docs
    'DOT_FILES_ORGANIZATION.md': 'docs/project/',
    'FILE_MANIFEST.md': 'docs/project/',
    'CONSOLIDATION_*.md': 'docs/project/',
    
    # Testing docs
    'TEST_RESULTS_*.md': 'docs/testing/',
    
    # Drift detection (keep at root - active development)
    'DRIFT_IMPLEMENTATION_REVIEW.md': './',  # Keep at root
}


def create_directories():
    """Create necessary directories if they don't exist."""
    directories = {
        'docs/database',
        'docs/intelligence',
        'docs/project/implementation',
        'docs/project/summaries',
        'docs/configuration',
        'docs/profiling',
        'docs/frameworks',
        'docs/testing',
    }
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")


def move_file(source, destination_dir):
    """Move a file to destination directory."""
    source_path = Path(source)
    dest_dir = Path(destination_dir)
    dest_path = dest_dir / source_path.name
    
    if source_path.exists():
        if dest_path.exists():
            print(f"⚠ Skipping {source} (already exists at destination)")
            return False
        
        shutil.move(str(source_path), str(dest_path))
        print(f"✓ Moved: {source} → {dest_path}")
        return True
    else:
        print(f"✗ Not found: {source}")
        return False


def organize_files():
    """Organize all root .md files according to mapping."""
    import glob
    
    moved_count = 0
    skipped_count = 0
    
    # Get all .md files in root
    root_md_files = glob.glob('*.md')
    
    # Exclude files we want to keep at root
    keep_at_root = {
        'README.md',
        'LICENSE',
        'CHANGELOG.md',
        'DRIFT_IMPLEMENTATION_REVIEW.md',  # Current active doc
    }
    
    files_to_move = [f for f in root_md_files if f not in keep_at_root]
    
    print(f"\nFound {len(files_to_move)} .md files to organize")
    print(f"Keeping {len(keep_at_root)} files at root")
    print()
    
    # Create directory structure
    create_directories()
    print()
    
    # Move files based on patterns
    for filename in files_to_move:
        moved = False
        
        # Check specific mappings first
        for pattern, dest_dir in FILE_MAPPING.items():
            if '*' in pattern:
                # Pattern matching
                pattern_parts = pattern.split('*')
                if all(part in filename for part in pattern_parts if part):
                    if move_file(filename, dest_dir):
                        moved_count += 1
                    else:
                        skipped_count += 1
                    moved = True
                    break
            else:
                # Exact match
                if filename == pattern:
                    if move_file(filename, dest_dir):
                        moved_count += 1
                    else:
                        skipped_count += 1
                    moved = True
                    break
        
        # Default fallback - move to docs/project/
        if not moved:
            print(f"⚠ No specific mapping for {filename}, moving to docs/project/")
            if move_file(filename, 'docs/project/'):
                moved_count += 1
            else:
                skipped_count += 1
    
    print()
    print("=" * 60)
    print(f"✓ Moved: {moved_count} files")
    print(f"⚠ Skipped: {skipped_count} files")
    print("=" * 60)


def create_index_file():
    """Create an index file documenting the organization."""
    index_content = """# Documentation Organization Index

## Directory Structure

### `docs/database/`
- PostgreSQL integration and setup guides
- Database configuration documentation

### `docs/intelligence/`
- Execution intelligence system
- Explainability features
- Drift detection and analysis
- AI-powered insights

### `docs/project/`
- Project organization and structure
- File manifests and maps

#### `docs/project/implementation/`
- Implementation status reports
- Feature completion summaries
- Development progress tracking

#### `docs/project/summaries/`
- Consolidated summaries
- Final status reports
- Review documents

### `docs/configuration/`
- Configuration guides
- crossbridge.yml documentation
- Environment setup
- Common infrastructure

### `docs/profiling/`
- Performance profiling
- Benchmarking results
- Optimization guides

### `docs/frameworks/`
- Framework support documentation
- Adapter guides
- Multi-framework compatibility

### `docs/testing/`
- Test results and reports
- Test suite documentation
- Quality assurance

## Files Kept at Root

- `README.md` - Main project documentation
- `LICENSE` - License information
- `CHANGELOG.md` - Version history (if exists)
- `DRIFT_IMPLEMENTATION_REVIEW.md` - Current active development doc

## Migration Date

Organized on: January 30, 2026
"""
    
    with open('docs/DOCUMENTATION_INDEX.md', 'w') as f:
        f.write(index_content)
    
    print("✓ Created documentation index: docs/DOCUMENTATION_INDEX.md")


if __name__ == '__main__':
    print("=" * 60)
    print("CrossBridge Documentation Organization Script")
    print("=" * 60)
    print()
    
    # Confirm before proceeding
    response = input("This will move .md files from root to docs/. Continue? (y/n): ")
    
    if response.lower() == 'y':
        organize_files()
        create_index_file()
        print("\n✓ Documentation organization complete!")
        print("\nNext steps:")
        print("1. Review moved files in docs/ subdirectories")
        print("2. Update any broken relative links")
        print("3. Run link checker: markdown-link-check docs/**/*.md")
        print("4. Commit changes to git")
    else:
        print("Operation cancelled.")
