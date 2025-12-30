"""
Step-to-code-path mapping package.

Signal-driven mapping of BDD steps to Page Objects, methods, and file paths.
Used for impact analysis, coverage tracking, migration parity, and diagnostics.
"""
from .models import (
    StepSignal,
    CodeReference,
    StepMapping,
    SignalType
)
from .registry import StepSignalRegistry
from .resolver import StepMappingResolver
from .persistence import (
    MappingPersistence,
    save_mapping,
    load_mapping,
    save_registry,
    load_registry,
)

__all__ = [
    'StepSignal',
    'CodeReference',
    'StepMapping',
    'SignalType',
    'StepSignalRegistry',
    'StepMappingResolver',
    'MappingPersistence',
    'save_mapping',
    'load_mapping',
    'save_registry',
    'load_registry',
]
