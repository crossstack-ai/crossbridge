"""
Advanced Page Object pattern detection with inheritance hierarchies.

Handles complex Page Object Model patterns including:
- Multi-level inheritance (BasePage → LoginPage → SecureLoginPage)
- Page Factory patterns with @FindBy
- LoadableComponent pattern
- Page Object composition
"""

import re
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class PageObjectClass:
    """Represents a Page Object class."""
    class_name: str
    parent_class: Optional[str]
    package: str
    elements: List[Dict[str, str]]
    methods: List[str]
    inheritance_level: int
    uses_page_factory: bool
    is_loadable_component: bool
    file_path: Path


class AdvancedPageObjectDetector:
    """Detect complex Page Object patterns in Selenium Java projects."""
    
    def __init__(self):
        # Page Object indicators
        self.page_indicators = [
            'Page', 'Screen', 'View', 'Panel', 'Component', 'Dialog', 'Modal'
        ]
        
        # Patterns
        self.class_pattern = re.compile(
            r'(?:public\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?',
            re.MULTILINE
        )
        self.package_pattern = re.compile(r'package\s+([\w.]+);')
        self.findby_pattern = re.compile(
            r'@FindBy\s*\(([^)]+)\)\s*(?:private|protected|public)?\s*WebElement\s+(\w+)',
            re.MULTILINE | re.DOTALL
        )
        self.findall_pattern = re.compile(
            r'@FindAll\s*\(\{([^}]+)\}\)\s*(?:private|protected|public)?\s*List<WebElement>\s+(\w+)',
            re.MULTILINE | re.DOTALL
        )
        self.page_factory_init = re.compile(
            r'PageFactory\.initElements\s*\([^)]+\)',
            re.MULTILINE
        )
        self.loadable_component = re.compile(
            r'extends\s+LoadableComponent<(\w+)>',
            re.MULTILINE
        )
    
    def detect_page_objects(
        self,
        project_root: Path
    ) -> List[PageObjectClass]:
        """
        Detect all Page Object classes in a project.
        
        Args:
            project_root: Root directory of Java project
            
        Returns:
            List of PageObjectClass objects
        """
        page_objects = []
        
        # Find potential Page Object files
        for java_file in project_root.rglob("*.java"):
            if self._is_page_object_file(java_file):
                po = self.extract_page_object(java_file)
                if po:
                    page_objects.append(po)
        
        # Calculate inheritance levels
        page_objects = self._calculate_inheritance_levels(page_objects)
        
        return page_objects
    
    def _is_page_object_file(self, java_file: Path) -> bool:
        """Check if file likely contains a Page Object."""
        file_name = java_file.stem
        
        # Check file name
        for indicator in self.page_indicators:
            if indicator in file_name:
                return True
        
        # Check if in pages/pageobjects directory
        path_parts = java_file.parts
        if any(part.lower() in ['pages', 'pageobjects', 'page-objects', 'screens'] 
               for part in path_parts):
            return True
        
        return False
    
    def extract_page_object(
        self,
        java_file: Path
    ) -> Optional[PageObjectClass]:
        """
        Extract Page Object details from a Java file.
        
        Args:
            java_file: Path to Java file
            
        Returns:
            PageObjectClass object or None
        """
        if not java_file.exists():
            return None
        
        content = java_file.read_text(encoding='utf-8')
        
        # Extract class info
        class_match = self.class_pattern.search(content)
        if not class_match:
            return None
        
        class_name = class_match.group(1)
        parent_class = class_match.group(2)
        
        # Extract package
        package_match = self.package_pattern.search(content)
        package = package_match.group(1) if package_match else 'unknown'
        
        # Extract elements (@FindBy, @FindAll)
        elements = self._extract_elements(content)
        
        # Extract methods
        methods = self._extract_methods(content)
        
        # Check for Page Factory
        uses_page_factory = bool(self.page_factory_init.search(content))
        
        # Check for LoadableComponent
        is_loadable = bool(self.loadable_component.search(content))
        
        return PageObjectClass(
            class_name=class_name,
            parent_class=parent_class,
            package=package,
            elements=elements,
            methods=methods,
            inheritance_level=0,  # Will be calculated later
            uses_page_factory=uses_page_factory,
            is_loadable_component=is_loadable,
            file_path=java_file
        )
    
    def _extract_elements(self, content: str) -> List[Dict[str, str]]:
        """Extract WebElement declarations."""
        elements = []
        
        # @FindBy elements
        for match in self.findby_pattern.finditer(content):
            locator_str = match.group(1)
            element_name = match.group(2)
            
            # Parse locator strategy
            locator = self._parse_locator(locator_str)
            
            elements.append({
                'name': element_name,
                'type': 'WebElement',
                'locator_strategy': locator['strategy'],
                'locator_value': locator['value']
            })
        
        # @FindAll elements
        for match in self.findall_pattern.finditer(content):
            locators_str = match.group(1)
            element_name = match.group(2)
            
            elements.append({
                'name': element_name,
                'type': 'List<WebElement>',
                'locator_strategy': 'multiple',
                'locator_value': locators_str[:50]  # Truncate for display
            })
        
        return elements
    
    def _parse_locator(self, locator_str: str) -> Dict[str, str]:
        """Parse @FindBy locator string."""
        strategies = ['id', 'name', 'className', 'css', 'xpath', 'tagName', 'linkText', 'partialLinkText']
        
        for strategy in strategies:
            pattern = re.compile(rf'{strategy}\s*=\s*"([^"]+)"', re.IGNORECASE)
            match = pattern.search(locator_str)
            if match:
                return {
                    'strategy': strategy,
                    'value': match.group(1)
                }
        
        return {'strategy': 'unknown', 'value': locator_str[:30]}
    
    def _extract_methods(self, content: str) -> List[str]:
        """Extract public methods from Page Object."""
        method_pattern = re.compile(
            r'public\s+(?:\w+(?:<[^>]+>)?)\s+(\w+)\s*\([^)]*\)',
            re.MULTILINE
        )
        
        methods = []
        for match in method_pattern.finditer(content):
            method_name = match.group(1)
            # Exclude getters, setters, standard methods
            if not method_name.startswith(('get', 'set', 'equals', 'hashCode', 'toString')):
                methods.append(method_name)
        
        return methods
    
    def _calculate_inheritance_levels(
        self,
        page_objects: List[PageObjectClass]
    ) -> List[PageObjectClass]:
        """Calculate inheritance depth for each Page Object."""
        # Build class name to object mapping
        class_map = {po.class_name: po for po in page_objects}
        
        def get_level(po: PageObjectClass, visited: Set[str] = None) -> int:
            if visited is None:
                visited = set()
            
            if po.class_name in visited:
                return 0  # Circular reference
            
            visited.add(po.class_name)
            
            if not po.parent_class or po.parent_class not in class_map:
                return 0
            
            parent = class_map[po.parent_class]
            return 1 + get_level(parent, visited)
        
        for po in page_objects:
            po.inheritance_level = get_level(po)
        
        return page_objects
    
    def build_inheritance_tree(
        self,
        page_objects: List[PageObjectClass]
    ) -> Dict[str, List[str]]:
        """
        Build inheritance tree showing parent-child relationships.
        
        Args:
            page_objects: List of PageObjectClass objects
            
        Returns:
            Dictionary mapping parent class to list of child classes
        """
        tree = {}
        
        for po in page_objects:
            if po.parent_class:
                if po.parent_class not in tree:
                    tree[po.parent_class] = []
                tree[po.parent_class].append(po.class_name)
        
        return tree
    
    def get_base_page_objects(
        self,
        page_objects: List[PageObjectClass]
    ) -> List[PageObjectClass]:
        """Get base Page Objects (no parent or non-PO parent)."""
        class_names = {po.class_name for po in page_objects}
        
        base_objects = []
        for po in page_objects:
            if not po.parent_class or po.parent_class not in class_names:
                base_objects.append(po)
        
        return base_objects
    
    def get_inheritance_chain(
        self,
        page_object: PageObjectClass,
        all_page_objects: List[PageObjectClass]
    ) -> List[str]:
        """Get full inheritance chain for a Page Object."""
        class_map = {po.class_name: po for po in all_page_objects}
        
        chain = [page_object.class_name]
        current = page_object
        
        while current.parent_class and current.parent_class in class_map:
            chain.append(current.parent_class)
            current = class_map[current.parent_class]
        
        return chain
    
    def convert_to_robot_resource(
        self,
        page_object: PageObjectClass
    ) -> str:
        """
        Convert Page Object to Robot Framework resource file.
        
        Args:
            page_object: PageObjectClass object
            
        Returns:
            Robot Framework resource file content
        """
        resource = f"*** Settings ***\n"
        resource += f"Documentation    {page_object.class_name} Page Object\n"
        resource += f"Library    SeleniumLibrary\n\n"
        
        # Variables section for locators
        resource += f"*** Variables ***\n"
        for element in page_object.elements:
            var_name = element['name'].upper()
            strategy = element['locator_strategy']
            value = element['locator_value']
            
            if strategy == 'id':
                resource += f"${{{{LOC_{var_name}}}}}    id={value}\n"
            elif strategy == 'xpath':
                resource += f"${{{{LOC_{var_name}}}}}    xpath={value}\n"
            elif strategy == 'css':
                resource += f"${{{{LOC_{var_name}}}}}    css={value}\n"
            else:
                resource += f"${{{{LOC_{var_name}}}}}    {strategy}={value}\n"
        
        resource += f"\n*** Keywords ***\n"
        
        # Create keywords for methods
        for method in page_object.methods[:10]:  # Limit to first 10
            keyword_name = method.replace('_', ' ').title()
            resource += f"{keyword_name}\n"
            resource += f"    [Documentation]    {method} action\n"
            resource += f"    # Implementation needed\n\n"
        
        return resource
