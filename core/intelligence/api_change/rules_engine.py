"""
Rules Engine

Rule-based intelligence without AI - always enabled
Provides deterministic test recommendations and risk analysis
"""

from typing import List, Dict, Any
from .models.api_change import APIChangeEvent, ChangeType, EntityType, RiskLevel
import logging

logger = logging.getLogger(__name__)


class RulesEngine:
    """Rule-based intelligence without AI - always enabled"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        logger.info(f"Rules engine initialized (enabled: {self.enabled})")
    
    def analyze(self, changes: List[APIChangeEvent]) -> List[APIChangeEvent]:
        """
        Analyze changes using rule-based logic
        
        Enhances each change with:
        - Test recommendations
        - Impacted areas
        - Edge cases
        
        Args:
            changes: List of normalized API changes
        
        Returns:
            Same list with intelligence added
        """
        if not self.enabled:
            return changes
        
        logger.info(f"Applying rules to {len(changes)} changes")
        
        for change in changes:
            # Apply rules based on change type and entity
            if change.entity_type == EntityType.ENDPOINT:
                self._analyze_endpoint_change(change)
            elif change.entity_type == EntityType.SCHEMA:
                self._analyze_schema_change(change)
            elif change.entity_type == EntityType.PARAMETER:
                self._analyze_parameter_change(change)
            elif change.entity_type == EntityType.RESPONSE:
                self._analyze_response_change(change)
        
        logger.info("Rules analysis complete")
        return changes
    
    def _analyze_endpoint_change(self, change: APIChangeEvent):
        """Apply rules for endpoint changes"""
        if change.change_type == ChangeType.ADDED:
            change.recommended_tests.extend([
                f"Create positive test for {change.entity_name}",
                f"Verify authentication/authorization for {change.entity_name}",
                f"Test error responses (400, 401, 403, 500) for {change.entity_name}",
                f"Validate request schema for {change.entity_name}",
                f"Validate response schema for {change.entity_name}",
            ])
            change.impacted_areas.append("New endpoint test coverage needed")
            change.edge_cases.extend([
                "Missing required parameters",
                "Invalid parameter types",
                "Unauthorized access attempts",
                "Large payload handling",
                "Concurrent requests",
            ])
        
        elif change.change_type == ChangeType.REMOVED:
            change.recommended_tests.extend([
                f"Verify {change.entity_name} returns 404",
                f"Update test suites to remove deprecated endpoint tests",
                f"Check dependent services for impact",
                f"Verify graceful degradation in client applications",
            ])
            change.impacted_areas.extend([
                "Endpoint removal",
                "Test deprecation needed",
                "Potential breaking change for consumers",
                "Client application updates required",
            ])
            change.edge_cases.extend([
                "Legacy clients still calling removed endpoint",
                "Cached responses from removed endpoint",
            ])
        
        elif change.change_type == ChangeType.MODIFIED:
            change.recommended_tests.extend([
                f"Regression tests for {change.entity_name}",
                f"Verify backward compatibility for {change.entity_name}",
                f"Test with old and new request formats",
            ])
            change.impacted_areas.append("Endpoint modification")
            change.edge_cases.append("Clients using old request/response format")
    
    def _analyze_schema_change(self, change: APIChangeEvent):
        """Apply rules for schema changes"""
        details = change.change_details
        
        if change.change_type == ChangeType.ADDED:
            change.recommended_tests.append(
                f"Add schema validation tests for {change.entity_name}"
            )
            change.impacted_areas.append("New schema definition")
        
        elif change.change_type == ChangeType.REMOVED:
            change.recommended_tests.extend([
                f"Verify removal of {change.entity_name} schema",
                f"Check for references to removed schema",
                f"Update dependent schemas and endpoints",
            ])
            change.impacted_areas.extend([
                "Schema removal",
                "Breaking change for consumers",
            ])
        
        elif "required" in str(details).lower() or change.breaking:
            # New required field or breaking schema change
            change.recommended_tests.extend([
                f"Test request without required field {change.entity_name}",
                f"Test request with null value for {change.entity_name}",
                f"Test request with invalid type for {change.entity_name}",
                f"Test request with valid value for {change.entity_name}",
                f"Test boundary values for {change.entity_name}",
            ])
            change.impacted_areas.extend([
                "Schema validation",
                "Required field addition",
                "Breaking change",
            ])
            change.edge_cases.extend([
                "Missing required field",
                "Null or empty values",
                "Type mismatch",
                "Out-of-range values",
            ])
        
        elif "type" in details and "changed" in str(details).lower():
            # Type change
            change.recommended_tests.extend([
                f"Verify new type handling for {change.entity_name}",
                f"Test backward compatibility with old type",
                f"Test boundary values for new type",
                f"Test type conversion scenarios",
            ])
            change.impacted_areas.extend([
                "Type change",
                "Potential serialization issues",
                "Data migration may be needed",
            ])
            change.edge_cases.extend([
                "Old type values in database",
                "Client libraries expecting old type",
            ])
        
        elif "enum" in str(details).lower():
            # Enum change
            change.recommended_tests.extend([
                f"Test all enum values for {change.entity_name}",
                f"Test invalid enum values are rejected",
                f"Verify default enum handling",
            ])
            change.impacted_areas.append("Enum value change")
            change.edge_cases.append("Clients using removed enum values")
    
    def _analyze_parameter_change(self, change: APIChangeEvent):
        """Apply rules for parameter changes"""
        details = change.change_details
        
        if "required" in details or change.breaking:
            change.recommended_tests.extend([
                f"Test request missing {change.entity_name}",
                f"Verify error message for missing {change.entity_name}",
                f"Test with null/empty {change.entity_name}",
                f"Test with valid {change.entity_name}",
            ])
            change.impacted_areas.append("New required parameter - breaking change")
            change.edge_cases.extend([
                "Missing parameter",
                "Null parameter value",
                "Empty string parameter",
            ])
        
        if "default" in details:
            change.recommended_tests.append(
                f"Test default behavior when {change.entity_name} is not provided"
            )
            change.impacted_areas.append("Default value change")
        
        if "validation" in details or "pattern" in details:
            # Validation rules changed
            change.recommended_tests.extend([
                f"Test boundary values for {change.entity_name}",
                f"Test invalid values for {change.entity_name}",
                f"Test validation error messages",
            ])
            change.impacted_areas.append("Validation rule change")
            change.edge_cases.extend([
                "Minimum boundary values",
                "Maximum boundary values",
                "Invalid format/pattern",
            ])
    
    def _analyze_response_change(self, change: APIChangeEvent):
        """Apply rules for response changes"""
        details = change.change_details
        
        if "status" in details or "code" in details:
            change.recommended_tests.append(
                f"Verify new response status handling for {change.entity_name}"
            )
            change.impacted_areas.append("Response status code change")
        
        if "schema" in str(details).lower():
            change.recommended_tests.extend([
                f"Verify response schema for {change.entity_name}",
                f"Test response deserialization",
                f"Check field presence and types in response",
                f"Test error response scenarios",
            ])
            change.impacted_areas.append("Response schema change")
            change.edge_cases.extend([
                "Missing response fields",
                "Unexpected response fields",
                "Type mismatches in response",
            ])
        
        if "header" in str(details).lower():
            change.recommended_tests.extend([
                f"Verify response headers for {change.entity_name}",
                f"Test header value formats",
            ])
            change.impacted_areas.append("Response header change")
