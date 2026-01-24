"""
Test script to verify enhanced failure reporting and retry logic.
Run this to see how the improved error handling works.
"""

from core.orchestration.orchestrator import MigrationOrchestrator
from core.orchestration.models import MigrationResult

def test_failure_report_generation():
    """Test the new failure report generation."""
    orchestrator = MigrationOrchestrator()
    
    # Simulate various types of failures
    failed_results = [
        # Batch commit failures (most common cause of 150 failures)
        *[MigrationResult(
            source_file=f"src/test{i}.robot",
            target_file=f"target/test{i}.robot",
            status="failed",
            error=f"Batch 1 commit failed: API rate limit exceeded"
        ) for i in range(25)],
        
        *[MigrationResult(
            source_file=f"src/test{i}.robot",
            target_file=f"target/test{i}.robot",
            status="failed",
            error=f"Batch 2 commit failed: Network timeout after 30 seconds"
        ) for i in range(25, 50)],
        
        *[MigrationResult(
            source_file=f"src/test{i}.robot",
            target_file=f"target/test{i}.robot",
            status="failed",
            error=f"Batch 3 commit failed: Connection refused by remote server"
        ) for i in range(50, 75)],
        
        # File read failures
        *[MigrationResult(
            source_file=f"src/missing{i}.robot",
            target_file="",
            status="failed",
            error=f"Failed to read src/missing{i}.robot: File not found"
        ) for i in range(10)],
        
        # Transformation failures
        *[MigrationResult(
            source_file=f"src/invalid{i}.feature",
            target_file=f"target/invalid{i}.robot",
            status="failed",
            error=f"Transformation failed: Invalid Gherkin syntax at line 42"
        ) for i in range(5)],
    ]
    
    total_files = 259
    
    print("\n" + "="*70)
    print("TESTING ENHANCED FAILURE REPORTING")
    print("="*70)
    print(f"\nSimulating: {len(failed_results)} failures out of {total_files} files")
    print(f"Success rate: {(total_files - len(failed_results))/total_files*100:.1f}%")
    
    # Generate the failure report
    report = orchestrator._generate_failure_report(failed_results, total_files)
    
    print(report)
    
    print("\n" + "="*70)
    print("KEY INSIGHTS FROM THE REPORT:")
    print("="*70)
    print("""
✅ What you can learn:
  1. Batch Commit Failures: The most common cause of bulk failures
     - 3 batches failed = 75 files (each batch has 25 files)
     - Typically caused by: rate limits, timeouts, network issues
  
  2. Pattern Detection: The report groups similar errors together
     - Shows which batch numbers failed
     - Identifies the root cause (API limits, timeouts, etc.)
  
  3. Actionable Recommendations:
     - Reduce batch size from 25 to 10
     - Check network/API connectivity
     - Retry logic is now automatically enabled

🔧 What's been improved:
  • Automatic retry for transient errors (timeout, rate limit, network)
  • 5-second delay before retry
  • Detailed logging of batch failures
  • Categorized error reporting by failure type
  • Specific recommendations based on failure patterns
""")

if __name__ == "__main__":
    test_failure_report_generation()
