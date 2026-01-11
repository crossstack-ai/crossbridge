"""
Heuristic Locator Quality Analyzer

Deterministic, rule-based risk scoring for locators.
NO AI - fast, predictable, explainable.

This always runs first, before any AI analysis.
"""

import re
from typing import List, Tuple
from core.locator_awareness.models import Locator, LocatorStrategy
from .models import RiskScore, RiskLevel


class LocatorQualityRule:
    """Base class for locator quality rules"""
    
    def __init__(self, name: str, risk_weight: float, description: str):
        self.name = name
        self.risk_weight = risk_weight  # 0.0 to 1.0
        self.description = description
    
    def applies_to(self, locator: Locator) -> bool:
        """Check if rule applies to this locator"""
        raise NotImplementedError
    
    def calculate_risk(self, locator: Locator) -> float:
        """Calculate risk score if rule applies"""
        raise NotImplementedError


class IndexBasedXPathRule(LocatorQualityRule):
    """Detects XPath with positional indices - VERY BRITTLE"""
    
    def __init__(self):
        super().__init__(
            name="index_based_xpath",
            risk_weight=0.9,
            description="XPath uses positional index (e.g., //div[1], //button[3])"
        )
        self.pattern = re.compile(r'\[\d+\]')
    
    def applies_to(self, locator: Locator) -> bool:
        return (locator.strategy == LocatorStrategy.XPATH and 
                self.pattern.search(locator.value) is not None)
    
    def calculate_risk(self, locator: Locator) -> float:
        # Count number of indices
        indices = self.pattern.findall(locator.value)
        # More indices = higher risk
        return min(0.9 + (len(indices) * 0.05), 1.0)


class ClassOnlyXPathRule(LocatorQualityRule):
    """Detects XPath using only class names - BRITTLE"""
    
    def __init__(self):
        super().__init__(
            name="class_only_xpath",
            risk_weight=0.65,
            description="XPath relies solely on class attributes"
        )
        self.pattern = re.compile(r"//[^@]*\[@class=")
    
    def applies_to(self, locator: Locator) -> bool:
        if locator.strategy != LocatorStrategy.XPATH:
            return False
        # Check if only has @class and no other attributes
        has_class = "@class=" in locator.value
        has_other_attrs = any(attr in locator.value for attr in ["@id=", "@name=", "@data-", "@role="])
        return has_class and not has_other_attrs
    
    def calculate_risk(self, locator: Locator) -> float:
        return self.risk_weight


class WildcardXPathRule(LocatorQualityRule):
    """Detects XPath with wildcards - AMBIGUOUS"""
    
    def __init__(self):
        super().__init__(
            name="wildcard_xpath",
            risk_weight=0.7,
            description="XPath uses wildcards (//*)"
        )
    
    def applies_to(self, locator: Locator) -> bool:
        return locator.strategy == LocatorStrategy.XPATH and "//*" in locator.value
    
    def calculate_risk(self, locator: Locator) -> float:
        return self.risk_weight


class LongXPathRule(LocatorQualityRule):
    """Detects overly complex XPath - MAINTENANCE BURDEN"""
    
    def __init__(self):
        super().__init__(
            name="long_xpath",
            risk_weight=0.6,
            description="XPath has deep nesting (4+ levels)"
        )
    
    def applies_to(self, locator: Locator) -> bool:
        if locator.strategy != LocatorStrategy.XPATH:
            return False
        # Count // and / separators
        depth = locator.value.count("//") + locator.value.count("/")
        return depth >= 4
    
    def calculate_risk(self, locator: Locator) -> float:
        depth = locator.value.count("//") + locator.value.count("/")
        # Scale risk with depth
        return min(0.5 + (depth * 0.05), 0.85)


class IDLocatorRule(LocatorQualityRule):
    """ID locators are generally safe"""
    
    def __init__(self):
        super().__init__(
            name="id_locator",
            risk_weight=0.15,
            description="Uses stable ID attribute"
        )
    
    def applies_to(self, locator: Locator) -> bool:
        return locator.strategy == LocatorStrategy.ID
    
    def calculate_risk(self, locator: Locator) -> float:
        # Check if ID looks generated (uuid, random chars)
        if re.match(r'^[a-f0-9-]{20,}$', locator.value):
            return 0.5  # Generated ID, less stable
        return self.risk_weight


class DataTestIDRule(LocatorQualityRule):
    """Data-testid attributes are best practice"""
    
    def __init__(self):
        super().__init__(
            name="data_testid",
            risk_weight=0.1,
            description="Uses data-testid attribute (best practice)"
        )
    
    def applies_to(self, locator: Locator) -> bool:
        return (locator.strategy == LocatorStrategy.DATA_TESTID or
                "data-testid" in locator.value or
                "data-test-id" in locator.value)
    
    def calculate_risk(self, locator: Locator) -> float:
        return self.risk_weight


class CSSClassOnlyRule(LocatorQualityRule):
    """CSS with only class selectors - FRAGILE"""
    
    def __init__(self):
        super().__init__(
            name="css_class_only",
            risk_weight=0.55,
            description="CSS selector uses only classes"
        )
    
    def applies_to(self, locator: Locator) -> bool:
        if locator.strategy != LocatorStrategy.CSS_SELECTOR:
            return False
        # Check if only has . (classes) and no # (IDs) or [ (attributes)
        has_classes = "." in locator.value
        has_id = "#" in locator.value
        has_attrs = "[" in locator.value
        return has_classes and not has_id and not has_attrs
    
    def calculate_risk(self, locator: Locator) -> float:
        return self.risk_weight


class TextBasedLocatorRule(LocatorQualityRule):
    """Text-based locators - FRAGILE (i18n issues)"""
    
    def __init__(self):
        super().__init__(
            name="text_based",
            risk_weight=0.65,
            description="Uses text content (breaks with i18n/content changes)"
        )
    
    def applies_to(self, locator: Locator) -> bool:
        return (locator.strategy in [LocatorStrategy.LINK_TEXT, LocatorStrategy.PARTIAL_LINK_TEXT] or
                "text()" in locator.value or
                "contains(text()" in locator.value)
    
    def calculate_risk(self, locator: Locator) -> float:
        return self.risk_weight


class HeuristicAnalyzer:
    """
    Deterministic locator quality analyzer
    
    Uses rule-based heuristics to score locator brittleness.
    NO AI - fast, predictable, explainable.
    """
    
    def __init__(self):
        self.rules: List[LocatorQualityRule] = [
            IndexBasedXPathRule(),
            WildcardXPathRule(),
            ClassOnlyXPathRule(),
            LongXPathRule(),
            IDLocatorRule(),
            DataTestIDRule(),
            CSSClassOnlyRule(),
            TextBasedLocatorRule(),
        ]
    
    def analyze(self, locator: Locator) -> RiskScore:
        """
        Analyze locator and return risk score
        
        Returns:
            RiskScore with heuristic-based assessment
        """
        applicable_rules = []
        risk_factors = []
        risk_values = []
        
        for rule in self.rules:
            if rule.applies_to(locator):
                applicable_rules.append(rule)
                risk = rule.calculate_risk(locator)
                risk_values.append(risk)
                risk_factors.append(rule.description)
        
        # Calculate final heuristic score
        if not risk_values:
            # No rules matched - assume medium risk
            heuristic_score = 0.5
            risk_factors.append("No specific quality rules matched")
        else:
            # Use maximum risk (most conservative)
            heuristic_score = max(risk_values)
        
        return RiskScore(
            heuristic_score=heuristic_score,
            risk_level=RiskLevel.MEDIUM,  # Will be recalculated in __post_init__
            risk_factors=risk_factors
        )
    
    def analyze_batch(self, locators: List[Locator]) -> List[Tuple[Locator, RiskScore]]:
        """Analyze multiple locators"""
        return [(locator, self.analyze(locator)) for locator in locators]
    
    def get_high_risk_locators(self, locators: List[Locator], threshold: float = 0.6) -> List[Tuple[Locator, RiskScore]]:
        """Filter locators above risk threshold"""
        results = self.analyze_batch(locators)
        return [(loc, risk) for loc, risk in results if risk.final_score >= threshold]


def create_default_analyzer() -> HeuristicAnalyzer:
    """Create analyzer with default rule set"""
    return HeuristicAnalyzer()
