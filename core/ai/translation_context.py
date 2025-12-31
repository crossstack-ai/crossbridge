"""
Test Translation Context Management.

Provides specialized context management for test framework migration/translation
tasks, including source/target framework tracking, pattern libraries, and
translation history.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.ai.models import AIExecutionContext, TaskType


@dataclass
class FrameworkInfo:
    """Information about a test framework."""
    name: str
    version: Optional[str] = None
    language: str = "python"
    conventions: Dict[str, Any] = field(default_factory=dict)
    patterns: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "language": self.language,
            "conventions": self.conventions,
            "patterns": self.patterns,
        }


@dataclass
class TranslationPattern:
    """A reusable translation pattern."""
    source_pattern: str
    target_pattern: str
    description: str
    source_framework: str
    target_framework: str
    confidence: float = 1.0
    examples: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class TranslationContext:
    """
    Specialized context for test translation tasks.
    
    Extends AIExecutionContext with translation-specific information
    like source/target frameworks, translation patterns, and history.
    """
    # Base execution context
    execution_context: AIExecutionContext
    
    # Framework information
    source_framework: FrameworkInfo
    target_framework: FrameworkInfo
    
    # Translation configuration
    preserve_comments: bool = True
    preserve_structure: bool = True
    generate_migration_notes: bool = True
    apply_target_conventions: bool = True
    
    # Pattern library
    custom_patterns: List[TranslationPattern] = field(default_factory=list)
    learned_patterns: List[TranslationPattern] = field(default_factory=list)
    
    # Translation history (for learning)
    previous_translations: List[Dict[str, Any]] = field(default_factory=list)
    
    # File context
    source_file_path: Optional[Path] = None
    target_file_path: Optional[Path] = None
    project_root: Optional[Path] = None
    
    # Dependencies
    source_dependencies: List[str] = field(default_factory=list)
    target_dependencies: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    translation_id: Optional[str] = None
    
    def add_pattern(self, pattern: TranslationPattern):
        """Add a custom translation pattern."""
        self.custom_patterns.append(pattern)
    
    def record_translation(
        self,
        source_code: str,
        translated_code: str,
        success: bool,
        warnings: List[str] = None,
    ):
        """Record a translation for learning."""
        self.previous_translations.append({
            "source": source_code,
            "target": translated_code,
            "success": success,
            "warnings": warnings or [],
            "timestamp": datetime.now().isoformat(),
        })
    
    def get_relevant_patterns(self) -> List[TranslationPattern]:
        """Get all relevant patterns for current translation."""
        return self.custom_patterns + self.learned_patterns
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for AI prompt context."""
        return {
            "source_framework": self.source_framework.to_dict(),
            "target_framework": self.target_framework.to_dict(),
            "preserve_comments": self.preserve_comments,
            "preserve_structure": self.preserve_structure,
            "generate_migration_notes": self.generate_migration_notes,
            "apply_target_conventions": self.apply_target_conventions,
            "custom_patterns": [
                {
                    "source": p.source_pattern,
                    "target": p.target_pattern,
                    "description": p.description,
                }
                for p in self.custom_patterns
            ],
            "source_file": str(self.source_file_path) if self.source_file_path else None,
            "target_file": str(self.target_file_path) if self.target_file_path else None,
            "source_dependencies": self.source_dependencies,
            "target_dependencies": self.target_dependencies,
            "translation_history_count": len(self.previous_translations),
        }


class TranslationContextManager:
    """
    Manages translation contexts and pattern libraries.
    
    Provides utilities for creating, storing, and retrieving
    translation contexts with learned patterns.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize context manager.
        
        Args:
            storage_path: Path to store learned patterns
        """
        self.storage_path = storage_path or Path("data/translation_contexts")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._pattern_library: Dict[str, List[TranslationPattern]] = {}
    
    def create_context(
        self,
        source_framework: str,
        target_framework: str,
        base_context: Optional[AIExecutionContext] = None,
        **kwargs,
    ) -> TranslationContext:
        """
        Create a new translation context.
        
        Args:
            source_framework: Source framework name
            target_framework: Target framework name
            base_context: Base AI execution context
            **kwargs: Additional configuration
        
        Returns:
            Configured translation context
        """
        # Create base context if not provided
        if base_context is None:
            base_context = AIExecutionContext(
                task_type=TaskType.TEST_MIGRATION,
            )
        
        # Create framework info
        source = FrameworkInfo(
            name=source_framework,
            language=kwargs.get("source_language", "python"),
        )
        target = FrameworkInfo(
            name=target_framework,
            language=kwargs.get("target_language", "python"),
        )
        
        # Create translation context
        context = TranslationContext(
            execution_context=base_context,
            source_framework=source,
            target_framework=target,
            preserve_comments=kwargs.get("preserve_comments", True),
            preserve_structure=kwargs.get("preserve_structure", True),
            generate_migration_notes=kwargs.get("generate_migration_notes", True),
            apply_target_conventions=kwargs.get("apply_target_conventions", True),
            source_file_path=kwargs.get("source_file_path"),
            target_file_path=kwargs.get("target_file_path"),
            project_root=kwargs.get("project_root"),
        )
        
        # Load relevant patterns from library
        pattern_key = f"{source_framework}_to_{target_framework}"
        if pattern_key in self._pattern_library:
            context.learned_patterns.extend(self._pattern_library[pattern_key])
        
        return context
    
    def add_pattern_to_library(
        self,
        source_framework: str,
        target_framework: str,
        pattern: TranslationPattern,
    ):
        """Add a pattern to the library."""
        key = f"{source_framework}_to_{target_framework}"
        if key not in self._pattern_library:
            self._pattern_library[key] = []
        self._pattern_library[key].append(pattern)
    
    def get_patterns(
        self, source_framework: str, target_framework: str
    ) -> List[TranslationPattern]:
        """Get all patterns for a framework pair."""
        key = f"{source_framework}_to_{target_framework}"
        return self._pattern_library.get(key, [])
    
    def save_context(self, context: TranslationContext, name: str):
        """Save a context to disk for reuse."""
        import json
        
        file_path = self.storage_path / f"{name}.json"
        data = context.to_dict()
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def load_context(
        self, name: str, base_context: Optional[AIExecutionContext] = None
    ) -> TranslationContext:
        """Load a saved context."""
        import json
        
        file_path = self.storage_path / f"{name}.json"
        
        with open(file_path, "r") as f:
            data = json.load(f)
        
        # Reconstruct context
        if base_context is None:
            base_context = AIExecutionContext(task_type=TaskType.TEST_MIGRATION)
        
        source_fw = FrameworkInfo(**data["source_framework"])
        target_fw = FrameworkInfo(**data["target_framework"])
        
        context = TranslationContext(
            execution_context=base_context,
            source_framework=source_fw,
            target_framework=target_fw,
            preserve_comments=data.get("preserve_comments", True),
            preserve_structure=data.get("preserve_structure", True),
            generate_migration_notes=data.get("generate_migration_notes", True),
            apply_target_conventions=data.get("apply_target_conventions", True),
            source_file_path=Path(data["source_file"]) if data.get("source_file") else None,
            target_file_path=Path(data["target_file"]) if data.get("target_file") else None,
            source_dependencies=data.get("source_dependencies", []),
            target_dependencies=data.get("target_dependencies", []),
        )
        
        # Load custom patterns
        for p_data in data.get("custom_patterns", []):
            pattern = TranslationPattern(
                source_pattern=p_data["source"],
                target_pattern=p_data["target"],
                description=p_data["description"],
                source_framework=source_fw.name,
                target_framework=target_fw.name,
            )
            context.add_pattern(pattern)
        
        return context


# Common framework patterns (pre-defined)
COMMON_PATTERNS = {
    "junit_to_pytest": [
        TranslationPattern(
            source_pattern="@Test",
            target_pattern="def test_",
            description="Convert JUnit @Test annotation to pytest function",
            source_framework="junit",
            target_framework="pytest",
        ),
        TranslationPattern(
            source_pattern="@BeforeEach",
            target_pattern="@pytest.fixture",
            description="Convert JUnit @BeforeEach to pytest fixture",
            source_framework="junit",
            target_framework="pytest",
        ),
        TranslationPattern(
            source_pattern="assertEquals(",
            target_pattern="assert ",
            description="Convert JUnit assertion to Python assert",
            source_framework="junit",
            target_framework="pytest",
        ),
    ],
    "selenium_java_to_playwright": [
        TranslationPattern(
            source_pattern="WebDriver driver",
            target_pattern="page: Page",
            description="Convert Selenium WebDriver to Playwright Page",
            source_framework="selenium_java",
            target_framework="playwright",
        ),
        TranslationPattern(
            source_pattern="driver.findElement(By.",
            target_pattern="page.locator(",
            description="Convert Selenium element location to Playwright locator",
            source_framework="selenium_java",
            target_framework="playwright",
        ),
    ],
}


def get_common_patterns(source: str, target: str) -> List[TranslationPattern]:
    """Get common pre-defined patterns for a framework pair."""
    key = f"{source}_to_{target}"
    return COMMON_PATTERNS.get(key, [])
