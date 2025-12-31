"""
Idiom and API Mapping Registries.

Provides deterministic mappings between framework-specific patterns.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ApiMapping:
    """Mapping from source API to target API."""
    source_pattern: str
    target_pattern: str
    source_framework: str
    target_framework: str
    confidence: float = 1.0
    notes: str = ""


class ApiMappingRegistry:
    """
    Registry for API-level mappings between frameworks.
    
    This provides deterministic translation for common patterns.
    """
    
    def __init__(self):
        """Initialize with default mappings."""
        self._mappings: Dict[Tuple[str, str], List[ApiMapping]] = {}
        self._load_default_mappings()
    
    def _load_default_mappings(self):
        """Load default API mappings."""
        # Selenium → Playwright mappings
        self._add_mapping(ApiMapping(
            source_pattern="driver.findElement(By.id(\"{id}\")).click()",
            target_pattern="page.locator(\"#{id}\").click()",
            source_framework="selenium",
            target_framework="playwright",
            confidence=1.0,
            notes="Simple click by ID"
        ))
        
        self._add_mapping(ApiMapping(
            source_pattern="driver.findElement(By.xpath(\"{xpath}\")).click()",
            target_pattern="page.locator(\"{xpath}\").click()",
            source_framework="selenium",
            target_framework="playwright",
            confidence=0.95,
            notes="XPath locator"
        ))
        
        self._add_mapping(ApiMapping(
            source_pattern="driver.findElement(By.id(\"{id}\")).sendKeys(\"{text}\")",
            target_pattern="page.locator(\"#{id}\").fill(\"{text}\")",
            source_framework="selenium",
            target_framework="playwright",
            confidence=1.0,
            notes="Fill input field"
        ))
        
        self._add_mapping(ApiMapping(
            source_pattern="driver.findElement(By.id(\"{id}\")).getText()",
            target_pattern="page.locator(\"#{id}\").text_content()",
            source_framework="selenium",
            target_framework="playwright",
            confidence=1.0,
            notes="Get text content"
        ))
        
        self._add_mapping(ApiMapping(
            source_pattern="driver.findElement(By.id(\"{id}\")).isDisplayed()",
            target_pattern="page.locator(\"#{id}\").is_visible()",
            source_framework="selenium",
            target_framework="playwright",
            confidence=1.0,
            notes="Check visibility"
        ))
        
        self._add_mapping(ApiMapping(
            source_pattern="driver.get(\"{url}\")",
            target_pattern="page.goto(\"{url}\")",
            source_framework="selenium",
            target_framework="playwright",
            confidence=1.0,
            notes="Navigate to URL"
        ))
        
        self._add_mapping(ApiMapping(
            source_pattern="WebDriverWait(driver, {timeout}).until(EC.presence_of_element_located((By.ID, \"{id}\")))",
            target_pattern="# Playwright has auto-wait\npage.locator(\"#{id}\")",
            source_framework="selenium",
            target_framework="playwright",
            confidence=0.9,
            notes="Explicit wait → auto-wait"
        ))
        
        self._add_mapping(ApiMapping(
            source_pattern="Thread.sleep({ms})",
            target_pattern="# Remove sleep - Playwright auto-waits",
            source_framework="selenium",
            target_framework="playwright",
            confidence=0.8,
            notes="Sleep should be removed"
        ))
        
        # RestAssured → requests mappings
        self._add_mapping(ApiMapping(
            source_pattern="given().auth().basic(user, pass).when().get(\"{url}\").then().statusCode({code})",
            target_pattern="response = requests.get(\"{url}\", auth=(user, pass))\nassert response.status_code == {code}",
            source_framework="restassured",
            target_framework="pytest-requests",
            confidence=1.0,
            notes="GET with basic auth"
        ))
        
        self._add_mapping(ApiMapping(
            source_pattern="given().body({body}).when().post(\"{url}\").then().statusCode({code})",
            target_pattern="response = requests.post(\"{url}\", json={body})\nassert response.status_code == {code}",
            source_framework="restassured",
            target_framework="pytest-requests",
            confidence=1.0,
            notes="POST with JSON body"
        ))
        
        # Robot → Pytest mappings
        self._add_mapping(ApiMapping(
            source_pattern="Click Element    {locator}",
            target_pattern="page.locator(\"{locator}\").click()",
            source_framework="robot",
            target_framework="playwright",
            confidence=0.95,
            notes="Click element in Robot"
        ))
        
        self._add_mapping(ApiMapping(
            source_pattern="Input Text    {locator}    {text}",
            target_pattern="page.locator(\"{locator}\").fill(\"{text}\")",
            source_framework="robot",
            target_framework="playwright",
            confidence=0.95,
            notes="Input text in Robot"
        ))
    
    def _add_mapping(self, mapping: ApiMapping):
        """Add a mapping to the registry."""
        key = (mapping.source_framework, mapping.target_framework)
        if key not in self._mappings:
            self._mappings[key] = []
        self._mappings[key].append(mapping)
    
    def get_mappings(
        self, source_framework: str, target_framework: str
    ) -> List[ApiMapping]:
        """Get all mappings for a framework pair."""
        key = (source_framework.lower(), target_framework.lower())
        return self._mappings.get(key, [])
    
    def find_mapping(
        self,
        source_framework: str,
        target_framework: str,
        pattern: str,
    ) -> Optional[ApiMapping]:
        """Find best matching mapping for a pattern."""
        mappings = self.get_mappings(source_framework, target_framework)
        
        # Exact match first
        for mapping in mappings:
            if mapping.source_pattern == pattern:
                return mapping
        
        # Pattern match (simplified)
        for mapping in mappings:
            # Basic pattern matching - can be enhanced
            if pattern in mapping.source_pattern or mapping.source_pattern in pattern:
                return mapping
        
        return None


@dataclass
class IdiomPattern:
    """Framework-specific idiom pattern."""
    name: str
    source_framework: str
    target_framework: str
    source_pattern: str
    target_pattern: str
    transformation_rule: str
    examples: List[Tuple[str, str]] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []


class IdiomRegistry:
    """
    Registry for framework-specific idioms.
    
    Idioms are higher-level patterns that go beyond API mappings.
    """
    
    def __init__(self):
        """Initialize with default idioms."""
        self._idioms: Dict[str, List[IdiomPattern]] = {}
        self._load_default_idioms()
    
    def _load_default_idioms(self):
        """Load default idiom patterns."""
        # Selenium waits → Playwright auto-wait
        self._add_idiom(IdiomPattern(
            name="explicit_wait_removal",
            source_framework="selenium",
            target_framework="playwright",
            source_pattern="WebDriverWait",
            target_pattern="# Auto-wait",
            transformation_rule="remove_wait",
            examples=[
                (
                    "WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'btn')))",
                    "# Playwright auto-waits\npage.locator('#btn')"
                )
            ]
        ))
        
        self._add_idiom(IdiomPattern(
            name="implicit_wait_removal",
            source_framework="selenium",
            target_framework="playwright",
            source_pattern="implicitly_wait",
            target_pattern="# Auto-wait",
            transformation_rule="remove_wait",
            examples=[
                (
                    "driver.implicitly_wait(10)",
                    "# Playwright has built-in auto-wait"
                )
            ]
        ))
        
        self._add_idiom(IdiomPattern(
            name="sleep_removal",
            source_framework="selenium",
            target_framework="playwright",
            source_pattern="Thread.sleep|time.sleep",
            target_pattern="# Remove",
            transformation_rule="remove_sleep",
            examples=[
                ("Thread.sleep(1000)", "# Removed - use Playwright auto-wait"),
                ("time.sleep(1)", "# Removed - use Playwright auto-wait")
            ]
        ))
        
        # RestAssured given-when-then → Pytest AAA
        self._add_idiom(IdiomPattern(
            name="given_when_then_to_aaa",
            source_framework="restassured",
            target_framework="pytest",
            source_pattern="given().when().then()",
            target_pattern="# Arrange-Act-Assert",
            transformation_rule="restructure_test",
            examples=[
                (
                    "given().auth().basic(u, p).when().get('/api').then().statusCode(200)",
                    "# Arrange\nauth = (u, p)\n# Act\nresponse = requests.get('/api', auth=auth)\n# Assert\nassert response.status_code == 200"
                )
            ]
        ))
        
        # Page Object patterns
        self._add_idiom(IdiomPattern(
            name="page_object_conversion",
            source_framework="selenium",
            target_framework="playwright",
            source_pattern="PageFactory",
            target_pattern="# Modern page object",
            transformation_rule="modernize_page_object",
            examples=[]
        ))
        
        # Locator strategy improvements
        self._add_idiom(IdiomPattern(
            name="prefer_role_based_selectors",
            source_framework="selenium",
            target_framework="playwright",
            source_pattern="By.ID|By.CLASS_NAME",
            target_pattern="get_by_role|get_by_label",
            transformation_rule="improve_locator",
            examples=[
                (
                    "driver.findElement(By.id('login-btn')).click()",
                    "page.get_by_role('button', name='Login').click()"
                )
            ]
        ))
    
    def _add_idiom(self, idiom: IdiomPattern):
        """Add an idiom to the registry."""
        key = f"{idiom.source_framework}->{idiom.target_framework}"
        if key not in self._idioms:
            self._idioms[key] = []
        self._idioms[key].append(idiom)
    
    def get_idioms(
        self, source_framework: str, target_framework: str
    ) -> List[IdiomPattern]:
        """Get all idioms for a framework pair."""
        key = f"{source_framework.lower()}->{target_framework.lower()}"
        return self._idioms.get(key, [])
    
    def find_idiom(
        self, source_framework: str, target_framework: str, pattern_name: str
    ) -> Optional[IdiomPattern]:
        """Find specific idiom by name."""
        idioms = self.get_idioms(source_framework, target_framework)
        for idiom in idioms:
            if idiom.name == pattern_name:
                return idiom
        return None
    
    def apply_idiom(self, idiom: IdiomPattern, source_code: str) -> str:
        """Apply idiom transformation to source code."""
        # This is a simplified version - real implementation would use AST
        if idiom.transformation_rule == "remove_wait":
            return "# Playwright auto-waits - wait removed"
        elif idiom.transformation_rule == "remove_sleep":
            return "# Sleep removed - use Playwright auto-wait"
        else:
            return source_code  # Default: no transformation
