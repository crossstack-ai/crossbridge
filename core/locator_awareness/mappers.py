"""
Phase 2: Usage Mapper

Maps Test → PageObject → Method → Locator relationships.
This creates the "usage graph" that makes Phase 2 valuable.
"""

import re
import logging
from typing import List, Dict, Optional

from .models import LocatorUsage, PageObject, Locator, LocatorInventory

logger = logging.getLogger(__name__)


class UsageMapper:
    """
    Creates usage graph: Test → PageObject → Method → Locator
    
    This is one of the key value-adds of Phase 2.
    Provides transparency into how locators are actually used.
    """
    
    def __init__(self):
        self.page_objects: Dict[str, PageObject] = {}
        self.inventory = LocatorInventory()
    
    def add_page_object(self, page_object: PageObject):
        """Register a Page Object."""
        self.page_objects[page_object.name] = page_object
        self.inventory.add_page_object(page_object)
        
        # Add all locators to inventory
        for locator in page_object.locators:
            self.inventory.add_locator(locator)
    
    def map_test_usage(
        self,
        test_name: str,
        test_file: str,
        test_content: str
    ):
        """
        Analyze test file to map Page Object and locator usage.
        
        Args:
            test_name: Test class name
            test_file: Test file path
            test_content: Test file content
        """
        logger.info(f"Mapping usage for test: {test_name}")
        
        # Find Page Object instantiations and method calls
        for po_name, page_object in self.page_objects.items():
            # Check if this Page Object is used in the test
            if po_name in test_content or self._camel_to_snake(po_name) in test_content:
                page_object.used_by_tests.append(test_name)
                
                # Find method calls on this Page Object
                self._map_method_calls(
                    test_name=test_name,
                    test_file=test_file,
                    test_content=test_content,
                    page_object=page_object
                )
    
    def _map_method_calls(
        self,
        test_name: str,
        test_file: str,
        test_content: str,
        page_object: PageObject
    ):
        """Map method calls to locator usage."""
        # Look for method calls like: loginPage.clickLoginButton()
        for method_info in page_object.methods:
            method_name = method_info['name']
            
            # Try both camelCase and snake_case
            patterns = [
                rf'{page_object.name}\.{method_name}\s*\(',
                rf'{self._camel_to_snake(page_object.name)}\.{method_name}\s*\(',
                rf'{self._camel_to_snake(page_object.name)}\.{self._camel_to_snake(method_name)}\s*\('
            ]
            
            for pattern in patterns:
                if re.search(pattern, test_content, re.IGNORECASE):
                    logger.debug(f"  Found call: {page_object.name}.{method_name}() in {test_name}")
                    
                    # Try to infer which locator is used by this method
                    # Look for locator field name in method name
                    for locator in page_object.locators:
                        if locator.name.lower() in method_name.lower():
                            # Create usage record
                            usage = LocatorUsage(
                                test_name=test_name,
                                page_object=page_object.name,
                                method_name=method_name,
                                locator_name=locator.name,
                                locator=locator,
                                test_file=test_file,
                                page_object_file=page_object.file_path
                            )
                            
                            self.inventory.add_usage(usage)
                            
                            if method_name not in locator.used_by_methods:
                                locator.used_by_methods.append(method_name)
                            
                            logger.debug(f"    Maps to locator: {locator.name}")
                            break
    
    def _camel_to_snake(self, name: str) -> str:
        """Convert camelCase to snake_case."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
        return s2.lower()
    
    def generate_usage_report(self) -> str:
        """Generate usage report."""
        lines = []
        lines.append("\n╭─────────────────────────────────────────────────────────╮")
        lines.append("│            Locator Usage Report                         │")
        lines.append("╰─────────────────────────────────────────────────────────╯\n")
        
        lines.append(f"📊 Usage Statistics:")
        lines.append(f"  • {len(self.inventory.usages)} usage mappings created")
        lines.append(f"  • {len(self.inventory.locators)} locators tracked")
        lines.append(f"  • {len(self.inventory.page_objects)} Page Objects analyzed")
        lines.append("")
        
        # Show most-used locators
        sorted_locators = sorted(
            self.inventory.locators,
            key=lambda l: l.usage_count,
            reverse=True
        )[:10]
        
        if sorted_locators:
            lines.append("🔥 Most Used Locators:")
            for i, locator in enumerate(sorted_locators, 1):
                lines.append(f"  {i}. {locator.name} ({locator.usage_count} uses)")
                lines.append(f"     Strategy: {locator.strategy.value}")
                lines.append(f"     Value: {locator.value}")
                lines.append(f"     Page Object: {locator.page_object}")
                lines.append("")
        
        # Find unused locators
        self.inventory.find_unused_locators()
        if self.inventory.unused_locators:
            lines.append(f"⚠️  {len(self.inventory.unused_locators)} Unused Locators:")
            for locator in self.inventory.unused_locators[:5]:
                lines.append(f"  • {locator.name} in {locator.page_object}")
            if len(self.inventory.unused_locators) > 5:
                lines.append(f"  ... and {len(self.inventory.unused_locators) - 5} more")
            lines.append("")
        
        # Find duplicates
        self.inventory.find_duplicate_locators()
        if self.inventory.duplicate_locators:
            lines.append(f"⚠️  {len(self.inventory.duplicate_locators)} Duplicate Locators:")
            for dup in self.inventory.duplicate_locators[:5]:
                loc1 = dup['locator1']
                loc2 = dup['locator2']
                lines.append(f"  • {loc1.name} (in {loc1.page_object})")
                lines.append(f"    = {loc2.name} (in {loc2.page_object})")
                lines.append(f"    Both use: {dup['strategy']}(\"{dup['value']}\")")
                lines.append("")
            if len(self.inventory.duplicate_locators) > 5:
                lines.append(f"  ... and {len(self.inventory.duplicate_locators) - 5} more")
        
        lines.append("╰─────────────────────────────────────────────────────────╯\n")
        
        return "\n".join(lines)
    
    def get_inventory(self) -> LocatorInventory:
        """Get complete locator inventory."""
        return self.inventory
