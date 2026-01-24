"""
Repository for Functional Coverage & Impact Analysis.

Handles persistence for:
- Features
- Code Units
- External Test Cases
- Test-to-Feature Mappings
- Test-to-Code Coverage Mappings
- Change Events
- Change Impact
"""

from typing import List, Optional, Dict
import uuid
from datetime import datetime
from sqlalchemy import (
    select, insert, update, delete,
    func, and_, or_
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .functional_models import (
    Feature, CodeUnit, ExternalTestCase,
    TestCaseExternalMap, TestFeatureMap,
    TestCodeCoverageMap, ChangeEvent, ChangeImpact,
    FunctionalCoverageMapEntry, TestToFeatureCoverageEntry,
    ChangeImpactSurfaceEntry
)


class FunctionalCoverageRepository:
    """
    Repository for Functional Coverage data.
    
    Provides CRUD operations and queries for coverage analysis.
    """
    
    def __init__(self, session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
    
    # ========================================
    # FEATURE OPERATIONS
    # ========================================
    
    def upsert_feature(self, feature: Feature) -> uuid.UUID:
        """
        Insert or update a feature.
        
        Args:
            feature: Feature object
            
        Returns:
            Feature UUID
        """
        stmt = pg_insert(
            'feature'
        ).values(
            id=feature.id,
            name=feature.name,
            type=feature.type.value,
            source=feature.source.value,
            description=feature.description,
            parent_feature_id=feature.parent_feature_id,
            metadata=feature.metadata,
            updated_at=datetime.utcnow()
        ).on_conflict_do_update(
            constraint='feature_name_type_source_key',
            set_={
                'description': feature.description,
                'parent_feature_id': feature.parent_feature_id,
                'metadata': feature.metadata,
                'updated_at': datetime.utcnow()
            }
        ).returning('id')
        
        result = self.session.execute(stmt)
        self.session.commit()
        
        return result.scalar()
    
    def get_feature_by_name(
        self,
        name: str,
        feature_type: Optional[str] = None,
        source: Optional[str] = None
    ) -> Optional[Feature]:
        """
        Get feature by name.
        
        Args:
            name: Feature name
            feature_type: Optional feature type filter
            source: Optional source filter
            
        Returns:
            Feature object or None
        """
        query = "SELECT * FROM feature WHERE name = %s"
        params = [name]
        
        if feature_type:
            query += " AND type = %s"
            params.append(feature_type)
        
        if source:
            query += " AND source = %s"
            params.append(source)
        
        query += " LIMIT 1"
        
        result = self.session.execute(query, params).fetchone()
        
        if result:
            return Feature(
                id=result['id'],
                name=result['name'],
                type=result['type'],
                source=result['source'],
                description=result['description'],
                parent_feature_id=result['parent_feature_id'],
                metadata=result['metadata'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )
        
        return None
    
    def get_all_features(self) -> List[Feature]:
        """
        Get all features.
        
        Returns:
            List of Feature objects
        """
        query = "SELECT * FROM feature ORDER BY name"
        results = self.session.execute(query).fetchall()
        
        return [
            Feature(
                id=row['id'],
                name=row['name'],
                type=row['type'],
                source=row['source'],
                description=row['description'],
                parent_feature_id=row['parent_feature_id'],
                metadata=row['metadata'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            for row in results
        ]
    
    # ========================================
    # CODE UNIT OPERATIONS
    # ========================================
    
    def upsert_code_unit(self, code_unit: CodeUnit) -> uuid.UUID:
        """
        Insert or update a code unit.
        
        Args:
            code_unit: CodeUnit object
            
        Returns:
            Code unit UUID
        """
        stmt = pg_insert(
            'code_unit'
        ).values(
            id=code_unit.id,
            file_path=code_unit.file_path,
            class_name=code_unit.class_name,
            method_name=code_unit.method_name,
            package_name=code_unit.package_name,
            module_name=code_unit.module_name,
            line_start=code_unit.line_start,
            line_end=code_unit.line_end,
            complexity=code_unit.complexity,
            metadata=code_unit.metadata,
            updated_at=datetime.utcnow()
        ).on_conflict_do_update(
            constraint='code_unit_file_path_class_name_method_name_key',
            set_={
                'package_name': code_unit.package_name,
                'module_name': code_unit.module_name,
                'line_start': code_unit.line_start,
                'line_end': code_unit.line_end,
                'complexity': code_unit.complexity,
                'metadata': code_unit.metadata,
                'updated_at': datetime.utcnow()
            }
        ).returning('id')
        
        result = self.session.execute(stmt)
        self.session.commit()
        
        return result.scalar()
    
    def get_code_unit(
        self,
        file_path: str,
        class_name: Optional[str] = None,
        method_name: Optional[str] = None
    ) -> Optional[CodeUnit]:
        """
        Get code unit by location.
        
        Args:
            file_path: File path
            class_name: Optional class name
            method_name: Optional method name
            
        Returns:
            CodeUnit object or None
        """
        query = "SELECT * FROM code_unit WHERE file_path = %s"
        params = [file_path]
        
        if class_name is not None:
            query += " AND class_name = %s"
            params.append(class_name)
        else:
            query += " AND class_name IS NULL"
        
        if method_name is not None:
            query += " AND method_name = %s"
            params.append(method_name)
        else:
            query += " AND method_name IS NULL"
        
        query += " LIMIT 1"
        
        result = self.session.execute(query, params).fetchone()
        
        if result:
            return CodeUnit(
                id=result['id'],
                file_path=result['file_path'],
                class_name=result['class_name'],
                method_name=result['method_name'],
                package_name=result['package_name'],
                module_name=result['module_name'],
                line_start=result['line_start'],
                line_end=result['line_end'],
                complexity=result['complexity'],
                metadata=result['metadata'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )
        
        return None
    
    def get_code_units_by_file(self, file_path: str) -> List[CodeUnit]:
        """
        Get all code units in a file.
        
        Args:
            file_path: File path
            
        Returns:
            List of CodeUnit objects
        """
        query = "SELECT * FROM code_unit WHERE file_path = %s ORDER BY line_start"
        results = self.session.execute(query, [file_path]).fetchall()
        
        return [
            CodeUnit(
                id=row['id'],
                file_path=row['file_path'],
                class_name=row['class_name'],
                method_name=row['method_name'],
                package_name=row['package_name'],
                module_name=row['module_name'],
                line_start=row['line_start'],
                line_end=row['line_end'],
                complexity=row['complexity'],
                metadata=row['metadata'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            for row in results
        ]
    
    # ========================================
    # EXTERNAL TEST CASE OPERATIONS
    # ========================================
    
    def upsert_external_test_case(
        self,
        external_tc: ExternalTestCase
    ) -> uuid.UUID:
        """
        Insert or update an external test case.
        
        Args:
            external_tc: ExternalTestCase object
            
        Returns:
            External test case UUID
        """
        stmt = pg_insert(
            'external_test_case'
        ).values(
            id=external_tc.id,
            system=external_tc.system.value,
            external_id=external_tc.external_id,
            title=external_tc.title,
            description=external_tc.description,
            priority=external_tc.priority,
            status=external_tc.status,
            metadata=external_tc.metadata,
            updated_at=datetime.utcnow()
        ).on_conflict_do_update(
            constraint='external_test_case_system_external_id_key',
            set_={
                'title': external_tc.title,
                'description': external_tc.description,
                'priority': external_tc.priority,
                'status': external_tc.status,
                'metadata': external_tc.metadata,
                'updated_at': datetime.utcnow()
            }
        ).returning('id')
        
        result = self.session.execute(stmt)
        self.session.commit()
        
        return result.scalar()
    
    def get_external_test_case(
        self,
        system: str,
        external_id: str
    ) -> Optional[ExternalTestCase]:
        """
        Get external test case by system and ID.
        
        Args:
            system: System name (e.g., 'testrail')
            external_id: External ID (e.g., 'C12345')
            
        Returns:
            ExternalTestCase object or None
        """
        query = """
            SELECT * FROM external_test_case 
            WHERE system = %s AND external_id = %s
            LIMIT 1
        """
        result = self.session.execute(
            query,
            [system, external_id]
        ).fetchone()
        
        if result:
            return ExternalTestCase(
                id=result['id'],
                system=result['system'],
                external_id=result['external_id'],
                title=result['title'],
                description=result['description'],
                priority=result['priority'],
                status=result['status'],
                metadata=result['metadata'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )
        
        return None
    
    # ========================================
    # MAPPING OPERATIONS
    # ========================================
    
    def create_test_external_mapping(
        self,
        mapping: TestCaseExternalMap
    ) -> None:
        """
        Create test-to-external-test-case mapping.
        
        Args:
            mapping: TestCaseExternalMap object
        """
        stmt = pg_insert(
            'test_case_external_map'
        ).values(
            test_case_id=mapping.test_case_id,
            external_test_case_id=mapping.external_test_case_id,
            confidence=mapping.confidence,
            source=mapping.source.value,
            discovery_run_id=mapping.discovery_run_id,
            metadata=mapping.metadata
        ).on_conflict_do_nothing()
        
        self.session.execute(stmt)
        self.session.commit()
    
    def create_test_feature_mapping(
        self,
        mapping: TestFeatureMap
    ) -> uuid.UUID:
        """
        Create test-to-feature mapping.
        
        Args:
            mapping: TestFeatureMap object
            
        Returns:
            Mapping UUID
        """
        stmt = pg_insert(
            'test_feature_map'
        ).values(
            id=mapping.id,
            test_case_id=mapping.test_case_id,
            feature_id=mapping.feature_id,
            confidence=mapping.confidence,
            source=mapping.source.value,
            discovery_run_id=mapping.discovery_run_id,
            metadata=mapping.metadata
        ).on_conflict_do_update(
            constraint='test_feature_map_test_case_id_feature_id_source_key',
            set_={
                'confidence': mapping.confidence,
                'metadata': mapping.metadata
            }
        ).returning('id')
        
        result = self.session.execute(stmt)
        self.session.commit()
        
        return result.scalar()
    
    def create_test_code_coverage_mapping(
        self,
        mapping: TestCodeCoverageMap
    ) -> uuid.UUID:
        """
        Create test-to-code-unit coverage mapping.
        
        Args:
            mapping: TestCodeCoverageMap object
            
        Returns:
            Mapping UUID
        """
        stmt = pg_insert(
            'test_code_coverage_map'
        ).values(
            id=mapping.id,
            test_case_id=mapping.test_case_id,
            code_unit_id=mapping.code_unit_id,
            coverage_type=mapping.coverage_type,
            covered_count=mapping.covered_count,
            missed_count=mapping.missed_count,
            coverage_percentage=mapping.coverage_percentage,
            confidence=mapping.confidence,
            execution_mode=mapping.execution_mode,
            discovery_run_id=mapping.discovery_run_id,
            metadata=mapping.metadata
        ).on_conflict_do_update(
            constraint='test_code_coverage_map_test_case_id_code_unit_id_coverage__key',
            set_={
                'covered_count': mapping.covered_count,
                'missed_count': mapping.missed_count,
                'coverage_percentage': mapping.coverage_percentage,
                'confidence': mapping.confidence,
                'execution_mode': mapping.execution_mode,
                'metadata': mapping.metadata
            }
        ).returning('id')
        
        result = self.session.execute(stmt)
        self.session.commit()
        
        return result.scalar()
    
    # ========================================
    # QUERY OPERATIONS (for console output)
    # ========================================
    
    def get_functional_coverage_map(
        self,
        limit: Optional[int] = None
    ) -> List[FunctionalCoverageMapEntry]:
        """
        Get Functional Coverage Map.
        
        Shows: Code Unit → Tests Covering → TestRail TCs
        
        Args:
            limit: Optional limit on results
            
        Returns:
            List of FunctionalCoverageMapEntry
        """
        query = """
            SELECT * FROM functional_coverage_map
            ORDER BY test_count DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        results = self.session.execute(query).fetchall()
        
        entries = []
        for row in results:
            code_unit = row['file_path']
            if row['class_name']:
                code_unit = f"{row['class_name']}"
                if row['method_name']:
                    code_unit += f".{row['method_name']}"
            
            testrail_tcs = []
            if row['testrail_tcs']:
                testrail_tcs = [
                    tc.strip()
                    for tc in row['testrail_tcs'].split(',')
                    if tc.strip()
                ]
            
            entries.append(FunctionalCoverageMapEntry(
                code_unit=code_unit,
                test_count=row['test_count'],
                testrail_tcs=testrail_tcs,
                avg_coverage=row['avg_coverage_percentage']
            ))
        
        return entries
    
    def get_test_to_feature_coverage(
        self,
        feature_filter: Optional[str] = None
    ) -> List[TestToFeatureCoverageEntry]:
        """
        Get Test-to-Feature Coverage.
        
        Shows: Feature → Test → TestRail TC
        
        Args:
            feature_filter: Optional feature name filter
            
        Returns:
            List of TestToFeatureCoverageEntry
        """
        query = "SELECT * FROM test_to_feature_coverage"
        params = []
        
        if feature_filter:
            query += " WHERE feature LIKE %s"
            params.append(f"%{feature_filter}%")
        
        query += " ORDER BY feature, test_name"
        
        results = self.session.execute(query, params).fetchall()
        
        return [
            TestToFeatureCoverageEntry(
                feature=row['feature'],
                feature_type=row['feature_type'],
                test_name=row['test_name'],
                testrail_tc=row['testrail_tc'],
                confidence=row['confidence']
            )
            for row in results
        ]
    
    def get_change_impact_surface(
        self,
        file_path: str
    ) -> List[ChangeImpactSurfaceEntry]:
        """
        Get Change Impact Surface for a file.
        
        Shows: Impacted Test → Feature → TestRail TC
        
        Args:
            file_path: Path to changed file
            
        Returns:
            List of ChangeImpactSurfaceEntry
        """
        query = """
            SELECT * FROM change_impact_surface
            WHERE changed_file = %s
            ORDER BY coverage_percentage DESC
        """
        
        results = self.session.execute(query, [file_path]).fetchall()
        
        return [
            ChangeImpactSurfaceEntry(
                impacted_test=row['impacted_test'],
                feature=row['feature'],
                testrail_tc=row['testrail_tc'],
                coverage_percentage=row['coverage_percentage']
            )
            for row in results
        ]
    
    def get_coverage_gaps(self) -> List[Feature]:
        """
        Get features without test coverage.
        
        Returns:
            List of Feature objects
        """
        query = "SELECT * FROM coverage_gaps ORDER BY feature_type, feature"
        results = self.session.execute(query).fetchall()
        
        return [
            Feature(
                name=row['feature'],
                type=row['feature_type'],
                source=row['feature_source'],
                id=uuid.uuid4()  # Placeholder
            )
            for row in results
        ]
    
    # ========================================
    # CHANGE EVENT OPERATIONS
    # ========================================
    
    def create_change_event(self, event: ChangeEvent) -> uuid.UUID:
        """
        Create a change event.
        
        Args:
            event: ChangeEvent object
            
        Returns:
            Event UUID
        """
        stmt = insert('change_event').values(
            id=event.id,
            commit_sha=event.commit_sha,
            commit_message=event.commit_message,
            author=event.author,
            file_path=event.file_path,
            change_type=event.change_type.value if event.change_type else None,
            lines_added=event.lines_added,
            lines_removed=event.lines_removed,
            branch=event.branch,
            timestamp=event.timestamp,
            metadata=event.metadata
        ).returning('id')
        
        result = self.session.execute(stmt)
        self.session.commit()
        
        return result.scalar()
    
    def create_change_impact(self, impact: ChangeImpact) -> uuid.UUID:
        """
        Create a change impact record.
        
        Args:
            impact: ChangeImpact object
            
        Returns:
            Impact UUID
        """
        stmt = pg_insert(
            'change_impact'
        ).values(
            id=impact.id,
            change_event_id=impact.change_event_id,
            test_case_id=impact.test_case_id,
            feature_id=impact.feature_id,
            impact_score=impact.impact_score,
            impact_reason=impact.impact_reason.value if impact.impact_reason else None,
            metadata=impact.metadata
        ).on_conflict_do_update(
            constraint='change_impact_change_event_id_test_case_id_key',
            set_={
                'impact_score': impact.impact_score,
                'impact_reason': impact.impact_reason.value if impact.impact_reason else None,
                'metadata': impact.metadata
            }
        ).returning('id')
        
        result = self.session.execute(stmt)
        self.session.commit()
        
        return result.scalar()
