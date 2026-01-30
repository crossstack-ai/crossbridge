"""
Unit tests for unified model format in impact_models.

Tests the to_unified_model() conversion for database compatibility.
"""

import pytest
from datetime import datetime
from adapters.common.impact_models import (
    MappingSource,
    PageObjectReference,
    TestToPageObjectMapping,
    PageObjectImpactMap
)


class TestUnifiedModelConversion:
    """Test conversion to unified data model format."""
    
    def test_mapping_to_unified_model_basic(self):
        """Test basic conversion to unified model format."""
        mapping = TestToPageObjectMapping(
            test_id="LoginTest.testValidLogin",
            test_file="src/test/java/LoginTest.java",
            mapping_source=MappingSource.STATIC_AST,
            confidence=0.85
        )
        mapping.add_page_object("LoginPage", "instantiation", 15)
        
        unified = mapping.to_unified_model("LoginPage")
        
        # Verify format: {test_id, page_object, source, confidence}
        assert unified["test_id"] == "LoginTest.testValidLogin"
        assert unified["page_object"] == "LoginPage"
        assert unified["source"] == "static_ast"
        assert unified["confidence"] == 0.85
    
    def test_mapping_to_unified_model_different_sources(self):
        """Test unified model with different mapping sources."""
        sources = [
            (MappingSource.STATIC_AST, "static_ast"),
            (MappingSource.CODE_COVERAGE, "coverage"),
            (MappingSource.AI, "ai"),
            (MappingSource.RUNTIME_TRACE, "runtime_trace"),
            (MappingSource.MANUAL, "manual")
        ]
        
        for source_enum, source_str in sources:
            mapping = TestToPageObjectMapping(
                test_id="Test.test",
                test_file="test.java",
                mapping_source=source_enum,
                confidence=0.9
            )
            mapping.add_page_object("Page", "import")
            
            unified = mapping.to_unified_model("Page")
            assert unified["source"] == source_str
    
    def test_mapping_to_unified_model_confidence_range(self):
        """Test unified model with various confidence values."""
        confidences = [0.0, 0.5, 0.85, 1.0]
        
        for conf in confidences:
            mapping = TestToPageObjectMapping(
                test_id="Test.test",
                test_file="test.java",
                confidence=conf
            )
            mapping.add_page_object("Page")
            
            unified = mapping.to_unified_model("Page")
            assert unified["confidence"] == conf
            assert 0.0 <= unified["confidence"] <= 1.0
    
    def test_mapping_to_unified_model_multiple_page_objects(self):
        """Test unified model when mapping has multiple Page Objects."""
        mapping = TestToPageObjectMapping(
            test_id="FlowTest.testCompleteFlow",
            test_file="src/test/java/FlowTest.java",
            mapping_source=MappingSource.STATIC_AST,
            confidence=0.88
        )
        mapping.add_page_object("LoginPage", "fixture")
        mapping.add_page_object("HomePage", "instantiation")
        mapping.add_page_object("SettingsPage", "import")
        
        # Should be able to generate unified model for each PO
        login_unified = mapping.to_unified_model("LoginPage")
        assert login_unified["page_object"] == "LoginPage"
        assert login_unified["test_id"] == "FlowTest.testCompleteFlow"
        
        home_unified = mapping.to_unified_model("HomePage")
        assert home_unified["page_object"] == "HomePage"
        assert home_unified["test_id"] == "FlowTest.testCompleteFlow"


class TestMappingSourceEnum:
    """Test MappingSource enum values."""
    
    def test_mapping_source_values(self):
        """Test all mapping source enum values."""
        assert MappingSource.STATIC_AST.value == "static_ast"
        assert MappingSource.RUNTIME_TRACE.value == "runtime_trace"
        assert MappingSource.CODE_COVERAGE.value == "coverage"
        assert MappingSource.AI.value == "ai"
        assert MappingSource.MANUAL.value == "manual"
        assert MappingSource.INFERRED.value == "inferred"
    
    def test_mapping_source_phase_alignment(self):
        """Test that sources align with analysis stages."""
        # Static AST Analysis
        static_sources = [MappingSource.STATIC_AST]
        
        # Runtime and Coverage Analysis
        runtime_sources = [MappingSource.RUNTIME_TRACE, MappingSource.CODE_COVERAGE]
        
        # AI Enhancement
        ai_sources = [MappingSource.AI]
        
        # Verify all exist
        for source in static_sources + runtime_sources + ai_sources:
            assert source in MappingSource


class TestPageObjectReference:
    """Test PageObjectReference data class."""
    
    def test_reference_creation(self):
        """Test creating a Page Object reference."""
        ref = PageObjectReference(
            page_object_class="com.example.pages.LoginPage",
            usage_type="instantiation",
            line_number=25,
            source_file="src/test/java/LoginTest.java"
        )
        
        assert ref.page_object_class == "com.example.pages.LoginPage"
        assert ref.usage_type == "instantiation"
        assert ref.line_number == 25
        assert ref.source_file == "src/test/java/LoginTest.java"
    
    def test_reference_simple_name(self):
        """Test extracting simple name from qualified name."""
        ref = PageObjectReference(
            page_object_class="com.example.pages.LoginPage",
            usage_type="import"
        )
        
        assert ref.get_simple_name() == "LoginPage"
    
    def test_reference_simple_name_already_simple(self):
        """Test simple name extraction when already simple."""
        ref = PageObjectReference(
            page_object_class="LoginPage",
            usage_type="fixture"
        )
        
        assert ref.get_simple_name() == "LoginPage"


class TestTestToPageObjectMapping:
    """Test TestToPageObjectMapping data class."""
    
    def test_mapping_creation(self):
        """Test creating a test-to-PO mapping."""
        mapping = TestToPageObjectMapping(
            test_id="LoginTest.testValidLogin",
            test_file="src/test/java/LoginTest.java",
            mapping_source=MappingSource.STATIC_AST,
            confidence=0.85
        )
        
        assert mapping.test_id == "LoginTest.testValidLogin"
        assert mapping.mapping_source == MappingSource.STATIC_AST
        assert mapping.confidence == 0.85
    
    def test_add_page_object(self):
        """Test adding Page Objects to mapping."""
        mapping = TestToPageObjectMapping(
            test_id="Test.test",
            test_file="Test.java"
        )
        
        mapping.add_page_object("LoginPage", "instantiation", 15)
        mapping.add_page_object("HomePage", "import", 5)
        
        assert len(mapping.page_objects) == 2
        assert "LoginPage" in mapping.page_objects
        assert "HomePage" in mapping.page_objects
        assert len(mapping.references) == 2
    
    def test_get_page_object_count(self):
        """Test counting unique Page Objects."""
        mapping = TestToPageObjectMapping(
            test_id="Test.test",
            test_file="Test.java"
        )
        
        mapping.add_page_object("LoginPage")
        mapping.add_page_object("HomePage")
        mapping.add_page_object("LoginPage")  # Duplicate
        
        assert mapping.get_page_object_count() == 2
    
    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        mapping = TestToPageObjectMapping(
            test_id="Test.test",
            test_file="Test.java",
            mapping_source=MappingSource.STATIC_AST,
            confidence=0.9
        )
        mapping.add_page_object("LoginPage", "fixture", 10)
        
        data = mapping.to_dict()
        
        assert data["test_id"] == "Test.test"
        assert data["test_file"] == "Test.java"
        assert data["mapping_source"] == "static_ast"
        assert data["confidence"] == 0.9
        assert len(data["page_objects"]) == 1
        assert len(data["references"]) == 1


class TestPageObjectImpactMap:
    """Test PageObjectImpactMap functionality."""
    
    def test_impact_map_creation(self):
        """Test creating an impact map."""
        impact_map = PageObjectImpactMap(project_root="/project")
        
        assert impact_map.project_root == "/project"
        assert len(impact_map.mappings) == 0
    
    def test_add_mapping(self):
        """Test adding mappings to impact map."""
        impact_map = PageObjectImpactMap(project_root="/project")
        
        mapping = TestToPageObjectMapping(
            test_id="Test.test",
            test_file="Test.java"
        )
        mapping.add_page_object("LoginPage")
        
        impact_map.add_mapping(mapping)
        
        assert len(impact_map.mappings) == 1
    
    def test_get_impacted_tests(self):
        """Test querying impacted tests."""
        impact_map = PageObjectImpactMap(project_root="/project")
        
        mapping1 = TestToPageObjectMapping(
            test_id="Test1.test",
            test_file="Test1.java"
        )
        mapping1.add_page_object("LoginPage")
        
        mapping2 = TestToPageObjectMapping(
            test_id="Test2.test",
            test_file="Test2.java"
        )
        mapping2.add_page_object("LoginPage")
        mapping2.add_page_object("HomePage")
        
        impact_map.add_mapping(mapping1)
        impact_map.add_mapping(mapping2)
        
        # Query impacted tests
        login_tests = impact_map.get_impacted_tests("LoginPage")
        assert len(login_tests) == 2
        assert "Test1.test" in login_tests
        assert "Test2.test" in login_tests
        
        home_tests = impact_map.get_impacted_tests("HomePage")
        assert len(home_tests) == 1
        assert "Test2.test" in home_tests
    
    def test_get_statistics(self):
        """Test getting impact map statistics."""
        impact_map = PageObjectImpactMap(project_root="/project")
        
        mapping1 = TestToPageObjectMapping(
            test_id="Test1.test",
            test_file="Test1.java"
        )
        mapping1.add_page_object("LoginPage")
        mapping1.add_page_object("HomePage")
        
        mapping2 = TestToPageObjectMapping(
            test_id="Test2.test",
            test_file="Test2.java"
        )
        mapping2.add_page_object("LoginPage")
        
        impact_map.add_mapping(mapping1)
        impact_map.add_mapping(mapping2)
        
        stats = impact_map.get_statistics()
        
        assert stats["total_tests"] == 2
        assert stats["total_page_objects"] == 2
        assert stats["total_mappings"] == 2


class TestMultiPhaseCompatibility:
    """Test compatibility with multi-stage mapping approach."""
    
    def test_static_ast_phase(self):
        """Test static AST analysis mappings."""
        mapping = TestToPageObjectMapping(
            test_id="Test.test",
            test_file="Test.java",
            mapping_source=MappingSource.STATIC_AST,
            confidence=0.85
        )
        mapping.add_page_object("LoginPage")
        
        unified = mapping.to_unified_model("LoginPage")
        assert unified["source"] == "static_ast"
    
    def test_coverage_phase(self):
        """Test code coverage analysis mappings."""
        mapping = TestToPageObjectMapping(
            test_id="Test.test",
            test_file="Test.java",
            mapping_source=MappingSource.CODE_COVERAGE,
            confidence=0.95
        )
        mapping.add_page_object("LoginPage")
        
        unified = mapping.to_unified_model("LoginPage")
        assert unified["source"] == "coverage"
    
    def test_ai_phase(self):
        """Test AI-inferred mappings."""
        mapping = TestToPageObjectMapping(
            test_id="Test.test",
            test_file="Test.java",
            mapping_source=MappingSource.AI,
            confidence=0.72
        )
        mapping.add_page_object("LoginPage")
        
        unified = mapping.to_unified_model("LoginPage")
        assert unified["source"] == "ai"
    
    def test_multiple_phases_same_mapping(self):
        """Test same test-PO pair detected in multiple analysis stages."""
        # Static Analysis
        mapping1 = TestToPageObjectMapping(
            test_id="Test.test",
            test_file="Test.java",
            mapping_source=MappingSource.STATIC_AST,
            confidence=0.85
        )
        mapping1.add_page_object("LoginPage")
        
        # Coverage Analysis
        mapping2 = TestToPageObjectMapping(
            test_id="Test.test",
            test_file="Test.java",
            mapping_source=MappingSource.CODE_COVERAGE,
            confidence=0.95
        )
        mapping2.add_page_object("LoginPage")
        
        # Both should produce valid unified models
        unified1 = mapping1.to_unified_model("LoginPage")
        unified2 = mapping2.to_unified_model("LoginPage")
        
        assert unified1["test_id"] == unified2["test_id"]
        assert unified1["page_object"] == unified2["page_object"]
        assert unified1["source"] != unified2["source"]
        assert unified1["confidence"] != unified2["confidence"]
