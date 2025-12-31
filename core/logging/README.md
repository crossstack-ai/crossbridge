

# CrossStack-AI CrossBridge Logging Framework

Comprehensive, enterprise-grade logging system for the CrossBridge platform with AI-specific capabilities.

## Features

✅ **Multiple Verbosity Levels**
- TRACE: Most detailed debugging
- DEBUG: Detailed information
- INFO: General information
- SUCCESS: Success operations (custom)
- WARNING: Warning messages
- ERROR: Error messages
- CRITICAL: Critical failures

✅ **Smart Output**
- Console logging with colors and emojis
- File logging with rotation
- JSON logging for machine parsing
- AI-specific logging

✅ **Category-Based Organization**
- GENERAL, AI, ADAPTER, MIGRATION
- GOVERNANCE, EXECUTION, PERSISTENCE
- ORCHESTRATION, TESTING, PERFORMANCE, SECURITY

✅ **AI Integration**
- CrossStack-AI branding
- AI operation tracking
- Prompt/response logging
- Token counting
- Model information

✅ **Intelligent Features**
- Context management
- Noise reduction
- Performance tracking
- Automatic log rotation
- Thread-safe

## Quick Start

### Basic Usage

```python
from core.logging import get_logger, LogLevel, LogCategory

# Get a logger
logger = get_logger(__name__, category=LogCategory.GENERAL)

# Log messages
logger.info("Application started")
logger.success("Operation completed successfully")
logger.warning("Resource usage high")
logger.error("Failed to connect", service="api")
```

### Configure Logging

```python
from core.logging import configure_logging, LogLevel
from pathlib import Path

# Configure global settings
configure_logging(
    level=LogLevel.INFO,
    log_dir=Path("logs"),
    enable_console=True,
    enable_file=True
)
```

### AI-Specific Logging

```python
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.AI)

# AI operations
logger.ai_operation("text_generation", "started", model="gpt-4")
logger.ai_prompt(prompt_text, model="gpt-4")
logger.ai_response(response_text, tokens=150)
logger.ai_error("Rate limit exceeded", operation="completion")
```

### Adapter Logging

```python
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.ADAPTER)

# Adapter operations
logger.adapter_detection("selenium", detected=True)
logger.adapter_operation("pytest", "discover_tests", count=25)
```

### Test Execution Logging

```python
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.TESTING)

# Test lifecycle
logger.test_started("test_user_login")
logger.test_passed("test_user_login", duration=1.5)
logger.test_failed("test_checkout", reason="Assertion failed")
```

### Context Management

```python
logger = get_logger(__name__)

# Add context to all subsequent logs
logger.add_context(user_id="123", session="abc")
logger.info("User action")  # Includes user_id and session

# Clear context
logger.clear_context()
```

### Performance Tracking

```python
import time

start = time.time()
# ... your operation ...
duration = time.time() - start

logger.performance("database_query", duration, rows=100)
```

## Verbosity Levels

Control log verbosity with different levels:

```python
from core.logging import set_global_log_level, LogLevel

# Development: see everything
set_global_log_level(LogLevel.TRACE)

# Testing: debug info
set_global_log_level(LogLevel.DEBUG)

# Production: info and above
set_global_log_level(LogLevel.INFO)

# Quiet: warnings and errors only
set_global_log_level(LogLevel.WARNING)
```

## Log Categories

Organize logs by category:

```python
from core.logging import get_logger, LogCategory

# Different categories for different modules
ai_logger = get_logger("ai_module", category=LogCategory.AI)
adapter_logger = get_logger("adapter", category=LogCategory.ADAPTER)
gov_logger = get_logger("governance", category=LogCategory.GOVERNANCE)
```

Each category gets its own log file when file logging is enabled.

## Console Output

Console logs include:
- ✅ Color coding by level
- ✅ Emoji indicators
- ✅ Timestamps
- ✅ Module names
- ✅ Clean formatting

Example output:
```
[10:30:45] ℹ️  INFO     [crossbridge.adapter] Adapter [selenium] ✅ detected
[10:30:46] ✅ SUCCESS  [crossbridge.testing] Test passed: test_login (1.2s)
[10:30:47] ⚠️  WARNING  [crossbridge.execution] High memory usage threshold=90%
[10:30:48] 🤖 INFO     [crossbridge.ai] AI Operation: text_generation - completed
```

## File Logging

File logs provide:
- ✅ Detailed timestamps
- ✅ Process/thread information
- ✅ Full module paths
- ✅ Automatic rotation (10MB default)
- ✅ Backup retention (5 files default)

Log files are organized by category:
```
logs/
├── general.log
├── ai.log
├── adapter.log
├── governance.log
├── crossstack-ai.log  (AI-specific)
└── [category].log.1  (rotated backups)
```

## JSON Logging

For machine parsing and analysis:

```python
from core.logging.formatters import JSONFormatter

handler.setFormatter(JSONFormatter())
```

JSON format includes:
```json
{
  "timestamp": "2025-12-31T10:30:45.123456",
  "level": "INFO",
  "logger": "crossbridge.adapter",
  "module": "selenium",
  "message": "Test passed",
  "brand": "CrossStack-AI CrossBridge",
  "test": "test_login",
  "duration": 1.2
}
```

## Filters

Control what gets logged:

```python
from core.logging.filters import CategoryFilter, AIOperationFilter
from core.logging import LogCategory

# Only log AI operations
handler.addFilter(AIOperationFilter())

# Only log specific categories
handler.addFilter(CategoryFilter({LogCategory.AI, LogCategory.ADAPTER}))
```

## Advanced Configuration

### Multiple Handlers

```python
from core.logging import CrossBridgeLogger, LogCategory
from core.logging.handlers import ConsoleHandler, RotatingFileHandler
from core.logging.formatters import ConsoleFormatter, FileFormatter
from pathlib import Path

logger = CrossBridgeLogger(
    name="my_module",
    category=LogCategory.GENERAL,
    log_dir=None,  # Manual handler setup
    enable_console=False,
    enable_file=False
)

# Console with colors
console = ConsoleHandler()
console.setFormatter(ConsoleFormatter(use_colors=True, use_emojis=True))
logger._logger.addHandler(console)

# File with rotation
file_handler = RotatingFileHandler("logs/app.log", maxBytes=20*1024*1024)
file_handler.setFormatter(FileFormatter())
logger._logger.addHandler(file_handler)
```

### Conditional Logging

```python
from core.logging import get_logger, LogLevel

logger = get_logger(__name__)

# Only log if needed
if logger._logger.isEnabledFor(LogLevel.DEBUG.value):
    expensive_debug_info = compute_debug_data()
    logger.debug(f"Debug data: {expensive_debug_info}")
```

## Best Practices

### 1. Use Appropriate Levels

```python
logger.trace("Function entered with args: ...")  # Very detailed
logger.debug("Processing record 5/100")          # Debug info
logger.info("Service started successfully")      # Normal operations
logger.success("Migration completed")            # Success milestones
logger.warning("Retry attempt 3/5")             # Warnings
logger.error("Database connection failed")       # Errors
logger.critical("System out of memory")          # Critical issues
```

### 2. Add Context

```python
# Good: includes context
logger.info("User action completed", user_id=user.id, action="purchase")

# Better: use context manager
logger.add_context(user_id=user.id)
logger.info("User logged in")
logger.info("User viewed product")
logger.clear_context()
```

### 3. Use Categories

```python
# Organize by module responsibility
ai_logger = get_logger(__name__, category=LogCategory.AI)
db_logger = get_logger(__name__, category=LogCategory.PERSISTENCE)
test_logger = get_logger(__name__, category=LogCategory.TESTING)
```

### 4. Log Exceptions Properly

```python
try:
    risky_operation()
except Exception as e:
    # Logs exception with full traceback
    logger.exception("Operation failed")
    
    # Or with custom message
    logger.error("Failed to process data", exc_info=True)
```

### 5. Performance Awareness

```python
# Avoid expensive operations in log messages
logger.debug(f"Data: {expensive_computation()}")  # Bad

# Use conditional logging
if logger._logger.isEnabledFor(LogLevel.DEBUG.value):
    logger.debug(f"Data: {expensive_computation()}")  # Good
```

## Integration Examples

### Flask Application

```python
from flask import Flask
from core.logging import configure_logging, get_logger, LogLevel, LogCategory

app = Flask(__name__)

# Configure at startup
configure_logging(
    level=LogLevel.INFO,
    log_dir=Path("logs"),
    enable_console=True,
    enable_file=True
)

logger = get_logger(__name__, category=LogCategory.GENERAL)

@app.route("/")
def index():
    logger.info("Index page accessed", method="GET")
    return "Hello"
```

### CLI Application

```python
import argparse
from core.logging import configure_logging, get_logger, LogLevel

parser = argparse.ArgumentParser()
parser.add_argument("--verbose", "-v", action="count", default=0)
args = parser.parse_args()

# Set level based on verbosity
level_map = {0: LogLevel.WARNING, 1: LogLevel.INFO, 2: LogLevel.DEBUG, 3: LogLevel.TRACE}
level = level_map.get(args.verbose, LogLevel.TRACE)

configure_logging(level=level, enable_file=False)
logger = get_logger(__name__)
```

### Testing

```python
from core.logging import configure_logging, LogLevel

# Quiet logs during tests
configure_logging(level=LogLevel.ERROR, enable_console=False)
```

## Troubleshooting

### Not Seeing Logs?

Check the log level:
```python
from core.logging import get_global_log_level
print(f"Current level: {get_global_log_level()}")
```

### Too Noisy?

Increase the log level or use filters:
```python
from core.logging import set_global_log_level, LogLevel

set_global_log_level(LogLevel.WARNING)  # Only warnings and above
```

### File Permissions?

Ensure write permissions:
```python
from pathlib import Path

log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)
```

## Architecture

```
core/logging/
├── __init__.py          # Public API
├── logger.py            # Core logger implementation
├── formatters.py        # Log formatters
├── handlers.py          # Log handlers
├── filters.py           # Log filters
└── README.md            # Documentation
```

## Status

✅ **FULLY IMPLEMENTED**

- Multiple verbosity levels (TRACE to CRITICAL)
- Console logging with colors and emojis
- File logging with rotation
- JSON logging for parsing
- AI-specific logging with CrossStack-AI branding
- Category-based organization
- Context management
- Performance tracking
- Noise reduction
- Thread-safe operations
- Comprehensive documentation
