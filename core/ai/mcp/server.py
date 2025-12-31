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
