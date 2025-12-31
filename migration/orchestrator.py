"""
Unified Migration Orchestrator

Provides a single interface for migrating Java Selenium BDD to:
- Python Playwright with pytest-bdd
- Python Playwright with Robot Framework

Includes full pipeline: generation → validation → refinement → execution
"""

from pathlib import Path
from typing import List, Literal, Dict, Optional
from dataclasses import dataclass, field

from adapters.selenium_bdd_java.step_definition_parser import StepDefinitionIntent
from migration.generators.playwright_generator import (
    MigrationOrchestrator as PytestMigrationOrchestrator
)
from migration.generators.robot_generator import (
    RobotMigrationOrchestrator
)


MigrationMode = Literal["pytest-bdd", "robot-framework"]


@dataclass
class MigrationPipelineResult:
    """Complete pipeline result with all phases"""
    target: str
    output_dir: str
    generation_result: dict
    validation_report: Optional[object] = None
    refinement_results: Optional[Dict] = None
    execution_report: Optional[object] = None
    success: bool = True
    errors: List[str] = field(default_factory=list)


class UnifiedMigrationOrchestrator:
    """
    Unified orchestrator for Java BDD migration.
    
    Supports multiple target frameworks:
    - pytest-bdd: Python Playwright with pytest-bdd
    - robot-framework: Robot Framework with Browser library
    
    Full pipeline includes:
    - Code generation
    - Validation
    - Refinement
    - Automated execution (optional)
    """
    
    def __init__(self):
        self.pytest_orchestrator = PytestMigrationOrchestrator()
        self.robot_orchestrator = RobotMigrationOrchestrator()
        
        # Import validation, refinement, execution modules
        try:
            from migration.validation import MigrationValidator
            from migration.refinement import CodeRefiner
            from migration.execution import TestExecutor
            
            self.validator = MigrationValidator()
            self.refiner = CodeRefiner()
            self.executor = TestExecutor()
            self.full_pipeline_available = True
        except ImportError:
            self.validator = None
            self.refiner = None
            self.executor = None
            self.full_pipeline_available = False
    
    def migrate(
        self,
        java_step_defs: List[StepDefinitionIntent],
        output_dir: Path,
        target: MigrationMode = "pytest-bdd",
        mode: str = "assistive",
        validate: bool = True,
        refine: bool = True,
        execute: bool = False,
        dry_run: bool = False
    ) -> MigrationPipelineResult:
        """
        Migrate Java step definitions to target framework with full pipeline.
        
        Args:
            java_step_defs: Parsed Java step definitions
            output_dir: Output directory for generated files
            target: Target framework ("pytest-bdd" or "robot-framework")
            mode: "assistive" (with TODOs) or "auto" (full generation)
            validate: Run validation phase
            refine: Run code refinement phase
            execute: Run automated test execution (requires dependencies)
            dry_run: If execute=True, perform dry run only
        
        Returns:
            MigrationPipelineResult with all phase results
        """
        pipeline_result = MigrationPipelineResult(
            target=target,
            output_dir=str(output_dir),
            generation_result={}
        )
        
        try:
            # Phase 1: Generate Code
            print(f"\nPhase 1: Generating {target} code...")
            if target == "pytest-bdd":
                gen_result = self._migrate_to_pytest(java_step_defs, output_dir, mode)
            elif target == "robot-framework":
                gen_result = self._migrate_to_robot(java_step_defs, output_dir)
            else:
                raise ValueError(f"Unsupported target: {target}")
            
            pipeline_result.generation_result = gen_result
            print(f"[OK] Code generation complete")
            
            # Phase 2: Validate (if enabled)
            if validate and self.validator:
                print(f"\nPhase 2: Validating generated code...")
                if target == "pytest-bdd":
                    validation_report = self.validator.validate_pytest_migration(output_dir)
                else:
                    validation_report = self.validator.validate_robot_migration(output_dir)
                
                pipeline_result.validation_report = validation_report
                
                if validation_report.passed:
                    print(f"[OK] Validation passed ({validation_report.summary['total']} checks)")
                else:
                    print(f"[WARN] Validation found issues: {validation_report.summary['errors']} errors, {validation_report.summary['warnings']} warnings")
                    if validation_report.summary['errors'] > 0:
                        pipeline_result.success = False
                        pipeline_result.errors.append("Validation failed with errors")
            
            # Phase 3: Refine (if enabled)
            if refine and self.refiner:
                print(f"\nPhase 3: Refining code quality...")
                if target == "pytest-bdd":
                    refinement_results = self.refiner.refine_pytest_migration(output_dir)
                else:
                    refinement_results = self.refiner.refine_robot_migration(output_dir)
                
                pipeline_result.refinement_results = refinement_results
                improved_count = len([r for r in refinement_results.values() if r.improved])
                print(f"[OK] Code refinement complete ({improved_count} files improved)")
            
            # Phase 4: Execute Tests (if enabled)
            if execute and self.executor:
                print(f"\n🧪 Phase 4: Executing tests...")
                execution_report = self.executor.execute(
                    output_dir,
                    target,
                    dry_run=dry_run
                )
                pipeline_result.execution_report = execution_report
                
                if execution_report.passed > 0:
                    print(f"[OK] Tests executed: {execution_report.passed}/{execution_report.total} passed")
                else:
                    print(f"[WARN] Test execution: {execution_report.errors + execution_report.failed} issues")
                    if execution_report.errors > 0:
                        pipeline_result.errors.append("Test execution had errors")
            
            return pipeline_result
            
        except Exception as e:
            pipeline_result.success = False
            pipeline_result.errors.append(f"Pipeline failed: {str(e)}")
            print(f"\n❌ Migration pipeline failed: {e}")
            return pipeline_result
    
    def _migrate_to_pytest(
        self,
        java_step_defs: List[StepDefinitionIntent],
        output_dir: Path,
        mode: str
    ) -> dict:
        """Migrate to pytest-bdd"""
        suite = self.pytest_orchestrator.migrate_step_definitions(
            java_step_defs,
            output_dir,
            mode=mode
        )
        
        self.pytest_orchestrator.write_migration_output(suite, output_dir)
        
        return {
            "target": "pytest-bdd",
            "step_definitions": len(suite.step_definitions),
            "page_objects": len(suite.page_objects),
            "output_dir": str(output_dir),
            "files": {
                "page_objects": [f"{po.class_name.lower()}.py" for po in suite.page_objects],
                "step_definitions": ["test_steps.py"],
                "fixtures": ["conftest.py"]
            }
        }
    
    def _migrate_to_robot(
        self,
        java_step_defs: List[StepDefinitionIntent],
        output_dir: Path
    ) -> dict:
        """Migrate to Robot Framework"""
        suite = self.robot_orchestrator.migrate_step_definitions(
            java_step_defs,
            output_dir
        )
        
        self.robot_orchestrator.write_migration_output(suite, output_dir)
        
        return {
            "target": "robot-framework",
            "test_cases": len(suite.test_cases),
            "resources": len(suite.resources),
            "output_dir": str(output_dir),
            "files": {
                "resources": [f"{r.resource_name}.robot" for r in suite.resources],
                "tests": ["test_suite.robot"],
                "readme": ["README.md"]
            }
        }
    
    def get_supported_targets(self) -> List[MigrationMode]:
        """Get list of supported migration targets"""
        return ["pytest-bdd", "robot-framework"]
    
    def get_target_info(self, target: MigrationMode) -> dict:
        """Get information about a migration target"""
        info = {
            "pytest-bdd": {
                "name": "pytest-bdd",
                "description": "Python Playwright with pytest-bdd",
                "framework": "pytest",
                "browser_library": "playwright",
                "bdd_library": "pytest-bdd",
                "file_extension": ".py",
                "install_command": "pip install pytest pytest-bdd playwright",
                "run_command": "pytest tests/",
                "features": [
                    "Page Object pattern",
                    "pytest fixtures",
                    "Playwright async/sync API",
                    "Python type hints",
                    "pytest parametrization"
                ]
            },
            "robot-framework": {
                "name": "robot-framework",
                "description": "Robot Framework with Browser library",
                "framework": "Robot Framework",
                "browser_library": "robotframework-browser (Playwright-based)",
                "bdd_library": "Built-in Robot Framework keywords",
                "file_extension": ".robot",
                "install_command": "pip install robotframework robotframework-browser && rfbrowser init",
                "run_command": "robot tests/",
                "features": [
                    "Keyword-driven testing",
                    "Resource files (Page Objects)",
                    "Built-in reporting",
                    "Tag-based execution",
                    "Data-driven testing"
                ]
            }
        }
        
        return info.get(target, {})
