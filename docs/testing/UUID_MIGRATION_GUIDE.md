# UUID Migration Guide for CrossBridge Persistence Tests

**Version**: 1.0  
**Date**: January 29, 2026  
**Status**: Migration in Progress (56% Complete - 84/149 tests passing)

## Overview

This guide documents the migration from integer primary keys to UUID primary keys in the CrossBridge persistence layer, including the necessary changes to unit tests that mock database operations.

## Table of Contents

1. [Background](#background)
2. [What Changed](#what-changed)
3. [Why Tests Need Fixing](#why-tests-need-fixing)
4. [The Tuple Structure Pattern](#the-tuple-structure-pattern)
5. [Step-by-Step Fix Guide](#step-by-step-fix-guide)
6. [Common Patterns](#common-patterns)
7. [Testing Checklist](#testing-checklist)
8. [Progress Tracker](#progress-tracker)

---

## Background

### The Migration

CrossBridge's persistence layer originally used auto-incrementing integer IDs for primary keys:

```python
# OLD - Integer IDs
id: int = Field(default=None, primary_key=True)
```

These have been migrated to UUIDs for better distributed system support and security:

```python
# NEW - UUID IDs
id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
```

### Impact on Tests

Unit tests that mock database operations need to be updated because:

1. **Return Types**: Functions now return `UUID` instead of `int`
2. **Mock Data**: Mocks must provide UUID values, not integers
3. **Tuple Structures**: Database query results return tuples with UUIDs in specific positions

---

## What Changed

### Repository Functions

All repository functions that return IDs now return UUIDs:

| Function | Old Return Type | New Return Type |
|----------|----------------|-----------------|
| `create_discovery_run()` | `int` | `uuid.UUID` |
| `upsert_page_object()` | `int` | `uuid.UUID` |
| `insert_mapping()` | `int` | `uuid.UUID` |
| `create_test_case()` | `int` | `uuid.UUID` |

### Model Objects

All model objects now have UUID primary keys:

```python
# discovery_run table
@dataclass
class DiscoveryRun:
    id: UUID  # Was: int
    project_name: str
    git_commit: Optional[str]
    # ... other fields
```

---

## Why Tests Need Fixing

### The Core Issue

Repository unit tests use mocks to simulate database operations without actual database connections. These mocks need to return data in the exact same structure as real database queries.

**Problem**: Tests were written when IDs were integers. Now that IDs are UUIDs, the mock return values need updating.

### Example of Broken Test

```python
# ❌ BROKEN - Uses integer ID
def test_get_discovery_run_found(self, mock_session):
    mock_row = MagicMock()
    mock_row.id = 456  # ← Integer, should be UUID
    mock_row.project_name = "my-project"
    mock_session.execute.return_value.fetchone.return_value = mock_row
    
    discovery = get_discovery_run(mock_session, uuid.uuid4())
    
    assert discovery.id == 456  # ← Will fail because actual function returns UUID
```

---

## The Tuple Structure Pattern

### How SQLAlchemy Returns Data

When using `text()` queries with SQLAlchemy, results come back as tuples, not objects:

```python
result = session.execute(
    text("SELECT id, project_name, git_commit FROM discovery_run WHERE id = :id"),
    {"id": run_id}
).fetchone()

# result is a tuple: (uuid_obj, "project-name", "abc123")
# NOT an object with attributes: result.id, result.project_name
```

### Repository Pattern

Repositories convert tuples to model objects:

```python
def get_discovery_run(session: Session, run_id: UUID) -> Optional[DiscoveryRun]:
    result = session.execute(text("SELECT ...")).fetchone()
    
    if result:
        return DiscoveryRun(
            id=result[0],           # ← Tuple index 0
            project_name=result[1],  # ← Tuple index 1
            git_commit=result[2],    # ← Tuple index 2
            # ...
        )
```

### Why This Matters for Tests

Tests must mock tuples, not objects:

```python
# ❌ WRONG - Mocking an object
mock_row = MagicMock()
mock_row.id = 456
mock_row.project_name = "test"

# ✅ CORRECT - Mocking a tuple
mock_row = (uuid.uuid4(), "test", None, None, "cli", datetime.now(UTC), {})
```

---

## Step-by-Step Fix Guide

### Step 1: Identify the Query Return Structure

Look at the repository function to see what the SELECT query returns:

```python
# In persistence/repositories/discovery_repo.py
result = session.execute(
    text("""
    SELECT id, project_name, git_commit, git_branch, triggered_by, created_at, metadata
    FROM discovery_run
    WHERE id = :id
    """),
    {"id": run_id}
).fetchone()
```

**Tuple Structure**: `(id, project_name, git_commit, git_branch, triggered_by, created_at, metadata)`  
**Indices**: 0=id, 1=project_name, 2=git_commit, 3=git_branch, 4=triggered_by, 5=created_at, 6=metadata

### Step 2: Create UUID Values in Tests

```python
import uuid

# At the top of test methods, create UUIDs
test_uuid = uuid.uuid4()
created_at = datetime.now(UTC)
```

### Step 3: Update Mock Return Value

Replace MagicMock objects with tuples:

```python
# ❌ OLD
mock_row = MagicMock()
mock_row.id = 456
mock_row.project_name = "test-project"
mock_row.git_commit = "abc123"
# ...

# ✅ NEW
mock_row = (test_uuid, "test-project", "abc123", "main", "cli", created_at, {})
```

### Step 4: Update Assertions

Change assertions from integer comparisons to UUID comparisons:

```python
# ❌ OLD
assert discovery.id == 456

# ✅ NEW
assert discovery.id == test_uuid
assert isinstance(discovery.id, uuid.UUID)
```

### Step 5: Handle Special Cases

#### For `fetchall()` (Multiple Rows)

```python
# ✅ List of tuples
mock_rows = [
    (uuid.uuid4(), "proj1", None, None, "cli", datetime.now(UTC), None),
    (uuid.uuid4(), "proj2", "abc", "main", "ci", datetime.now(UTC), None)
]

mock_result = MagicMock()
mock_result.fetchall.return_value = mock_rows
mock_session.execute.return_value = mock_result
```

#### For Aggregate Queries (Stats)

```python
# Single row with multiple counts
# Tuple: (test_count, page_object_count, mapping_count)
mock_row = (15, 8, 42)

mock_result = MagicMock()
mock_result.fetchone.return_value = mock_row
mock_session.execute.return_value = mock_result
```

#### For `inserted_primary_key`

```python
# After INSERT operations
test_uuid = uuid.uuid4()
mock_result = MagicMock()
mock_result.inserted_primary_key = [test_uuid]  # ← List with UUID
mock_session.execute.return_value = mock_result
```

---

## Common Patterns

### Pattern 1: Test Get Single Record

```python
def test_get_record_found(self, mock_session):
    """Test retrieving a single record."""
    test_uuid = uuid.uuid4()
    created_at = datetime.now(UTC)
    
    # Tuple structure matching SELECT query
    mock_row = (
        test_uuid,          # id
        "test-value",       # name/project/etc
        "additional",       # additional fields...
        created_at,         # timestamp
        {}                  # metadata
    )
    
    mock_result = MagicMock()
    mock_result.fetchone.return_value = mock_row
    mock_session.execute.return_value = mock_result
    
    record = get_record(mock_session, test_uuid)
    
    assert record is not None
    assert record.id == test_uuid
    assert isinstance(record.id, uuid.UUID)
```

### Pattern 2: Test List Records

```python
def test_list_records(self, mock_session):
    """Test listing multiple records."""
    uuid1 = uuid.uuid4()
    uuid2 = uuid.uuid4()
    created_at = datetime.now(UTC)
    
    mock_rows = [
        (uuid1, "record1", created_at, None),
        (uuid2, "record2", created_at, None)
    ]
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = mock_rows
    mock_session.execute.return_value = mock_result
    
    records = list_records(mock_session)
    
    assert len(records) == 2
    assert records[0].id == uuid1
    assert records[1].id == uuid2
```

### Pattern 3: Test Create Record

```python
def test_create_record(self, mock_session):
    """Test creating a new record."""
    test_uuid = uuid.uuid4()
    
    mock_result = MagicMock()
    mock_result.inserted_primary_key = [test_uuid]
    mock_session.execute.return_value = mock_result
    
    record_id = create_record(mock_session, name="test")
    
    assert isinstance(record_id, uuid.UUID)
    assert record_id == test_uuid
```

### Pattern 4: Test Stats/Aggregates

```python
def test_get_stats(self, mock_session):
    """Test getting aggregated statistics."""
    # Single tuple with multiple aggregate values
    mock_row = (15, 8, 42)  # (count1, count2, count3)
    
    mock_result = MagicMock()
    mock_result.fetchone.return_value = mock_row
    mock_session.execute.return_value = mock_result
    
    stats = get_stats(mock_session, uuid.uuid4())
    
    assert stats["count1"] == 15
    assert stats["count2"] == 8
    assert stats["count3"] == 42
```

---

## Testing Checklist

Use this checklist when fixing persistence tests:

- [ ] Import `uuid` module at top of test file
- [ ] Replace all integer ID values with `uuid.uuid4()` calls
- [ ] Convert MagicMock rows to tuples matching SELECT column order
- [ ] Update `inserted_primary_key` mocks to return UUID lists
- [ ] Change assertions from `== integer` to `== test_uuid`
- [ ] Add `isinstance(result.id, uuid.UUID)` assertions where appropriate
- [ ] For `fetchall()` results, use list of tuples
- [ ] For aggregate queries, use single tuple with counts
- [ ] Verify tuple indices match repository SELECT statement order
- [ ] Run tests to verify fixes: `pytest tests/unit/persistence/test_FILE.py -v`

---

## Progress Tracker

### Current Status

**Overall**: 84/149 tests passing (56%)

### By File

| File | Status | Tests Passing | Notes |
|------|--------|--------------|-------|
| `test_discovery_repo.py` | 🟨 Partial | 14/22 (64%) | List tests and create tests need fixes |
| `test_mapping_repo.py` | ❌ Failing | ~10/35 (29%) | Needs tuple structure fixes |
| `test_page_object_repo.py` | ❌ Failing | ~12/38 (32%) | Needs tuple structure fixes |
| `test_test_case_repo.py` | ❌ Failing | ~20/46 (43%) | Needs tuple structure fixes |
| `test_orchestrator.py` | ❌ Failing | ~28/8 (78%) | Minor fixes needed |

### Specific Issues

#### test_discovery_repo.py (8 tests failing)

1. **test_create_discovery_run_minimal** - Insert mock needs UUID
2. **test_create_discovery_run_with_git_context** - Insert mock needs UUID
3. **test_create_discovery_run_with_metadata** - Insert mock needs UUID
4. **test_create_discovery_run_with_triggered_by** - Insert mock needs UUID
5. **test_create_discovery_run_error_handling** - Rollback assertion issue
6. **test_list_discovery_runs_all** - Needs iterable tuple list ✅ Fixed structure, may need iteration fix
7. **test_list_discovery_runs_by_project** - Needs iterable tuple list ✅ Fixed structure, may need iteration fix
8. **test_list_discovery_runs_with_limit** - Needs iterable tuple list ✅ Fixed structure, may need iteration fix

**Fixed (14 tests)**:
- ✅ test_get_discovery_run_found
- ✅ test_get_discovery_run_not_found
- ✅ test_get_latest_discovery_run_found
- ✅ test_get_latest_discovery_run_not_found
- ✅ test_list_discovery_runs_empty
- ✅ test_get_discovery_stats_full
- ✅ test_get_discovery_stats_zero_counts
- ✅ test_get_discovery_stats_none_results
- ✅ All Contract Stability tests (4)
- ✅ All Edge Case tests (3)

#### Remaining Files (~65 tests)

Similar patterns in:
- `test_mapping_repo.py` - 25+ tests need tuple fixes
- `test_page_object_repo.py` - 26+ tests need tuple fixes
- `test_test_case_repo.py` - 26+ tests need tuple fixes
- `test_orchestrator.py` - Few tests, mostly integration issues

---

## Quick Reference

### Import Statement
```python
import uuid
from datetime import datetime, UTC
```

### Create Test UUID
```python
test_uuid = uuid.uuid4()
```

### Mock fetchone() Result
```python
mock_row = (test_uuid, "value1", "value2", ...)
mock_result = MagicMock()
mock_result.fetchone.return_value = mock_row
mock_session.execute.return_value = mock_result
```

### Mock fetchall() Result
```python
mock_rows = [
    (uuid.uuid4(), "value1", ...),
    (uuid.uuid4(), "value2", ...)
]
mock_result = MagicMock()
mock_result.fetchall.return_value = mock_rows
mock_session.execute.return_value = mock_result
```

### Mock INSERT Result
```python
test_uuid = uuid.uuid4()
mock_result = MagicMock()
mock_result.inserted_primary_key = [test_uuid]
mock_session.execute.return_value = mock_result
```

### Assert UUID
```python
assert isinstance(result.id, uuid.UUID)
assert result.id == test_uuid
```

---

## Troubleshooting

### Error: "AssertionError: assert None == 'value'"

**Cause**: Trying to access compiled params dict with wrong key  
**Fix**: Don't assert on `compile().params` - it may not have readable values

### Error: "AssertionError: assert <MagicMock> == 123"

**Cause**: Mock returns MagicMock instead of actual value  
**Fix**: Use tuple structure: `mock_row = (uuid, "value", ...)` not `mock_row.id = 123`

### Error: "assert 0 == 2" in list tests

**Cause**: `fetchall()` returns empty list because mock doesn't iterate properly  
**Fix**: Ensure mock returns iterable list of tuples, not MagicMock objects

### Error: "TypeError: 'MagicMock' object is not iterable"

**Cause**: Repository tries to iterate over result, but mock isn't iterable  
**Fix**: Make mock return list: `mock_result.fetchall.return_value = [tuple1, tuple2]`

---

## Next Steps

### To Complete Migration (44% remaining)

1. **Fix discovery_repo.py** (8 tests)
   - Update INSERT operation mocks with UUIDs
   - Fix list iteration mocks
   
2. **Fix mapping_repo.py** (~25 tests)
   - Apply tuple structure pattern
   - Update all assertions
   
3. **Fix page_object_repo.py** (~26 tests)
   - Apply tuple structure pattern
   - Handle upsert operations
   
4. **Fix test_case_repo.py** (~26 tests)
   - Apply tuple structure pattern
   - Update discovery test case joins
   
5. **Fix orchestrator.py** (~5 tests)
   - Integration test fixes
   - Mock coordination

### Automation Opportunity

Consider creating a script to automatically convert common patterns:
- Find all `MagicMock()` with `.id = integer`
- Replace with tuple structures
- Update assertions

---

## Resources

- **Repository Code**: `persistence/repositories/*.py`
- **Model Definitions**: `persistence/models.py`
- **Test Files**: `tests/unit/persistence/*.py`
- **SQLAlchemy Text Queries**: https://docs.sqlalchemy.org/en/20/core/connections.html#sqlalchemy.engine.Result

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-29 | Initial guide, 56% tests passing |

---

## Contributors

- **Vikas Verma** - Initial migration and guide creation
- **CrossStack AI** - Test fixing assistance

---

**Last Updated**: January 29, 2026  
**Status**: 🟨 Migration 56% Complete (84/149 tests passing)
