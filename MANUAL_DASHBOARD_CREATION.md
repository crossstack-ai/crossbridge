# Step-by-Step Dashboard Creation Guide

Since import isn't working, let's create panels manually:

## Step 1: Create New Dashboard
1. Go to: http://10.55.12.99:3000/dashboard/new
2. Click "Add visualization"

## Step 2: Configure First Panel (Total Tests)
1. **Select your PostgreSQL datasource**
2. Switch to "Code" mode
3. **Paste this query:**
```sql
SELECT 
    NOW() as time,
    COUNT(*) as value
FROM test_execution_event 
WHERE application_version IS NOT NULL 
AND created_at >= NOW() - INTERVAL '10 days'
```
4. Make sure **Format = Table** (dropdown above query)
5. Click "Run query" - should show 110
6. On the right panel:
   - Panel title: "Total Tests"
   - Visualization: Stat
7. Click "Apply"

## Step 3: Save Dashboard
1. Click disk icon (Save)
2. Name: "CrossBridge Version Tracking"
3. Click "Save"

## Step 4: Add Second Panel (Pass Rate by Version)
1. Click "Add" → "Visualization"
2. Select your PostgreSQL datasource
3. Switch to "Code" mode
4. **Paste this query:**
```sql
SELECT 
    application_version as metric,
    ROUND(100.0 * SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) / COUNT(*), 1) as value
FROM test_execution_event 
WHERE application_version IS NOT NULL 
AND created_at >= NOW() - INTERVAL '10 days'
GROUP BY application_version 
ORDER BY application_version
```
5. Make sure **Format = Table**
6. Click "Run query" - should show 4 versions with percentages
7. On the right:
   - Visualization: Bar gauge
   - Panel title: "Pass Rate by Version"
   - Unit: Percent (0-100)
   - Max: 100
   - Display mode: Gradient
8. Click "Apply"

## Step 5: Add Table Panel (Version Details)
1. Click "Add" → "Visualization"
2. Select PostgreSQL datasource
3. Code mode, paste:
```sql
SELECT 
    application_version as "Version",
    product_name as "Product",
    environment as "Environment",
    COUNT(*) as "Total Tests",
    SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as "Passed",
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as "Failed",
    ROUND(100.0 * SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) / COUNT(*), 1) as "Pass Rate %"
FROM test_execution_event 
WHERE application_version IS NOT NULL 
AND created_at >= NOW() - INTERVAL '10 days'
GROUP BY application_version, product_name, environment 
ORDER BY product_name, application_version
```
4. Format = Table
5. Run query - should show 4 rows
6. Visualization: Table
7. Panel title: "Version Details"
8. Click "Apply"

## Important Note
If panels work when created manually but imported dashboards are blank, the issue is:
- **Datasource UID mismatch** in the JSON
- Need to get your actual datasource UID

To get your datasource UID:
1. Go to: http://10.55.12.99:3000/connections/datasources
2. Click your PostgreSQL datasource
3. Look at the URL: `.../datasources/edit/XXXXXXX`
4. The XXXXXXX is your datasource UID
5. Tell me this UID so I can create a working JSON
