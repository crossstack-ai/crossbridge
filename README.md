# CrossBridge 🌉
### by CrossStack AI

> **AI-Powered Test Automation Transformation Platform**  
> Modernize legacy test frameworks to modern, maintainable architectures

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
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

**CrossBridge** is an open-source platform that automatically transforms legacy test automation to modern frameworks, powered by intelligent parsing and optional AI assistance.

### What CrossBridge Does

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
- ✅ **Automated Migration**: Convert entire test suites in hours, not months
- ✅ **Intelligent Parsing**: Extracts test intent, locators, and page objects
- ✅ **Framework-Agnostic**: Plugin architecture supports multiple sources/targets
- ✅ **AI-Enhanced** (Optional): Improves locator strategies and test quality
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

# Run interactive CLI
python -m cli.app
```

### Your First Migration

```bash
# Start the interactive menu
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

### Source Frameworks (Input)
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

## 🛠️ Configuration Example

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

MIT License - see [LICENSE](LICENSE) for details.

**Commercial Use**: Allowed. Attribution appreciated but not required.

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
