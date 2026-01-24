# Grafana Panel Update: Recent Embeddings Created
## Test Case ID Display Enhancement

**Date**: January 24, 2026  
**Issue**: Panel showing UUID entity_id instead of readable test case identifiers  
**Solution**: Enhanced SQL query with LEFT JOIN to test_case table  

---

## Changes Made

### Before (Original Query)
```sql
SELECT 
    entity_type, 
    entity_id::text as entity_id, 
    content_hash, 
    (metadata->>'test_name') as test_name, 
    (metadata->>'model') as model, 
    created_at 
FROM memory_embeddings 
ORDER BY created_at DESC 
LIMIT 20
```

**Problems**:
- Showed raw UUID for entity_id
- metadata->>'test_name' was NULL (not populated in embeddings)
- No link to actual test case data
- No framework or file information

### After (Enhanced Query)
```sql
SELECT 
    COALESCE(
        tc.test_name,
        me.metadata->>'name',
        SUBSTRING(me.metadata->>'text', 1, 50),
        CAST(me.entity_id AS VARCHAR)
    ) as "Test Case ID",
    me.entity_type as "Type",
    COALESCE(tc.framework, me.metadata->>'framework', 'N/A') as "Framework",
    COALESCE(
        SUBSTRING(tc.test_file_path, 1, 40),
        me.metadata->>'file',
        'N/A'
    ) as "File",
    COALESCE(tc.suite_name, 'N/A') as "Suite",
    COALESCE(me.metadata->>'model', 'N/A') as "Model",
    me.created_at as "Created At"
FROM memory_embeddings me
LEFT JOIN test_case tc ON me.entity_id = tc.id
ORDER BY me.created_at DESC
LIMIT 20
```

**Improvements**:
- ✅ Shows actual test names (e.g., "test_playwright_checkout_1")
- ✅ Falls back to metadata text description if no test_case match
- ✅ Displays framework (pytest, playwright, cucumber, etc.)
- ✅ Shows file path (truncated to 40 chars)
- ✅ Includes test suite name
- ✅ Shows embedding model used
- ✅ Proper column headers for Grafana table

---

## Query Logic Explanation

### Test Case ID Column
```sql
COALESCE(
    tc.test_name,                              -- Priority 1: Actual test name from test_case table
    me.metadata->>'name',                       -- Priority 2: Name from metadata JSON
    SUBSTRING(me.metadata->>'text', 1, 50),    -- Priority 3: First 50 chars of description
    CAST(me.entity_id AS VARCHAR)              -- Priority 4: Fallback to UUID
)
```

This ensures we always show the most readable identifier available.

### Framework Column
```sql
COALESCE(
    tc.framework,                              -- From test_case table (most reliable)
    me.metadata->>'framework',                  -- From embedding metadata
    'N/A'                                       -- Fallback
)
```

### File Column
```sql
COALESCE(
    SUBSTRING(tc.test_file_path, 1, 40),       -- Truncated file path
    me.metadata->>'file',                       -- From metadata
    'N/A'                                       -- Fallback
)
```

---

## Sample Output

### Before
```
entity_type | entity_id                              | content_hash | test_name | model | created_at
------------|----------------------------------------|--------------|-----------|-------|---------------------------
test        | 599737e1-0434-4d38-b4a5-5c8835eb9c9b  | hash_123     | NULL      | NULL  | 2026-01-24 00:52:52+05:30
test        | 4d18fa21-be57-4b4b-91a3-0ad335d653cd  | hash_456     | NULL      | NULL  | 2026-01-24 00:52:52+05:30
```

### After
```
Test Case ID                                  | Type     | Framework  | File                                    | Suite              | Model      | Created At
----------------------------------------------|----------|------------|-----------------------------------------|--------------------|-----------|--------------------------
test_playwright_checkout_1                    | test_case| playwright | tests/test_playwright_checkout_1.py     | playwright_suite_1 | N/A        | 2026-01-24 00:08:15+05:30
test_testng_payment_0                         | test_case| testng     | tests/test_testng_payment_0.py          | testng_suite_1     | N/A        | 2026-01-24 00:08:15+05:30
Test UI button click with network delay veri  | test     | playwright | N/A                                     | N/A                | N/A        | 2026-01-24 00:52:52+05:30
Test database transaction with rollback veri  | test     | pytest     | N/A                                     | N/A                | N/A        | 2026-01-24 00:52:52+05:30
```

**Key Improvements Visible**:
- Real test names like "test_playwright_checkout_1" instead of UUIDs
- Framework information (playwright, testng, pytest, cucumber)
- File paths showing test location
- Suite names for organized viewing
- Descriptive text for embeddings without test_case link

---

## Dashboard File Updated

**File**: `grafana/dashboards/crossbridge_overview.json`  
**Panel ID**: 16  
**Panel Title**: "Recent Embeddings Created"  
**Panel Type**: table  
**Validation**: ✅ JSON valid, 7 panels total

---

## Testing & Verification

### Query Tested Successfully
```bash
python scripts/test_improved_query.py
```

**Results**:
- ✅ 20 embeddings returned
- ✅ Test case IDs showing properly
- ✅ Proper fallback for embeddings without test_case link
- ✅ All columns populated correctly
- ✅ No NULL values in key columns (using COALESCE)

### Database Statistics
- **Total Embeddings**: 89
- **With test_case link**: ~30 (test_case entity type)
- **Without test_case link**: ~59 (synthetic test data from integration tests)
- **Entity Types**: test_case, test, scenario, feature, page_object, code_unit

---

## Benefits

### For End Users
1. **Immediate Test Identification** - See actual test names, not UUIDs
2. **Better Context** - Framework, file path, and suite information
3. **TestRail-like Experience** - Similar to commercial test management tools
4. **Easier Debugging** - Can quickly identify which tests have embeddings
5. **Time Savings** - No need to copy UUIDs and query separately

### For Developers
1. **Better Traceability** - Link embeddings back to test code
2. **Easier Debugging** - See exactly which tests are being embedded
3. **Quality Validation** - Verify correct tests are in memory system
4. **Audit Trail** - Track when specific tests got embeddings

### For Grafana Users
1. **Professional Dashboard** - More polished and user-friendly
2. **Searchable Table** - Can search by test name in Grafana
3. **Export-Friendly** - CSV exports now have meaningful data
4. **Column Sorting** - Can sort by any column for analysis

---

## Next Steps (Optional)

### Additional Enhancements

1. **Add Test Status Column**
```sql
tc.status as "Status"  -- Show if test is active/inactive
```

2. **Add Priority Column**
```sql
tc.priority as "Priority"  -- Show test priority (high/medium/low)
```

3. **Add Tags Column**
```sql
ARRAY_TO_STRING(tc.tags, ', ') as "Tags"  -- Show test tags
```

4. **Add Similarity Score** (for duplicate detection)
```sql
-- When showing duplicate embeddings
similarity_score as "Similarity %"
```

5. **Add Clickable Links** (if Grafana supports)
```sql
CONCAT('https://testrail.com/tests/', tc.id) as "TestRail Link"
```

---

## Rollback Instructions

If needed, revert to original query:

1. Open `grafana/dashboards/crossbridge_overview.json`
2. Find panel with `"id": 16`
3. Replace `rawSql` with original:
```json
"rawSql": "SELECT entity_type, entity_id::text as entity_id, content_hash, (metadata->>'test_name') as test_name, (metadata->>'model') as model, created_at FROM memory_embeddings ORDER BY created_at DESC LIMIT 20"
```

---

## Related Files

- **Dashboard**: `grafana/dashboards/crossbridge_overview.json`
- **Test Script**: `scripts/test_improved_query.py`
- **Schema Analysis**: `scripts/analyze_test_schema.py`
- **Verification**: `scripts/verify_grafana_data.py`

---

**Status**: ✅ **COMPLETE**  
**Tested**: ✅ Query validated with 89 embeddings  
**Deployed**: ✅ Dashboard JSON updated  
**Documented**: ✅ This document + inline comments
