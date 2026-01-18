"""
CrossBridge Event Models

Defines the standard event contract for all framework hooks.
Events are emitted by test frameworks and consumed by CrossBridge observer.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import json


class EventType(str, Enum):
    """Standard event types across all frameworks"""
    TEST_START = "test_start"
    TEST_END = "test_end"
    STEP = "step"
    API_CALL = "api_call"
    UI_INTERACTION = "ui_interaction"
    ASSERTION = "assertion"
    ERROR = "error"
    NETWORK_CAPTURE = "network_capture"


@dataclass
class CrossBridgeEvent:
    """
    Base event schema for all CrossBridge framework hooks.
    
    This is the single event contract that all frameworks must emit.
    CrossBridge never controls execution - it only observes via these events.
    """
    
    # Required fields (common across all frameworks)
    event_type: str              # test_start | test_end | step | api_call
    framework: str               # pytest | robot | playwright | cypress | selenium
    test_id: str                 # Unique test identifier (framework-specific format)
    timestamp: datetime          # When event occurred
    
    # Optional fields (populated based on event type)
    status: Optional[str] = None        # passed | failed | skipped | error
    duration_ms: Optional[int] = None   # Execution duration
    error_message: Optional[str] = None # Failure/error details
    stack_trace: Optional[str] = None   # Full stack trace if error
    
    # Version tracking (for coverage by version analysis)
    application_version: Optional[str] = None  # e.g., "2.1.0", "v3.0.0-beta"
    product_name: Optional[str] = None         # e.g., "MyWebApp", "PaymentAPI"
    environment: Optional[str] = None          # e.g., "dev", "staging", "production"
    
    # Extensible metadata (framework-specific data)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Versioning for backward compatibility
    schema_version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime to ISO format
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CrossBridgeEvent':
        """Create event from dictionary"""
        # Convert ISO timestamp back to datetime
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class TestStartEvent(CrossBridgeEvent):
    """Event emitted when test execution starts"""
    
    def __init__(self, framework: str, test_id: str, **kwargs):
        super().__init__(
            event_type=EventType.TEST_START,
            framework=framework,
            test_id=test_id,
            timestamp=datetime.now(),
            **kwargs
        )


@dataclass
class TestEndEvent(CrossBridgeEvent):
    """Event emitted when test execution completes"""
    
    def __init__(
        self, 
        framework: str, 
        test_id: str, 
        status: str, 
        duration_ms: int,
        **kwargs
    ):
        super().__init__(
            event_type=EventType.TEST_END,
            framework=framework,
            test_id=test_id,
            timestamp=datetime.now(),
            status=status,
            duration_ms=duration_ms,
            **kwargs
        )


@dataclass
class ApiCallEvent(CrossBridgeEvent):
    """Event emitted when API call is made during test"""
    
    def __init__(
        self,
        framework: str,
        test_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        **kwargs
    ):
        metadata = kwargs.pop('metadata', {})
        metadata.update({
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code
        })
        
        super().__init__(
            event_type=EventType.API_CALL,
            framework=framework,
            test_id=test_id,
            timestamp=datetime.now(),
            metadata=metadata,
            **kwargs
        )


@dataclass
class UiInteractionEvent(CrossBridgeEvent):
    """Event emitted when UI interaction occurs"""
    
    def __init__(
        self,
        framework: str,
        test_id: str,
        component_name: str,
        interaction_type: str,
        page_url: str,
        **kwargs
    ):
        metadata = kwargs.pop('metadata', {})
        metadata.update({
            'component_name': component_name,
            'interaction_type': interaction_type,
            'page_url': page_url
        })
        
        super().__init__(
            event_type=EventType.UI_INTERACTION,
            framework=framework,
            test_id=test_id,
            timestamp=datetime.now(),
            metadata=metadata,
            **kwargs
        )


@dataclass
class StepEvent(CrossBridgeEvent):
    """Event emitted for test step execution (BDD/keyword frameworks)"""
    
    def __init__(
        self,
        framework: str,
        test_id: str,
        step_name: str,
        step_status: str,
        **kwargs
    ):
        metadata = kwargs.pop('metadata', {})
        metadata.update({
            'step_name': step_name,
            'step_status': step_status
        })
        
        super().__init__(
            event_type=EventType.STEP,
            framework=framework,
            test_id=test_id,
            timestamp=datetime.now(),
            status=step_status,
            metadata=metadata,
            **kwargs
        )
