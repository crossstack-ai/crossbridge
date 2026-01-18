"""
Continuous Coverage Intelligence

Maintains and updates Test→Feature, Test→API, and Test→Page mappings
based on observed execution events. This is NOT traditional code coverage -
it's behavioral coverage intelligence.

Key concepts:
- Coverage graph: nodes (tests, features, APIs, pages) + edges (relationships)
- Incremental updates: append observations, never overwrite
- Change impact: which tests are affected by code changes
"""

import logging
from datetime import datetime
from typing import List, Dict, Set, Optional
from dataclasses import dataclass

from .events import CrossBridgeEvent, EventType

logger = logging.getLogger(__name__)


@dataclass
class CoverageNode:
    """Node in the coverage graph"""
    node_id: str
    node_type: str  # test | feature | api | page | ui_component
    metadata: dict
    created_at: datetime
    updated_at: datetime


@dataclass
class CoverageEdge:
    """Edge in the coverage graph (relationship)"""
    from_node: str
    to_node: str
    edge_type: str  # tests | calls_api | visits_page | interacts_with
    weight: int  # Number of times relationship observed
    first_seen: datetime
    last_seen: datetime
    metadata: dict


class CoverageIntelligence:
    """
    Maintains continuous coverage intelligence graph.
    
    Updates mappings incrementally based on observed test execution.
    Never overwrites - only appends new observations.
    """
    
    def __init__(self, db_connection=None):
        self.db_connection = db_connection
        self.graph_nodes: Dict[str, CoverageNode] = {}
        self.graph_edges: List[CoverageEdge] = []
        
        if db_connection:
            self._load_existing_graph()
    
    def process_event(self, event: CrossBridgeEvent):
        """
        Process event to update coverage graph.
        
        Different event types contribute different insights:
        - test_start/end: test existence and execution
        - api_call: test → API relationships
        - ui_interaction: test → page/component relationships
        - step: test behavior breakdown
        """
        # Ensure test node exists
        self._ensure_test_node(event)
        
        # Process based on event type
        if event.event_type == EventType.API_CALL.value:
            self._process_api_call(event)
        elif event.event_type == EventType.UI_INTERACTION.value:
            self._process_ui_interaction(event)
        elif event.event_type == EventType.STEP.value:
            self._process_step(event)
    
    def _ensure_test_node(self, event: CrossBridgeEvent):
        """Ensure test node exists in graph"""
        test_node_id = f"test:{event.framework}:{event.test_id}"
        
        if test_node_id not in self.graph_nodes:
            node = CoverageNode(
                node_id=test_node_id,
                node_type='test',
                metadata={
                    'framework': event.framework,
                    'test_id': event.test_id,
                    'version': event.application_version,
                    'product': event.product_name,
                    'environment': event.environment
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.graph_nodes[test_node_id] = node
            
            if self.db_connection:
                self._persist_node(node)
    
    def _process_api_call(self, event: CrossBridgeEvent):
        """Process API call event to create test → API edges"""
        if not event.metadata or 'endpoint' not in event.metadata:
            return
        
        endpoint = event.metadata['endpoint']
        method = event.metadata.get('http_method', 'GET')
        
        # Create API node
        api_node_id = f"api:{method}:{endpoint}"
        if api_node_id not in self.graph_nodes:
            api_node = CoverageNode(
                node_id=api_node_id,
                node_type='api',
                metadata={
                    'endpoint': endpoint,
                    'method': method
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.graph_nodes[api_node_id] = api_node
            
            if self.db_connection:
                self._persist_node(api_node)
        
        # Create edge: test → API
        test_node_id = f"test:{event.framework}:{event.test_id}"
        self._create_or_update_edge(
            from_node=test_node_id,
            to_node=api_node_id,
            edge_type='calls_api',
            metadata={'status_code': event.metadata.get('status_code')}
        )
    
    def _process_ui_interaction(self, event: CrossBridgeEvent):
        """Process UI interaction to create test → page/component edges"""
        if not event.metadata:
            return
        
        # Page visit
        if 'page_url' in event.metadata:
            page_url = event.metadata['page_url']
            page_node_id = f"page:{page_url}"
            
            if page_node_id not in self.graph_nodes:
                page_node = CoverageNode(
                    node_id=page_node_id,
                    node_type='page',
                    metadata={'url': page_url},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.graph_nodes[page_node_id] = page_node
                
                if self.db_connection:
                    self._persist_node(page_node)
            
            # Edge: test → page
            test_node_id = f"test:{event.framework}:{event.test_id}"
            self._create_or_update_edge(
                from_node=test_node_id,
                to_node=page_node_id,
                edge_type='visits_page',
                metadata={}
            )
        
        # UI component interaction
        if 'component_name' in event.metadata:
            component = event.metadata['component_name']
            component_node_id = f"ui:{component}"
            
            if component_node_id not in self.graph_nodes:
                component_node = CoverageNode(
                    node_id=component_node_id,
                    node_type='ui_component',
                    metadata={
                        'name': component,
                        'type': event.metadata.get('component_type')
                    },
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.graph_nodes[component_node_id] = component_node
                
                if self.db_connection:
                    self._persist_node(component_node)
            
            # Edge: test → UI component
            test_node_id = f"test:{event.framework}:{event.test_id}"
            self._create_or_update_edge(
                from_node=test_node_id,
                to_node=component_node_id,
                edge_type='interacts_with',
                metadata={'action': event.metadata.get('action')}
            )
    
    def _process_step(self, event: CrossBridgeEvent):
        """Process step/keyword execution"""
        # Steps can be used to infer feature coverage
        if not event.metadata or 'step_name' not in event.metadata:
            return
        
        step_name = event.metadata['step_name']
        
        # Create feature node (inferred from step name)
        feature_node_id = f"feature:{step_name}"
        if feature_node_id not in self.graph_nodes:
            feature_node = CoverageNode(
                node_id=feature_node_id,
                node_type='feature',
                metadata={'name': step_name},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.graph_nodes[feature_node_id] = feature_node
            
            if self.db_connection:
                self._persist_node(feature_node)
        
        # Edge: test → feature
        test_node_id = f"test:{event.framework}:{event.test_id}"
        self._create_or_update_edge(
            from_node=test_node_id,
            to_node=feature_node_id,
            edge_type='tests',
            metadata={}
        )
    
    def _create_or_update_edge(self, from_node: str, to_node: str, edge_type: str, metadata: dict):
        """Create new edge or update existing edge weight"""
        # Find existing edge
        existing = None
        for edge in self.graph_edges:
            if edge.from_node == from_node and edge.to_node == to_node and edge.edge_type == edge_type:
                existing = edge
                break
        
        if existing:
            # Update existing edge
            existing.weight += 1
            existing.last_seen = datetime.utcnow()
            existing.metadata.update(metadata)
            
            if self.db_connection:
                self._update_edge_weight(existing)
        else:
            # Create new edge
            new_edge = CoverageEdge(
                from_node=from_node,
                to_node=to_node,
                edge_type=edge_type,
                weight=1,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                metadata=metadata
            )
            self.graph_edges.append(new_edge)
            
            if self.db_connection:
                self._persist_edge(new_edge)
    
    def get_test_coverage(self, test_id: str) -> Dict[str, List[str]]:
        """
        Get what a test covers.
        
        Returns:
            Dict with keys: apis, pages, ui_components, features
        """
        test_node_id = f"test:{test_id}"
        
        coverage = {
            'apis': [],
            'pages': [],
            'ui_components': [],
            'features': []
        }
        
        for edge in self.graph_edges:
            if edge.from_node != test_node_id:
                continue
            
            target_node = self.graph_nodes.get(edge.to_node)
            if not target_node:
                continue
            
            if target_node.node_type == 'api':
                coverage['apis'].append(target_node.metadata['endpoint'])
            elif target_node.node_type == 'page':
                coverage['pages'].append(target_node.metadata['url'])
            elif target_node.node_type == 'ui_component':
                coverage['ui_components'].append(target_node.metadata['name'])
            elif target_node.node_type == 'feature':
                coverage['features'].append(target_node.metadata['name'])
        
        return coverage
    
    def get_impacted_tests(self, changed_resource: str, resource_type: str) -> List[str]:
        """
        Get tests impacted by a change to a resource (API, page, component).
        
        Args:
            changed_resource: Resource identifier (e.g., "/api/users")
            resource_type: Type of resource (api, page, ui_component)
        
        Returns:
            List of test IDs that interact with this resource
        """
        resource_node_id = f"{resource_type}:{changed_resource}"
        impacted = []
        
        for edge in self.graph_edges:
            if edge.to_node == resource_node_id:
                # This is a test that uses the resource
                test_node = self.graph_nodes.get(edge.from_node)
                if test_node and test_node.node_type == 'test':
                    impacted.append(test_node.metadata['test_id'])
        
        return impacted
    
    def _persist_node(self, node: CoverageNode):
        """Persist node to database"""
        if not self.db_connection:
            return
        
        cursor = self.db_connection.cursor()
        cursor.execute("""
            INSERT INTO coverage_graph_nodes (
                node_id, node_type, metadata, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (node_id) DO UPDATE SET
                metadata = EXCLUDED.metadata,
                updated_at = EXCLUDED.updated_at
        """, (node.node_id, node.node_type, node.metadata, node.created_at, node.updated_at))
        self.db_connection.commit()
        cursor.close()
    
    def _persist_edge(self, edge: CoverageEdge):
        """Persist edge to database"""
        if not self.db_connection:
            return
        
        cursor = self.db_connection.cursor()
        cursor.execute("""
            INSERT INTO coverage_graph_edges (
                from_node, to_node, edge_type, weight, first_seen, last_seen, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (edge.from_node, edge.to_node, edge.edge_type, edge.weight, 
              edge.first_seen, edge.last_seen, edge.metadata))
        self.db_connection.commit()
        cursor.close()
    
    def _update_edge_weight(self, edge: CoverageEdge):
        """Update edge weight in database"""
        if not self.db_connection:
            return
        
        cursor = self.db_connection.cursor()
        cursor.execute("""
            UPDATE coverage_graph_edges 
            SET weight = %s, last_seen = %s, metadata = %s
            WHERE from_node = %s AND to_node = %s AND edge_type = %s
        """, (edge.weight, edge.last_seen, edge.metadata, 
              edge.from_node, edge.to_node, edge.edge_type))
        self.db_connection.commit()
        cursor.close()
    
    def _load_existing_graph(self):
        """Load existing coverage graph from database"""
        # TODO: Implement graph loading
        pass
