# CrossBridge CLI - Professional-Grade Architecture

**Product:** CrossBridge  
**Company:** CrossStack AI

## Overview

The CrossBridge CLI is built following **professional DevOps/platform CLI patterns** (Terraform, AWS CLI, kubectl). It implements a clean separation between:

- **CLI Layer**: User interaction (Typer + Rich)
- **Orchestration Engine**: Business logic (reusable by UI/API)
- **Service Layer**: Migration, transformation, AI

> **Key Principle**: "The CLI is a conversation. The orchestrator is the product."

## Architecture

```
┌─────────────────────────────────────────────┐
│          CLI Layer (cli/)                    │
│  ┌──────────┬──────────┬─────────────────┐ │
│  │ app.py   │ prompts  │ branding.py     │ │
│  │ (Typer)  │ (input)  │ (Rich panels)   │ │
│  └──────────┴──────────┴─────────────────┘ │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│   Orchestration Engine (core/orchestration/) │
│  ┌──────────────────────────────────────┐  │
│  │ MigrationOrchestrator                │  │
│  │   - run()                            │  │
│  │   - validate()                       │  │
│  │   - transform()                      │  │
│  │   - commit()                         │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │ Pydantic Models                      │  │
│  │   - MigrationRequest                 │  │
│  │   - MigrationResponse                │  │
│  │   - Field validation                 │  │
│  └──────────────────────────────────────┘  │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│        Service Layer                         │
│  ┌──────────┬────────────┬──────────────┐  │
│  │ Repo     │ Transform  │ AI Services  │  │
│  │ Connectors│ Services  │              │  │
│  └──────────┴────────────┴──────────────┘  │
└─────────────────────────────────────────────┘
```

## Components

### 1. CLI Layer (`cli/`)

#### `app.py` - Main Entry Point
- **Purpose**: Typer-based CLI routing
- **Commands**:
  - `crossbridge migrate` - Interactive migration workflow
  - `crossbridge version` - Display version
- **Features**:
  - Interactive mode with prompts
  - Non-interactive mode for CI/CD
  - Dry-run support
  - Error handling with user-friendly messages

#### `branding.py` - CrossStack AI Identity
- **Purpose**: Rich-based UI components
- **Functions**:
  - `show_welcome()` - Branded welcome screen
  - `show_migration_summary()` - Configuration table
  - `show_completion()` - Success message with PR link
  - `show_error()` - Friendly error messages with suggestions
- **Design**: Clean, professional, subtle (not overwhelming)

#### `prompts.py` - User Interaction
- **Purpose**: Typer/Rich prompts for configuration
- **Functions**:
  - `prompt_migration_type()` - Select migration type
  - `prompt_repository()` - Repo URL, branch, auth
  - `prompt_ai_settings()` - AI configuration
- **Security**: `hide_input=True` for tokens/passwords

#### `progress.py` - Visual Feedback
- **Purpose**: Rich progress bars and live updates
- **Class**: `MigrationProgressTracker`
  - Maps `MigrationStatus` to progress %
  - Real-time updates during workflow
  - Spinner + progress bar

#### `errors.py` - Error Handling
- **Purpose**: User-friendly error messages
- **Classes**:
  - `CrossBridgeError` - Base exception
  - `AuthenticationError` - CS-AUTH-001
  - `RepositoryError` - CS-REPO-001
  - `TransformationError` - CS-TRANSFORM-001
- **Features**:
  - Error codes for tracking
  - Actionable suggestions
  - Stack traces hidden (in log file only)

### 2. Orchestration Engine (`core/orchestration/`)

#### `orchestrator.py` - MigrationOrchestrator
- **Purpose**: Framework-agnostic business logic
- **Method**: `run(request, progress_callback) -> response`
- **Workflow**:
  1. **Validate**: Test repo access, list branches
  2. **Analyze**: Discover Java/feature files with pagination
  3. **Transform**: Convert to Robot Framework + Playwright
  4. **Generate**: Create target framework structure
  5. **Commit**: Create branch and PR
- **Features**:
  - Progress callbacks for UI updates
  - Structured error codes
  - Auto-detection of source paths
  - Dry-run support

#### `models.py` - Pydantic Models
- **Purpose**: Request/response contracts
- **Classes**:
  - `MigrationRequest`: Complete specification (type, repo, auth, AI)
  - `MigrationResponse`: Results (files, PR, timing, errors)
  - `RepositoryAuth`: Credentials with `Field(exclude=True)` for security
  - `AIConfig`: AI service settings
- **Enums**:
  - `MigrationType`: 4 migration types
  - `AuthType`: GitHub/Bitbucket/Azure
  - `AIMode`: Public cloud, on-prem, disabled
  - `MigrationStatus`: 8 workflow states

### 3. Services Layer (`services/`)

#### `logging_service.py` - Dual-Layer Logging
- **Purpose**: Console + file logging
- **Console**: High-level steps, clean output
- **File**: Full debug, stack traces, API payloads
- **Location**: `~/.crossbridge/logs/run-<timestamp>.log`
- **Security**: `SensitiveDataFilter` redacts tokens/keys

## Usage

### Interactive Mode (Recommended)

```bash
crossbridge migrate
```

**Workflow**:
1. ✨ Welcome screen (CrossStack AI branding)
2. 📋 Select migration type (Selenium Java BDD → Robot Framework)
3. 🔗 Enter repository URL
4. 🌿 Specify branch (default: main)
5. 🔐 Provide authentication (token never echoed)
6. 🤖 Enable AI assistance? (Yes/No)
7. ⚙️ Configure AI provider (OpenAI/Anthropic/On-prem)
8. ✅ Confirm configuration
9. ⏳ Watch progress with real-time updates
10. 🎉 View results + log location

### Non-Interactive Mode (CI/CD)

```bash
crossbridge migrate \
  --repo https://bitbucket.org/workspace/repo \
  --branch main \
  --non-interactive
```

### Dry-Run Mode

```bash
crossbridge migrate --dry-run
```

Preview changes without committing to repository.

## Security Features

### 1. Token Protection
- **Input**: `typer.prompt(..., hide_input=True)`
- **Storage**: `Field(exclude=True)` - never serialized/logged
- **Logs**: `SensitiveDataFilter` redacts API keys, tokens, passwords

### 2. Credential Handling
- Tokens collected interactively (never from command history)
- No plaintext storage in config files
- Redacted from all console output and log files

### 3. Error Handling
- Stack traces hidden from console (file-only)
- Error messages sanitized (no sensitive data exposure)
- Error codes for tracking without revealing internals

## Logging Strategy

### Console Output (High-Level)
```
✨ CrossBridge by CrossStack AI
   Test Framework Migration • AI-Powered Modernization

→ Validating repository access
→ Scanning for Java files in TetonUIAutomation/src/main/java
  Discovered 150 Java files...
→ Scanning for feature files in TetonUIAutomation/src/main/resources/UIFeature
  Discovered 260 feature files...
→ Transforming 150 test files
→ Creating migration branch and pull request

✓ Migration completed successfully
  Pull Request: https://bitbucket.org/arcservedev/cc-ui-automation/pull-requests/850
  Logs: /Users/you/.crossbridge/logs/run-20231215_143022.log
  Duration: 45.3s
```

### File Output (Full Debug)
```
2023-12-15 14:30:22 | INFO     | root | CrossBridge session started
2023-12-15 14:30:22 | INFO     | root | Log file: /Users/you/.crossbridge/logs/run-20231215_143022.log
2023-12-15 14:30:23 | INFO     | core.orchestration.orchestrator | [validating] Validating repository access
2023-12-15 14:30:24 | DEBUG    | core.repo.bitbucket | Listing branches for workspace=arcservedev, repo=cc-ui-automation
2023-12-15 14:30:25 | DEBUG    | core.repo.bitbucket | Found 457 branches
2023-12-15 14:30:25 | INFO     | core.orchestration.orchestrator | Repository access validated. Found 457 branches.
...
```

## Error Handling

### User-Friendly Messages
```
✗ Migration failed
  Authentication failed

  Error code: CS-AUTH-001
  Suggestion: Check your credentials and repository permissions. Ensure your token has read/write access.
```

### Error Codes
- **CS-AUTH-001**: Authentication/authorization failed
- **CS-REPO-001**: Repository access or operation failed
- **CS-TRANSFORM-001**: File transformation failed
- **CS-AI-001**: AI service unavailable
- **CS-CONFIG-001**: Configuration invalid
- **CS-UNKNOWN-001**: Unexpected error

## Extension Points

### 1. Future UI Integration
```python
# Web UI can reuse orchestrator
from core.orchestration import MigrationOrchestrator, MigrationRequest

@app.post("/api/migrate")
async def migrate_endpoint(request: MigrationRequest):
    orchestrator = MigrationOrchestrator()
    return orchestrator.run(request, progress_callback=websocket.send)
```

### 2. Custom Progress Callbacks
```python
def custom_callback(message: str, status: MigrationStatus):
    # Send to Slack, Discord, etc.
    slack.send(f"[{status}] {message}")

orchestrator.run(request, progress_callback=custom_callback)
```

### 3. Plugin Architecture (Future)
- Custom transformers
- Additional AI providers
- New repository platforms

## Dependencies

### Required
- **typer** (>=0.9.0): CLI framework
- **rich** (>=13.0.0): Console output, progress bars
- **pydantic** (>=2.0.0): Data validation
- **requests** (>=2.31.0): HTTP client

### Optional
- **openai**: OpenAI API integration
- **anthropic**: Claude API integration

## Installation

```bash
# Install in development mode
pip install -e .

# Verify installation
crossbridge version
```

## Testing

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Test CLI without execution
crossbridge migrate --dry-run
```

## Best Practices

### 1. Separation of Concerns
- CLI handles interaction only
- Orchestrator contains all business logic
- Services are stateless and reusable

### 2. Progress Feedback
- Always provide progress callbacks
- Show file counts during discovery
- Display estimated time remaining

### 3. Error Resilience
- Validate early, fail fast
- Provide recovery suggestions
- Log full details for debugging

### 4. Security First
- Never log credentials
- Redact sensitive data automatically
- Use secure prompt for passwords

## Roadmap

### Release Stage: Core (✅ Complete)
- [x] Orchestration engine with Pydantic models
- [x] CLI branding and welcome screen
- [x] Interactive prompts for configuration
- [x] Progress tracking with Rich
- [x] Dual-layer logging
- [x] Error handling with codes

### Release Stage: Enhancement (🚧 In Progress)
- [ ] Config file persistence (`~/.crossbridge/config.yaml`)
- [ ] Profile management (save/load configurations)
- [ ] AI integration (OpenAI/Anthropic/On-prem)
- [ ] Advanced file transformation

### Release Stage: Platform (📋 Planned)
- [ ] Web UI (FastAPI + React)
- [ ] REST API
- [ ] Webhook notifications
- [ ] Plugin system

## License

MIT License - See [LICENSE](LICENSE) for details.

---

**Built with ❤️ by CrossStack AI**
