# CrossBridge 🌉
### by CrossStack AI

> **AI-Powered Test Automation Transformation Platform**  
> Modernize legacy test frameworks to modern, maintainable architectures

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Development Status](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/yourusername/crossbridge)
[![CrossStack AI](https://img.shields.io/badge/by-CrossStack%20AI-blue)](https://crossstack.ai)

---

## 🎯 The Problem

Testing teams worldwide face a critical challenge: **legacy test automation debt**. Organizations struggle with:

- **Brittle Selenium-based tests** that break with every UI change
- **Framework lock-in** making modernization expensive and risky
- **Manual migration efforts** taking months of engineering time
- **Lost tribal knowledge** when converting old test suites
- **Inconsistent quality** across migrated tests

**The cost?** Delayed releases, frustrated teams, and mounting technical debt that only grows over time.

---

## 💡 The Solution

**CrossBridge** is an open-source platform that works in **TWO MODES**:

### Mode 1: NO MIGRATION (Sidecar Observer) ⭐ NEW!

Work with your **existing frameworks WITHOUT any migration**:

```
┌─────────────────────┐         ┌──────────────────┐         
│   Your Tests        │         │   CrossBridge    │         
│   (NO CHANGES!)     │────────▶│   (Observer)     │────────▶ 📊 Insights
│                     │         │                  │         
│  • Selenium Java    │         │  • Auto-detect   │         • Coverage tracking
│  • Cypress          │         │  • Auto-register │         • Flaky detection
│  • pytest           │         │  • AI analysis   │         • Risk scores
│  • Robot Framework  │         │  • Zero impact   │         • Test optimization
└─────────────────────┘         └──────────────────┘         
```

**Supports 8+ frameworks as-is**: Selenium Java/BDD/RestAssured, .NET SpecFlow, Python pytest/Robot, Cypress
**Zero code changes**: Add a listener/plugin and go!

### Mode 2: FULL MIGRATION (Transformation)

Transform legacy tests to modern frameworks:

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   Legacy Tests      │         │   CrossBridge    │         │   Modern Tests      │
│                     │         │                  │         │                     │
│  • Selenium Java    │────────▶│  • Smart Parser  │────────▶│  • Robot Framework  │
│  • Cucumber BDD     │         │  • AI Enhancement│         │  • Playwright       │
│  • Pytest Selenium  │         │  • Pattern Match │         │  • Maintainable     │
│  • .NET SpecFlow    │         │  • Validation    │         │  • Modern Syntax    │
└─────────────────────┘         └──────────────────┘         └─────────────────────┘
```

**Key Capabilities:**
- ✅ **NO MIGRATION MODE**: Work with existing frameworks (Selenium, Cypress, pytest, Robot, etc.) as sidecar observer
- ✅ **Automated Migration**: Or convert entire test suites in hours when you're ready
- ✅ **Intelligent Parsing**: Extracts test intent, locators, and page objects
- ✅ **Continuous Intelligence**: Coverage tracking, flaky detection, AI optimization recommendations
- ✅ **AI-Enhanced** (Optional): Improves transformation quality, locator strategies, and provides self-healing
- ✅ **Framework-Agnostic**: Plugin architecture supports multiple sources/targets
- ✅ **Repository-Native**: Works directly with Git/Bitbucket/Azure DevOps
- ✅ **Impact Analysis**: Understand what tests break when code changes
- ✅ **Validation & Review**: Built-in quality checks and hybrid modes

---

## 🎪 Who Is This For?

### Primary Audience
- **QA Engineers** modernizing Selenium test suites
- **Test Automation Architects** planning framework migrations
- **DevOps Teams** consolidating CI/CD test pipelines
- **Engineering Managers** reducing technical debt

### You Should Use CrossBridge If You:
- ✅ Have 100+ Selenium tests that need modernization
- ✅ Want to adopt Robot Framework + Playwright
- ✅ Need to migrate before losing team knowledge
- ✅ Require audit trails and reproducible transformations
- ✅ Value open-source and extensibility

### This May Not Be For You If:
- ❌ You have < 50 tests (manual rewrite may be faster)
- ❌ Your tests are already modern (Playwright/Cypress native)
- ❌ You need production-grade stability today (see maturity below)
- ❌ Your framework isn't supported yet (contributions welcome!)

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/crossbridge.git
cd crossbridge

# Install dependencies
pip install -r requirements.txt
```

### Option 1: NO MIGRATION MODE (Recommended for new users!)

**Just observe your existing tests - no changes needed:**

```bash
# Configure database (one-time)
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_DB_HOST=10.55.12.99
export CROSSBRIDGE_APPLICATION_VERSION=v2.0.0

# Add listener to your framework:
```

**For Selenium Java:**
```xml
<!-- testng.xml -->
<listeners>
  <listener class-name="com.crossbridge.CrossBridgeListener"/>
</listeners>
```

**For Python pytest:**
```python
# conftest.py
pytest_plugins = ["crossbridge.pytest_plugin"]
```

**For Cypress:**
```javascript
// cypress.config.js
const crossbridge = require('crossbridge-cypress');
crossbridge.register(on, { enabled: true });
```

**That's it!** Run your tests normally - CrossBridge observes and provides intelligence.

📖 **See [NO_MIGRATION_FRAMEWORK_SUPPORT.md](docs/NO_MIGRATION_FRAMEWORK_SUPPORT.md) for all 8+ frameworks**

### Option 2: FULL MIGRATION MODE

**Transform tests to modern frameworks:**

```bash
# Start the interactive CLI
python -m cli.app

# Follow the prompts:
# 1. Select "Migration + Transformation"
# 2. Choose your source framework (e.g., Selenium Java BDD)
# 3. Connect your repository (Bitbucket/GitHub/Azure DevOps)
# 4. Configure paths (step definitions, page objects, features)
# 5. Select transformation mode (Enhanced recommended)
# 6. Run migration ✨
```

**Output:** Transformed Robot Framework tests in a new branch, ready for review.

---

## 📋 Supported Frameworks

### NO MIGRATION MODE (Sidecar Observer) ⭐
| Framework | Status | Hook Type | Setup Time |
|-----------|--------|-----------|------------|
| **Selenium Java** | ✅ Ready | TestNG/JUnit Listener | 5 min |
| **Selenium Java BDD** | ✅ Ready | TestNG Listener | 5 min |
| **Selenium Java + RestAssured** | ✅ Ready | TestNG Listener | 5 min |
| **Selenium .NET SpecFlow** | ✅ Ready | SpecFlow Plugin | 5 min |
| **Selenium Python pytest** | ✅ Ready | pytest Plugin | 5 min |
| **Selenium Python Robot** | ✅ Ready | Robot Listener | 5 min |
| **Requests Python Robot (API)** | ✅ Ready | Robot Listener | 5 min |
| **Cypress** | ✅ Ready | Cypress Plugin | 5 min |

**All work with ZERO test code changes!**

### MIGRATION MODE (Full Transformation)

**Source Frameworks (Input):**
| Framework | Status | Notes |
|-----------|--------|-------|
| Selenium Java + Cucumber | ✅ **Stable** | Primary use case, well-tested |
| Selenium Java (no BDD) | ✅ Supported | Basic transformation |
| Pytest + Selenium | 🟡 Beta | In active development |
| .NET SpecFlow | 🟡 Beta | Basic support |
| Robot Framework (existing) | ✅ Supported | For transformation/enhancement |
| Cypress | 🔵 Planned | Roadmap Q2 2026 |
| Playwright (Java/Python) | 🔵 Planned | Roadmap Q3 2026 |

**Target Frameworks (Output):**
| Framework | Status | Notes |
|-----------|--------|-------|
| Selenium Java + Cucumber | ✅ **Stable** | Primary use case, well-tested |
| Selenium Java (no BDD) | ✅ Supported | Basic transformation |
| Pytest + Selenium | 🟡 Beta | In active development |
| .NET SpecFlow | 🟡 Beta | Basic support |
| Robot Framework (existing) | ✅ Supported | For transformation/enhancement |
| Cypress | 🔵 Planned | Roadmap Q2 2026 |
| Playwright (Java/Python) | 🔵 Planned | Roadmap Q3 2026 |

### Target Frameworks (Output)
| Framework | Status | Quality |
|-----------|--------|---------|
| Robot Framework + Playwright | ✅ **Primary** | Production-ready output |
| pytest-bdd | 🟡 Experimental | Early stage |

---

## 🎛️ Core Features

### 1. Migration Modes

```
Manual Mode         → Creates placeholders with TODOs (fast, requires review)
Enhanced Mode       → Smart extraction with pattern matching (recommended)
Hybrid Mode         → AI-enhanced with human review markers (best quality)
```

**🤖 AI-Powered Enhancement** (Optional):
- Enable OpenAI/Anthropic integration for intelligent transformation
- Supports **step definitions**, **page objects**, and **locators**
- Better Cucumber pattern recognition and Playwright action generation
- **Self-healing locator strategies** - prioritizes data-testid > id > CSS > XPath
- **Locator extraction tracking** - counts and reports all locators extracted from page objects
- **AI metrics & cost analysis** - detailed token usage, cost per file, and transformation statistics
- Natural language documentation and best practice implementations
- Automatic fallback to pattern-based if AI unavailable
- See [`docs/AI_TRANSFORMATION_USAGE.md`](docs/AI_TRANSFORMATION_USAGE.md) for setup

```python
# Enable AI transformation for all file types
request.use_ai = True
request.ai_config = {
    'provider': 'openai',  # or 'anthropic'
    'api_key': 'sk-...',
    'model': 'gpt-3.5-turbo'  # or 'gpt-4', 'claude-3-sonnet'
}

# AI will transform:
# • Step Definitions: Cucumber → Robot Framework with smart pattern matching
# • Page Objects: Selenium → Playwright with locator extraction (tracked!)
# • Locators: Quality analysis + self-healing recommendations
# • Generates comprehensive AI summary with cost breakdown and metrics
```

**📊 AI Transformation Summary** (displayed after migration):
```
🤖 AI Transformation Statistics:
  ✓ Total Files Transformed: 50
  ✓ Step Definitions: 35
  ✓ Page Objects: 15
  ✓ Standalone Locator Files: 0
  ✓ Locators Extracted from Page Objects: 243  ← NEW!

🛡️  Self-Healing Locator Strategy Applied:  ← NEW!
  ✓ Priority: data-testid > id > CSS > XPath
  ✓ Text-based matching for visible elements
  ✓ Avoided brittle positional XPath selectors
  ✓ Modern Playwright locator best practices

💰 Token Usage & Cost:
  • Total Tokens: 125,430
  • Total Cost: $0.1254
  • Avg Tokens/File: 2,508
  • Avg Cost/File: $0.0025
```

### 2. Transformation Tiers

```
Tier 1: Quick Refresh     → Syntax updates only
Tier 2: Content Validation → Parse + validate structure  
Tier 3: Deep Regeneration → Full AI-powered rewrite
```

### 3. Repository Integration

- **Direct Git Operations**: Read from and write to repositories
- **Branch Management**: Automatic PR/MR creation
- **Batch Commits**: Configurable commit sizes for large migrations
- **Credential Caching**: Secure storage of API tokens

### 4. Impact Analysis

```bash
# Discover which tests use specific page objects
crossbridge impact --page-object LoginPage

# Find tests affected by code changes
crossbridge analyze-impact --changed-files src/pages/HomePage.java
```

### 5. Post-Migration Testing

- **Validation Reports**: Syntax checks, missing imports, undefined keywords
- **Execution Readiness**: Verify tests can run in Robot Framework
- **Documentation**: Auto-generated setup guides per repository

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI / Interactive Menu                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┴──────────────┐
        │   Core Orchestrator         │
        │   - Migration Pipeline      │
        │   - Transformation Engine   │
        │   - Validation Framework    │
        └─────────────┬───────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
┌───▼────┐      ┌────▼─────┐     ┌────▼─────┐
│Adapters│      │Generators│     │Connectors│
│        │      │          │     │          │
│Selenium│      │Robot FW  │     │Git/BB/ADO│
│Pytest  │      │pytest-bdd│     │Local FS  │
│SpecFlow│      │          │     │          │
└────────┘      └──────────┘     └──────────┘
```

**Plugin Architecture**: Add new frameworks by implementing adapter interfaces.

---

## 📊 Project Maturity & Limitations

### Current Status: **Alpha (v0.1.0)**

**What Works Well:**
- ✅ Selenium Java + Cucumber → Robot Framework migrations
- ✅ Step definition parsing and transformation
- ✅ Bitbucket/GitHub/Azure DevOps integration
- ✅ Page object extraction and locator migration
- ✅ Impact analysis and coverage mapping
- ✅ Multi-threaded processing for large repositories

**Known Limitations:**
- ⚠️ **Parser Coverage**: Complex Java patterns may not parse (fallback generates TODOs)
- ⚠️ **Manual Review Required**: Output needs human validation before production use
- ⚠️ **AI Features**: Optional and require API keys (Azure OpenAI)
- ⚠️ **Error Handling**: Large repos may hit API rate limits
- ⚠️ **Documentation**: Some advanced features lack complete docs
- ⚠️ **Windows Paths**: Primary development on Windows; Unix path handling improving

**Not Yet Supported:**
- ❌ Dynamic locators or runtime-generated selectors
- ❌ Custom Selenium extensions or third-party frameworks
- ❌ Non-English test files (internationalization planned)
- ❌ Parallel test execution during validation

### Production Readiness

| Use Case | Readiness | Recommendation |
|----------|-----------|----------------|
| Personal projects | ✅ Ready | Great for experimentation |
| Internal tools/POCs | 🟡 Use with caution | Review output carefully |
| Production test suites | ❌ Not recommended | Wait for beta/v1.0 or contribute! |
| Enterprise deployments | ❌ Not recommended | Pilot programs only |

**Expected Timeline:**
- **Beta (v0.5)**: Q2 2026 (improved stability, more adapters)
- **v1.0 (Stable)**: Q4 2026 (production-ready, comprehensive testing)

---

## � AI Monetization & Cost Management

CrossBridge provides transparent AI cost tracking to help you optimize your migration budget:

### Cost Transparency Features
- **Real-time cost tracking** - See token usage and costs during transformation
- **Per-file cost breakdown** - Identify expensive files (complex step definitions, large page objects)
- **Model comparison** - Compare costs between GPT-3.5-turbo, GPT-4, Claude, etc.
- **Cost savings calculator** - Shows potential savings with different models
- **Budget-friendly defaults** - Uses GPT-3.5-turbo by default (~15x cheaper than GPT-4)

### Typical Migration Costs

| Project Size | Files | Estimated Tokens | GPT-3.5-turbo | GPT-4 |
|--------------|-------|------------------|---------------|-------|
| Small (50 files) | 50 | ~125K tokens | $0.12 | $1.80 |
| Medium (200 files) | 200 | ~500K tokens | $0.50 | $7.20 |
| Large (500 files) | 500 | ~1.25M tokens | $1.25 | $18.00 |
| Enterprise (2000 files) | 2000 | ~5M tokens | $5.00 | $72.00 |

**💡 Cost Optimization Tips:**
- Use **GPT-3.5-turbo** for initial migrations (93% cost savings vs GPT-4)
- Enable AI only for **complex files** (step definitions, page objects)
- Use **pattern-based transformation** for simple utility files (free!)
- Set **batch limits** to control spending per run
- Review **top cost files** in AI summary to optimize retry strategies

**🎯 Hybrid Approach** (Recommended):
```python
# Use pattern-based for utilities (free)
# Use AI for complex logic (paid)
transformation_mode: "hybrid"

# Result: ~60% cost savings while maintaining quality
```

### AI Summary Cost Breakdown
After each migration, CrossBridge displays:
- **Total cost and token usage**
- **Cost per file type** (step definitions vs page objects vs locators)
- **Top 5 most expensive files** - helps identify optimization opportunities
- **Model comparison** - shows savings with alternative models

Example:
```
💵 Top Cost Files:
  1. DataStoreSteps.robot (Step Definition): $0.0234 (5,430 tokens)
  2. BackUpJobStep.robot (Step Definition): $0.0198 (4,102 tokens)
  3. AddPolicies.robot (Step Definition): $0.0187 (3,988 tokens)

💡 Cost Savings:
  • Using gpt-3.5-turbo: $1.25
  • Same with gpt-4: ~$18.00
  • Savings: ~$16.75 (93% reduction)
```

---
## 🔌 Model Context Protocol (MCP) Integration

CrossBridge is **both an MCP Client and MCP Server**, enabling seamless integration with AI agents and external tools.

### 🖥️ MCP Server: Expose CrossBridge as Tools

CrossBridge exposes its capabilities as MCP tools that AI agents (Claude, ChatGPT, etc.) can consume:

**Available Tools:**
- `run_tests` - Execute tests in any project (pytest, junit, robot)
- `analyze_flaky_tests` - Detect flaky tests from execution history
- `migrate_framework` - Convert tests between frameworks
- `analyze_coverage` - Generate coverage reports and impact analysis
- `generate_tests` - AI-powered test generation from requirements

**Starting the MCP Server:**
```python
from core.ai.mcp.server import MCPServer, MCPServerConfig

# Configure server
config = MCPServerConfig(
    host="localhost",
    port=8080,
    auth_enabled=True,
    api_key="your-api-key"
)

# Start server
server = MCPServer(config)
server.start()

# AI agents can now call CrossBridge tools via MCP!
```

**Example: AI Agent Using CrossBridge**
```json
{
  "tool": "migrate_framework",
  "inputs": {
    "source_framework": "selenium_java_bdd",
    "target_framework": "robot_playwright",
    "repository_url": "https://github.com/org/repo",
    "branch": "main"
  }
}
```

### 🔄 MCP Client: Consume External Tools

CrossBridge can connect to external MCP servers (Jira, GitHub, CI/CD) to enhance workflows:

**Supported External Tools:**
- **Jira**: Create issues, search, update
- **GitHub**: Create PRs, get status, merge
- **CI/CD**: Trigger builds, get status

**Using External Tools:**
```python
from core.ai.mcp.client import MCPClient, MCPToolRegistry

# Discover tools from Jira server
registry = MCPToolRegistry(config_path="config/mcp_servers.json")
tools = registry.discover_tools("jira_server")

# Use MCP client to call tool
client = MCPClient(registry)
result = client.call_tool(
    "jira_create_issue",
    inputs={
        "project": "TEST",
        "summary": "Migration failed for LoginTest.java",
        "description": "AI transformation returned empty content",
        "issue_type": "Bug"
    }
)
```

**Configuration (config/mcp_servers.json):**
```json
{
  "servers": {
    "jira_server": {
      "url": "https://jira.example.com",
      "authentication": {
        "type": "bearer",
        "token": "your-jira-token"
      }
    },
    "github_server": {
      "url": "https://api.github.com",
      "authentication": {
        "type": "token",
        "token": "ghp_your-token"
      }
    }
  }
}
```

### 🎯 MCP Use Cases

**1. AI-Driven Workflows:**
```
AI Agent → CrossBridge MCP Server → Run tests → Create Jira issue (MCP Client)
```

**2. Automated Test Intelligence:**
```
Claude detects flaky test → CrossBridge analyzes → GitHub PR created → CI triggered
```

**3. Self-Service Test Migration:**
```
ChatGPT plugin → CrossBridge migrate_framework → PR opened → Slack notification
```

### 📚 MCP Documentation

- **[MCP Client Implementation](core/ai/mcp/client.py)** - Connect to external tools
- **[MCP Server Implementation](core/ai/mcp/server.py)** - Expose CrossBridge tools
- **[Unit Tests](tests/unit/core/ai/test_mcp_and_memory.py)** - Comprehensive test coverage

---
## �🛠️ Configuration Example

```yaml
# Example: Selenium Java BDD migration
migration:
  source_framework: selenium_bdd_java
  target_framework: robot_playwright
  
  paths:
    features: "src/test/resources/features"
    step_definitions: "src/main/java/com/example/stepdefinition"
    page_objects: "src/main/java/com/example/pagefactory"
  
  transformation:
    mode: enhanced  # manual | enhanced | hybrid
    tier: 2  # 1 (quick) | 2 (standard) | 3 (deep)
    batch_size: 10
  
  repository:
    type: bitbucket
    workspace: your-workspace
    repo: your-repo
    branch: feature/robot-migration
```

---

## 📚 Documentation

- **[Getting Started Guide](docs/usage/)** - Step-by-step tutorials
- **[Architecture Overview](docs/architecture/)** - System design and components
- **[Adapter Development](docs/contributing/ADAPTER_DEVELOPMENT.md)** - Build your own adapters
- **[Migration Strategies](docs/migration/)** - Best practices for large migrations
- **[API Reference](docs/vision/)** - Future roadmap and APIs

---

## 🤝 Contributing

We welcome contributions! This project needs help with:

- 🔧 **Adapters**: Support for new frameworks (Cypress, Katalon, etc.)
- 🐛 **Bug Fixes**: Parser improvements, edge case handling
- 📖 **Documentation**: Tutorials, examples, API docs
- 🧪 **Testing**: Unit tests, integration tests, real-world validations
- 🌍 **Internationalization**: Non-English test support

**See [CONTRIBUTING.md](CONTRIBUTING.md)** for guidelines.

### Quick Contribution Guide

```bash
# Fork and clone
git clone https://github.com/yourusername/crossbridge.git

# Create a feature branch
git checkout -b feature/my-adapter

# Make changes and test
pytest tests/

# Submit a pull request
```

---

## 🎓 Learning Resources

- **[Post-Migration Testing Guide](docs/POST_MIGRATION_TESTING.md)** - Validate transformed tests
- **[Step Definition Enhancement](docs/STEP_DEFINITION_TRANSFORMATION_ENHANCEMENT.md)** - Advanced transformations
- **[Impact Analysis](docs/testing-impact-mapping.md)** - Track test-to-code dependencies

---

## 📜 License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

**Commercial Use**: Allowed under the terms of the Apache 2.0 license. 
**Attribution**: Required as per Apache 2.0 terms.
**Patent Grant**: Includes explicit patent protection for contributors and users.

---

## 🙏 Acknowledgments

Built by **CrossStack AI** for the global QA and DevOps community. Special thanks to:
- Robot Framework and Playwright communities
- Contributors to Selenium and Cucumber projects
- Early adopters providing feedback and bug reports

---

## 📞 Support & Community

- **Issues**: [GitHub Issues](https://github.com/yourusername/crossbridge/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/crossbridge/discussions)
- **Email**: vikas.sdet@gmail.com (for sensitive topics)

**Response Time**: This is a volunteer project. Please be patient! 🙂

---

## 🗺️ Roadmap

### Q1 2026 (Current)
- [x] Core Selenium Java migration
- [x] Bitbucket/GitHub/Azure DevOps integration
- [x] Impact analysis features
- [ ] Improved error handling and logging
- [ ] Comprehensive test coverage (>80%)

### Q2 2026
- [ ] Beta release (v0.5)
- [ ] Cypress adapter
- [ ] Enhanced AI features (Claude, GPT-4 support)
- [ ] Web UI for migrations
- [ ] Docker support

### Q3 2026
- [ ] Playwright (Java/Python) adapter
- [ ] Performance optimization
- [ ] Internationalization
- [ ] Plugin marketplace

### Q4 2026
- [ ] v1.0 Stable release
- [ ] Enterprise features (LDAP, SSO)
- [ ] Cloud-hosted service option
- [ ] Certification program

---

## 💬 Testimonials

*Coming soon! We'd love to hear about your experience with CrossBridge.*

---

## ⭐ Show Your Support

If CrossBridge helps your team, please:
- ⭐ **Star this repository** to help others discover it
- 📢 **Share your experience** in Discussions or LinkedIn
- 🐛 **Report bugs** to help improve quality
- 💻 **Contribute code** to make it better for everyone

---

**Built with ❤️ by CrossStack AI for the test automation community.**

*CrossBridge is a product of CrossStack AI - Bridging Legacy to AI-Powered Test Systems*
