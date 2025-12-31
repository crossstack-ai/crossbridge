"""
Neutral Intent Model (NIM) - Core Abstraction.

This model is framework-agnostic and language-agnostic.
It represents the SEMANTIC meaning of tests, not syntax.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class IntentType(str, Enum):
    """Type of test intent."""
    UI = "ui"
    API = "api"
    BDD = "bdd"
    UNIT = "unit"
    INTEGRATION = "integration"


class ActionType(str, Enum):
    """Type of action intent."""
    # UI Actions
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    HOVER = "hover"
    DRAG = "drag"
    NAVIGATE = "navigate"
    WAIT = "wait"
    SCROLL = "scroll"
    UPLOAD = "upload"
    
    # API Actions
    REQUEST = "request"
    AUTH = "auth"
    
    # Data Actions
    SET_DATA = "set_data"
    GET_DATA = "get_data"
    
    # Custom
    CUSTOM = "custom"


class AssertionType(str, Enum):
    """Type of assertion intent."""
    # Visibility
    VISIBLE = "visible"
    HIDDEN = "hidden"
    EXISTS = "exists"
    
    # State
    ENABLED = "enabled"
    DISABLED = "disabled"
    CHECKED = "checked"
    SELECTED = "selected"
    
    # Content
    EQUALS = "equals"
    CONTAINS = "contains"
    MATCHES = "matches"
    TEXT_CONTENT = "text_content"
    
    # API
    STATUS_CODE = "status_code"
    HEADER = "header"
    RESPONSE_BODY = "response_body"
    
    # Count
    COUNT = "count"
    
    # Custom
    CUSTOM = "custom"


@dataclass
class ActionIntent:
    """
    Framework-agnostic action representation.
    
    Represents what the test wants to DO, not how to do it.
    """
    action_type: ActionType
    target: str  # Logical name (e.g., "login_button", "user_endpoint")
    selector: Optional[str] = None  # Technical selector (e.g., "#login", "By.ID")
    value: Optional[Any] = None  # Value for fill, select, etc.
    
    # Semantic properties (framework-independent)
    semantics: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    description: str = ""
    line_number: Optional[int] = None
    confidence: float = 1.0  # 0.0 to 1.0
    
    # Additional metadata
    wait_strategy: Optional[str] = None  # "auto", "explicit", "implicit"
    retry_count: int = 0
    timeout: Optional[float] = None
    
    def __post_init__(self):
        """Validate and normalize action intent."""
        if isinstance(self.action_type, str):
            self.action_type = ActionType(self.action_type)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "action_type": self.action_type.value,
            "target": self.target,
            "selector": self.selector,
            "value": self.value,
            "semantics": self.semantics,
            "description": self.description,
            "line_number": self.line_number,
            "confidence": self.confidence,
            "wait_strategy": self.wait_strategy,
            "retry_count": self.retry_count,
            "timeout": self.timeout,
        }


@dataclass
class AssertionIntent:
    """
    Framework-agnostic assertion representation.
    
    Represents what the test wants to VERIFY, not how to verify it.
    """
    assertion_type: AssertionType
    target: str  # What to assert on
    expected: Any  # Expected value/state
    
    # Context
    description: str = ""
    operator: Optional[str] = None  # "==", "!=", ">", "contains", etc.
    message: Optional[str] = None  # Failure message
    
    # Technical details
    selector: Optional[str] = None
    attribute: Optional[str] = None  # For attribute assertions
    
    # Metadata
    line_number: Optional[int] = None
    confidence: float = 1.0
    
    def __post_init__(self):
        """Validate and normalize assertion intent."""
        if isinstance(self.assertion_type, str):
            self.assertion_type = AssertionType(self.assertion_type)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "assertion_type": self.assertion_type.value,
            "target": self.target,
            "expected": self.expected,
            "description": self.description,
            "operator": self.operator,
            "message": self.message,
            "selector": self.selector,
            "attribute": self.attribute,
            "line_number": self.line_number,
            "confidence": self.confidence,
        }


@dataclass
class TestIntent:
    """
    Complete framework-agnostic test representation.
    
    This is the core abstraction that bridges all frameworks.
    """
    test_type: IntentType
    name: str
    steps: List[ActionIntent] = field(default_factory=list)
    assertions: List[AssertionIntent] = field(default_factory=list)
    
    # Test structure
    setup_steps: List[ActionIntent] = field(default_factory=list)
    teardown_steps: List[ActionIntent] = field(default_factory=list)
    
    # Test data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    description: str = ""
    source_framework: str = ""
    source_file: str = ""
    
    # BDD-specific (optional)
    scenario: Optional[str] = None
    given_steps: List[ActionIntent] = field(default_factory=list)
    when_steps: List[ActionIntent] = field(default_factory=list)
    then_steps: List[AssertionIntent] = field(default_factory=list)
    
    # Page objects (if detected)
    page_objects: List[str] = field(default_factory=list)
    
    # Quality metrics
    confidence: float = 1.0  # Overall confidence
    complexity: int = 0  # Number of steps
    todos: List[str] = field(default_factory=list)  # Manual review needed
    
    def __post_init__(self):
        """Validate and compute derived properties."""
        if isinstance(self.test_type, str):
            self.test_type = IntentType(self.test_type)
        
        # Calculate complexity
        self.complexity = (
            len(self.steps) +
            len(self.assertions) +
            len(self.setup_steps) +
            len(self.teardown_steps)
        )
        
        # Calculate overall confidence (average of all intents)
        all_confidences = (
            [s.confidence for s in self.steps] +
            [a.confidence for a in self.assertions] +
            [s.confidence for s in self.setup_steps] +
            [s.confidence for s in self.teardown_steps]
        )
        if all_confidences:
            self.confidence = sum(all_confidences) / len(all_confidences)
    
    def add_step(self, step: ActionIntent):
        """Add a step to the test."""
        self.steps.append(step)
        self.complexity += 1
    
    def add_assertion(self, assertion: AssertionIntent):
        """Add an assertion to the test."""
        self.assertions.append(assertion)
        self.complexity += 1
    
    def add_todo(self, message: str):
        """Add a TODO for manual review."""
        self.todos.append(message)
    
    def has_data_driven(self) -> bool:
        """Check if test uses data-driven patterns."""
        return bool(self.data) or '@ParameterizedTest' in self.description or 'pytest.mark.parametrize' in self.description
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "test_type": self.test_type.value,
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
            "assertions": [a.to_dict() for a in self.assertions],
            "setup_steps": [s.to_dict() for s in self.setup_steps],
            "teardown_steps": [s.to_dict() for s in self.teardown_steps],
            "data": self.data,
            "tags": self.tags,
            "description": self.description,
            "source_framework": self.source_framework,
            "source_file": self.source_file,
            "scenario": self.scenario,
            "given_steps": [s.to_dict() for s in self.given_steps],
            "when_steps": [s.to_dict() for s in self.when_steps],
            "then_steps": [a.to_dict() for a in self.then_steps],
            "page_objects": self.page_objects,
            "confidence": self.confidence,
            "complexity": self.complexity,
            "todos": self.todos,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestIntent":
        """Create from dictionary."""
        # Convert nested structures
        steps = [ActionIntent(**s) for s in data.get("steps", [])]
        assertions = [AssertionIntent(**a) for a in data.get("assertions", [])]
        setup_steps = [ActionIntent(**s) for s in data.get("setup_steps", [])]
        teardown_steps = [ActionIntent(**s) for s in data.get("teardown_steps", [])]
        given_steps = [ActionIntent(**s) for s in data.get("given_steps", [])]
        when_steps = [ActionIntent(**s) for s in data.get("when_steps", [])]
        then_steps = [AssertionIntent(**a) for a in data.get("then_steps", [])]
        
        return cls(
            test_type=IntentType(data["test_type"]),
            name=data["name"],
            steps=steps,
            assertions=assertions,
            setup_steps=setup_steps,
            teardown_steps=teardown_steps,
            data=data.get("data", {}),
            tags=data.get("tags", []),
            description=data.get("description", ""),
            source_framework=data.get("source_framework", ""),
            source_file=data.get("source_file", ""),
            scenario=data.get("scenario"),
            given_steps=given_steps,
            when_steps=when_steps,
            then_steps=then_steps,
            page_objects=data.get("page_objects", []),
            confidence=data.get("confidence", 1.0),
            complexity=data.get("complexity", 0),
            todos=data.get("todos", []),
        )
