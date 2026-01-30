"""
Execution Intelligence Graph Linking

Create graph relationships between test entities and source code:
- Cucumber: Step → Java Method → File
- Robot: Keyword → Library → File
- Pytest: Test → Fixture → Module

Enables:
- Impact analysis (which tests affected by code change)
- Coverage mapping (which code exercised by tests)
- Root cause analysis (trace failure to source code)
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path
import re

from core.logging import get_logger
from core.execution.intelligence.models import (
    StepBinding,
    CucumberScenario,
    CucumberStep,
    RobotTest,
    RobotKeyword,
    PytestTest,
    PytestFixture,
)

logger = get_logger(__name__)


@dataclass
class CodeNode:
    """Represents a code file/method/class in the graph"""
    node_id: str
    node_type: str  # file, class, method, function
    name: str
    file_path: str
    line_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestNode:
    """Represents a test entity in the graph"""
    node_id: str
    node_type: str  # scenario, step, test, keyword, fixture
    name: str
    framework: str  # cucumber, robot, pytest
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """Represents a relationship between nodes"""
    from_node: str  # node_id
    to_node: str    # node_id
    edge_type: str  # calls, uses, depends_on, implements, tests
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExecutionGraph:
    """
    Graph of test entities and code relationships.
    
    Supports queries like:
    - Which tests use this method?
    - Which code files does this scenario cover?
    - What's the impact of changing this file?
    """
    
    def __init__(self):
        self.nodes: Dict[str, TestNode | CodeNode] = {}
        self.edges: List[GraphEdge] = []
        
        # Indexes for fast lookup
        self.edges_from: Dict[str, List[GraphEdge]] = {}
        self.edges_to: Dict[str, List[GraphEdge]] = {}
    
    def add_node(self, node: TestNode | CodeNode):
        """Add a node to the graph"""
        self.nodes[node.node_id] = node
    
    def add_edge(self, edge: GraphEdge):
        """Add an edge to the graph"""
        self.edges.append(edge)
        
        # Update indexes
        if edge.from_node not in self.edges_from:
            self.edges_from[edge.from_node] = []
        self.edges_from[edge.from_node].append(edge)
        
        if edge.to_node not in self.edges_to:
            self.edges_to[edge.to_node] = []
        self.edges_to[edge.to_node].append(edge)
    
    def get_node(self, node_id: str) -> Optional[TestNode | CodeNode]:
        """Get node by ID"""
        return self.nodes.get(node_id)
    
    def get_outgoing_edges(self, node_id: str) -> List[GraphEdge]:
        """Get edges going out from a node"""
        return self.edges_from.get(node_id, [])
    
    def get_incoming_edges(self, node_id: str) -> List[GraphEdge]:
        """Get edges coming into a node"""
        return self.edges_to.get(node_id, [])
    
    def get_connected_nodes(self, node_id: str, edge_type: Optional[str] = None) -> List[TestNode | CodeNode]:
        """Get nodes connected to this node"""
        connected = []
        
        # Outgoing edges
        for edge in self.get_outgoing_edges(node_id):
            if edge_type is None or edge.edge_type == edge_type:
                node = self.get_node(edge.to_node)
                if node:
                    connected.append(node)
        
        # Incoming edges
        for edge in self.get_incoming_edges(node_id):
            if edge_type is None or edge.edge_type == edge_type:
                node = self.get_node(edge.from_node)
                if node:
                    connected.append(node)
        
        return connected
    
    def find_tests_for_file(self, file_path: str) -> List[TestNode]:
        """Find all tests that exercise code in a file"""
        tests = []
        
        # Find code nodes for this file
        code_nodes = [
            node for node in self.nodes.values()
            if isinstance(node, CodeNode) and node.file_path == file_path
        ]
        
        # Find test nodes that connect to these code nodes
        for code_node in code_nodes:
            for edge in self.get_incoming_edges(code_node.node_id):
                from_node = self.get_node(edge.from_node)
                if isinstance(from_node, TestNode):
                    if from_node not in tests:
                        tests.append(from_node)
        
        return tests
    
    def find_code_coverage(self, test_node_id: str) -> List[CodeNode]:
        """Find all code files/methods covered by a test"""
        coverage = []
        
        # BFS to find all connected code nodes
        visited = set()
        queue = [test_node_id]
        
        while queue:
            current_id = queue.pop(0)
            
            if current_id in visited:
                continue
            visited.add(current_id)
            
            for edge in self.get_outgoing_edges(current_id):
                target_node = self.get_node(edge.to_node)
                
                if isinstance(target_node, CodeNode):
                    if target_node not in coverage:
                        coverage.append(target_node)
                
                # Continue traversal
                if edge.to_node not in visited:
                    queue.append(edge.to_node)
        
        return coverage
    
    def calculate_impact(self, file_path: str) -> Dict[str, Any]:
        """
        Calculate impact of changing a file.
        
        Returns:
            Dictionary with impact metrics
        """
        affected_tests = self.find_tests_for_file(file_path)
        
        # Group by framework
        by_framework = {}
        for test in affected_tests:
            framework = test.framework
            if framework not in by_framework:
                by_framework[framework] = []
            by_framework[framework].append(test)
        
        return {
            'file_path': file_path,
            'affected_test_count': len(affected_tests),
            'by_framework': {
                framework: len(tests)
                for framework, tests in by_framework.items()
            },
            'affected_tests': [
                {
                    'name': test.name,
                    'type': test.node_type,
                    'framework': test.framework,
                }
                for test in affected_tests
            ]
        }
    
    def stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        node_types = {}
        for node in self.nodes.values():
            node_type = node.node_type
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        edge_types = {}
        for edge in self.edges:
            edge_type = edge.edge_type
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        
        return {
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'node_types': node_types,
            'edge_types': edge_types,
        }


class CucumberGraphBuilder:
    """Build graph for Cucumber scenarios"""
    
    def __init__(self, graph: ExecutionGraph):
        self.graph = graph
    
    def add_scenario(
        self,
        scenario: CucumberScenario,
        step_bindings: Dict[str, StepBinding]
    ):
        """
        Add Cucumber scenario to graph with step → method links.
        
        Args:
            scenario: CucumberScenario object
            step_bindings: Map of step text → StepBinding
        """
        # Create scenario node
        scenario_id = f"scenario:{scenario.feature_name}:{scenario.name}"
        scenario_node = TestNode(
            node_id=scenario_id,
            node_type="scenario",
            name=scenario.name,
            framework="cucumber",
            metadata={
                'feature_name': scenario.feature_name,
                'tags': scenario.tags,
            }
        )
        self.graph.add_node(scenario_node)
        
        # Process steps
        for step in scenario.steps:
            # Create step node
            step_id = f"step:{scenario.feature_name}:{scenario.name}:{step.text}"
            step_node = TestNode(
                node_id=step_id,
                node_type="step",
                name=f"{step.keyword} {step.text}",
                framework="cucumber",
                metadata={
                    'keyword': step.keyword,
                    'scenario_name': scenario.name,
                }
            )
            self.graph.add_node(step_node)
            
            # Link step to scenario
            self.graph.add_edge(GraphEdge(
                from_node=scenario_id,
                to_node=step_id,
                edge_type="contains",
            ))
            
            # Link step to Java method (if binding exists)
            binding = step_bindings.get(step.text)
            if binding:
                # Create method node
                method_id = f"method:{binding.class_name}:{binding.method_name}"
                method_node = CodeNode(
                    node_id=method_id,
                    node_type="method",
                    name=binding.method_name,
                    file_path=binding.file_path,
                    line_number=binding.line_number,
                    metadata={
                        'class_name': binding.class_name,
                        'annotation': binding.annotation_type,
                    }
                )
                self.graph.add_node(method_node)
                
                # Link step to method
                self.graph.add_edge(GraphEdge(
                    from_node=step_id,
                    to_node=method_id,
                    edge_type="implements",
                    metadata={'binding': binding.step_pattern}
                ))
                
                # Create file node
                file_id = f"file:{binding.file_path}"
                file_node = CodeNode(
                    node_id=file_id,
                    node_type="file",
                    name=Path(binding.file_path).name,
                    file_path=binding.file_path,
                )
                self.graph.add_node(file_node)
                
                # Link method to file
                self.graph.add_edge(GraphEdge(
                    from_node=method_id,
                    to_node=file_id,
                    edge_type="defined_in",
                ))


class RobotGraphBuilder:
    """Build graph for Robot Framework tests"""
    
    def __init__(self, graph: ExecutionGraph):
        self.graph = graph
    
    def add_test(self, test: RobotTest, library_paths: Optional[Dict[str, str]] = None):
        """
        Add Robot test to graph with keyword → library links.
        
        Args:
            test: RobotTest object
            library_paths: Optional map of library name → file path
        """
        # Create test node
        test_id = f"test:{test.suite_name}:{test.name}"
        test_node = TestNode(
            node_id=test_id,
            node_type="test",
            name=test.name,
            framework="robot",
            metadata={
                'suite_name': test.suite_name,
                'tags': test.tags,
            }
        )
        self.graph.add_node(test_node)
        
        # Process keywords
        for kw in test.keywords:
            # Create keyword node
            kw_id = f"keyword:{test.suite_name}:{test.name}:{kw.name}"
            kw_node = TestNode(
                node_id=kw_id,
                node_type="keyword",
                name=kw.name,
                framework="robot",
                metadata={
                    'library': kw.library,
                    'test_name': test.name,
                }
            )
            self.graph.add_node(kw_node)
            
            # Link keyword to test
            self.graph.add_edge(GraphEdge(
                from_node=test_id,
                to_node=kw_id,
                edge_type="calls",
            ))
            
            # Link keyword to library (if path known)
            if library_paths and kw.library in library_paths:
                library_path = library_paths[kw.library]
                
                # Create library/file node
                lib_id = f"library:{kw.library}"
                lib_node = CodeNode(
                    node_id=lib_id,
                    node_type="file",
                    name=kw.library,
                    file_path=library_path,
                    metadata={'library_name': kw.library}
                )
                self.graph.add_node(lib_node)
                
                # Link keyword to library
                self.graph.add_edge(GraphEdge(
                    from_node=kw_id,
                    to_node=lib_id,
                    edge_type="uses",
                ))


class PytestGraphBuilder:
    """Build graph for Pytest tests"""
    
    def __init__(self, graph: ExecutionGraph):
        self.graph = graph
    
    def add_test(self, test: PytestTest, test_file_path: str):
        """
        Add Pytest test to graph with fixture dependencies.
        
        Args:
            test: PytestTest object
            test_file_path: Path to test file
        """
        # Create test node
        test_id = f"test:{test.module}:{test.name}"
        test_node = TestNode(
            node_id=test_id,
            node_type="function",
            name=test.name,
            framework="pytest",
            metadata={
                'module': test.module,
                'markers': test.markers,
            }
        )
        self.graph.add_node(test_node)
        
        # Create test file node
        file_id = f"file:{test_file_path}"
        file_node = CodeNode(
            node_id=file_id,
            node_type="file",
            name=Path(test_file_path).name,
            file_path=test_file_path,
        )
        self.graph.add_node(file_node)
        
        # Link test to file
        self.graph.add_edge(GraphEdge(
            from_node=test_id,
            to_node=file_id,
            edge_type="defined_in",
        ))
        
        # Process fixtures
        for fixture in test.fixtures:
            # Create fixture node
            fixture_id = f"fixture:{fixture.name}"
            fixture_node = TestNode(
                node_id=fixture_id,
                node_type="fixture",
                name=fixture.name,
                framework="pytest",
                metadata={
                    'scope': fixture.scope,
                    'phase': fixture.phase,
                }
            )
            self.graph.add_node(fixture_node)
            
            # Link test to fixture
            self.graph.add_edge(GraphEdge(
                from_node=test_id,
                to_node=fixture_id,
                edge_type="depends_on",
                metadata={'scope': fixture.scope}
            ))


# Convenience functions

def build_complete_graph(
    scenarios: List[CucumberScenario] = None,
    step_bindings: Dict[str, StepBinding] = None,
    robot_tests: List[RobotTest] = None,
    robot_library_paths: Dict[str, str] = None,
    pytest_tests: List[PytestTest] = None,
    pytest_file_paths: Dict[str, str] = None,
) -> ExecutionGraph:
    """
    Build complete execution graph from all frameworks.
    
    Args:
        scenarios: Cucumber scenarios
        step_bindings: Cucumber step bindings (step text → StepBinding)
        robot_tests: Robot tests
        robot_library_paths: Robot library name → file path
        pytest_tests: Pytest tests
        pytest_file_paths: Pytest test name → file path
        
    Returns:
        ExecutionGraph with all relationships
    """
    graph = ExecutionGraph()
    
    # Cucumber
    if scenarios:
        cucumber_builder = CucumberGraphBuilder(graph)
        bindings = step_bindings or {}
        
        for scenario in scenarios:
            # Create step text → binding map
            step_binding_map = {}
            for step in scenario.steps:
                # Find matching binding
                for binding in bindings.values():
                    if binding.matches(step.text):
                        step_binding_map[step.text] = binding
                        break
            
            cucumber_builder.add_scenario(scenario, step_binding_map)
    
    # Robot
    if robot_tests:
        robot_builder = RobotGraphBuilder(graph)
        lib_paths = robot_library_paths or {}
        
        for test in robot_tests:
            robot_builder.add_test(test, lib_paths)
    
    # Pytest
    if pytest_tests:
        pytest_builder = PytestGraphBuilder(graph)
        file_paths = pytest_file_paths or {}
        
        for test in pytest_tests:
            test_file = file_paths.get(test.name, f"{test.module}.py")
            pytest_builder.add_test(test, test_file)
    
    logger.info(f"Built graph: {graph.stats()}")
    
    return graph


# Example usage
if __name__ == "__main__":
    from core.execution.intelligence.cucumber_parser import CucumberJSONParser
    from core.execution.intelligence.java_step_parser import get_step_definition_parser
    
    # Parse Cucumber scenarios
    parser = CucumberJSONParser()
    scenarios = parser.parse_file("cucumber.json")
    
    # Parse Java step definitions
    step_parser = get_step_definition_parser()
    bindings_list = step_parser.parse_directory("src/test/java/stepdefinitions")
    bindings = {binding.step_pattern: binding for binding in bindings_list}
    
    # Build graph
    graph = build_complete_graph(scenarios=scenarios, step_bindings=bindings)
    
    print(f"Graph statistics:")
    print(f"  Nodes: {graph.stats()['total_nodes']}")
    print(f"  Edges: {graph.stats()['total_edges']}")
    print(f"  Node types: {graph.stats()['node_types']}")
    print(f"  Edge types: {graph.stats()['edge_types']}")
    
    # Impact analysis example
    test_file = "src/test/java/stepdefinitions/LoginSteps.java"
    impact = graph.calculate_impact(test_file)
    
    print(f"\nImpact of changing {test_file}:")
    print(f"  Affected tests: {impact['affected_test_count']}")
    print(f"  By framework: {impact['by_framework']}")
