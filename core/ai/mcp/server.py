"""
MCP Server Implementation.

Exposes CrossBridge capabilities as MCP tools for AI agents to consume.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path


@dataclass
class ToolDefinition:
    """Definition of an MCP tool."""
    
    name: str
    description: str
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    category: str = "general"
    requires_auth: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPServerConfig:
    """Configuration for MCP server."""
    
    host: str = "localhost"
    port: int = 8080
    auth_enabled: bool = True
    api_key: Optional[str] = None
    cors_enabled: bool = True
    log_requests: bool = True
    max_request_size: int = 10 * 1024 * 1024  # 10MB


class MCPServer:
    """
    MCP Server exposing CrossBridge tools.
    
    Makes CrossBridge capabilities available to external AI agents via MCP protocol.
    """
    
    def __init__(self, config: Optional[MCPServerConfig] = None):
        """
        Initialize MCP server.
        
        Args:
            config: Server configuration
        """
        self.config = config or MCPServerConfig()
        self._tools: Dict[str, ToolDefinition] = {}
        self._request_history: List[Dict[str, Any]] = []
        
        # Register built-in CrossBridge tools
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """Register CrossBridge's built-in tools."""
        
        # Test execution tools
        self.register_tool(ToolDefinition(
            name="run_tests",
            description="Execute tests in a project",
            handler=self._handle_run_tests,
            input_schema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "test_pattern": {"type": "string"},
                    "framework": {"type": "string", "enum": ["pytest", "junit", "robot"]},
                },
                "required": ["project_path", "framework"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "total": {"type": "integer"},
                    "passed": {"type": "integer"},
                    "failed": {"type": "integer"},
                    "skipped": {"type": "integer"},
                    "duration": {"type": "number"},
                    "failures": {"type": "array"},
                },
            },
            category="testing",
            requires_auth=True,  # Require authentication
        ))
        
        # Test analysis tools
        self.register_tool(ToolDefinition(
            name="analyze_flaky_tests",
            description="Analyze test execution history to detect flaky tests",
            handler=self._handle_analyze_flaky,
            input_schema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "test_pattern": {"type": "string"},
                    "history_days": {"type": "integer", "default": 30},
                },
                "required": ["project_path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "flaky_tests": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "test_name": {"type": "string"},
                                "flaky_score": {"type": "number"},
                                "failure_rate": {"type": "number"},
                                "root_causes": {"type": "array"},
                            },
                        },
                    },
                },
            },
            category="analysis",
        ))
        
        # Test migration tools
        self.register_tool(ToolDefinition(
            name="migrate_tests",
            description="Migrate tests from one framework to another",
            handler=self._handle_migrate_tests,
            input_schema={
                "type": "object",
                "properties": {
                    "source_path": {"type": "string"},
                    "source_framework": {"type": "string"},
                    "target_framework": {"type": "string"},
                    "output_path": {"type": "string"},
                },
                "required": ["source_path", "source_framework", "target_framework"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "migrated_count": {"type": "integer"},
                    "output_path": {"type": "string"},
                    "warnings": {"type": "array"},
                },
            },
            category="migration",
        ))
        
        # Coverage tools
        self.register_tool(ToolDefinition(
            name="analyze_coverage",
            description="Analyze test coverage and suggest improvements",
            handler=self._handle_coverage_analysis,
            input_schema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "coverage_file": {"type": "string"},
                },
                "required": ["project_path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "coverage_percentage": {"type": "number"},
                    "uncovered_files": {"type": "array"},
                    "suggestions": {"type": "array"},
                },
            },
            category="analysis",
        ))
        
        # Impact analysis tools
        self.register_tool(ToolDefinition(
            name="analyze_impact",
            description="Analyze impact of code changes on tests",
            handler=self._handle_impact_analysis,
            input_schema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "changed_files": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["project_path", "changed_files"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "affected_tests": {"type": "array"},
                    "impact_score": {"type": "number"},
                    "recommended_tests": {"type": "array"},
                },
            },
            category="analysis",
        ))
        
        # BDD analysis tools (NEW)
        self.register_tool(ToolDefinition(
            name="analyze_bdd_features",
            description="Analyze BDD features (Cucumber, Robot BDD, JBehave)",
            handler=self._handle_bdd_analysis,
            input_schema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "framework": {"type": "string", "enum": ["cucumber-java", "robot-bdd", "jbehave"]},
                    "features_dir": {"type": "string"},
                    "step_definitions_dir": {"type": "string"},
                },
                "required": ["project_path", "framework"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "total_features": {"type": "integer"},
                    "total_scenarios": {"type": "integer"},
                    "step_coverage": {"type": "object"},
                    "unmapped_steps": {"type": "array"},
                },
            },
            category="bdd",
        ))
        
        # Execution orchestration tools (NEW)
        self.register_tool(ToolDefinition(
            name="orchestrate_execution",
            description="Intelligent test execution with strategy selection (smoke, impacted, risk, full)",
            handler=self._handle_orchestration,
            input_schema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "framework": {"type": "string"},
                    "strategy": {"type": "string", "enum": ["smoke", "impacted", "risk", "full"]},
                    "max_tests": {"type": "integer"},
                    "base_branch": {"type": "string"},
                },
                "required": ["project_path", "framework", "strategy"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "tests_selected": {"type": "array"},
                    "total_tests": {"type": "integer"},
                    "reduction_percent": {"type": "number"},
                    "execution_result": {"type": "object"},
                },
            },
            category="execution",
        ))
        
        # Semantic search tools (NEW)
        self.register_tool(ToolDefinition(
            name="semantic_search_tests",
            description="Search tests using natural language queries",
            handler=self._handle_semantic_search,
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "framework": {"type": "string"},
                    "top_k": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "matches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "test_name": {"type": "string"},
                                "similarity": {"type": "number"},
                                "framework": {"type": "string"},
                            },
                        },
                    },
                },
            },
            category="intelligence",
        ))
        
        # Execution intelligence tools (NEW)
        self.register_tool(ToolDefinition(
            name="classify_failure",
            description="Classify test failure (product defect, locator issue, environment, flaky)",
            handler=self._handle_failure_classification,
            input_schema={
                "type": "object",
                "properties": {
                    "log_file": {"type": "string"},
                    "framework": {"type": "string"},
                    "test_name": {"type": "string"},
                },
                "required": ["log_file", "framework"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "classification": {"type": "string"},
                    "confidence": {"type": "number"},
                    "code_reference": {"type": "object"},
                    "signals": {"type": "array"},
                },
            },
            category="intelligence",
        ))
        
        # Sidecar runtime tools (NEW)
        self.register_tool(ToolDefinition(
            name="sidecar_status",
            description="Get sidecar runtime health and metrics",
            handler=self._handle_sidecar_status,
            input_schema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                },
                "required": ["project_path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "metrics": {"type": "object"},
                    "health": {"type": "object"},
                },
            },
            category="monitoring",
        ))
        
        # Performance profiling tools (NEW)
        self.register_tool(ToolDefinition(
            name="get_profiling_report",
            description="Get performance profiling report for test execution",
            handler=self._handle_profiling_report,
            input_schema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "test_run_id": {"type": "string"},
                    "framework": {"type": "string"},
                },
                "required": ["project_path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "avg_duration": {"type": "number"},
                    "slowest_tests": {"type": "array"},
                    "http_requests": {"type": "object"},
                    "webdriver_commands": {"type": "object"},
                },
            },
            category="profiling",
        ))
        
        # AI transformation validation tools (NEW)
        self.register_tool(ToolDefinition(
            name="validate_transformation",
            description="Validate AI-generated code transformation with confidence scoring",
            handler=self._handle_transformation_validation,
            input_schema={
                "type": "object",
                "properties": {
                    "transformation_id": {"type": "string"},
                    "operation": {"type": "string"},
                },
                "required": ["transformation_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "confidence": {"type": "number"},
                    "requires_review": {"type": "boolean"},
                    "signals": {"type": "object"},
                },
            },
            category="validation",
        ))
    
    def register_tool(self, tool: ToolDefinition):
        """
        Register a new tool.
        
        Args:
            tool: Tool definition to register
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        
        self._tools[tool.name] = tool
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool.
        
        Args:
            tool_name: Name of tool to unregister
        
        Returns:
            True if tool was removed
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            return True
        return False
    
    def list_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available tools.
        
        Args:
            category: Optional category filter
        
        Returns:
            List of tool descriptions
        """
        tools = []
        for tool in self._tools.values():
            if category and tool.category != category:
                continue
            
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "input_schema": tool.input_schema,
                "output_schema": tool.output_schema,
                "requires_auth": tool.requires_auth,
            })
        
        return tools
    
    def execute_tool(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a tool.
        
        Args:
            tool_name: Name of tool to execute
            inputs: Tool inputs
            auth_token: Optional authentication token
        
        Returns:
            Tool execution result
        
        Raises:
            ValueError: If tool not found
            PermissionError: If authentication fails
        """
        if tool_name not in self._tools:
            raise ValueError(f"Tool not found: {tool_name}")
        
        tool = self._tools[tool_name]
        
        # Check authentication
        if self.config.auth_enabled and tool.requires_auth:
            if not self._validate_auth(auth_token):
                raise PermissionError("Invalid or missing authentication token")
        
        # Execute tool
        try:
            # Validate inputs
            self._validate_inputs(inputs, tool.input_schema)
            
            result = tool.handler(inputs)
            
            # Log request
            if self.config.log_requests:
                self._request_history.append({
                    "tool": tool_name,
                    "inputs": inputs,
                    "result": result,
                    "timestamp": str(Path.cwd()),  # Placeholder
                })
            
            return result
        
        except Exception as e:
            return {
                "error": str(e),
                "success": False,
            }
    
    def _validate_auth(self, token: Optional[str]) -> bool:
        """Validate authentication token."""
        if not self.config.auth_enabled:
            return True
        
        return token == self.config.api_key
    
    def _validate_inputs(self, inputs: Dict[str, Any], schema: Dict[str, Any]):
        """Validate inputs against JSON schema."""
        # In production, use jsonschema library
        required = schema.get("required", [])
        for field in required:
            if field not in inputs:
                raise ValueError(f"Required field missing: {field}")
    
    # Tool handlers (mock implementations)
    
    def _handle_run_tests(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle test execution request."""
        return {
            "total": 100,
            "passed": 95,
            "failed": 3,
            "skipped": 2,
            "duration": 45.2,
            "failures": [
                {"name": "test_login", "error": "Timeout"},
                {"name": "test_checkout", "error": "Element not found"},
                {"name": "test_payment", "error": "Connection refused"},
            ],
        }
    
    def _handle_analyze_flaky(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle flaky test analysis request."""
        return {
            "flaky_tests": [
                {
                    "test_name": "test_login",
                    "flaky_score": 0.75,
                    "failure_rate": 0.25,
                    "root_causes": ["Network timeout", "Race condition"],
                },
                {
                    "test_name": "test_search",
                    "flaky_score": 0.60,
                    "failure_rate": 0.15,
                    "root_causes": ["Database latency"],
                },
            ],
        }
    
    def _handle_migrate_tests(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle test migration request."""
        return {
            "migrated_count": 42,
            "output_path": inputs.get("output_path", "migrated_tests/"),
            "warnings": ["Manual review needed for async tests"],
        }
    
    def _handle_coverage_analysis(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle coverage analysis request."""
        return {
            "coverage_percentage": 78.5,
            "uncovered_files": ["auth.py", "payment.py"],
            "suggestions": [
                "Add tests for error handling in auth.py",
                "Increase coverage of payment.py edge cases",
            ],
        }
    
    def _handle_impact_analysis(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle impact analysis request."""
        return {
            "affected_tests": [
                "test_auth.py::test_login",
                "test_auth.py::test_logout",
            ],
            "impact_score": 0.65,
            "recommended_tests": [
                "test_auth.py",
                "test_integration.py::test_full_flow",
            ],
        }
    
    def _handle_bdd_analysis(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle BDD feature analysis request."""
        return {
            "total_features": 15,
            "total_scenarios": 87,
            "step_coverage": {
                "total_steps": 245,
                "mapped_steps": 238,
                "coverage_percent": 97.1,
            },
            "unmapped_steps": [
                "When user performs advanced search",
                "Then system should display filtered results",
            ],
        }
    
    def _handle_orchestration(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle execution orchestration request."""
        strategy = inputs.get("strategy", "smoke")
        reduction = {"smoke": 85, "impacted": 70, "risk": 50, "full": 0}
        return {
            "tests_selected": [
                "test_login.py::test_valid_login",
                "test_checkout.py::test_checkout_flow",
            ],
            "total_tests": 250,
            "reduction_percent": reduction.get(strategy, 0),
            "execution_result": {
                "passed": 38,
                "failed": 0,
                "duration": 45.2,
            },
        }
    
    def _handle_semantic_search(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle semantic search request."""
        return {
            "matches": [
                {
                    "test_name": "test_login_timeout",
                    "similarity": 0.92,
                    "framework": "pytest",
                },
                {
                    "test_name": "test_auth_timeout_handling",
                    "similarity": 0.87,
                    "framework": "selenium",
                },
            ],
        }
    
    def _handle_failure_classification(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failure classification request."""
        return {
            "classification": "LOCATOR_ISSUE",
            "confidence": 0.89,
            "code_reference": {
                "file": "tests/test_login.py",
                "line": 42,
                "snippet": "driver.find_element(By.ID, 'login-button').click()",
            },
            "signals": [
                {"type": "NoSuchElementException", "confidence": 0.9},
                {"type": "locator_pattern", "confidence": 0.85},
            ],
        }
    
    def _handle_sidecar_status(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle sidecar status request."""
        return {
            "status": "healthy",
            "metrics": {
                "events_observed": 15234,
                "queue_size": 127,
                "sampling_rate": 0.1,
                "cpu_usage": 3.2,
                "memory_mb": 67,
            },
            "health": {
                "fail_open": True,
                "adaptive_sampling": True,
                "resource_budget_ok": True,
            },
        }
    
    def _handle_profiling_report(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle profiling report request."""
        return {
            "avg_duration": 2.34,
            "slowest_tests": [
                {"name": "test_large_dataset", "duration": 45.2},
                {"name": "test_integration_flow", "duration": 32.1},
            ],
            "http_requests": {
                "total": 1245,
                "avg_latency_ms": 234,
                "errors": 12,
            },
            "webdriver_commands": {
                "total": 3456,
                "avg_duration_ms": 89,
            },
        }
    
    def _handle_transformation_validation(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle AI transformation validation request."""
        return {
            "confidence": 0.87,
            "requires_review": False,
            "signals": {
                "model_confidence": 0.92,
                "diff_size_penalty": -0.05,
                "syntax_valid": True,
                "similarity_score": 0.65,
            },
        }
    
    def get_request_history(self) -> List[Dict[str, Any]]:
        """Get history of tool requests."""
        return self._request_history.copy()
    
    def to_mcp_spec(self) -> Dict[str, Any]:
        """
        Export server definition in MCP specification format.
        
        Returns:
            MCP-compliant server specification
        """
        return {
            "name": "CrossBridge MCP Server",
            "version": "1.0.0",
            "description": "AI-powered test automation and analysis tools",
            "tools": self.list_tools(),
            "capabilities": {
                "testing": ["execution", "analysis", "migration"],
                "coverage": ["analysis", "suggestions"],
                "impact": ["change_analysis", "test_selection"],
            },
            "authentication": {
                "enabled": self.config.auth_enabled,
                "type": "api_key",
            },
        }
