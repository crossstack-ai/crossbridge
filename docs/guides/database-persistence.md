# Database Persistence for Page Object Mappings

## Installation

```bash
pip install sqlalchemy psycopg2-binary
```

## Quick Start

### 1. Create Database

```sql
CREATE DATABASE crossbridge;
```

### 2. Initialize Schema

```python
from adapters.common.db_models import DatabaseManager, export_sql_schema

# Option 1: Use SQLAlchemy (recommended)
db = DatabaseManager("postgresql://user:password@localhost:5432/crossbridge")
db.create_tables()

# Option 2: Manual SQL
export_sql_schema("schema.sql")  # Creates schema.sql file
# Then run: psql -U user -d crossbridge -f schema.sql
```

### 3. Store Mappings

```python
from adapters.java.impact_mapper import create_impact_map

# Generate impact map from source code
impact_map = create_impact_map("d:/Future/my-project")

# Store in database
with db.get_session() as session:
    for mapping in impact_map.mappings:
        # Add Page Objects
        for po_name in mapping.page_objects:
            po = db.add_page_object(
                session,
                name=po_name,
                file_path=f"src/pages/{po_name}.java",
                framework="selenium-java-junit"
            )
            
            # Add Test Case
            test = db.add_test_case(
                session,
                test_id=mapping.test_id,
                file_path=mapping.test_file,
                framework="selenium-java-junit"
            )
            
            # Add Mapping
            db.add_mapping(
                session,
                test_case_id=test.id,
                page_object_id=po.id,
                source=mapping.mapping_source.value,
                confidence=mapping.confidence
            )
```

### 4. Query Impacted Tests

```python
# Which tests are impacted by LoginPage change?
with db.get_session() as session:
    impacted = db.get_impacted_tests(session, "LoginPage", min_confidence=0.5)
    print(impacted)
    # [
    #   {"test_id": "LoginTest.testValidLogin", "page_object": "LoginPage", "source": "static_ast", "confidence": 0.85},
    #   {"test_id": "LoginTest.testInvalidLogin", "page_object": "LoginPage", "source": "static_ast", "confidence": 0.92}
    # ]
```

## Unified Data Model

All mappings follow this format:

```json
{
  "test_id": "LoginTest.testValidLogin",
  "page_object": "LoginPage",
  "source": "static_ast",
  "confidence": 0.85
}
```

### Source Types

- `static_ast`: Release Stage - Static code analysis
- `coverage`: Release Stage - Code coverage data
- `ai`: Release Stage - AI-inferred mappings
- `runtime_trace`: Release Stage - Execution traces
- `manual`: User-defined mappings

## Schema

### Tables

**page_object**
- `id` (UUID): Primary key
- `name` (TEXT): Class name (e.g., "LoginPage")
- `file_path` (TEXT): Source file path
- `framework` (TEXT): Test framework (e.g., "selenium-java-junit")
- `package` (TEXT): Package/module name
- `base_class` (TEXT): Parent class
- `created_at`, `updated_at` (TIMESTAMP)

**test_case**
- `id` (UUID): Primary key
- `test_id` (TEXT): Unique identifier (e.g., "LoginTest.testValidLogin")
- `file_path` (TEXT): Test file path
- `framework` (TEXT): Test framework
- `class_name`, `method_name` (TEXT): Test location
- `created_at`, `updated_at` (TIMESTAMP)

**test_page_mapping**
- `id` (UUID): Primary key
- `test_case_id` (UUID): Foreign key to test_case
- `page_object_id` (UUID): Foreign key to page_object
- `source` (TEXT): Mapping source (static_ast, coverage, ai)
- `confidence` (FLOAT): Confidence score (0.0-1.0)
- `observed_at` (TIMESTAMP): When mapping was detected
- `usage_type` (TEXT): How PO is used (import, instantiation, etc.)
- `line_number` (TEXT): Line numbers of usage

## API Reference

### DatabaseManager

```python
db = DatabaseManager(connection_string)
```

**Methods:**
- `create_tables()`: Create schema
- `get_session()`: Get database session
- `add_page_object(...)`: Add/update Page Object
- `add_test_case(...)`: Add/update test case
- `add_mapping(...)`: Add test-PO mapping
- `get_impacted_tests(po_name, min_confidence)`: Query impacted tests
- `get_page_objects_for_test(test_id)`: Query POs for test
- `get_mappings_by_source(source)`: Query by source
- `get_statistics()`: Get mapping stats

## Multi-Phase Support

The schema supports all mapping phases:

```python
# Release Stage: Static AST
mapping = db.add_mapping(
    session, test_id, po_id,
    source="static_ast",
    confidence=0.85
)

# Release Stage: Code Coverage
mapping = db.add_mapping(
    session, test_id, po_id,
    source="coverage",
    confidence=0.95
)

# Release Stage: AI Inference
mapping = db.add_mapping(
    session, test_id, po_id,
    source="ai",
    confidence=0.72
)
```

Multiple sources for the same test-PO pair are tracked separately, allowing confidence aggregation and source comparison.

## Example: Complete Workflow

```python
from adapters.common.db_models import DatabaseManager
from adapters.java.impact_mapper import create_impact_map

# 1. Initialize database
db = DatabaseManager("postgresql://localhost:5432/crossbridge")
db.create_tables()

# 2. Generate mappings from source code
impact_map = create_impact_map("d:/Future/my-project")

# 3. Store all mappings
with db.get_session() as session:
    for mapping in impact_map.mappings:
        test = db.add_test_case(
            session,
            test_id=mapping.test_id,
            file_path=mapping.test_file,
            framework="selenium-java-junit"
        )
        
        for ref in mapping.references:
            po = db.add_page_object(
                session,
                name=ref.page_object_class,
                file_path=ref.source_file or "unknown",
                framework="selenium-java-junit"
            )
            
            db.add_mapping(
                session,
                test_case_id=test.id,
                page_object_id=po.id,
                source=mapping.mapping_source.value,
                confidence=mapping.confidence,
                usage_type=ref.usage_type,
                line_number=str(ref.line_number) if ref.line_number else None
            )

# 4. Query impacted tests
with db.get_session() as session:
    # LoginPage changed - which tests?
    results = db.get_impacted_tests(session, "LoginPage")
    
    for r in results:
        print(f"Run test: {r['test_id']} (confidence: {r['confidence']})")
    
    # Statistics
    stats = db.get_statistics(session)
    print(f"Total mappings: {stats['total_mappings']}")
    print(f"Static AST: {stats['mappings_by_source']['static_ast']}")
```
