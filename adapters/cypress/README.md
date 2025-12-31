# Cypress Adapter

Comprehensive adapter for Cypress E2E and component testing with full support for both JavaScript and TypeScript.

## Overview

This adapter enables CrossBridge to understand, analyze, and execute Cypress tests. It provides complete support for:

- **Languages**: JavaScript and TypeScript
- **Test Types**: E2E (End-to-End) and Component Testing
- **Configurations**: Modern (Cypress 10+) and Legacy (< 10)
- **Browsers**: Electron, Chrome, Firefox, Edge
- **Features**: Custom commands, fixtures, page objects

## Features

### Automatic Project Detection
- Detects modern config files (`cypress.config.js/ts`)
- Supports legacy `cypress.json` configuration
- Auto-discovers E2E and component test directories
- Identifies TypeScript usage
- Extracts Cypress version from `package.json`

### Test File Parsing
- Parses JavaScript and TypeScript test files
- Extracts `describe` blocks and test hierarchy
- Handles `it()` and `test()` syntax
- Supports nested describe blocks
- Removes comments to avoid false matches

### Test Execution
- Runs tests via `npx cypress run`
- Supports browser selection (electron, chrome, firefox, edge)
- Headless and headed modes
- Spec file filtering
- Tag-based filtering (with cypress-grep plugin)
- JSON report generation and parsing

### Metadata Extraction
- Extracts test metadata from spec files
- Identifies custom Cypress commands
- Discovers fixture files
- Detects page object patterns
- Provides detailed test structure information

## Installation Requirements

### Node.js and npm
```bash
# Check Node.js installation
node --version  # Should be 14.0.0 or higher

# Check npm installation
npm --version

# Install Node.js if needed
# Download from: https://nodejs.org/
```

### Cypress Installation
```bash
# Install Cypress as dev dependency
npm install --save-dev cypress

# Or with Yarn
yarn add --dev cypress

# Verify installation
npx cypress --version
```

### Project Setup

#### Modern Configuration (Cypress 10+)
```javascript
// cypress.config.js
const { defineConfig } = require('cypress')

module.exports = defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
    baseUrl: 'http://localhost:3000',
    specPattern: 'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
    supportFile: 'cypress/support/e2e.js',
  },
  component: {
    devServer: {
      framework: 'react',
      bundler: 'vite',
    },
    specPattern: 'src/**/*.cy.{js,jsx,ts,tsx}',
  },
})
```

#### TypeScript Configuration
```javascript
// cypress.config.ts
import { defineConfig } from 'cypress'

export default defineConfig({
  e2e: {
    setupNodeEvents(on, config) {},
    baseUrl: 'http://localhost:3000',
  },
})
```

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["es5", "dom"],
    "types": ["cypress", "node"]
  },
  "include": ["**/*.ts"]
}
```

#### Legacy Configuration (Cypress < 10)
```json
// cypress.json
{
  "baseUrl": "http://localhost:3000",
  "integrationFolder": "cypress/integration",
  "supportFile": "cypress/support/index.js",
  "fixturesFolder": "cypress/fixtures",
  "video": false
}
```

## Usage

### Basic Usage

```python
from adapters.cypress import CypressAdapter, CypressProjectDetector

# Auto-detect project configuration
detector = CypressProjectDetector("/path/to/cypress/project")
config = detector.detect()

if config:
    print(f"Detected {config.test_type.value} tests")
    print(f"TypeScript: {config.has_typescript}")
    print(f"Cypress version: {config.cypress_version}")
    
    # Create adapter
    adapter = CypressAdapter("/path/to/cypress/project")
    
    # Discover all tests
    tests = adapter.discover_tests()
    print(f"Found {len(tests)} tests")
    
    # Run all tests
    results = adapter.run_tests()
    
    for result in results:
        print(f"{result.name}: {result.status} ({result.duration_ms}ms)")
```

### Manual Configuration

```python
from adapters.cypress import (
    CypressAdapter,
    CypressConfig,
    CypressTestType
)
from pathlib import Path

# Manual configuration
config = CypressConfig(
    project_root=Path("/path/to/project"),
    config_file=Path("/path/to/cypress.config.js"),
    specs_dir=Path("/path/to/cypress/e2e"),
    test_type=CypressTestType.E2E,
    has_typescript=True,
    cypress_version="13.6.0"
)

adapter = CypressAdapter("/path/to/project", config=config)
```

### Running Tests with Options

```python
# Run with specific browser
results = adapter.run_tests(browser="chrome")

# Run specific spec file
results = adapter.run_tests(
    spec="cypress/e2e/login.cy.js"
)

# Run with tags (requires cypress-grep)
results = adapter.run_tests(
    tags=["@smoke", "@critical"]
)

# Run in headed mode
results = adapter.run_tests(
    headless=False,
    browser="electron"
)

# Run with custom timeout
results = adapter.run_tests(timeout=600)
```

### Metadata Extraction

```python
from adapters.cypress import CypressExtractor

extractor = CypressExtractor("/path/to/project")

# Extract all test metadata
tests = extractor.extract_tests()
for test in tests:
    print(f"Test: {test.test_name}")
    print(f"  File: {test.file_path}")
    print(f"  Framework: {test.framework}")
    print(f"  Tags: {test.tags}")

# Extract custom commands
commands = extractor.extract_custom_commands()
for cmd in commands:
    print(f"Command: cy.{cmd['name']}()")
    print(f"  Defined in: {cmd['file']}")

# Extract fixtures
fixtures = extractor.extract_fixtures()
for fixture in fixtures:
    print(f"Fixture: {fixture['name']}")
    print(f"  Path: {fixture['path']}")

# Extract page objects
page_objects = extractor.extract_page_objects()
for po in page_objects:
    print(f"Page Object: {po['class_name']}")
    print(f"  File: {po['file']}")
```

## Project Structure

### Typical Cypress Project Layout

```
my-cypress-project/
├── cypress.config.js             # Modern config
├── package.json                  # Dependencies
├── tsconfig.json                 # TypeScript config (if using TS)
├── cypress/
│   ├── e2e/                      # E2E tests (modern)
│   │   ├── login.cy.js
│   │   ├── search.cy.js
│   │   └── checkout.cy.js
│   ├── integration/              # Integration tests (legacy)
│   │   └── *.spec.js
│   ├── component/                # Component tests
│   │   └── Button.cy.jsx
│   ├── support/                  # Support files
│   │   ├── e2e.js                # E2E support
│   │   ├── commands.js           # Custom commands
│   │   └── component.js          # Component support
│   └── fixtures/                 # Test data
│       ├── users.json
│       └── products.json
└── node_modules/
    └── cypress/
```

### E2E Test Example (JavaScript)

```javascript
// cypress/e2e/login.cy.js
describe('User Authentication', () => {
  beforeEach(() => {
    cy.visit('/login')
  })

  it('should log in with valid credentials', () => {
    cy.get('#username').type('testuser')
    cy.get('#password').type('TestPass123!')
    cy.get('button[type="submit"]').click()
    
    cy.url().should('include', '/dashboard')
    cy.get('.welcome-message').should('be.visible')
    cy.get('.welcome-message').should('contain', 'Welcome back')
  })

  it('should show error with invalid credentials', () => {
    cy.get('#username').type('invalid')
    cy.get('#password').type('wrong')
    cy.get('button[type="submit"]').click()
    
    cy.get('.error-message').should('be.visible')
    cy.get('.error-message').should('contain', 'Invalid credentials')
  })

  it('should log out successfully', () => {
    cy.login('testuser', 'TestPass123!')  // Custom command
    cy.get('.logout-btn').click()
    
    cy.url().should('include', '/login')
  })
})
```

### E2E Test Example (TypeScript)

```typescript
// cypress/e2e/search.cy.ts
describe('Product Search', () => {
  interface SearchResult {
    name: string
    price: number
  }

  beforeEach(() => {
    cy.visit('/products')
  })

  it('should display search results', () => {
    cy.get('input[name="search"]').type('laptop')
    cy.get('button[type="submit"]').click()
    
    cy.get('.product-card').should('have.length.greaterThan', 0)
    cy.get('.product-card').first()
      .should('contain', 'laptop')
  })

  it('should filter by price range', () => {
    cy.get('#price-min').type('500')
    cy.get('#price-max').type('1000')
    cy.get('.filter-btn').click()
    
    cy.get('.product-card').each(($el) => {
      cy.wrap($el).find('.price')
        .invoke('text')
        .then((priceText) => {
          const price = parseFloat(priceText.replace('$', ''))
          expect(price).to.be.within(500, 1000)
        })
    })
  })
})
```

### Custom Commands

```javascript
// cypress/support/commands.js
Cypress.Commands.add('login', (username, password) => {
  cy.session([username, password], () => {
    cy.visit('/login')
    cy.get('#username').type(username)
    cy.get('#password').type(password)
    cy.get('button[type="submit"]').click()
    cy.url().should('include', '/dashboard')
  })
})

Cypress.Commands.add('selectProduct', (productName) => {
  cy.get('.product-card')
    .contains(productName)
    .parents('.product-card')
    .find('.add-to-cart')
    .click()
})

Cypress.Commands.add('checkoutWithItems', (items) => {
  items.forEach(item => {
    cy.selectProduct(item)
  })
  cy.get('.cart-icon').click()
  cy.get('.checkout-btn').click()
})
```

### Using Fixtures

```javascript
// cypress/fixtures/users.json
{
  "validUser": {
    "username": "testuser",
    "password": "TestPass123!",
    "email": "test@example.com"
  },
  "adminUser": {
    "username": "admin",
    "password": "AdminPass456!",
    "email": "admin@example.com"
  }
}

// cypress/e2e/registration.cy.js
describe('User Registration', () => {
  it('should register new user', () => {
    cy.fixture('users').then((users) => {
      cy.visit('/register')
      cy.get('#username').type(users.validUser.username)
      cy.get('#email').type(users.validUser.email)
      cy.get('#password').type(users.validUser.password)
      cy.get('button[type="submit"]').click()
      
      cy.url().should('include', '/success')
    })
  })
})
```

### Page Object Pattern

```javascript
// cypress/support/pages/LoginPage.js
class LoginPage {
  visit() {
    cy.visit('/login')
    return this
  }

  get usernameInput() {
    return cy.get('#username')
  }

  get passwordInput() {
    return cy.get('#password')
  }

  get submitButton() {
    return cy.get('button[type="submit"]')
  }

  get errorMessage() {
    return cy.get('.error-message')
  }

  login(username, password) {
    this.usernameInput.type(username)
    this.passwordInput.type(password)
    this.submitButton.click()
    return this
  }

  verifyErrorMessage(message) {
    this.errorMessage.should('be.visible')
    this.errorMessage.should('contain', message)
    return this
  }
}

export default LoginPage

// Usage in test
import LoginPage from '../support/pages/LoginPage'

describe('Login', () => {
  const loginPage = new LoginPage()

  it('should show error for invalid credentials', () => {
    loginPage.visit()
      .login('invalid', 'wrong')
      .verifyErrorMessage('Invalid credentials')
  })
})
```

## Configuration

### Test Discovery

The adapter automatically discovers tests by:
1. Finding `cypress.config.js/ts` or `cypress.json`
2. Locating `e2e/`, `integration/`, or `component/` directories
3. Scanning for files matching:
   - `*.cy.js`
   - `*.cy.ts`
   - `*.spec.js`
   - `*.spec.ts`

### Supported Browsers

- **electron** (default): Headless Chromium bundled with Cypress
- **chrome**: Google Chrome
- **firefox**: Mozilla Firefox
- **edge**: Microsoft Edge

### Tag-Based Filtering

Requires the `cypress-grep` plugin:

```bash
npm install --save-dev @cypress/grep
```

```javascript
// cypress.config.js
const { defineConfig } = require('cypress')

module.exports = defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      require('@cypress/grep/src/plugin')(config)
      return config
    },
  },
})

// cypress/support/e2e.js
import registerCypressGrep from '@cypress/grep'
registerCypressGrep()
```

Use tags in tests:

```javascript
describe('Login', { tags: '@smoke' }, () => {
  it('should login', { tags: '@critical' }, () => {})
})
```

## Test Execution

### Command Line
```bash
# Run all tests
npx cypress run

# Run specific spec
npx cypress run --spec "cypress/e2e/login.cy.js"

# Run with specific browser
npx cypress run --browser chrome

# Run in headed mode
npx cypress run --headed

# Run with grep filter
npx cypress run --env grep=@smoke
```

### Via Adapter
```python
# Run all E2E tests
results = adapter.run_tests()

# Run with options
results = adapter.run_tests(
    spec="cypress/e2e/login.cy.js",
    browser="chrome",
    headless=False,
    timeout=600
)

# Run component tests
component_adapter = CypressAdapter("/path/to/project")
results = component_adapter.run_tests()
```

## Troubleshooting

### Project Not Detected
**Problem**: `CypressProjectDetector` returns `None`

**Solutions**:
1. Verify `cypress.config.js/ts` or `cypress.json` exists
2. Check Cypress is in `package.json` dependencies
3. Ensure test files exist in `cypress/e2e/` or `cypress/integration/`
4. Use manual configuration as fallback

### Tests Not Found
**Problem**: `discover_tests()` returns empty list

**Solutions**:
1. Check test file naming (must end with `.cy.js/ts` or `.spec.js/ts`)
2. Verify tests are in correct directory
3. Ensure test files have `it()` or `test()` blocks
4. Check file permissions

### Execution Fails
**Problem**: `run_tests()` returns failed results

**Solutions**:
1. Verify Cypress is installed: `npx cypress --version`
2. Check Node.js version: `node --version` (≥ 14.0.0)
3. Run tests manually: `npx cypress run`
4. Check for missing dependencies: `npm install`
5. Review error messages in TestResult objects

### TypeScript Errors
**Problem**: TypeScript tests fail to run

**Solutions**:
1. Verify `tsconfig.json` exists with Cypress types
2. Install type definitions: `npm install --save-dev @types/node`
3. Check `cypress/tsconfig.json` if using separate config
4. Ensure TypeScript is installed: `npm install --save-dev typescript`

### Custom Commands Not Found
**Problem**: `cy.customCommand()` not recognized

**Solutions**:
1. Verify commands defined in `cypress/support/commands.js/ts`
2. Check support file is imported in `cypress/support/e2e.js/ts`
3. Add TypeScript declarations in `cypress/support/index.d.ts`
4. Restart Cypress after adding commands

## Integration with CrossBridge

### CLI Integration

```bash
# Auto-detect and run Cypress tests
crossbridge test cypress --path /path/to/project

# Run with specific browser
crossbridge test cypress --path /path/to/project --browser chrome

# Run with spec filter
crossbridge test cypress --path /path/to/project --spec "**/*login*"

# Extract metadata
crossbridge extract cypress --path /path/to/project
```

### Pipeline Integration

```python
from core.orchestration import TestOrchestrator

orchestrator = TestOrchestrator()

# Register Cypress adapter
orchestrator.register_adapter("cypress", CypressAdapter)

# Run in pipeline
results = orchestrator.execute_tests(
    adapter_type="cypress",
    project_path="/path/to/project",
    options={
        "browser": "chrome",
        "headless": True
    }
)
```

## API Reference

### Classes

#### `CypressAdapter`
Main adapter for Cypress test execution.

**Methods**:
- `discover_tests()` → List[str]
- `run_tests(tests=None, tags=None, spec=None, browser="electron", headless=True, timeout=300)` → List[TestResult]
- `get_config_info()` → Dict[str, str]

#### `CypressExtractor`
Extracts metadata from Cypress projects.

**Methods**:
- `extract_tests()` → List[TestMetadata]
- `extract_custom_commands()` → List[Dict]
- `extract_fixtures()` → List[Dict]
- `extract_page_objects()` → List[Dict]

#### `CypressProjectDetector`
Detects and analyzes Cypress project configuration.

**Methods**:
- `detect()` → Optional[CypressConfig]

#### `CypressTestParser`
Parses Cypress test files.

**Methods**:
- `parse_test_file(test_file: Path)` → List[Dict]
- `extract_custom_commands(support_file: Path)` → List[str]

### Data Classes

#### `CypressConfig`
```python
@dataclass
class CypressConfig:
    project_root: Path
    config_file: Path              # cypress.config.js/ts or cypress.json
    specs_dir: Path                # e2e/ or integration/
    test_type: CypressTestType     # E2E or COMPONENT
    support_file: Optional[Path]   # support/e2e.js
    fixtures_dir: Optional[Path]   # fixtures/
    has_typescript: bool
    cypress_version: Optional[str]
```

#### `CypressTestType`
```python
class CypressTestType(Enum):
    E2E = "e2e"
    COMPONENT = "component"
```

## Best Practices

### Test Organization
- Group related tests in describe blocks
- Use descriptive test names starting with "should"
- Keep tests independent and isolated
- Use beforeEach for common setup
- Clean up state in afterEach

### Custom Commands
- Create reusable commands for common workflows
- Add TypeScript type definitions
- Document command parameters
- Return chainable objects
- Keep commands focused and single-purpose

### Fixtures
- Use JSON fixtures for test data
- Keep fixtures small and focused
- Version control fixture files
- Use meaningful fixture names
- Validate fixture structure

### Page Objects
- Encapsulate page interactions
- Use getters for element selectors
- Chain methods for fluent API
- Return page objects from methods
- Keep selectors DRY

### Performance
- Use `cy.session()` for login state
- Minimize `cy.visit()` calls
- Leverage fixtures over API calls
- Run tests in parallel when possible
- Use `baseUrl` configuration

## Limitations

- Requires Node.js 14.0.0 or higher
- Cypress must be installed via npm/yarn
- Test name extraction based on regex patterns
- No support for dynamic test generation
- JSON reporter required for detailed results
- Tag filtering requires cypress-grep plugin

## Support

For issues, questions, or contributions:
- GitHub Issues: [CrossBridge Repository]
- Documentation: See `/docs/adapters/cypress.md`
- Examples: See `/examples/cypress-sample/`
- Cypress Docs: https://docs.cypress.io/

## License

This adapter is part of the CrossBridge project and follows the same license terms.
