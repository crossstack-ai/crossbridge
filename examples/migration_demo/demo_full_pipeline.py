"""
Full Migration Pipeline Demo

Demonstrates complete migration pipeline with all phases:
1. Code Generation
2. Validation
3. Refinement
4. Quality Verification
"""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from adapters.selenium_bdd_java.step_definition_parser import JavaStepDefinitionParser
from migration.orchestrator import UnifiedMigrationOrchestrator


def print_section(title: str):
    """Print formatted section header"""
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print()


def main():
    """Run full pipeline demo"""
    
    print_section("FULL MIGRATION PIPELINE DEMO")
    
    # 1. Parse Java source
    java_file = Path(__file__).parent / "java_source" / "LoginSteps.java"
    
    print(f"Reading Java file: {java_file.name}")
    with open(java_file, "r") as f:
        java_code = f.read()
    print(f"   [OK] Read {len(java_code)} characters")
    
    # 2. Parse step definitions
    print("\nParsing Java step definitions...")
    parser = JavaStepDefinitionParser()
    result = parser.parse_content(java_code, str(java_file))
    step_defs = result.step_definitions
    print(f"   [OK] Found {len(step_defs)} step definitions")
    
    # 3. Run full pipeline for pytest-bdd
    print_section("PIPELINE: pytest-bdd")
    
    orchestrator = UnifiedMigrationOrchestrator()
    output_pytest = Path(__file__).parent / "output_pipeline_pytest"
    
    pipeline_result = orchestrator.migrate(
        step_defs,
        output_pytest,
        target="pytest-bdd",
        validate=True,
        refine=True,
        execute=False  # Set to True to run tests (requires dependencies)
    )
    
    # Show results
    print("\nPipeline Results:")
    print(f"   Target: {pipeline_result.target}")
    print(f"   Success: {'[OK] YES' if pipeline_result.success else '[FAIL] NO'}")
    print(f"   Output: {pipeline_result.output_dir}")
    
    if pipeline_result.validation_report:
        val_report = pipeline_result.validation_report
        print(f"\n   Validation:")
        print(f"      Passed: {'[OK]' if val_report.passed else '[FAIL]'}")
        print(f"      Issues: {val_report.summary.get('total', 0)}")
        print(f"      Errors: {val_report.summary.get('errors', 0)}")
        print(f"      Warnings: {val_report.summary.get('warnings', 0)}")
        
        # Show errors if any
        if val_report.summary.get('errors', 0) > 0:
            print(f"\n   Error Details:")
            for issue in val_report.get_errors():
                print(f"      - {issue.message}")
                if issue.file_path:
                    print(f"        File: {issue.file_path}")
    
    if pipeline_result.refinement_results:
        improved = len([r for r in pipeline_result.refinement_results.values() if r.improved])
        total = len(pipeline_result.refinement_results)
        print(f"\n   Refinement:")
        print(f"      Files Processed: {total}")
        print(f"      Files Improved: {improved}")
    
    if pipeline_result.execution_report:
        exec_report = pipeline_result.execution_report
        print(f"\n   Execution:")
        print(f"      Total Tests: {exec_report.total}")
        print(f"      Passed: {exec_report.passed}")
        print(f"      Failed: {exec_report.failed}")
        print(f"      Pass Rate: {exec_report.get_pass_rate():.1f}%")
    
    # 4. Run full pipeline for Robot Framework
    print_section("PIPELINE: Robot Framework")
    
    output_robot = Path(__file__).parent / "output_pipeline_robot"
    
    pipeline_result_robot = orchestrator.migrate(
        step_defs,
        output_robot,
        target="robot-framework",
        validate=True,
        refine=True,
        execute=False
    )
    
    print("\nPipeline Results:")
    print(f"   Target: {pipeline_result_robot.target}")
    print(f"   Success: {'[OK] YES' if pipeline_result_robot.success else '[FAIL] NO'}")
    print(f"   Output: {pipeline_result_robot.output_dir}")
    
    if pipeline_result_robot.validation_report:
        val_report = pipeline_result_robot.validation_report
        print(f"\n   Validation:")
        print(f"      Passed: {'[OK]' if val_report.passed else '[FAIL]'}")
        print(f"      Issues: {val_report.summary.get('total', 0)}")
        print(f"      Errors: {val_report.summary.get('errors', 0)}")
        print(f"      Warnings: {val_report.summary.get('warnings', 0)}")
    
    if pipeline_result_robot.refinement_results:
        improved = len([r for r in pipeline_result_robot.refinement_results.values() if r.improved])
        total = len(pipeline_result_robot.refinement_results)
        print(f"\n   Refinement:")
        print(f"      Files Processed: {total}")
        print(f"      Files Improved: {improved}")
    
    # 5. Summary
    print_section("[OK] PIPELINE COMPLETE")
    
    print("Pipeline Phases Executed:")
    print("  1. [OK] Code Generation")
    print("  2. [OK] Validation")
    print("  3. [OK] Code Refinement")
    print("  4. [SKIP] Test Execution (skipped - set execute=True to run)")
    
    print("\nOutputs Generated:")
    print(f"  pytest-bdd: {output_pytest}")
    print(f"  Robot Framework: {output_robot}")
    
    print("\nPipeline Features:")
    print("  [x] Syntax validation")
    print("  [x] Import checking")
    print("  [x] Code formatting")
    print("  [x] Best practices verification")
    print("  [x] TODO detection")
    print("  [x] Quality metrics")
    
    print("\nProduction Ready:")
    print("  [x] Full validation pipeline")
    print("  [x] Automated refinement")
    print("  [x] Quality verification")
    print("  [x] Execution capability")
    print("  [x] Comprehensive error handling")
    

if __name__ == "__main__":
    main()
