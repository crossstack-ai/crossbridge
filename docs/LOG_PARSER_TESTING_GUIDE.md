# Testing Log Parser Feature with Sidecar

## Overview

The generic log parser endpoint supports all major test frameworks:
- **Robot Framework** - Parse output.xml for detailed test analysis
- **Cypress** - Parse JSON results with test statistics
- **Playwright** - Parse trace files for actions and performance
- **Behave** - Parse JSON results for BDD scenarios
- **Java** - Parse step definitions for Cucumber

## Quick Test

### 1. Restart Sidecar (to load new endpoint)

On your Linux server:
```bash
cd /path/to/crossbridge
git pull origin dev
docker compose -f docker-compose-remote-sidecar.yml restart
```

### 2. Run Test Script

On Windows (Git Bash):
```bash
cd /d/Future-work2/crossbridge
export SIDECAR_HOST=10.60.75.145
export SIDECAR_PORT=8765

./scripts/test_log_parser.sh
```

The script will:
- ✓ Check sidecar health
- ✓ Verify log parsing feature is enabled
- ✓ Auto-detect Robot output.xml files
- ✓ Parse and show detailed statistics
- ✓ Display failed tests and slowest tests
- ✓ Validate error handling

### 3. Manual Test with Your Robot Results

```bash
# After running your Robot tests
curl -X POST http://10.60.75.145:8765/parse/robot \
     -H "Content-Type: application/xml" \
     --data-binary @cloudconsole-restapi-automation/output.xml | jq
```

## Expected Response Format

### Robot Framework
```json
{
  "framework": "robot",
  "suite": {
    "name": "Tests.APISuites",
    "status": "PASS",
    "total_tests": 25,
    "passed_tests": 24,
    "failed_tests": 1,
    "elapsed_ms": 45230
  },
  "statistics": {
    "total": 25,
    "passed": 24,
    "failed": 1,
    "pass_rate": 96.0
  },
  "failed_keywords": [
    {
      "name": "Should Be Equal",
      "library": "BuiltIn",
      "error": "Expected 'expected' but got 'actual'",
      "messages": ["..."]
    }
  ],
  "slowest_tests": [
    {
      "name": "Test Backup Process",
      "suite": "Tests.APISuites.Backup",
      "elapsed_ms": 8234,
      "status": "PASS"
    }
  ],
  "slowest_keywords": [
    {
      "name": "Wait Until Keyword Succeeds",
      "library": "BuiltIn",
      "elapsed_ms": 5123
    }
  ]
}
```

## Use Cases

### 1. Post-Execution Analysis
After test execution, upload results for detailed analysis:
```bash
./crossbridge-run robot tests/
curl -X POST http://10.60.75.145:8765/parse/robot --data-binary @output.xml | jq
```

### 2. CI/CD Integration
Add to Jenkins/GitLab CI to parse results:
```groovy
stage('Analyze Results') {
    steps {
        sh '''
            curl -X POST ${SIDECAR_URL}/parse/robot \
                 --data-binary @output.xml \
                 -o analysis.json
        '''
        archiveArtifacts 'analysis.json'
    }
}
```

### 3. Historical Analysis
Parse old test results stored in archives:
```bash
# Parse archived results
find ./archives -name "output.xml" | while read file; do
    echo "Parsing: $file"
    curl -X POST http://10.60.75.145:8765/parse/robot \
         --data-binary @"$file" | jq '.statistics'
done
```

### 4. Failure Investigation
Quick analysis of failed tests:
```bash
curl -X POST http://10.60.75.145:8765/parse/robot \
     --data-binary @output.xml | \
     jq '.failed_keywords[] | {name, error}'
```

### 5. Performance Monitoring
Track slowest tests over time:
```bash
curl -X POST http://10.60.75.145:8765/parse/robot \
     --data-binary @output.xml | \
     jq '.slowest_tests[:5]'
```

## Supported Frameworks

| Framework | Endpoint | Input Format | Key Features |
|-----------|----------|--------------|--------------|
| Robot | `/parse/robot` | output.xml | Keywords, suites, hierarchies |
| Cypress | `/parse/cypress` | results.json | Test stats, failures, insights |
| Playwright | `/parse/playwright` | trace.json | Actions, network, console |
| Behave | `/parse/behave` | results.json | Features, scenarios, steps |
| Java | `/parse/java` | Steps.java | Step definitions, bindings |

## Troubleshooting

### Sidecar Not Responding
```bash
curl http://10.60.75.145:8765/health
# If fails, check sidecar logs:
docker logs crossbridge-sidecar
```

### Feature Not Available
```bash
curl http://10.60.75.145:8765/config | jq '.features'
# Should show: "log_parsing": true
```

### Parse Error
```bash
# Check if file is valid XML/JSON
cat output.xml | head -5
# Verify content-type header
curl -v -X POST http://10.60.75.145:8765/parse/robot --data-binary @output.xml
```

## Benefits

1. **No Code Changes** - Parse results without modifying tests
2. **Centralized Analysis** - All frameworks use same API
3. **Rich Insights** - Statistics, failures, performance metrics
4. **CI/CD Ready** - Easy integration with pipelines
5. **Historical Data** - Parse archived results anytime
6. **Framework Agnostic** - Consistent interface across all frameworks

## Next Steps

1. Run test script: `./scripts/test_log_parser.sh`
2. Parse your test results with appropriate endpoint
3. Integrate into CI/CD pipeline
4. Set up automated analysis workflows
