"""
API Change Intelligence Orchestrator

Main entry point that coordinates all components
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging
import time

from .spec_collector import SpecCollector
from .oasdiff_engine import OASDiffEngine
from .change_normalizer import ChangeNormalizer
from .rules_engine import RulesEngine
from .ai_engine import AIEngine
from .models.api_change import DiffResult
from .doc_generator.markdown import MarkdownGenerator
from .impact_analyzer import ImpactAnalyzer
from .ci_integration import CIIntegration
from .alerting.alert_manager import AlertManager

logger = logging.getLogger(__name__)


class APIChangeOrchestrator:
    """Main orchestrator for API Change Intelligence"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize orchestrator
        
        Args:
            config: API change configuration from crossbridge.yml
        """
        self.config = config
        self.enabled = config.get("enabled", False)
        
        if not self.enabled:
            logger.info("API Change Intelligence is disabled")
            return
        
        logger.info("Initializing API Change Intelligence...")
        
        # Initialize components
        self.spec_collector = SpecCollector(config.get("spec_source", {}))
        self.oasdiff_engine = OASDiffEngine()
        self.normalizer = ChangeNormalizer()
        
        # Intelligence engines
        intelligence_config = config.get("intelligence", {})
        self.rules_engine = RulesEngine(intelligence_config.get("rules", {}))
        self.ai_engine = AIEngine(intelligence_config.get("ai", {}))
        
        # Impact analyzer
        impact_config = config.get("impact_analysis", {})
        self.impact_analyzer = ImpactAnalyzer(impact_config) if impact_config.get("enabled", True) else None
        
        # CI Integration
        ci_config = config.get("ci_integration", {})
        self.ci_integration = CIIntegration(ci_config) if ci_config.get("enabled", False) else None
        
        # Alert manager
        alert_config = config.get("alerts", {})
        self.alert_manager = AlertManager(alert_config) if alert_config.get("enabled", False) else None
        
        # Documentation
        doc_config = config.get("documentation", {})
        if doc_config.get("enabled", True):
            markdown_config = doc_config.get("formats", {}).get("markdown", {})
            if markdown_config.get("enabled", True):
                self.markdown_generator = MarkdownGenerator(doc_config)
            else:
                self.markdown_generator = None
        else:
            self.markdown_generator = None
        
        logger.info("API Change Intelligence initialized")
    
    def run(self) -> DiffResult:
        """
        Run complete API change detection workflow
        
        Returns:
            DiffResult with all changes and statistics
        """
        if not self.enabled:
            logger.warning("API Change Intelligence is disabled")
            result = DiffResult()
            result.status = "disabled"
            return result
        
        logger.info("=" * 60)
        logger.info("API Change Intelligence - Starting Analysis")
        logger.info("=" * 60)
        
        start_time = time.time()
        result = DiffResult(started_at=datetime.utcnow())
        
        try:
            # Step 1: Collect specs
            logger.info("\n[1/6] Collecting OpenAPI specifications...")
            current_spec, previous_spec, current_version, previous_version = self.spec_collector.collect_specs()
            
            result.old_spec_version = previous_version
            result.new_spec_version = current_version
            result.old_spec_source = str(self.config.get("spec_source", {}).get("previous", ""))
            result.new_spec_source = str(self.config.get("spec_source", {}).get("current", ""))
            
            logger.info(f"  Previous version: {previous_version}")
            logger.info(f"  Current version: {current_version}")
            
            # Step 2: Run oasdiff
            logger.info("\n[2/6] Running oasdiff comparison...")
            diff_result = self.oasdiff_engine.diff(previous_spec, current_spec)
            breaking_changes = self.oasdiff_engine.diff_breaking(previous_spec, current_spec)
            
            logger.info(f"  Found {len(breaking_changes)} breaking changes")
            
            # Step 3: Normalize changes
            logger.info("\n[3/6] Normalizing changes...")
            api_name = self.spec_collector.get_spec_info(current_spec).get("title", "API")
            api_version = current_version
            
            changes = self.normalizer.normalize(
                diff_result,
                breaking_changes,
                api_name,
                api_version
            )
            
            logger.info(f"  Normalized {len(changes)} changes")
            
            # Step 4: Apply rules engine
            logger.info("\n[4/6] Applying rule-based intelligence...")
            changes = self.rules_engine.analyze(changes)
            
            # Step 5: Apply AI engine (optional)
            logger.info("\n[5/6] Applying AI intelligence...")
            ai_config = self.config.get("intelligence", {}).get("ai", {})
            if ai_config.get("enabled", False):
                changes = self.ai_engine.analyze(changes)
                ai_usage = self.ai_engine.get_token_usage()
                result.ai_enabled = True
                result.ai_tokens_used = ai_usage["tokens_used"]
                logger.info(f"  AI tokens used: {result.ai_tokens_used}")
            else:
                logger.info("  AI intelligence disabled")
            
            # Step 5.5: Analyze impact (optional)
            if self.impact_analyzer:
                logger.info("\n[5.5/6] Analyzing test impact...")
                from pathlib import Path
                workspace_root = Path.cwd()
                impacts = self.impact_analyzer.analyze_impact(changes, workspace_root)
                result.test_impacts = impacts
                logger.info(f"  Found {len(impacts)} potentially affected tests")
                
                # Get test recommendations
                recommendations = self.impact_analyzer.get_test_selection_recommendations(impacts)
                result.test_recommendations = recommendations
                logger.info(f"  Must run: {len(recommendations['must_run'])} tests")
                logger.info(f"  Should run: {len(recommendations['should_run'])} tests")
            
            # Step 5.6: Send alerts (optional)
            if self.alert_manager:
                logger.info("\n[5.6/6] Sending alerts...")
                import asyncio
                # Check if there are breaking changes or high-risk changes
                critical_changes = [c for c in changes if c.breaking or (c.risk_level and c.risk_level.value == 'high')]
                if critical_changes:
                    asyncio.run(self.alert_manager.send_bulk_alerts(critical_changes, summary_mode=True))
                    logger.info(f"  Sent alerts for {len(critical_changes)} critical changes")
            
            # Step 6: Generate documentation
            logger.info("\n[6/6] Generating documentation...")
            result.changes = changes
            result.calculate_statistics()
            
            if self.markdown_generator:
                self.markdown_generator.generate(result)
                logger.info("  Markdown documentation generated")
            
            # Complete result
            result.completed_at = datetime.utcnow()
            result.duration_ms = int((time.time() - start_time) * 1000)
            result.status = "completed"
            
            # Print summary
            logger.info("\n" + "=" * 60)
            logger.info("Analysis Complete!")
            logger.info("=" * 60)
            logger.info(f"Total Changes: {result.total_changes}")
            logger.info(f"Breaking Changes: {result.breaking_changes}")
            logger.info(f"High Risk Changes: {result.high_risk_changes}")
            logger.info(f"Added Endpoints: {result.added_endpoints}")
            logger.info(f"Modified Endpoints: {result.modified_endpoints}")
            logger.info(f"Removed Endpoints: {result.removed_endpoints}")
            logger.info(f"Duration: {result.duration_ms}ms")
            logger.info("=" * 60)
            
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            result.status = "failed"
            result.error_message = str(e)
            result.completed_at = datetime.utcnow()
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result
    
    def run_and_store(self, session) -> DiffResult:
        """
        Run analysis and store results in database
        
        Args:
            session: SQLAlchemy session
        
        Returns:
            DiffResult
        """
        from .storage.repository import APIChangeRepository
        
        result = self.run()
        
        if result.status == "completed" and session:
            try:
                repo = APIChangeRepository(session)
                
                # Save run
                run_id = repo.create_diff_run(result)
                logger.info(f"Saved run to database: {run_id}")
                
                # Save changes
                if result.changes:
                    repo.save_changes(result.changes, run_id)
                    logger.info(f"Saved {len(result.changes)} changes to database")
                
            except Exception as e:
                logger.error(f"Failed to store results: {e}")
        
        return result
