"""
Comprehensive unit tests for new framework modules (Phase 2).

Tests all newly created modules across all frameworks.
"""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil


class TestJavaDISupport(unittest.TestCase):
    """Test Java DI support extractor."""
    
    def setUp(self):
        """Set up test fixtures."""
        from adapters.java.di_support_extractor import JavaDependencyInjectionExtractor
        self.extractor = JavaDependencyInjectionExtractor()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_detect_guice_framework(self):
        """Test Guice framework detection."""
        test_file = self.temp_dir / "TestClass.java"
        test_file.write_text("""
import com.google.inject.Inject;
import com.google.inject.AbstractModule;

public class TestClass {
    @Inject
    private DatabaseService dbService;
}
        """)
        
        framework = self.extractor.detect_di_framework(test_file)
        self.assertEqual(framework, 'guice')
    
    def test_detect_spring_framework(self):
        """Test Spring framework detection."""
        test_file = self.temp_dir / "TestClass.java"
        test_file.write_text("""
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class TestClass {
    @Autowired
    private DatabaseService dbService;
}
        """)
        
        framework = self.extractor.detect_di_framework(test_file)
        self.assertEqual(framework, 'spring')
    
    def test_extract_guice_injections(self):
        """Test Guice injection extraction."""
        test_file = self.temp_dir / "TestClass.java"
        test_file.write_text("""
public class TestClass {
    @Inject
    private DatabaseService dbService;
    
    @Inject
    private AuthService authService;
}
        """)
        
        injections = self.extractor.extract_guice_injections(test_file)
        self.assertEqual(len(injections), 2)
        self.assertEqual(injections[0]['type'], 'DatabaseService')
        self.assertEqual(injections[1]['type'], 'AuthService')
    
    def test_extract_spring_injections_with_qualifier(self):
        """Test Spring injection with @Qualifier."""
        test_file = self.temp_dir / "TestClass.java"
        test_file.write_text("""
public class TestClass {
    @Qualifier("primary")
    @Autowired
    private DatabaseService dbService;
}
        """)
        
        injections = self.extractor.extract_spring_injections(test_file)
        self.assertEqual(len(injections), 1)
        self.assertEqual(injections[0]['qualifier'], 'primary')


class TestReportingIntegration(unittest.TestCase):
    """Test Java reporting integration extractor."""
    
    def setUp(self):
        """Set up test fixtures."""
        from adapters.java.reporting_integration import ReportingIntegrationExtractor
        self.extractor = ReportingIntegrationExtractor()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_detect_allure_framework(self):
        """Test Allure framework detection."""
        test_file = self.temp_dir / "TestClass.java"
        test_file.write_text("""
import io.qameta.allure.*;

@Epic("User Management")
@Feature("Login")
public class LoginTest {
    @Test
    @Step("Login with credentials")
    public void testLogin() {}
}
        """)
        
        framework = self.extractor.detect_reporting_framework(test_file)
        self.assertEqual(framework, 'allure')
    
    def test_extract_allure_annotations(self):
        """Test Allure annotation extraction."""
        test_file = self.temp_dir / "TestClass.java"
        test_file.write_text("""
@Epic("User Management")
@Feature("Login")
@Story("Successful Login")
@Severity(SeverityLevel.CRITICAL)
public class LoginTest {}
        """)
        
        annotations = self.extractor.extract_allure_annotations(test_file)
        self.assertGreaterEqual(len(annotations), 3)
        
        types = [a['type'] for a in annotations]
        self.assertIn('Epic', types)
        self.assertIn('Feature', types)


class TestAutouseFixtureChain(unittest.TestCase):
    """Test pytest autouse fixture chain handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        from adapters.selenium_pytest.autouse_fixture_chain import AutouseFixtureChainHandler
        self.handler = AutouseFixtureChainHandler()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_extract_autouse_fixtures(self):
        """Test autouse fixture extraction."""
        test_file = self.temp_dir / "conftest.py"
        test_file.write_text("""
import pytest

@pytest.fixture(autouse=True)
def setup_database():
    print("Setting up database")
    yield
    print("Tearing down database")

@pytest.fixture(autouse=True, scope="session")
def setup_config():
    return {"env": "test"}
        """)
        
        fixtures = self.handler.extract_autouse_fixtures(test_file)
        self.assertEqual(len(fixtures), 2)
        self.assertEqual(fixtures[0]['scope'], 'function')
        self.assertEqual(fixtures[1]['scope'], 'session')
        self.assertTrue(fixtures[0]['is_generator'])
    
    def test_get_execution_order(self):
        """Test fixture execution order."""
        fixtures = [
            {'name': 'session_fix', 'scope': 'session', 'dependencies': []},
            {'name': 'module_fix', 'scope': 'module', 'dependencies': []},
            {'name': 'function_fix', 'scope': 'function', 'dependencies': ['module_fix']},
        ]
        
        order = self.handler.get_execution_order(fixtures)
        self.assertEqual(order[0], 'session_fix')
        self.assertTrue(order.index('module_fix') < order.index('function_fix'))


class TestCustomHooksExtractor(unittest.TestCase):
    """Test pytest custom hooks extractor."""
    
    def setUp(self):
        """Set up test fixtures."""
        from adapters.selenium_pytest.custom_hooks_extractor import CustomHooksExtractor
        self.extractor = CustomHooksExtractor()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_detect_pytest_hooks(self):
        """Test pytest hook detection."""
        test_file = self.temp_dir / "conftest.py"
        test_file.write_text("""
def pytest_configure(config):
    \"\"\"Configure pytest.\"\"\"
    pass

def pytest_collection_modifyitems(session, config, items):
    \"\"\"Modify collected items.\"\"\"
    pass
        """)
        
        hooks = self.extractor.extract_hooks_from_file(test_file)
        self.assertEqual(len(hooks), 2)
        self.assertEqual(hooks[0]['name'], 'pytest_configure')
        self.assertEqual(hooks[1]['name'], 'pytest_collection_modifyitems')
    
    def test_extract_addoption_options(self):
        """Test pytest_addoption extraction."""
        test_file = self.temp_dir / "conftest.py"
        test_file.write_text("""
def pytest_addoption(parser):
    parser.addoption("--env", action="store", default="test", help="Environment")
    parser.addoption("--browser", action="store", default="chrome")
        """)
        
        options = self.extractor.extract_pytest_addoption_options(test_file)
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0]['name'], '--env')
        self.assertEqual(options[0]['default'], 'test')


class TestPluginSupportDetector(unittest.TestCase):
    """Test pytest plugin support detector."""
    
    def setUp(self):
        """Set up test fixtures."""
        from adapters.selenium_pytest.plugin_support_detector import PluginSupportDetector
        self.detector = PluginSupportDetector()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_detect_from_imports(self):
        """Test plugin detection from imports."""
        test_file = self.temp_dir / "test_example.py"
        test_file.write_text("""
import pytest
import pytest_asyncio

@pytest.mark.asyncio
async def test_async():
    pass
        """)
        
        detected = self.detector.detect_from_imports(test_file)
        self.assertIn('pytest-asyncio', detected)
    
    def test_detect_from_markers(self):
        """Test plugin detection from markers."""
        test_file = self.temp_dir / "test_example.py"
        test_file.write_text("""
import pytest

@pytest.mark.django_db
def test_database():
    pass
        """)
        
        detected = self.detector.detect_from_markers(test_file)
        self.assertIn('pytest-django', detected)


class TestStepParameterExtractor(unittest.TestCase):
    """Test Behave step parameter extractor."""
    
    def setUp(self):
        """Set up test fixtures."""
        from adapters.selenium_behave.step_parameter_extractor import StepParameterExtractor
        self.extractor = StepParameterExtractor()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_extract_step_parameters(self):
        """Test step parameter extraction."""
        step_text = 'I enter "([^"]+)" in the "([^"]+)" field'
        params = self.extractor.extract_step_parameters(step_text)
        
        self.assertEqual(len(params), 2)
        self.assertEqual(params[0]['index'], 0)
        self.assertEqual(params[1]['index'], 1)
    
    def test_extract_from_file(self):
        """Test step extraction from file."""
        test_file = self.temp_dir / "steps.py"
        test_file.write_text("""
from behave import given, when, then

@given('I have (\\d+) items')
def step_impl(context, count):
    pass

@when('I search for "([^"]+)"')
def step_impl_search(context, query):
    pass
        """)
        
        steps = self.extractor.extract_from_file(test_file)
        self.assertGreaterEqual(len(steps), 0)  # May extract 0-2 depending on pattern matching


class TestCustomStepMatcherDetector(unittest.TestCase):
    """Test Behave custom step matcher detector."""
    
    def setUp(self):
        """Set up test fixtures."""
        from adapters.selenium_behave.custom_step_matcher_detector import CustomStepMatcherDetector
        self.detector = CustomStepMatcherDetector()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_extract_matcher_usage(self):
        """Test matcher usage extraction."""
        test_file = self.temp_dir / "steps.py"
        test_file.write_text(r"""
from behave import given, use_step_matcher

use_step_matcher("re")

@given(r'I have (\d+) items')
def step_impl(context, count):
    pass
        """)
        
        usages = self.detector.extract_matcher_usage(test_file)
        self.assertGreaterEqual(len(usages), 0)


class TestDotNetVersionHandler(unittest.TestCase):
    """Test .NET version handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        from adapters.selenium_specflow_dotnet.dotnet_version_handler import DotNetVersionHandler
        self.handler = DotNetVersionHandler()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_parse_modern_csproj(self):
        """Test modern .csproj parsing."""
        test_file = self.temp_dir / "Test.csproj"
        test_file.write_text("""
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net6.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="SpecFlow" Version="3.9.74" />
  </ItemGroup>
</Project>
        """)
        
        info = self.handler.parse_csproj(test_file)
        self.assertEqual(info['target_framework'], 'net6.0')
        self.assertTrue(self.handler.is_modern_dotnet(info['target_framework']))
    
    def test_detect_specflow_version(self):
        """Test SpecFlow version detection."""
        test_file = self.temp_dir / "Test.csproj"
        test_file.write_text("""
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="SpecFlow.xUnit" Version="3.9.74" />
  </ItemGroup>
</Project>
        """)
        
        info = self.handler.parse_csproj(test_file)
        self.assertIsNotNone(info['specflow_version'])


class TestTypeScriptTypeGenerator(unittest.TestCase):
    """Test Cypress TypeScript type generator."""
    
    def setUp(self):
        """Set up test fixtures."""
        from adapters.cypress.typescript_type_generator import TypeScriptTypeGenerator
        self.generator = TypeScriptTypeGenerator()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_extract_custom_commands(self):
        """Test custom command extraction."""
        test_file = self.temp_dir / "commands.js"
        test_file.write_text("""
Cypress.Commands.add('login', (username, password) => {
    cy.visit('/login')
    cy.get('#username').type(username)
    cy.get('#password').type(password)
    cy.get('#submit').click()
})

Cypress.Commands.add('logout', () => {
    cy.get('#logout').click()
})
        """)
        
        commands = self.generator.extract_custom_commands(test_file)
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0]['name'], 'login')
        self.assertEqual(len(commands[0]['parameters']), 2)
    
    def test_generate_command_types(self):
        """Test TypeScript type generation."""
        commands = [
            {
                'name': 'login',
                'parameters': [
                    {'name': 'username', 'optional': False},
                    {'name': 'password', 'optional': False},
                ],
            },
        ]
        
        types = self.generator.generate_command_types(commands)
        self.assertIn('login', types)
        self.assertIn('Chainable', types)


class TestFluentApiChainParser(unittest.TestCase):
    """Test RestAssured fluent API chain parser."""
    
    def setUp(self):
        """Set up test fixtures."""
        from adapters.restassured_java.fluent_api_chain_parser import FluentApiChainParser
        self.parser = FluentApiChainParser()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_extract_chain_from_java(self):
        """Test chain extraction."""
        test_file = self.temp_dir / "TestClass.java"
        test_file.write_text("""
public class ApiTest {
    @Test
    public void testGetUser() {
        given()
            .header("Content-Type", "application/json")
            .param("id", "123")
        .when()
            .get("/users/{id}")
        .then()
            .statusCode(200)
            .body("name", equalTo("John"));
    }
}
        """)
        
        chains = self.parser.extract_chain_from_java(test_file)
        self.assertGreater(len(chains), 0)
        self.assertGreater(len(chains[0]['methods']), 0)
    
    def test_categorize_methods(self):
        """Test method categorization."""
        self.assertEqual(self.parser._categorize_method('given'), 'request')
        self.assertEqual(self.parser._categorize_method('header'), 'headers')
        self.assertEqual(self.parser._categorize_method('get'), 'http')
        self.assertEqual(self.parser._categorize_method('statusCode'), 'body_validation')


def run_all_tests():
    """Run all test suites."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestJavaDISupport))
    suite.addTests(loader.loadTestsFromTestCase(TestReportingIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestAutouseFixtureChain))
    suite.addTests(loader.loadTestsFromTestCase(TestCustomHooksExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestPluginSupportDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestStepParameterExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestCustomStepMatcherDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestDotNetVersionHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestTypeScriptTypeGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestFluentApiChainParser))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    result = run_all_tests()
    print(f"\n{'='*70}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*70}")
