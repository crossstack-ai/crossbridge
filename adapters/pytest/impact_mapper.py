"""
Python Page Object detector and mapper for pytest.

Detects Page Object classes and maps them to pytest tests.
"""

from pathlib import Path
from typing import List, Set, Optional
import ast
import re

from ..common.impact_models import (
    PageObjectMetadata,
    TestToPageObjectMapping,
    PageObjectImpactMap,
    MappingSource
)


class PytestPageObjectDetector:
    """
    Detects Page Object classes in Python/pytest projects.
    
    Uses heuristics:
    - Class name ends with "Page"
    - Inherits from BasePage
    - Located in "pages" module
    """
    
    def __init__(self, source_root: str = "pages"):
        self.source_root = Path(source_root)
    
    def detect_page_objects(self) -> List[PageObjectMetadata]:
        """Scan project for Page Object classes."""
        page_objects = []
        
        if not self.source_root.exists():
            # Try alternative locations
            for alt_path in ["src/pages", "tests/pages"]:
                if Path(alt_path).exists():
                    self.source_root = Path(alt_path)
                    break
        
        if not self.source_root.exists():
            # Try alternative locations
            for alt_path in ["src/pages", "tests/pages"]:
                if Path(alt_path).exists():
                    self.source_root = Path(alt_path)
                    break
        
        if not self.source_root.exists():
            return page_objects
        
        for py_file in self.source_root.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            
            pos = self._analyze_file(py_file)
            page_objects.extend(pos)
        
        return page_objects
    
    def _analyze_file(self, py_file: Path) -> List[PageObjectMetadata]:
        """Analyze a Python file for Page Object patterns."""
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(py_file))
            
            page_objects = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if self._is_page_object_class(node):
                        # Extract module path
                        module = self._get_module_path(py_file)
                        qualified_name = f"{module}.{node.name}" if module else node.name
                        
                        # Extract base class
                        base_class = None
                        if node.bases:
                            if isinstance(node.bases[0], ast.Name):
                                base_class = node.bases[0].id
                            elif isinstance(node.bases[0], ast.Attribute):
                                base_class = node.bases[0].attr
                        
                        # Extract methods
                        methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                        
                        page_objects.append(PageObjectMetadata(
                            class_name=qualified_name,
                            file_path=str(py_file),
                            package=module or "",
                            base_class=base_class,
                            methods=methods,
                            language="python"
                        ))
            
            return page_objects
            
        except Exception:
            return []
    
    def _is_page_object_class(self, node: ast.ClassDef) -> bool:
        """Check if a class is likely a Page Object."""
        # Heuristic checks - only match if ends with "Page"
        if node.name.endswith("Page"):
            return True
        
        # Check if extends BasePage or similar
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id.endswith("Page"):
                return True
        
        return False
    
    def _get_module_path(self, py_file: Path) -> str:
        """Get Python module path from file path."""
        # Remove .py extension and convert to module notation
        parts = py_file.parts
        
        # Find the start of the module path
        start_idx = 0
        for i, part in enumerate(parts):
            if part in ["pages", "src", "tests"]:
                start_idx = i
                break
        
        module_parts = list(parts[start_idx:])
        module_parts[-1] = module_parts[-1].replace(".py", "")
        
        return ".".join(module_parts)


class PytestTestToPageObjectMapper:
    """
    Maps pytest tests to Page Objects they use.
    
    Detects:
    - Imports of Page Object classes
    - Fixture usage (*_page fixtures)
    - Instantiations in test functions
    """
    
    def __init__(self, test_root: str = "tests", 
                 known_page_objects: Optional[Set[str]] = None):
        self.test_root = Path(test_root)
        self.known_page_objects = known_page_objects or set()
    
    def map_tests_to_page_objects(self) -> PageObjectImpactMap:
        """Scan all tests and create impact map."""
        impact_map = PageObjectImpactMap(project_root=str(self.test_root.parent))
        
        if not self.test_root.exists():
            return impact_map
        
        for py_file in self.test_root.rglob("test_*.py"):
            mappings = self._analyze_test_file(py_file)
            for mapping in mappings:
                impact_map.add_mapping(mapping)
        
        return impact_map
    
    def _analyze_test_file(self, test_file: Path) -> List[TestToPageObjectMapping]:
        """Analyze a test file for Page Object usage."""
        try:
            content = test_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(test_file))
            
            mappings = []
            
            # Find all test functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    module = self._get_module_path(test_file)
                    test_id = f"{module}.{node.name}" if module else node.name
                    
                    mapping = TestToPageObjectMapping(
                        test_id=test_id,
                        test_file=str(test_file),
                        mapping_source=MappingSource.STATIC_AST
                    )
                    
                    # Detect Page Object usage in function
                    self._detect_fixtures(node, mapping)
                    self._detect_instantiations(node, mapping, tree)
                    
                    if mapping.page_objects:
                        mappings.append(mapping)
            
            return mappings
            
        except Exception:
            return []
    
    def _detect_fixtures(self, func_node: ast.FunctionDef, mapping: TestToPageObjectMapping):
        """Detect Page Object fixtures in test parameters."""
        for arg in func_node.args.args:
            arg_name = arg.arg
            
            # Check if fixture name ends with _page
            if arg_name.endswith("_page"):
                # Convert fixture name to class name (login_page -> LoginPage)
                class_name = self._fixture_to_class_name(arg_name)
                
                mapping.add_page_object(
                    class_name,
                    usage_type="fixture",
                    line_number=func_node.lineno
                )
    
    def _detect_instantiations(self, func_node: ast.FunctionDef, 
                              mapping: TestToPageObjectMapping,
                              module_tree: ast.Module):
        """Detect Page Object instantiations in test body."""
        for node in ast.walk(func_node):
            # Look for Class() calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    class_name = node.func.id
                    if self._is_page_object_class_name(class_name):
                        mapping.add_page_object(
                            class_name,
                            usage_type="instantiation",
                            line_number=node.lineno
                        )
    
    def _fixture_to_class_name(self, fixture_name: str) -> str:
        """Convert fixture name to class name (login_page -> LoginPage)."""
        parts = fixture_name.replace("_page", "").split("_")
        return "".join(p.capitalize() for p in parts) + "Page"
    
    def _is_page_object_class_name(self, class_name: str) -> bool:
        """Check if a class name is likely a Page Object."""
        if self.known_page_objects:
            if class_name in self.known_page_objects:
                return True
        
        return class_name.endswith("Page")
    
    def _get_module_path(self, py_file: Path) -> str:
        """Get Python module path from file path."""
        parts = py_file.parts
        
        start_idx = 0
        for i, part in enumerate(parts):
            if part in ["tests", "test"]:
                start_idx = i
                break
        
        module_parts = list(parts[start_idx:])
        module_parts[-1] = module_parts[-1].replace(".py", "")
        
        return ".".join(module_parts)


def create_pytest_impact_map(project_root: str,
                             source_root: str = "pages",
                             test_root: str = "tests") -> PageObjectImpactMap:
    """
    Create complete Page Object → Test impact map for a pytest project.
    
    Args:
        project_root: Root directory of the project.
        source_root: Source code directory (for Page Objects).
        test_root: Test code directory.
        
    Returns:
        Complete impact map.
    """
    # Step 1: Detect Page Objects
    detector = PytestPageObjectDetector(f"{project_root}/{source_root}")
    page_objects = detector.detect_page_objects()
    
    # Extract Page Object class names
    po_classes = {po.class_name for po in page_objects}
    po_simple_names = {po.get_simple_name() for po in page_objects}
    all_po_names = po_classes | po_simple_names
    
    # Step 2: Map tests to Page Objects
    mapper = PytestTestToPageObjectMapper(
        f"{project_root}/{test_root}",
        known_page_objects=all_po_names
    )
    
    return mapper.map_tests_to_page_objects()
