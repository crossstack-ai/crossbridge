"""
Failure Deduplication & Root Cause Clustering

Intelligently clusters test failures to identify root causes and reduce noise.
Avoids showing duplicate failures across multiple test cases.

Features:
- Error message similarity detection
- Stack trace fingerprinting
- HTTP status code clustering
- Keyword signature matching
- Severity-based prioritization
"""

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum

from core.logging import get_logger, LogCategory

# Get logger with EXECUTION category for test result analysis
logger = get_logger(__name__, category=LogCategory.EXECUTION)


class FailureSeverity(str, Enum):
    """Failure severity levels for prioritization."""
    CRITICAL = "critical"      # System crashes, data corruption
    HIGH = "high"              # Test failures, assertion errors
    MEDIUM = "medium"          # Timeouts, network issues
    LOW = "low"                # Warnings, deprecations


class FailureDomain(str, Enum):
    """Failure domain classification for root cause analysis."""
    INFRA = "infrastructure"           # SSH failures, connection refused, VM issues
    ENVIRONMENT = "environment"         # Config missing, env vars, setup issues
    TEST_AUTOMATION = "test_automation" # Test code bugs, IndexError, framework issues
    PRODUCT = "product"                # API errors, application bugs, business logic
    UNKNOWN = "unknown"                # Cannot be classified


@dataclass
class ClusteredFailure:
    """
    Represents a single failure instance within a cluster.
    
    Attributes:
        test_name: Name of the failed test
        keyword_name: Name of the failed keyword (if applicable)
        error_message: Full error message
        stack_trace: Stack trace if available
        library: Library/module name if applicable
        http_status: HTTP status code if network-related
        timestamp: Failure timestamp if available
        domain: Failure domain classification (INFRA/ENVIRONMENT/TEST_AUTOMATION/PRODUCT)
    """
    test_name: str
    keyword_name: Optional[str] = None
    error_message: str = ""
    stack_trace: Optional[str] = None
    library: Optional[str] = None
    http_status: Optional[int] = None
    timestamp: Optional[str] = None
    domain: FailureDomain = FailureDomain.UNKNOWN
    metadata: Dict = field(default_factory=dict)


@dataclass
class FailureCluster:
    """
    Represents a cluster of related failures sharing the same root cause.
    
    Attributes:
        fingerprint: Unique hash identifying this cluster
        root_cause: Normalized error message representing the root cause
        severity: Severity level of this cluster
        domain: Failure domain classification
        failure_count: Number of failures in this cluster
        failures: List of individual failure instances
        keywords: Set of affected keywords
        tests: Set of affected test names
        error_patterns: Common patterns found in errors
        suggested_fix: Optional suggestion for fixing this issue
    """
    fingerprint: str
    root_cause: str
    severity: FailureSeverity
    domain: FailureDomain = FailureDomain.UNKNOWN
    failure_count: int = 0
    failures: List[ClusteredFailure] = field(default_factory=list)
    keywords: Set[str] = field(default_factory=set)
    tests: Set[str] = field(default_factory=set)
    error_patterns: List[str] = field(default_factory=list)
    suggested_fix: Optional[str] = None
    
    def add_failure(self, failure: ClusteredFailure):
        """Add a failure to this cluster."""
        self.failures.append(failure)
        self.failure_count += 1
        self.tests.add(failure.test_name)
        if failure.keyword_name:
            self.keywords.add(failure.keyword_name)


def fingerprint_error(
    error_message: str,
    stack_trace: Optional[str] = None,
    http_status: Optional[int] = None
) -> str:
    """
    Generate a unique fingerprint for an error based on its characteristics.
    
    This function normalizes the error message by:
    - Converting to lowercase
    - Removing variable portions (timestamps, IDs, URLs)
    - Extracting exception types
    - Incorporating HTTP status codes if present
    - Using stack trace patterns if available
    
    Args:
        error_message: The error message to fingerprint
        stack_trace: Optional stack trace for additional context
        http_status: Optional HTTP status code
        
    Returns:
        MD5 hash of the normalized error signature
        
    Examples:
        >>> fingerprint_error("ElementNotFound: Could not find element #btn-123")
        'a1b2c3d4e5f6...'
        >>> fingerprint_error("Timeout after 30000ms")
        'f6e5d4c3b2a1...'
    """
    # Start with normalized error message
    normalized = error_message.lower().strip()
    
    # Remove common variable portions
    # - Timestamps: "2024-01-15 10:30:45" or "10:30:45.123"
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}[\s:]\d{2}:\d{2}:\d{2}', '<timestamp>', normalized)
    normalized = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3}', '<timestamp>', normalized)
    
    # - IDs and numbers: "element-123", "timeout: 30000ms", "#btn-login", etc.
    normalized = re.sub(r'#[a-z0-9\-_]+', '#<id>', normalized)  # HTML IDs like #btn-login
    normalized = re.sub(r'[#\-]\d{3,}', '<id>', normalized)
    normalized = re.sub(r'\d{3,}ms', '<time>ms', normalized)
    normalized = re.sub(r'\d+px', '<px>px', normalized)
    
    # - Specific element names/IDs that vary (e.g., "button", "link", "login", "signup")
    # Replace common UI element names with generic placeholder
    normalized = re.sub(r'\b(button|link|input|form|div|span|menu|dropdown)\b', '<element>', normalized)
    normalized = re.sub(r'btn-\w+', 'btn-<name>', normalized)
    
    # - URLs and paths
    normalized = re.sub(r'https?://[^\s]+', '<url>', normalized)
    normalized = re.sub(r'[a-z]:[/\\][\w/\\]+', '<path>', normalized)
    normalized = re.sub(r'/[\w/\-\.]+', '<path>', normalized)
    
    # - Line numbers: "at line 42", "line: 123"
    normalized = re.sub(r'\bline[:\s]+\d+', 'line:<num>', normalized)
    
    # - Memory addresses: "0x7f1234abcd"
    normalized = re.sub(r'0x[0-9a-f]{6,}', '<addr>', normalized)
    
    # Extract exception type (most significant part)
    exception_match = re.search(
        r'(\w+(?:exception|error|notfound))\s*:',
        normalized,
        re.IGNORECASE
    )
    exception_type = exception_match.group(1) if exception_match else None
    
    # Build signature components
    signature_parts = []
    
    if exception_type:
        signature_parts.append(f"exception:{exception_type}")
    
    if http_status:
        signature_parts.append(f"http:{http_status}")
    
    # Add normalized message (truncated for consistency)
    signature_parts.append(normalized[:200])
    
    # Include stack trace pattern if available
    if stack_trace:
        # Extract just the top frame location
        stack_normalized = stack_trace.lower().strip()
        frame_match = re.search(
            r'at\s+([\w\.]+)\s*\(',
            stack_normalized
        )
        if frame_match:
            signature_parts.append(f"frame:{frame_match.group(1)}")
    
    # Combine and hash
    signature = "|".join(signature_parts)
    return hashlib.md5(signature.encode('utf-8')).hexdigest()


def _detect_severity(
    error_message: str, 
    keyword_name: Optional[str] = None,
    http_status: Optional[int] = None
) -> FailureSeverity:
    """
    Detect the severity level of a failure based on error characteristics.
    
    Uses a comprehensive rule-based scoring system to determine failure impact:
    - HTTP status codes (if available)
    - Error message patterns
    - Exception types
    - Keyword context
    
    Args:
        error_message: The error message
        keyword_name: Optional keyword name for context
        http_status: Optional HTTP status code
        
    Returns:
        Detected severity level (CRITICAL, HIGH, MEDIUM, or LOW)
    """
    error_lower = error_message.lower()
    
    # HTTP Status Code Priority (most reliable indicator)
    if http_status:
        # CRITICAL: Server errors that indicate system failure
        if http_status in [500, 501, 507, 508, 511]:  # 500 Internal Server Error, etc.
            return FailureSeverity.CRITICAL
        
        # HIGH: Server errors and client errors indicating functional issues
        if http_status in [502, 503, 504]:  # Bad Gateway, Service Unavailable, Gateway Timeout
            return FailureSeverity.HIGH
        if http_status in [400, 401, 403, 404, 409, 422]:  # Client errors
            return FailureSeverity.HIGH
        
        # MEDIUM: Temporary/retryable issues
        if http_status in [408, 429]:  # Request Timeout, Too Many Requests
            return FailureSeverity.MEDIUM
        
        # LOW: Informational or successful with warnings
        if http_status in [300, 301, 302, 303, 304, 307, 308]:  # Redirects
            return FailureSeverity.LOW
    
    # CRITICAL: System crashes, data corruption, security issues
    critical_patterns = [
        # System failures
        r'\bcrash\b', r'core dump', r'segmentation fault', r'\bfatal\b',
        r'out\s*of\s*memory', r'memory leak', r'stack overflow',
        # Data integrity
        r'data corruption', r'corrupt.*database', r'integrity.*violation',
        # Security
        r'\bunauthorized\b', r'permission denied', r'access denied',
        r'authentication.*fail', r'security.*violation', r'security.*exception',
        r'access.*violation',
        # Service failures
        r'cannot.*start', r'system.*down', r'service.*unavailable.*critical',
        r'database.*down', r'server.*crash',
        # API critical errors
        r'http\s*500', r'internal\s*server\s*error', r'500\s*error'
    ]
    for pattern in critical_patterns:
        if re.search(pattern, error_lower):
            return FailureSeverity.CRITICAL
    
    # HIGH: Test failures, assertion errors, functional failures
    high_patterns = [
        # Test/Assertion failures
        r'assertion.*fail', r'expected.*but.*was', r'should.*equal',
        r'test.*fail', r'verification.*fail', r'validation.*fail',
        # Element/UI issues
        r'element.*not.*found', r'no such element', r'locator.*fail',
        r'unable to.*locate', r'selector.*not.*found',
        # Operation failures
        r'unable to.*perform', r'operation.*failed', r'command.*failed',
        r'execution.*failed', r'process.*failed',
        # API/HTTP errors
        r'http\s*40[0-4]', r'not found.*404', r'forbidden.*403',
        r'bad request.*400', r'unauthorized.*401',
        # Database errors (must come before connection patterns in MEDIUM)
        r'sql.*error', r'sqlexception', r'query.*failed', r'deadlock',
        r'constraint.*violation', r'duplicate\s*key',
        # Business logic
        r'business.*rule.*violation', r'invalid.*state', r'precondition.*failed'
    ]
    for pattern in high_patterns:
        if re.search(pattern, error_lower):
            return FailureSeverity.HIGH
    
    # MEDIUM: Timeouts, network issues, retryable errors
    medium_patterns = [
        # Timeouts
        r'\btimeout\b', r'timed out', r'time.*out.*exception',
        r'operation.*timeout', r'request.*timeout',
        # Network issues (after database patterns to avoid conflicts)
        r'connection.*refused', r'cannot.*connect', r'connection.*failed',
        r'connection.*closed',
        r'network.*error', r'socket.*error', r'connection.*reset',
        r'dns.*error', r'host.*not.*found',
        # Service temporarily unavailable
        r'service.*unavailable', r'temporarily.*unavailable',
        r'http\s*50[2-4]', r'bad gateway', r'gateway.*timeout',
        # Retryable errors
        r'retry.*exceeded', r'max.*retries', r'too many.*requests',
        r'rate.*limit', r'throttled'
    ]
    for pattern in medium_patterns:
        if re.search(pattern, error_lower):
            return FailureSeverity.MEDIUM
    
    # LOW: Warnings, deprecations, non-critical issues
    low_patterns = [
        # Warnings
        r'\bwarning\b', r'\bwarn\b', r'deprecation.*warning',
        # Non-critical
        r'skipped', r'ignored', r'optional.*fail',
        r'informational', r'notice',
        # Redirects
        r'redirect', r'moved.*permanently', r'http.*30[0-8]'
    ]
    for pattern in low_patterns:
        if re.search(pattern, error_lower):
            return FailureSeverity.LOW
    
    # Default to HIGH for unclassified failures
    return FailureSeverity.HIGH


# Severity scoring rules for export/documentation
SEVERITY_RULES = {
    "CRITICAL": {
        "description": "System crashes, data corruption, security violations",
        "http_codes": [500, 501, 507, 508, 511],
        "patterns": [
            "crash", "fatal", "out of memory", "data corruption",
            "unauthorized", "permission denied", "system down",
            "http 500", "internal server error"
        ],
        "impact": "Immediate attention required - system or data integrity at risk"
    },
    "HIGH": {
        "description": "Test failures, functional defects, assertion errors",
        "http_codes": [400, 401, 403, 404, 409, 422, 502, 503, 504],
        "patterns": [
            "assertion fail", "expected but was", "element not found",
            "test fail", "operation failed", "http 404", "http 403",
            "sql error", "validation fail"
        ],
        "impact": "Functional issue - requires investigation and fix"
    },
    "MEDIUM": {
        "description": "Timeouts, network issues, retryable errors",
        "http_codes": [408, 429],
        "patterns": [
            "timeout", "connection refused", "network error",
            "service unavailable", "retry exceeded", "rate limit"
        ],
        "impact": "Temporary or environmental issue - may resolve with retry"
    },
    "LOW": {
        "description": "Warnings, deprecations, non-critical issues",
        "http_codes": [300, 301, 302, 303, 304, 307, 308],
        "patterns": [
            "warning", "deprecation", "skipped", "redirect"
        ],
        "impact": "Informational - no immediate action required"
    }
}


def _classify_failure_domain(
    error_message: str,
    stack_trace: Optional[str] = None,
    library: Optional[str] = None
) -> FailureDomain:
    """
    Classify the failure domain based on error patterns.
    
    Categorizes failures into infrastructure, environment, test automation,
    or product domains to help route issues to the right teams.
    
    Args:
        error_message: The error message text
        stack_trace: Optional stack trace for additional context
        library: Optional library name that raised the error
        
    Returns:
        FailureDomain classification
        
    Examples:
        >>> _classify_failure_domain("SSH connection refused")
        FailureDomain.INFRA
        
        >>> _classify_failure_domain("IndexError: list index out of range")
        FailureDomain.TEST_AUTOMATION
        
        >>> _classify_failure_domain("HTTP 500 Internal Server Error")
        FailureDomain.PRODUCT
    """
    error_lower = error_message.lower()
    stack_lower = stack_trace.lower() if stack_trace else ""
    combined = f"{error_lower} {stack_lower}"
    
    # Early check for test framework fixtures (before environment checks)
    if re.search(r'fixture', combined):
        logger.debug(f"Classified as TEST_AUTOMATION: fixture detected")
        return FailureDomain.TEST_AUTOMATION
    
    # INFRA: SSH failures, connection refused, VM issues, network infrastructure
    infra_patterns = [
        # SSH and remote access
        r'\bssh\b', r'ssh.*fail', r'ssh.*connection', r'ssh.*timeout',
        # VM and infrastructure
        r'\bvm\b.*not.*found', r'virtual.*machine.*not.*found',
        r'instance.*not.*found', r'host.*not.*found', r'host.*unreachable',
        # Network infrastructure
        r'connection.*refused', r'connection.*reset', r'connection.*timed.*out',
        r'network.*unreachable', r'no.*route.*to.*host',
        # DNS and routing
        r'dns.*resolution.*fail', r'dns.*error', r'name.*resolution.*fail',
        # Port and socket issues
        r'port.*\d+.*closed', r'socket.*connection.*refused',
        r'unable.*to.*reach.*port', r'connection.*actively.*refused',
        # Cloud infrastructure
        r'cloud.*resource.*not.*found', r'ec2.*instance', r'azure.*vm'
    ]
    for pattern in infra_patterns:
        if re.search(pattern, combined):
            logger.debug(f"Classified as INFRA: matched pattern '{pattern}'")
            return FailureDomain.INFRA
    
    # ENVIRONMENT: Config missing, environment variables, setup issues
    environment_patterns = [
        # Configuration
        r'config.*not.*found', r'configuration.*missing', r'config.*error',
        r'missing.*configuration', r'invalid.*configuration',
        # Environment variables
        r'environment.*variable.*not.*set', r'env.*var.*missing',
        r'\$\{.*\}.*not.*found', r'environment.*not.*configured',
        # File/path issues
        r'file.*not.*found', r'path.*does.*not.*exist', r'directory.*not.*found',
        r'no.*such.*file.*or.*directory', r'\.env.*not.*found',
        # Dependencies and setup
        r'module.*not.*found', r'package.*not.*installed', r'dependency.*missing',
        r'import.*error', r'cannot.*import', r'no.*module.*named',
        # Properties and setup
        r'property.*not.*set', r'system.*property.*missing',
        r'setup.*fail', r'initialization.*error', r'bootstrap.*fail',
        # Credentials and secrets
        r'credentials.*not.*found', r'api.*key.*missing', r'secret.*not.*configured',
        r'authentication.*credentials.*not.*found'
    ]
    for pattern in environment_patterns:
        if re.search(pattern, combined):
            logger.debug(f"Classified as ENVIRONMENT: matched pattern '{pattern}'")
            return FailureDomain.ENVIRONMENT
    
    # TEST_AUTOMATION: Test code bugs, framework issues, automation errors
    test_automation_patterns = [
        # Python test errors
        r'\bindexerror\b', r'list.*index.*out.*of.*range', r'index.*out.*of.*bounds',
        r'\bkeyerror\b', r'key.*not.*found.*in.*dict', r'dictionary.*key.*error',
        r'\battributeerror\b', r'has.*no.*attribute', r'object.*has.*no.*attribute',
        r'\btypeerror\b', r'type.*error', r'unexpected.*type',
        r'\bnameerror\b', r'name.*is.*not.*defined',
        # Java test errors
        r'nullpointerexception', r'null.*pointer', r'arrayindexoutofboundsexception',
        # Element locator issues (test automation specific)
        r'element.*not.*found', r'locator.*not.*found', r'unable.*to.*locate.*element',
        r'no.*such.*element', r'stale.*element.*reference', r'element.*not.*visible',
        r'element.*not.*interactable', r'element.*click.*intercepted',
        # Test framework errors
        r'test.*setup.*fail', r'test.*teardown.*fail', r'fixture.*error',
        r'before.*hook.*fail', r'after.*hook.*fail',
        # Selenium/WebDriver specific
        r'webdriver.*exception', r'selenium.*exception', r'driver.*not.*found',
        r'browser.*not.*found', r'driver.*executable.*not.*found',
        # Assertion in test code (not product assertions)
        r'assert.*fail.*in.*test', r'test.*assertion.*fail',
        # Page object issues
        r'page.*object.*error', r'locator.*strategy.*fail',
        # Wait/sync issues in automation
        r'implicit.*wait', r'explicit.*wait.*fail', r'element.*wait.*timeout'
    ]
    
    # Check if error originates from test code (stack trace analysis)
    test_code_indicators = [
        r'test_.*\.py', r'.*_test\.py', r'tests?/', r'spec\.js',
        r'\.spec\.', r'\.test\.', r'test.*suite', r'conftest\.py'
    ]
    
    has_test_pattern = any(re.search(pattern, combined) for pattern in test_automation_patterns)
    has_test_code = any(re.search(indicator, stack_lower) for indicator in test_code_indicators)
    
    if has_test_pattern or has_test_code:
        logger.debug(f"Classified as TEST_AUTOMATION: automation error detected")
        return FailureDomain.TEST_AUTOMATION
    
    # PRODUCT: API errors, application bugs, business logic failures
    product_patterns = [
        # HTTP errors from product APIs
        r'http.*40[0-9]', r'http.*50[0-9]', r'status.*code.*[45]\d{2}',
        r'bad.*request', r'unauthorized', r'forbidden', r'not.*found.*404',
        r'internal.*server.*error', r'service.*unavailable',
        # API and service errors
        r'api.*error', r'api.*fail', r'rest.*api.*error', r'graphql.*error',
        r'endpoint.*error', r'service.*error', r'microservice.*fail',
        # Business logic
        r'business.*rule.*violation', r'business.*logic.*error',
        r'validation.*fail', r'invalid.*input', r'constraint.*violation',
        # Database errors (product-level)
        r'database.*error', r'sql.*exception', r'query.*fail',
        r'deadlock.*detected', r'duplicate.*key', r'foreign.*key.*constraint',
        # Application-level errors
        r'application.*error', r'runtime.*error', r'execution.*error',
        r'operation.*fail', r'transaction.*fail', r'rollback.*fail',
        # Product-specific
        r'authentication.*fail', r'authorization.*fail', r'access.*denied',
        r'insufficient.*permissions', r'user.*not.*found', r'session.*expired',
        # Timeout in product operations (not infrastructure)
        r'operation.*timeout', r'request.*timeout', r'response.*timeout'
    ]
    
    # Exclude if it's clearly a test automation issue
    if not has_test_pattern and not has_test_code:
        for pattern in product_patterns:
            if re.search(pattern, combined):
                logger.debug(f"Classified as PRODUCT: matched pattern '{pattern}'")
                return FailureDomain.PRODUCT
    
    # Default to UNKNOWN if no clear classification
    logger.debug(f"Classified as UNKNOWN: no matching pattern found")
    return FailureDomain.UNKNOWN


def _extract_patterns(error_messages: List[str]) -> List[str]:
    """
    Extract common patterns from a list of error messages.
    
    Args:
        error_messages: List of error messages in the cluster
        
    Returns:
        List of common patterns found
    """
    patterns = []
    
    # Combine all messages
    combined = " ".join(error_messages).lower()
    
    # Common error patterns
    pattern_checks = [
        (r'element.*not.*found', 'Element Not Found'),
        (r'timeout|timed out', 'Timeout'),
        (r'connection.*refused|cannot.*connect', 'Connection Refused'),
        (r'assertion.*fail|expected.*but.*was', 'Assertion Failure'),
        (r'null.*pointer|none.*type', 'Null/None Reference'),
        (r'index.*out.*of.*bounds|list.*index', 'Index Out of Bounds'),
        (r'404|not found', 'Resource Not Found (404)'),
        (r'500|internal.*server.*error', 'Internal Server Error (500)'),
        (r'503|service.*unavailable', 'Service Unavailable (503)'),
    ]
    
    for regex, label in pattern_checks:
        if re.search(regex, combined):
            patterns.append(label)
    
    return patterns


def _suggest_fix(cluster: FailureCluster) -> Optional[str]:
    """
    Generate a suggested fix based on the failure cluster characteristics.
    
    Args:
        cluster: The failure cluster to analyze
        
    Returns:
        Human-readable suggestion or None
    """
    root_cause_lower = cluster.root_cause.lower()
    
    # Element not found
    if 'element' in root_cause_lower and 'not found' in root_cause_lower:
        return (
            "Check if element locators are correct and elements are visible. "
            "Consider adding explicit waits or updating selectors if page structure changed."
        )
    
    # Timeout
    if 'timeout' in root_cause_lower or 'timed out' in root_cause_lower:
        return (
            "Increase timeout values or investigate performance bottlenecks. "
            "Check if external services are responding slowly."
        )
    
    # Connection issues
    if 'connection' in root_cause_lower or 'network' in root_cause_lower:
        return (
            "Verify network connectivity and service availability. "
            "Check firewall rules, DNS resolution, and service health."
        )
    
    # Assertion failures
    if 'assertion' in root_cause_lower or 'expected' in root_cause_lower:
        return (
            "Review test expectations and actual application behavior. "
            "Update assertions if requirements changed or fix application logic."
        )
    
    # Null/None errors
    if 'null' in root_cause_lower or 'none' in root_cause_lower:
        return (
            "Add null checks or ensure required data is initialized properly. "
            "Verify API responses contain expected fields."
        )
    
    return None


def cluster_failures(
    failures: List[Dict],
    deduplicate: bool = True,
    min_cluster_size: int = 1
) -> Dict[str, FailureCluster]:
    """
    Cluster test failures by error fingerprint to identify root causes.
    
    This function takes a list of failure dictionaries and groups them by
    similarity, reducing noise from duplicate failures and highlighting
    unique root causes.
    
    Args:
        failures: List of failure dictionaries with keys:
            - name (str): Test/keyword name
            - error (str): Error message
            - library (str, optional): Library name
            - keyword_name (str, optional): Keyword name
            - stack_trace (str, optional): Stack trace
            - http_status (int, optional): HTTP status code
        deduplicate: If True, only count each unique failure once per test
        min_cluster_size: Minimum failures to form a cluster (default: 1)
        
    Returns:
        Dictionary mapping fingerprints to FailureCluster objects
        
    Examples:
        >>> failures = [
        ...     {"name": "Test Login", "error": "ElementNotFound: #btn-login"},
        ...     {"name": "Test Signup", "error": "ElementNotFound: #btn-signup"}
        ... ]
        >>> clusters = cluster_failures(failures)
        >>> list(clusters.values())[0].failure_count
        2
    """
    logger.debug(
        f"Starting failure clustering: {len(failures)} failures, "
        f"deduplicate={deduplicate}, min_cluster_size={min_cluster_size}"
    )
    
    clusters: Dict[str, FailureCluster] = {}
    seen_combinations: Set[tuple] = set()  # For deduplication
    skipped_empty = 0
    skipped_duplicate = 0
    
    for failure_data in failures:
        # Extract failure attributes
        test_name = failure_data.get("name", "Unknown Test")
        error_message = failure_data.get("error", "")
        keyword_name = failure_data.get("keyword_name")
        library = failure_data.get("library")
        stack_trace = failure_data.get("stack_trace")
        http_status = failure_data.get("http_status")
        timestamp = failure_data.get("timestamp")
        
        # Skip empty errors
        if not error_message.strip():
            skipped_empty += 1
            continue
        
        # Classify failure domain
        domain = _classify_failure_domain(
            error_message=error_message,
            stack_trace=stack_trace,
            library=library
        )
        
        # Create failure instance
        failure = ClusteredFailure(
            test_name=test_name,
            keyword_name=keyword_name,
            error_message=error_message,
            stack_trace=stack_trace,
            library=library,
            http_status=http_status,
            timestamp=timestamp,
            domain=domain,
            metadata=failure_data
        )
        
        # Generate fingerprint
        fingerprint = fingerprint_error(
            error_message=error_message,
            stack_trace=stack_trace,
            http_status=http_status
        )
        
        # Check for deduplication
        if deduplicate:
            combination = (fingerprint, test_name, keyword_name)
            if combination in seen_combinations:
                skipped_duplicate += 1
                continue  # Skip duplicate within same test
            seen_combinations.add(combination)
        
        # Create or update cluster
        if fingerprint not in clusters:
            # Extract simplified root cause (first line of error)
            root_cause = error_message.split('\n')[0].strip()
            if len(root_cause) > 150:
                root_cause = root_cause[:147] + "..."
            
            # Detect severity (uses error message, keyword, and HTTP status)
            severity = _detect_severity(error_message, keyword_name, http_status)
            
            # Classify domain (uses error message, stack trace, and library)
            domain = _classify_failure_domain(
                error_message=error_message,
                stack_trace=stack_trace,
                library=library
            )
            
            # Create new cluster
            clusters[fingerprint] = FailureCluster(
                fingerprint=fingerprint,
                root_cause=root_cause,
                severity=severity,
                domain=domain
            )
        
        # Add failure to cluster
        clusters[fingerprint].add_failure(failure)
    
    # Post-process clusters
    for fingerprint, cluster in clusters.items():
        # Extract common patterns
        all_errors = [f.error_message for f in cluster.failures]
        cluster.error_patterns = _extract_patterns(all_errors)
        
        # Generate suggested fix
        cluster.suggested_fix = _suggest_fix(cluster)
    
    # Filter by minimum cluster size
    pre_filter_count = len(clusters)
    if min_cluster_size > 1:
        clusters = {
            fp: cluster
            for fp, cluster in clusters.items()
            if cluster.failure_count >= min_cluster_size
        }
        filtered_count = pre_filter_count - len(clusters)
        if filtered_count > 0:
            logger.debug(f"Filtered out {filtered_count} clusters below min_cluster_size={min_cluster_size}")
    
    # Log summary
    total_clustered = sum(c.failure_count for c in clusters.values())
    logger.info(
        f"Clustering complete: {len(clusters)} unique issues from {total_clustered} failures "
        f"(skipped {skipped_empty} empty, {skipped_duplicate} duplicates)"
    )
    
    # Log severity distribution
    severity_counts = {}
    for cluster in clusters.values():
        severity_counts[cluster.severity.value] = severity_counts.get(cluster.severity.value, 0) + 1
    logger.debug(f"Severity distribution: {severity_counts}")
    
    # Log domain distribution
    domain_counts = {}
    for cluster in clusters.values():
        domain_counts[cluster.domain.value] = domain_counts.get(cluster.domain.value, 0) + 1
    logger.debug(f"Domain distribution: {domain_counts}")
    
    return clusters


def get_cluster_summary(clusters: Dict[str, FailureCluster]) -> Dict:
    """
    Generate a summary of clustered failures for reporting.
    
    Args:
        clusters: Dictionary of failure clusters
        
    Returns:
        Summary dictionary with statistics, prioritized clusters, and systemic patterns
    """
    logger.debug(f"Generating cluster summary for {len(clusters)} clusters")
    
    total_failures = sum(c.failure_count for c in clusters.values())
    total_unique_issues = len(clusters)
    
    # Group by severity
    by_severity = {
        FailureSeverity.CRITICAL: [],
        FailureSeverity.HIGH: [],
        FailureSeverity.MEDIUM: [],
        FailureSeverity.LOW: []
    }
    
    for cluster in clusters.values():
        by_severity[cluster.severity].append(cluster)
    
    # Sort each severity group by failure count (descending)
    for severity in by_severity:
        by_severity[severity].sort(key=lambda c: c.failure_count, reverse=True)
    
    # Group by domain
    by_domain = {
        FailureDomain.INFRA: [],
        FailureDomain.ENVIRONMENT: [],
        FailureDomain.TEST_AUTOMATION: [],
        FailureDomain.PRODUCT: [],
        FailureDomain.UNKNOWN: []
    }
    
    for cluster in clusters.values():
        by_domain[cluster.domain].append(cluster)
    
    # Detect systemic patterns
    systemic_patterns = detect_systemic_patterns(clusters)
    
    return {
        "total_failures": total_failures,
        "unique_issues": total_unique_issues,
        "deduplication_ratio": round(total_failures / max(total_unique_issues, 1), 2),
        "systemic_patterns": systemic_patterns,
        "by_severity": {
            "critical": len(by_severity[FailureSeverity.CRITICAL]),
            "high": len(by_severity[FailureSeverity.HIGH]),
            "medium": len(by_severity[FailureSeverity.MEDIUM]),
            "low": len(by_severity[FailureSeverity.LOW])
        },
        "by_domain": {
            "infrastructure": len(by_domain[FailureDomain.INFRA]),
            "environment": len(by_domain[FailureDomain.ENVIRONMENT]),
            "test_automation": len(by_domain[FailureDomain.TEST_AUTOMATION]),
            "product": len(by_domain[FailureDomain.PRODUCT]),
            "unknown": len(by_domain[FailureDomain.UNKNOWN])
        },
        "clusters_by_severity": {
            "critical": [_cluster_to_dict(c) for c in by_severity[FailureSeverity.CRITICAL][:5]],
            "high": [_cluster_to_dict(c) for c in by_severity[FailureSeverity.HIGH][:5]],
            "medium": [_cluster_to_dict(c) for c in by_severity[FailureSeverity.MEDIUM][:3]],
            "low": [_cluster_to_dict(c) for c in by_severity[FailureSeverity.LOW][:2]]
        }
    }


def _cluster_to_dict(cluster: FailureCluster) -> Dict:
    """Convert FailureCluster to dictionary for JSON serialization."""
    return {
        "fingerprint": cluster.fingerprint,
        "root_cause": cluster.root_cause,
        "severity": cluster.severity.value,
        "domain": cluster.domain.value,
        "failure_count": cluster.failure_count,
        "affected_tests": list(cluster.tests),
        "affected_keywords": list(cluster.keywords),
        "error_patterns": cluster.error_patterns,
        "suggested_fix": cluster.suggested_fix,
        "sample_failures": [
            {
                "test": f.test_name,
                "keyword": f.keyword_name,
                "error": f.error_message[:200] + "..." if len(f.error_message) > 200 else f.error_message
            }
            for f in cluster.failures[:3]  # Show up to 3 examples
        ]
    }


def detect_systemic_patterns(clusters: Dict[str, FailureCluster]) -> List[str]:
    """
    Detect cross-test failure patterns indicating systemic issues.
    
    Analyzes clusters to identify patterns like:
    - Volume-based regressions (many unique failures)
    - Cascade failures (tests failing after first failure)
    - Environment-specific issues (all ESXi, all Instant VM, etc.)
    - Common keyword/library patterns
    - Feature-specific failures
    
    Args:
        clusters: Dictionary of failure clusters from cluster_failures()
        
    Returns:
        List of pattern warning strings describing systemic issues
        
    Examples:
        >>> clusters = cluster_failures([...])
        >>> patterns = detect_systemic_patterns(clusters)
        >>> print(patterns[0])
        "⚠️  6+ unique failure types suggests possible systemic regression"
    """
    if not clusters:
        return []
    
    patterns = []
    
    # Get all failures across all clusters
    all_failures = []
    for cluster in clusters.values():
        all_failures.extend(cluster.failures)
    
    # 1. Volume-based pattern: Many unique failure types
    unique_count = len(clusters)
    total_failures = len(all_failures)
    
    if unique_count >= 6:
        patterns.append(
            f"⚠️  {unique_count} unique failure types suggests possible systemic regression"
        )
    
    # 2. Cascade failure pattern: Multiple tests failing after first failure
    timestamped_failures = [f for f in all_failures if f.timestamp]
    if len(timestamped_failures) >= 3:
        # Sort by timestamp
        try:
            sorted_failures = sorted(
                timestamped_failures,
                key=lambda f: f.timestamp
            )
            # Check if multiple tests failed after the first one
            unique_tests_after_first = len(set(
                f.test_name for f in sorted_failures[1:]
            ))
            if unique_tests_after_first >= 2:
                patterns.append(
                    f"⚠️  {unique_tests_after_first + 1} tests failed after first failure occurred"
                )
        except (ValueError, TypeError):
            # Skip if timestamp parsing fails
            pass
    
    # 3. Common keyword pattern: Most failures involve same keyword
    all_keywords = []
    for cluster in clusters.values():
        all_keywords.extend(cluster.keywords)
    
    if all_keywords:
        keyword_counts = defaultdict(int)
        for keyword in all_keywords:
            keyword_counts[keyword] += 1
        
        # Find most common keyword
        most_common_keyword = max(keyword_counts.items(), key=lambda x: x[1])
        keyword_name, keyword_count = most_common_keyword
        
        # If >70% of clusters involve same keyword, it's a pattern
        if keyword_count >= len(clusters) * 0.7 and len(clusters) >= 3:
            patterns.append(
                f"⚠️  {keyword_count} clusters involve '{keyword_name}' keyword"
            )
    
    # 4. Common library pattern: Most failures from same library
    libraries = []
    for cluster in clusters.values():
        for failure in cluster.failures:
            if failure.library:
                libraries.append(failure.library)
    
    if libraries:
        library_counts = defaultdict(int)
        for library in libraries:
            library_counts[library] += 1
        
        most_common_library = max(library_counts.items(), key=lambda x: x[1])
        library_name, library_count = most_common_library
        
        # If >70% of failures from same library, it's a pattern
        if library_count >= total_failures * 0.7 and total_failures >= 3:
            patterns.append(
                f"⚠️  {library_count}/{total_failures} failures involve {library_name}"
            )
    
    # 5. Test name pattern extraction: Find common features
    test_names = set()
    for cluster in clusters.values():
        test_names.update(cluster.tests)
    
    if len(test_names) >= 3:
        # Extract common words (ignoring common test words)
        common_test_words = {'test', 'check', 'verify', 'validate', 'should', 'can'}
        word_counts = defaultdict(int)
        
        for test_name in test_names:
            # Split by common delimiters and filter out noise
            words = re.findall(r'\b[A-Z][a-z]+|\b[a-z]+', test_name.replace('_', ' '))
            for word in words:
                word_lower = word.lower()
                if word_lower not in common_test_words and len(word) > 2:
                    word_counts[word] += 1
        
        # Find features mentioned in >60% of test names
        threshold = len(test_names) * 0.6
        common_features = [
            word for word, count in word_counts.items()
            if count >= threshold
        ]
        
        # Report top 2 common features
        if common_features:
            sorted_features = sorted(
                common_features,
                key=lambda w: word_counts[w],
                reverse=True
            )[:2]
            
            for feature in sorted_features:
                count = word_counts[feature]
                patterns.append(
                    f"⚠️  {count}/{len(test_names)} failures involve {feature} feature"
                )
    
    # 6. Environment pattern: Check for environment-specific words
    environment_keywords = {
        'esxi', 'vmware', 'azure', 'aws', 'kubernetes', 'k8s',
        'docker', 'windows', 'linux', 'production', 'staging'
    }
    
    env_counts = defaultdict(int)
    for test_name in test_names:
        test_lower = test_name.lower()
        for env in environment_keywords:
            if env in test_lower:
                env_counts[env] += 1
    
    for env, count in env_counts.items():
        # If >70% of tests mention same environment
        if count >= len(test_names) * 0.7 and len(test_names) >= 3:
            patterns.append(
                f"⚠️  {count}/{len(test_names)} failures involve {env.upper()} environment"
            )
    
    return patterns
