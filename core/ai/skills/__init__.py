"""
AI Skills - Business-level AI capabilities for CrossBridge.

Skills combine prompts, parsing, and validation to accomplish specific tasks.
"""

import json
import re
from typing import Any, Dict, List

from core.ai.base import AISkill
from core.ai.models import AIResponse, TaskType


class FlakyAnalyzer(AISkill):
    """
    Analyze test execution history to detect flaky behavior.
    
    Uses historical test runs, failure patterns, and environment data
    to determine if a test is flaky and identify root causes.
    """
    
    skill_name = "flaky_analyzer"
    description = "Detect and analyze flaky test behavior"
    task_type = TaskType.FLAKY_ANALYSIS
    
    default_model = "gpt-4o-mini"
    default_temperature = 0.3
    default_max_tokens = 2048
    
    prompt_template_id = "flaky_analysis"
    prompt_version = "v1"
    
    def prepare_inputs(self, **kwargs) -> Dict[str, Any]:
        """
        Prepare inputs for flaky analysis.
        
        Required kwargs:
            test_name: Name of the test
            test_file: File containing the test
            execution_history: List of execution results
        
        Optional kwargs:
            coverage_data: Coverage information
            environment_info: Environment details
        """
        # Validate required inputs
        required = ["test_name", "test_file", "execution_history"]
        for key in required:
            if key not in kwargs:
                raise ValueError(f"Missing required input: {key}")
        
        # Format execution history
        history = kwargs["execution_history"]
        if isinstance(history, list):
            history_str = "\n".join(
                f"- Run {i+1}: {run.get('status', 'unknown')} "
                f"({run.get('duration', 'N/A')}s) "
                f"- {run.get('error', 'no error')}"
                for i, run in enumerate(history)
            )
        else:
            history_str = str(history)
        
        return {
            "test_name": kwargs["test_name"],
            "test_file": kwargs["test_file"],
            "execution_history": history_str,
            "execution_count": len(history) if isinstance(history, list) else 0,
            "coverage_data": kwargs.get("coverage_data", ""),
            "environment_info": kwargs.get("environment_info", ""),
        }
    
    def parse_response(self, response: AIResponse) -> Dict[str, Any]:
        """Parse JSON response from AI."""
        try:
            # Try to extract JSON from response
            content = response.content.strip()
            
            # Handle markdown code blocks
            if "```json" in content:
                json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
            elif "```" in content:
                json_match = re.search(r'```\s*\n(.*?)\n```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
            
            parsed = json.loads(content)
            
            return {
                "is_flaky": parsed.get("is_flaky", False),
                "confidence": float(parsed.get("confidence", 0.0)),
                "flaky_score": float(parsed.get("flaky_score", 0.0)),
                "explanation": parsed.get("explanation", ""),
                "root_causes": parsed.get("root_causes", []),
                "recommendations": parsed.get("recommendations", []),
            }
        
        except json.JSONDecodeError:
            # Fallback: parse unstructured response
            return {
                "is_flaky": "flaky" in response.content.lower(),
                "confidence": 0.5,
                "flaky_score": 0.5,
                "explanation": response.content,
                "root_causes": [],
                "recommendations": [],
            }
    
    def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate parsed output."""
        required_keys = ["is_flaky", "confidence", "explanation"]
        return all(key in output for key in required_keys)


class TestGenerator(AISkill):
    """
    Generate test cases from source code.
    
    Analyzes source code and generates comprehensive test cases
    following framework conventions and best practices.
    """
    
    skill_name = "test_generator"
    description = "Generate test cases from source code"
    task_type = TaskType.TEST_GENERATION
    
    default_model = "gpt-4o"
    default_temperature = 0.5
    default_max_tokens = 4096
    
    prompt_template_id = "test_generation"
    prompt_version = "v1"
    
    def prepare_inputs(self, **kwargs) -> Dict[str, Any]:
        """
        Prepare inputs for test generation.
        
        Required kwargs:
            source_file: Path to source file
            source_code: Source code content
            language: Programming language
            test_framework: Testing framework
        
        Optional kwargs:
            existing_tests: Existing test code
            coverage_gaps: Areas needing coverage
        """
        required = ["source_file", "source_code", "language", "test_framework"]
        for key in required:
            if key not in kwargs:
                raise ValueError(f"Missing required input: {key}")
        
        return {
            "source_file": kwargs["source_file"],
            "source_code": kwargs["source_code"],
            "language": kwargs["language"],
            "test_framework": kwargs["test_framework"],
            "existing_tests": kwargs.get("existing_tests", ""),
            "coverage_gaps": kwargs.get("coverage_gaps", ""),
        }
    
    def parse_response(self, response: AIResponse) -> Dict[str, Any]:
        """Parse test generation response."""
        content = response.content.strip()
        
        # Extract code from markdown blocks
        code_blocks = re.findall(r'```(?:\w+)?\s*\n(.*?)\n```', content, re.DOTALL)
        
        if code_blocks:
            test_code = code_blocks[0]  # Take first code block
        else:
            test_code = content
        
        # Count test functions/methods
        test_count = len(re.findall(r'def test_\w+|it\(|test\(', test_code))
        
        return {
            "test_code": test_code,
            "test_count": test_count,
            "full_response": content,
        }
    
    def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate test generation output."""
        return "test_code" in output and len(output["test_code"]) > 0


class TestMigrator(AISkill):
    """
    Migrate tests from one framework to another.
    
    Converts test code between frameworks while preserving logic
    and following target framework idioms.
    """
    
    skill_name = "test_migrator"
    description = "Migrate tests between frameworks"
    task_type = TaskType.TEST_MIGRATION
    
    default_model = "gpt-4o"
    default_temperature = 0.4
    default_max_tokens = 4096
    
    prompt_template_id = "test_migration"
    prompt_version = "v1"
    
    def prepare_inputs(self, **kwargs) -> Dict[str, Any]:
        """
        Prepare inputs for test migration.
        
        Required kwargs:
            source_framework: Source framework name
            target_framework: Target framework name
            language: Programming language
            source_test_code: Source test code
        
        Optional kwargs:
            target_patterns: Target framework patterns
            migration_notes: Additional migration notes
        """
        required = ["source_framework", "target_framework", "language", "source_test_code"]
        for key in required:
            if key not in kwargs:
                raise ValueError(f"Missing required input: {key}")
        
        return {
            "source_framework": kwargs["source_framework"],
            "target_framework": kwargs["target_framework"],
            "language": kwargs["language"],
            "source_test_code": kwargs["source_test_code"],
            "target_patterns": kwargs.get("target_patterns", ""),
            "migration_notes": kwargs.get("migration_notes", ""),
        }
    
    def parse_response(self, response: AIResponse) -> Dict[str, Any]:
        """Parse migration response."""
        try:
            # Try to parse as JSON
            content = response.content.strip()
            
            if "```json" in content:
                json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
            
            parsed = json.loads(content)
            
            return {
                "migrated_code": parsed.get("migrated_code", ""),
                "changes": parsed.get("changes", []),
                "warnings": parsed.get("warnings", []),
                "confidence": float(parsed.get("confidence", 0.8)),
            }
        
        except json.JSONDecodeError:
            # Fallback: extract code blocks
            code_blocks = re.findall(r'```(?:\w+)?\s*\n(.*?)\n```', response.content, re.DOTALL)
            
            return {
                "migrated_code": code_blocks[0] if code_blocks else response.content,
                "changes": [],
                "warnings": [],
                "confidence": 0.7,
            }
    
    def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate migration output."""
        return "migrated_code" in output and len(output["migrated_code"]) > 0


class CoverageReasoner(AISkill):
    """
    Infer test coverage needs and recommend improvements.
    
    Analyzes code complexity and suggests test scenarios.
    """
    
    skill_name = "coverage_reasoner"
    description = "Infer coverage needs and recommend tests"
    task_type = TaskType.COVERAGE_INFERENCE
    
    default_model = "gpt-4o-mini"
    default_temperature = 0.4
    default_max_tokens = 2048
    
    prompt_template_id = "coverage_inference"
    prompt_version = "v1"
    
    def prepare_inputs(self, **kwargs) -> Dict[str, Any]:
        """Prepare inputs for coverage analysis."""
        required = ["source_file", "source_code", "language"]
        for key in required:
            if key not in kwargs:
                raise ValueError(f"Missing required input: {key}")
        
        return {
            "source_file": kwargs["source_file"],
            "source_code": kwargs["source_code"],
            "language": kwargs["language"],
            "existing_coverage": kwargs.get("existing_coverage", ""),
            "related_files": kwargs.get("related_files", ""),
        }
    
    def parse_response(self, response: AIResponse) -> Dict[str, Any]:
        """Parse coverage analysis response."""
        try:
            content = response.content.strip()
            
            if "```json" in content:
                json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
            
            parsed = json.loads(content)
            
            return {
                "complexity_score": int(parsed.get("complexity_score", 5)),
                "critical_paths": parsed.get("critical_paths", []),
                "edge_cases": parsed.get("edge_cases", []),
                "integration_points": parsed.get("integration_points", []),
                "test_scenarios": parsed.get("test_scenarios", []),
                "coverage_recommendation": parsed.get("coverage_recommendation", ""),
            }
        
        except json.JSONDecodeError:
            return {
                "complexity_score": 5,
                "critical_paths": [],
                "edge_cases": [],
                "integration_points": [],
                "test_scenarios": [],
                "coverage_recommendation": response.content,
            }
    
    def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate coverage analysis output."""
        return "complexity_score" in output and "coverage_recommendation" in output


class RootCauseAnalyzer(AISkill):
    """
    Analyze test failures and determine root causes.
    
    Examines failures, stack traces, and code changes to identify
    the root cause and suggest fixes.
    """
    
    skill_name = "root_cause_analyzer"
    description = "Analyze test failures and find root causes"
    task_type = TaskType.ROOT_CAUSE_ANALYSIS
    
    default_model = "gpt-4o"
    default_temperature = 0.3
    default_max_tokens = 3072
    
    prompt_template_id = "root_cause_analysis"
    prompt_version = "v1"
    
    def prepare_inputs(self, **kwargs) -> Dict[str, Any]:
        """Prepare inputs for root cause analysis."""
        required = ["test_name", "test_file", "failure_info"]
        for key in required:
            if key not in kwargs:
                raise ValueError(f"Missing required input: {key}")
        
        return {
            "test_name": kwargs["test_name"],
            "test_file": kwargs["test_file"],
            "failure_info": kwargs["failure_info"],
            "stack_trace": kwargs.get("stack_trace", ""),
            "recent_changes": kwargs.get("recent_changes", ""),
            "test_code": kwargs.get("test_code", ""),
            "source_code": kwargs.get("source_code", ""),
        }
    
    def parse_response(self, response: AIResponse) -> Dict[str, Any]:
        """Parse root cause analysis response."""
        try:
            content = response.content.strip()
            
            if "```json" in content:
                json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
            
            parsed = json.loads(content)
            
            return {
                "root_cause": parsed.get("root_cause", ""),
                "confidence": float(parsed.get("confidence", 0.0)),
                "contributing_factors": parsed.get("contributing_factors", []),
                "recommended_fixes": parsed.get("recommended_fixes", []),
                "prevention": parsed.get("prevention", []),
                "similar_issues": parsed.get("similar_issues", []),
            }
        
        except json.JSONDecodeError:
            return {
                "root_cause": response.content,
                "confidence": 0.6,
                "contributing_factors": [],
                "recommended_fixes": [],
                "prevention": [],
                "similar_issues": [],
            }
    
    def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate root cause analysis output."""
        return "root_cause" in output and len(output["root_cause"]) > 0
