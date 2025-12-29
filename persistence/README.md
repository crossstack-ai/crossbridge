# CrossBridge Persistence Layer

Optional PostgreSQL persistence for test discovery metadata with append-only observational design.

## 🎯 Design Principles

✅ **Optional** - Works without database  
✅ **Append-Only** - Observational, not destructive  
✅ **Phase-Compatible** - Supports Phase 1 (static), Phase 2 (coverage), Phase 3 (AI)  
✅ **BI-Ready** - Normalized schema for reporting  
✅ **Audit-Safe** - Complete history preservation  

## 🏗️ Architecture

```
crossbridge discover --persist
      ↓
Extractors (AST / static)
      ↓
Neutral Models (TestMetadata)
      ↓
Persistence Layer (optional)
      ↓
PostgreSQL
```

## 📊 Database Schema

### Core Tables

| Table | Purpose | Key Features |
|-------|---------|--------------|
| `discovery_run` | Anchor table for discovery sessions | Git context, triggered_by |
| `test_case` | Framework-agnostic test storage | Unique constraint, idempotent upsert |
| `page_object` | Page Object pattern storage | Unique constraint |
| `test_page_mapping` | **Append-only** test ↔ page relationships | Source tracking, confidence scores |
| `discovery_test_case` | Links tests to discovery runs | History tracking |

### Key Design Features

**Append-Only Mappings**:
```sql
-- Never overwrite, always append
INSERT INTO test_page_mapping (...)
-- No ON CONFLICT DO UPDATE!
```

**Provenance Tracking**:
- `source`: `static_ast` | `coverage` | `ai` | `manual`
- `confidence`: 0.0 to 1.0
- `discovery_run_id`: Links to when discovered

**Views for BI**:
- `latest_discovery_per_project`
- `test_with_page_count`
- `page_object_usage`
- `discovery_history`

## 🚀 Quick Start

### 1. Setup Database

```bash
# Create PostgreSQL database
createdb crossbridge

# Initialize schema
psql crossbridge < persistence/schema.sql
```

### 2. Configure Connection

```bash
# Option 1: Full URL
export CROSSBRIDGE_DB_URL=postgresql://user:pass@localhost:5432/crossbridge

# Option 2: Individual components
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=crossbridge
export DB_USER=crossbridge
export DB_PASSWORD=your_password
```

### 3. Use in CLI

```bash
# Discover without persistence (default)
crossbridge discover

# Discover WITH persistence
crossbridge discover --persist

# With specific framework
crossbridge discover --framework selenium-java --persist
```

## 📝 Usage Examples

### Check Database Health

```python
from persistence import check_database_health

health = check_database_health()
print(health)
# {
#     "configured": True,
#     "connected": True,
#     "table_count": 5,
#     "schema_complete": True,
#     "message": "Database healthy"
# }
```

### Persist Discovery Results

```python
from persistence.orchestrator import persist_discovery

# After discovering tests
run_id = persist_discovery(
    discovered_tests=tests,  # List[TestMetadata]
    project_name="my-project",
    triggered_by="cli",
    framework_hint="junit5"
)

print(f"Discovery run ID: {run_id}")
```

### Query Discovery History

```python
from persistence import create_session, discovery_repo

session = create_session()

# Get latest discovery for project
latest = discovery_repo.get_latest_discovery_run(session, "my-project")
print(f"Last run: {latest.created_at}")
print(f"Git commit: {latest.git_commit}")

# Get statistics
stats = discovery_repo.get_discovery_stats(session, latest.id)
print(f"Tests: {stats['test_count']}")
print(f"Page Objects: {stats['page_object_count']}")
print(f"Mappings: {stats['mapping_count']}")

session.close()
```

### Find Impacted Tests

```python
from persistence import create_session, mapping_repo, page_object_repo

session = create_session()

# Find page object
page_id = page_object_repo.find_page_object(session, "LoginPage", "...")

# Get impacted tests
impacted_test_ids = mapping_repo.get_impacted_tests(
    session,
    page_id,
    min_confidence=0.7
)

print(f"{len(impacted_test_ids)} tests impacted by LoginPage change")

session.close()
```

## 🔧 API Reference

### Database Connection

```python
from persistence import DatabaseConfig, create_session, init_database

# Check if configured
if DatabaseConfig.is_configured():
    session = create_session()
    # ... use session
    session.commit()
    session.close()

# Initialize schema
init_database()
```

### Repositories

#### discovery_repo

```python
from persistence import create_session, discovery_repo

session = create_session()

# Create discovery run
run_id = discovery_repo.create_discovery_run(
    session,
    project_name="my-project",
    git_commit="abc123",
    git_branch="main",
    triggered_by="cli"
)

# Get discovery run
run = discovery_repo.get_discovery_run(session, run_id)

# Get latest
latest = discovery_repo.get_latest_discovery_run(session, "my-project")

# Get stats
stats = discovery_repo.get_discovery_stats(session, run_id)

session.close()
```

#### test_case_repo

```python
from persistence import create_session, test_case_repo, TestCase

session = create_session()

# Upsert test (idempotent)
test = TestCase(
    framework="junit5",
    package="com.example",
    class_name="LoginTest",
    method_name="testValidLogin",
    file_path="src/test/java/LoginTest.java",
    tags=["smoke"]
)
test_id = test_case_repo.upsert_test_case(session, test)

# Link to discovery run
test_case_repo.link_test_to_discovery(session, run_id, test_id)

# Find test
test_id = test_case_repo.find_test_case(
    session, "junit5", "com.example", "LoginTest", "testValidLogin"
)

# List tests
tests = test_case_repo.list_test_cases(
    session, framework="junit5", tags=["smoke"]
)

session.close()
```

#### page_object_repo

```python
from persistence import create_session, page_object_repo, PageObject

session = create_session()

# Upsert page object
page = PageObject(
    name="LoginPage",
    file_path="src/main/java/pages/LoginPage.java",
    framework="selenium"
)
page_id = page_object_repo.upsert_page_object(session, page)

# Get usage stats
usage = page_object_repo.get_page_object_usage(session, page_id)
# {"test_count": 5, "discovery_count": 3, "sources": ["static_ast", "ai"]}

# Get most used
top_pages = page_object_repo.get_most_used_page_objects(session, limit=10)
for page, count in top_pages:
    print(f"{page.name}: {count} tests")

session.close()
```

#### mapping_repo

```python
from persistence import create_session, mapping_repo

session = create_session()

# Insert mapping (append-only)
mapping_id = mapping_repo.insert_mapping(
    session,
    test_case_id=test_id,
    page_object_id=page_id,
    source="static_ast",
    discovery_run_id=run_id,
    confidence=0.95
)

# Get mappings for test
mappings = mapping_repo.get_mappings_for_test(session, test_id)

# Get impacted tests when page changes
impacted = mapping_repo.get_impacted_tests(
    session, page_id, min_confidence=0.7
)

session.close()
```

## 📈 BI / Reporting Queries

### Discovery Trend

```sql
SELECT 
    project_name,
    DATE(created_at) as date,
    COUNT(*) as discovery_count,
    AVG(test_count) as avg_tests
FROM discovery_history
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY project_name, DATE(created_at)
ORDER BY date DESC;
```

### Most Used Page Objects

```sql
SELECT 
    name,
    test_count,
    framework
FROM page_object_usage
ORDER BY test_count DESC
LIMIT 10;
```

### Mapping Source Distribution

```sql
SELECT 
    source,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence
FROM test_page_mapping
WHERE discovery_run_id = 'your-run-id'
GROUP BY source;
```

## 🔄 Phase Compatibility

### Phase 1: Static Discovery (Current)

```python
# AST-based discovery
run_id = persist_discovery(tests, project, "cli")
# source="static_ast", confidence=0.8
```

### Phase 2: Coverage Mapping (Future)

```python
# Add coverage-based mappings
mapping_repo.insert_mapping(
    session,
    test_id,
    page_id,
    source="coverage",  # New source!
    discovery_run_id=run_id,
    confidence=1.0  # Coverage is definitive
)
```

### Phase 3: AI Inference (Future)

```python
# Add AI-inferred mappings
mapping_repo.insert_mapping(
    session,
    test_id,
    page_id,
    source="ai",  # AI-inferred!
    discovery_run_id=run_id,
    confidence=0.75,  # ML confidence score
    metadata={"model": "gpt-4", "reasoning": "..."}
)
```

## 🧪 Testing

```bash
# Run persistence layer tests
pytest tests/unit/persistence/ -v

# Test with real PostgreSQL
export CROSSBRIDGE_DB_URL=postgresql://...
pytest tests/integration/persistence/ -v
```

## 🐳 Docker Setup

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: crossbridge
      POSTGRES_USER: crossbridge
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - ./persistence/schema.sql:/docker-entrypoint-initdb.d/schema.sql
```

```bash
docker-compose up -d
export CROSSBRIDGE_DB_URL=postgresql://crossbridge:dev_password@localhost:5432/crossbridge
crossbridge discover --persist
```

## 🔒 Security

**Never commit database credentials!**

```bash
# .gitignore
.env
*.env
secrets/
```

Use environment variables or secret managers:

```bash
# .env (not committed)
CROSSBRIDGE_DB_URL=postgresql://...
```

## 📊 Performance

- **Upserts are idempotent**: Safe to run multiple times
- **Append-only mappings**: No update overhead
- **Indexed queries**: Fast lookups on common patterns
- **Connection pooling**: Efficient resource usage

## 🤝 Contributing

When adding new persistence features:

1. Update schema.sql with new tables/columns
2. Add repository methods
3. Update orchestrator.py if needed
4. Add unit tests
5. Update this README

## See Also

- [Java Extractor Tests](../tests/unit/adapters/java/README.md)
- [Selenium Java Runner](../docs/selenium-java-runner.md)
- [Database Schema](schema.sql)
