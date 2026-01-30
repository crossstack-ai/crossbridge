"""
Framework Adapters

Adapters translate ExecutionPlan into framework-specific invocations.

Key principle: Adapters invoke frameworks via CLI, never replacing them.
Each adapter knows how to:
1. Generate framework-specific inputs (suite files, filters, tags)
2. Construct CLI commands
3. Parse framework outputs into ExecutionResult

Supported frameworks (13 total):
- Java: TestNG, JUnit 4/5, RestAssured, Cucumber
- Python: Pytest, Robot Framework, Behave
- JavaScript/TypeScript: Cypress, Playwright
- .NET: NUnit, SpecFlow
- BDD: Cucumber (Java), Behave (Python), SpecFlow (.NET)
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional
import subprocess
import logging
import json
import xml.etree.ElementTree as ET
from datetime import datetime

from .api import ExecutionPlan, ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


class FrameworkAdapter(ABC):
    """
    Base adapter for framework execution.
    
    Adapters are stateless - they just translate plans to commands.
    """
    
    def __init__(self, framework_name: str):
        self.framework_name = framework_name
    
    @abstractmethod
    def plan_to_command(self, plan: ExecutionPlan, workspace: Path) -> List[str]:
        """
        Convert execution plan to framework CLI command.
        
        Args:
            plan: Execution plan with selected tests
            workspace: Path to project workspace
            
        Returns:
            List of command parts (for subprocess)
        """
        pass
    
    @abstractmethod
    def parse_result(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        """
        Parse framework output into ExecutionResult.
        
        Args:
            plan: Original execution plan
            workspace: Path to project workspace
            
        Returns:
            ExecutionResult with standardized data
        """
        pass
    
    def execute(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        """
        Execute the plan (main entry point).
        
        This handles the full lifecycle:
        1. Generate inputs
        2. Run command
        3. Parse outputs
        """
        start_time = datetime.utcnow()
        
        try:
            # Generate command
            command = self.plan_to_command(plan, workspace)
            logger.info(f"Executing: {' '.join(command)}")
            
            # Execute
            result = subprocess.run(
                command,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=plan.max_duration_minutes * 60 if plan.max_duration_minutes else None
            )
            
            # Parse result
            execution_result = self.parse_result(plan, workspace)
            execution_result.start_time = start_time
            execution_result.end_time = datetime.utcnow()
            execution_result.execution_time_seconds = (
                execution_result.end_time - start_time
            ).total_seconds()
            
            # Check status
            if result.returncode != 0 and not execution_result.has_failures():
                execution_result.status = ExecutionStatus.FAILED
                execution_result.error_message = f"Command failed with code {result.returncode}"
            
            return execution_result
            
        except subprocess.TimeoutExpired:
            logger.error(f"Execution timeout after {plan.max_duration_minutes} minutes")
            return self._create_timeout_result(plan, start_time)
        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            return self._create_error_result(plan, start_time, str(e))
    
    def _create_timeout_result(self, plan: ExecutionPlan, start_time: datetime) -> ExecutionResult:
        """Create result for timeout"""
        return ExecutionResult(
            executed_tests=[],
            passed_tests=[],
            failed_tests=[],
            skipped_tests=plan.selected_tests,
            error_tests=[],
            execution_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
            start_time=start_time,
            end_time=datetime.utcnow(),
            report_paths=[],
            log_paths=[],
            framework=plan.framework,
            environment=plan.environment,
            status=ExecutionStatus.FAILED,
            error_message=f"Execution timeout after {plan.max_duration_minutes} minutes"
        )
    
    def _create_error_result(
        self,
        plan: ExecutionPlan,
        start_time: datetime,
        error: str
    ) -> ExecutionResult:
        """Create result for error"""
        return ExecutionResult(
            executed_tests=[],
            passed_tests=[],
            failed_tests=[],
            skipped_tests=plan.selected_tests,
            error_tests=[],
            execution_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
            start_time=start_time,
            end_time=datetime.utcnow(),
            report_paths=[],
            log_paths=[],
            framework=plan.framework,
            environment=plan.environment,
            status=ExecutionStatus.FAILED,
            error_message=error
        )


class TestNGAdapter(FrameworkAdapter):
    """
    TestNG adapter for Java-based testing.
    
    Invokes TestNG via Maven or Gradle.
    Supports:
    - Group-based execution
    - Suite XML generation
    - Parallel execution
    """
    
    def __init__(self):
        super().__init__("testng")
        self.build_tool = "mvn"  # or "gradle"
    
    def plan_to_command(self, plan: ExecutionPlan, workspace: Path) -> List[str]:
        """Generate Maven/Gradle command"""
        
        # Option 1: Use groups (if tests have @Test(groups="..."))
        if self._can_use_groups(plan):
            groups = self._extract_groups(plan)
            return [
                self.build_tool,
                "test",
                f"-Dgroups={','.join(groups)}",
                f"-Denvironment={plan.environment}",
            ]
        
        # Option 2: Generate suite XML (more flexible)
        suite_path = self._generate_suite_xml(plan, workspace)
        command = [
            self.build_tool,
            "test",
            f"-DsuiteXmlFile={suite_path}",
            f"-Denvironment={plan.environment}",
        ]
        
        if plan.parallel:
            command.append("-Dparallel=methods")
            command.append("-DthreadCount=4")
        
        return command
    
    def _can_use_groups(self, plan: ExecutionPlan) -> bool:
        """Check if we can use TestNG groups"""
        # Simple heuristic: if all tests have group metadata
        return all("group" in test for test in plan.selected_tests)
    
    def _extract_groups(self, plan: ExecutionPlan) -> List[str]:
        """Extract unique groups from selected tests"""
        groups = set()
        for test in plan.selected_tests:
            # Extract group from test metadata
            # Format: "com.tests.LoginTest[group=auth]"
            if "[group=" in test:
                group = test.split("[group=")[1].rstrip("]")
                groups.add(group)
        return list(groups)
    
    def _generate_suite_xml(self, plan: ExecutionPlan, workspace: Path) -> Path:
        """Generate TestNG suite XML"""
        suite = ET.Element("suite", name="Crossbridge Suite", parallel="methods" if plan.parallel else "false")
        test = ET.SubElement(suite, "test", name=f"{plan.strategy.value.title()} Tests")
        classes = ET.SubElement(test, "classes")
        
        for test_class in plan.selected_tests:
            # Clean test class name (remove any metadata)
            class_name = test_class.split("[")[0]
            ET.SubElement(classes, "class", name=class_name)
        
        # Write to file
        suite_path = workspace / "target" / "crossbridge-suite.xml"
        suite_path.parent.mkdir(parents=True, exist_ok=True)
        
        tree = ET.ElementTree(suite)
        tree.write(suite_path, encoding="utf-8", xml_declaration=True)
        
        logger.info(f"Generated TestNG suite: {suite_path}")
        return suite_path
    
    def parse_result(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        """Parse TestNG XML reports"""
        report_dir = workspace / "target" / "surefire-reports"
        
        executed = []
        passed = []
        failed = []
        skipped = []
        errors = []
        
        # Parse TestNG results XML
        for xml_file in report_dir.glob("TEST-*.xml"):
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            for testcase in root.findall(".//testcase"):
                name = f"{testcase.get('classname')}.{testcase.get('name')}"
                executed.append(name)
                
                if testcase.find("failure") is not None:
                    failed.append(name)
                elif testcase.find("error") is not None:
                    errors.append(name)
                elif testcase.find("skipped") is not None:
                    skipped.append(name)
                else:
                    passed.append(name)
        
        return ExecutionResult(
            executed_tests=executed,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            error_tests=errors,
            execution_time_seconds=0,  # Will be set by execute()
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            report_paths=[str(p) for p in report_dir.glob("*.xml")],
            log_paths=[str(p) for p in report_dir.glob("*.txt")],
            framework="testng",
            environment=plan.environment,
        )


class RobotAdapter(FrameworkAdapter):
    """
    Robot Framework adapter.
    
    Invokes Robot via CLI with tag-based filtering.
    Very clean integration - Robot is designed for this.
    """
    
    def __init__(self):
        super().__init__("robot")
    
    def plan_to_command(self, plan: ExecutionPlan, workspace: Path) -> List[str]:
        """Generate robot command"""
        command = ["robot"]
        
        # Add tags for selected tests
        # Robot tests are typically files or tags
        if self._can_use_tags(plan):
            tags = self._extract_tags(plan)
            for tag in tags:
                command.extend(["--include", tag])
        else:
            # Add specific test files
            command.extend(plan.selected_tests)
        
        # Add variables
        command.extend(["--variable", f"ENV:{plan.environment}"])
        
        # Output directory
        output_dir = workspace / "robot-results"
        output_dir.mkdir(parents=True, exist_ok=True)
        command.extend(["--outputdir", str(output_dir)])
        
        # Parallel execution (requires pabot)
        if plan.parallel:
            command = ["pabot", "--processes", "4"] + command[1:]
        
        # Test directory
        command.append("tests/")
        
        return command
    
    def _can_use_tags(self, plan: ExecutionPlan) -> bool:
        """Check if we can use Robot tags"""
        return any("@" in test or "tag:" in test for test in plan.selected_tests)
    
    def _extract_tags(self, plan: ExecutionPlan) -> List[str]:
        """Extract tags from test identifiers"""
        tags = set()
        for test in plan.selected_tests:
            if "tag:" in test:
                tag = test.split("tag:")[1]
                tags.add(tag)
        return list(tags)
    
    def parse_result(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        """Parse Robot output.xml"""
        output_xml = workspace / "robot-results" / "output.xml"
        
        if not output_xml.exists():
            logger.error("Robot output.xml not found")
            return self._create_error_result(
                plan, datetime.utcnow(), "output.xml not found"
            )
        
        tree = ET.parse(output_xml)
        root = tree.getroot()
        
        executed = []
        passed = []
        failed = []
        skipped = []
        
        for test in root.findall(".//test"):
            name = test.get("name")
            executed.append(name)
            
            status = test.find("status")
            if status.get("status") == "PASS":
                passed.append(name)
            elif status.get("status") == "FAIL":
                failed.append(name)
            else:
                skipped.append(name)
        
        return ExecutionResult(
            executed_tests=executed,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            error_tests=[],
            execution_time_seconds=0,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            report_paths=[str(output_xml)],
            log_paths=[str(workspace / "robot-results" / "log.html")],
            framework="robot",
            environment=plan.environment,
        )


class PytestAdapter(FrameworkAdapter):
    """
    Pytest adapter for Python testing.
    
    Invokes pytest with marker-based or path-based filtering.
    """
    
    def __init__(self):
        super().__init__("pytest")
    
    def plan_to_command(self, plan: ExecutionPlan, workspace: Path) -> List[str]:
        """Generate pytest command"""
        command = ["pytest"]
        
        # Add markers (if using @pytest.mark.smoke, etc.)
        if self._can_use_markers(plan):
            markers = self._extract_markers(plan)
            command.extend(["-m", " or ".join(markers)])
        else:
            # Add specific test files/functions
            command.extend(plan.selected_tests)
        
        # Environment variable
        command.extend(["--env", plan.environment])
        
        # Parallel execution
        if plan.parallel:
            command.extend(["-n", "4"])  # Requires pytest-xdist
        
        # Output
        command.extend(["--junitxml", "pytest-results.xml"])
        command.extend(["--html", "pytest-report.html"])
        
        return command
    
    def _can_use_markers(self, plan: ExecutionPlan) -> bool:
        """Check if we can use pytest markers"""
        return any("@" in test or "marker:" in test for test in plan.selected_tests)
    
    def _extract_markers(self, plan: ExecutionPlan) -> List[str]:
        """Extract pytest markers"""
        markers = set()
        for test in plan.selected_tests:
            if "marker:" in test:
                marker = test.split("marker:")[1]
                markers.add(marker)
        return list(markers)
    
    def parse_result(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        """Parse pytest JUnit XML"""
        junit_xml = workspace / "pytest-results.xml"
        
        if not junit_xml.exists():
            logger.error("pytest JUnit XML not found")
            return self._create_error_result(
                plan, datetime.utcnow(), "pytest-results.xml not found"
            )
        
        tree = ET.parse(junit_xml)
        root = tree.getroot()
        
        executed = []
        passed = []
        failed = []
        skipped = []
        errors = []
        
        for testcase in root.findall(".//testcase"):
            name = f"{testcase.get('classname')}.{testcase.get('name')}"
            executed.append(name)
            
            if testcase.find("failure") is not None:
                failed.append(name)
            elif testcase.find("error") is not None:
                errors.append(name)
            elif testcase.find("skipped") is not None:
                skipped.append(name)
            else:
                passed.append(name)
        
        return ExecutionResult(
            executed_tests=executed,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            error_tests=errors,
            execution_time_seconds=0,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            report_paths=[str(junit_xml), str(workspace / "pytest-report.html")],
            log_paths=[],
            framework="pytest",
            environment=plan.environment,
        )


class RestAssuredAdapter(FrameworkAdapter):
    """RestAssured + Java API testing adapter (TestNG or JUnit 5)"""
    
    def __init__(self):
        super().__init__("restassured")
    
    def plan_to_command(self, plan: ExecutionPlan, workspace: Path) -> List[str]:
        """Generate Maven/Gradle command for RestAssured tests"""
        # Detect build tool (similar to TestNG)
        if (workspace / "pom.xml").exists():
            command = ["mvn", "test"]
            if plan.selected_tests:
                tests = ",".join([t.split(".")[-1] for t in plan.selected_tests])
                command.append(f"-Dtest={tests}")
        else:
            command = ["./gradlew", "test"]
            if plan.selected_tests:
                tests = " or ".join([f"*{t.split('.')[-1]}" for t in plan.selected_tests])
                command.append(f"--tests={tests}")
        
        command.extend([f"-Denvironment={plan.environment}"])
        if plan.parallel:
            command.append("-DparallelTests=true")
        
        return command
    
    def parse_result(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        """Parse Surefire/Gradle test reports"""
        # Reuse TestNG parsing as RestAssured uses same report format
        adapter = TestNGAdapter()
        return adapter.parse_result(plan, workspace)


class CypressAdapter(FrameworkAdapter):
    """Cypress E2E testing adapter"""
    
    def __init__(self):
        super().__init__("cypress")
    
    def plan_to_command(self, plan: ExecutionPlan, workspace: Path) -> List[str]:
        """Generate Cypress command"""
        command = ["npx", "cypress", "run"]
        
        # Spec files
        if plan.selected_tests:
            command.extend(["--spec", ",".join(plan.selected_tests)])
        
        # Environment
        command.extend(["--env", f"testEnv={plan.environment}"])
        
        # Browser
        command.extend(["--browser", "chrome"])
        
        # Parallel (Cypress Cloud)
        if plan.parallel:
            command.append("--parallel")
        
        return command
    
    def parse_result(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        """Parse Cypress JSON results"""
        results_file = workspace / "cypress" / "results" / "results.json"
        
        if not results_file.exists():
            return self._create_error_result(plan, datetime.utcnow(), "Cypress results not found")
        
        with open(results_file) as f:
            data = json.load(f)
        
        executed, passed, failed, skipped = [], [], [], []
        
        for run in data.get("runs", []):
            for test in run.get("tests", []):
                name = test["title"][0] if test["title"] else "unknown"
                executed.append(name)
                if test["state"] == "passed":
                    passed.append(name)
                elif test["state"] == "failed":
                    failed.append(name)
                elif test["state"] == "skipped":
                    skipped.append(name)
        
        return ExecutionResult(
            executed_tests=executed,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            error_tests=[],
            execution_time_seconds=data.get("totalDuration", 0) / 1000,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            report_paths=[str(results_file)],
            log_paths=[],
            framework="cypress",
            environment=plan.environment,
        )


class PlaywrightAdapter(FrameworkAdapter):
    """Playwright testing adapter"""
    
    def __init__(self):
        super().__init__("playwright")
    
    def plan_to_command(self, plan: ExecutionPlan, workspace: Path) -> List[str]:
        """Generate Playwright command"""
        command = ["npx", "playwright", "test"]
        
        # Test files
        if plan.selected_tests:
            command.extend(plan.selected_tests)
        
        # Grep for test names
        if hasattr(plan, "tags") and plan.tags:
            command.extend(["--grep", "|".join(plan.tags)])
        
        # Parallel workers
        if plan.parallel:
            command.extend(["--workers", "4"])
        
        # Reporter
        command.extend(["--reporter=json"])
        
        return command
    
    def parse_result(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        """Parse Playwright JSON report"""
        report_file = workspace / "playwright-report" / "results.json"
        
        if not report_file.exists():
            return self._create_error_result(plan, datetime.utcnow(), "Playwright report not found")
        
        with open(report_file) as f:
            data = json.load(f)
        
        executed, passed, failed, skipped = [], [], [], []
        
        for suite in data.get("suites", []):
            for spec in suite.get("specs", []):
                name = spec["title"]
                executed.append(name)
                if spec.get("ok"):
                    passed.append(name)
                else:
                    failed.append(name)
        
        return ExecutionResult(
            executed_tests=executed,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            error_tests=[],
            execution_time_seconds=data.get("duration", 0) / 1000,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            report_paths=[str(report_file)],
            log_paths=[],
            framework="playwright",
            environment=plan.environment,
        )


class JUnitAdapter(FrameworkAdapter):
    """JUnit (4/5) testing adapter"""
    
    def __init__(self):
        super().__init__("junit")
    
    def plan_to_command(self, plan: ExecutionPlan, workspace: Path) -> List[str]:
        """Generate Maven/Gradle command for JUnit"""
        # Similar to TestNG
        if (workspace / "pom.xml").exists():
            command = ["mvn", "test"]
            if plan.selected_tests:
                tests = ",".join([t.split(".")[-1] for t in plan.selected_tests])
                command.append(f"-Dtest={tests}")
        else:
            command = ["./gradlew", "test"]
            if plan.selected_tests:
                command.append(f"--tests={','.join(plan.selected_tests)}")
        
        if plan.parallel:
            command.append("-Djunit.jupiter.execution.parallel.enabled=true")
        
        return command
    
    def parse_result(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        """Parse JUnit XML reports"""
        adapter = TestNGAdapter()
        return adapter.parse_result(plan, workspace)


class CucumberAdapter(FrameworkAdapter):
    """Cucumber BDD testing adapter"""
    
    def __init__(self):
        super().__init__("cucumber")
    
    def plan_to_command(self, plan: ExecutionPlan, workspace: Path) -> List[str]:
        """Generate Cucumber command"""
        command = ["mvn", "test", "-Dcucumber.options="]
        
        # Tags
        if hasattr(plan, "tags") and plan.tags:
            tags_expr = " or ".join([f"@{tag}" for tag in plan.tags])
            command[-1] += f"--tags '{tags_expr}'"
        
        # Features
        if plan.selected_tests:
            command[-1] += f" {' '.join(plan.selected_tests)}"
        
        # Plugin
        command[-1] += " --plugin json:target/cucumber-report.json"
        
        if plan.parallel:
            command.append("-Dcucumber.execution.parallel.enabled=true")
        
        return command
    
    def parse_result(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        """Parse Cucumber JSON report"""
        report_file = workspace / "target" / "cucumber-report.json"
        
        if not report_file.exists():
            return self._create_error_result(plan, datetime.utcnow(), "Cucumber report not found")
        
        with open(report_file) as f:
            data = json.load(f)
        
        executed, passed, failed, skipped = [], [], [], []
        
        for feature in data:
            for element in feature.get("elements", []):
                name = f"{feature['name']}.{element['name']}"
                executed.append(name)
                
                status = "passed"
                for step in element.get("steps", []):
                    if step["result"]["status"] == "failed":
                        status = "failed"
                        break
                    elif step["result"]["status"] == "skipped":
                        status = "skipped"
                
                if status == "passed":
                    passed.append(name)
                elif status == "failed":
                    failed.append(name)
                else:
                    skipped.append(name)
        
        return ExecutionResult(
            executed_tests=executed,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            error_tests=[],
            execution_time_seconds=0,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            report_paths=[str(report_file)],
            log_paths=[],
            framework="cucumber",
            environment=plan.environment,
        )


class BehaveAdapter(FrameworkAdapter):
    """Behave BDD testing adapter (Python)"""
    
    def __init__(self):
        super().__init__("behave")
    
    def plan_to_command(self, plan: ExecutionPlan, workspace: Path) -> List[str]:
        """Generate Behave command"""
        command = ["behave"]
        
        # Features
        if plan.selected_tests:
            command.extend(plan.selected_tests)
        
        # Tags
        if hasattr(plan, "tags") and plan.tags:
            command.extend(["--tags", ",".join(plan.tags)])
        
        # Parallel
        if plan.parallel:
            command.extend(["--processes", "4"])
        
        # Format
        command.extend(["--format", "json", "--outfile", "behave-results.json"])
        
        return command
    
    def parse_result(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        """Parse Behave JSON results"""
        results_file = workspace / "behave-results.json"
        
        if not results_file.exists():
            return self._create_error_result(plan, datetime.utcnow(), "Behave results not found")
        
        with open(results_file) as f:
            data = json.load(f)
        
        executed, passed, failed, skipped = [], [], [], []
        
        for feature in data:
            for element in feature.get("elements", []):
                name = f"{feature['name']}.{element['name']}"
                executed.append(name)
                
                if element["status"] == "passed":
                    passed.append(name)
                elif element["status"] == "failed":
                    failed.append(name)
                else:
                    skipped.append(name)
        
        return ExecutionResult(
            executed_tests=executed,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            error_tests=[],
            execution_time_seconds=0,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            report_paths=[str(results_file)],
            log_paths=[],
            framework="behave",
            environment=plan.environment,
        )


class SpecFlowAdapter(FrameworkAdapter):
    """SpecFlow BDD testing adapter (.NET)"""
    
    def __init__(self):
        super().__init__("specflow")
    
    def plan_to_command(self, plan: ExecutionPlan, workspace: Path) -> List[str]:
        """Generate dotnet test command for SpecFlow"""
        command = ["dotnet", "test"]
        
        # Filter by test name
        if plan.selected_tests:
            filters = " | ".join([f"FullyQualifiedName~{test}" for test in plan.selected_tests])
            command.extend(["--filter", filters])
        
        # Logger
        command.extend(["--logger", "trx;LogFileName=specflow-results.trx"])
        
        return command
    
    def parse_result(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        """Parse SpecFlow TRX results"""
        results_file = workspace / "TestResults" / "specflow-results.trx"
        
        if not results_file.exists():
            return self._create_error_result(plan, datetime.utcnow(), "SpecFlow results not found")
        
        tree = ET.parse(results_file)
        root = tree.getroot()
        ns = {"": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
        
        executed, passed, failed, skipped = [], [], [], []
        
        for test in root.findall(".//UnitTestResult", ns):
            name = test.get("testName")
            executed.append(name)
            
            outcome = test.get("outcome")
            if outcome == "Passed":
                passed.append(name)
            elif outcome == "Failed":
                failed.append(name)
            else:
                skipped.append(name)
        
        return ExecutionResult(
            executed_tests=executed,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            error_tests=[],
            execution_time_seconds=0,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            report_paths=[str(results_file)],
            log_paths=[],
            framework="specflow",
            environment=plan.environment,
        )


class NUnitAdapter(FrameworkAdapter):
    """NUnit testing adapter (.NET)"""
    
    def __init__(self):
        super().__init__("nunit")
    
    def plan_to_command(self, plan: ExecutionPlan, workspace: Path) -> List[str]:
        """Generate dotnet test command for NUnit"""
        command = ["dotnet", "test"]
        
        # Filter
        if plan.selected_tests:
            filters = " | ".join([f"FullyQualifiedName~{test}" for test in plan.selected_tests])
            command.extend(["--filter", filters])
        
        # Logger
        command.extend(["--logger", "nunit;LogFileName=nunit-results.xml"])
        
        return command
    
    def parse_result(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        """Parse NUnit XML results"""
        results_file = workspace / "TestResults" / "nunit-results.xml"
        
        if not results_file.exists():
            return self._create_error_result(plan, datetime.utcnow(), "NUnit results not found")
        
        tree = ET.parse(results_file)
        root = tree.getroot()
        
        executed, passed, failed, skipped = [], [], [], []
        
        for testcase in root.findall(".//test-case"):
            name = testcase.get("fullname")
            executed.append(name)
            
            result = testcase.get("result")
            if result == "Passed":
                passed.append(name)
            elif result == "Failed":
                failed.append(name)
            else:
                skipped.append(name)
        
        return ExecutionResult(
            executed_tests=executed,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            error_tests=[],
            execution_time_seconds=0,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            report_paths=[str(results_file)],
            log_paths=[],
            framework="nunit",
            environment=plan.environment,
        )


# Adapter factory
def create_adapter(framework: str) -> FrameworkAdapter:
    """
    Create framework adapter.
    
    Supported frameworks:
    - Java: testng, junit, restassured, cucumber
    - Python: pytest, behave, robot
    - JavaScript: cypress, playwright
    - .NET: nunit, specflow
    - BDD: cucumber, behave, specflow
    """
    adapters = {
        "testng": TestNGAdapter,
        "robot": RobotAdapter,
        "pytest": PytestAdapter,
        "restassured": RestAssuredAdapter,
        "cypress": CypressAdapter,
        "playwright": PlaywrightAdapter,
        "junit": JUnitAdapter,
        "cucumber": CucumberAdapter,
        "behave": BehaveAdapter,
        "specflow": SpecFlowAdapter,
        "nunit": NUnitAdapter,
    }
    
    adapter_class = adapters.get(framework.lower())
    if not adapter_class:
        supported = ", ".join(adapters.keys())
        raise ValueError(f"Unsupported framework: {framework}. Supported: {supported}")
    
    return adapter_class()
