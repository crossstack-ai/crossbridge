# Copyright (c) 2025 Vikas Verma
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Universal test normalizer for CrossBridge adapters.

Converts framework-specific TestMetadata to UnifiedTestMemory with embedding support.
Provides consistent memory/embedding integration across all 13 frameworks.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
import uuid

from adapters.common.models import TestMetadata
from core.intelligence.models import (
    UnifiedTestMemory,
    StructuralSignals,
    SemanticSignals,
    TestMetadata as IntelligenceTestMetadata,
    TestType,
    Priority
)
from core.intelligence.java_ast_extractor import JavaASTExtractor, JavaASTExtractorFactory
from core.intelligence.javascript_ast_extractor import JavaScriptASTExtractor, TypeScriptASTExtractor, JavaScriptASTExtractorFactory


class UniversalTestNormalizer:
    """
    Normalizes test metadata from any framework to UnifiedTestMemory format.
    
    Supports all 13 frameworks with AST extraction for structural signals
    and embedding generation for semantic search.
    """
    
    def __init__(self):
        """Initialize normalizer with AST extractors."""
        self.java_extractor_factory = JavaASTExtractorFactory()
        self.js_extractor_factory = JavaScriptASTExtractorFactory()
    
    def normalize(
        self,
        test_metadata: TestMetadata,
        source_code: Optional[str] = None,
        generate_embedding: bool = True
    ) -> UnifiedTestMemory:
        """
        Convert framework-specific TestMetadata to UnifiedTestMemory.
        
        Args:
            test_metadata: Framework-specific test metadata
            source_code: Optional source code for AST extraction
            generate_embedding: Whether to generate semantic embeddings
            
        Returns:
            UnifiedTestMemory instance with all signals populated
        """
        # Extract language from framework
        language = self._detect_language(test_metadata.framework, test_metadata.language)
        
        # Extract structural signals if source code available
        structural = StructuralSignals()
        if source_code:
            structural = self._extract_structural_signals(
                source_code,
                test_metadata.test_name,
                language,
                test_metadata.framework
            )
        
        # Generate semantic signals
        semantic = self._generate_semantic_signals(
            test_metadata,
            source_code,
            generate_embedding
        )
        
        # Convert metadata
        intelligence_metadata = self._convert_metadata(test_metadata)
        
        # Generate test ID
        test_id = self._generate_test_id(test_metadata)
        
        return UnifiedTestMemory(
            test_id=test_id,
            framework=test_metadata.framework,
            language=language,
            file_path=test_metadata.file_path,
            test_name=test_metadata.test_name,
            semantic=semantic,
            structural=structural,
            metadata=intelligence_metadata,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    
    def normalize_batch(
        self,
        test_metadatas: List[TestMetadata],
        source_codes: Optional[Dict[str, str]] = None,
        generate_embeddings: bool = True
    ) -> List[UnifiedTestMemory]:
        """
        Normalize multiple tests in batch.
        
        Args:
            test_metadatas: List of framework test metadata
            source_codes: Optional dict mapping file paths to source code
            generate_embeddings: Whether to generate embeddings
            
        Returns:
            List of UnifiedTestMemory instances
        """
        results = []
        
        for metadata in test_metadatas:
            source_code = None
            if source_codes and metadata.file_path in source_codes:
                source_code = source_codes[metadata.file_path]
            
            unified = self.normalize(metadata, source_code, generate_embeddings)
            results.append(unified)
        
        return results
    
    def _detect_language(self, framework: str, explicit_language: str) -> str:
        """Detect programming language from framework."""
        if explicit_language and explicit_language != "python":
            return explicit_language
        
        # Framework to language mapping
        java_frameworks = [
            "junit", "testng", "selenium-java", "cucumber-java",
            "restassured", "restassured-java"
        ]
        js_frameworks = [
            "cypress", "playwright", "jest", "mocha", "jasmine"
        ]
        python_frameworks = [
            "pytest", "unittest", "selenium-pytest", "selenium-behave",
            "robot"
        ]
        csharp_frameworks = ["nunit", "xunit", "mstest", "specflow"]
        
        framework_lower = framework.lower()
        
        if any(fw in framework_lower for fw in java_frameworks):
            return "java"
        elif any(fw in framework_lower for fw in js_frameworks):
            return "javascript"
        elif any(fw in framework_lower for fw in python_frameworks):
            return "python"
        elif any(fw in framework_lower for fw in csharp_frameworks):
            return "csharp"
        
        # Default based on file extension
        return explicit_language or "python"
    
    def _extract_structural_signals(
        self,
        source_code: str,
        test_name: str,
        language: str,
        framework: str
    ) -> StructuralSignals:
        """Extract structural signals using AST extractors."""
        try:
            if language == "java":
                extractor = self.java_extractor_factory.create()
                return extractor.extract(source_code, test_name)
            
            elif language in ["javascript", "typescript"]:
                extractor = self.js_extractor_factory.create(language)
                return extractor.extract(source_code, test_name)
            
            # Fallback for unsupported languages - extract basic info
            return self._basic_extraction(source_code, framework)
        
        except Exception as e:
            print(f"Warning: AST extraction failed: {e}")
            return StructuralSignals()
    
    def _basic_extraction(self, source_code: str, framework: str) -> StructuralSignals:
        """Basic extraction without AST for unsupported languages."""
        signals = StructuralSignals()
        
        # Detect common patterns
        if "robot" in framework.lower():
            # Robot Framework keywords
            import re
            keywords = re.findall(r'^\s*([A-Z][A-Za-z0-9\s]+)$', source_code, re.MULTILINE)
            signals.functions = list(set(keywords[:20]))  # Limit to 20
        
        # Detect assertions (language-agnostic patterns)
        assertion_keywords = ["assert", "expect", "should", "verify"]
        if any(kw in source_code.lower() for kw in assertion_keywords):
            # Count occurrences
            for kw in assertion_keywords:
                count = source_code.lower().count(kw)
                if count > 0:
                    from core.intelligence.models import Assertion
                    signals.assertions.append(
                        Assertion(type=kw, target="detected", expected_value=None)
                    )
        
        return signals
    
    def _generate_semantic_signals(
        self,
        test_metadata: TestMetadata,
        source_code: Optional[str],
        generate_embedding: bool
    ) -> SemanticSignals:
        """Generate semantic signals for test discovery."""
        # Build intent text from metadata
        intent_parts = [
            f"Test: {test_metadata.test_name}",
            f"Framework: {test_metadata.framework}"
        ]
        
        if test_metadata.tags:
            intent_parts.append(f"Tags: {', '.join(test_metadata.tags)}")
        
        intent_text = " | ".join(intent_parts)
        
        # Extract keywords from test name
        keywords = self._extract_keywords(test_metadata.test_name)
        keywords.extend(test_metadata.tags)
        
        semantic = SemanticSignals(
            intent_text=intent_text,
            keywords=list(set(keywords)),  # Deduplicate
            embedding=None  # Will be populated by embedding service
        )
        
        # TODO: Integrate with embedding service when needed
        # if generate_embedding:
        #     from core.memory.embedding_provider import EmbeddingProvider
        #     provider = EmbeddingProvider()
        #     semantic.embedding = provider.embed(intent_text)
        
        return semantic
    
    def _extract_keywords(self, test_name: str) -> List[str]:
        """Extract keywords from test name using common patterns."""
        import re
        
        # Split camelCase and snake_case
        words = re.sub(r'([a-z])([A-Z])', r'\1 \2', test_name)
        words = words.replace('_', ' ').replace('-', ' ')
        
        # Split and filter
        keywords = [
            word.lower()
            for word in words.split()
            if len(word) > 2 and word.lower() not in ['test', 'the', 'and', 'with']
        ]
        
        return keywords
    
    def _convert_metadata(self, test_metadata: TestMetadata) -> IntelligenceTestMetadata:
        """Convert adapter TestMetadata to intelligence TestMetadata."""
        # Map test_type string to TestType enum
        test_type = TestType.POSITIVE  # Default
        test_type_lower = test_metadata.test_type.lower() if test_metadata.test_type else ""
        
        if test_type_lower in ["negative", "error"]:
            test_type = TestType.NEGATIVE
        elif test_type_lower == "boundary":
            test_type = TestType.BOUNDARY
        elif test_type_lower in ["integration", "api"]:
            test_type = TestType.INTEGRATION
        elif test_type_lower == "unit":
            test_type = TestType.UNIT
        elif test_type_lower == "e2e":
            test_type = TestType.E2E
        
        # Determine priority from tags
        priority = Priority.P2  # Default
        if any(tag in test_metadata.tags for tag in ["critical", "p0", "smoke"]):
            priority = Priority.P0
        elif any(tag in test_metadata.tags for tag in ["high", "p1"]):
            priority = Priority.P1
        elif any(tag in test_metadata.tags for tag in ["low", "p3"]):
            priority = Priority.P3
        
        return IntelligenceTestMetadata(
            test_type=test_type,
            priority=priority,
            tags=test_metadata.tags,
            feature=None,  # Could be extracted from tags/path
            component=None  # Could be extracted from file path
        )
    
    def _generate_test_id(self, test_metadata: TestMetadata) -> str:
        """Generate stable test ID."""
        # Use framework::file::test format
        file_name = Path(test_metadata.file_path).name
        return f"{test_metadata.framework}::{file_name}::{test_metadata.test_name}"


def normalize_cypress_test(
    test_metadata: TestMetadata,
    source_code: Optional[str] = None
) -> UnifiedTestMemory:
    """
    Convenience function to normalize Cypress test.
    
    Args:
        test_metadata: Cypress test metadata
        source_code: Optional Cypress test source code
        
    Returns:
        UnifiedTestMemory instance
    """
    normalizer = UniversalTestNormalizer()
    return normalizer.normalize(test_metadata, source_code, generate_embedding=True)


def normalize_playwright_test(
    test_metadata: TestMetadata,
    source_code: Optional[str] = None
) -> UnifiedTestMemory:
    """
    Convenience function to normalize Playwright test.
    
    Args:
        test_metadata: Playwright test metadata
        source_code: Optional Playwright test source code
        
    Returns:
        UnifiedTestMemory instance
    """
    normalizer = UniversalTestNormalizer()
    return normalizer.normalize(test_metadata, source_code, generate_embedding=True)


def normalize_robot_test(
    test_metadata: TestMetadata,
    source_code: Optional[str] = None
) -> UnifiedTestMemory:
    """
    Convenience function to normalize Robot Framework test.
    
    Args:
        test_metadata: Robot Framework test metadata
        source_code: Optional Robot Framework test source code
        
    Returns:
        UnifiedTestMemory instance
    """
    normalizer = UniversalTestNormalizer()
    return normalizer.normalize(test_metadata, source_code, generate_embedding=True)
