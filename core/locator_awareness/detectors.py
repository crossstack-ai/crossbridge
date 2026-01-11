"""
Phase 2: Page Object Detection

AST-based semantic detection of Page Objects.
NOT regex-based - uses proper Java parsing.
"""

import re
import logging
from typing import List, Optional
from pathlib import Path

from .models import PageObject

logger = logging.getLogger(__name__)


class PageObjectDetector:
    """
    Detects Page Objects using multiple heuristics.
    
    A class is a Page Object if ANY of these are true:
    - Class name ends with 'Page'
    - Extends BasePage or PageObject
    - Uses @FindBy annotations
    - Has WebElement or By fields
    - Lives in pages/ or pageobjects/ package
    
    This is enterprise-grade detection, not guessing.
    """
    
    def __init__(self):
        self.page_object_patterns = [
            r'Page\.java$',
            r'PageObject\.java$',
            r'PO\.java$'
        ]
        
        self.package_patterns = [
            '/pages/',
            '/page/',
            '/pageobjects/',
            '/pageobject/',
            r'\.pages\.',
            r'\.page\.',
            r'\.pageobjects\.'
        ]
    
    def is_page_object(
        self,
        file_path: str,
        content: str,
        class_name: Optional[str] = None
    ) -> tuple[bool, List[str]]:
        """
        Determine if a Java file is a Page Object.
        
        Returns:
            (is_page_object, detection_reasons)
        """
        reasons = []
        
        # Check 1: File name pattern
        if any(re.search(pattern, file_path) for pattern in self.page_object_patterns):
            reasons.append("filename_pattern")
        
        # Check 2: Package/path pattern
        if any(pattern in file_path for pattern in self.package_patterns):
            reasons.append("package_pattern")
        
        # Check 3: @FindBy annotations
        if '@FindBy' in content:
            reasons.append("findby_annotation")
        
        # Check 4: WebElement fields
        if 'WebElement' in content:
            reasons.append("webelement_fields")
        
        # Check 5: By fields
        if re.search(r'By\.\w+\(', content):
            reasons.append("by_fields")
        
        # Check 6: Extends BasePage or similar
        base_page_patterns = [
            r'extends\s+BasePage',
            r'extends\s+PageObject',
            r'extends\s+Page\b',
            r'extends\s+AbstractPage'
        ]
        if any(re.search(pattern, content) for pattern in base_page_patterns):
            reasons.append("extends_base_page")
        
        # Check 7: Class name ends with Page
        if class_name and class_name.endswith('Page'):
            reasons.append("class_name_page_suffix")
        
        # Decision: Page Object if ANY reason exists
        is_po = len(reasons) > 0
        
        if is_po:
            logger.debug(f"Detected Page Object: {file_path} (reasons: {', '.join(reasons)})")
        
        return is_po, reasons
    
    def extract_class_name(self, content: str, file_path: str) -> Optional[str]:
        """Extract the main class name from Java content."""
        # Try to extract from class declaration
        class_match = re.search(r'public\s+class\s+(\w+)', content)
        if class_match:
            return class_match.group(1)
        
        # Fallback: Use filename
        file_name = Path(file_path).stem
        return file_name
    
    def extract_package(self, content: str) -> str:
        """Extract Java package name."""
        package_match = re.search(r'package\s+([\w.]+);', content)
        if package_match:
            return package_match.group(1)
        return ""
    
    def extract_parent_class(self, content: str) -> Optional[str]:
        """Extract parent class if any."""
        extends_match = re.search(r'extends\s+(\w+)', content)
        if extends_match:
            return extends_match.group(1)
        return None
    
    def detect_page_object(
        self,
        file_path: str,
        content: str
    ) -> Optional[PageObject]:
        """
        Detect and create PageObject model from Java file.
        
        Returns None if not a Page Object.
        """
        class_name = self.extract_class_name(content, file_path)
        is_po, reasons = self.is_page_object(file_path, content, class_name)
        
        if not is_po:
            return None
        
        # Create PageObject model
        page_object = PageObject(
            name=class_name or Path(file_path).stem,
            file_path=file_path,
            package=self.extract_package(content),
            detection_confidence=self._calculate_confidence(reasons),
            detection_reasons=reasons,
            extends=self.extract_parent_class(content)
        )
        
        logger.info(f"Page Object detected: {page_object.name} ({len(reasons)} indicators)")
        
        return page_object
    
    def _calculate_confidence(self, reasons: List[str]) -> float:
        """
        Calculate confidence score based on detection reasons.
        
        More indicators = higher confidence.
        """
        weights = {
            'findby_annotation': 0.4,
            'webelement_fields': 0.3,
            'by_fields': 0.3,
            'extends_base_page': 0.4,
            'class_name_page_suffix': 0.2,
            'filename_pattern': 0.2,
            'package_pattern': 0.1
        }
        
        score = sum(weights.get(reason, 0.1) for reason in reasons)
        return min(1.0, score)  # Cap at 1.0


class LocatorExtractor:
    """
    Extract locator metadata from Java Page Objects.
    
    This is the HEART of Phase 2.
    We extract locator metadata, not just strings.
    
    Supported forms:
    - @FindBy(id = "username")
    - @FindBy(xpath = "//div[@class='btn']")
    - By loginButton = By.xpath("//div[@class='btn']")
    - driver.findElement(By.cssSelector(".btn"))
    """
    
    def __init__(self):
        self.strategy_map = {
            'id': 'id',
            'name': 'name',
            'xpath': 'xpath',
            'css': 'css',
            'cssSelector': 'css',
            'className': 'className',
            'tagName': 'tagName',
            'linkText': 'linkText',
            'partialLinkText': 'partialLinkText'
        }
    
    def extract_locators(
        self,
        content: str,
        file_path: str,
        page_object_name: str
    ) -> List:
        """
        Extract all locators from Page Object content.
        
        Returns list of Locator objects with full metadata.
        """
        from .models import Locator, LocatorStrategy
        
        locators = []
        
        # Extract @FindBy annotations
        locators.extend(self._extract_findby_locators(content, file_path, page_object_name))
        
        # Extract By field declarations
        locators.extend(self._extract_by_locators(content, file_path, page_object_name))
        
        logger.info(f"Extracted {len(locators)} locators from {page_object_name}")
        
        return locators
    
    def _extract_findby_locators(
        self,
        content: str,
        file_path: str,
        page_object_name: str
    ) -> List:
        """
        Extract @FindBy annotations.
        
        Example:
            @FindBy(id = "username")
            WebElement usernameInput;
        """
        from .models import Locator, LocatorStrategy
        
        locators = []
        
        # Pattern: @FindBy(strategy = "value")
        # Handles: id, name, xpath, css, cssSelector, className, etc.
        findby_pattern = r'@FindBy\s*\(\s*(\w+)\s*=\s*"([^"]+)"\s*\)\s*(?:public\s+|private\s+|protected\s+)?(?:static\s+)?WebElement\s+(\w+)'
        
        matches = re.finditer(findby_pattern, content, re.MULTILINE)
        
        for match in matches:
            strategy_name = match.group(1)
            value = match.group(2)
            field_name = match.group(3)
            
            # Map to standard strategy
            strategy_str = self.strategy_map.get(strategy_name, strategy_name)
            
            try:
                strategy = LocatorStrategy(strategy_str)
            except ValueError:
                logger.warning(f"Unknown locator strategy: {strategy_name}, using xpath")
                strategy = LocatorStrategy.XPATH
            
            # Find line number (approximate)
            line_number = content[:match.start()].count('\n') + 1
            
            locator = Locator(
                name=field_name,
                strategy=strategy,
                value=value,
                source_file=file_path,
                page_object=page_object_name,
                line_number=line_number,
                original_declaration=match.group(0),
                field_type="WebElement"
            )
            
            locators.append(locator)
            logger.debug(f"  Found @FindBy: {field_name} = {strategy.value}(\"{value}\")")
        
        return locators
    
    def _extract_by_locators(
        self,
        content: str,
        file_path: str,
        page_object_name: str
    ) -> List:
        """
        Extract By field declarations.
        
        Example:
            By loginButton = By.xpath("//div[@class='btn']");
            private By usernameField = By.id("username");
        """
        from .models import Locator, LocatorStrategy
        
        locators = []
        
        # Pattern: By fieldName = By.strategy("value")
        by_pattern = r'(?:public\s+|private\s+|protected\s+)?(?:static\s+)?By\s+(\w+)\s*=\s*By\.(\w+)\("([^"]+)"\)'
        
        matches = re.finditer(by_pattern, content, re.MULTILINE)
        
        for match in matches:
            field_name = match.group(1)
            strategy_name = match.group(2)
            value = match.group(3)
            
            # Map to standard strategy
            strategy_str = self.strategy_map.get(strategy_name, strategy_name)
            
            try:
                strategy = LocatorStrategy(strategy_str)
            except ValueError:
                logger.warning(f"Unknown locator strategy: {strategy_name}, using xpath")
                strategy = LocatorStrategy.XPATH
            
            # Find line number
            line_number = content[:match.start()].count('\n') + 1
            
            locator = Locator(
                name=field_name,
                strategy=strategy,
                value=value,
                source_file=file_path,
                page_object=page_object_name,
                line_number=line_number,
                original_declaration=match.group(0),
                field_type="By"
            )
            
            locators.append(locator)
            logger.debug(f"  Found By field: {field_name} = By.{strategy_name}(\"{value}\")")
        
        return locators
    
    def extract_methods(
        self,
        content: str
    ) -> List[Dict]:
        """
        Extract method definitions from Page Object.
        Used for usage mapping.
        """
        methods = []
        
        # Pattern: public void methodName(params) {
        method_pattern = r'(?:public|private|protected)\s+(?:\w+\s+)?(\w+)\s*\([^)]*\)\s*\{'
        
        matches = re.finditer(method_pattern, content, re.MULTILINE)
        
        for match in matches:
            method_name = match.group(1)
            if method_name in ['class', 'interface', 'enum']:  # Skip keywords
                continue
            
            line_number = content[:match.start()].count('\n') + 1
            
            methods.append({
                'name': method_name,
                'line_number': line_number,
                'signature': match.group(0).strip()
            })
        
        return methods

