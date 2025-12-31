"""
Translation Pipeline - Core orchestration.

Coordinates the entire translation process from source to target.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.translation.intent_model import TestIntent
from core.translation.registry import ApiMappingRegistry, IdiomRegistry


class TranslationMode(str, Enum):
    """Translation mode."""
    ASSISTIVE = "assistive"  # Human reviews all changes
    AUTOMATED = "automated"  # Automated with confidence checks
    BATCH = "batch"  # Bulk translation


class ValidationLevel(str, Enum):
    """Validation strictness level."""
    STRICT = "strict"  # All validations must pass
    LENIENT = "lenient"  # Warnings allowed
    SKIP = "skip"  # No validation


@dataclass
class TranslationConfig:
    """Configuration for translation."""
    source_framework: str
    target_framework: str
    mode: TranslationMode = TranslationMode.ASSISTIVE
    use_ai: bool = False
    max_ai_credits: float = 100.0
    validation_level: ValidationLevel = ValidationLevel.STRICT
    preserve_comments: bool = True
    inject_todos: bool = True
    confidence_threshold: float = 0.7
    
    # Output options
    output_format: str = "python"  # python, javascript, etc.
    test_framework: str = ""  # pytest, jest, etc.
    style_guide: Optional[str] = None


@dataclass
class TranslationResult:
    """Result of translation operation."""
    success: bool
    target_code: str
    intent: TestIntent
    
    # Quality metrics
    confidence: float = 0.0
    todos: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Traceability
    source_file: str = ""
    target_file: str = ""
    source_lines: Optional[tuple] = None
    
    # Statistics
    actions_translated: int = 0
    assertions_translated: int = 0
    idioms_applied: int = 0
    ai_refinements: int = 0
    statistics: Dict[str, int] = field(default_factory=dict)  # Backward compatibility
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "target_code": self.target_code,
            "intent": self.intent.to_dict() if self.intent else None,
            "confidence": self.confidence,
            "todos": self.todos,
            "warnings": self.warnings,
            "errors": self.errors,
            "source_file": self.source_file,
            "target_file": self.target_file,
            "actions_translated": self.actions_translated,
            "assertions_translated": self.assertions_translated,
            "idioms_applied": self.idioms_applied,
            "ai_refinements": self.ai_refinements,
        }


class SourceParser:
    """Base class for source framework parsers."""
    
    def __init__(self, framework: str):
        """Initialize parser."""
        self.framework = framework
    
    def can_parse(self, source_code: str) -> bool:
        """Check if parser can handle this source code."""
        raise NotImplementedError
    
    def parse(self, source_code: str, source_file: str = "") -> TestIntent:
        """Parse source code into TestIntent."""
        raise NotImplementedError


class TargetGenerator:
    """Base class for target framework generators."""
    
    def __init__(self, framework: str, config: TranslationConfig):
        """Initialize generator."""
        self.framework = framework
        self.config = config
    
    def can_generate(self, intent: TestIntent) -> bool:
        """Check if generator can handle this intent."""
        raise NotImplementedError
    
    def generate(self, intent: TestIntent) -> str:
        """Generate target code from TestIntent."""
        raise NotImplementedError


class TranslationPipeline:
    """
    Main translation pipeline.
    
    Orchestrates: Parse → Intent → Idioms → Generate → AI Refine → Validate
    """
    
    def __init__(self, config: TranslationConfig = None):
        """Initialize pipeline."""
        self.config = config
        self.api_registry = ApiMappingRegistry()
        self.idiom_registry = IdiomRegistry()
        
        # Initialize parser and generator later if config not provided
        self.parser = None
        self.generator = None
        
        if config:
            self.parser = self._get_parser(config.source_framework)
            self.generator = self._get_generator(config.target_framework)
    
    def _get_parser(self, framework: str) -> SourceParser:
        """Get appropriate parser for source framework."""
        framework_lower = framework.lower()
        
        # Import parsers dynamically to avoid circular dependencies
        if "selenium" in framework_lower and "bdd" in framework_lower:
            from core.translation.parsers.selenium_bdd_parser import SeleniumJavaBDDParser
            return SeleniumJavaBDDParser(framework)
        elif "selenium" in framework_lower:
            from core.translation.parsers.selenium_parser import SeleniumParser
            return SeleniumParser(framework)
        elif "restassured" in framework_lower:
            from core.translation.parsers.restassured_parser import RestAssuredParser
            return RestAssuredParser(framework)
        elif "robot" in framework_lower:
            from core.translation.parsers.robot_parser import RobotParser
            return RobotParser(framework)
        else:
            # Generic parser
            return SourceParser(framework)
    
    def _get_generator(self, framework: str) -> TargetGenerator:
        """Get appropriate generator for target framework."""
        framework_lower = framework.lower()
        
        if "playwright" in framework_lower:
            from core.translation.generators.playwright_generator import PlaywrightGenerator
            return PlaywrightGenerator(framework, self.config)
        elif "pytest" in framework_lower:
            from core.translation.generators.pytest_generator import PytestGenerator
            return PytestGenerator(framework, self.config)
        elif "robot" in framework_lower:
            from core.translation.generators.robot_generator import RobotGenerator
            return RobotGenerator(framework, self.config)
        else:
            # Generic generator
            return TargetGenerator(framework, self.config)
    
    def translate(
        self, source_code: str, source_framework: str = None, target_framework: str = None, source_file: str = ""
    ) -> TranslationResult:
        """
        Execute complete translation pipeline.
        
        Steps:
        1. Parse source → Intent
        2. Normalize intent
        3. Apply idioms
        4. Generate target
        5. AI refinement (optional)
        6. Validation
        7. TODO injection
        """
        # Get parser and generator if not already initialized
        if not self.parser and source_framework:
            self.parser = self._get_parser(source_framework)
        if not self.generator and target_framework:
            # Create config if needed
            if not self.config:
                self.config = TranslationConfig(
                    source_framework=source_framework,
                    target_framework=target_framework,
                )
            self.generator = self._get_generator(target_framework)
        
        result = TranslationResult(
            success=False,
            target_code="",
            intent=None,
            source_file=source_file,
        )
        
        try:
            # Step 1: Parse source code
            intent = self.parser.parse(source_code, source_file)
            result.intent = intent
            
            if not intent:
                result.errors.append("Failed to parse source code")
                return result
            
            # Step 2: Normalize intent
            self._normalize_intent(intent)
            
            # Step 3: Apply idioms
            idioms_applied = self._apply_idioms(intent)
            result.idioms_applied = idioms_applied
            
            # Step 4: Generate target code
            if not self.generator.can_generate(intent):
                result.errors.append(
                    f"Generator cannot handle intent type: {intent.test_type}"
                )
                return result
            
            target_code = self.generator.generate(intent)
            result.target_code = target_code
            
            # Step 5: AI refinement (if enabled)
            if self.config.use_ai:
                target_code, ai_count = self._ai_refine(intent, target_code)
                result.target_code = target_code
                result.ai_refinements = ai_count
            
            # Step 6: Inject TODOs
            if self.config.inject_todos and intent.todos:
                target_code = self._inject_todos(target_code, intent.todos)
                result.target_code = target_code
            
            # Step 7: Validation
            validation_result = self._validate(intent, target_code)
            result.warnings.extend(validation_result.get("warnings", []))
            result.errors.extend(validation_result.get("errors", []))
            
            # Set final metrics
            result.confidence = intent.confidence
            result.todos = intent.todos
            result.actions_translated = len(intent.steps)
            result.assertions_translated = len(intent.assertions)
            
            # Add statistics dict for test compatibility
            result.statistics = {
                'actions': len(intent.steps),
                'assertions': len(intent.assertions),
                'idioms_applied': idioms_applied,
            }
            
            # Determine success
            if self.config.validation_level == ValidationLevel.STRICT:
                result.success = len(result.errors) == 0
            else:
                result.success = True
            
        except Exception as e:
            result.errors.append(f"Translation error: {str(e)}")
            result.success = False
        
        return result
    
    def _normalize_intent(self, intent: TestIntent):
        """Normalize and clean up intent."""
        # Remove low-confidence steps if needed
        if intent.confidence < self.config.confidence_threshold:
            intent.add_todo(
                f"Low confidence translation ({intent.confidence:.2f}). "
                "Please review carefully."
            )
        
        # Detect patterns that need human review
        for step in intent.steps:
            if step.wait_strategy == "explicit":
                intent.add_todo(
                    f"Explicit wait at line {step.line_number} - "
                    "verify if still needed in target framework"
                )
    
    def _apply_idioms(self, intent: TestIntent) -> int:
        """Apply framework-specific idioms."""
        idioms = self.idiom_registry.get_idioms(
            self.config.source_framework,
            self.config.target_framework
        )
        
        applied_count = 0
        
        # Apply idioms to each step
        for step in intent.steps:
            for idiom in idioms:
                # Check if idiom applies
                if idiom.name == "explicit_wait_removal" and step.wait_strategy == "explicit":
                    step.semantics["wait_removed"] = True
                    step.confidence *= 0.95  # Slight confidence reduction
                    applied_count += 1
                elif idiom.name == "sleep_removal" and "sleep" in step.description.lower():
                    step.semantics["sleep_removed"] = True
                    intent.add_todo(f"Sleep removed at line {step.line_number} - verify behavior")
                    applied_count += 1
        
        return applied_count
    
    def _ai_refine(self, intent: TestIntent, code: str) -> tuple[str, int]:
        """Use AI to refine generated code (if enabled)."""
        # This would integrate with the AI module
        # For now, return unchanged
        return code, 0
    
    def _inject_todos(self, code: str, todos: List[str]) -> str:
        """Inject TODO comments into generated code."""
        if not todos:
            return code
        
        header = "# " + "=" * 70 + "\n"
        header += "# TRANSLATION TODOs - MANUAL REVIEW REQUIRED\n"
        header += "# " + "=" * 70 + "\n"
        
        for i, todo in enumerate(todos, 1):
            header += f"# TODO {i}: {todo}\n"
        
        header += "# " + "=" * 70 + "\n\n"
        
        return header + code
    
    def _validate(self, intent: TestIntent, code: str) -> Dict[str, List[str]]:
        """Validate generated code."""
        validation = {"warnings": [], "errors": []}
        
        # Basic validations
        if not code.strip():
            validation["errors"].append("Generated code is empty")
        
        if intent.complexity > 20:
            validation["warnings"].append(
                f"Complex test ({intent.complexity} steps) - consider splitting"
            )
        
        if len(intent.steps) > 0 and len(intent.assertions) == 0:
            validation["warnings"].append("No assertions found - test may not verify anything")
        
        return validation
    
    def translate_file(self, source_file: Path) -> TranslationResult:
        """Translate an entire file."""
        source_code = source_file.read_text(encoding="utf-8")
        return self.translate(source_code, str(source_file))
    
    def translate_batch(
        self, source_files: List[Path]
    ) -> List[TranslationResult]:
        """Translate multiple files."""
        results = []
        
        for source_file in source_files:
            result = self.translate_file(source_file)
            results.append(result)
        
        return results
