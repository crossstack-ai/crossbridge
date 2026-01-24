# Copyright (c) 2025 Vikas Verma
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

# Copyright (c) 2025 Vikas Verma
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Enhanced Test Memory Model for CrossBridge Intelligent Test Assistance.

This model extends semantic embeddings with structural signals from AST/ASM analysis,
enabling hybrid intelligence (semantic + structural) for test assistance.

Design Principles:
- Framework-agnostic core model
- Structural signals normalized across languages
- Semantic embeddings for intent discovery
- Metadata for filtering and prioritization
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TestType(str, Enum):
    """Test classification types."""
    POSITIVE = "positive"  # Happy path tests
    NEGATIVE = "negative"  # Error/edge case tests
    BOUNDARY = "boundary"  # Boundary condition tests
    INTEGRATION = "integration"  # Integration tests
    UNIT = "unit"  # Unit tests
    E2E = "e2e"  # End-to-end tests


class Priority(str, Enum):
    """Test priority levels."""
    P0 = "P0"  # Critical - must run always
    P1 = "P1"  # High - run on major changes
    P2 = "P2"  # Medium - run regularly
    P3 = "P3"  # Low - run periodically


@dataclass
class APICall:
    """Represents an API call extracted from test code."""
    method: str  # GET, POST, PUT, DELETE, etc.
    endpoint: str  # /api/users, /checkout, etc.
    expected_status: Optional[int] = None  # 200, 404, 500, etc.
    request_body: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None


@dataclass
class Assertion:
    """Represents an assertion extracted from test code."""
    type: str  # assertEqual, assertRaises, expect, verify, etc.
    target: str  # Variable or expression being asserted
    expected_value: Optional[Any] = None
    comparator: Optional[str] = None  # ==, !=, >, <, contains, etc.


@dataclass
class StructuralSignals:
    """
    Structural information extracted via AST/ASM.
    
    These signals enable precise matching and validation beyond semantic similarity.
    Framework-agnostic representation.
    """
    
    # Code structure
    imports: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    
    # UI interactions (for web/mobile testing)
    ui_interactions: List[str] = field(default_factory=list)
    page_objects: List[str] = field(default_factory=list)
    
    # API interactions
    api_calls: List[APICall] = field(default_factory=list)
    
    # Validations
    assertions: List[Assertion] = field(default_factory=list)
    
    # Expected outcomes
    expected_status_codes: List[int] = field(default_factory=list)
    expected_exceptions: List[str] = field(default_factory=list)
    
    # Control flow patterns
    has_retry_logic: bool = False
    has_timeout: bool = False
    has_async_await: bool = False
    has_loop: bool = False
    has_conditional: bool = False
    
    # Dependencies
    external_services: List[str] = field(default_factory=list)
    database_operations: List[str] = field(default_factory=list)
    file_operations: List[str] = field(default_factory=list)
    
    # Test fixtures/setup
    fixtures: List[str] = field(default_factory=list)
    setup_methods: List[str] = field(default_factory=list)
    teardown_methods: List[str] = field(default_factory=list)


@dataclass
class SemanticSignals:
    """
    Semantic information for intent-based discovery.
    
    From Phase-1 embeddings system.
    """
    
    intent_text: str = ""  # Natural language description of test intent
    embedding: Optional[List[float]] = None  # Vector embedding
    keywords: List[str] = field(default_factory=list)
    business_context: Optional[str] = None


@dataclass
class TestMetadata:
    """
    Metadata for filtering, prioritization, and organization.
    """
    
    test_type: TestType = TestType.POSITIVE
    priority: Priority = Priority.P2
    feature: Optional[str] = None
    component: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    owner: Optional[str] = None
    jira_ticket: Optional[str] = None
    execution_time_ms: Optional[int] = None
    flakiness_score: float = 0.0


@dataclass
class UnifiedTestMemory:
    """
    Unified test memory model combining semantic and structural intelligence.
    
    This is the single source of truth for Phase-2.
    All downstream features (RAG, recommendations, generation) use this model.
    """
    
    # Core identification
    test_id: str  # UUID
    framework: str  # pytest, junit, robot, playwright, cypress, etc.
    language: str  # python, java, javascript, csharp, etc.
    file_path: str  # Relative path to test file
    test_name: str  # Function/method/scenario name
    
    # Hybrid intelligence signals
    semantic: SemanticSignals = field(default_factory=SemanticSignals)
    structural: StructuralSignals = field(default_factory=StructuralSignals)
    metadata: TestMetadata = field(default_factory=TestMetadata)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_executed_at: Optional[datetime] = None
    
    # Source tracking
    source_hash: Optional[str] = None  # Git commit hash or file hash
    version: int = 1  # Increment on updates
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "test_id": self.test_id,
            "framework": self.framework,
            "language": self.language,
            "file_path": self.file_path,
            "test_name": self.test_name,
            "semantic": {
                "intent_text": self.semantic.intent_text,
                "embedding": self.semantic.embedding,
                "keywords": self.semantic.keywords,
                "business_context": self.semantic.business_context,
            },
            "structural": {
                "api_calls": [
                    {
                        "method": call.method,
                        "endpoint": call.endpoint,
                        "expected_status": call.expected_status,
                        "request_body": call.request_body,
                        "headers": call.headers,
                    }
                    for call in self.structural.api_calls
                ],
                "assertions": [
                    {
                        "type": a.type,
                        "target": a.target,
                        "expected_value": a.expected_value,
                        "comparator": a.comparator,
                    }
                    for a in self.structural.assertions
                ],
                "expected_status_codes": self.structural.expected_status_codes,
                "expected_exceptions": self.structural.expected_exceptions,
                "has_retry_logic": self.structural.has_retry_logic,
                "has_timeout": self.structural.has_timeout,
                "has_async_await": self.structural.has_async_await,
                "has_loop": self.structural.has_loop,
                "has_conditional": self.structural.has_conditional,
                "external_services": self.structural.external_services,
                "database_operations": self.structural.database_operations,
                "file_operations": self.structural.file_operations,
                "fixtures": self.structural.fixtures,
                "setup_methods": self.structural.setup_methods,
                "teardown_methods": self.structural.teardown_methods,
            },
            "metadata": {
                "test_type": self.metadata.test_type.value,
                "priority": self.metadata.priority.value,
                "feature": self.metadata.feature,
                "component": self.metadata.component,
                "tags": self.metadata.tags,
                "owner": self.metadata.owner,
                "jira_ticket": self.metadata.jira_ticket,
                "execution_time_ms": self.metadata.execution_time_ms,
                "flakiness_score": self.metadata.flakiness_score,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_executed_at": self.last_executed_at.isoformat()
            if self.last_executed_at
            else None,
            "source_hash": self.source_hash,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedTestMemory":
        """Create from dictionary."""
        semantic = SemanticSignals(
            intent_text=data["semantic"]["intent_text"],
            embedding=data["semantic"].get("embedding"),
            keywords=data["semantic"].get("keywords", []),
            business_context=data["semantic"].get("business_context"),
        )
        
        structural = StructuralSignals(
            api_calls=[
                APICall(
                    method=call["method"],
                    endpoint=call["endpoint"],
                    expected_status=call.get("expected_status"),
                    request_body=call.get("request_body"),
                    headers=call.get("headers"),
                )
                for call in data["structural"].get("api_calls", [])
            ],
            assertions=[
                Assertion(
                    type=a["type"],
                    target=a["target"],
                    expected_value=a.get("expected_value"),
                    comparator=a.get("comparator"),
                )
                for a in data["structural"].get("assertions", [])
            ],
            expected_status_codes=data["structural"].get("expected_status_codes", []),
            expected_exceptions=data["structural"].get("expected_exceptions", []),
            has_retry_logic=data["structural"].get("has_retry_logic", False),
            has_timeout=data["structural"].get("has_timeout", False),
            has_async_await=data["structural"].get("has_async_await", False),
            has_loop=data["structural"].get("has_loop", False),
            has_conditional=data["structural"].get("has_conditional", False),
            external_services=data["structural"].get("external_services", []),
            database_operations=data["structural"].get("database_operations", []),
            file_operations=data["structural"].get("file_operations", []),
            fixtures=data["structural"].get("fixtures", []),
            setup_methods=data["structural"].get("setup_methods", []),
            teardown_methods=data["structural"].get("teardown_methods", []),
        )
        
        metadata = TestMetadata(
            test_type=TestType(data["metadata"]["test_type"]),
            priority=Priority(data["metadata"]["priority"]),
            feature=data["metadata"].get("feature"),
            component=data["metadata"].get("component"),
            tags=data["metadata"].get("tags", []),
            owner=data["metadata"].get("owner"),
            jira_ticket=data["metadata"].get("jira_ticket"),
            execution_time_ms=data["metadata"].get("execution_time_ms"),
            flakiness_score=data["metadata"].get("flakiness_score", 0.0),
        )
        
        return cls(
            test_id=data["test_id"],
            framework=data["framework"],
            language=data["language"],
            file_path=data["file_path"],
            test_name=data["test_name"],
            semantic=semantic,
            structural=structural,
            metadata=metadata,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            last_executed_at=datetime.fromisoformat(data["last_executed_at"])
            if data.get("last_executed_at")
            else None,
            source_hash=data.get("source_hash"),
            version=data.get("version", 1),
        )


def calculate_structural_overlap(test1: UnifiedTestMemory, test2: UnifiedTestMemory) -> float:
    """
    Calculate structural similarity between two tests.
    
    Used for test recommendations and duplicate detection.
    Returns score 0.0-1.0.
    """
    score = 0.0
    weights = {
        "api_overlap": 0.3,
        "assertion_overlap": 0.2,
        "status_code_overlap": 0.2,
        "exception_overlap": 0.1,
        "dependency_overlap": 0.2,
    }
    
    # API endpoint overlap
    endpoints1 = {call.endpoint for call in test1.structural.api_calls}
    endpoints2 = {call.endpoint for call in test2.structural.api_calls}
    if endpoints1 or endpoints2:
        api_overlap = len(endpoints1 & endpoints2) / len(endpoints1 | endpoints2)
        score += api_overlap * weights["api_overlap"]
    
    # Status code overlap
    codes1 = set(test1.structural.expected_status_codes)
    codes2 = set(test2.structural.expected_status_codes)
    if codes1 or codes2:
        code_overlap = len(codes1 & codes2) / len(codes1 | codes2)
        score += code_overlap * weights["status_code_overlap"]
    
    # Exception overlap
    exc1 = set(test1.structural.expected_exceptions)
    exc2 = set(test2.structural.expected_exceptions)
    if exc1 or exc2:
        exc_overlap = len(exc1 & exc2) / len(exc1 | exc2)
        score += exc_overlap * weights["exception_overlap"]
    
    # External service overlap
    svc1 = set(test1.structural.external_services)
    svc2 = set(test2.structural.external_services)
    if svc1 or svc2:
        svc_overlap = len(svc1 & svc2) / len(svc1 | svc2)
        score += svc_overlap * weights["dependency_overlap"]
    
    return min(score, 1.0)
