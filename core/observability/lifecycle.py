"""
CrossBridge Lifecycle and Mode Management

DESIGN CONTRACT:
- CrossBridge never owns test execution
- CrossBridge never regenerates test code post-migration
- CrossBridge operates as an observer via hooks

This module enforces the lifecycle state machine and prevents architectural drift.
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CrossBridgeMode(Enum):
    """
    CrossBridge operational modes.
    
    MIGRATION: Initial test translation (source → target framework)
    OBSERVER: Post-migration continuous intelligence via hooks
    OPTIMIZATION: AI-driven suggestions and analysis (non-invasive)
    """
    MIGRATION = "migration"
    OBSERVER = "observer"
    OPTIMIZATION = "optimization"


@dataclass
class LifecycleState:
    """Current lifecycle state of a project"""
    project_id: str
    mode: CrossBridgeMode
    migration_completed_at: Optional[datetime] = None
    observer_enabled: bool = False
    hooks_registered: bool = False
    last_event_at: Optional[datetime] = None
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LifecycleManager:
    """
    Manages CrossBridge lifecycle state transitions.
    
    Enforces:
    - No test execution control in any mode
    - No code regeneration post-migration
    - Observer mode is permanent after migration
    """
    
    def __init__(self, db_connection=None):
        self.db_connection = db_connection
        self._current_state: Optional[LifecycleState] = None
    
    def get_state(self, project_id: str) -> LifecycleState:
        """Get current lifecycle state for project"""
        if not self.db_connection:
            # Default state when no persistence
            return LifecycleState(
                project_id=project_id,
                mode=CrossBridgeMode.MIGRATION,
                observer_enabled=False
            )
        
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT 
                project_id,
                mode,
                migration_completed_at,
                observer_enabled,
                hooks_registered,
                last_event_at,
                metadata
            FROM migration_state
            WHERE project_id = %s
        """, (project_id,))
        
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            # First time - create default state
            return LifecycleState(
                project_id=project_id,
                mode=CrossBridgeMode.MIGRATION,
                observer_enabled=False
            )
        
        return LifecycleState(
            project_id=row[0],
            mode=CrossBridgeMode(row[1]),
            migration_completed_at=row[2],
            observer_enabled=row[3],
            hooks_registered=row[4],
            last_event_at=row[5],
            metadata=row[6] or {}
        )
    
    def complete_migration(self, project_id: str, metadata: dict = None):
        """
        Mark migration as complete and transition to observer mode.
        
        This is a ONE-WAY transition. Once migration is complete,
        CrossBridge switches to permanent observer mode.
        
        Args:
            project_id: Unique project identifier
            metadata: Migration summary (test count, framework, etc.)
        """
        if not self.db_connection:
            logger.warning("No database connection - cannot persist migration state")
            return
        
        logger.info(f"Completing migration for project: {project_id}")
        
        cursor = self.db_connection.cursor()
        cursor.execute("""
            INSERT INTO migration_state (
                project_id,
                mode,
                migration_completed_at,
                observer_enabled,
                hooks_registered,
                metadata
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (project_id) 
            DO UPDATE SET
                mode = EXCLUDED.mode,
                migration_completed_at = EXCLUDED.migration_completed_at,
                observer_enabled = EXCLUDED.observer_enabled,
                metadata = EXCLUDED.metadata
        """, (
            project_id,
            CrossBridgeMode.OBSERVER.value,
            datetime.utcnow(),
            True,
            False,
            metadata
        ))
        self.db_connection.commit()
        cursor.close()
        
        logger.info(f"Project {project_id} transitioned to OBSERVER mode")
    
    def enable_hooks(self, project_id: str):
        """Mark hooks as registered for this project"""
        if not self.db_connection:
            return
        
        cursor = self.db_connection.cursor()
        cursor.execute("""
            UPDATE migration_state 
            SET hooks_registered = true
            WHERE project_id = %s
        """, (project_id,))
        self.db_connection.commit()
        cursor.close()
        
        logger.info(f"Hooks enabled for project: {project_id}")
    
    def update_last_event(self, project_id: str):
        """Update timestamp of last received event"""
        if not self.db_connection:
            return
        
        cursor = self.db_connection.cursor()
        cursor.execute("""
            UPDATE migration_state 
            SET last_event_at = %s
            WHERE project_id = %s
        """, (datetime.utcnow(), project_id))
        self.db_connection.commit()
        cursor.close()
    
    def ensure_observer_mode(self, project_id: str):
        """
        Guard function to ensure operation is valid in current mode.
        
        Raises:
            RuntimeError: If attempting observer actions in migration mode
        """
        state = self.get_state(project_id)
        
        if state.mode != CrossBridgeMode.OBSERVER:
            raise RuntimeError(
                f"Observer actions not allowed in {state.mode.value} mode. "
                f"Complete migration first using lifecycle.complete_migration()"
            )
    
    def ensure_migration_mode(self, project_id: str):
        """
        Guard function for migration-only operations.
        
        Raises:
            RuntimeError: If attempting migration after completion
        """
        state = self.get_state(project_id)
        
        if state.mode != CrossBridgeMode.MIGRATION:
            raise RuntimeError(
                f"Migration actions not allowed in {state.mode.value} mode. "
                f"Migration was completed at {state.migration_completed_at}"
            )
    
    def can_remigrate(self, project_id: str) -> bool:
        """
        Check if remigration is allowed.
        
        Remigration should be VERY rare and require explicit opt-in.
        Normal workflow is: migration → observer (permanent)
        """
        state = self.get_state(project_id)
        
        # Only allow remigration if explicitly disabled
        return state.metadata.get('allow_remigration', False)


def ensure_observer_only():
    """
    Runtime guard for observer-only operations.
    
    Use this in event ingestion, coverage updates, and AI analyzers
    to prevent execution in migration mode.
    """
    # This is a simplified version - in production, check global config
    import os
    mode = os.getenv('CROSSBRIDGE_MODE', 'observer')
    
    if mode != CrossBridgeMode.OBSERVER.value:
        raise RuntimeError(
            f"Observer operations not allowed in {mode} mode. "
            f"Set CROSSBRIDGE_MODE=observer to enable continuous intelligence."
        )
