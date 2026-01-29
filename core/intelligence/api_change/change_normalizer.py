"""
Change Normalizer

Converts raw oasdiff output into normalized APIChangeEvent objects
"""

from typing import Dict, List, Any
from .models.api_change import (
    APIChangeEvent, ChangeType, EntityType, RiskLevel, Severity
)
import logging

logger = logging.getLogger(__name__)


class ChangeNormalizer:
    """Convert oasdiff output to normalized APIChangeEvent objects"""
    
    def __init__(self):
        pass
    
    def normalize(
        self,
        diff_result: Dict[str, Any],
        breaking_changes: List[Dict[str, Any]],
        api_name: str = "",
        api_version: str = ""
    ) -> List[APIChangeEvent]:
        """
        Normalize oasdiff output into APIChangeEvent objects
        
        Args:
            diff_result: Raw oasdiff diff output
            breaking_changes: Breaking changes from oasdiff breaking command
            api_name: Name of the API
            api_version: Version of the API
        
        Returns:
            List of normalized APIChangeEvent objects
        """
        changes = []
        
        logger.info("Normalizing diff results...")
        
        # Process endpoint changes
        paths = diff_result.get("paths", {})
        if paths:
            logger.info(f"Processing {len(paths)} path changes")
            for path, path_changes in paths.items():
                if isinstance(path_changes, dict):
                    changes.extend(self._process_path_changes(path, path_changes, api_name, api_version))
        
        # Process schema changes
        schemas = diff_result.get("schemas", {}) or diff_result.get("components", {}).get("schemas", {})
        if schemas:
            logger.info(f"Processing {len(schemas)} schema changes")
            for schema_name, schema_changes in schemas.items():
                if isinstance(schema_changes, dict):
                    changes.extend(self._process_schema_changes(schema_name, schema_changes, api_name, api_version))
        
        # Mark breaking changes
        breaking_set = self._create_breaking_set(breaking_changes)
        for change in changes:
            change_key = self._get_change_key(change)
            if change_key in breaking_set:
                change.breaking = True
                # Upgrade risk level for breaking changes
                if change.risk_level == RiskLevel.LOW:
                    change.risk_level = RiskLevel.MEDIUM
                elif change.risk_level == RiskLevel.MEDIUM:
                    change.risk_level = RiskLevel.HIGH
        
        logger.info(f"Normalized {len(changes)} changes")
        return changes
    
    def _process_path_changes(
        self,
        path: str,
        path_changes: Dict[str, Any],
        api_name: str,
        api_version: str
    ) -> List[APIChangeEvent]:
        """Process changes to API endpoints"""
        changes = []
        
        for method, method_changes in path_changes.items():
            if not isinstance(method_changes, dict):
                continue
            
            # Added endpoint
            if method_changes.get("added") or method_changes.get("status") == "added":
                changes.append(APIChangeEvent(
                    change_type=ChangeType.ADDED,
                    entity_type=EntityType.ENDPOINT,
                    entity_name=f"{method.upper()} {path}",
                    path=path,
                    http_method=method.upper(),
                    breaking=False,
                    risk_level=self._calculate_endpoint_risk(method_changes, "added"),
                    severity=Severity.MINOR,
                    change_details=method_changes,
                    api_name=api_name,
                    api_version=api_version,
                ))
            
            # Removed endpoint
            elif method_changes.get("deleted") or method_changes.get("status") == "deleted":
                changes.append(APIChangeEvent(
                    change_type=ChangeType.REMOVED,
                    entity_type=EntityType.ENDPOINT,
                    entity_name=f"{method.upper()} {path}",
                    path=path,
                    http_method=method.upper(),
                    breaking=True,  # Endpoint deletion is always breaking
                    risk_level=RiskLevel.HIGH,
                    severity=Severity.CRITICAL,
                    change_details=method_changes,
                    api_name=api_name,
                    api_version=api_version,
                ))
            
            # Modified endpoint
            elif method_changes.get("modified") or method_changes.get("status") == "modified":
                modifications = method_changes.get("modified", method_changes)
                changes.extend(
                    self._process_endpoint_modifications(
                        path, method, modifications, api_name, api_version
                    )
                )
        
        return changes
    
    def _process_endpoint_modifications(
        self,
        path: str,
        method: str,
        modifications: Dict[str, Any],
        api_name: str,
        api_version: str
    ) -> List[APIChangeEvent]:
        """Process modifications to an existing endpoint"""
        changes = []
        
        # Parameter changes
        if "parameters" in modifications:
            params = modifications["parameters"]
            if isinstance(params, list):
                for param_change in params:
                    changes.append(APIChangeEvent(
                        change_type=ChangeType.MODIFIED,
                        entity_type=EntityType.PARAMETER,
                        entity_name=f"{method.upper()} {path} - {param_change.get('name', 'parameter')}",
                        path=path,
                        http_method=method.upper(),
                        breaking=param_change.get("required", False),
                        risk_level=self._calculate_param_risk(param_change),
                        severity=Severity.MAJOR if param_change.get("required") else Severity.MINOR,
                        change_details=param_change,
                        api_name=api_name,
                        api_version=api_version,
                    ))
        
        # Request body changes
        if "requestBody" in modifications or "request" in modifications:
            request_change = modifications.get("requestBody") or modifications.get("request")
            changes.append(APIChangeEvent(
                change_type=ChangeType.MODIFIED,
                entity_type=EntityType.PARAMETER,
                entity_name=f"{method.upper()} {path} - Request Body",
                path=path,
                http_method=method.upper(),
                breaking=False,
                risk_level=RiskLevel.MEDIUM,
                severity=Severity.MAJOR,
                change_details=request_change if isinstance(request_change, dict) else {},
                api_name=api_name,
                api_version=api_version,
            ))
        
        # Response changes
        if "responses" in modifications or "response" in modifications:
            responses = modifications.get("responses") or modifications.get("response")
            if isinstance(responses, dict):
                for status_code, response_change in responses.items():
                    if isinstance(response_change, dict):
                        changes.append(APIChangeEvent(
                            change_type=ChangeType.MODIFIED,
                            entity_type=EntityType.RESPONSE,
                            entity_name=f"{method.upper()} {path} - {status_code}",
                            path=path,
                            http_method=method.upper(),
                            breaking=False,
                            risk_level=self._calculate_response_risk(response_change),
                            severity=Severity.MINOR,
                            change_details=response_change,
                            api_name=api_name,
                            api_version=api_version,
                        ))
        
        return changes
    
    def _process_schema_changes(
        self,
        schema_name: str,
        schema_changes: Dict[str, Any],
        api_name: str,
        api_version: str
    ) -> List[APIChangeEvent]:
        """Process changes to data schemas"""
        changes = []
        
        # Added schema
        if schema_changes.get("added") or schema_changes.get("status") == "added":
            changes.append(APIChangeEvent(
                change_type=ChangeType.ADDED,
                entity_type=EntityType.SCHEMA,
                entity_name=schema_name,
                breaking=False,
                risk_level=RiskLevel.LOW,
                severity=Severity.MINOR,
                change_details=schema_changes,
                api_name=api_name,
                api_version=api_version,
            ))
        
        # Removed schema
        elif schema_changes.get("deleted") or schema_changes.get("status") == "deleted":
            changes.append(APIChangeEvent(
                change_type=ChangeType.REMOVED,
                entity_type=EntityType.SCHEMA,
                entity_name=schema_name,
                breaking=True,
                risk_level=RiskLevel.HIGH,
                severity=Severity.CRITICAL,
                change_details=schema_changes,
                api_name=api_name,
                api_version=api_version,
            ))
        
        # Modified schema
        elif schema_changes.get("modified") or schema_changes.get("properties"):
            # Process property changes
            properties = schema_changes.get("properties", schema_changes.get("modified", {}).get("properties", []))
            
            if isinstance(properties, list):
                for prop_change in properties:
                    if isinstance(prop_change, dict):
                        prop_name = prop_change.get("name", "property")
                        changes.append(APIChangeEvent(
                            change_type=ChangeType.MODIFIED,
                            entity_type=EntityType.SCHEMA,
                            entity_name=f"{schema_name}.{prop_name}",
                            breaking=prop_change.get("required", False),
                            risk_level=self._calculate_schema_risk(prop_change),
                            severity=Severity.MAJOR if prop_change.get("required") else Severity.MINOR,
                            change_details=prop_change,
                            api_name=api_name,
                            api_version=api_version,
                        ))
        
        return changes
    
    def _calculate_endpoint_risk(
        self,
        changes: Dict[str, Any],
        change_type: str
    ) -> RiskLevel:
        """Calculate risk level for endpoint changes"""
        if change_type == "deleted":
            return RiskLevel.HIGH
        elif change_type == "added":
            # New public endpoints are medium risk
            return RiskLevel.MEDIUM if changes.get("public", True) else RiskLevel.LOW
        else:
            return RiskLevel.MEDIUM
    
    def _calculate_param_risk(self, param_change: Dict[str, Any]) -> RiskLevel:
        """Calculate risk level for parameter changes"""
        if param_change.get("required"):
            return RiskLevel.HIGH
        elif param_change.get("type_changed"):
            return RiskLevel.MEDIUM
        elif param_change.get("added"):
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_response_risk(self, response_change: Dict[str, Any]) -> RiskLevel:
        """Calculate risk level for response changes"""
        if response_change.get("schema_changed") or response_change.get("removed"):
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_schema_risk(self, prop_change: Dict[str, Any]) -> RiskLevel:
        """Calculate risk level for schema property changes"""
        if prop_change.get("required"):
            return RiskLevel.HIGH
        elif prop_change.get("type_changed") or prop_change.get("removed"):
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _create_breaking_set(
        self,
        breaking_changes: List[Dict[str, Any]]
    ) -> set:
        """Create set of breaking change identifiers"""
        breaking_set = set()
        for change in breaking_changes:
            # Create multiple keys to match different patterns
            method = change.get("method", "")
            path = change.get("path", "")
            field = change.get("field", "")
            
            breaking_set.add(f"{method}:{path}:{field}")
            breaking_set.add(f"{method.upper()}:{path}")
            breaking_set.add(f"{path}:{field}")
        
        return breaking_set
    
    def _get_change_key(self, change: APIChangeEvent) -> str:
        """Generate unique key for change matching"""
        return f"{change.http_method}:{change.path}:{change.entity_name}"
