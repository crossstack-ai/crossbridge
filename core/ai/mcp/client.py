"""
MCP Client Implementation.

Connects to external MCP servers (Jira, GitHub, CI/CD) to consume tools.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path


@dataclass
class MCPTool:
    """Represents an external tool available via MCP."""
    
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    server_url: str
    authentication: Optional[Dict[str, str]] = None
    timeout: int = 30
    retry_count: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPToolRegistry:
    """
    Registry of available MCP tools.
    
    Discovers and caches tool definitions from MCP servers.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize tool registry.
        
        Args:
            config_path: Path to MCP server configuration
        """
        self.config_path = config_path or Path("config/mcp_servers.json")
        self._tools: Dict[str, MCPTool] = {}
        self._servers: Dict[str, Dict[str, Any]] = {}
        
        if self.config_path.exists():
            self._load_servers()
    
    def _load_servers(self):
        """Load MCP server configurations."""
        try:
            with open(self.config_path) as f:
                config = json.load(f)
                self._servers = config.get("servers", {})
        except Exception as e:
            print(f"Failed to load MCP servers: {e}")
    
    def discover_tools(self, server_name: str) -> List[MCPTool]:
        """
        Discover tools from an MCP server.
        
        Args:
            server_name: Name of the MCP server
        
        Returns:
            List of discovered tools
        """
        if server_name not in self._servers:
            raise ValueError(f"Unknown MCP server: {server_name}")
        
        server_config = self._servers[server_name]
        server_url = server_config.get("url")
        auth = server_config.get("authentication")
        
        # In production, make HTTP request to server's /tools endpoint
        # For now, return mock tools based on server type
        tools = []
        
        if "jira" in server_name.lower():
            tools.extend(self._get_jira_tools(server_url, auth))
        elif "github" in server_name.lower():
            tools.extend(self._get_github_tools(server_url, auth))
        elif "ci" in server_name.lower() or "jenkins" in server_name.lower():
            tools.extend(self._get_ci_tools(server_url, auth))
        
        # Cache discovered tools
        for tool in tools:
            self._tools[tool.name] = tool
        
        return tools
    
    def _get_jira_tools(self, server_url: str, auth: Optional[Dict]) -> List[MCPTool]:
        """Get Jira integration tools."""
        return [
            MCPTool(
                name="jira_create_issue",
                description="Create a new Jira issue",
                input_schema={
                    "type": "object",
                    "properties": {
                        "project": {"type": "string"},
                        "summary": {"type": "string"},
                        "description": {"type": "string"},
                        "issue_type": {"type": "string", "enum": ["Bug", "Task", "Story"]},
                    },
                    "required": ["project", "summary", "issue_type"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "issue_key": {"type": "string"},
                        "url": {"type": "string"},
                    },
                },
                server_url=server_url,
                authentication=auth,
            ),
            MCPTool(
                name="jira_search_issues",
                description="Search for Jira issues using JQL",
                input_schema={
                    "type": "object",
                    "properties": {
                        "jql": {"type": "string"},
                        "max_results": {"type": "integer", "default": 50},
                    },
                    "required": ["jql"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "issues": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string"},
                                    "summary": {"type": "string"},
                                    "status": {"type": "string"},
                                },
                            },
                        },
                    },
                },
                server_url=server_url,
                authentication=auth,
            ),
        ]
    
    def _get_github_tools(self, server_url: str, auth: Optional[Dict]) -> List[MCPTool]:
        """Get GitHub integration tools."""
        return [
            MCPTool(
                name="github_create_pr",
                description="Create a GitHub pull request",
                input_schema={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string"},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "base": {"type": "string", "default": "main"},
                        "head": {"type": "string"},
                    },
                    "required": ["repo", "title", "head"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                        "url": {"type": "string"},
                    },
                },
                server_url=server_url,
                authentication=auth,
            ),
            MCPTool(
                name="github_get_pr_status",
                description="Get status of a pull request",
                input_schema={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string"},
                        "pr_number": {"type": "integer"},
                    },
                    "required": ["repo", "pr_number"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "state": {"type": "string"},
                        "checks": {"type": "array"},
                        "mergeable": {"type": "boolean"},
                    },
                },
                server_url=server_url,
                authentication=auth,
            ),
        ]
    
    def _get_ci_tools(self, server_url: str, auth: Optional[Dict]) -> List[MCPTool]:
        """Get CI/CD integration tools."""
        return [
            MCPTool(
                name="ci_trigger_build",
                description="Trigger a CI/CD build",
                input_schema={
                    "type": "object",
                    "properties": {
                        "job_name": {"type": "string"},
                        "parameters": {"type": "object"},
                    },
                    "required": ["job_name"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "build_id": {"type": "string"},
                        "url": {"type": "string"},
                    },
                },
                server_url=server_url,
                authentication=auth,
            ),
            MCPTool(
                name="ci_get_build_status",
                description="Get status of a CI/CD build",
                input_schema={
                    "type": "object",
                    "properties": {
                        "build_id": {"type": "string"},
                    },
                    "required": ["build_id"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "result": {"type": "string"},
                        "duration": {"type": "number"},
                    },
                },
                server_url=server_url,
                authentication=auth,
            ),
        ]
    
    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Get a registered tool by name."""
        return self._tools.get(tool_name)
    
    def list_tools(self, server_name: Optional[str] = None) -> List[MCPTool]:
        """List all registered tools, optionally filtered by server."""
        if server_name:
            return [
                tool for tool in self._tools.values()
                if server_name.lower() in tool.name.lower()
            ]
        return list(self._tools.values())


class MCPClient:
    """
    MCP Client for consuming external tools.
    
    Connects to MCP servers and executes tool calls.
    """
    
    def __init__(self, registry: Optional[MCPToolRegistry] = None):
        """
        Initialize MCP client.
        
        Args:
            registry: Tool registry (creates default if not provided)
        """
        self.registry = registry or MCPToolRegistry()
        self._call_history: List[Dict[str, Any]] = []
    
    def call_tool(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Call an MCP tool.
        
        Args:
            tool_name: Name of the tool to call
            inputs: Tool input parameters
            timeout: Optional timeout override
        
        Returns:
            Tool execution result
        
        Raises:
            ValueError: If tool not found
            AIError: If tool execution fails
        """
        tool = self.registry.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        # Validate inputs against schema
        self._validate_inputs(inputs, tool.input_schema)
        
        # Execute tool (with retries)
        for attempt in range(tool.retry_count):
            try:
                result = self._execute_tool(tool, inputs, timeout or tool.timeout)
                
                # Validate output
                self._validate_output(result, tool.output_schema)
                
                # Log call
                self._call_history.append({
                    "tool": tool_name,
                    "inputs": inputs,
                    "result": result,
                    "timestamp": time.time(),
                    "attempt": attempt + 1,
                })
                
                return result
            
            except Exception as e:
                if attempt == tool.retry_count - 1:
                    raise Exception(f"Tool execution failed after {tool.retry_count} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def _execute_tool(
        self,
        tool: MCPTool,
        inputs: Dict[str, Any],
        timeout: int,
    ) -> Dict[str, Any]:
        """
        Execute tool call (makes HTTP request to MCP server).
        
        In production, this would:
        1. Construct MCP-compliant request
        2. Add authentication headers
        3. Make HTTP POST to {server_url}/tools/{tool_name}
        4. Parse MCP response
        
        For now, returns mock response.
        """
        # Mock implementation
        if "jira_create_issue" in tool.name:
            return {
                "issue_key": "PROJ-123",
                "url": f"{tool.server_url}/browse/PROJ-123",
            }
        elif "github_create_pr" in tool.name:
            return {
                "pr_number": 42,
                "url": f"{tool.server_url}/pull/42",
            }
        elif "ci_trigger_build" in tool.name:
            return {
                "build_id": "build-12345",
                "url": f"{tool.server_url}/job/{inputs.get('job_name')}/12345",
            }
        
        return {"success": True}
    
    def _validate_inputs(self, inputs: Dict[str, Any], schema: Dict[str, Any]):
        """Validate inputs against JSON schema."""
        # In production, use jsonschema library
        required = schema.get("required", [])
        for field in required:
            if field not in inputs:
                raise ValueError(f"Required field missing: {field}")
    
    def _validate_output(self, output: Dict[str, Any], schema: Dict[str, Any]):
        """Validate output against JSON schema."""
        # In production, use jsonschema library
        pass
    
    def get_call_history(self) -> List[Dict[str, Any]]:
        """Get history of tool calls."""
        return self._call_history.copy()
