# MCP Integration Examples - Practical Use Cases

Copyright (c) 2025 Vikas Verma  
Licensed under the Apache License, Version 2.0

**Comprehensive examples demonstrating MCP client usage for test transformations, analysis, and generation.**

---

## Table of Contents

1. [Basic Setup](#basic-setup)
2. [Example 1: JUnit to Pytest Transformation](#example-1-junit-to-pytest-transformation)
3. [Example 2: Flaky Test Analysis](#example-2-flaky-test-analysis)
4. [Example 3: Test Generation from Spec](#example-3-test-generation-from-spec)
5. [Example 4: Streaming Transformations](#example-4-streaming-transformations)
6. [Example 5: Error Handling & Fallbacks](#example-5-error-handling--fallbacks)
7. [Example 6: Cost Optimization](#example-6-cost-optimization)
8. [Example 7: Batch Processing](#example-7-batch-processing)

---

## Basic Setup

### Initialize MCP Client

```python
from core.ai.mcp_client import MCPClient

# Initialize with OpenAI
client = MCPClient(
    provider="openai",
    model="gpt-4-turbo-preview",
    api_key="sk-..."
)

# Or with Anthropic
client = MCPClient(
    provider="anthropic",
    model="claude-3-5-sonnet-20241022",
    api_key="sk-ant-..."
)

# Or with Ollama (local)
client = MCPClient(
    provider="ollama",
    model="llama3.2:3b",
    base_url="http://localhost:11434"
)
```

---

## Example 1: JUnit to Pytest Transformation

**Use Case:** Convert legacy JUnit test to modern Pytest format with fixtures.

### Input Code

```java
// LoginTest.java
import org.junit.Test;
import org.junit.Before;
import org.junit.After;
import static org.junit.Assert.*;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;

public class LoginTest {
    private WebDriver driver;
    
    @Before
    public void setUp() {
        System.setProperty("webdriver.chrome.driver", "/path/to/chromedriver");
        driver = new ChromeDriver();
        driver.get("https://example.com/login");
    }
    
    @Test
    public void testValidLogin() {
        driver.findElement(By.id("username")).sendKeys("testuser");
        driver.findElement(By.id("password")).sendKeys("password123");
        driver.findElement(By.id("loginBtn")).click();
        
        assertEquals("Dashboard", driver.getTitle());
    }
    
    @After
    public void tearDown() {
        if (driver != null) {
            driver.quit();
        }
    }
}
```

### Transformation Code

```python
from core.ai.mcp_client import MCPClient

# Initialize client
client = MCPClient(provider="openai", model="gpt-4-turbo-preview")

# Read source code
with open("LoginTest.java", "r") as f:
    java_code = f.read()

# Transform with context
prompt = f"""
Transform this JUnit test to Pytest with the following requirements:
1. Use pytest fixtures for setup/teardown
2. Convert to modern Playwright instead of Selenium
3. Use page object model pattern
4. Add type hints
5. Include proper error handling

Source code:
{java_code}
"""

response = client.send_request(
    prompt=prompt,
    context={
        "source_framework": "selenium-java",
        "target_framework": "playwright-python",
        "transformation_type": "full_migration"
    }
)

# Save transformed code
with open("test_login.py", "w") as f:
    f.write(response["content"])

print(f"Transformation complete!")
print(f"Tokens used: {response['usage']['total_tokens']}")
print(f"Cost: ${response['usage']['cost']:.4f}")
```

### Output Code

```python
# test_login.py
import pytest
from playwright.sync_api import Page, expect
from pages.login_page import LoginPage

@pytest.fixture
def login_page(page: Page) -> LoginPage:
    """Fixture to initialize login page."""
    page.goto("https://example.com/login")
    return LoginPage(page)

def test_valid_login(login_page: LoginPage) -> None:
    """Test successful login with valid credentials."""
    login_page.login(username="testuser", password="password123")
    
    # Verify navigation to dashboard
    expect(login_page.page).to_have_title("Dashboard")
```

### Result

```
✅ Transformation complete!
📊 Tokens used: 1,245
💰 Cost: $0.0249
⏱️  Time: 3.2 seconds
```

---

## Example 2: Flaky Test Analysis

**Use Case:** Analyze test failure history and identify flakiness patterns.

### Analysis Code

```python
from core.ai.mcp_client import MCPClient
import json

# Initialize client
client = MCPClient(provider="anthropic", model="claude-3-5-sonnet-20241022")

# Gather test failure history
test_history = {
    "test_name": "test_checkout_flow",
    "total_runs": 50,
    "failures": 7,
    "failure_rate": 0.14,
    "failure_logs": [
        "ElementClickInterceptedException: Element is not clickable at point (100, 200)",
        "TimeoutException: Timeout waiting for element #payment-btn",
        "StaleElementReferenceException: Element is no longer attached to DOM",
        "ElementClickInterceptedException: Element is not clickable at point (100, 200)",
        "TimeoutException: Timeout waiting for element #payment-btn",
        "ElementClickInterceptedException: Element is not clickable at point (100, 200)",
        "NoSuchElementException: Unable to locate element #confirmation"
    ],
    "test_code": """
def test_checkout_flow(page):
    page.click("#add-to-cart")
    page.click("#checkout-btn")
    page.fill("#card-number", "4111111111111111")
    page.click("#payment-btn")
    page.wait_for_selector("#confirmation")
    assert "Order Confirmed" in page.inner_text("#confirmation")
"""
}

# Analyze flakiness
prompt = f"""
Analyze this flaky test and provide:
1. Root cause analysis of failures
2. Pattern identification (timing issues, race conditions, etc.)
3. Specific code fixes with explanations
4. Prevention strategies

Test data:
{json.dumps(test_history, indent=2)}
"""

response = client.send_request(
    prompt=prompt,
    context={
        "analysis_type": "flaky_detection",
        "framework": "playwright-python"
    }
)

# Parse recommendations
analysis = response["content"]
print("🔍 Flaky Test Analysis Report\n")
print(analysis)
print(f"\n📊 Analysis cost: ${response['usage']['cost']:.4f}")
```

### Analysis Output

```
🔍 Flaky Test Analysis Report

ROOT CAUSE ANALYSIS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Race Conditions (71% of failures)
   - ElementClickInterceptedException: Overlay/modal blocking clicks
   - Likely cause: Animations or loading spinners still present

2. Timing Issues (29% of failures)
   - TimeoutException: Element appears but not within default timeout
   - StaleElementReferenceException: DOM updates during test execution

PATTERN IDENTIFICATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Failures spike during peak hours (14:00-16:00 UTC)
- 100% failures involve payment button interaction
- All ElementClickIntercepted errors occur at same coordinates (100, 200)
- Suggests persistent overlay element

RECOMMENDED FIXES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fix 1: Wait for overlay dismissal
```python
def test_checkout_flow(page):
    page.click("#add-to-cart")
    
    # Wait for any loading overlays to disappear
    page.wait_for_selector(".loading-overlay", state="hidden", timeout=10000)
    
    page.click("#checkout-btn")
    page.fill("#card-number", "4111111111111111")
    
    # Ensure payment button is actionable (visible, stable, enabled)
    page.wait_for_selector("#payment-btn", state="visible")
    page.wait_for_function("document.querySelector('#payment-btn').disabled === false")
    
    page.click("#payment-btn")
    
    # Increase timeout for confirmation (network-dependent)
    page.wait_for_selector("#confirmation", timeout=15000)
    assert "Order Confirmed" in page.inner_text("#confirmation")
```

Fix 2: Use force_click with retry logic
```python
def test_checkout_flow(page):
    page.click("#add-to-cart")
    page.click("#checkout-btn")
    page.fill("#card-number", "4111111111111111")
    
    # Force click to bypass intercepting elements
    page.click("#payment-btn", force=True)
    
    page.wait_for_selector("#confirmation", timeout=15000)
    assert "Order Confirmed" in page.inner_text("#confirmation")
```

PREVENTION STRATEGIES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Disable animations in test environment:
   ```python
   page.add_init_script("document.documentElement.style.transition = 'none'")
   ```

2. Use auto-waiting actions:
   ```python
   # Playwright waits automatically for actionability
   page.click("#payment-btn")  # Waits for visible, stable, enabled
   ```

3. Add explicit waits before critical actions:
   ```python
   page.wait_for_load_state("networkidle")
   ```

4. Implement retry logic for known flaky operations:
   ```python
   from playwright.sync_api import TimeoutError as PlaywrightTimeout
   
   for attempt in range(3):
       try:
           page.click("#payment-btn")
           break
       except PlaywrightTimeout:
           if attempt == 2:
               raise
           page.wait_for_timeout(1000)
   ```

📊 Analysis cost: $0.0189
⏱️  Analysis time: 2.8 seconds
```

---

## Example 3: Test Generation from Spec

**Use Case:** Generate complete test suite from user story/specification.

### Specification

```markdown
# User Story: Shopping Cart

As a customer, I want to add items to my cart, update quantities, and proceed to checkout.

**Acceptance Criteria:**
1. User can add items to cart from product page
2. Cart icon shows item count badge
3. User can view cart and see all items
4. User can update item quantities (min: 1, max: 10)
5. User can remove items from cart
6. Cart total updates automatically
7. User can proceed to checkout with valid items
```

### Generation Code

```python
from core.ai.mcp_client import MCPClient

client = MCPClient(provider="openai", model="gpt-4-turbo-preview")

# Read specification
with open("user_story.md", "r") as f:
    spec = f.read()

# Generate tests
prompt = f"""
Generate a complete Playwright test suite for this user story:

{spec}

Requirements:
1. Use pytest framework
2. Implement page object model
3. Include fixtures for test data
4. Add parametrized tests where appropriate
5. Include positive and negative test cases
6. Add proper assertions and error messages

Provide:
- test_shopping_cart.py (test file)
- pages/cart_page.py (page object)
- conftest.py (fixtures)
"""

response = client.send_request(
    prompt=prompt,
    context={
        "generation_type": "test_suite",
        "framework": "playwright-python",
        "pattern": "page_object_model"
    }
)

# Extract generated files
files = parse_generated_files(response["content"])

for filename, content in files.items():
    with open(filename, "w") as f:
        f.write(content)
    print(f"✅ Generated: {filename}")

print(f"\n💰 Total cost: ${response['usage']['cost']:.4f}")
```

### Generated Files

**test_shopping_cart.py:**
```python
import pytest
from playwright.sync_api import Page, expect
from pages.cart_page import CartPage

@pytest.mark.parametrize("quantity", [1, 5, 10])
def test_add_item_with_quantity(page: Page, cart_page: CartPage, quantity: int):
    """Test adding items with various quantities."""
    cart_page.add_item("Product A", quantity)
    
    expect(cart_page.cart_badge).to_have_text(str(quantity))
    expect(cart_page.cart_total).to_be_visible()

def test_update_item_quantity(page: Page, cart_page: CartPage):
    """Test updating item quantity in cart."""
    cart_page.add_item("Product A", 1)
    cart_page.open_cart()
    cart_page.update_quantity("Product A", 3)
    
    expect(cart_page.get_item_quantity("Product A")).to_have_value("3")

def test_remove_item_from_cart(page: Page, cart_page: CartPage):
    """Test removing item from cart."""
    cart_page.add_item("Product A", 2)
    cart_page.open_cart()
    cart_page.remove_item("Product A")
    
    expect(cart_page.empty_cart_message).to_be_visible()
    expect(cart_page.cart_badge).to_have_text("0")

def test_quantity_validation(page: Page, cart_page: CartPage):
    """Test quantity validation (min: 1, max: 10)."""
    cart_page.add_item("Product A", 1)
    cart_page.open_cart()
    
    # Attempt to set quantity below minimum
    cart_page.update_quantity("Product A", 0)
    expect(cart_page.error_message).to_contain_text("Minimum quantity is 1")
    
    # Attempt to set quantity above maximum
    cart_page.update_quantity("Product A", 11)
    expect(cart_page.error_message).to_contain_text("Maximum quantity is 10")

def test_cart_total_updates(page: Page, cart_page: CartPage):
    """Test that cart total updates when quantities change."""
    cart_page.add_item("Product A", 2)  # $10 each
    initial_total = cart_page.get_cart_total()
    
    cart_page.open_cart()
    cart_page.update_quantity("Product A", 5)
    
    new_total = cart_page.get_cart_total()
    assert new_total == initial_total * 2.5

def test_proceed_to_checkout(page: Page, cart_page: CartPage):
    """Test proceeding to checkout with valid items."""
    cart_page.add_item("Product A", 2)
    cart_page.open_cart()
    cart_page.click_checkout()
    
    expect(page).to_have_url("https://example.com/checkout")
```

**pages/cart_page.py:**
```python
from playwright.sync_api import Page, Locator

class CartPage:
    def __init__(self, page: Page):
        self.page = page
        self.cart_badge = page.locator(".cart-badge")
        self.cart_total = page.locator(".cart-total")
        self.empty_cart_message = page.locator(".empty-cart")
        self.error_message = page.locator(".error-message")
        
    def add_item(self, product_name: str, quantity: int) -> None:
        """Add item to cart from product page."""
        self.page.goto(f"https://example.com/products/{product_name.lower().replace(' ', '-')}")
        self.page.fill("#quantity", str(quantity))
        self.page.click("#add-to-cart")
        self.page.wait_for_selector(".cart-badge", state="visible")
        
    def open_cart(self) -> None:
        """Open cart sidebar."""
        self.page.click(".cart-icon")
        self.page.wait_for_selector(".cart-sidebar", state="visible")
        
    def update_quantity(self, product_name: str, quantity: int) -> None:
        """Update item quantity in cart."""
        row = self.page.locator(f"[data-product='{product_name}']")
        row.locator(".quantity-input").fill(str(quantity))
        row.locator(".update-btn").click()
        
    def remove_item(self, product_name: str) -> None:
        """Remove item from cart."""
        row = self.page.locator(f"[data-product='{product_name}']")
        row.locator(".remove-btn").click()
        
    def get_item_quantity(self, product_name: str) -> Locator:
        """Get item quantity locator."""
        return self.page.locator(f"[data-product='{product_name}'] .quantity-input")
        
    def get_cart_total(self) -> float:
        """Get current cart total as float."""
        total_text = self.cart_total.inner_text()
        return float(total_text.replace("$", "").replace(",", ""))
        
    def click_checkout(self) -> None:
        """Click checkout button."""
        self.page.click("#checkout-btn")
```

**conftest.py:**
```python
import pytest
from playwright.sync_api import Page
from pages.cart_page import CartPage

@pytest.fixture
def cart_page(page: Page) -> CartPage:
    """Fixture to provide CartPage instance."""
    return CartPage(page)

@pytest.fixture(autouse=True)
def clear_cart(page: Page):
    """Clear cart before each test."""
    page.context.clear_cookies()
    page.context.clear_permissions()
    yield
```

### Result

```
✅ Generated: test_shopping_cart.py (87 lines)
✅ Generated: pages/cart_page.py (65 lines)
✅ Generated: conftest.py (18 lines)

💰 Total cost: $0.0412
⏱️  Generation time: 8.7 seconds
```

---

## Example 4: Streaming Transformations

**Use Case:** Transform large test file with real-time progress updates.

```python
from core.ai.mcp_client import MCPClient

client = MCPClient(provider="anthropic", model="claude-3-5-sonnet-20241022")

# Read large test file
with open("LargeTestSuite.java", "r") as f:
    java_code = f.read()  # 2000+ lines

prompt = f"Transform this large JUnit test suite to Pytest:\n\n{java_code}"

# Stream response for progress tracking
print("🔄 Starting transformation (this may take 30-60 seconds)...")
print("━" * 60)

full_response = ""
for chunk in client.stream_request(prompt=prompt):
    # chunk = {"delta": "partial content", "usage": {...}}
    full_response += chunk.get("delta", "")
    
    # Show progress
    print(".", end="", flush=True)

print("\n━" * 60)
print("✅ Transformation complete!")

# Save result
with open("test_large_suite.py", "w") as f:
    f.write(full_response)

# Get final usage stats
usage = client.get_usage_summary()
print(f"\n📊 Tokens: {usage['total_tokens']:,}")
print(f"💰 Cost: ${usage['cost']:.4f}")
```

### Output

```
🔄 Starting transformation (this may take 30-60 seconds)...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
....................................................
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Transformation complete!

📊 Tokens: 8,456
💰 Cost: $0.1691
⏱️  Time: 47.3 seconds
```

---

## Example 5: Error Handling & Fallbacks

**Use Case:** Implement robust error handling with fallback providers.

```python
from core.ai.mcp_client import MCPClient
from core.ai.exceptions import MCPError, RateLimitError, TokenLimitError

# Initialize primary client
primary_client = MCPClient(provider="openai", model="gpt-4-turbo-preview")

# Initialize fallback client (cheaper model)
fallback_client = MCPClient(provider="openai", model="gpt-3.5-turbo")

def transform_with_fallback(code: str) -> dict:
    """Transform code with automatic fallback on errors."""
    
    try:
        # Try primary model first
        return primary_client.send_request(
            prompt=f"Transform this code to Python:\n{code}",
            context={"transformation_type": "migration"}
        )
        
    except TokenLimitError as e:
        print(f"⚠️  Token limit exceeded: {e}")
        print("🔄 Splitting into smaller chunks...")
        
        # Split code and transform in chunks
        chunks = split_code(code, max_size=4000)
        results = []
        
        for i, chunk in enumerate(chunks):
            print(f"   Processing chunk {i+1}/{len(chunks)}...")
            result = primary_client.send_request(
                prompt=f"Transform this code chunk to Python:\n{chunk}"
            )
            results.append(result["content"])
        
        return {"content": "\n\n".join(results)}
        
    except RateLimitError as e:
        print(f"⚠️  Rate limit hit: {e}")
        print("🔄 Falling back to GPT-3.5-turbo...")
        
        # Use fallback model
        return fallback_client.send_request(
            prompt=f"Transform this code to Python:\n{code}"
        )
        
    except MCPError as e:
        print(f"❌ MCP Error: {e}")
        print("🔄 Retrying with exponential backoff...")
        
        # Retry with backoff
        for attempt in range(3):
            try:
                time.sleep(2 ** attempt)  # 2s, 4s, 8s
                return primary_client.send_request(
                    prompt=f"Transform this code to Python:\n{code}"
                )
            except MCPError:
                if attempt == 2:
                    raise

# Usage
with open("ComplexTest.java", "r") as f:
    code = f.read()

try:
    result = transform_with_fallback(code)
    print(f"✅ Transformation successful!")
    print(f"📄 Output length: {len(result['content'])} characters")
except Exception as e:
    print(f"❌ All attempts failed: {e}")
```

---

## Example 6: Cost Optimization

**Use Case:** Optimize AI costs by selecting appropriate models based on task complexity.

```python
from core.ai.mcp_client import MCPClient

class CostOptimizedTransformer:
    def __init__(self):
        # Small model for simple tasks
        self.small_client = MCPClient(provider="ollama", model="llama3.2:3b")
        
        # Medium model for moderate complexity
        self.medium_client = MCPClient(provider="openai", model="gpt-3.5-turbo")
        
        # Large model for complex tasks
        self.large_client = MCPClient(provider="openai", model="gpt-4-turbo-preview")
        
    def classify_complexity(self, code: str) -> str:
        """Classify code complexity."""
        lines = len(code.split("\n"))
        has_complex_patterns = any(p in code for p in ["@", "extends", "implements", "generic"])
        
        if lines < 50 and not has_complex_patterns:
            return "simple"
        elif lines < 200:
            return "moderate"
        else:
            return "complex"
    
    def transform(self, code: str) -> dict:
        """Transform with cost-optimized model selection."""
        complexity = self.classify_complexity(code)
        
        if complexity == "simple":
            print("💡 Using Ollama (local, free)")
            client = self.small_client
        elif complexity == "moderate":
            print("💡 Using GPT-3.5-turbo ($0.002/1K tokens)")
            client = self.medium_client
        else:
            print("💡 Using GPT-4-turbo ($0.01/1K tokens)")
            client = self.large_client
        
        result = client.send_request(
            prompt=f"Transform this code to Python:\n{code}"
        )
        
        print(f"💰 Cost: ${result.get('usage', {}).get('cost', 0):.4f}")
        return result

# Usage
transformer = CostOptimizedTransformer()

# Simple test (Ollama - free)
simple_test = """
@Test
public void testAdd() {
    assertEquals(5, calculator.add(2, 3));
}
"""

result = transformer.transform(simple_test)
# Output: 💡 Using Ollama (local, free)
#         💰 Cost: $0.0000

# Complex test (GPT-4)
complex_test = open("ComplexGenericTest.java").read()
result = transformer.transform(complex_test)
# Output: 💡 Using GPT-4-turbo ($0.01/1K tokens)
#         💰 Cost: $0.0347
```

---

## Example 7: Batch Processing

**Use Case:** Transform multiple test files efficiently.

```python
from core.ai.mcp_client import MCPClient
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import glob

client = MCPClient(provider="openai", model="gpt-4-turbo-preview")

def transform_file(filepath: str) -> dict:
    """Transform a single test file."""
    with open(filepath, "r") as f:
        code = f.read()
    
    try:
        result = client.send_request(
            prompt=f"Transform this Java test to Python pytest:\n{code}",
            context={"source_file": filepath}
        )
        
        # Save transformed file
        output_path = filepath.replace(".java", ".py").replace("src/test/java", "tests")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w") as f:
            f.write(result["content"])
        
        return {
            "status": "success",
            "input": filepath,
            "output": output_path,
            "tokens": result["usage"]["total_tokens"],
            "cost": result["usage"]["cost"]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "input": filepath,
            "error": str(e)
        }

# Find all Java test files
test_files = glob.glob("src/test/java/**/*Test.java", recursive=True)
print(f"📁 Found {len(test_files)} test files to transform\n")

# Transform in parallel (max 5 concurrent requests to respect rate limits)
results = []
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(transform_file, f): f for f in test_files}
    
    for future in as_completed(futures):
        result = future.result()
        results.append(result)
        
        if result["status"] == "success":
            print(f"✅ {result['input']} → {result['output']}")
            print(f"   💰 ${result['cost']:.4f} ({result['tokens']} tokens)")
        else:
            print(f"❌ {result['input']}: {result['error']}")

# Summary
successful = [r for r in results if r["status"] == "success"]
failed = [r for r in results if r["status"] == "error"]

total_cost = sum(r.get("cost", 0) for r in successful)
total_tokens = sum(r.get("tokens", 0) for r in successful)

print("\n" + "━" * 60)
print("📊 BATCH TRANSFORMATION SUMMARY")
print("━" * 60)
print(f"✅ Successful: {len(successful)}/{len(test_files)}")
print(f"❌ Failed: {len(failed)}/{len(test_files)}")
print(f"📈 Total tokens: {total_tokens:,}")
print(f"💰 Total cost: ${total_cost:.2f}")
print(f"⏱️  Avg time per file: {sum(r.get('time', 0) for r in successful) / len(successful):.1f}s")
```

### Output

```
📁 Found 23 test files to transform

✅ src/test/java/LoginTest.java → tests/test_login.py
   💰 $0.0234 (1,234 tokens)
✅ src/test/java/CheckoutTest.java → tests/test_checkout.py
   💰 $0.0312 (1,645 tokens)
✅ src/test/java/SearchTest.java → tests/test_search.py
   💰 $0.0189 (998 tokens)
...
❌ src/test/java/ComplexGenericTest.java: Token limit exceeded

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 BATCH TRANSFORMATION SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Successful: 22/23
❌ Failed: 1/23
📈 Total tokens: 31,456
💰 Total cost: $0.63
⏱️  Avg time per file: 4.2s
```

---

## Best Practices

### 1. Context Management

Always provide context for better results:

```python
response = client.send_request(
    prompt=prompt,
    context={
        "source_framework": "selenium-java",
        "target_framework": "playwright-python",
        "pattern": "page_object_model",
        "project_structure": "pytest_fixtures",
        "assertions": "playwright_expect"
    }
)
```

### 2. Token Usage Monitoring

Track token usage to avoid surprises:

```python
# Set budget alert
client.set_budget_alert(max_cost=5.00)

# Get usage summary
usage = client.get_usage_summary()
if usage["cost"] > 4.50:
    print("⚠️  Approaching budget limit!")
```

### 3. Error Recovery

Implement retry logic with exponential backoff:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def transform_with_retry(code):
    return client.send_request(prompt=f"Transform:\n{code}")
```

### 4. Result Validation

Always validate AI-generated code:

```python
result = client.send_request(prompt=transformation_prompt)

# Extract code from response
code = extract_code_block(result["content"])

# Validate syntax
try:
    compile(code, "<string>", "exec")
    print("✅ Valid Python syntax")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
```

---

## Additional Resources

- **[MCP Documentation](MCP_DOCUMENTATION.md)** - Complete MCP reference
- **[AI Setup Guide](../ai/AI_SETUP.md)** - Provider configuration
- **[Cost Management](MCP_DOCUMENTATION.md#cost-management)** - Token tracking
- **[API Reference](../api/API.md)** - Full API documentation

---

**Need Help?**

- 📧 Email: vikas.sdet@gmail.com
- 💬 Discussions: [GitHub Discussions](https://github.com/crossstack-ai/crossbridge/discussions)
- 🐛 Issues: [GitHub Issues](https://github.com/crossstack-ai/crossbridge/issues)

---

**Transform smarter, not harder.** 🚀
