# Policy Governance Framework

A comprehensive framework for defining, enforcing, and monitoring policies in test automation.

## Overview

The Policy Governance Framework provides:

- **Policy Definition**: Structured way to define policies and rules
- **Policy Engine**: Automated evaluation and enforcement
- **Automated Checks**: Ready-to-use checks for common scenarios
- **Compliance Reporting**: Detailed reports on policy compliance
- **Audit Trail**: Complete history of policy-related actions

## Quick Start

### 1. Define a Policy

```python
from core.governance import Policy, PolicyRule, PolicySeverity, PolicyCategory

# Create a custom policy
policy = Policy(
    id="my-policy",
    name="My Test Policy",
    description="Ensures tests meet quality standards",
    category=PolicyCategory.QUALITY
)

# Add rules
policy.add_rule(PolicyRule(
    id="rule-1",
    name="Test Coverage",
    description="Coverage must be >= 80%",
    severity=PolicySeverity.ERROR,
    check_function=lambda ctx: ctx.get('coverage', 0) >= 80
))
```

### 2. Use Policy Engine

```python
from core.governance import PolicyEngine

# Create engine
engine = PolicyEngine(strict_mode=True)

# Register policies
engine.register_policy(policy)

# Evaluate
context = {'coverage': 75}
result = engine.evaluate_policy(policy, context)

print(f"Compliant: {result.compliant}")
print(f"Violations: {len(result.violations)}")
```

### 3. Generate Reports

```python
from core.governance import ComplianceReporter

# Evaluate all policies
results = engine.evaluate_all(context)

# Generate report
reporter = ComplianceReporter()
report = reporter.generate_report(results, title="Q4 2025 Compliance")

# Save as markdown
report.save(Path("compliance_report.md"), format="markdown")
```

### 4. Maintain Audit Trail

```python
from core.governance import AuditTrail, AuditLogger

# Create audit trail
audit = AuditTrail(storage_path=Path("audit.json"))
logger = AuditLogger(audit)

# Log events
logger.log_compliance_check(
    policies_checked=5,
    violations_found=2,
    compliance_rate=85.5
)

# Query history
recent = audit.get_recent_entries(10)
```

## Built-in Policies

The framework includes pre-configured policies:

### Test Coverage Policy
```python
from core.governance.policy import create_test_coverage_policy

policy = create_test_coverage_policy()
```

### Test Quality Policy
```python
from core.governance.policy import create_test_quality_policy

policy = create_test_quality_policy()
```

### Security Policy
```python
from core.governance.policy import create_security_policy

policy = create_security_policy()
```

### Documentation Policy
```python
from core.governance.policy import create_documentation_policy

policy = create_documentation_policy()
```

## Automated Checks

Use `PolicyChecker` for common checks:

```python
from core.governance import PolicyChecker

# Check test coverage
result = PolicyChecker.check_test_coverage(
    coverage_data={'coverage_percent': 85.0},
    threshold=80.0
)

# Check for hardcoded secrets
result = PolicyChecker.check_no_hardcoded_secrets(
    file_path=Path("test_api.py")
)

# Check test naming
result = PolicyChecker.check_test_naming_convention(
    test_files=[Path("test_user.py"), Path("test_auth.py")]
)
```

## Policy Severity Levels

- **CRITICAL**: Blocks execution, requires immediate action
- **ERROR**: Major violation, should be fixed soon
- **WARNING**: Minor issue, should be addressed
- **INFO**: Informational, no action required

## Compliance Reporting

Reports include:

- Overall compliance rate
- Violations by severity
- Violations by policy category
- Detailed policy results
- Remediation suggestions

Export formats:
- JSON (machine-readable)
- Markdown (human-readable)
- CSV (for violations)

## Audit Trail

The audit trail tracks:

- Policy evaluations
- Policy changes (create, update, delete)
- Violation detection
- Violation status changes (acknowledged, resolved, ignored)
- Compliance checks
- Enforcement actions

Query capabilities:
- Filter by policy ID
- Filter by event type
- Filter by time range
- Filter by actor

## Integration Example

```python
from pathlib import Path
from core.governance import (
    PolicyEngine,
    ComplianceReporter,
    AuditTrail,
    AuditLogger,
)
from core.governance.policy import (
    create_test_coverage_policy,
    create_test_quality_policy,
    create_security_policy,
)

# Setup
engine = PolicyEngine(strict_mode=False)
audit = AuditTrail(storage_path=Path("audit.json"))
logger = AuditLogger(audit)

# Register policies
engine.register_policy(create_test_coverage_policy())
engine.register_policy(create_test_quality_policy())
engine.register_policy(create_security_policy())

# Evaluate
context = {
    'coverage': 85.0,
    'flaky_tests': [],
    'hardcoded_secrets': [],
    'tests_without_assertions': ['test_empty'],
}

results = engine.evaluate_all(context)

# Log to audit
for result in results:
    logger.audit_trail.log_policy_evaluation(
        policy_id=result.policy.id,
        result=result
    )

# Generate report
reporter = ComplianceReporter()
report = reporter.generate_report(results)
report.save(Path("reports/compliance.md"), format="markdown")

# Check if execution should proceed
can_proceed = engine.enforce_policies(context)
if not can_proceed:
    print("❌ Execution blocked due to critical violations")
    logger.log_enforcement_action(
        policy_id="security",
        action="block_execution",
        reason="Critical security violations detected"
    )
else:
    print("✅ All policies passed, execution can proceed")
```

## Best Practices

1. **Start Simple**: Begin with a few important policies
2. **Set Appropriate Severity**: Not everything needs to be CRITICAL
3. **Provide Context**: Include helpful context in rule checks
4. **Regular Reviews**: Periodically review and update policies
5. **Audit Everything**: Maintain comprehensive audit trail
6. **Report Regularly**: Generate compliance reports for stakeholders
7. **Iterate**: Refine policies based on real-world usage

## Architecture

```
core/governance/
├── __init__.py          # Public API
├── policy.py            # Policy definitions
├── engine.py            # Policy evaluation engine
├── checks.py            # Automated policy checks
├── reporting.py         # Compliance reporting
└── audit.py             # Audit trail
```

## Extending the Framework

### Custom Policy Rules

```python
def check_custom_rule(context):
    # Your custom logic
    return context.get('my_metric') > threshold

policy.add_rule(PolicyRule(
    id="custom-rule",
    name="Custom Check",
    description="My custom validation",
    severity=PolicySeverity.WARNING,
    check_function=check_custom_rule
))
```

### Custom Checks

```python
class CustomChecker:
    @staticmethod
    def my_check(data) -> CheckResult:
        passed = # your logic
        return CheckResult(
            passed=passed,
            message="Check description",
            details={}
        )
```

## Status

✅ **IMPLEMENTED** - Full production-ready implementation

- Policy definition framework
- Policy engine with evaluation
- Automated policy checks
- Compliance reporting (JSON, Markdown, CSV)
- Audit trail with persistence
- Pre-built policy templates
- Comprehensive documentation
