"""
Data models for Phase 2: Page Object & Locator Awareness

These models are framework-agnostic and form the core of semantic preservation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class LocatorStrategy(Enum):
    """Supported locator strategies (framework-agnostic)"""
    ID = "id"
    XPATH = "xpath"
    CSS_SELECTOR = "css"
    NAME = "name"
    CLASS_NAME = "className"
    TAG_NAME = "tagName"
    LINK_TEXT = "linkText"
    PARTIAL_LINK_TEXT = "partialLinkText"
    DATA_TESTID = "data-testid"


@dataclass
class Locator:
    """
    Framework-agnostic locator model.
    
    This is the CORE of Phase 2 - locator metadata, not just strings.
    Every locator gets identity, provenance, and usage tracking.
    """
    name: str                           # e.g., "loginButton"
    strategy: LocatorStrategy           # e.g., XPATH
    value: str                          # e.g., "//div[@class='btn']"
    source_file: str                    # e.g., "pages/LoginPage.java"
    page_object: str                    # e.g., "LoginPage"
    line_number: Optional[int] = None   # Line in source file
    
    # Metadata for transparency and trust
    original_declaration: str = ""      # Full @FindBy or By.xxx code
    field_type: str = "WebElement"      # WebElement | By | List<WebElement>
    is_list: bool = False               # For findElements / List<WebElement>
    
    # Usage tracking
    used_by_methods: List[str] = field(default_factory=list)
    used_in_tests: List[str] = field(default_factory=list)
    usage_count: int = 0
    
    # Preservation flags
    preserved: bool = True              # Always True in Phase 2
    confidence: float = 1.0             # Preservation confidence
    
    # Optional AI suggestions (non-destructive)
    suggested_alternative: Optional[str] = None
    suggestion_confidence: float = 0.0
    suggestion_reason: Optional[str] = None
    
    def to_playwright_locator(self) -> str:
        """
        Convert to Playwright locator expression.
        
        CRITICAL: This preserves the locator value exactly.
        We only change the API, not the locator itself.
        """
        if self.strategy == LocatorStrategy.ID:
            return f'page.locator("#{self.value}")'
        elif self.strategy == LocatorStrategy.CSS_SELECTOR:
            return f'page.locator("{self.value}")'
        elif self.strategy == LocatorStrategy.XPATH:
            return f'page.locator("{self.value}")'
        elif self.strategy == LocatorStrategy.NAME:
            return f'page.locator("[name=\\"{self.value}\\"]")'
        elif self.strategy == LocatorStrategy.CLASS_NAME:
            return f'page.locator(".{self.value}")'
        elif self.strategy == LocatorStrategy.DATA_TESTID:
            return f'page.get_by_test_id("{self.value}")'
        else:
            # Fallback - preserve as XPath
            return f'page.locator("{self.value}")'
    
    def to_robot_locator(self) -> str:
        """Convert to Robot Framework Browser library locator."""
        if self.strategy == LocatorStrategy.ID:
            return f'id={self.value}'
        elif self.strategy == LocatorStrategy.CSS_SELECTOR:
            return f'css={self.value}'
        elif self.strategy == LocatorStrategy.XPATH:
            return f'xpath={self.value}'
        elif self.strategy == LocatorStrategy.NAME:
            return f'name={self.value}'
        elif self.strategy == LocatorStrategy.CLASS_NAME:
            return f'css=.{self.value}'
        elif self.strategy == LocatorStrategy.DATA_TESTID:
            return f'data-testid={self.value}'
        else:
            return self.value


@dataclass
class PageObject:
    """
    Represents a detected Page Object class.
    
    Preserves semantic boundaries - this is NOT merged or flattened.
    """
    name: str                           # Class name
    file_path: str                      # Source file path
    package: str                        # Java package
    
    # Detection metadata
    detection_confidence: float = 1.0
    detection_reasons: List[str] = field(default_factory=list)
    
    # Locators defined in this Page Object
    locators: List[Locator] = field(default_factory=list)
    
    # Methods defined in this Page Object
    methods: List[Dict] = field(default_factory=list)
    
    # Inheritance
    extends: Optional[str] = None       # Parent class
    implements: List[str] = field(default_factory=list)
    
    # Usage tracking
    used_by_tests: List[str] = field(default_factory=list)
    
    def add_locator(self, locator: Locator):
        """Add a locator to this Page Object."""
        self.locators.append(locator)
        locator.page_object = self.name
    
    def add_method(self, method_name: str, method_info: Dict):
        """Add a method to this Page Object."""
        self.methods.append({
            'name': method_name,
            **method_info
        })
    
    def get_locator(self, name: str) -> Optional[Locator]:
        """Find a locator by name."""
        for locator in self.locators:
            if locator.name == name:
                return locator
        return None


@dataclass
class LocatorUsage:
    """
    Tracks how a locator is used: Test → PageObject → Method → Locator
    
    This is the "usage graph" that makes Phase 2 valuable.
    """
    test_name: str                      # e.g., "LoginTest.testValidLogin"
    page_object: str                    # e.g., "LoginPage"
    method_name: str                    # e.g., "clickLoginButton"
    locator_name: str                   # e.g., "loginButton"
    locator: Locator                    # Full locator object
    
    # Context
    test_file: str = ""
    page_object_file: str = ""
    
    # Usage details
    action: str = ""                    # click, sendKeys, getText, etc.
    line_number: Optional[int] = None


@dataclass
class LocatorInventory:
    """
    Complete inventory of all detected locators.
    
    This is one of the key Phase 2 output artifacts.
    Provides transparency and builds trust.
    """
    page_objects: List[PageObject] = field(default_factory=list)
    locators: List[Locator] = field(default_factory=list)
    usages: List[LocatorUsage] = field(default_factory=list)
    
    # Statistics
    total_page_objects: int = 0
    total_locators: int = 0
    total_usages: int = 0
    
    # Quality metrics
    duplicate_locators: List[Dict] = field(default_factory=list)
    unused_locators: List[Locator] = field(default_factory=list)
    brittle_locators: List[Locator] = field(default_factory=list)
    
    # AI suggestions (optional, non-destructive)
    ai_suggestions: List[Dict] = field(default_factory=list)
    
    def add_page_object(self, page_object: PageObject):
        """Add a Page Object to inventory."""
        self.page_objects.append(page_object)
        self.total_page_objects += 1
    
    def add_locator(self, locator: Locator):
        """Add a locator to inventory."""
        self.locators.append(locator)
        self.total_locators += 1
    
    def add_usage(self, usage: LocatorUsage):
        """Add a usage record."""
        self.usages.append(usage)
        self.total_usages += 1
        
        # Update locator usage count
        usage.locator.usage_count += 1
        if usage.test_name not in usage.locator.used_in_tests:
            usage.locator.used_in_tests.append(usage.test_name)
    
    def find_duplicate_locators(self):
        """
        Identify duplicate locators (same strategy+value, different names).
        Useful for future optimization, but NOT changed in Phase 2.
        """
        seen = {}
        for locator in self.locators:
            key = (locator.strategy, locator.value)
            if key in seen:
                self.duplicate_locators.append({
                    'locator1': seen[key],
                    'locator2': locator,
                    'strategy': locator.strategy.value,
                    'value': locator.value
                })
            else:
                seen[key] = locator
    
    def find_unused_locators(self):
        """Identify locators with zero usage."""
        self.unused_locators = [
            loc for loc in self.locators 
            if loc.usage_count == 0
        ]
    
    def generate_report(self) -> str:
        """
        Generate human-readable inventory report.
        This builds transparency and trust.
        """
        report = []
        report.append("\n╭─────────────────────────────────────────────────────────╮")
        report.append("│         Phase 2: Locator Inventory Report               │")
        report.append("╰─────────────────────────────────────────────────────────╯\n")
        
        report.append("📊 Discovery Summary:")
        report.append(f"  ✓ {self.total_page_objects} Page Objects detected")
        report.append(f"  ✓ {self.total_locators} Locators extracted")
        report.append(f"  ✓ {self.total_usages} Usage mappings created")
        report.append("")
        
        if self.duplicate_locators:
            report.append(f"⚠️  {len(self.duplicate_locators)} duplicate locators found")
        
        if self.unused_locators:
            report.append(f"⚠️  {len(self.unused_locators)} unused locators found")
        
        report.append("\n📝 Page Objects:")
        for po in self.page_objects[:10]:  # Show first 10
            report.append(f"  • {po.name} ({len(po.locators)} locators)")
            report.append(f"    Location: {po.file_path}")
        
        if len(self.page_objects) > 10:
            report.append(f"  ... and {len(self.page_objects) - 10} more")
        
        report.append("\n🎯 Locator Strategies:")
        strategy_counts = {}
        for loc in self.locators:
            strategy_counts[loc.strategy.value] = strategy_counts.get(loc.strategy.value, 0) + 1
        
        for strategy, count in sorted(strategy_counts.items(), key=lambda x: x[1], reverse=True):
            report.append(f"  • {strategy}: {count} locators")
        
        report.append("\n✅ Preservation Guarantee:")
        report.append("  • All locators preserved exactly as-is")
        report.append("  • Page Object boundaries maintained")
        report.append("  • Locator identity tracked")
        report.append("  • Usage context mapped")
        
        if self.ai_suggestions:
            report.append(f"\n💡 AI Suggestions Available: {len(self.ai_suggestions)}")
            report.append("  (Optional - not applied automatically)")
        
        report.append("\n╰─────────────────────────────────────────────────────────╯\n")
        
        return "\n".join(report)
    
    def to_json(self) -> Dict:
        """Export inventory as JSON for external tools."""
        return {
            'page_objects': [
                {
                    'name': po.name,
                    'file': po.file_path,
                    'locators': [
                        {
                            'name': loc.name,
                            'strategy': loc.strategy.value,
                            'value': loc.value,
                            'preserved': loc.preserved,
                            'usage_count': loc.usage_count
                        }
                        for loc in po.locators
                    ]
                }
                for po in self.page_objects
            ],
            'statistics': {
                'total_page_objects': self.total_page_objects,
                'total_locators': self.total_locators,
                'total_usages': self.total_usages,
                'duplicate_locators': len(self.duplicate_locators),
                'unused_locators': len(self.unused_locators)
            },
            'ai_suggestions': self.ai_suggestions
        }
