"""
Unit tests for StepMappingResolver.

Tests signal-driven step-to-code-path resolution.
"""
import pytest
from adapters.common.mapping.models import StepSignal, SignalType, CodeReference
from adapters.common.mapping.registry import StepSignalRegistry
from adapters.common.mapping.resolver import StepMappingResolver


class TestBasicStepMapping:
    """Test basic step mapping functionality."""
    
    def test_resolve_step_with_code_path_signal(self):
        """Given a step and registered CODE_PATH signal, resolver returns correct mapping."""
        registry = StepSignalRegistry()
        registry.register_signal(
            "user logs in",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/login_page.py::LoginPage.login"
            )
        )
        
        resolver = StepMappingResolver(registry)
        mapping = resolver.resolve_step("when user logs in")
        
        assert mapping.step == "user logs in"
        assert "LoginPage" in mapping.page_objects
        assert "login" in mapping.methods
        assert "pages/login_page.py::LoginPage.login" in mapping.code_paths
    
    def test_resolve_step_with_page_object_signal(self):
        """PAGE_OBJECT signal should populate page_objects list."""
        registry = StepSignalRegistry()
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        
        resolver = StepMappingResolver(registry)
        mapping = resolver.resolve_step("user logs in")
        
        assert "LoginPage" in mapping.page_objects
    
    def test_resolve_step_with_method_signal(self):
        """METHOD signal should populate methods list."""
        registry = StepSignalRegistry()
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.METHOD, value="login")
        )
        
        resolver = StepMappingResolver(registry)
        mapping = resolver.resolve_step("user logs in")
        
        assert "login" in mapping.methods
    
    def test_resolve_step_with_multiple_signals(self):
        """Multiple signals for same step should all contribute to mapping."""
        registry = StepSignalRegistry()
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.METHOD, value="login")
        )
        registry.register_signal(
            "user logs in",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/login_page.py::LoginPage.login"
            )
        )
        
        resolver = StepMappingResolver(registry)
        mapping = resolver.resolve_step("user logs in")
        
        assert "LoginPage" in mapping.page_objects
        assert "login" in mapping.methods
        assert "pages/login_page.py::LoginPage.login" in mapping.code_paths
    
    def test_resolve_step_removes_bdd_keywords(self):
        """BDD keywords should be removed for normalized step text."""
        registry = StepSignalRegistry()
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        
        resolver = StepMappingResolver(registry)
        
        # All should resolve to same normalized step
        mapping1 = resolver.resolve_step("Given user logs in")
        mapping2 = resolver.resolve_step("When user logs in")
        mapping3 = resolver.resolve_step("Then user logs in")
        
        assert mapping1.step == mapping2.step == mapping3.step == "user logs in"
        assert all("LoginPage" in m.page_objects for m in [mapping1, mapping2, mapping3])


class TestDeterminismAndSafety:
    """Test deterministic behavior and safety guarantees."""
    
    def test_empty_mapping_when_no_signals(self):
        """Unknown steps should return empty mapping, not error."""
        registry = StepSignalRegistry()
        resolver = StepMappingResolver(registry)
        
        mapping = resolver.resolve_step("unknown step")
        
        assert mapping.step == "unknown step"
        assert mapping.page_objects == []
        assert mapping.methods == []
        assert mapping.code_paths == []
        assert mapping.signals == []
    
    def test_order_preserved(self):
        """Signal registration order should be preserved in mapping."""
        registry = StepSignalRegistry()
        
        # Register in specific order
        registry.register_signal(
            "user performs action",
            StepSignal(type=SignalType.PAGE_OBJECT, value="FirstPage")
        )
        registry.register_signal(
            "user performs action",
            StepSignal(type=SignalType.PAGE_OBJECT, value="SecondPage")
        )
        registry.register_signal(
            "user performs action",
            StepSignal(type=SignalType.PAGE_OBJECT, value="ThirdPage")
        )
        
        resolver = StepMappingResolver(registry)
        mapping = resolver.resolve_step("user performs action")
        
        # Order should match registration order
        assert mapping.page_objects == ["FirstPage", "SecondPage", "ThirdPage"]
    
    def test_no_mutation_of_registry(self):
        """Resolver should not mutate the registry."""
        registry = StepSignalRegistry()
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        
        initial_count = registry.count()
        
        resolver = StepMappingResolver(registry)
        resolver.resolve_step("user logs in")
        resolver.resolve_step("user logs in")
        
        # Registry should be unchanged
        assert registry.count() == initial_count
    
    def test_no_duplicates_in_mapping(self):
        """Duplicate signals should not create duplicate entries in mapping."""
        registry = StepSignalRegistry()
        
        # Register same signal multiple times
        for _ in range(3):
            registry.register_signal(
                "user logs in",
                StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
            )
        
        resolver = StepMappingResolver(registry)
        mapping = resolver.resolve_step("user logs in")
        
        # Should only appear once
        assert mapping.page_objects.count("LoginPage") == 1
    
    def test_multiple_calls_identical_results(self):
        """Multiple calls with same step should produce identical results."""
        registry = StepSignalRegistry()
        registry.register_signal(
            "user logs in",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/login_page.py::LoginPage.login"
            )
        )
        
        resolver = StepMappingResolver(registry)
        
        mapping1 = resolver.resolve_step("user logs in")
        mapping2 = resolver.resolve_step("user logs in")
        
        assert mapping1.step == mapping2.step
        assert mapping1.page_objects == mapping2.page_objects
        assert mapping1.methods == mapping2.methods
        assert mapping1.code_paths == mapping2.code_paths


class TestMultiStepMapping:
    """Test scenarios where single step maps to multiple code paths."""
    
    def test_step_maps_to_multiple_page_objects(self):
        """A step may interact with multiple Page Objects."""
        registry = StepSignalRegistry()
        
        # Step interacts with LoginPage and Dashboard
        registry.register_signal(
            "user logs in",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/login_page.py::LoginPage.login"
            )
        )
        registry.register_signal(
            "user logs in",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/dashboard.py::DashboardPage.verify_logged_in"
            )
        )
        
        resolver = StepMappingResolver(registry)
        mapping = resolver.resolve_step("user logs in")
        
        assert "LoginPage" in mapping.page_objects
        assert "DashboardPage" in mapping.page_objects
        assert len(mapping.code_paths) == 2
    
    def test_step_maps_to_ui_and_api(self):
        """A step may involve both UI actions and API calls."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user creates account",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/signup_page.py::SignupPage.fill_form"
            )
        )
        registry.register_signal(
            "user creates account",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="api/user_api.py::UserAPI.create_user"
            )
        )
        
        resolver = StepMappingResolver(registry)
        mapping = resolver.resolve_step("user creates account")
        
        assert len(mapping.code_paths) == 2
        assert any("signup_page.py" in path for path in mapping.code_paths)
        assert any("user_api.py" in path for path in mapping.code_paths)
    
    def test_complex_step_with_multiple_methods(self):
        """Complex step may invoke multiple methods on same Page Object."""
        registry = StepSignalRegistry()
        
        registry.register_signal(
            "user fills login form",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/login_page.py::LoginPage.enter_username"
            )
        )
        registry.register_signal(
            "user fills login form",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/login_page.py::LoginPage.enter_password"
            )
        )
        registry.register_signal(
            "user fills login form",
            StepSignal(
                type=SignalType.CODE_PATH,
                value="pages/login_page.py::LoginPage.click_submit"
            )
        )
        
        resolver = StepMappingResolver(registry)
        mapping = resolver.resolve_step("user fills login form")
        
        # Should have 1 page object but 3 methods
        assert mapping.page_objects == ["LoginPage"]
        assert len(mapping.methods) == 3
        assert "enter_username" in mapping.methods
        assert "enter_password" in mapping.methods
        assert "click_submit" in mapping.methods


class TestBatchResolution:
    """Test resolving multiple steps in batch."""
    
    def test_resolve_multiple_steps(self):
        """resolve_steps should resolve multiple steps in order."""
        registry = StepSignalRegistry()
        registry.register_signal(
            "user logs in",
            StepSignal(type=SignalType.PAGE_OBJECT, value="LoginPage")
        )
        registry.register_signal(
            "user logs out",
            StepSignal(type=SignalType.PAGE_OBJECT, value="HeaderPage")
        )
        
        resolver = StepMappingResolver(registry)
        mappings = resolver.resolve_steps(["user logs in", "user logs out"])
        
        assert len(mappings) == 2
        assert "LoginPage" in mappings[0].page_objects
        assert "HeaderPage" in mappings[1].page_objects
    
    def test_resolve_steps_preserves_order(self):
        """Batch resolution should preserve input order."""
        registry = StepSignalRegistry()
        
        steps = ["step1", "step2", "step3", "step4"]
        resolver = StepMappingResolver(registry)
        mappings = resolver.resolve_steps(steps)
        
        assert [m.step for m in mappings] == steps


class TestCodePathParsing:
    """Test parsing of code path strings."""
    
    def test_parse_full_code_path(self):
        """Test parsing file::Class.method format."""
        registry = StepSignalRegistry()
        resolver = StepMappingResolver(registry)
        
        code_ref = resolver._parse_code_path("pages/login_page.py::LoginPage.login")
        
        assert code_ref.file_path == "pages/login_page.py"
        assert code_ref.class_name == "LoginPage"
        assert code_ref.method_name == "login"
    
    def test_parse_code_path_class_only(self):
        """Test parsing file::Class format."""
        registry = StepSignalRegistry()
        resolver = StepMappingResolver(registry)
        
        code_ref = resolver._parse_code_path("pages/login_page.py::LoginPage")
        
        assert code_ref.file_path == "pages/login_page.py"
        assert code_ref.class_name == "LoginPage"
        assert code_ref.method_name is None
    
    def test_parse_code_path_method_only(self):
        """Test parsing file::method format (lowercase = method)."""
        registry = StepSignalRegistry()
        resolver = StepMappingResolver(registry)
        
        code_ref = resolver._parse_code_path("utils/helpers.py::validate")
        
        assert code_ref.file_path == "utils/helpers.py"
        assert code_ref.class_name is None
        assert code_ref.method_name == "validate"
    
    def test_parse_file_path_only(self):
        """Test parsing just a file path."""
        registry = StepSignalRegistry()
        resolver = StepMappingResolver(registry)
        
        code_ref = resolver._parse_code_path("pages/login_page.py")
        
        assert code_ref.file_path == "pages/login_page.py"
        assert code_ref.class_name is None
        assert code_ref.method_name is None


class TestSignalExtraction:
    """Test extraction of page objects and methods from signals."""
    
    def test_extract_page_object_from_dotted_name(self):
        """Extract class from 'LoginPage.login' format."""
        registry = StepSignalRegistry()
        resolver = StepMappingResolver(registry)
        
        page_object = resolver._extract_page_object_name("LoginPage.login")
        
        assert page_object == "LoginPage"
    
    def test_extract_method_from_dotted_name(self):
        """Extract method from 'LoginPage.login' format."""
        registry = StepSignalRegistry()
        resolver = StepMappingResolver(registry)
        
        method = resolver._extract_method_name("LoginPage.login")
        
        assert method == "login"
    
    def test_extract_from_code_path(self):
        """Extract class/method from full code path."""
        registry = StepSignalRegistry()
        resolver = StepMappingResolver(registry)
        
        page_object = resolver._extract_page_object_name(
            "pages/login_page.py::LoginPage.login"
        )
        method = resolver._extract_method_name(
            "pages/login_page.py::LoginPage.login"
        )
        
        assert page_object == "LoginPage"
        assert method == "login"
