"""
CLI Commands for AI Transformation Review

Provides commands for:
- Listing transformations
- Approving/rejecting transformations
- Viewing diffs
- Rolling back transformations
- Audit trail inspection
"""

import click
from pathlib import Path
from typing import Optional

from core.ai.transformation_service import AITransformationService
from core.ai.transformation_validation import TransformationStatus
from core.logging import get_logger, LogCategory, configure_logging, LogLevel

logger = get_logger(__name__, category=LogCategory.AI)


@click.group(name='ai-transform')
def ai_transform():
    """AI Transformation validation and review commands"""
    pass


@ai_transform.command(name='list')
@click.option('--status', type=click.Choice(['pending', 'approved', 'rejected', 'applied', 'rolled_back']), 
              help='Filter by status')
@click.option('--needs-review', is_flag=True, help='Show only transformations needing review')
@click.option('--storage-dir', type=click.Path(), help='Transformation storage directory')
def list_transformations(status: Optional[str], needs_review: bool, storage_dir: Optional[str]):
    """List AI transformations"""
    try:
        service = AITransformationService(
            storage_dir=Path(storage_dir) if storage_dir else None
        )
        
        status_filter = TransformationStatus(status) if status else None
        transformations = service.list_transformations(
            status=status_filter,
            requires_review=True if needs_review else None
        )
        
        if not transformations:
            click.echo("No transformations found")
            return
        
        click.echo(f"\n{'ID':<15} {'Operation':<12} {'Type':<10} {'Confidence':<12} {'Status':<15} {'Review?':<8}")
        click.echo("-" * 85)
        
        for t in transformations:
            confidence_str = f"{t.confidence:.2f} ({t.confidence_level.value})"
            review_str = "Yes" if t.requires_review else "No"
            
            click.echo(
                f"{t.id:<15} {t.operation:<12} {t.artifact_type:<10} "
                f"{confidence_str:<12} {t.status.value:<15} {review_str:<8}"
            )
        
        click.echo(f"\nTotal: {len(transformations)} transformations")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@ai_transform.command(name='show')
@click.argument('transformation_id')
@click.option('--storage-dir', type=click.Path(), help='Transformation storage directory')
@click.option('--show-diff', is_flag=True, help='Show full diff')
def show_transformation(transformation_id: str, storage_dir: Optional[str], show_diff: bool):
    """Show transformation details"""
    try:
        service = AITransformationService(
            storage_dir=Path(storage_dir) if storage_dir else None
        )
        
        transformation = service.get_transformation(transformation_id)
        if not transformation:
            click.echo(f"Transformation {transformation_id} not found", err=True)
            raise click.Abort()
        
        click.echo("\n" + "=" * 80)
        click.echo(f"Transformation: {transformation.id}")
        click.echo("=" * 80)
        
        click.echo(f"\nOperation:      {transformation.operation}")
        click.echo(f"Artifact Type:  {transformation.artifact_type}")
        click.echo(f"Artifact Path:  {transformation.artifact_path}")
        click.echo(f"Status:         {transformation.status.value}")
        click.echo(f"Confidence:     {transformation.confidence:.3f} ({transformation.confidence_level.value})")
        click.echo(f"Requires Review: {transformation.requires_review}")
        click.echo(f"Model Used:     {transformation.model_used}")
        click.echo(f"Created:        {transformation.created_at}")
        
        if transformation.review:
            click.echo(f"\nReview:")
            click.echo(f"  Reviewer:     {transformation.review.reviewer}")
            click.echo(f"  Decision:     {transformation.review.decision}")
            click.echo(f"  Comments:     {transformation.review.comments}")
            click.echo(f"  Reviewed At:  {transformation.review.reviewed_at}")
        
        if transformation.confidence_signals:
            signals = transformation.confidence_signals
            click.echo(f"\nConfidence Signals:")
            click.echo(f"  Model Confidence:    {signals.model_confidence:.3f}")
            click.echo(f"  Similarity:          {signals.similarity_to_existing:.3f}")
            click.echo(f"  Rule Violations:     {signals.rule_violations}")
            click.echo(f"  Diff Size:           {signals.diff_size} lines")
            click.echo(f"  Syntax Valid:        {signals.syntax_valid}")
            click.echo(f"  Coverage Maintained: {signals.test_coverage_maintained}")
        
        if show_diff:
            click.echo("\n" + "-" * 80)
            click.echo("DIFF:")
            click.echo("-" * 80)
            click.echo(transformation.diff)
        else:
            diff_lines = len(transformation.diff.splitlines())
            click.echo(f"\nDiff: {diff_lines} lines (use --show-diff to view)")
        
        click.echo("\n" + "=" * 80)
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@ai_transform.command(name='approve')
@click.argument('transformation_id')
@click.option('--reviewer', required=True, help='Reviewer name/email')
@click.option('--comments', default='', help='Review comments')
@click.option('--storage-dir', type=click.Path(), help='Transformation storage directory')
@click.option('--apply', is_flag=True, help='Apply transformation immediately after approval')
def approve_transformation(transformation_id: str, reviewer: str, comments: str, 
                          storage_dir: Optional[str], apply: bool):
    """Approve an AI transformation"""
    try:
        service = AITransformationService(
            storage_dir=Path(storage_dir) if storage_dir else None
        )
        
        transformation = service.approve(transformation_id, reviewer, comments)
        
        click.echo(f"✓ Transformation {transformation_id} approved by {reviewer}")
        click.echo(f"  Confidence: {transformation.confidence:.3f}")
        click.echo(f"  Artifact: {transformation.artifact_path}")
        
        if apply:
            transformation = service.apply(transformation_id)
            click.echo(f"\n✓ Transformation applied to {transformation.artifact_path}")
        else:
            click.echo(f"\nTo apply: crossbridge ai-transform apply {transformation_id}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@ai_transform.command(name='reject')
@click.argument('transformation_id')
@click.option('--reviewer', required=True, help='Reviewer name/email')
@click.option('--reason', required=True, help='Rejection reason')
@click.option('--storage-dir', type=click.Path(), help='Transformation storage directory')
def reject_transformation(transformation_id: str, reviewer: str, reason: str, 
                         storage_dir: Optional[str]):
    """Reject an AI transformation"""
    try:
        service = AITransformationService(
            storage_dir=Path(storage_dir) if storage_dir else None
        )
        
        transformation = service.reject(transformation_id, reviewer, reason)
        
        click.echo(f"✗ Transformation {transformation_id} rejected by {reviewer}")
        click.echo(f"  Reason: {reason}")
        click.echo(f"  Confidence was: {transformation.confidence:.3f}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@ai_transform.command(name='apply')
@click.argument('transformation_id')
@click.option('--storage-dir', type=click.Path(), help='Transformation storage directory')
def apply_transformation(transformation_id: str, storage_dir: Optional[str]):
    """Apply an approved transformation"""
    try:
        service = AITransformationService(
            storage_dir=Path(storage_dir) if storage_dir else None
        )
        
        transformation = service.apply(transformation_id)
        
        click.echo(f"✓ Transformation {transformation_id} applied")
        click.echo(f"  File: {transformation.artifact_path}")
        click.echo(f"  Applied at: {transformation.applied_at}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@ai_transform.command(name='rollback')
@click.argument('transformation_id')
@click.option('--storage-dir', type=click.Path(), help='Transformation storage directory')
@click.confirmation_option(prompt='Are you sure you want to rollback this transformation?')
def rollback_transformation(transformation_id: str, storage_dir: Optional[str]):
    """Rollback an applied transformation"""
    try:
        service = AITransformationService(
            storage_dir=Path(storage_dir) if storage_dir else None
        )
        
        transformation = service.rollback(transformation_id)
        
        click.echo(f"↶ Transformation {transformation_id} rolled back")
        click.echo(f"  File: {transformation.artifact_path}")
        click.echo(f"  Restored to previous state")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@ai_transform.command(name='audit')
@click.argument('transformation_id')
@click.option('--storage-dir', type=click.Path(), help='Transformation storage directory')
def show_audit_trail(transformation_id: str, storage_dir: Optional[str]):
    """Show audit trail for transformation"""
    try:
        service = AITransformationService(
            storage_dir=Path(storage_dir) if storage_dir else None
        )
        
        audit = service.get_audit_trail(transformation_id)
        
        click.echo("\n" + "=" * 80)
        click.echo(f"Audit Trail: {transformation_id}")
        click.echo("=" * 80)
        
        click.echo(f"\nActor:          {audit['actor']}")
        click.echo(f"Model:          {audit['model']}")
        click.echo(f"Prompt Hash:    {audit['prompt_hash']}")
        click.echo(f"Operation:      {audit['operation']}")
        click.echo(f"Artifact Type:  {audit['artifact_type']}")
        click.echo(f"Artifact Path:  {audit['artifact_path']}")
        click.echo(f"Confidence:     {audit['confidence']:.3f} ({audit['confidence_level']})")
        click.echo(f"Status:         {audit['status']}")
        click.echo(f"Requires Review: {audit['requires_review']}")
        click.echo(f"Created:        {audit['created_at']}")
        
        if audit['review']:
            click.echo(f"\nReview:")
            click.echo(f"  Reviewer:   {audit['review']['reviewer']}")
            click.echo(f"  Decision:   {audit['review']['decision']}")
            click.echo(f"  Comments:   {audit['review']['comments']}")
            click.echo(f"  Reviewed:   {audit['review']['reviewed_at']}")
        
        if audit['applied_at']:
            click.echo(f"\nApplied:        {audit['applied_at']}")
        
        if audit['rolled_back_at']:
            click.echo(f"Rolled Back:    {audit['rolled_back_at']}")
        
        if audit['metadata']:
            click.echo(f"\nMetadata:")
            for key, value in audit['metadata'].items():
                click.echo(f"  {key}: {value}")
        
        click.echo("\n" + "=" * 80)
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@ai_transform.command(name='stats')
@click.option('--storage-dir', type=click.Path(), help='Transformation storage directory')
def show_statistics(storage_dir: Optional[str]):
    """Show transformation statistics"""
    try:
        service = AITransformationService(
            storage_dir=Path(storage_dir) if storage_dir else None
        )
        
        stats = service.get_statistics()
        
        click.echo("\n" + "=" * 80)
        click.echo("AI Transformation Statistics")
        click.echo("=" * 80)
        
        click.echo(f"\nTotal Transformations: {stats['total_transformations']}")
        
        click.echo(f"\nBy Status:")
        for status, count in stats['by_status'].items():
            click.echo(f"  {status.capitalize():<12} {count:>5}")
        
        click.echo(f"\nBy Confidence:")
        for level, count in stats['by_confidence'].items():
            click.echo(f"  {level.capitalize():<12} {count:>5}")
        
        click.echo(f"\nRates:")
        click.echo(f"  Average Confidence: {stats['average_confidence']:.3f}")
        click.echo(f"  Approval Rate:      {stats['approval_rate']:.1%}")
        click.echo(f"  Rejection Rate:     {stats['rejection_rate']:.1%}")
        
        click.echo("\n" + "=" * 80)
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
