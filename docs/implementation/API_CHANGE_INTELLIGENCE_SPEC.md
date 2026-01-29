# API Change Intelligence - Implementation Specification

**Version:** 1.0  
**Date:** January 29, 2026  
**Status:** Ready for Implementation

---

## 📋 Executive Summary

This specification defines the complete implementation of **API Change Intelligence** for CrossBridge - a platform capability that detects OpenAPI/Swagger changes, generates incremental documentation, provides observability via Grafana, optionally enhances insights using AI, and triggers alerts and selective CI test runs.

### Core Principle

**Work without AI → Get better with AI → Enable metered monetization**

---

## 🎯 Objectives

1. **Detect API Changes**: Use oasdiff to compare OpenAPI specifications
2. **Normalize Data**: Convert raw diffs into structured, actionable models
3. **Generate Documentation**: Create incremental, human-readable change logs
4. **Provide Observability**: Grafana dashboards for trends, risks, and insights
5. **Enable Intelligence**: Rule-based + optional AI-augmented analysis
6. **Trigger Actions**: Alerts (email/Slack) and selective CI test execution
7. **Ensure Enterprise Safety**: Configurable, disabled by default, predictable costs

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     OpenAPI Spec Sources                            │
│  (File | Git | URL | CI Artifacts)                                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Spec Collector                                  │
│  • Download/Load specs                                               │
│  • Version tracking                                                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      OASDiff Engine                                  │
│  • Run oasdiff comparison                                            │
│  • Parse JSON output                                                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Change Normalizer                                  │
│  • Convert to internal model                                         │
│  • Calculate risk levels                                             │
│  • Detect breaking changes                                           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Intelligence Engine                                 │
│  ┌────────────────────┐        ┌────────────────────┐              │
│  │  Rules Engine      │        │  AI Engine         │              │
│  │  (No AI, Always)   │   →    │  (Optional)        │              │
│  │  • Pattern match   │        │  • Risk analysis   │              │
│  │  • Test recommend  │        │  • Test generation │              │
│  └────────────────────┘        └────────────────────┘              │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Storage Layer                                   │
│  • PostgreSQL (api_changes table)                                    │
│  • Time-series optimized                                             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────┬───────────────────┬──────────────────────────┐
│  Doc Generator       │   Observability   │   Action Orchestrator    │
│  • Markdown          │   • Grafana       │   • Alerts (Slack/Email) │
│  • Confluence        │   • Dashboards    │   • CI Trigger           │
│  • Text/Word         │   • Metrics       │   • Selective Tests      │
└──────────────────────┴───────────────────┴──────────────────────────┘
```

---

## 📁 Module Structure

```
crossbridge/
├── intelligence/
│   ├── api_change/
│   │   ├── __init__.py
│   │   ├── spec_collector.py           # Spec download/loading
│   │   ├── oasdiff_engine.py           # Wrapper for oasdiff
│   │   ├── change_normalizer.py        # Diff → Internal model
│   │   ├── change_classifier.py        # Risk/breaking detection
│   │   ├── rules_engine.py             # Rule-based intelligence
│   │   ├── ai_engine.py                # Optional AI enhancement
│   │   ├── impact_analyzer.py          # Test impact mapping
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── schema.py               # DB schema definitions
│   │   │   └── repository.py           # Data access layer
│   │   ├── doc_generator/
│   │   │   ├── __init__.py
│   │   │   ├── markdown.py             # Markdown generator
│   │   │   ├── confluence.py           # Confluence integration
│   │   │   └── text.py                 # Plain text/Word
│   │   ├── alerts/
│   │   │   ├── __init__.py
│   │   │   ├── email_notifier.py       # Email alerts
│   │   │   └── slack_notifier.py       # Slack alerts
│   │   ├── ci_trigger/
│   │   │   ├── __init__.py
│   │   │   ├── test_selector.py        # Selective test logic
│   │   │   └── ci_integration.py       # CI system integration
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── api_change.py           # Core data models
│   │       └── test_impact.py          # Test mapping models
│   └── __init__.py
├── cli/
│   └── commands/
│       └── api_diff.py                 # CLI interface
└── grafana/
    └── dashboards/
        └── api_change_intelligence.json  # Grafana dashboard

docs/
└── api-change/
    ├── API_CHANGE_INTELLIGENCE_SPEC.md   # This file
    ├── SETUP_GUIDE.md                     # User setup guide
    └── GRAFANA_DASHBOARD_GUIDE.md         # Dashboard usage
```

---

## 💾 Database Schema

```sql
-- API Change Events (Time-series optimized)
CREATE TABLE api_changes (
    id BIGSERIAL PRIMARY KEY,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    run_id UUID NOT NULL,
    
    -- Source information
    api_name VARCHAR(255) NOT NULL,
    api_version VARCHAR(50),
    spec_source VARCHAR(255),
    
    -- Change details
    change_type VARCHAR(50) NOT NULL, -- added, modified, removed
    entity_type VARCHAR(50) NOT NULL, -- endpoint, schema, parameter
    entity_name VARCHAR(255) NOT NULL,
    http_method VARCHAR(10),          -- GET, POST, etc.
    path VARCHAR(500),
    
    -- Classification
    breaking BOOLEAN NOT NULL DEFAULT false,
    risk_level VARCHAR(20) NOT NULL,  -- low, medium, high, critical
    severity VARCHAR(20),              -- minor, major, critical
    
    -- Change content
    change_details JSONB NOT NULL,    -- Full diff data
    old_value JSONB,
    new_value JSONB,
    
    -- Intelligence
    ai_enhanced BOOLEAN NOT NULL DEFAULT false,
    ai_model VARCHAR(50),
    ai_reasoning TEXT,
    
    -- Recommendations
    recommended_tests TEXT[],
    impacted_areas TEXT[],
    
    -- Metadata
    created_by VARCHAR(100),
    project_id VARCHAR(100),
    tags TEXT[],
    
    -- Indexes for common queries
    INDEX idx_detected_at (detected_at DESC),
    INDEX idx_api_name (api_name),
    INDEX idx_breaking (breaking) WHERE breaking = true,
    INDEX idx_risk_level (risk_level),
    INDEX idx_change_type (change_type)
);

-- API Diff Runs (Track execution)
CREATE TABLE api_diff_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL,      -- running, completed, failed
    
    -- Spec information
    old_spec_source VARCHAR(500),
    new_spec_source VARCHAR(500),
    old_spec_version VARCHAR(50),
    new_spec_version VARCHAR(50),
    
    -- Results
    total_changes INTEGER NOT NULL DEFAULT 0,
    breaking_changes INTEGER NOT NULL DEFAULT 0,
    high_risk_changes INTEGER NOT NULL DEFAULT 0,
    
    -- AI usage
    ai_enabled BOOLEAN NOT NULL DEFAULT false,
    ai_tokens_used INTEGER DEFAULT 0,
    ai_cost_usd DECIMAL(10, 4) DEFAULT 0,
    
    -- Execution details
    duration_ms INTEGER,
    error_message TEXT,
    
    INDEX idx_started_at (started_at DESC),
    INDEX idx_status (status)
);

-- Test Impact Mapping
CREATE TABLE api_test_coverage (
    id BIGSERIAL PRIMARY KEY,
    
    -- API reference
    api_name VARCHAR(255) NOT NULL,
    endpoint_path VARCHAR(500) NOT NULL,
    http_method VARCHAR(10),
    schema_name VARCHAR(255),
    
    -- Test reference
    test_id VARCHAR(255) NOT NULL,
    test_name VARCHAR(500) NOT NULL,
    test_file VARCHAR(500),
    test_framework VARCHAR(50),
    
    -- Coverage type
    coverage_type VARCHAR(50), -- direct, indirect, schema-based
    confidence DECIMAL(3, 2),  -- 0.00 to 1.00
    
    -- Metadata
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_verified TIMESTAMPTZ,
    source VARCHAR(50),        -- static, runtime, ai-inferred
    
    -- Indexes
    INDEX idx_endpoint (endpoint_path, http_method),
    INDEX idx_test (test_id),
    INDEX idx_api_name (api_name),
    UNIQUE (api_name, endpoint_path, http_method, test_id)
);

-- Alert History
CREATE TABLE api_change_alerts (
    id BIGSERIAL PRIMARY KEY,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    change_id BIGINT REFERENCES api_changes(id),
    
    -- Alert details
    alert_type VARCHAR(50),    -- breaking_change, high_risk, new_endpoint
    channel VARCHAR(50),       -- email, slack, webhook
    recipient VARCHAR(255),
    
    -- Status
    status VARCHAR(20),        -- sent, failed, pending
    error_message TEXT,
    
    INDEX idx_sent_at (sent_at DESC),
    INDEX idx_change_id (change_id)
);

-- AI Token Usage (For billing)
CREATE TABLE ai_token_usage (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    run_id UUID REFERENCES api_diff_runs(id),
    
    -- Usage details
    organization_id VARCHAR(100),
    project_id VARCHAR(100),
    feature VARCHAR(50),       -- risk_analysis, test_recommendation, etc.
    
    -- Token consumption
    model VARCHAR(50) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost_usd DECIMAL(10, 6),
    
    -- Rate limiting
    monthly_total INTEGER,
    
    INDEX idx_timestamp (timestamp DESC),
    INDEX idx_org_project (organization_id, project_id),
    INDEX idx_monthly (date_trunc('month', timestamp))
);
```

---

## ⚙️ Configuration Schema

Add to `crossbridge.yml`:

```yaml
crossbridge:
  # API Change Intelligence Configuration
  api_change:
    enabled: false  # DISABLED BY DEFAULT
    
    # Spec Sources
    spec_source:
      type: file              # file | url | git | auto
      current: specs/openapi.yaml
      previous: specs/openapi_prev.yaml
      
      # Optional: Git-based
      git:
        enabled: false
        repo: .
        current_commit: HEAD
        previous_commit: HEAD~1
        spec_path: docs/api/openapi.yaml
      
      # Optional: URL-based
      url:
        current: https://api.example.com/swagger.json
        previous: https://api.example.com/swagger.json?version=prev
        headers:
          Authorization: Bearer ${API_TOKEN}
    
    # Intelligence Configuration
    intelligence:
      mode: hybrid            # none | rules | hybrid | ai-only
      
      # Rule-based intelligence (always enabled)
      rules:
        enabled: true
        detect_breaking: true
        calculate_risk: true
        recommend_tests: true
      
      # AI Enhancement (optional, metered)
      ai:
        enabled: false        # DISABLED BY DEFAULT
        provider: openai      # openai | anthropic | azure
        model: gpt-4.1-mini
        max_tokens_per_run: 2000
        temperature: 0.2
        
        # Features
        features:
          risk_analysis: true
          test_recommendations: true
          impact_reasoning: true
          edge_case_detection: true
        
        # Budget Control
        budgeting:
          monthly_token_limit: 5000000
          warn_at_percent: 80
          stop_at_percent: 95
          cost_per_1k_tokens: 0.01
    
    # Documentation Generation
    documentation:
      enabled: true
      output_dir: docs/api-changes
      
      # Formats
      formats:
        markdown:
          enabled: true
          file: api-changes.md
          append_mode: true
        
        text:
          enabled: false
          file: api-changes.txt
        
        confluence:
          enabled: false
          url: https://company.atlassian.net
          space: QA
          page_id: 123456
          append_mode: true
          auth_token: ${CONFLUENCE_TOKEN}
    
    # Observability (Grafana)
    observability:
      enabled: true
      
      # Metrics export
      metrics:
        prometheus: true
        grafana: true
      
      # Dashboard
      grafana:
        dashboard_uid: api-change-intel
        auto_import: true
    
    # Alerts
    alerts:
      enabled: false
      
      # Trigger conditions
      triggers:
        breaking_changes: true
        high_risk_changes: true
        critical_severity: true
        min_risk_level: medium  # low | medium | high | critical
      
      # Channels
      channels:
        email:
          enabled: false
          recipients:
            - qa-team@example.com
          smtp_host: smtp.example.com
          smtp_port: 587
          from_address: crossbridge@example.com
        
        slack:
          enabled: false
          webhook_url: ${SLACK_WEBHOOK}
          channel: "#api-alerts"
          mention_users:
            - "@qa-lead"
        
        webhook:
          enabled: false
          url: https://example.com/api/webhooks/api-changes
          headers:
            Authorization: Bearer ${WEBHOOK_TOKEN}
    
    # CI Integration
    ci:
      enabled: false
      mode: selective         # none | selective | full
      
      # Trigger conditions
      triggers:
        on_breaking: true
        on_high_risk: true
        min_risk_level: medium
      
      # Test selection
      test_selection:
        strategy: impact-based  # all | impact-based | risk-weighted
        include_indirect: true
        max_tests: 100
        
        # Coverage source
        coverage_source: auto   # auto | database | static | runtime
      
      # CI System Integration
      integration:
        type: generic           # generic | github | gitlab | jenkins
        trigger_url: ${CI_TRIGGER_URL}
        auth_token: ${CI_AUTH_TOKEN}
        
        # Test filter output
        output_format: pytest   # pytest | robot | junit | list
        output_file: .crossbridge/impacted-tests.txt
    
    # Storage
    storage:
      database:
        enabled: true
        connection: ${CROSSBRIDGE_DB_URL}
      
      retention:
        days: 90              # Keep 90 days of history
        compress_after_days: 30
```

---

## 🔨 Implementation Steps

### Phase 1: Core Infrastructure (Week 1)

#### Step 1.1: Database Setup
```python
# intelligence/api_change/storage/schema.py
from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, JSON, ARRAY, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from persistence.base import Base

class APIChange(Base):
    __tablename__ = "api_changes"
    
    id = Column(Integer, primary_key=True)
    detected_at = Column(TIMESTAMP(timezone=True))
    run_id = Column(UUID(as_uuid=True))
    api_name = Column(String(255))
    change_type = Column(String(50))
    entity_type = Column(String(50))
    entity_name = Column(String(255))
    breaking = Column(Boolean, default=False)
    risk_level = Column(String(20))
    change_details = Column(JSONB)
    ai_enhanced = Column(Boolean, default=False)
    recommended_tests = Column(ARRAY(String))
    # ... additional fields

class APIDiffRun(Base):
    __tablename__ = "api_diff_runs"
    # ... fields

class APITestCoverage(Base):
    __tablename__ = "api_test_coverage"
    # ... fields
```

#### Step 1.2: Data Models
```python
# intelligence/api_change/models/api_change.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ChangeType(Enum):
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"

class EntityType(Enum):
    ENDPOINT = "endpoint"
    SCHEMA = "schema"
    PARAMETER = "parameter"
    RESPONSE = "response"
    SECURITY = "security"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class APIChangeEvent:
    """Normalized API change event"""
    change_type: ChangeType
    entity_type: EntityType
    entity_name: str
    breaking: bool
    risk_level: RiskLevel
    
    # Optional fields
    path: Optional[str] = None
    http_method: Optional[str] = None
    change_details: Dict[str, Any] = field(default_factory=dict)
    old_value: Optional[Dict] = None
    new_value: Optional[Dict] = None
    
    # Intelligence
    ai_enhanced: bool = False
    ai_reasoning: Optional[str] = None
    recommended_tests: List[str] = field(default_factory=list)
    impacted_areas: List[str] = field(default_factory=list)
    
    # Metadata
    detected_at: datetime = field(default_factory=datetime.utcnow)
    api_name: str = ""
    api_version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "change_type": self.change_type.value,
            "entity_type": self.entity_type.value,
            "entity_name": self.entity_name,
            "breaking": self.breaking,
            "risk_level": self.risk_level.value,
            "path": self.path,
            "http_method": self.http_method,
            "change_details": self.change_details,
            "ai_enhanced": self.ai_enhanced,
            "recommended_tests": self.recommended_tests,
            "impacted_areas": self.impacted_areas,
            "detected_at": self.detected_at.isoformat()
        }

@dataclass
class DiffResult:
    """Complete diff result from a comparison"""
    run_id: str
    old_spec_version: str
    new_spec_version: str
    changes: List[APIChangeEvent]
    total_changes: int
    breaking_changes: int
    high_risk_changes: int
    ai_tokens_used: int = 0
    duration_ms: int = 0
```

#### Step 1.3: Spec Collector
```python
# intelligence/api_change/spec_collector.py
from typing import Dict, Any, Tuple
from pathlib import Path
import requests
import yaml
import json
import subprocess

class SpecCollector:
    """Collect OpenAPI specs from various sources"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def collect_specs(self) -> Tuple[Dict, Dict]:
        """
        Collect current and previous specs
        
        Returns:
            Tuple of (current_spec, previous_spec) as dictionaries
        """
        source_type = self.config.get("type", "file")
        
        if source_type == "file":
            return self._collect_from_files()
        elif source_type == "url":
            return self._collect_from_urls()
        elif source_type == "git":
            return self._collect_from_git()
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
    
    def _collect_from_files(self) -> Tuple[Dict, Dict]:
        """Load specs from local files"""
        current_path = Path(self.config["current"])
        previous_path = Path(self.config["previous"])
        
        current = self._load_spec_file(current_path)
        previous = self._load_spec_file(previous_path)
        
        return current, previous
    
    def _collect_from_urls(self) -> Tuple[Dict, Dict]:
        """Download specs from URLs"""
        url_config = self.config["url"]
        headers = url_config.get("headers", {})
        
        current_url = url_config["current"]
        previous_url = url_config["previous"]
        
        current = self._download_spec(current_url, headers)
        previous = self._download_spec(previous_url, headers)
        
        return current, previous
    
    def _collect_from_git(self) -> Tuple[Dict, Dict]:
        """Extract specs from Git commits"""
        git_config = self.config["git"]
        repo = git_config["repo"]
        spec_path = git_config["spec_path"]
        current_commit = git_config.get("current_commit", "HEAD")
        previous_commit = git_config.get("previous_commit", "HEAD~1")
        
        current = self._get_file_from_git(repo, spec_path, current_commit)
        previous = self._get_file_from_git(repo, spec_path, previous_commit)
        
        return current, previous
    
    def _load_spec_file(self, path: Path) -> Dict:
        """Load spec from file (YAML or JSON)"""
        content = path.read_text()
        
        if path.suffix in [".yaml", ".yml"]:
            return yaml.safe_load(content)
        elif path.suffix == ".json":
            return json.loads(content)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
    
    def _download_spec(self, url: str, headers: Dict) -> Dict:
        """Download spec from URL"""
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            return response.json()
        else:
            return yaml.safe_load(response.text)
    
    def _get_file_from_git(self, repo: str, file_path: str, commit: str) -> Dict:
        """Get file content from specific Git commit"""
        cmd = ["git", "-C", repo, "show", f"{commit}:{file_path}"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if file_path.endswith((".yaml", ".yml")):
            return yaml.safe_load(result.stdout)
        else:
            return json.loads(result.stdout)
```

### Phase 2: OASDiff Integration (Week 1)

#### Step 2.1: OASDiff Engine
```python
# intelligence/api_change/oasdiff_engine.py
import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any
import yaml

class OASDiffEngine:
    """Wrapper for oasdiff CLI tool"""
    
    def __init__(self):
        self._check_oasdiff_installed()
    
    def _check_oasdiff_installed(self):
        """Verify oasdiff is installed"""
        try:
            subprocess.run(
                ["oasdiff", "--version"],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "oasdiff not found. Install it: go install github.com/tufin/oasdiff@latest"
            )
    
    def diff(
        self,
        old_spec: Dict[str, Any],
        new_spec: Dict[str, Any],
        include_checks: bool = True
    ) -> Dict[str, Any]:
        """
        Compare two OpenAPI specs using oasdiff
        
        Args:
            old_spec: Previous OpenAPI spec as dictionary
            new_spec: Current OpenAPI spec as dictionary
            include_checks: Include breaking change checks
        
        Returns:
            Parsed diff result as dictionary
        """
        # Write specs to temporary files
        with tempfile.TemporaryDirectory() as tmpdir:
            old_path = Path(tmpdir) / "old.yaml"
            new_path = Path(tmpdir) / "new.yaml"
            
            old_path.write_text(yaml.dump(old_spec))
            new_path.write_text(yaml.dump(new_spec))
            
            # Run oasdiff
            cmd = [
                "oasdiff",
                "diff",
                str(old_path),
                str(new_path),
                "-f", "json"
            ]
            
            if include_checks:
                cmd.extend(["-c", "all"])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False  # Don't fail on differences
            )
            
            if result.returncode not in [0, 1]:  # 0=no diff, 1=diff found
                raise RuntimeError(f"oasdiff failed: {result.stderr}")
            
            # Parse JSON output
            if result.stdout:
                return json.loads(result.stdout)
            else:
                return {"paths": {}, "schemas": {}}
    
    def diff_breaking(
        self,
        old_spec: Dict[str, Any],
        new_spec: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detect breaking changes only
        
        Returns:
            List of breaking changes
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            old_path = Path(tmpdir) / "old.yaml"
            new_path = Path(tmpdir) / "new.yaml"
            
            old_path.write_text(yaml.dump(old_spec))
            new_path.write_text(yaml.dump(new_spec))
            
            cmd = [
                "oasdiff",
                "breaking",
                str(old_path),
                str(new_path),
                "-f", "json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.stdout:
                data = json.loads(result.stdout)
                return data.get("breaking", [])
            else:
                return []
```

#### Step 2.2: Change Normalizer
```python
# intelligence/api_change/change_normalizer.py
from typing import Dict, List, Any
from .models.api_change import (
    APIChangeEvent, ChangeType, EntityType, RiskLevel
)

class ChangeNormalizer:
    """Convert oasdiff output to normalized APIChangeEvent objects"""
    
    def normalize(
        self,
        diff_result: Dict[str, Any],
        breaking_changes: List[Dict[str, Any]]
    ) -> List[APIChangeEvent]:
        """
        Normalize oasdiff output into APIChangeEvent objects
        
        Args:
            diff_result: Raw oasdiff diff output
            breaking_changes: Breaking changes from oasdiff breaking command
        
        Returns:
            List of normalized APIChangeEvent objects
        """
        changes = []
        
        # Process endpoint changes
        for path, path_changes in diff_result.get("paths", {}).items():
            changes.extend(self._process_path_changes(path, path_changes))
        
        # Process schema changes
        for schema_name, schema_changes in diff_result.get("schemas", {}).items():
            changes.extend(self._process_schema_changes(schema_name, schema_changes))
        
        # Mark breaking changes
        breaking_set = self._create_breaking_set(breaking_changes)
        for change in changes:
            change_key = self._get_change_key(change)
            if change_key in breaking_set:
                change.breaking = True
                # Upgrade risk level for breaking changes
                if change.risk_level == RiskLevel.LOW:
                    change.risk_level = RiskLevel.MEDIUM
                elif change.risk_level == RiskLevel.MEDIUM:
                    change.risk_level = RiskLevel.HIGH
        
        return changes
    
    def _process_path_changes(
        self,
        path: str,
        path_changes: Dict[str, Any]
    ) -> List[APIChangeEvent]:
        """Process changes to API endpoints"""
        changes = []
        
        for method, method_changes in path_changes.items():
            if method_changes.get("added"):
                changes.append(APIChangeEvent(
                    change_type=ChangeType.ADDED,
                    entity_type=EntityType.ENDPOINT,
                    entity_name=f"{method.upper()} {path}",
                    path=path,
                    http_method=method.upper(),
                    breaking=False,
                    risk_level=self._calculate_endpoint_risk(method_changes, "added"),
                    change_details=method_changes
                ))
            
            elif method_changes.get("deleted"):
                changes.append(APIChangeEvent(
                    change_type=ChangeType.REMOVED,
                    entity_type=EntityType.ENDPOINT,
                    entity_name=f"{method.upper()} {path}",
                    path=path,
                    http_method=method.upper(),
                    breaking=True,  # Endpoint deletion is always breaking
                    risk_level=RiskLevel.HIGH,
                    change_details=method_changes
                ))
            
            elif method_changes.get("modified"):
                changes.extend(
                    self._process_endpoint_modifications(
                        path, method, method_changes["modified"]
                    )
                )
        
        return changes
    
    def _process_endpoint_modifications(
        self,
        path: str,
        method: str,
        modifications: Dict[str, Any]
    ) -> List[APIChangeEvent]:
        """Process modifications to an existing endpoint"""
        changes = []
        
        # Parameter changes
        if "parameters" in modifications:
            for param_change in modifications["parameters"]:
                changes.append(APIChangeEvent(
                    change_type=ChangeType.MODIFIED,
                    entity_type=EntityType.PARAMETER,
                    entity_name=f"{method.upper()} {path} - {param_change.get('name')}",
                    path=path,
                    http_method=method.upper(),
                    breaking=param_change.get("required", False),
                    risk_level=self._calculate_param_risk(param_change),
                    change_details=param_change
                ))
        
        # Request body changes
        if "requestBody" in modifications:
            changes.append(APIChangeEvent(
                change_type=ChangeType.MODIFIED,
                entity_type=EntityType.PARAMETER,
                entity_name=f"{method.upper()} {path} - Request Body",
                path=path,
                http_method=method.upper(),
                breaking=False,
                risk_level=RiskLevel.MEDIUM,
                change_details=modifications["requestBody"]
            ))
        
        # Response changes
        if "responses" in modifications:
            for status_code, response_change in modifications["responses"].items():
                changes.append(APIChangeEvent(
                    change_type=ChangeType.MODIFIED,
                    entity_type=EntityType.RESPONSE,
                    entity_name=f"{method.upper()} {path} - {status_code}",
                    path=path,
                    http_method=method.upper(),
                    breaking=False,
                    risk_level=self._calculate_response_risk(response_change),
                    change_details=response_change
                ))
        
        return changes
    
    def _process_schema_changes(
        self,
        schema_name: str,
        schema_changes: Dict[str, Any]
    ) -> List[APIChangeEvent]:
        """Process changes to data schemas"""
        changes = []
        
        if schema_changes.get("added"):
            changes.append(APIChangeEvent(
                change_type=ChangeType.ADDED,
                entity_type=EntityType.SCHEMA,
                entity_name=schema_name,
                breaking=False,
                risk_level=RiskLevel.LOW,
                change_details=schema_changes
            ))
        
        elif schema_changes.get("deleted"):
            changes.append(APIChangeEvent(
                change_type=ChangeType.REMOVED,
                entity_type=EntityType.SCHEMA,
                entity_name=schema_name,
                breaking=True,
                risk_level=RiskLevel.HIGH,
                change_details=schema_changes
            ))
        
        elif schema_changes.get("modified"):
            # Process property changes
            for prop_change in schema_changes["modified"].get("properties", []):
                changes.append(APIChangeEvent(
                    change_type=ChangeType.MODIFIED,
                    entity_type=EntityType.SCHEMA,
                    entity_name=f"{schema_name}.{prop_change.get('name')}",
                    breaking=prop_change.get("required", False),
                    risk_level=self._calculate_schema_risk(prop_change),
                    change_details=prop_change
                ))
        
        return changes
    
    def _calculate_endpoint_risk(
        self,
        changes: Dict[str, Any],
        change_type: str
    ) -> RiskLevel:
        """Calculate risk level for endpoint changes"""
        if change_type == "deleted":
            return RiskLevel.HIGH
        elif change_type == "added":
            return RiskLevel.MEDIUM if changes.get("public") else RiskLevel.LOW
        else:
            return RiskLevel.MEDIUM
    
    def _calculate_param_risk(self, param_change: Dict[str, Any]) -> RiskLevel:
        """Calculate risk level for parameter changes"""
        if param_change.get("required"):
            return RiskLevel.HIGH
        elif param_change.get("type_changed"):
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_response_risk(self, response_change: Dict[str, Any]) -> RiskLevel:
        """Calculate risk level for response changes"""
        if response_change.get("schema_changed"):
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_schema_risk(self, prop_change: Dict[str, Any]) -> RiskLevel:
        """Calculate risk level for schema property changes"""
        if prop_change.get("required"):
            return RiskLevel.HIGH
        elif prop_change.get("type_changed"):
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _create_breaking_set(
        self,
        breaking_changes: List[Dict[str, Any]]
    ) -> set:
        """Create set of breaking change identifiers"""
        breaking_set = set()
        for change in breaking_changes:
            key = f"{change.get('method')}:{change.get('path')}:{change.get('field')}"
            breaking_set.add(key)
        return breaking_set
    
    def _get_change_key(self, change: APIChangeEvent) -> str:
        """Generate unique key for change matching"""
        return f"{change.http_method}:{change.path}:{change.entity_name}"
```

### Phase 3: Intelligence Engine (Week 2)

#### Step 3.1: Rules Engine
```python
# intelligence/api_change/rules_engine.py
from typing import List, Dict, Any
from .models.api_change import APIChangeEvent, ChangeType, EntityType, RiskLevel

class RulesEngine:
    """Rule-based intelligence without AI - always enabled"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rules = self._load_rules()
    
    def analyze(self, changes: List[APIChangeEvent]) -> List[APIChangeEvent]:
        """
        Analyze changes using rule-based logic
        
        Enhances each change with:
        - Test recommendations
        - Impacted areas
        - Additional context
        
        Args:
            changes: List of normalized API changes
        
        Returns:
            Same list with intelligence added
        """
        for change in changes:
            # Apply rules based on change type and entity
            if change.entity_type == EntityType.ENDPOINT:
                self._analyze_endpoint_change(change)
            elif change.entity_type == EntityType.SCHEMA:
                self._analyze_schema_change(change)
            elif change.entity_type == EntityType.PARAMETER:
                self._analyze_parameter_change(change)
            elif change.entity_type == EntityType.RESPONSE:
                self._analyze_response_change(change)
        
        return changes
    
    def _analyze_endpoint_change(self, change: APIChangeEvent):
        """Apply rules for endpoint changes"""
        if change.change_type == ChangeType.ADDED:
            change.recommended_tests.extend([
                f"Create positive test for {change.entity_name}",
                f"Verify authentication/authorization for {change.entity_name}",
                f"Test error responses (400, 401, 403, 500) for {change.entity_name}",
                f"Validate request schema for {change.entity_name}",
                f"Validate response schema for {change.entity_name}"
            ])
            change.impacted_areas.append("New endpoint test coverage needed")
        
        elif change.change_type == ChangeType.REMOVED:
            change.recommended_tests.extend([
                f"Verify {change.entity_name} returns 404",
                f"Update test suites to remove deprecated endpoint tests",
                f"Check dependent services for impact"
            ])
            change.impacted_areas.extend([
                "Endpoint removal",
                "Test deprecation needed",
                "Potential breaking change for consumers"
            ])
        
        elif change.change_type == ChangeType.MODIFIED:
            change.recommended_tests.extend([
                f"Regression tests for {change.entity_name}",
                f"Verify backward compatibility for {change.entity_name}"
            ])
            change.impacted_areas.append("Endpoint modification")
    
    def _analyze_schema_change(self, change: APIChangeEvent):
        """Apply rules for schema changes"""
        details = change.change_details
        
        if change.change_type == ChangeType.ADDED:
            change.recommended_tests.append(
                f"Add schema validation tests for {change.entity_name}"
            )
        
        elif "required" in details and details["required"]:
            # New required field
            change.recommended_tests.extend([
                f"Test request without required field {change.entity_name}",
                f"Test request with null value for {change.entity_name}",
                f"Test request with invalid type for {change.entity_name}",
                f"Test request with valid value for {change.entity_name}"
            ])
            change.impacted_areas.extend([
                "Schema validation",
                "Required field addition",
                "Breaking change"
            ])
        
        elif "type_changed" in details:
            # Type change
            change.recommended_tests.extend([
                f"Verify new type handling for {change.entity_name}",
                f"Test backward compatibility with old type",
                f"Test boundary values for new type"
            ])
            change.impacted_areas.extend([
                "Type change",
                "Potential serialization issues"
            ])
        
        elif "enum_values" in details:
            # Enum change
            old_values = set(details.get("old_enum_values", []))
            new_values = set(details.get("new_enum_values", []))
            
            added_values = new_values - old_values
            removed_values = old_values - new_values
            
            if added_values:
                change.recommended_tests.append(
                    f"Test new enum values: {added_values} for {change.entity_name}"
                )
            
            if removed_values:
                change.recommended_tests.append(
                    f"Verify handling of removed enum values: {removed_values}"
                )
                change.impacted_areas.append("Enum value removal - breaking change")
    
    def _analyze_parameter_change(self, change: APIChangeEvent):
        """Apply rules for parameter changes"""
        details = change.change_details
        
        if "required" in details and details["required"]:
            change.recommended_tests.extend([
                f"Test request missing {change.entity_name}",
                f"Verify error message for missing {change.entity_name}"
            ])
            change.impacted_areas.append("New required parameter - breaking change")
        
        if "default_value" in details:
            change.recommended_tests.append(
                f"Test default behavior when {change.entity_name} is not provided"
            )
        
        if "validation" in details:
            # Validation rules changed
            change.recommended_tests.extend([
                f"Test boundary values for {change.entity_name}",
                f"Test invalid values for {change.entity_name}"
            ])
            change.impacted_areas.append("Validation rule change")
    
    def _analyze_response_change(self, change: APIChangeEvent):
        """Apply rules for response changes"""
        details = change.change_details
        
        if "status_code" in details:
            change.recommended_tests.append(
                f"Verify new response status {details['status_code']}"
            )
        
        if "schema_changed" in details:
            change.recommended_tests.extend([
                f"Verify response schema for {change.entity_name}",
                f"Test response deserialization",
                f"Check field presence and types"
            ])
            change.impacted_areas.append("Response schema change")
        
        if "header_changed" in details:
            change.recommended_tests.append(
                f"Verify response headers for {change.entity_name}"
            )
    
    def _load_rules(self) -> Dict[str, Any]:
        """Load rule configuration"""
        return {
            "breaking_change_patterns": [
                "endpoint_removal",
                "required_field_addition",
                "type_change",
                "enum_value_removal"
            ],
            "high_risk_patterns": [
                "authentication_change",
                "authorization_change",
                "data_validation_change"
            ]
        }
```

#### Step 3.2: AI Engine (Optional)
```python
# intelligence/api_change/ai_engine.py
from typing import List, Dict, Any, Optional
from .models.api_change import APIChangeEvent
import openai
import anthropic
from dataclasses import asdict

class AIEngine:
    """AI-augmented intelligence - optional, metered"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", False)
        
        if self.enabled:
            self.provider = config.get("provider", "openai")
            self.model = config.get("model", "gpt-4.1-mini")
            self.max_tokens = config.get("max_tokens_per_run", 2000)
            self.temperature = config.get("temperature", 0.2)
            
            # Initialize client
            if self.provider == "openai":
                self.client = openai.OpenAI()
            elif self.provider == "anthropic":
                self.client = anthropic.Anthropic()
            else:
                raise ValueError(f"Unsupported AI provider: {self.provider}")
            
            # Token usage tracking
            self.tokens_used = 0
            self.monthly_limit = config.get("budgeting", {}).get("monthly_token_limit", 5000000)
    
    def analyze(
        self,
        changes: List[APIChangeEvent],
        context: Optional[Dict[str, Any]] = None
    ) -> List[APIChangeEvent]:
        """
        Enhance changes with AI analysis
        
        Args:
            changes: List of normalized changes with rule-based intelligence
            context: Optional context (historical data, test suite info, etc.)
        
        Returns:
            Same list with AI enhancements added
        """
        if not self.enabled:
            return changes
        
        # Check token budget
        if self.tokens_used >= self.monthly_limit:
            print(f"WARNING: Monthly token limit reached ({self.monthly_limit})")
            return changes
        
        # Process high-risk and complex changes only
        high_priority_changes = [
            c for c in changes
            if c.risk_level.value in ["high", "critical"] or c.breaking
        ]
        
        for change in high_priority_changes:
            try:
                self._enhance_with_ai(change, context)
            except Exception as e:
                print(f"AI analysis failed for {change.entity_name}: {e}")
                # Continue without AI enhancement
        
        return changes
    
    def _enhance_with_ai(
        self,
        change: APIChangeEvent,
        context: Optional[Dict[str, Any]]
    ):
        """Enhance a single change with AI analysis"""
        # Build prompt
        prompt = self._build_prompt(change, context)
        
        # Call AI
        response = self._call_ai(prompt)
        
        # Parse response
        enhancements = self._parse_ai_response(response)
        
        # Apply enhancements
        change.ai_enhanced = True
        change.ai_reasoning = enhancements.get("reasoning", "")
        
        # Add AI-generated recommendations (don't replace rule-based ones)
        ai_tests = enhancements.get("recommended_tests", [])
        change.recommended_tests.extend(ai_tests)
        
        # Add AI-identified impacts
        ai_impacts = enhancements.get("impacted_areas", [])
        change.impacted_areas.extend(ai_impacts)
        
        # Update risk level if AI suggests higher risk
        ai_risk = enhancements.get("risk_level")
        if ai_risk and self._risk_level_higher(ai_risk, change.risk_level.value):
            change.risk_level = RiskLevel(ai_risk)
    
    def _build_prompt(
        self,
        change: APIChangeEvent,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build AI prompt with structured input"""
        prompt = f"""Analyze this API change and provide testing recommendations.

Change Details:
- Type: {change.change_type.value}
- Entity: {change.entity_type.value}
- Name: {change.entity_name}
- Path: {change.path}
- Method: {change.http_method}
- Breaking: {change.breaking}
- Current Risk: {change.risk_level.value}

Change Specifics:
{self._format_change_details(change.change_details)}

Rule-Based Recommendations (already identified):
{chr(10).join(f"- {t}" for t in change.recommended_tests[:5])}

"""
        
        if context:
            prompt += f"\nAdditional Context:\n"
            if "historical_failures" in context:
                prompt += f"- Historical failures: {context['historical_failures']}\n"
            if "test_coverage" in context:
                prompt += f"- Test coverage: {context['test_coverage']}\n"
        
        prompt += """
Please provide:
1. Risk analysis (is current risk level appropriate?)
2. Additional test scenarios humans might miss
3. Potential edge cases
4. Downstream impact areas

Format your response as JSON:
{
  "risk_level": "low|medium|high|critical",
  "reasoning": "brief explanation",
  "recommended_tests": ["test 1", "test 2", ...],
  "edge_cases": ["case 1", "case 2", ...],
  "impacted_areas": ["area 1", "area 2", ...]
}
"""
        return prompt
    
    def _call_ai(self, prompt: str) -> str:
        """Call AI provider"""
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert API testing consultant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            self.tokens_used += response.usage.total_tokens
            return response.choices[0].message.content
        
        elif self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            self.tokens_used += response.usage.input_tokens + response.usage.output_tokens
            return response.content[0].text
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response JSON"""
        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback if not valid JSON
            return {
                "reasoning": response,
                "recommended_tests": [],
                "impacted_areas": []
            }
    
    def _format_change_details(self, details: Dict[str, Any]) -> str:
        """Format change details for prompt"""
        if not details:
            return "No additional details"
        
        lines = []
        for key, value in details.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)
    
    def _risk_level_higher(self, new_level: str, current_level: str) -> bool:
        """Check if new risk level is higher than current"""
        levels = ["low", "medium", "high", "critical"]
        return levels.index(new_level) > levels.index(current_level)
    
    def get_token_usage(self) -> Dict[str, int]:
        """Get current token usage statistics"""
        return {
            "tokens_used": self.tokens_used,
            "monthly_limit": self.monthly_limit,
            "remaining": self.monthly_limit - self.tokens_used,
            "percent_used": (self.tokens_used / self.monthly_limit) * 100
        }
```

### Phase 4: Documentation Generation (Week 2)

#### Step 4.1: Markdown Generator
```python
# intelligence/api_change/doc_generator/markdown.py
from typing import List
from datetime import datetime
from pathlib import Path
from ..models.api_change import APIChangeEvent, DiffResult

class MarkdownGenerator:
    """Generate incremental Markdown documentation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_dir = Path(config.get("output_dir", "docs/api-changes"))
        self.output_file = config.get("file", "api-changes.md")
        self.append_mode = config.get("append_mode", True)
    
    def generate(self, result: DiffResult):
        """Generate markdown documentation for diff result"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / self.output_file
        
        content = self._build_content(result)
        
        if self.append_mode and output_path.exists():
            # Append to existing file
            with output_path.open("a") as f:
                f.write("\n\n---\n\n")
                f.write(content)
        else:
            # Create new file
            with output_path.open("w") as f:
                f.write(self._build_header())
                f.write(content)
        
        print(f"Documentation written to: {output_path}")
    
    def _build_header(self) -> str:
        """Build document header"""
        return f"""# API Change Log

Generated by CrossBridge API Change Intelligence

---

"""
    
    def _build_content(self, result: DiffResult) -> str:
        """Build content for a single diff result"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        
        content = f"""## API Changes – {timestamp}

**Spec Versions:**
- Previous: `{result.old_spec_version}`
- Current: `{result.new_spec_version}`

**Summary:**
- Total Changes: {result.total_changes}
- Breaking Changes: {result.breaking_changes}
- High Risk Changes: {result.high_risk_changes}
"""
        
        if result.ai_tokens_used > 0:
            content += f"- AI Tokens Used: {result.ai_tokens_used}\n"
        
        content += "\n"
        
        # Group changes by type
        added = [c for c in result.changes if c.change_type.value == "added"]
        modified = [c for c in result.changes if c.change_type.value == "modified"]
        removed = [c for c in result.changes if c.change_type.value == "removed"]
        
        # Added endpoints/schemas
        if added:
            content += "### ➕ Added\n\n"
            content += self._format_changes(added)
        
        # Modified endpoints/schemas
        if modified:
            content += "### 🔄 Modified\n\n"
            content += self._format_changes(modified)
        
        # Removed endpoints/schemas
        if removed:
            content += "### ❌ Removed\n\n"
            content += self._format_changes(removed)
        
        # Breaking changes section
        breaking = [c for c in result.changes if c.breaking]
        if breaking:
            content += "### ⚠️ Breaking Changes\n\n"
            for change in breaking:
                content += f"- **{change.entity_name}**\n"
                content += f"  - Risk: {change.risk_level.value.upper()}\n"
                if change.recommended_tests:
                    content += f"  - Action Required: {change.recommended_tests[0]}\n"
                content += "\n"
        else:
            content += "### ✅ No Breaking Changes\n\n"
        
        # High-risk changes
        high_risk = [c for c in result.changes if c.risk_level.value in ["high", "critical"]]
        if high_risk:
            content += "### 🔥 High Risk Changes\n\n"
            for change in high_risk:
                content += f"- **{change.entity_name}** ({change.risk_level.value})\n"
                if change.ai_reasoning:
                    content += f"  - AI Analysis: {change.ai_reasoning}\n"
                content += "\n"
        
        return content
    
    def _format_changes(self, changes: List[APIChangeEvent]) -> str:
        """Format a list of changes"""
        content = ""
        
        for change in changes:
            # Entity name with method/path
            if change.http_method and change.path:
                content += f"**`{change.http_method} {change.path}`**\n\n"
            else:
                content += f"**{change.entity_name}**\n\n"
            
            # Risk badge
            risk_emoji = {
                "low": "🟢",
                "medium": "🟡",
                "high": "🔴",
                "critical": "⚫"
            }
            content += f"- Risk: {risk_emoji.get(change.risk_level.value, '⚪')} {change.risk_level.value.upper()}\n"
            
            # Breaking badge
            if change.breaking:
                content += "- **⚠️ BREAKING CHANGE**\n"
            
            # AI enhancement badge
            if change.ai_enhanced:
                content += "- 🤖 AI Enhanced\n"
            
            # Recommended tests
            if change.recommended_tests:
                content += "- **Recommended Tests:**\n"
                for test in change.recommended_tests[:5]:  # Limit to 5
                    content += f"  - {test}\n"
            
            # Impacted areas
            if change.impacted_areas:
                content += "- **Impacted Areas:** " + ", ".join(change.impacted_areas) + "\n"
            
            content += "\n"
        
        return content
```

### Phase 5: Grafana Integration (Week 3)

#### Step 5.1: Grafana Dashboard JSON
```json
// grafana/dashboards/api_change_intelligence.json
{
  "dashboard": {
    "title": "API Change Intelligence",
    "tags": ["crossbridge", "api", "changes"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "API Changes Over Time",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [
          {
            "refId": "A",
            "rawSql": "SELECT detected_at AS time, count(*) AS changes FROM api_changes WHERE $__timeFilter(detected_at) GROUP BY detected_at ORDER BY detected_at"
          }
        ]
      },
      {
        "id": 2,
        "title": "Breaking vs Non-Breaking Changes",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
        "targets": [
          {
            "refId": "A",
            "rawSql": "SELECT detected_at AS time, sum(CASE WHEN breaking THEN 1 ELSE 0 END) AS breaking, sum(CASE WHEN NOT breaking THEN 1 ELSE 0 END) AS non_breaking FROM api_changes WHERE $__timeFilter(detected_at) GROUP BY detected_at"
          }
        ]
      },
      {
        "id": 3,
        "title": "Risk Level Distribution",
        "type": "piechart",
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 8},
        "targets": [
          {
            "refId": "A",
            "rawSql": "SELECT risk_level, count(*) AS count FROM api_changes WHERE $__timeFilter(detected_at) GROUP BY risk_level"
          }
        ]
      },
      {
        "id": 4,
        "title": "High-Risk APIs Heatmap",
        "type": "table",
        "gridPos": {"h": 8, "w": 18, "x": 6, "y": 8},
        "targets": [
          {
            "refId": "A",
            "rawSql": "SELECT api_name, count(*) AS high_risk_changes FROM api_changes WHERE risk_level IN ('high', 'critical') AND $__timeFilter(detected_at) GROUP BY api_name ORDER BY high_risk_changes DESC LIMIT 10"
          }
        ]
      },
      {
        "id": 5,
        "title": "AI Usage vs Manual Detection",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
        "targets": [
          {
            "refId": "A",
            "rawSql": "SELECT detected_at AS time, count(*) FILTER (WHERE ai_enhanced = true) AS ai, count(*) FILTER (WHERE ai_enhanced = false) AS rules FROM api_changes WHERE $__timeFilter(detected_at) GROUP BY detected_at"
          }
        ]
      },
      {
        "id": 6,
        "title": "AI Token Usage",
        "type": "stat",
        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 16},
        "targets": [
          {
            "refId": "A",
            "rawSql": "SELECT sum(ai_tokens_used) AS total_tokens FROM api_diff_runs WHERE $__timeFilter(started_at)"
          }
        ]
      },
      {
        "id": 7,
        "title": "Change Type Breakdown",
        "type": "barchart",
        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 16},
        "targets": [
          {
            "refId": "A",
            "rawSql": "SELECT change_type, count(*) AS count FROM api_changes WHERE $__timeFilter(detected_at) GROUP BY change_type"
          }
        ]
      },
      {
        "id": 8,
        "title": "Recent Breaking Changes",
        "type": "table",
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 24},
        "targets": [
          {
            "refId": "A",
            "rawSql": "SELECT detected_at, api_name, entity_name, risk_level, recommended_tests[1] AS primary_action FROM api_changes WHERE breaking = true AND $__timeFilter(detected_at) ORDER BY detected_at DESC LIMIT 20"
          }
        ]
      }
    ]
  }
}
```

### Phase 6: Alerts & CI Triggering (Week 3)

#### Step 6.1: Alert System
```python
# intelligence/api_change/alerts/slack_notifier.py
from typing import List, Dict, Any
import requests
from ..models.api_change import APIChangeEvent

class SlackNotifier:
    """Send Slack alerts for API changes"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get("webhook_url")
        self.channel = config.get("channel", "#api-alerts")
        self.mention_users = config.get("mention_users", [])
    
    def send_alert(self, changes: List[APIChangeEvent]):
        """Send Slack notification for changes"""
        if not self.webhook_url:
            return
        
        # Filter to alertable changes
        alertable = [
            c for c in changes
            if c.breaking or c.risk_level.value in ["high", "critical"]
        ]
        
        if not alertable:
            return
        
        message = self._build_message(alertable)
        
        response = requests.post(
            self.webhook_url,
            json=message,
            timeout=10
        )
        response.raise_for_status()
    
    def _build_message(self, changes: List[APIChangeEvent]) -> Dict[str, Any]:
        """Build Slack message payload"""
        breaking_count = sum(1 for c in changes if c.breaking)
        high_risk_count = sum(1 for c in changes if c.risk_level.value in ["high", "critical"])
        
        # Header
        text = "🚨 *API Change Alert*\n\n"
        
        if breaking_count > 0:
            text += f"⚠️ *{breaking_count} Breaking Change(s)*\n"
        
        if high_risk_count > 0:
            text += f"🔥 *{high_risk_count} High Risk Change(s)*\n"
        
        text += "\n"
        
        # List changes
        for change in changes[:5]:  # Limit to 5 to avoid huge messages
            emoji = "⚠️" if change.breaking else "🔴" if change.risk_level.value == "high" else "⚫"
            text += f"{emoji} *{change.entity_name}*\n"
            text += f"  Risk: {change.risk_level.value.upper()}\n"
            
            if change.recommended_tests:
                text += f"  Action: {change.recommended_tests[0]}\n"
            
            text += "\n"
        
        if len(changes) > 5:
            text += f"_...and {len(changes) - 5} more changes_\n\n"
        
        # Mentions
        if self.mention_users:
            text += " ".join(self.mention_users)
        
        return {
            "channel": self.channel,
            "text": text,
            "username": "CrossBridge API Monitor",
            "icon_emoji": ":robot_face:"
        }
```

#### Step 6.2: CI Trigger
```python
# intelligence/api_change/ci_trigger/test_selector.py
from typing import List, Set
from ..models.api_change import APIChangeEvent
from ..models.test_impact import TestImpact

class TestSelector:
    """Select tests to run based on API changes"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.strategy = config.get("strategy", "impact-based")
        self.max_tests = config.get("max_tests", 100)
        self.include_indirect = config.get("include_indirect", True)
    
    def select_tests(
        self,
        changes: List[APIChangeEvent],
        coverage_map: Dict[str, List[str]]
    ) -> List[str]:
        """
        Select tests to run based on changes and coverage
        
        Args:
            changes: List of API changes
            coverage_map: Mapping of API endpoints/schemas to test IDs
        
        Returns:
            List of test IDs to execute
        """
        if self.strategy == "all":
            # Run all tests (not recommended)
            return self._get_all_tests(coverage_map)
        
        elif self.strategy == "impact-based":
            return self._select_impacted_tests(changes, coverage_map)
        
        elif self.strategy == "risk-weighted":
            return self._select_risk_weighted_tests(changes, coverage_map)
        
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")
    
    def _select_impacted_tests(
        self,
        changes: List[APIChangeEvent],
        coverage_map: Dict[str, List[str]]
    ) -> List[str]:
        """Select tests directly impacted by changes"""
        selected_tests = set()
        
        for change in changes:
            # Get tests for this change
            change_key = self._get_change_key(change)
            tests = coverage_map.get(change_key, [])
            selected_tests.update(tests)
            
            # Include tests for related endpoints
            if self.include_indirect and change.path:
                # Find tests that use the same base path
                base_path = self._get_base_path(change.path)
                for key, tests in coverage_map.items():
                    if base_path in key:
                        selected_tests.update(tests)
        
        # Limit to max_tests (prioritize by change risk)
        if len(selected_tests) > self.max_tests:
            prioritized = self._prioritize_tests(selected_tests, changes, coverage_map)
            return prioritized[:self.max_tests]
        
        return list(selected_tests)
    
    def _select_risk_weighted_tests(
        self,
        changes: List[APIChangeEvent],
        coverage_map: Dict[str, List[str]]
    ) -> List[str]:
        """Select tests weighted by risk level"""
        test_scores = {}
        
        for change in changes:
            change_key = self._get_change_key(change)
            tests = coverage_map.get(change_key, [])
            
            # Score based on risk
            risk_weight = {
                "low": 1,
                "medium": 2,
                "high": 4,
                "critical": 8
            }.get(change.risk_level.value, 1)
            
            if change.breaking:
                risk_weight *= 2
            
            for test in tests:
                test_scores[test] = test_scores.get(test, 0) + risk_weight
        
        # Sort by score and select top N
        sorted_tests = sorted(test_scores.items(), key=lambda x: x[1], reverse=True)
        return [test for test, score in sorted_tests[:self.max_tests]]
    
    def _get_change_key(self, change: APIChangeEvent) -> str:
        """Generate key for coverage lookup"""
        if change.path and change.http_method:
            return f"{change.http_method}:{change.path}"
        else:
            return change.entity_name
    
    def _get_base_path(self, path: str) -> str:
        """Extract base path (e.g., /api/v1/users/123 -> /api/v1/users)"""
        parts = path.split("/")
        # Remove last part if it looks like an ID
        if parts[-1].isdigit() or "{" in parts[-1]:
            parts = parts[:-1]
        return "/".join(parts)
    
    def _prioritize_tests(
        self,
        tests: Set[str],
        changes: List[APIChangeEvent],
        coverage_map: Dict[str, List[str]]
    ) -> List[str]:
        """Prioritize tests by change importance"""
        # This is a simplified version - implement full prioritization logic
        return list(tests)
    
    def _get_all_tests(self, coverage_map: Dict[str, List[str]]) -> List[str]:
        """Get all tests from coverage map"""
        all_tests = set()
        for tests in coverage_map.values():
            all_tests.update(tests)
        return list(all_tests)
```

### Phase 7: CLI Interface (Week 3)

```python
# cli/commands/api_diff.py
import click
from intelligence.api_change import APIChangeOrchestrator
from core.config import load_config

@click.group()
def api_diff():
    """API Change Intelligence commands"""
    pass

@api_diff.command()
@click.option("--config", default="crossbridge.yml", help="Config file path")
@click.option("--ai/--no-ai", default=None, help="Enable/disable AI enhancement")
@click.option("--alerts/--no-alerts", default=None, help="Enable/disable alerts")
@click.option("--ci-trigger/--no-ci-trigger", default=None, help="Enable/disable CI trigger")
def run(config, ai, alerts, ci_trigger):
    """Run API diff analysis"""
    # Load config
    cfg = load_config(config)
    
    # Override with CLI flags
    if ai is not None:
        cfg["api_change"]["intelligence"]["ai"]["enabled"] = ai
    if alerts is not None:
        cfg["api_change"]["alerts"]["enabled"] = alerts
    if ci_trigger is not None:
        cfg["api_change"]["ci"]["enabled"] = ci_trigger
    
    # Run analysis
    orchestrator = APIChangeOrchestrator(cfg["api_change"])
    result = orchestrator.run()
    
    # Print summary
    click.echo(f"\n✅ Analysis Complete")
    click.echo(f"Total Changes: {result.total_changes}")
    click.echo(f"Breaking Changes: {result.breaking_changes}")
    click.echo(f"High Risk: {result.high_risk_changes}")
    if result.ai_tokens_used > 0:
        click.echo(f"AI Tokens Used: {result.ai_tokens_used}")

@api_diff.command()
@click.argument("output", type=click.Path())
def export_tests(output):
    """Export selected test list for CI"""
    # Implementation here
    pass
```

---

## 🚀 Usage Examples

### Basic Usage
```bash
# Run with defaults (no AI, no alerts, no CI)
crossbridge api-diff run

# Enable AI enhancement
crossbridge api-diff run --ai

# Enable everything
crossbridge api-diff run --ai --alerts --ci-trigger
```

### CI Integration (GitHub Actions)
```yaml
name: API Change Detection

on:
  pull_request:
    paths:
      - 'docs/api/openapi.yaml'

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 2
      
      - name: Setup CrossBridge
        run: pip install crossbridge
      
      - name: Analyze API Changes
        run: |
          crossbridge api-diff run --alerts
      
      - name: Trigger Selective Tests
        if: success()
        run: |
          # Get selected tests
          crossbridge api-diff export-tests impacted-tests.txt
          
          # Run only impacted tests
          pytest $(cat impacted-tests.txt)
```

---

## 📊 Success Metrics

1. **QA Efficiency**
   - Reduce time to understand API changes by 70%
   - Reduce missed test scenarios by 50%

2. **Documentation Currency**
   - API change docs updated within minutes of spec change
   - Zero manual doc lag

3. **Test Precision**
   - Run only 20-30% of test suite on average
   - Maintain 95%+ defect catch rate

4. **AI Value**
   - 30%+ additional test scenarios identified
   - 40%+ reduction in post-release API bugs

---

## 🎯 Implementation Timeline

| Week | Deliverable | Status |
|------|-------------|--------|
| 1 | Core infrastructure + OASDiff integration | 📋 Planned |
| 2 | Intelligence engine (rules + AI) | 📋 Planned |
| 2 | Documentation generation | 📋 Planned |
| 3 | Grafana dashboards | 📋 Planned |
| 3 | Alerts & CI triggering | 📋 Planned |
| 3 | CLI & testing | 📋 Planned |
| 4 | Documentation & examples | 📋 Planned |
| 4 | Beta release | 📋 Planned |

---

## 🔐 Security & Privacy

1. **API Specs**: Never sent to external AI providers without explicit consent
2. **AI Prompts**: Only normalized change metadata sent, not full specs
3. **Token Limits**: Hard caps prevent runaway costs
4. **Audit Trail**: All AI calls logged with org/project context

---

## 💰 Monetization Model

### Open Source (Free)
- Spec diffing
- Rule-based intelligence
- Markdown docs
- PostgreSQL storage
- Grafana dashboards

### Professional (Metered AI)
- AI-enhanced risk analysis
- AI test recommendations
- Advanced impact reasoning
- Historical correlation
- **Pricing**: $X per 100k tokens (bulk rate)

### Enterprise
- Dedicated AI models
- Priority support
- Custom rules
- White-label dashboards
- **Pricing**: Annual license

---

## 📝 Next Steps

1. **Review this specification** with stakeholders
2. **Prioritize features** for MVP (Week 1-2 scope)
3. **Set up development environment**
4. **Begin Phase 1 implementation**
5. **Create test data** (sample OpenAPI specs)

---

## 📞 Questions & Feedback

For questions about this specification:
- **Email**: vikas.sdet@gmail.com
- **Slack**: #api-change-intel
- **GitHub**: [crossstack-ai/crossbridge](https://github.com/crossstack-ai/crossbridge)

---

**Built with ❤️ by CrossStack AI**

*Bridging API Changes to Test Intelligence*
