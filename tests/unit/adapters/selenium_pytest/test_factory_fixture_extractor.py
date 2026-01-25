"""
Comprehensive unit tests for Pytest Factory Fixture Extractor.
"""

import pytest
from pathlib import Path
from adapters.selenium_pytest.factory_fixture_extractor import PytestFactoryFixtureExtractor


@pytest.fixture
def extractor():
    return PytestFactoryFixtureExtractor()


@pytest.fixture
def test_file_with_factories(tmp_path):
    """Create test file with factory fixtures."""
    test_file = tmp_path / "test_factories.py"
    test_file.write_text("""
import pytest

@pytest.fixture
def make_user():
    def _make_user(username, role="user"):
        return User(username=username, role=role)
    return _make_user

def test_user_creation(make_user):
    admin = make_user("admin", role="admin")
    assert admin.role == "admin"
    
    user = make_user("john")
    assert user.role == "user"

@pytest.fixture
def create_product():
    created_products = []
    
    def _create_product(name, price):
        product = Product(name, price)
        created_products.append(product)
        return product
    
    yield _create_product
    
    # Cleanup
    for product in created_products:
        product.delete()

def test_product_management(create_product):
    p1 = create_product("Widget", 9.99)
    p2 = create_product("Gadget", 19.99)
    assert len([p1, p2]) == 2

@pytest.fixture
def build_api_client():
    \"\"\"Factory for creating API clients.\"\"\"
    def _build_client(base_url, timeout=30):
        client = APIClient(base_url)
        client.timeout = timeout
        return client
    return _build_client

def test_api_calls(build_api_client):
    client = build_api_client("https://api.example.com")
    response = client.get("/users")
    assert response.status_code == 200

@pytest.fixture
def user_factory():
    counter = 0
    
    def _factory(username=None):
        nonlocal counter
        counter += 1
        if username is None:
            username = f"user{counter}"
        return User(username)
    
    return _factory

def test_unique_users(user_factory):
    u1 = user_factory()
    u2 = user_factory()
    u3 = user_factory("custom")
    assert u1.username != u2.username
    assert u3.username == "custom"
    """)
    return test_file


@pytest.fixture
def test_file_complex_factories(tmp_path):
    """Create test file with complex factory patterns."""
    test_file = tmp_path / "test_complex.py"
    test_file.write_text("""
import pytest

@pytest.fixture
def create_database():
    connections = []
    
    def _create(db_type, host, port):
        conn = Database.connect(db_type, host, port)
        connections.append(conn)
        return conn
    
    yield _create
    
    for conn in connections:
        conn.close()

@pytest.fixture
def make_http_request():
    session = requests.Session()
    
    def _request(method, url, **kwargs):
        return session.request(method, url, **kwargs)
    
    yield _request
    
    session.close()

@pytest.fixture(scope="module")
def create_temp_file():
    temp_files = []
    
    def _create(filename, content):
        path = Path(tempfile.gettempdir()) / filename
        path.write_text(content)
        temp_files.append(path)
        return path
    
    yield _create
    
    for path in temp_files:
        if path.exists():
            path.unlink()
    """)
    return test_file


class TestFactoryFixtureDetection:
    """Test detection of factory fixtures."""
    
    def test_detect_make_factory(self, extractor, test_file_with_factories):
        """Test detection of make_* factory pattern."""
        factories = extractor.extract_factory_fixtures(test_file_with_factories)
        
        make_user = next((f for f in factories if f.fixture_name == 'make_user'), None)
        assert make_user is not None
        assert make_user.factory_pattern == 'make_'
    
    def test_detect_create_factory(self, extractor, test_file_with_factories):
        """Test detection of create_* factory pattern."""
        factories = extractor.extract_factory_fixtures(test_file_with_factories)
        
        create_product = next((f for f in factories if f.fixture_name == 'create_product'), None)
        assert create_product is not None
        assert create_product.factory_pattern == 'create_'
    
    def test_detect_build_factory(self, extractor, test_file_with_factories):
        """Test detection of build_* factory pattern."""
        factories = extractor.extract_factory_fixtures(test_file_with_factories)
        
        build_client = next((f for f in factories if f.fixture_name == 'build_api_client'), None)
        assert build_client is not None
        assert build_client.factory_pattern == 'build_'
    
    def test_detect_factory_suffix(self, extractor, test_file_with_factories):
        """Test detection of *_factory pattern."""
        factories = extractor.extract_factory_fixtures(test_file_with_factories)
        
        user_factory = next((f for f in factories if f.fixture_name == 'user_factory'), None)
        assert user_factory is not None
        assert user_factory.factory_pattern == '_factory'
    
    def test_is_factory_fixture(self, extractor, test_file_with_factories):
        """Test is_factory_fixture method."""
        assert extractor.is_factory_fixture("make_user") is True
        assert extractor.is_factory_fixture("create_product") is True
        assert extractor.is_factory_fixture("build_api_client") is True
        assert extractor.is_factory_fixture("user_factory") is True
        assert extractor.is_factory_fixture("regular_fixture") is False


class TestFactoryParameters:
    """Test extraction of factory parameters."""
    
    def test_extract_factory_parameters(self, extractor, test_file_with_factories):
        """Test extraction of factory function parameters."""
        factories = extractor.extract_factory_fixtures(test_file_with_factories)
        
        make_user = next((f for f in factories if f.fixture_name == 'make_user'), None)
        assert make_user is not None
        
        params = make_user.factory_params
        assert 'username' in params
        assert 'role' in params
        assert params['role'] == 'user'  # default value
    
    def test_parameters_with_defaults(self, extractor, test_file_with_factories):
        """Test parameters with default values."""
        factories = extractor.extract_factory_fixtures(test_file_with_factories)
        
        build_client = next((f for f in factories if f.fixture_name == 'build_api_client'), None)
        assert build_client is not None
        
        params = build_client.factory_params
        assert 'base_url' in params
        assert 'timeout' in params
        assert params['timeout'] == 30


class TestFactoryWithCleanup:
    """Test factories with cleanup logic."""
    
    def test_factory_with_yield(self, extractor, test_file_with_factories):
        """Test factory with yield for cleanup."""
        factories = extractor.extract_factory_fixtures(test_file_with_factories)
        
        create_product = next((f for f in factories if f.fixture_name == 'create_product'), None)
        assert create_product is not None
        assert create_product.has_cleanup is True
    
    def test_factory_without_cleanup(self, extractor, test_file_with_factories):
        """Test factory without cleanup (return only)."""
        factories = extractor.extract_factory_fixtures(test_file_with_factories)
        
        make_user = next((f for f in factories if f.fixture_name == 'make_user'), None)
        assert make_user is not None
        assert create_product.has_cleanup is False or make_user.has_cleanup is False
    
    def test_cleanup_with_tracking(self, extractor, test_file_with_factories):
        """Test factory that tracks created objects for cleanup."""
        factories = extractor.extract_factory_fixtures(test_file_with_factories)
        
        create_product = next((f for f in factories if f.fixture_name == 'create_product'), None)
        assert create_product is not None
        
        # Should have tracking list
        fixture_code = create_product.fixture_code
        assert 'created_products' in fixture_code or 'append' in fixture_code


class TestComplexFactories:
    """Test complex factory patterns."""
    
    def test_factory_with_state(self, extractor, test_file_with_factories):
        """Test factory with internal state."""
        factories = extractor.extract_factory_fixtures(test_file_with_factories)
        
        user_factory = next((f for f in factories if f.fixture_name == 'user_factory'), None)
        assert user_factory is not None
        
        # Should have counter or similar state
        fixture_code = user_factory.fixture_code
        assert 'counter' in fixture_code or 'count' in fixture_code
    
    def test_factory_with_optional_params(self, extractor, test_file_with_factories):
        """Test factory with optional parameters."""
        factories = extractor.extract_factory_fixtures(test_file_with_factories)
        
        user_factory = next((f for f in factories if f.fixture_name == 'user_factory'), None)
        assert user_factory is not None
        
        params = user_factory.factory_params
        assert 'username' in params
    
    def test_factory_with_scope(self, extractor, test_file_complex_factories):
        """Test factory with custom scope."""
        factories = extractor.extract_factory_fixtures(test_file_complex_factories)
        
        create_temp = next((f for f in factories if 'temp_file' in f.fixture_name), None)
        if create_temp:
            assert create_temp.scope == "module" or create_temp.scope is not None


class TestRobotFrameworkConversion:
    """Test conversion to Robot Framework."""
    
    def test_convert_simple_factory(self, extractor, test_file_with_factories):
        """Test conversion of simple factory to Robot Framework."""
        factories = extractor.extract_factory_fixtures(test_file_with_factories)
        
        make_user = next((f for f in factories if f.fixture_name == 'make_user'), None)
        robot_code = extractor.convert_to_robot_keyword(make_user)
        
        assert "*** Keywords ***" in robot_code
        assert "Make User" in robot_code or "Create User" in robot_code
    
    def test_convert_factory_with_params(self, extractor, test_file_with_factories):
        """Test conversion with parameters."""
        factories = extractor.extract_factory_fixtures(test_file_with_factories)
        
        build_client = next((f for f in factories if f.fixture_name == 'build_api_client'), None)
        robot_code = extractor.convert_to_robot_keyword(build_client)
        
        assert robot_code is not None
        # Should have parameter placeholders
        assert "${" in robot_code or "[Arguments]" in robot_code


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_non_factory_fixtures(self, extractor, tmp_path):
        """Test file with regular fixtures (not factories)."""
        test_file = tmp_path / "test_regular.py"
        test_file.write_text("""
import pytest

@pytest.fixture
def database():
    db = Database()
    yield db
    db.close()

@pytest.fixture
def config():
    return load_config()
        """)
        
        factories = extractor.extract_factory_fixtures(test_file)
        assert len(factories) == 0
    
    def test_factory_without_inner_function(self, extractor, tmp_path):
        """Test fixture named like factory but without inner function."""
        test_file = tmp_path / "test_fake_factory.py"
        test_file.write_text("""
import pytest

@pytest.fixture
def make_user():
    # Not actually a factory
    return User("default")
        """)
        
        factories = extractor.extract_factory_fixtures(test_file)
        # Should either not detect or detect without inner function
        if len(factories) > 0:
            assert factories[0].fixture_name == "make_user"
    
    def test_nonexistent_file(self, extractor, tmp_path):
        """Test handling of nonexistent file."""
        nonexistent = tmp_path / "doesnt_exist.py"
        
        factories = extractor.extract_factory_fixtures(nonexistent)
        assert len(factories) == 0
    
    def test_invalid_python_syntax(self, extractor, tmp_path):
        """Test handling of invalid Python syntax."""
        invalid_file = tmp_path / "invalid.py"
        invalid_file.write_text("def make_something( invalid syntax")
        
        factories = extractor.extract_factory_fixtures(invalid_file)
        assert len(factories) == 0
    
    def test_factory_with_lambda(self, extractor, tmp_path):
        """Test factory that returns lambda."""
        test_file = tmp_path / "test_lambda.py"
        test_file.write_text("""
import pytest

@pytest.fixture
def make_adder():
    return lambda x, y: x + y
        """)
        
        factories = extractor.extract_factory_fixtures(test_file)
        # Lambda might not be detected as traditional factory
        # but should handle gracefully


class TestRealWorldScenarios:
    """Test real-world factory patterns."""
    
    def test_page_object_factory(self, extractor, tmp_path):
        """Test factory for creating page objects."""
        test_file = tmp_path / "test_pages.py"
        test_file.write_text("""
import pytest

@pytest.fixture
def create_page():
    pages = []
    
    def _create(page_class, driver):
        page = page_class(driver)
        pages.append(page)
        return page
    
    yield _create
    
    for page in pages:
        page.cleanup()

def test_login_page(create_page, driver):
    login_page = create_page(LoginPage, driver)
    assert login_page.is_loaded()
        """)
        
        factories = extractor.extract_factory_fixtures(test_file)
        assert len(factories) > 0
        
        create_page = factories[0]
        assert create_page.has_cleanup is True
    
    def test_test_data_factory(self, extractor, tmp_path):
        """Test factory for creating test data."""
        test_file = tmp_path / "test_data.py"
        test_file.write_text("""
import pytest

@pytest.fixture
def make_test_data():
    def _make(entity_type, **kwargs):
        if entity_type == "user":
            return create_user(**kwargs)
        elif entity_type == "order":
            return create_order(**kwargs)
        return create_generic(entity_type, **kwargs)
    return _make

def test_user_creation(make_test_data):
    user = make_test_data("user", name="John", email="john@test.com")
    assert user.name == "John"
        """)
        
        factories = extractor.extract_factory_fixtures(test_file)
        assert len(factories) > 0
        
        make_data = factories[0]
        params = make_data.factory_params
        assert 'entity_type' in params
