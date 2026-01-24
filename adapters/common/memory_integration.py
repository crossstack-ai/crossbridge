"""
Memory and embedding integration helpers for all framework adapters.

Provides easy-to-use methods to convert any adapter's TestMetadata to
UnifiedTestMemory with structural and semantic signals.
"""

from typing import List, Optional, Dict
from pathlib import Path

from adapters.common.models import TestMetadata
from adapters.common.normalizer import UniversalTestNormalizer
from core.intelligence.models import UnifiedTestMemory


class MemoryIntegrationMixin:
    """
    Mixin class that adds memory/embedding support to any adapter.
    
    Add this to your adapter class to instantly get UnifiedTestMemory support:
    
    Example:
        class MyAdapter(BaseTestAdapter, MemoryIntegrationMixin):
            pass
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._normalizer = UniversalTestNormalizer()
    
    def to_unified_memory(
        self,
        test_metadata: TestMetadata,
        source_code: Optional[str] = None,
        generate_embedding: bool = True
    ) -> UnifiedTestMemory:
        """
        Convert single test metadata to UnifiedTestMemory.
        
        Args:
            test_metadata: Framework test metadata
            source_code: Optional source code for AST extraction
            generate_embedding: Whether to generate embeddings
            
        Returns:
            UnifiedTestMemory with all signals
        """
        return self._normalizer.normalize(
            test_metadata,
            source_code,
            generate_embedding
        )
    
    def to_unified_memory_batch(
        self,
        test_metadatas: List[TestMetadata],
        source_codes: Optional[Dict[str, str]] = None,
        generate_embeddings: bool = True
    ) -> List[UnifiedTestMemory]:
        """
        Convert multiple tests to UnifiedTestMemory.
        
        Args:
            test_metadatas: List of framework test metadata
            source_codes: Optional dict mapping file paths to source code
            generate_embeddings: Whether to generate embeddings
            
        Returns:
            List of UnifiedTestMemory instances
        """
        return self._normalizer.normalize_batch(
            test_metadatas,
            source_codes,
            generate_embeddings
        )
    
    def extract_with_memory(
        self,
        load_source_code: bool = True
    ) -> List[UnifiedTestMemory]:
        """
        Extract all tests with UnifiedTestMemory format.
        
        This method should be overridden by adapters to provide optimized
        extraction with source code loading.
        
        Args:
            load_source_code: Whether to load source files for AST extraction
            
        Returns:
            List of UnifiedTestMemory instances
        """
        # Default implementation - calls extract_tests() and converts
        if hasattr(self, 'extract_tests'):
            tests = self.extract_tests()
            
            if not load_source_code:
                return self.to_unified_memory_batch(tests, generate_embeddings=True)
            
            # Try to load source codes
            source_codes = {}
            if load_source_code:
                for test in tests:
                    try:
                        path = Path(test.file_path)
                        if path.exists():
                            source_codes[test.file_path] = path.read_text(encoding='utf-8')
                    except Exception as e:
                        print(f"Warning: Could not read {test.file_path}: {e}")
            
            return self.to_unified_memory_batch(
                tests,
                source_codes,
                generate_embeddings=True
            )
        
        raise NotImplementedError("Adapter must implement extract_tests() or override extract_with_memory()")


def add_memory_support_to_adapter(adapter_instance):
    """
    Dynamically add memory support to an existing adapter instance.
    
    Args:
        adapter_instance: Any adapter instance
        
    Returns:
        The same instance with memory methods added
    """
    normalizer = UniversalTestNormalizer()
    
    def to_unified_memory(
        test_metadata: TestMetadata,
        source_code: Optional[str] = None,
        generate_embedding: bool = True
    ) -> UnifiedTestMemory:
        return normalizer.normalize(test_metadata, source_code, generate_embedding)
    
    def to_unified_memory_batch(
        test_metadatas: List[TestMetadata],
        source_codes: Optional[Dict[str, str]] = None,
        generate_embeddings: bool = True
    ) -> List[UnifiedTestMemory]:
        return normalizer.normalize_batch(test_metadatas, source_codes, generate_embeddings)
    
    # Add methods to instance
    adapter_instance.to_unified_memory = to_unified_memory
    adapter_instance.to_unified_memory_batch = to_unified_memory_batch
    adapter_instance._normalizer = normalizer
    
    return adapter_instance


# Convenience functions for specific frameworks

def cypress_to_memory(
    test_metadata: TestMetadata,
    source_code: Optional[str] = None
) -> UnifiedTestMemory:
    """Convert Cypress test to UnifiedTestMemory."""
    normalizer = UniversalTestNormalizer()
    return normalizer.normalize(test_metadata, source_code, True)


def playwright_to_memory(
    test_metadata: TestMetadata,
    source_code: Optional[str] = None
) -> UnifiedTestMemory:
    """Convert Playwright test to UnifiedTestMemory."""
    normalizer = UniversalTestNormalizer()
    return normalizer.normalize(test_metadata, source_code, True)


def robot_to_memory(
    test_metadata: TestMetadata,
    source_code: Optional[str] = None
) -> UnifiedTestMemory:
    """Convert Robot Framework test to UnifiedTestMemory."""
    normalizer = UniversalTestNormalizer()
    return normalizer.normalize(test_metadata, source_code, True)


def pytest_to_memory(
    test_metadata: TestMetadata,
    source_code: Optional[str] = None
) -> UnifiedTestMemory:
    """Convert pytest test to UnifiedTestMemory."""
    normalizer = UniversalTestNormalizer()
    return normalizer.normalize(test_metadata, source_code, True)


def junit_to_memory(
    test_metadata: TestMetadata,
    source_code: Optional[str] = None
) -> UnifiedTestMemory:
    """Convert JUnit test to UnifiedTestMemory."""
    normalizer = UniversalTestNormalizer()
    return normalizer.normalize(test_metadata, source_code, True)


def testng_to_memory(
    test_metadata: TestMetadata,
    source_code: Optional[str] = None
) -> UnifiedTestMemory:
    """Convert TestNG test to UnifiedTestMemory."""
    normalizer = UniversalTestNormalizer()
    return normalizer.normalize(test_metadata, source_code, True)


def restassured_to_memory(
    test_metadata: TestMetadata,
    source_code: Optional[str] = None
) -> UnifiedTestMemory:
    """Convert RestAssured test to UnifiedTestMemory."""
    normalizer = UniversalTestNormalizer()
    return normalizer.normalize(test_metadata, source_code, True)


def selenium_to_memory(
    test_metadata: TestMetadata,
    source_code: Optional[str] = None
) -> UnifiedTestMemory:
    """Convert Selenium test to UnifiedTestMemory."""
    normalizer = UniversalTestNormalizer()
    return normalizer.normalize(test_metadata, source_code, True)


def cucumber_to_memory(
    test_metadata: TestMetadata,
    source_code: Optional[str] = None
) -> UnifiedTestMemory:
    """Convert Cucumber test to UnifiedTestMemory."""
    normalizer = UniversalTestNormalizer()
    return normalizer.normalize(test_metadata, source_code, True)


def behave_to_memory(
    test_metadata: TestMetadata,
    source_code: Optional[str] = None
) -> UnifiedTestMemory:
    """Convert Behave test to UnifiedTestMemory."""
    normalizer = UniversalTestNormalizer()
    return normalizer.normalize(test_metadata, source_code, True)


def specflow_to_memory(
    test_metadata: TestMetadata,
    source_code: Optional[str] = None
) -> UnifiedTestMemory:
    """Convert SpecFlow test to UnifiedTestMemory."""
    normalizer = UniversalTestNormalizer()
    return normalizer.normalize(test_metadata, source_code, True)
