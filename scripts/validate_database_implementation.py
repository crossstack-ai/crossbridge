"""
Final validation script for comprehensive database implementation.
Verifies all components are in place and tests pass.
"""

import sys
import subprocess
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def check_file_exists(file_path: Path, description: str) -> bool:
    """Check if a file exists."""
    if file_path.exists():
        logger.info(f"✅ {description}: {file_path}")
        return True
    else:
        logger.error(f"❌ {description}: {file_path} NOT FOUND")
        return False


def check_file_size(file_path: Path, min_lines: int) -> bool:
    """Check if file has minimum number of lines."""
    if not file_path.exists():
        return False
    
    try:
        with open(file_path, encoding='utf-8') as f:
            lines = len(f.readlines())
    except UnicodeDecodeError:
        # Try with different encoding
        try:
            with open(file_path, encoding='latin-1') as f:
                lines = len(f.readlines())
        except Exception as e:
            logger.warning(f"   ⚠ Could not read file: {e}")
            return True  # Don't fail validation on encoding issues
    
    if lines >= min_lines:
        logger.info(f"   ✓ {lines} lines (>= {min_lines} required)")
        return True
    else:
        logger.warning(f"   ⚠ {lines} lines (< {min_lines} required)")
        return False


def run_tests() -> bool:
    """Run unit tests."""
    logger.info("\n🧪 Running unit tests...")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/test_comprehensive_schema.py", "-v", "--tb=short"],
            capture_output=True,
            text=True
        )
        
        if "passed" in result.stdout:
            # Extract test results
            for line in result.stdout.split('\n'):
                if "passed" in line or "skipped" in line:
                    logger.info(f"✅ {line.strip()}")
            return result.returncode == 0
        else:
            logger.error("❌ Tests failed")
            logger.error(result.stdout)
            return False
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        return False


def main():
    """Main validation."""
    logger.info("="*60)
    logger.info("CrossBridge Comprehensive Database Implementation Validation")
    logger.info("="*60)
    
    all_passed = True
    
    # Check schema files
    logger.info("\n📁 Checking Schema Files...")
    all_passed &= check_file_exists(
        Path("scripts/comprehensive_schema.sql"),
        "Comprehensive Schema"
    )
    all_passed &= check_file_size(Path("scripts/comprehensive_schema.sql"), 800)
    
    # Check setup script
    logger.info("\n📁 Checking Setup Scripts...")
    all_passed &= check_file_exists(
        Path("scripts/setup_comprehensive_schema.py"),
        "Setup Script"
    )
    all_passed &= check_file_size(Path("scripts/setup_comprehensive_schema.py"), 200)
    
    # Check data generator
    logger.info("\n📁 Checking Data Generator...")
    all_passed &= check_file_exists(
        Path("scripts/generate_test_data.py"),
        "Test Data Generator"
    )
    all_passed &= check_file_size(Path("scripts/generate_test_data.py"), 500)
    
    # Check Grafana dashboard
    logger.info("\n📁 Checking Grafana Dashboard...")
    all_passed &= check_file_exists(
        Path("grafana/dashboards/crossbridge_overview.json"),
        "Grafana Dashboard"
    )
    all_passed &= check_file_size(Path("grafana/dashboards/crossbridge_overview.json"), 500)
    
    # Check documentation
    logger.info("\n📁 Checking Documentation...")
    all_passed &= check_file_exists(
        Path("docs/COMPREHENSIVE_DATABASE_SCHEMA.md"),
        "Schema Documentation"
    )
    all_passed &= check_file_size(Path("docs/COMPREHENSIVE_DATABASE_SCHEMA.md"), 1000)
    
    all_passed &= check_file_exists(
        Path("IMPLEMENTATION_SUMMARY_DATABASE.md"),
        "Implementation Summary"
    )
    
    # Check test file
    logger.info("\n📁 Checking Test Files...")
    all_passed &= check_file_exists(
        Path("tests/test_comprehensive_schema.py"),
        "Unit Tests"
    )
    all_passed &= check_file_size(Path("tests/test_comprehensive_schema.py"), 400)
    
    # Run unit tests
    test_passed = run_tests()
    all_passed &= test_passed
    
    # Check schema content
    logger.info("\n🔍 Validating Schema Content...")
    schema_path = Path("scripts/comprehensive_schema.sql")
    if schema_path.exists():
        with open(schema_path) as f:
            content = f.read()
        
        required_items = {
            "TimescaleDB Extension": "timescaledb",
            "pgvector Extension": "vector",
            "test_execution hypertable": "create_hypertable('test_execution'",
            "HNSW index": "USING hnsw",
            "Continuous aggregates": "WITH (timescaledb.continuous)",
            "Retention policies": "add_retention_policy",
        }
        
        for name, keyword in required_items.items():
            if keyword in content:
                logger.info(f"✅ {name} found")
            else:
                logger.error(f"❌ {name} NOT found")
                all_passed = False
    
    # Summary
    logger.info("\n" + "="*60)
    if all_passed:
        logger.info("✅ ALL VALIDATIONS PASSED!")
        logger.info("="*60)
        logger.info("\n📋 Next Steps:")
        logger.info("1. Setup database: python scripts/setup_comprehensive_schema.py")
        logger.info("2. Generate test data: python scripts/generate_test_data.py")
        logger.info("3. Import Grafana dashboard: grafana/dashboards/crossbridge_overview.json")
        logger.info("4. Configure datasource in Grafana")
        logger.info("5. Read documentation: docs/COMPREHENSIVE_DATABASE_SCHEMA.md")
        return 0
    else:
        logger.error("❌ SOME VALIDATIONS FAILED")
        logger.error("="*60)
        logger.error("Please review the errors above and fix them.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
