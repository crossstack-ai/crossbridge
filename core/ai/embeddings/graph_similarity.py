"""
Graph-based Similarity Scoring

Enhances semantic similarity with relationship-aware scoring.
Captures structural relationships between tests, files, methods, and failures.

Graph entities:
- Test
- Scenario
- File
- Method
- Failure

Graph edges:
- TEST_USES_FILE
- TEST_CALLS_METHOD
- FAILURE_OCCURS_IN_TEST
- SCENARIO_PART_OF_FEATURE
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.AI)


@dataclass
class GraphNode:
    """Node in the similarity graph"""
    id: str
    type: str  # test, scenario, file, method, failure
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """Edge in the similarity graph"""
    source: str  # node ID
    target: str  # node ID
    edge_type: str  # uses_file, calls_method, occurs_in, part_of
    weight: float = 1.0


class SimilarityGraph:
    """
    Graph structure for relationship-aware similarity.
    
    Phase-1: Simple adjacency list + Jaccard overlap
    Phase-2: Neo4j/Memgraph + graph embeddings (node2vec)
    
    Storage:
    - Nodes: dict[id -> GraphNode]
    - Edges: adjacency list dict[id -> list[neighbor_id]]
    """
    
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, List[GraphEdge]] = defaultdict(list)
        
        # Adjacency for fast neighbor lookup
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        
        logger.info("Similarity graph initialized")
    
    def add_node(self, node_id: str, node_type: str, metadata: Optional[Dict] = None) -> None:
        """Add or update node"""
        self.nodes[node_id] = GraphNode(
            id=node_id,
            type=node_type,
            metadata=metadata or {}
        )
    
    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        weight: float = 1.0
    ) -> None:
        """Add edge between nodes"""
        # Create nodes if they don't exist
        if source not in self.nodes:
            self.add_node(source, "unknown")
        if target not in self.nodes:
            self.add_node(target, "unknown")
        
        # Add edge
        edge = GraphEdge(
            source=source,
            target=target,
            edge_type=edge_type,
            weight=weight
        )
        self.edges[source].append(edge)
        
        # Update adjacency (bidirectional for similarity)
        self.adjacency[source].add(target)
        self.adjacency[target].add(source)
    
    def get_neighbors(self, node_id: str) -> Set[str]:
        """Get all neighbors of a node"""
        return self.adjacency.get(node_id, set())
    
    def get_typed_neighbors(self, node_id: str, edge_type: Optional[str] = None) -> List[str]:
        """Get neighbors by edge type"""
        if node_id not in self.edges:
            return []
        
        neighbors = []
        for edge in self.edges[node_id]:
            if edge_type is None or edge.edge_type == edge_type:
                neighbors.append(edge.target)
        
        return neighbors
    
    def jaccard_similarity(self, node_a: str, node_b: str) -> float:
        """
        Calculate Jaccard similarity between two nodes based on neighbor overlap.
        
        Formula: |A ∩ B| / |A ∪ B|
        
        Returns:
            Similarity score (0.0 - 1.0)
        """
        neighbors_a = self.get_neighbors(node_a)
        neighbors_b = self.get_neighbors(node_b)
        
        if not neighbors_a and not neighbors_b:
            return 0.0
        
        intersection = len(neighbors_a & neighbors_b)
        union = len(neighbors_a | neighbors_b)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def common_neighbors_count(self, node_a: str, node_b: str) -> int:
        """Count common neighbors"""
        neighbors_a = self.get_neighbors(node_a)
        neighbors_b = self.get_neighbors(node_b)
        return len(neighbors_a & neighbors_b)
    
    def node_count(self) -> int:
        """Total number of nodes"""
        return len(self.nodes)
    
    def edge_count(self) -> int:
        """Total number of edges"""
        return sum(len(edges) for edges in self.edges.values())


class GraphSimilarityScorer:
    """
    Combines semantic and graph-based similarity.
    
    Final score = semantic_similarity * α + graph_overlap * β
    
    Phase-1 weights:
    - semantic: 0.7
    - graph: 0.3
    
    Phase-2: Adaptive weights based on confidence
    """
    
    def __init__(
        self,
        graph: SimilarityGraph,
        semantic_weight: float = 0.7,
        graph_weight: float = 0.3
    ):
        """
        Initialize graph similarity scorer
        
        Args:
            graph: Similarity graph
            semantic_weight: Weight for semantic similarity (default: 0.7)
            graph_weight: Weight for graph overlap (default: 0.3)
        """
        if abs(semantic_weight + graph_weight - 1.0) > 0.01:
            raise ValueError("Weights must sum to 1.0")
        
        self.graph = graph
        self.semantic_weight = semantic_weight
        self.graph_weight = graph_weight
        
        logger.info(
            f"Graph similarity scorer initialized",
            semantic_weight=semantic_weight,
            graph_weight=graph_weight
        )
    
    def calculate_combined_score(
        self,
        node_a: str,
        node_b: str,
        semantic_score: float
    ) -> float:
        """
        Calculate combined similarity score.
        
        Args:
            node_a: First node ID
            node_b: Second node ID
            semantic_score: Semantic similarity (0.0 - 1.0)
        
        Returns:
            Combined score (0.0 - 1.0)
        """
        # Get graph overlap score
        graph_score = self.graph.jaccard_similarity(node_a, node_b)
        
        # Weighted combination
        combined = (
            semantic_score * self.semantic_weight +
            graph_score * self.graph_weight
        )
        
        return min(1.0, max(0.0, combined))
    
    def enhance_search_results(
        self,
        query_node: str,
        semantic_results: List[Tuple[str, float]]
    ) -> List[Tuple[str, float, Dict[str, float]]]:
        """
        Enhance semantic search results with graph scores.
        
        Args:
            query_node: Query node ID
            semantic_results: List of (node_id, semantic_score)
        
        Returns:
            List of (node_id, combined_score, score_breakdown)
        """
        enhanced = []
        
        for node_id, semantic_score in semantic_results:
            graph_score = self.graph.jaccard_similarity(query_node, node_id)
            combined_score = self.calculate_combined_score(
                query_node,
                node_id,
                semantic_score
            )
            
            # Get common neighbors for explanation
            common_count = self.graph.common_neighbors_count(query_node, node_id)
            
            score_breakdown = {
                "semantic": semantic_score,
                "graph": graph_score,
                "combined": combined_score,
                "common_neighbors": common_count
            }
            
            enhanced.append((node_id, combined_score, score_breakdown))
        
        # Sort by combined score
        enhanced.sort(key=lambda x: x[1], reverse=True)
        
        return enhanced


class GraphBuilder:
    """
    Helper to build similarity graph from test data.
    
    Extracts relationships from:
    - Test files
    - Method calls
    - Import statements
    - Failure patterns
    """
    
    def __init__(self, graph: SimilarityGraph):
        self.graph = graph
    
    def add_test(
        self,
        test_id: str,
        file_path: str,
        methods_called: List[str],
        imports: List[str],
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Add test node and relationships
        
        Args:
            test_id: Test identifier
            file_path: Source file path
            methods_called: Methods called in test
            imports: Imported modules
            metadata: Additional metadata
        """
        # Add test node
        self.graph.add_node(test_id, "test", metadata or {})
        
        # Add file relationship
        file_id = f"file:{file_path}"
        self.graph.add_node(file_id, "file", {"path": file_path})
        self.graph.add_edge(test_id, file_id, "uses_file")
        
        # Add method relationships
        for method in methods_called:
            method_id = f"method:{method}"
            self.graph.add_node(method_id, "method", {"name": method})
            self.graph.add_edge(test_id, method_id, "calls_method")
        
        # Add import relationships
        for module in imports:
            module_id = f"module:{module}"
            self.graph.add_node(module_id, "module", {"name": module})
            self.graph.add_edge(test_id, module_id, "imports")
    
    def add_failure(
        self,
        failure_id: str,
        test_id: str,
        error_type: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Add failure node and relationship
        
        Args:
            failure_id: Failure identifier
            test_id: Related test ID
            error_type: Type of error
            metadata: Additional metadata
        """
        # Add failure node
        self.graph.add_node(
            failure_id,
            "failure",
            {**(metadata or {}), "error_type": error_type}
        )
        
        # Link to test
        self.graph.add_edge(failure_id, test_id, "occurs_in")
    
    def add_scenario(
        self,
        scenario_id: str,
        feature: str,
        tests: List[str],
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Add scenario node and relationships
        
        Args:
            scenario_id: Scenario identifier
            feature: Feature name
            tests: Related test IDs
            metadata: Additional metadata
        """
        # Add scenario node
        self.graph.add_node(
            scenario_id,
            "scenario",
            {**(metadata or {}), "feature": feature}
        )
        
        # Add feature relationship
        feature_id = f"feature:{feature}"
        self.graph.add_node(feature_id, "feature", {"name": feature})
        self.graph.add_edge(scenario_id, feature_id, "part_of")
        
        # Link to tests
        for test_id in tests:
            self.graph.add_edge(scenario_id, test_id, "includes_test")


def create_similarity_graph() -> SimilarityGraph:
    """Factory function to create a new similarity graph"""
    return SimilarityGraph()


def create_graph_scorer(
    graph: SimilarityGraph,
    semantic_weight: float = 0.7,
    graph_weight: float = 0.3
) -> GraphSimilarityScorer:
    """Factory function to create graph similarity scorer"""
    return GraphSimilarityScorer(graph, semantic_weight, graph_weight)
