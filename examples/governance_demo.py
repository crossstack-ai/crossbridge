"""
Policy Governance Framework Demo.

Demonstrates the complete policy governance framework capabilities.
"""

from pathlib import Path
from core.governance import (
    Policy,
    PolicyRule,
    PolicySeverity,
    PolicyCategory,
    PolicyEngine,
    ComplianceReporter,
    AuditTrail,
    AuditLogger,
    PolicyChecker,
)
from core.governance.policy import (
    create_test_coverage_policy,
    create_test_quality_policy,
    create_security_policy,
    create_documentation_policy,
)


def demo_basic_policy():
    """Demonstrate basic policy creation and evaluation."""
    print("=" * 60)
    print("Demo 1: Basic Policy Creation and Evaluation")
    print("=" * 60)
    
    # Create a custom policy
    policy = Policy(
        id="demo-policy",
        name="Demo Quality Policy",
        description="Demonstrates policy creation",
        category=PolicyCategory.QUALITY
    )
    
    # Add rules
    policy.add_rule(PolicyRule(
        id="coverage-rule",
        name="Minimum Coverage",
        description="Test coverage must be at least 75%",
        severity=PolicySeverity.ERROR,
        check_function=lambda ctx: ctx.get('coverage', 0) >= 75
    ))
    
    policy.add_rule(PolicyRule(
        id="test-count-rule",
        name="Minimum Test Count",
        description="Must have at least 10 tests",
        severity=PolicySeverity.WARNING,
        check_function=lambda ctx: ctx.get('test_count', 0) >= 10
    ))
    
    # Create engine and evaluate
    engine = PolicyEngine()
    engine.register_policy(policy)
    
    # Test with passing context
    print("\n✅ Testing with compliant data:")
    context_pass = {'coverage': 85, 'test_count': 15}
    result = engine.evaluate_policy(policy, context_pass)
    print(f"  Compliant: {result.compliant}")
    print(f"  Compliance Rate: {result.compliance_rate:.1f}%")
    print(f"  Violations: {len(result.violations)}")
    
    # Test with failing context
    print("\n❌ Testing with non-compliant data:")
    context_fail = {'coverage': 60, 'test_count': 5}
    result = engine.evaluate_policy(policy, context_fail)
    print(f"  Compliant: {result.compliant}")
    print(f"  Compliance Rate: {result.compliance_rate:.1f}%")
    print(f"  Violations: {len(result.violations)}")
    for v in result.violations:
        print(f"    - [{v.severity.value.upper()}] {v.rule_name}")


def demo_predefined_policies():
    """Demonstrate using predefined policy templates."""
    print("\n" + "=" * 60)
    print("Demo 2: Predefined Policy Templates")
    print("=" * 60)
    
    engine = PolicyEngine()
    
    # Register all predefined policies
    engine.register_policy(create_test_coverage_policy())
    engine.register_policy(create_test_quality_policy())
    engine.register_policy(create_security_policy())
    engine.register_policy(create_documentation_policy())
    
    # Create realistic test context
    context = {
        'coverage': 85.0,
        'untested_critical_paths': [],
        'flaky_tests': [],
        'avg_execution_time': 120,
        'tests_without_assertions': [],
        'hardcoded_secrets': [],
        'unprotected_sensitive_data': [],
        'tests_without_descriptions': ['test_something'],
        'has_readme': True,
    }
    
    # Evaluate all policies
    results = engine.evaluate_all(context)
    
    print(f"\n📊 Evaluated {len(results)} policies:")
    for result in results:
        status = "✅" if result.compliant else "❌"
        print(f"  {status} {result.policy.name}: {result.compliance_rate:.1f}% compliant")
        if not result.compliant:
            for v in result.violations:
                print(f"      - {v.rule_name}")


def demo_compliance_reporting():
    """Demonstrate compliance report generation."""
    print("\n" + "=" * 60)
    print("Demo 3: Compliance Reporting")
    print("=" * 60)
    
    engine = PolicyEngine()
    engine.register_policy(create_test_coverage_policy())
    engine.register_policy(create_test_quality_policy())
    engine.register_policy(create_security_policy())
    
    context = {
        'coverage': 75.0,
        'untested_critical_paths': ['critical_path_1'],
        'flaky_tests': ['test_flaky'],
        'avg_execution_time': 350,
        'tests_without_assertions': [],
        'hardcoded_secrets': [],
        'unprotected_sensitive_data': ['user_password'],
    }
    
    # Evaluate
    results = engine.evaluate_all(context)
    
    # Generate report
    reporter = ComplianceReporter()
    report = reporter.generate_report(results, title="Demo Compliance Report")
    
    print(f"\n📄 Report Summary:")
    print(f"  Total Policies: {report.policies_evaluated}")
    print(f"  Total Rules Checked: {report.total_rules_checked}")
    print(f"  Total Violations: {report.total_violations}")
    print(f"  Overall Compliance: {report.compliance_rate:.1f}%")
    
    print(f"\n📊 Violations by Severity:")
    for severity, count in sorted(report.summary_by_severity.items()):
        print(f"  {severity.upper()}: {count}")
    
    # Save report
    output_dir = Path("governance_reports")
    output_dir.mkdir(exist_ok=True)
    
    report.save(output_dir / "demo_report.json", format="json")
    report.save(output_dir / "demo_report.md", format="markdown")
    
    print(f"\n💾 Reports saved to {output_dir}/")


def demo_automated_checks():
    """Demonstrate automated policy checks."""
    print("\n" + "=" * 60)
    print("Demo 4: Automated Policy Checks")
    print("=" * 60)
    
    # Coverage check
    print("\n🔍 Coverage Check:")
    result = PolicyChecker.check_test_coverage(
        coverage_data={
            'coverage_percent': 82.5,
            'covered_lines': 825,
            'total_lines': 1000
        },
        threshold=80.0
    )
    print(f"  {result.message}")
    print(f"  Passed: {result.passed}")
    
    # Flaky tests check
    print("\n🔍 Flaky Tests Check:")
    test_results = [
        {'test_name': 'test_a', 'passed': True},
        {'test_name': 'test_a', 'passed': True},
        {'test_name': 'test_a', 'passed': False},  # Flaky
        {'test_name': 'test_b', 'passed': True},
        {'test_name': 'test_b', 'passed': True},
    ]
    result = PolicyChecker.check_flaky_tests(test_results, threshold=0.95)
    print(f"  {result.message}")
    print(f"  Passed: {result.passed}")
    if not result.passed:
        for flaky in result.details['flaky_tests']:
            print(f"    - {flaky['test']}: {flaky['pass_rate']:.1%} pass rate")
    
    # Execution time check
    print("\n🔍 Execution Time Check:")
    execution_times = {
        'test_fast': 30.0,
        'test_medium': 150.0,
        'test_slow': 400.0,  # Too slow
    }
    result = PolicyChecker.check_test_execution_time(execution_times, max_time=300.0)
    print(f"  {result.message}")
    print(f"  Passed: {result.passed}")
    if not result.passed:
        for slow in result.details['slow_tests']:
            print(f"    - {slow['test']}: {slow['duration']:.1f}s (max: {slow['max_allowed']}s)")


def demo_audit_trail():
    """Demonstrate audit trail functionality."""
    print("\n" + "=" * 60)
    print("Demo 5: Audit Trail")
    print("=" * 60)
    
    # Create audit trail
    audit_path = Path("governance_audit.json")
    audit = AuditTrail(storage_path=audit_path)
    logger = AuditLogger(audit)
    
    # Create and evaluate policies
    engine = PolicyEngine()
    policy = create_test_coverage_policy()
    engine.register_policy(policy)
    
    context = {'coverage': 70, 'untested_critical_paths': ['critical_1']}
    result = engine.evaluate_policy(policy, context)
    
    # Log events
    logger.audit_trail.log_policy_evaluation(
        policy_id=policy.id,
        result=result,
        actor="demo_user"
    )
    
    for violation in result.violations:
        logger.audit_trail.log_violation(violation, actor="demo_user")
    
    logger.log_compliance_check(
        policies_checked=1,
        violations_found=len(result.violations),
        compliance_rate=result.compliance_rate,
        actor="demo_user"
    )
    
    # Query audit trail
    print(f"\n📝 Audit Trail:")
    recent = audit.get_recent_entries(5)
    for entry in recent:
        print(f"  [{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
              f"{entry.event_type.value} by {entry.actor}")
        if entry.details:
            print(f"    Details: {entry.details}")
    
    print(f"\n💾 Audit trail saved to {audit_path}")


def demo_strict_enforcement():
    """Demonstrate strict policy enforcement."""
    print("\n" + "=" * 60)
    print("Demo 6: Strict Policy Enforcement")
    print("=" * 60)
    
    # Create engine in strict mode
    engine = PolicyEngine(strict_mode=True)
    engine.register_policy(create_security_policy())
    
    # Test with critical violation
    print("\n❌ Testing with CRITICAL security violation:")
    context_critical = {
        'hardcoded_secrets': ['api_key=abc123'],
        'unprotected_sensitive_data': [],
    }
    
    can_proceed = engine.enforce_policies(context_critical)
    print(f"  Can proceed with execution: {can_proceed}")
    
    # Test without critical violations
    print("\n✅ Testing without CRITICAL violations:")
    context_safe = {
        'hardcoded_secrets': [],
        'unprotected_sensitive_data': ['some_data'],  # ERROR level, not CRITICAL
    }
    
    can_proceed = engine.enforce_policies(context_safe)
    print(f"  Can proceed with execution: {can_proceed}")


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("Policy Governance Framework - Complete Demo")
    print("=" * 60)
    
    demo_basic_policy()
    demo_predefined_policies()
    demo_compliance_reporting()
    demo_automated_checks()
    demo_audit_trail()
    demo_strict_enforcement()
    
    print("\n" + "=" * 60)
    print("✅ Demo Complete!")
    print("=" * 60)
    print("\nGenerated artifacts:")
    print("  - governance_reports/demo_report.json")
    print("  - governance_reports/demo_report.md")
    print("  - governance_audit.json")


if __name__ == "__main__":
    main()
