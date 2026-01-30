# Copyright (c) 2025 Vikas Verma
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""
Playwright Trace Parser for CrossBridge Intelligence.

Parse Playwright trace files for deep execution analysis:
- Action timeline and timing
- Network requests and responses
- Console logs and errors
- Screenshots and videos
- Performance metrics
"""

import json
import logging
import zipfile
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PlaywrightAction:
    """Represents a Playwright action."""
    type: str  # 'click', 'fill', 'goto', 'wait', etc.
    selector: Optional[str] = None
    value: Optional[str] = None
    url: Optional[str] = None
    timestamp: float = 0.0
    duration_ms: float = 0.0
    error: Optional[str] = None
    stack_trace: Optional[List[str]] = None


@dataclass
class PlaywrightNetworkRequest:
    """Represents a network request."""
    method: str  # GET, POST, etc.
    url: str
    status: int = 0
    duration_ms: float = 0.0
    request_headers: Dict[str, str] = field(default_factory=dict)
    response_headers: Dict[str, str] = field(default_factory=dict)
    request_body: Optional[str] = None
    response_body: Optional[str] = None
    timestamp: float = 0.0


@dataclass
class PlaywrightConsoleMessage:
    """Represents a console log message."""
    type: str  # 'log', 'error', 'warn', 'info'
    text: str
    location: Optional[str] = None
    timestamp: float = 0.0


@dataclass
class PlaywrightScreenshot:
    """Represents a screenshot."""
    path: str
    timestamp: float = 0.0
    width: int = 0
    height: int = 0


@dataclass
class PlaywrightTraceResult:
    """Complete Playwright trace analysis result."""
    test_name: str
    duration_ms: float = 0.0
    actions: List[PlaywrightAction] = field(default_factory=list)
    network_requests: List[PlaywrightNetworkRequest] = field(default_factory=list)
    console_messages: List[PlaywrightConsoleMessage] = field(default_factory=list)
    screenshots: List[PlaywrightScreenshot] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def get_failed_actions(self) -> List[PlaywrightAction]:
        """Get all actions that failed."""
        return [a for a in self.actions if a.error]
    
    def get_api_calls(self) -> List[PlaywrightNetworkRequest]:
        """Get API calls (JSON requests)."""
        return [r for r in self.network_requests 
                if 'application/json' in r.request_headers.get('content-type', '').lower()
                or 'application/json' in r.response_headers.get('content-type', '').lower()]
    
    def get_slow_actions(self, threshold_ms: float = 1000) -> List[PlaywrightAction]:
        """Get actions slower than threshold."""
        return [a for a in self.actions if a.duration_ms > threshold_ms]
    
    def get_slow_requests(self, threshold_ms: float = 1000) -> List[PlaywrightNetworkRequest]:
        """Get network requests slower than threshold."""
        return [r for r in self.network_requests if r.duration_ms > threshold_ms]


class PlaywrightTraceParser:
    """
    Parse Playwright trace files (.zip format).
    
    Playwright traces contain:
    - trace.json: Action timeline
    - trace.network: Network activity
    - trace-resources/: Screenshots, videos, etc.
    """
    
    def __init__(self):
        self.trace_data = None
    
    def parse_trace(self, trace_path: Path) -> Optional[PlaywrightTraceResult]:
        """
        Parse Playwright trace file.
        
        Args:
            trace_path: Path to trace.zip file
            
        Returns:
            PlaywrightTraceResult or None if parsing fails
        """
        try:
            if not trace_path.exists():
                logger.error(f"Trace file not found: {trace_path}")
                return None
            
            # Extract trace data from zip
            with zipfile.ZipFile(trace_path, 'r') as zip_ref:
                # Read trace.json (main timeline)
                if 'trace.json' in zip_ref.namelist():
                    trace_json = json.loads(zip_ref.read('trace.json'))
                else:
                    # Try alternative names
                    json_files = [f for f in zip_ref.namelist() if f.endswith('.json')]
                    if not json_files:
                        logger.error("No trace JSON found in archive")
                        return None
                    trace_json = json.loads(zip_ref.read(json_files[0]))
                
                # Read network data if available
                network_data = None
                if 'trace.network' in zip_ref.namelist():
                    network_data = json.loads(zip_ref.read('trace.network'))
                
                self.trace_data = trace_json
            
            # Parse the trace
            result = self._parse_trace_data(trace_json, network_data)
            
            logger.info(f"Parsed trace: {len(result.actions)} actions, "
                       f"{len(result.network_requests)} requests, "
                       f"{len(result.errors)} errors")
            
            return result
            
        except zipfile.BadZipFile:
            logger.error(f"Invalid zip file: {trace_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in trace: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse trace {trace_path}: {e}")
            return None
    
    def _parse_trace_data(self, trace_json: Dict, network_data: Optional[Dict]) -> PlaywrightTraceResult:
        """Parse trace JSON data."""
        result = PlaywrightTraceResult(
            test_name=trace_json.get('name', 'Unknown')
        )
        
        # Extract actions from events
        events = trace_json.get('events', [])
        result.actions = self._parse_actions(events)
        
        # Calculate total duration
        if result.actions:
            start_time = min(a.timestamp for a in result.actions if a.timestamp > 0)
            end_time = max(a.timestamp + a.duration_ms for a in result.actions)
            result.duration_ms = end_time - start_time
        
        # Parse network requests
        if network_data:
            result.network_requests = self._parse_network_requests(network_data)
        elif 'resources' in trace_json:
            result.network_requests = self._parse_network_from_trace(trace_json['resources'])
        
        # Parse console messages
        result.console_messages = self._parse_console_messages(events)
        
        # Parse screenshots
        result.screenshots = self._parse_screenshots(trace_json)
        
        # Extract errors
        result.errors = self._extract_errors(events)
        
        # Calculate performance metrics
        result.performance_metrics = self._calculate_performance_metrics(result)
        
        return result
    
    def _parse_actions(self, events: List[Dict]) -> List[PlaywrightAction]:
        """Parse actions from trace events."""
        actions = []
        
        # Playwright trace events have type: 'action'
        for event in events:
            if event.get('type') == 'action' or 'method' in event:
                action_type = event.get('method', event.get('apiName', 'unknown'))
                
                # Extract details
                params = event.get('params', {})
                metadata = event.get('metadata', {})
                
                action = PlaywrightAction(
                    type=action_type,
                    selector=params.get('selector'),
                    value=params.get('value') or params.get('text'),
                    url=params.get('url'),
                    timestamp=event.get('startTime', 0),
                    duration_ms=event.get('duration', 0),
                    error=metadata.get('error'),
                    stack_trace=metadata.get('stack')
                )
                
                actions.append(action)
        
        return actions
    
    def _parse_network_requests(self, network_data: Dict) -> List[PlaywrightNetworkRequest]:
        """Parse network requests from separate network file."""
        requests = []
        
        for request_data in network_data.get('requests', []):
            request = PlaywrightNetworkRequest(
                method=request_data.get('method', 'GET'),
                url=request_data.get('url', ''),
                status=request_data.get('status', 0),
                duration_ms=request_data.get('duration', 0),
                request_headers=request_data.get('requestHeaders', {}),
                response_headers=request_data.get('responseHeaders', {}),
                request_body=request_data.get('requestBody'),
                response_body=request_data.get('responseBody'),
                timestamp=request_data.get('timestamp', 0)
            )
            requests.append(request)
        
        return requests
    
    def _parse_network_from_trace(self, resources: List[Dict]) -> List[PlaywrightNetworkRequest]:
        """Parse network requests from trace resources."""
        requests = []
        
        for resource in resources:
            if resource.get('resourceType') == 'fetch' or resource.get('resourceType') == 'xhr':
                request = PlaywrightNetworkRequest(
                    method=resource.get('request', {}).get('method', 'GET'),
                    url=resource.get('request', {}).get('url', ''),
                    status=resource.get('response', {}).get('status', 0),
                    duration_ms=resource.get('duration', 0),
                    request_headers=resource.get('request', {}).get('headers', {}),
                    response_headers=resource.get('response', {}).get('headers', {}),
                    timestamp=resource.get('timestamp', 0)
                )
                requests.append(request)
        
        return requests
    
    def _parse_console_messages(self, events: List[Dict]) -> List[PlaywrightConsoleMessage]:
        """Parse console messages from events."""
        messages = []
        
        for event in events:
            if event.get('type') == 'console' or event.get('method') == 'console':
                message_type = event.get('messageType', 'log')
                text = event.get('text', event.get('message', ''))
                
                message = PlaywrightConsoleMessage(
                    type=message_type,
                    text=text,
                    location=event.get('location'),
                    timestamp=event.get('timestamp', 0)
                )
                messages.append(message)
        
        return messages
    
    def _parse_screenshots(self, trace_json: Dict) -> List[PlaywrightScreenshot]:
        """Parse screenshots from trace."""
        screenshots = []
        
        # Screenshots are in resources or snapshots
        resources = trace_json.get('resources', [])
        for resource in resources:
            if resource.get('resourceType') == 'screenshot':
                screenshot = PlaywrightScreenshot(
                    path=resource.get('path', ''),
                    timestamp=resource.get('timestamp', 0),
                    width=resource.get('width', 0),
                    height=resource.get('height', 0)
                )
                screenshots.append(screenshot)
        
        return screenshots
    
    def _extract_errors(self, events: List[Dict]) -> List[str]:
        """Extract error messages from events."""
        errors = []
        
        for event in events:
            # Check for errors in metadata
            metadata = event.get('metadata', {})
            if metadata.get('error'):
                errors.append(metadata['error'])
            
            # Check for console errors
            if event.get('type') == 'console' and event.get('messageType') == 'error':
                errors.append(event.get('text', 'Unknown error'))
            
            # Check for failed actions
            if event.get('type') == 'action' and event.get('status') == 'failed':
                method = event.get('method', 'Unknown action')
                errors.append(f"{method} failed")
        
        return errors
    
    def _calculate_performance_metrics(self, result: PlaywrightTraceResult) -> Dict[str, Any]:
        """Calculate performance metrics."""
        metrics = {
            'total_duration_ms': result.duration_ms,
            'total_actions': len(result.actions),
            'total_network_requests': len(result.network_requests),
            'total_errors': len(result.errors),
            'failed_actions': len(result.get_failed_actions()),
            'api_calls': len(result.get_api_calls()),
        }
        
        # Action timing stats
        if result.actions:
            action_durations = [a.duration_ms for a in result.actions if a.duration_ms > 0]
            if action_durations:
                metrics['avg_action_duration_ms'] = sum(action_durations) / len(action_durations)
                metrics['max_action_duration_ms'] = max(action_durations)
                metrics['min_action_duration_ms'] = min(action_durations)
        
        # Network timing stats
        if result.network_requests:
            request_durations = [r.duration_ms for r in result.network_requests if r.duration_ms > 0]
            if request_durations:
                metrics['avg_request_duration_ms'] = sum(request_durations) / len(request_durations)
                metrics['max_request_duration_ms'] = max(request_durations)
                metrics['min_request_duration_ms'] = min(request_durations)
        
        # Error rate
        if result.actions:
            metrics['error_rate'] = len(result.get_failed_actions()) / len(result.actions)
        
        return metrics
    
    def get_test_summary(self, result: PlaywrightTraceResult) -> Dict[str, Any]:
        """Get human-readable test summary."""
        return {
            'test_name': result.test_name,
            'duration': f"{result.duration_ms:.0f}ms",
            'total_actions': len(result.actions),
            'failed_actions': len(result.get_failed_actions()),
            'network_requests': len(result.network_requests),
            'api_calls': len(result.get_api_calls()),
            'console_errors': len([m for m in result.console_messages if m.type == 'error']),
            'screenshots': len(result.screenshots),
            'success': len(result.errors) == 0,
        }


# ============================================================================
# Convenience Functions
# ============================================================================

def parse_playwright_trace(trace_path: Path) -> Optional[PlaywrightTraceResult]:
    """
    Convenience function to parse Playwright trace.
    
    Args:
        trace_path: Path to trace.zip file
        
    Returns:
        PlaywrightTraceResult or None
    """
    parser = PlaywrightTraceParser()
    return parser.parse_trace(trace_path)


def analyze_playwright_performance(trace_path: Path) -> Dict[str, Any]:
    """
    Quick performance analysis of Playwright trace.
    
    Args:
        trace_path: Path to trace.zip file
        
    Returns:
        Dict with performance insights
    """
    result = parse_playwright_trace(trace_path)
    if not result:
        return {}
    
    return {
        'duration_ms': result.duration_ms,
        'slow_actions': len(result.get_slow_actions()),
        'slow_requests': len(result.get_slow_requests()),
        'failed_actions': len(result.get_failed_actions()),
        'error_rate': result.performance_metrics.get('error_rate', 0),
        'avg_action_time': result.performance_metrics.get('avg_action_duration_ms', 0),
        'avg_request_time': result.performance_metrics.get('avg_request_duration_ms', 0),
    }
