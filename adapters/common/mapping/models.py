"""
Data models for step-to-code-path mapping.

Signal-driven mapping of BDD steps to Page Objects, methods, and file paths.
No heuristics, no NLP, no regex - only explicit signal registration.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class SignalType(str, Enum):
    """Types of signals that contribute to step mapping."""
    PAGE_OBJECT = "page_object"
    METHOD = "method"
    CODE_PATH = "code_path"
    DECORATOR = "decorator"
    ANNOTATION = "annotation"


@dataclass(frozen=True)
class StepSignal:
    """
    A signal that contributes to step-to-code mapping.
    
    Signals are registered by adapters during discovery based on:
    - Page Object method names
    - Decorators/annotations
    - Naming conventions
    - Explicit mapping config
    
    Attributes:
        type: Type of signal (page_object, method, code_path, etc.)
        value: Signal value (e.g., "LoginPage.login", "pages/login_page.py::LoginPage.login")
        metadata: Optional additional context
        
    Example:
        >>> signal = StepSignal(
        ...     type=SignalType.CODE_PATH,
        ...     value="pages/login_page.py::LoginPage.login"
        ... )
    """
    type: SignalType
    value: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class CodeReference:
    """
    Reference to a specific code location (file, class, method).
    
    Provides structured representation of code paths for:
    - Impact analysis (which tests affected by code change)
    - Coverage tracking (which code covered by test)
    - Migration parity (source → target mapping validation)
    
    Attributes:
        file_path: Relative file path (e.g., "pages/login_page.py")
        class_name: Class name if applicable (e.g., "LoginPage")
        method_name: Method name if applicable (e.g., "login")
        line_number: Optional line number for precision
        
    Example:
        >>> ref = CodeReference(
        ...     file_path="pages/login_page.py",
        ...     class_name="LoginPage",
        ...     method_name="login"
        ... )
        >>> ref.full_path
        'pages/login_page.py::LoginPage.login'
    """
    file_path: str
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    line_number: Optional[int] = None
    
    @property
    def full_path(self) -> str:
        """
        Get fully qualified code path.
        
        Format: file_path[::class_name[.method_name]]
        
        Returns:
            Fully qualified path string
            
        Example:
            >>> CodeReference("pages/login.py", "LoginPage", "login").full_path
            'pages/login.py::LoginPage.login'
            >>> CodeReference("utils/helpers.py", None, "validate").full_path
            'utils/helpers.py::validate'
        """
        parts = [self.file_path]
        
        if self.class_name and self.method_name:
            parts.append(f"::{self.class_name}.{self.method_name}")
        elif self.class_name:
            parts.append(f"::{self.class_name}")
        elif self.method_name:
            parts.append(f"::{self.method_name}")
        
        return "".join(parts)


@dataclass
class StepMapping:
    """
    Complete mapping of a BDD step to code paths.
    
    This is the ground truth for:
    - Impact-based test selection
    - Migration parity checks
    - Coverage persistence
    - AI-assisted translation
    - Diagnostics ("What broke?")
    
    Attributes:
        step: Normalized step text (e.g., "user logs in with admin and admin123")
        page_objects: List of Page Object classes involved
        methods: List of methods invoked
        code_paths: List of fully qualified code paths
        signals: List of signals that contributed to this mapping
        
    Example:
        >>> mapping = StepMapping(
        ...     step="user logs in with admin and admin123",
        ...     page_objects=["LoginPage"],
        ...     methods=["login"],
        ...     code_paths=["pages/login_page.py::LoginPage.login"]
        ... )
    """
    step: str
    page_objects: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    code_paths: List[str] = field(default_factory=list)
    signals: List[StepSignal] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary for persistence/transmission.
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "step": self.step,
            "page_objects": self.page_objects,
            "methods": self.methods,
            "code_paths": self.code_paths,
            "signals": [
                {"type": s.type.value, "value": s.value, "metadata": s.metadata}
                for s in self.signals
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepMapping":
        """
        Deserialize from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            StepMapping instance
        """
        signals = [
            StepSignal(
                type=SignalType(s["type"]),
                value=s["value"],
                metadata=s.get("metadata")
            )
            for s in data.get("signals", [])
        ]
        
        return cls(
            step=data["step"],
            page_objects=data.get("page_objects", []),
            methods=data.get("methods", []),
            code_paths=data.get("code_paths", []),
            signals=signals
        )
    
    def add_code_path(self, code_path: str) -> None:
        """Add a code path if not already present (preserves order)."""
        if code_path not in self.code_paths:
            self.code_paths.append(code_path)
    
    def add_page_object(self, page_object: str) -> None:
        """Add a page object if not already present (preserves order)."""
        if page_object not in self.page_objects:
            self.page_objects.append(page_object)
    
    def add_method(self, method: str) -> None:
        """Add a method if not already present (preserves order)."""
        if method not in self.methods:
            self.methods.append(method)
