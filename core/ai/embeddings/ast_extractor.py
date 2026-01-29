"""
AST Extraction for Code Structure Analysis

Extracts structural summaries from source code to augment embeddings.
Supports Python, Java, and JavaScript.
"""

import ast
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
from abc import ABC, abstractmethod

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.AI)


@dataclass
class ASTSummary:
    """
    Structural code summary extracted from AST.
    
    This is NOT the AST itself - it's a human-readable summary
    that will be converted to text and appended to embeddings.
    """
    language: str
    classes: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    external_calls: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    assertions: int = 0
    control_flow: Dict[str, int] = field(default_factory=lambda: {
        "if": 0,
        "loop": 0,
        "try": 0
    })
    decorators: List[str] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    complexity_score: float = 0.0
    
    def to_text(self) -> str:
        """
        Convert AST summary to human-readable text for embedding augmentation.
        
        CRITICAL: This text is appended to base embeddings, not replacing them.
        """
        parts = []
        
        parts.append(f"Code Structure ({self.language}):")
        
        if self.classes:
            parts.append(f"Classes: {', '.join(self.classes[:10])}")
        
        if self.methods:
            parts.append(f"Methods: {', '.join(self.methods[:10])}")
        
        if self.functions:
            parts.append(f"Functions: {', '.join(self.functions[:10])}")
        
        if self.external_calls:
            parts.append(f"External Calls: {', '.join(self.external_calls[:15])}")
        
        if self.imports:
            parts.append(f"Imports: {', '.join(self.imports[:10])}")
        
        if self.assertions > 0:
            parts.append(f"Assertions: {self.assertions}")
        
        if self.decorators:
            parts.append(f"Decorators: {', '.join(self.decorators[:5])}")
        
        if any(self.control_flow.values()):
            cf_parts = []
            if self.control_flow.get("if", 0) > 0:
                cf_parts.append(f"Conditionals: {self.control_flow['if']}")
            if self.control_flow.get("loop", 0) > 0:
                cf_parts.append(f"Loops: {self.control_flow['loop']}")
            if self.control_flow.get("try", 0) > 0:
                cf_parts.append(f"Error Handling: {self.control_flow['try']}")
            parts.append(f"Control Flow: {', '.join(cf_parts)}")
        
        if self.complexity_score > 0:
            parts.append(f"Complexity: {self.complexity_score:.1f}")
        
        return "\n".join(parts)


class ASTExtractor(ABC):
    """Abstract base for language-specific AST extractors"""
    
    @abstractmethod
    def extract(self, code: str, file_path: Optional[str] = None) -> ASTSummary:
        """Extract AST summary from source code"""
        pass
    
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Return supported file extensions"""
        pass


class PythonASTExtractor(ASTExtractor):
    """
    Python AST extractor using stdlib ast module.
    
    Extracts:
    - Class names
    - Method/function names
    - External calls (imported modules usage)
    - Assert statements
    - Control flow (if/for/while/try)
    - Decorators
    - Type annotations
    """
    
    def extract(self, code: str, file_path: Optional[str] = None) -> ASTSummary:
        """Extract Python AST summary"""
        try:
            tree = ast.parse(code)
            summary = ASTSummary(language="python")
            
            for node in ast.walk(tree):
                # Classes
                if isinstance(node, ast.ClassDef):
                    summary.classes.append(node.name)
                    # Extract decorators
                    for dec in node.decorator_list:
                        if isinstance(dec, ast.Name):
                            summary.decorators.append(dec.id)
                
                # Functions/Methods
                elif isinstance(node, ast.FunctionDef):
                    summary.methods.append(node.name)
                    # Extract decorators
                    for dec in node.decorator_list:
                        if isinstance(dec, ast.Name):
                            summary.decorators.append(dec.id)
                    # Type annotations
                    if node.returns:
                        summary.annotations.append(f"{node.name} -> return type")
                
                # Imports
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        summary.imports.append(alias.name)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        summary.imports.append(node.module)
                
                # Function calls (external calls)
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        summary.external_calls.append(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name):
                            summary.external_calls.append(
                                f"{node.func.value.id}.{node.func.attr}"
                            )
                
                # Assertions
                elif isinstance(node, ast.Assert):
                    summary.assertions += 1
                
                # Control flow
                elif isinstance(node, ast.If):
                    summary.control_flow["if"] += 1
                
                elif isinstance(node, (ast.For, ast.While)):
                    summary.control_flow["loop"] += 1
                
                elif isinstance(node, ast.Try):
                    summary.control_flow["try"] += 1
            
            # Calculate complexity (simple heuristic)
            summary.complexity_score = (
                len(summary.methods) * 1.0 +
                summary.control_flow["if"] * 0.5 +
                summary.control_flow["loop"] * 0.7 +
                summary.control_flow["try"] * 0.3
            )
            
            # Deduplicate
            summary.classes = list(dict.fromkeys(summary.classes))
            summary.methods = list(dict.fromkeys(summary.methods))
            summary.external_calls = list(dict.fromkeys(summary.external_calls))
            summary.imports = list(dict.fromkeys(summary.imports))
            summary.decorators = list(dict.fromkeys(summary.decorators))
            
            logger.debug(
                f"Extracted Python AST: {len(summary.classes)} classes, "
                f"{len(summary.methods)} methods, {summary.assertions} assertions"
            )
            
            return summary
            
        except SyntaxError as e:
            logger.warning(f"Python syntax error: {e}")
            return ASTSummary(language="python")
        except Exception as e:
            logger.error(f"Python AST extraction failed: {e}")
            return ASTSummary(language="python")
    
    def supported_extensions(self) -> List[str]:
        return [".py"]


class JavaASTExtractor(ASTExtractor):
    """
    Java AST extractor using tree-sitter or javalang.
    
    Phase-1: Basic pattern matching
    Phase-2: Full JavaParser integration
    """
    
    def extract(self, code: str, file_path: Optional[str] = None) -> ASTSummary:
        """Extract Java AST summary (basic implementation)"""
        summary = ASTSummary(language="java")
        
        # Basic pattern matching for Phase-1
        # TODO: Replace with JavaParser for production
        
        import re
        
        # Classes
        class_pattern = r'class\s+(\w+)'
        summary.classes = re.findall(class_pattern, code)
        
        # Methods
        method_pattern = r'(?:public|private|protected)?\s+(?:static\s+)?(?:\w+\s+)+(\w+)\s*\('
        summary.methods = re.findall(method_pattern, code)
        
        # Imports
        import_pattern = r'import\s+([\w.]+);'
        summary.imports = re.findall(import_pattern, code)
        
        # Assertions (JUnit/TestNG)
        assert_patterns = [
            r'assert(?:True|False|Equals|NotNull|Null|That)\s*\(',
            r'verify\s*\(',
            r'expect\s*\('
        ]
        for pattern in assert_patterns:
            summary.assertions += len(re.findall(pattern, code))
        
        # Control flow
        summary.control_flow["if"] = len(re.findall(r'\bif\s*\(', code))
        summary.control_flow["loop"] = len(re.findall(r'\b(?:for|while)\s*\(', code))
        summary.control_flow["try"] = len(re.findall(r'\btry\s*\{', code))
        
        # Annotations
        annotation_pattern = r'@(\w+)'
        summary.decorators = re.findall(annotation_pattern, code)
        
        # Deduplicate
        summary.classes = list(dict.fromkeys(summary.classes))
        summary.methods = list(dict.fromkeys(summary.methods))
        summary.imports = list(dict.fromkeys(summary.imports))
        summary.decorators = list(dict.fromkeys(summary.decorators))
        
        logger.debug(
            f"Extracted Java AST: {len(summary.classes)} classes, "
            f"{len(summary.methods)} methods, {summary.assertions} assertions"
        )
        
        return summary
    
    def supported_extensions(self) -> List[str]:
        return [".java"]


class JavaScriptASTExtractor(ASTExtractor):
    """
    JavaScript/TypeScript AST extractor.
    
    Phase-1: Basic pattern matching
    Phase-2: tree-sitter or babel integration
    """
    
    def extract(self, code: str, file_path: Optional[str] = None) -> ASTSummary:
        """Extract JavaScript AST summary (basic implementation)"""
        summary = ASTSummary(language="javascript")
        
        import re
        
        # Classes
        class_pattern = r'class\s+(\w+)'
        summary.classes = re.findall(class_pattern, code)
        
        # Functions
        func_patterns = [
            r'function\s+(\w+)\s*\(',
            r'const\s+(\w+)\s*=\s*\(',
            r'(\w+)\s*:\s*function\s*\(',
            r'(\w+)\s*=>\s*'
        ]
        for pattern in func_patterns:
            summary.functions.extend(re.findall(pattern, code))
        
        # Imports
        import_patterns = [
            r'import\s+.*\s+from\s+["\']([^"\']+)["\']',
            r'require\s*\(["\']([^"\']+)["\']\)'
        ]
        for pattern in import_patterns:
            summary.imports.extend(re.findall(pattern, code))
        
        # Assertions (Jest/Mocha/Cypress)
        assert_patterns = [
            r'expect\s*\(',
            r'assert\.',
            r'should\.',
            r'cy\.should\('
        ]
        for pattern in assert_patterns:
            summary.assertions += len(re.findall(pattern, code))
        
        # Control flow
        summary.control_flow["if"] = len(re.findall(r'\bif\s*\(', code))
        summary.control_flow["loop"] = len(re.findall(r'\b(?:for|while)\s*\(', code))
        summary.control_flow["try"] = len(re.findall(r'\btry\s*\{', code))
        
        # Decorators (TypeScript)
        annotation_pattern = r'@(\w+)'
        summary.decorators = re.findall(annotation_pattern, code)
        
        # Deduplicate
        summary.classes = list(dict.fromkeys(summary.classes))
        summary.functions = list(dict.fromkeys(summary.functions))
        summary.imports = list(dict.fromkeys(summary.imports))
        summary.decorators = list(dict.fromkeys(summary.decorators))
        
        logger.debug(
            f"Extracted JavaScript AST: {len(summary.classes)} classes, "
            f"{len(summary.functions)} functions, {summary.assertions} assertions"
        )
        
        return summary
    
    def supported_extensions(self) -> List[str]:
        return [".js", ".ts", ".jsx", ".tsx"]


class ASTExtractorFactory:
    """Factory for creating language-specific AST extractors"""
    
    _extractors = {
        "python": PythonASTExtractor(),
        "java": JavaASTExtractor(),
        "javascript": JavaScriptASTExtractor()
    }
    
    @classmethod
    def get_extractor(cls, language: str) -> Optional[ASTExtractor]:
        """Get extractor for language"""
        return cls._extractors.get(language.lower())
    
    @classmethod
    def get_extractor_for_file(cls, file_path: str) -> Optional[ASTExtractor]:
        """Get extractor based on file extension"""
        ext = Path(file_path).suffix.lower()
        
        for extractor in cls._extractors.values():
            if ext in extractor.supported_extensions():
                return extractor
        
        return None
    
    @classmethod
    def extract_from_file(cls, file_path: str) -> Optional[ASTSummary]:
        """
        Extract AST summary from file.
        
        Returns None if file type not supported or extraction fails.
        """
        try:
            extractor = cls.get_extractor_for_file(file_path)
            if not extractor:
                logger.debug(f"No AST extractor for {file_path}")
                return None
            
            code = Path(file_path).read_text(encoding='utf-8')
            return extractor.extract(code, file_path)
            
        except Exception as e:
            logger.error(f"AST extraction failed for {file_path}: {e}")
            return None


def augment_text_with_ast(base_text: str, ast_summary: Optional[ASTSummary]) -> str:
    """
    Augment base embedding text with AST summary.
    
    CRITICAL RULE: Never replace base text, always append.
    
    Args:
        base_text: Original embedding text
        ast_summary: AST summary (None if not available)
    
    Returns:
        Augmented text (base + AST summary)
    """
    if not ast_summary:
        return base_text
    
    ast_text = ast_summary.to_text()
    if not ast_text.strip():
        return base_text
    
    return f"{base_text}\n\n{ast_text}"
