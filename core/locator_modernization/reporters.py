"""
Modernization Report Generators

Human-readable reports, risk heatmaps, and change logs for Phase 3.
"""

from typing import List, Dict
import json
from datetime import datetime
from .models import (
    ModernizationSuggestion,
    ModernizationRecommendation,
    RiskLevel,
    SuggestionStatus
)


class ModernizationReporter:
    """
    Generates human-readable modernization reports
    
    Produces CLI-friendly output and exportable artifacts
    """
    
    def __init__(self):
        self.report_timestamp = datetime.now()
    
    def generate_summary_report(
        self,
        recommendations: List[ModernizationRecommendation],
        summary_stats: Dict
    ) -> str:
        """Generate overall modernization summary"""
        
        lines = []
        lines.append("\n" + "="*80)
        lines.append("╔════════════════════════════════════════════════════════════════════════════╗")
        lines.append("║          Phase 3: AI-Assisted Locator Modernization Report               ║")
        lines.append("╠════════════════════════════════════════════════════════════════════════════╣")
        lines.append(f"║  Generated: {self.report_timestamp.strftime('%Y-%m-%d %H:%M:%S')}                                              ║")
        lines.append("╚════════════════════════════════════════════════════════════════════════════╝")
        lines.append("")
        
        # Overall statistics
        lines.append("📊 ANALYSIS SUMMARY")
        lines.append("-" * 80)
        lines.append(f"  Total Locators Analyzed:    {summary_stats.get('total_locators_analyzed', 0)}")
        lines.append(f"  High-Risk Locators:         {summary_stats.get('high_risk_locators', 0)} 🔴")
        lines.append(f"  Page Objects Analyzed:      {summary_stats.get('page_objects_analyzed', 0)}")
        lines.append(f"  High-Priority Pages:        {summary_stats.get('high_priority_pages', 0)}")
        lines.append("")
        lines.append(f"  Total Suggestions:          {summary_stats.get('total_suggestions', 0)}")
        lines.append(f"  ├─ Pending Review:          {summary_stats.get('pending_review', 0)}")
        lines.append(f"  ├─ Approved:                {summary_stats.get('approved', 0)}")
        lines.append(f"  └─ Applied:                 {summary_stats.get('applied', 0)}")
        lines.append("")
        lines.append(f"  AI Analysis:                {'✅ ENABLED' if summary_stats.get('ai_enabled') else '❌ DISABLED'}")
        lines.append("")
        
        # Page Object prioritization
        if recommendations:
            lines.append("🎯 PAGE OBJECT MODERNIZATION PRIORITIES")
            lines.append("-" * 80)
            
            # Sort by priority
            priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            sorted_recs = sorted(
                recommendations,
                key=lambda r: (priority_order.get(r.modernization_priority, 4), -r.high_risk_locators)
            )
            
            for rec in sorted_recs[:10]:  # Top 10
                priority_emoji = {
                    'critical': '🔥',
                    'high': '🔴',
                    'medium': '🟡',
                    'low': '🟢'
                }
                emoji = priority_emoji.get(rec.modernization_priority, '⚪')
                
                lines.append(f"  {emoji} {rec.page_object}")
                lines.append(f"     Priority: {rec.modernization_priority.upper()}")
                lines.append(f"     High Risk: {rec.high_risk_locators}, Medium: {rec.medium_risk_locators}, Low: {rec.low_risk_locators}")
                lines.append(f"     Suggestions: {len(rec.suggestions)}")
                lines.append("")
        
        lines.append("="*80)
        
        return "\n".join(lines)
    
    def generate_suggestion_review_report(
        self,
        suggestions: List[ModernizationSuggestion]
    ) -> str:
        """Generate report for reviewing suggestions"""
        
        lines = []
        lines.append("\n" + "="*80)
        lines.append("📋 MODERNIZATION SUGGESTIONS FOR REVIEW")
        lines.append("="*80)
        lines.append("")
        
        if not suggestions:
            lines.append("  ✅ No pending suggestions - all reviewed!")
            lines.append("")
            return "\n".join(lines)
        
        # Group by Page Object
        by_page = {}
        for suggestion in suggestions:
            if suggestion.page_object not in by_page:
                by_page[suggestion.page_object] = []
            by_page[suggestion.page_object].append(suggestion)
        
        for page_object, page_suggestions in by_page.items():
            lines.append(f"\n🔹 Page Object: {page_object}")
            lines.append("-" * 80)
            
            for i, suggestion in enumerate(page_suggestions, 1):
                lines.append(suggestion.format_cli_display())
                
                # Add action prompt
                lines.append("\n📝 Actions:")
                lines.append("   [a] Approve    [r] Reject    [d] Defer (review later)    [s] Skip")
                lines.append("")
        
        lines.append("="*80)
        
        return "\n".join(lines)
    
    def generate_change_log(
        self,
        applied_suggestions: List[ModernizationSuggestion]
    ) -> str:
        """Generate change log of applied suggestions"""
        
        lines = []
        lines.append("\n" + "="*80)
        lines.append("📝 MODERNIZATION CHANGE LOG")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("="*80)
        lines.append("")
        
        if not applied_suggestions:
            lines.append("  No changes applied yet.")
            lines.append("")
            return "\n".join(lines)
        
        # Group by Page Object
        by_page = {}
        for suggestion in applied_suggestions:
            if suggestion.page_object not in by_page:
                by_page[suggestion.page_object] = []
            by_page[suggestion.page_object].append(suggestion)
        
        for page_object, page_suggestions in by_page.items():
            lines.append(f"\n📄 {page_object}")
            lines.append("-" * 80)
            
            for suggestion in page_suggestions:
                lines.append(f"  Locator: {suggestion.locator_name}")
                lines.append(f"  Before:  {suggestion.current_strategy}={suggestion.current_value}")
                lines.append(f"  After:   {suggestion.suggested_value}")
                lines.append(f"  Reason:  {suggestion.reason}")
                lines.append(f"  Confidence: {suggestion.confidence:.2f}")
                lines.append(f"  Applied: {suggestion.reviewed_at.strftime('%Y-%m-%d %H:%M:%S') if suggestion.reviewed_at else 'N/A'}")
                lines.append("")
        
        lines.append("="*80)
        
        return "\n".join(lines)
    
    def export_to_json(
        self,
        recommendations: List[ModernizationRecommendation],
        output_file: str
    ):
        """Export recommendations to JSON"""
        
        data = {
            'generated_at': self.report_timestamp.isoformat(),
            'phase': 'Phase 3: AI-Assisted Locator Modernization',
            'recommendations': [rec.to_dict() for rec in recommendations]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)


class RiskHeatmapGenerator:
    """
    Generates risk heatmap visualizations
    
    Shows locator risk distribution across Page Objects
    """
    
    def generate_text_heatmap(
        self,
        recommendations: List[ModernizationRecommendation]
    ) -> str:
        """Generate ASCII art risk heatmap"""
        
        lines = []
        lines.append("\n" + "="*80)
        lines.append("🔥 RISK HEATMAP")
        lines.append("="*80)
        lines.append("")
        
        if not recommendations:
            lines.append("  No data available.")
            return "\n".join(lines)
        
        # Sort by risk
        sorted_recs = sorted(
            recommendations,
            key=lambda r: r.high_risk_locators,
            reverse=True
        )
        
        lines.append("Page Object                          High  Med   Low   Priority")
        lines.append("-" * 80)
        
        for rec in sorted_recs:
            # Create visual bar
            total = max(rec.high_risk_locators + rec.medium_risk_locators + rec.low_risk_locators, 1)
            high_bar = '█' * min(int((rec.high_risk_locators / total) * 10), 10)
            med_bar = '▓' * min(int((rec.medium_risk_locators / total) * 10), 10)
            low_bar = '░' * min(int((rec.low_risk_locators / total) * 10), 10)
            
            priority_indicator = {
                'critical': '🔥',
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }.get(rec.modernization_priority, '⚪')
            
            name = rec.page_object[:35].ljust(35)
            lines.append(f"{name}  {rec.high_risk_locators:3d}   {rec.medium_risk_locators:3d}   {rec.low_risk_locators:3d}   {priority_indicator}")
            lines.append(f"                                     {high_bar}{med_bar}{low_bar}")
            lines.append("")
        
        lines.append("="*80)
        lines.append("Legend: 🔥 Critical  🔴 High  🟡 Medium  🟢 Low")
        lines.append("="*80)
        
        return "\n".join(lines)
    
    def generate_risk_matrix(
        self,
        recommendations: List[ModernizationRecommendation]
    ) -> Dict:
        """Generate risk matrix data"""
        
        matrix = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }
        
        for rec in recommendations:
            matrix[rec.modernization_priority].append({
                'page_object': rec.page_object,
                'high_risk_count': rec.high_risk_locators,
                'medium_risk_count': rec.medium_risk_locators,
                'low_risk_count': rec.low_risk_locators,
                'total_suggestions': len(rec.suggestions)
            })
        
        return matrix


def generate_modernization_report(
    recommendations: List[ModernizationRecommendation],
    summary_stats: Dict,
    output_dir: str = "."
) -> Dict[str, str]:
    """
    Generate complete Phase 3 modernization report
    
    Returns:
        Dict with report file paths
    """
    reporter = ModernizationReporter()
    heatmap_gen = RiskHeatmapGenerator()
    
    # Generate reports
    summary = reporter.generate_summary_report(recommendations, summary_stats)
    
    pending_suggestions = []
    for rec in recommendations:
        pending_suggestions.extend(rec.get_pending_suggestions())
    
    suggestion_review = reporter.generate_suggestion_review_report(pending_suggestions)
    
    applied_suggestions = []
    for rec in recommendations:
        applied_suggestions.extend([s for s in rec.suggestions if s.status == SuggestionStatus.APPLIED])
    
    change_log = reporter.generate_change_log(applied_suggestions)
    
    heatmap = heatmap_gen.generate_text_heatmap(recommendations)
    
    # Save to files
    import os
    
    summary_file = os.path.join(output_dir, "modernization_summary.txt")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    review_file = os.path.join(output_dir, "suggestions_for_review.txt")
    with open(review_file, 'w', encoding='utf-8') as f:
        f.write(suggestion_review)
    
    changelog_file = os.path.join(output_dir, "change_log.txt")
    with open(changelog_file, 'w', encoding='utf-8') as f:
        f.write(change_log)
    
    heatmap_file = os.path.join(output_dir, "risk_heatmap.txt")
    with open(heatmap_file, 'w', encoding='utf-8') as f:
        f.write(heatmap)
    
    json_file = os.path.join(output_dir, "modernization_report.json")
    reporter.export_to_json(recommendations, json_file)
    
    return {
        'summary': summary_file,
        'review': review_file,
        'changelog': changelog_file,
        'heatmap': heatmap_file,
        'json': json_file
    }
