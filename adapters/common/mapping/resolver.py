"""
Step mapping resolver - converts signals to step-to-code mappings.

Pure signal-driven logic. No heuristics, no regex, no AI.
"""
from typing import List, Optional
from .models import StepSignal, StepMapping, SignalType, CodeReference
from .registry import StepSignalRegistry


class StepMappingResolver:
    """
    Resolve step text to code paths using registered signals.
    
    This is the main logic that converts step text + signals into structured
    StepMapping objects for impact analysis, migration, and coverage tracking.
    
    Responsibilities:
    - Accept step text and StepSignalRegistry
    - Resolve page objects, methods, and code paths from signals
    - Deduplicate mappings
    - Preserve deterministic order
    - Return empty mapping if no signals found (no errors)
    
    Pure logic - easy to test, no side effects.
    
    Example:
        >>> registry = StepSignalRegistry()
        >>> registry.register_signal("user logs in",
        ...     StepSignal(type=SignalType.CODE_PATH,
        ...               value="pages/login_page.py::LoginPage.login"))
        >>> resolver = StepMappingResolver(registry)
        >>> mapping = resolver.resolve_step("when user logs in")
        >>> mapping.code_paths
        ['pages/login_page.py::LoginPage.login']
    """
    
    def __init__(self, registry: StepSignalRegistry):
        """
        Initialize resolver with a signal registry.
        
        Args:
            registry: StepSignalRegistry containing adapter-registered signals
        """
        self.registry = registry
    
    def resolve_step(self, step_text: str) -> StepMapping:
        """
        Resolve a step to its code paths using registered signals.
        
        Args:
            step_text: BDD step text (e.g., "When user logs in with admin")
            
        Returns:
            StepMapping with resolved page_objects, methods, and code_paths.
            Returns empty mapping if no signals found.
            
        Example:
            >>> mapping = resolver.resolve_step("user logs in")
            >>> mapping.page_objects
            ['LoginPage']
            >>> mapping.code_paths
            ['pages/login_page.py::LoginPage.login']
        """
        # Get all signals for this step
        signals = self.registry.get_signals_for_step(step_text)
        
        # Initialize mapping
        mapping = StepMapping(
            step=self._normalize_step_text(step_text),
            signals=signals
        )
        
        # Process each signal to extract page objects, methods, code paths
        for signal in signals:
            self._process_signal(signal, mapping)
        
        return mapping
    
    def resolve_steps(self, step_texts: List[str]) -> List[StepMapping]:
        """
        Resolve multiple steps in batch.
        
        Args:
            step_texts: List of BDD step texts
            
        Returns:
            List of StepMapping objects, one per step
            
        Example:
            >>> steps = ["user logs in", "user clicks logout"]
            >>> mappings = resolver.resolve_steps(steps)
            >>> len(mappings)
            2
        """
        return [self.resolve_step(step) for step in step_texts]
    
    def _process_signal(self, signal: StepSignal, mapping: StepMapping) -> None:
        """
        Process a single signal and update the mapping.
        
        Args:
            signal: StepSignal to process
            mapping: StepMapping to update (in-place)
        """
        if signal.type == SignalType.PAGE_OBJECT:
            # Extract page object name
            page_object = self._extract_page_object_name(signal.value)
            if page_object:
                mapping.add_page_object(page_object)
        
        elif signal.type == SignalType.METHOD:
            # Extract method name
            method = self._extract_method_name(signal.value)
            if method:
                mapping.add_method(method)
        
        elif signal.type == SignalType.CODE_PATH:
            # Full code path provided
            mapping.add_code_path(signal.value)
            
            # Also extract page object and method from code path
            code_ref = self._parse_code_path(signal.value)
            if code_ref:
                if code_ref.class_name:
                    mapping.add_page_object(code_ref.class_name)
                if code_ref.method_name:
                    mapping.add_method(code_ref.method_name)
        
        elif signal.type == SignalType.DECORATOR:
            # Decorator signal may contain code path info
            if "::" in signal.value:
                mapping.add_code_path(signal.value)
        
        elif signal.type == SignalType.ANNOTATION:
            # Annotation signal may contain code path info
            if "::" in signal.value:
                mapping.add_code_path(signal.value)
    
    def _extract_page_object_name(self, value: str) -> Optional[str]:
        """
        Extract page object class name from signal value.
        
        Args:
            value: Signal value (e.g., "LoginPage", "LoginPage.login")
            
        Returns:
            Page object class name or None
            
        Example:
            >>> resolver._extract_page_object_name("LoginPage")
            'LoginPage'
            >>> resolver._extract_page_object_name("LoginPage.login")
            'LoginPage'
        """
        # If contains ::, parse as code path first
        if "::" in value:
            code_ref = self._parse_code_path(value)
            return code_ref.class_name if code_ref else None
        
        # If contains dot, take first part
        if "." in value:
            return value.split(".")[0]
        
        # Otherwise assume whole value is class name
        return value
    
    def _extract_method_name(self, value: str) -> Optional[str]:
        """
        Extract method name from signal value.
        
        Args:
            value: Signal value (e.g., "login", "LoginPage.login")
            
        Returns:
            Method name or None
            
        Example:
            >>> resolver._extract_method_name("login")
            'login'
            >>> resolver._extract_method_name("LoginPage.login")
            'login'
        """
        # If contains ::, parse as code path first
        if "::" in value:
            code_ref = self._parse_code_path(value)
            return code_ref.method_name if code_ref else None
        
        # If contains dot, take last part
        if "." in value:
            return value.split(".")[-1]
        
        # Otherwise assume whole value is method name
        return value
    
    def _parse_code_path(self, code_path: str) -> Optional[CodeReference]:
        """
        Parse a code path string into a CodeReference.
        
        Format: file_path[::class_name[.method_name]]
        
        Args:
            code_path: Code path string
            
        Returns:
            CodeReference or None if parsing fails
            
        Example:
            >>> ref = resolver._parse_code_path("pages/login_page.py::LoginPage.login")
            >>> ref.file_path
            'pages/login_page.py'
            >>> ref.class_name
            'LoginPage'
            >>> ref.method_name
            'login'
        """
        try:
            # Split by ::
            if "::" not in code_path:
                # Just a file path
                return CodeReference(file_path=code_path)
            
            parts = code_path.split("::")
            file_path = parts[0]
            
            if len(parts) < 2:
                return CodeReference(file_path=file_path)
            
            # Parse class.method or just class or just method
            class_method = parts[1]
            
            if "." in class_method:
                # Contains both class and method
                class_name, method_name = class_method.split(".", 1)
                return CodeReference(
                    file_path=file_path,
                    class_name=class_name,
                    method_name=method_name
                )
            else:
                # Just class or method (assume class if capitalized)
                if class_method[0].isupper():
                    return CodeReference(file_path=file_path, class_name=class_method)
                else:
                    return CodeReference(file_path=file_path, method_name=class_method)
        
        except Exception:
            return None
    
    def _normalize_step_text(self, step_text: str) -> str:
        """
        Normalize step text for consistent storage.
        
        Args:
            step_text: Raw step text
            
        Returns:
            Normalized text
        """
        # Use registry's normalization
        return self.registry._normalize_step_text(step_text)
