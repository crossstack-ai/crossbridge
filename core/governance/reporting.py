"""
Compliance reporting for policy governance.

Generates reports on policy compliance status and violations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path
import json

from .policy import Policy, PolicySeverity, PolicyCategory
from .engine import PolicyResult, PolicyViolation, ViolationStatus


@dataclass
class ComplianceReport:
    """
    Compliance report for policy evaluations.
    
    Attributes:
        title: Report title
        generated_at: When report was generated
        policies_evaluated: Number of policies evaluated
        total_rules_checked: Total rules checked
        total_violations: Total violations found
        compliance_rate: Overall compliance rate
        results: Policy evaluation results
        summary_by_severity: Violations grouped by severity
        summary_by_category: Compliance grouped by category
    """
    title: str
    generated_at: datetime = field(default_factory=datetime.now)
    policies_evaluated: int = 0
    total_rules_checked: int = 0
    total_violations: int = 0
    compliance_rate: float = 100.0
    results: List[PolicyResult] = field(default_factory=list)
    summary_by_severity: Dict[str, int] = field(default_factory=dict)
    summary_by_category: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            'title': self.title,
            'generated_at': self.generated_at.isoformat(),
            'summary': {
                'policies_evaluated': self.policies_evaluated,
                'total_rules_checked': self.total_rules_checked,
                'total_violations': self.total_violations,
                'compliance_rate': self.compliance_rate,
            },
            'violations_by_severity': self.summary_by_severity,
            'compliance_by_category': self.summary_by_category,
            'policy_results': [
                {
                    'policy_id': r.policy.id,
                    'policy_name': r.policy.name,
                    'compliant': r.compliant,
                    'checked_rules': r.checked_rules,
                    'passed_rules': r.passed_rules,
                    'compliance_rate': r.compliance_rate,
                    'violations': [
                        {
                            'rule_id': v.rule_id,
                            'rule_name': v.rule_name,
                            'severity': v.severity.value,
                            'description': v.description,
                            'status': v.status.value,
                        }
                        for v in r.violations
                    ]
                }
                for r in self.results
            ]
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            f"# {self.title}",
            "",
            f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            "",
            f"- **Policies Evaluated:** {self.policies_evaluated}",
            f"- **Total Rules Checked:** {self.total_rules_checked}",
            f"- **Total Violations:** {self.total_violations}",
            f"- **Overall Compliance Rate:** {self.compliance_rate:.1f}%",
            "",
        ]
        
        # Violations by severity
        if self.summary_by_severity:
            lines.extend([
                "## Violations by Severity",
                "",
                "| Severity | Count |",
                "|----------|-------|",
            ])
            for severity, count in sorted(self.summary_by_severity.items()):
                lines.append(f"| {severity.upper()} | {count} |")
            lines.append("")
        
        # Compliance by category
        if self.summary_by_category:
            lines.extend([
                "## Compliance by Category",
                "",
                "| Category | Compliance Rate | Violations |",
                "|----------|----------------|------------|",
            ])
            for category, data in sorted(self.summary_by_category.items()):
                rate = data.get('compliance_rate', 0)
                violations = data.get('violations', 0)
                lines.append(f"| {category} | {rate:.1f}% | {violations} |")
            lines.append("")
        
        # Policy details
        lines.extend([
            "## Policy Details",
            "",
        ])
        
        for result in self.results:
            status_icon = "✅" if result.compliant else "❌"
            lines.extend([
                f"### {status_icon} {result.policy.name}",
                "",
                f"**ID:** `{result.policy.id}`  ",
                f"**Category:** {result.policy.category.value}  ",
                f"**Compliance Rate:** {result.compliance_rate:.1f}%  ",
                f"**Rules Checked:** {result.checked_rules}  ",
                f"**Rules Passed:** {result.passed_rules}  ",
                "",
            ])
            
            if result.violations:
                lines.extend([
                    "**Violations:**",
                    "",
                ])
                for v in result.violations:
                    severity_emoji = {
                        'critical': '🔴',
                        'error': '🟠',
                        'warning': '🟡',
                        'info': '🔵'
                    }.get(v.severity.value, '⚪')
                    
                    lines.extend([
                        f"- {severity_emoji} **[{v.severity.value.upper()}]** {v.rule_name}",
                        f"  - **Description:** {v.description}",
                        f"  - **Status:** {v.status.value}",
                    ])
                    if v.remediation:
                        lines.append(f"  - **Remediation:** {v.remediation}")
                    lines.append("")
            else:
                lines.extend([
                    "✅ All rules passed",
                    "",
                ])
        
        return "\n".join(lines)
    
    def save(self, output_path: Path, format: str = 'json') -> None:
        """
        Save report to file.
        
        Args:
            output_path: Path to save report
            format: Output format ('json' or 'markdown')
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            content = self.to_json()
        elif format == 'markdown':
            content = self.to_markdown()
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        output_path.write_text(content, encoding='utf-8')


class ComplianceReporter:
    """Generate compliance reports from policy evaluation results."""
    
    @staticmethod
    def generate_report(
        results: List[PolicyResult],
        title: str = "Policy Compliance Report"
    ) -> ComplianceReport:
        """
        Generate a compliance report from policy results.
        
        Args:
            results: List of policy evaluation results
            title: Report title
            
        Returns:
            ComplianceReport
        """
        report = ComplianceReport(title=title)
        report.results = results
        report.policies_evaluated = len(results)
        
        # Calculate statistics
        total_rules = 0
        total_passed = 0
        violations_by_severity = {}
        compliance_by_category = {}
        
        for result in results:
            total_rules += result.checked_rules
            total_passed += result.passed_rules
            
            # Count violations by severity
            for violation in result.violations:
                severity_key = violation.severity.value
                violations_by_severity[severity_key] = violations_by_severity.get(severity_key, 0) + 1
            
            # Track compliance by category
            category_key = result.policy.category.value
            if category_key not in compliance_by_category:
                compliance_by_category[category_key] = {
                    'total_rules': 0,
                    'passed_rules': 0,
                    'violations': 0,
                    'compliance_rate': 0.0
                }
            
            cat_data = compliance_by_category[category_key]
            cat_data['total_rules'] += result.checked_rules
            cat_data['passed_rules'] += result.passed_rules
            cat_data['violations'] += len(result.violations)
        
        # Calculate compliance rates by category
        for category, data in compliance_by_category.items():
            if data['total_rules'] > 0:
                data['compliance_rate'] = (data['passed_rules'] / data['total_rules']) * 100
        
        report.total_rules_checked = total_rules
        report.total_violations = sum(violations_by_severity.values())
        report.compliance_rate = (total_passed / total_rules * 100) if total_rules > 0 else 100.0
        report.summary_by_severity = violations_by_severity
        report.summary_by_category = compliance_by_category
        
        return report
    
    @staticmethod
    def generate_violation_summary(violations: List[PolicyViolation]) -> Dict[str, Any]:
        """
        Generate summary statistics for violations.
        
        Args:
            violations: List of violations
            
        Returns:
            Dictionary with violation statistics
        """
        summary = {
            'total': len(violations),
            'by_severity': {},
            'by_status': {},
            'by_policy': {},
            'critical_count': 0,
            'open_count': 0,
        }
        
        for v in violations:
            # By severity
            sev_key = v.severity.value
            summary['by_severity'][sev_key] = summary['by_severity'].get(sev_key, 0) + 1
            
            # By status
            status_key = v.status.value
            summary['by_status'][status_key] = summary['by_status'].get(status_key, 0) + 1
            
            # By policy
            policy_key = v.policy_id
            summary['by_policy'][policy_key] = summary['by_policy'].get(policy_key, 0) + 1
            
            # Counters
            if v.severity == PolicySeverity.CRITICAL:
                summary['critical_count'] += 1
            if v.status == ViolationStatus.OPEN:
                summary['open_count'] += 1
        
        return summary
    
    @staticmethod
    def export_violations_csv(violations: List[PolicyViolation], output_path: Path) -> None:
        """
        Export violations to CSV file.
        
        Args:
            violations: List of violations to export
            output_path: Path to save CSV file
        """
        import csv
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with output_path.open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Timestamp', 'Policy ID', 'Rule ID', 'Rule Name',
                'Severity', 'Status', 'Description'
            ])
            
            for v in violations:
                writer.writerow([
                    v.timestamp.isoformat(),
                    v.policy_id,
                    v.rule_id,
                    v.rule_name,
                    v.severity.value,
                    v.status.value,
                    v.description
                ])
