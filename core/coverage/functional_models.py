"""
Functional Coverage & Impact Analysis Models for CrossBridge.

Implements:
- Functional Coverage Map
- Test-to-Feature Coverage
- Change Impact Surface
- External Test Case Integration (TestRail, Zephyr, etc.)

These models enable honest, actionable coverage reporting without fake percentages.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set
from datetime import datetime, timezone
from enum import Enum
import uuid


# ========================================
# 1️⃣ ENUMS
# ========================================

class FeatureType(str, Enum):
    """Type of feature in the system."""
    API = "api"
    API_ENDPOINT = "api_endpoint"     # Specific API endpoint
    SERVICE = "service"
    BDD = "bdd"
    MODULE = "module"
    COMPONENT = "component"
    UI_COMPONENT = "ui_component"     # UI element/component
    UI_FLOW = "ui_flow"               # UI user flow
    FEATURE_FLAG = "feature_flag"     # Feature toggle


class FeatureSource(str, Enum):
    """Source where feature was discovered."""
    CUCUMBER = "cucumber"
    JIRA = "jira"
    CODE = "code"
    MANUAL = "manual"
    API_SPEC = "api_spec"
    NETWORK_CAPTURE = "network_capture"  # From network traffic
    UI_MAPPING = "ui_mapping"            # From UI element mapping
    CONTRACT = "contract"                 # From API contracts


class ExternalSystem(str, Enum):
    """External test management systems."""
    TESTRAIL = "testrail"
    ZEPHYR = "zephyr"
    QTEST = "qtest"
    JIRA = "jira"
    MANUAL = "manual"


class MappingSource(str, Enum):
    """Source of test mapping."""
    ANNOTATION = "annotation"
    TAG = "tag"
    FILE = "file"
    API = "api"
    COVERAGE = "coverage"           # Instrumented code coverage
    NETWORK = "network"             # Network traffic capture
    UI_INTERACTION = "ui_interaction"  # UI element interaction
    CONTRACT = "contract"           # API contract validation
    AI = "ai"
    MANUAL = "manual"


class ChangeType(str, Enum):
    """Type of code change."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class ImpactReason(str, Enum):
    """Reason for test impact."""
    DIRECT_COVERAGE = "direct_coverage"
    FEATURE_LINK = "feature_link"
    TRANSITIVE = "transitive"


# ========================================
# 2️⃣ CORE MODELS
# ========================================

@dataclass
class Feature:
    """
    Represents a functional unit of the product.
    
    Features can be:
    - API endpoints
    - Services/components
    - BDD features
    - Code modules
    """
    name: str
    type: FeatureType
    source: FeatureSource
    description: Optional[str] = None
    parent_feature_id: Optional[uuid.UUID] = None
    metadata: Optional[Dict] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CodeUnit:
    """
    Represents an individual code unit (class, method, function).
    
    This is more granular than files - allows precise coverage tracking.
    """
    file_path: str
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    package_name: Optional[str] = None
    module_name: Optional[str] = None  # For Python/Robot
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    complexity: Optional[int] = None  # Cyclomatic complexity
    metadata: Optional[Dict] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def full_name(self) -> str:
        """Get fully qualified name."""
        parts = []
        if self.package_name:
            parts.append(self.package_name)
        if self.class_name:
            parts.append(self.class_name)
        if self.method_name:
            parts.append(self.method_name)
        return ".".join(parts) if parts else self.file_path
    
    def __hash__(self):
        """Allow use in sets."""
        return hash((self.file_path, self.class_name, self.method_name))
    
    def __eq__(self, other):
        """Equality based on file, class, and method."""
        if not isinstance(other, CodeUnit):
            return False
        return (self.file_path == other.file_path and 
                self.class_name == other.class_name and 
                self.method_name == other.method_name)


@dataclass
class ExternalTestCase:
    """
    External test case reference (TestRail, Zephyr, qTest, etc.).
    
    CrossBridge is NOT the source of truth - we just reference external IDs.
    """
    system: ExternalSystem
    external_id: str  # e.g. "C12345", "T-1234"
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None  # high | medium | low
    status: Optional[str] = None  # active | inactive | deprecated
    metadata: Optional[Dict] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    @property
    def full_id(self) -> str:
        """Get system:id format (e.g., 'testrail:C12345')."""
        return f"{self.system.value}:{self.external_id}"


@dataclass
class ExternalTestRef:
    """
    Lightweight reference to external test case.
    
    Used during extraction/parsing before persistence.
    """
    system: str  # "testrail", "zephyr", etc.
    external_id: str  # "C12345"
    source: str  # "annotation", "tag", etc.
    confidence: float = 1.0


@dataclass
class TestCaseExternalMap:
    """
    Maps CrossBridge test cases to external test case IDs.
    
    Supports many-to-many relationships.
    """
    test_case_id: uuid.UUID
    external_test_case_id: uuid.UUID
    confidence: float = 1.0  # 0.0 to 1.0
    source: MappingSource = MappingSource.MANUAL
    discovery_run_id: Optional[uuid.UUID] = None
    metadata: Optional[Dict] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


@dataclass
class TestFeatureMap:
    """
    Maps tests to features - enables Test-to-Feature Coverage.
    
    Answers: "Which tests validate which features?"
    """
    test_case_id: uuid.UUID
    feature_id: uuid.UUID
    confidence: float = 1.0  # 0.0 to 1.0
    source: MappingSource = MappingSource.MANUAL
    discovery_run_id: Optional[uuid.UUID] = None
    metadata: Optional[Dict] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TestCodeCoverageMap:
    """
    Maps tests to code units via coverage data.
    
    Enables:
    - Functional Coverage Map
    - Change Impact Surface
    """
    test_case_id: uuid.UUID
    code_unit_id: uuid.UUID
    coverage_type: str  # instruction | line | branch | method
    covered_count: int = 0
    missed_count: int = 0
    coverage_percentage: float = 0.0
    confidence: float = 1.0
    execution_mode: Optional[str] = None  # isolated | small_batch | full_suite
    discovery_run_id: Optional[uuid.UUID] = None
    metadata: Optional[Dict] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


@dataclass
class ChangeEvent:
    """
    Represents a code change (from Git).
    
    Used for Change Impact Surface analysis.
    """
    commit_sha: str
    file_path: str
    timestamp: datetime
    commit_message: Optional[str] = None
    author: Optional[str] = None
    change_type: Optional[ChangeType] = None
    lines_added: int = 0
    lines_removed: int = 0
    branch: Optional[str] = None
    metadata: Optional[Dict] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


@dataclass
class ChangeImpact:
    """
    Pre-computed change impact for performance.
    
    Caches the relationship between changes and impacted tests.
    """
    change_event_id: uuid.UUID
    test_case_id: uuid.UUID
    feature_id: Optional[uuid.UUID] = None
    impact_score: float = 1.0  # 0.0 to 1.0
    impact_reason: Optional[ImpactReason] = None
    metadata: Optional[Dict] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


# ========================================
# 2️⃣B BEHAVIORAL COVERAGE MODELS (SaaS-Friendly)
# ========================================

@dataclass
class ApiEndpointCoverage:
    """
    Tracks API endpoint coverage (behavioral, not instrumented).
    
    Captures which API endpoints are exercised during test execution.
    Essential for SaaS/black-box testing where backend instrumentation is not available.
    """
    test_case_id: uuid.UUID
    endpoint_path: str                    # e.g., /api/v1/users/{id}
    http_method: str                      # GET, POST, PUT, DELETE, etc.
    status_code: int                      # HTTP response code
    request_schema: Optional[Dict] = None # Request payload schema
    response_schema: Optional[Dict] = None # Response payload schema
    feature_flags: Optional[List[str]] = field(default_factory=list)  # Feature flags active
    execution_time_ms: Optional[float] = None
    metadata: Optional[Dict] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    @property
    def full_endpoint(self) -> str:
        """Full endpoint representation."""
        return f"{self.http_method} {self.endpoint_path}"


@dataclass
class UiComponentCoverage:
    """
    Tracks UI component/element coverage (behavioral).
    
    Captures which UI components are interacted with during test execution.
    Useful for UI testing frameworks (Selenium, Playwright, Cypress).
    """
    test_case_id: uuid.UUID
    component_name: str                   # Component/element name
    component_type: str                   # button, input, dropdown, etc.
    selector: Optional[str] = None        # CSS selector or XPath
    page_url: Optional[str] = None        # Page where component appears
    interaction_type: str = "click"       # click, type, hover, etc.
    interaction_count: int = 1
    metadata: Optional[Dict] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


@dataclass
class NetworkCapture:
    """
    Captures network traffic during test execution.
    
    Records all API calls made during test execution for behavioral coverage.
    Alternative to backend instrumentation for SaaS applications.
    """
    test_case_id: uuid.UUID
    request_url: str
    request_method: str
    request_headers: Optional[Dict] = None
    request_body: Optional[str] = None
    response_status: Optional[int] = None
    response_headers: Optional[Dict] = None
    response_body: Optional[str] = None
    duration_ms: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    metadata: Optional[Dict] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class ContractCoverage:
    """
    Tracks API contract/schema coverage.
    
    Verifies which request/response schemas are exercised.
    Useful for API testing and contract validation.
    """
    test_case_id: uuid.UUID
    contract_name: str                    # e.g., UserAPI.getUser
    contract_version: str                 # API version
    request_fields_covered: Set[str] = field(default_factory=set)
    response_fields_covered: Set[str] = field(default_factory=set)
    validation_passed: bool = True
    validation_errors: Optional[List[str]] = None
    metadata: Optional[Dict] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


# ========================================
# 3️⃣ CONSOLE OUTPUT MODELS
# ========================================

@dataclass
class FunctionalCoverageMapEntry:
    """
    Single entry in Functional Coverage Map.
    
    Shows: Code Unit → Tests Covering → TestRail TCs
    """
    code_unit: str  # file_path or full_name
    test_count: int
    testrail_tcs: List[str] = field(default_factory=list)
    avg_coverage: Optional[float] = None
    
    def to_row(self) -> List:
        """Convert to table row for console output."""
        tc_str = ", ".join(self.testrail_tcs[:5])  # Limit to 5 for readability
        if len(self.testrail_tcs) > 5:
            tc_str += f" (+{len(self.testrail_tcs) - 5} more)"
        
        return [
            self.code_unit,
            self.test_count,
            tc_str if tc_str else "-"
        ]


@dataclass
class TestToFeatureCoverageEntry:
    """
    Single entry in Test-to-Feature Coverage.
    
    Shows: Feature → Test → TestRail TC
    """
    feature: str
    feature_type: str
    test_name: str
    testrail_tc: Optional[str] = None
    confidence: Optional[float] = None
    
    def to_row(self) -> List:
        """Convert to table row for console output."""
        return [
            self.feature,
            self.test_name,
            self.testrail_tc if self.testrail_tc else "-"
        ]


@dataclass
class ChangeImpactSurfaceEntry:
    """
    Single entry in Change Impact Surface.
    
    Shows: Impacted Test → Feature → TestRail TC
    """
    impacted_test: str
    feature: Optional[str] = None
    testrail_tc: Optional[str] = None
    coverage_percentage: Optional[float] = None
    
    def to_row(self) -> List:
        """Convert to table row for console output."""
        return [
            self.impacted_test,
            self.feature if self.feature else "-",
            self.testrail_tc if self.testrail_tc else "-"
        ]


# ========================================
# 4️⃣ AGGREGATE MODELS
# ========================================

@dataclass
class FunctionalCoverageMapReport:
    """
    Complete Functional Coverage Map report.
    """
    entries: List[FunctionalCoverageMapEntry]
    total_code_units: int
    total_tests: int
    total_external_tcs: int
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


@dataclass
class TestToFeatureCoverageReport:
    """
    Complete Test-to-Feature Coverage report.
    """
    entries: List[TestToFeatureCoverageEntry]
    total_features: int
    total_tests: int
    features_without_tests: int
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


@dataclass
class ChangeImpactSurfaceReport:
    """
    Complete Change Impact Surface report.
    """
    changed_file: str
    entries: List[ChangeImpactSurfaceEntry]
    total_impacted_tests: int
    total_impacted_features: int
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


# ========================================
# 5️⃣ CONVERSION HELPERS
# ========================================

def parse_external_test_refs(
    annotations: List[str],
    tags: List[str]
) -> List[ExternalTestRef]:
    """
    Parse external test case references from annotations and tags.
    
    Supports:
    - @TestRail(id = "C12345")
    - @ExternalTestCase("C12345")
    - @testrail:C12345
    - [Tags] testrail:C12345
    
    Args:
        annotations: List of annotation strings
        tags: List of tag strings
        
    Returns:
        List of ExternalTestRef objects
    """
    refs = []
    
    # Parse annotations
    for annotation in annotations:
        # @TestRail(id = "C12345")
        if "TestRail" in annotation and "id" in annotation:
            import re
            match = re.search(r'id\s*=\s*["\']([^"\']+)["\']', annotation)
            if match:
                refs.append(ExternalTestRef(
                    system="testrail",
                    external_id=match.group(1),
                    source="annotation"
                ))
        
        # @ExternalTestCase("C12345")
        elif "ExternalTestCase" in annotation:
            import re
            match = re.search(r'["\']([^"\']+)["\']', annotation)
            if match:
                refs.append(ExternalTestRef(
                    system="testrail",  # Default to TestRail
                    external_id=match.group(1),
                    source="annotation"
                ))
    
    # Parse tags
    for tag in tags:
        # @testrail:C12345 or [Tags] testrail:C12345
        # Remove @ prefix if present
        clean_tag = tag.lstrip('@')
        
        if ":" in clean_tag:
            parts = clean_tag.split(":", 1)
            system = parts[0].strip().lower()
            external_id = parts[1].strip()
            
            # Validate system
            if system in ["testrail", "zephyr", "qtest", "jira"]:
                refs.append(ExternalTestRef(
                    system=system,
                    external_id=external_id,
                    source="tag"
                ))
    
    return refs
