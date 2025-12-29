"""
Page Object to Test mapping models.

Maps which Page Objects are used by which tests for impact analysis.
"""

from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional
from enum import Enum
from datetime import datetime


class MappingSource(Enum):
    """
    Source of the Page Object mapping.
    
    Unified enum supporting all phases (static AST, coverage, AI).
    """
    STATIC_AST = "static_ast"           # Parsed from source code (Phase 1)
    RUNTIME_TRACE = "runtime_trace"     # Captured during test execution (Phase 2)
    CODE_COVERAGE = "coverage"          # Derived from coverage data (Phase 2)
    AI = "ai"                          # AI-inferred mappings (Phase 3)
    MANUAL = "manual"                   # Manually specified
    INFERRED = "inferred"              # Inferred from patterns


@dataclass
class PageObjectReference:
    """
    A reference to a Page Object from a test.
    
    Attributes:
        page_object_class: Fully qualified Page Object class name
        usage_type: How the PO is used (instantiation, import, field, method_call)
        line_number: Line number where reference occurs
        source_file: File where the test is located
    """
    page_object_class: str
    usage_type: str  # "instantiation", "import", "field", "method_call", "fixture"
    line_number: Optional[int] = None
    source_file: Optional[str] = None
    
    def get_simple_name(self) -> str:
        """Get simple class name from qualified name."""
        return self.page_object_class.split(".")[-1]


@dataclass
class TestToPageObjectMapping:
    """
    Mapping between a test and the Page Objects it uses.
    
    Attributes:
        test_id: Unique test identifier (e.g., "com.example.LoginTest.testValidLogin")
        test_file: Source file containing the test
        page_objects: Set of Page Object class names used by this test
        references: Detailed references with line numbers
        mapping_source: How this mapping was detected
        confidence: Confidence score (0.0-1.0)
        detected_at: When this mapping was detected
    """
    test_id: str
    test_file: str
    page_objects: Set[str] = field(default_factory=set)
    references: List[PageObjectReference] = field(default_factory=list)
    mapping_source: MappingSource = MappingSource.STATIC_AST
    confidence: float = 1.0
    detected_at: datetime = field(default_factory=datetime.now)
    
    def add_page_object(self, page_object: str, usage_type: str = "unknown", 
                       line_number: Optional[int] = None):
        """Add a Page Object reference to this test."""
        self.page_objects.add(page_object)
        self.references.append(PageObjectReference(
            page_object_class=page_object,
            usage_type=usage_type,
            line_number=line_number,
            source_file=self.test_file
        ))
    
    def get_page_object_count(self) -> int:
        """Get number of unique Page Objects used."""
        return len(self.page_objects)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for persistence."""
        return {
            "test_id": self.test_id,
            "test_file": self.test_file,
            "page_objects": list(self.page_objects),
            "references": [
                {
                    "page_object": ref.page_object_class,
                    "usage_type": ref.usage_type,
                    "line_number": ref.line_number,
                    "source_file": ref.source_file
                }
                for ref in self.references
            ],
            "mapping_source": self.mapping_source.value,
            "confidence": self.confidence,
            "detected_at": self.detected_at.isoformat()
        }
    
    def to_unified_model(self, page_object: str) -> dict:
        """
        Convert to unified data model format for a specific Page Object.
        
        Format: {test_id, page_object, source, confidence}
        
        Args:
            page_object: Name of the Page Object to include
            
        Returns:
            Dictionary in unified model format
        """
        return {
            "test_id": self.test_id,
            "page_object": page_object,
            "source": self.mapping_source.value,
            "confidence": self.confidence
        }


@dataclass
class PageObjectImpactMap:
    """
    Complete impact map for a project.
    
    Maps Page Objects → Tests that use them.
    Used for impact analysis when Page Objects change.
    
    Attributes:
        project_root: Root directory of the project
        mappings: List of test-to-pageobject mappings
        reverse_index: Page Object → Tests index for fast lookup
    """
    project_root: str
    mappings: List[TestToPageObjectMapping] = field(default_factory=list)
    reverse_index: Dict[str, Set[str]] = field(default_factory=dict)
    
    def add_mapping(self, mapping: TestToPageObjectMapping):
        """Add a test-to-pageobject mapping."""
        self.mappings.append(mapping)
        
        # Update reverse index
        for po in mapping.page_objects:
            if po not in self.reverse_index:
                self.reverse_index[po] = set()
            self.reverse_index[po].add(mapping.test_id)
    
    def get_impacted_tests(self, page_object: str) -> Set[str]:
        """
        Get all tests impacted by a Page Object change.
        
        Args:
            page_object: Page Object class name (can be simple or qualified).
            
        Returns:
            Set of test IDs that use this Page Object.
        """
        # Try exact match first
        if page_object in self.reverse_index:
            return self.reverse_index[page_object].copy()
        
        # Try simple name match (LoginPage vs com.example.pages.LoginPage)
        simple_name = page_object.split(".")[-1]
        impacted = set()
        
        for po_class, tests in self.reverse_index.items():
            if po_class.split(".")[-1] == simple_name:
                impacted.update(tests)
        
        return impacted
    
    def get_page_objects_for_test(self, test_id: str) -> Set[str]:
        """Get all Page Objects used by a test."""
        for mapping in self.mappings:
            if mapping.test_id == test_id:
                return mapping.page_objects.copy()
        return set()
    
    def get_statistics(self) -> dict:
        """Get statistics about the impact map."""
        return {
            "total_tests": len(self.mappings),
            "total_page_objects": len(self.reverse_index),
            "total_mappings": len(self.mappings),
            "avg_page_objects_per_test": sum(len(m.page_objects) for m in self.mappings) / len(self.mappings) if self.mappings else 0,
            "max_page_objects_in_test": max((len(m.page_objects) for m in self.mappings), default=0),
            "most_used_page_objects": self._get_most_used_page_objects(5)
        }
    
    def _get_most_used_page_objects(self, top_n: int = 5) -> List[tuple]:
        """Get most frequently used Page Objects."""
        usage_counts = [(po, len(tests)) for po, tests in self.reverse_index.items()]
        usage_counts.sort(key=lambda x: x[1], reverse=True)
        return usage_counts[:top_n]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for persistence."""
        return {
            "project_root": self.project_root,
            "mappings": [m.to_dict() for m in self.mappings],
            "statistics": self.get_statistics()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PageObjectImpactMap":
        """Create from dictionary."""
        impact_map = cls(project_root=data["project_root"])
        
        for mapping_data in data.get("mappings", []):
            mapping = TestToPageObjectMapping(
                test_id=mapping_data["test_id"],
                test_file=mapping_data["test_file"],
                page_objects=set(mapping_data["page_objects"]),
                mapping_source=MappingSource(mapping_data["mapping_source"]),
                confidence=mapping_data["confidence"],
                detected_at=datetime.fromisoformat(mapping_data["detected_at"])
            )
            
            # Restore references
            for ref_data in mapping_data.get("references", []):
                mapping.references.append(PageObjectReference(
                    page_object_class=ref_data["page_object"],
                    usage_type=ref_data["usage_type"],
                    line_number=ref_data.get("line_number"),
                    source_file=ref_data.get("source_file")
                ))
            
            impact_map.add_mapping(mapping)
        
        return impact_map


@dataclass
class PageObjectMetadata:
    """
    Metadata about a Page Object class.
    
    Attributes:
        class_name: Fully qualified class name
        file_path: Source file path
        package: Package name
        base_class: Base class name (if extends BasePage, etc.)
        methods: Public methods exposed by this PO
        language: Programming language (java, python, etc.)
    """
    class_name: str
    file_path: str
    package: str = ""
    base_class: Optional[str] = None
    methods: List[str] = field(default_factory=list)
    language: str = "java"
    
    def is_page_object(self) -> bool:
        """Check if this class is likely a Page Object."""
        simple_name = self.class_name.split(".")[-1]
        
        # Heuristic checks
        if simple_name.endswith("Page"):
            return True
        if self.base_class and "Page" in self.base_class:
            return True
        if "pages" in self.package.lower():
            return True
        
        return False
    
    def get_simple_name(self) -> str:
        """Get simple class name."""
        return self.class_name.split(".")[-1]
