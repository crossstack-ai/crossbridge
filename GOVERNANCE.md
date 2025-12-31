# CrossBridge Governance

## Project Governance Model

CrossBridge uses a transparent governance model focused on quality, security, and compliance for test automation.

## Policy Framework

CrossBridge includes a comprehensive **Policy Governance Framework** for automated policy enforcement and compliance monitoring.

### Framework Location
- **Implementation**: `core/governance/`
- **Documentation**: [core/governance/README.md](core/governance/README.md)
- **Demo**: [examples/governance_demo.py](examples/governance_demo.py)

### Capabilities

✅ **Policy Definition Framework**
- Structured policy and rule definitions
- Multiple severity levels (INFO, WARNING, ERROR, CRITICAL)
- Policy categories (Testing, Security, Quality, Performance, Documentation, Architecture, Compliance)
- Pre-built policy templates

✅ **Policy Engine**
- Automated policy evaluation
- Strict enforcement mode for critical violations
- Context-based rule checking
- Evaluation history tracking

✅ **Automated Policy Checks**
- Test coverage validation
- Security checks (hardcoded secrets, sensitive data)
- Test quality checks (assertions, flaky tests, execution time)
- Documentation requirements
- Naming conventions

✅ **Compliance Reporting**
- JSON and Markdown report formats
- CSV export for violations
- Severity-based violation grouping
- Category-based compliance metrics
- Remediation suggestions

✅ **Audit Trail**
- Complete history of policy-related actions
- Persistent audit log storage
- Query capabilities (by policy, event type, time range, actor)
- Event tracking for evaluations, violations, and enforcement actions

### Quick Start

```python
from core.governance import PolicyEngine, ComplianceReporter
from core.governance.policy import create_test_coverage_policy

# Create and register policies
engine = PolicyEngine(strict_mode=False)
engine.register_policy(create_test_coverage_policy())

# Evaluate policies
context = {'coverage': 85.0}
results = engine.evaluate_all(context)

# Generate compliance report
reporter = ComplianceReporter()
report = reporter.generate_report(results)
report.save(Path("compliance.md"), format="markdown")
```

See [core/governance/README.md](core/governance/README.md) for complete documentation.

## Decision Making Process

### Technical Decisions
1. **Proposal**: Create an issue or RFC describing the change
2. **Discussion**: Community discussion and feedback
3. **Policy Check**: Validate against governance policies
4. **Review**: Code review and automated checks
5. **Approval**: Maintainer approval required
6. **Merge**: After all checks pass and policies are satisfied

### Policy Enforcement
- **Automated**: Policy engine runs on all changes
- **Blocking**: Critical policy violations block merges
- **Reporting**: Compliance reports generated regularly
- **Audit**: All policy decisions tracked in audit trail

## Roles and Responsibilities

### Maintainers
- Enforce governance policies
- Review and approve changes
- Manage policy configurations
- Review compliance reports

### Contributors
- Follow governance policies
- Address policy violations
- Participate in policy discussions

### Policy Administrator
- Configure and update policies
- Review audit trails
- Generate compliance reports
- Manage policy exceptions

## Community Guidelines

### Code Quality Standards
- All code must pass policy checks
- Test coverage requirements enforced
- Security policies must be satisfied
- Documentation requirements apply

### Compliance Requirements
- Regular compliance audits
- Violation remediation tracking
- Policy adherence monitoring
- Audit trail maintenance

## Policy Templates

### Built-in Policies
- **Test Coverage Policy**: Ensures adequate test coverage (≥80%)
- **Test Quality Policy**: Enforces test quality standards
- **Security Policy**: Validates security best practices
- **Documentation Policy**: Ensures documentation requirements

### Custom Policies
Organizations can create custom policies for their specific needs. See [policy.py](core/governance/policy.py) for examples.

## Reporting and Auditing

### Compliance Reports
- Generated automatically on schedule
- Available in JSON, Markdown, and CSV formats
- Tracked in version control
- Distributed to stakeholders

### Audit Trail
- All policy actions logged
- Persistent storage of audit events
- Queryable by policy, time, actor
- Exportable for external analysis

## Contact

For governance questions or policy discussions, please create an issue with the `governance` label
