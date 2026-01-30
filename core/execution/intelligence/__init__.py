"""
Execution Intelligence Engine

Framework-agnostic execution log analyzer that converts raw automation logs
into structured failure signals with explainable classification.

Architecture:
1. Raw Logs → Normalization (Framework Adapters)
2. Normalized Events → Failure Signal Extraction
3. Failure Signals → Classification (Rules + Optional AI)
4. Classification → Code Reference Resolution
5. Results → CI Integration / Reports

Works with & without AI - deterministic by default, AI enhancement optional.
"""

from core.execution.intelligence.models import (
    ExecutionEvent,
    FailureSignal,
    FailureType,
    FailureClassification,
    CodeReference,
    AnalysisResult,
    LogLevel,
    SignalType,
)

from core.execution.intelligence.adapters import (
    LogAdapter,
    SeleniumLogAdapter,
    PytestLogAdapter,
    RobotFrameworkLogAdapter,
    PlaywrightLogAdapter,
    CypressLogAdapter,
    RestAssuredLogAdapter,
    CucumberBDDLogAdapter,
    SpecFlowLogAdapter,
    BehaveLogAdapter,
    JavaTestNGLogAdapter,
    GenericLogAdapter,
    parse_logs,
    register_custom_adapter,
)

from core.execution.intelligence.classifier import (
    RuleBasedClassifier,
    ClassificationRule,
)

from core.execution.intelligence.extractor import (
    FailureSignalExtractor,
    TimeoutExtractor,
    AssertionExtractor,
    LocatorExtractor,
    HttpErrorExtractor,
    InfraErrorExtractor,
)

from core.execution.intelligence.resolver import CodeReferenceResolver

from core.execution.intelligence.analyzer import ExecutionAnalyzer

__all__ = [
    # Models
    "ExecutionEvent",
    "FailureSignal",
    "FailureType",
    "FailureClassification",
    "CodeReference",
    "AnalysisResult",
    "LogLevel",
    "SignalType",
    # Adapters
    "LogAdapter",
    "SeleniumLogAdapter",
    "PytestLogAdapter",
    "RobotFrameworkLogAdapter",
    "PlaywrightLogAdapter",
    "CypressLogAdapter",
    "RestAssuredLogAdapter",
    "CucumberBDDLogAdapter",
    "SpecFlowLogAdapter",
    "BehaveLogAdapter",
    "JavaTestNGLogAdapter",
    "GenericLogAdapter",
    "parse_logs",
    "register_custom_adapter",
    # Classifier
    "RuleBasedClassifier",
    "ClassificationRule",
    # Extractors
    "FailureSignalExtractor",
    "TimeoutExtractor",
    "AssertionExtractor",
    "LocatorExtractor",
    "HttpErrorExtractor",
    "InfraErrorExtractor",
    # Resolver
    "CodeReferenceResolver",
    # Main Analyzer
    "ExecutionAnalyzer",
]
