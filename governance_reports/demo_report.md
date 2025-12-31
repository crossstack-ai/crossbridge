# Demo Compliance Report

**Generated:** 2025-12-31 17:32:57

## Summary

- **Policies Evaluated:** 3
- **Total Rules Checked:** 7
- **Total Violations:** 5
- **Overall Compliance Rate:** 28.6%

## Violations by Severity

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| ERROR | 2 |
| WARNING | 2 |

## Compliance by Category

| Category | Compliance Rate | Violations |
|----------|----------------|------------|
| quality | 33.3% | 2 |
| security | 50.0% | 1 |
| testing | 0.0% | 2 |

## Policy Details

### ❌ Test Coverage Policy

**ID:** `test-coverage`  
**Category:** testing  
**Compliance Rate:** 0.0%  
**Rules Checked:** 2  
**Rules Passed:** 0  

**Violations:**

- 🟠 **[ERROR]** Minimum Coverage Threshold
  - **Description:** Test coverage must be at least 80%
  - **Status:** open

- 🔴 **[CRITICAL]** Critical Paths Must Be Tested
  - **Description:** All critical code paths must have tests
  - **Status:** open

### ❌ Test Quality Policy

**ID:** `test-quality`  
**Category:** quality  
**Compliance Rate:** 33.3%  
**Rules Checked:** 3  
**Rules Passed:** 1  

**Violations:**

- 🟡 **[WARNING]** No Flaky Tests
  - **Description:** Tests must not be flaky (pass rate < 95%)
  - **Status:** open

- 🟡 **[WARNING]** Test Execution Time Limit
  - **Description:** Tests should complete within reasonable time
  - **Status:** open

### ❌ Security Policy

**ID:** `security`  
**Category:** security  
**Compliance Rate:** 50.0%  
**Rules Checked:** 2  
**Rules Passed:** 1  

**Violations:**

- 🟠 **[ERROR]** Secure Test Data Handling
  - **Description:** Sensitive test data must be encrypted or masked
  - **Status:** open
