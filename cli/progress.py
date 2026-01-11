"""
Progress tracking and visual feedback for CrossBridge CLI.

Uses Rich progress bars and live updates for real-time feedback.
"""

import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.live import Live
from rich.table import Table
from typing import Optional, Dict

from core.orchestration import MigrationStatus

console = Console()


class MigrationProgressTracker:
    """
    Track migration progress with Rich UI components.
    
    Example:
        tracker = MigrationProgressTracker()
        orchestrator.run(request, progress_callback=tracker.update)
    """
    
    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style="green", finished_style="bright_green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        )
        self.task: Optional[TaskID] = None
        # Map each status to its progress range (start%, end%)
        self.status_map: Dict[MigrationStatus, tuple] = {
            MigrationStatus.NOT_STARTED: (0, 0),
            MigrationStatus.VALIDATING: (0, 15),
            MigrationStatus.ANALYZING: (15, 30),
            MigrationStatus.TRANSFORMING: (30, 85),
            MigrationStatus.GENERATING: (85, 95),
            MigrationStatus.COMMITTING: (95, 100),
            MigrationStatus.COMPLETED: (100, 100),
            MigrationStatus.FAILED: (0, 0)
        }
        self.live: Optional[Live] = None
        self.current_phase: Optional[MigrationStatus] = None
    
    def start(self, total: int = 100):
        """Start progress tracking."""
        self.task = self.progress.add_task(
            "Initializing migration...",
            total=total
        )
        self.live = Live(self.progress, console=console)
        self.live.start()
    
    def update(self, message: str, status: MigrationStatus, completed_percent: Optional[float] = None):
        """
        Update progress based on migration status.
        
        Args:
            message: Progress message
            status: Current migration status
            completed_percent: Optional specific completion percentage (0-100)
        """
        # Start live progress if not started
        if self.live is None:
            self.start()
        
        # Update task
        if self.task is not None:
            # If specific percentage provided, use it
            if completed_percent is not None:
                # Check if this is a phase completion (end of range)
                status_range = self.status_map.get(status, (0, 0))
                if completed_percent == status_range[1] and completed_percent > 0:
                    # This is a phase completion - show 100% to indicate phase is done
                    self.progress.update(
                        self.task,
                        description=f"✓ {message}",  # Add checkmark for completed phases
                        completed=100  # Always show 100% for phase completion
                    )
                    time.sleep(0.5)  # Brief pause to show 100% completion
                    # Print a separator line after major phase completion
                    console.print("[dim]" + "─" * 70 + "[/dim]")
                    return
                else:
                    # Regular progress update within or between phases
                    completed = completed_percent
            else:
                # Otherwise, use the start of the status range
                status_range = self.status_map.get(status, (0, 0))
                completed = status_range[0]  # Start of range
            
            self.progress.update(
                self.task,
                description=message,
                completed=completed
            )
            self.current_phase = status
        
        # Stop on completion or failure (but don't print failure message here)
        if status in (MigrationStatus.COMPLETED, MigrationStatus.FAILED):
            self.stop()
            # Don't print the failure message - let the main error handler do that
            if status == MigrationStatus.FAILED:
                return  # Suppress "Migration failed" message here
    
    def stop(self):
        """Stop progress tracking."""
        if self.live:
            self.live.stop()
            self.live = None
    
    def __enter__(self):
        """Context manager support."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.stop()


def show_file_discovery_progress(file_type: str, count: int):
    """Show inline progress for file discovery."""
    console.print(f"  [dim]Found {count} {file_type} files...[/dim]", end="\r")


def show_transformation_progress(current: int, total: int, filename: str):
    """Show inline progress for file transformation."""
    console.print(
        f"  [dim]Transforming {current}/{total}: {filename}[/dim]",
        end="\r"
    )
