# AI Transformation Validation System

## Overview

The AI Transformation Validation System provides a comprehensive framework for managing AI-generated code changes with confidence scoring, human review workflows, rollback capabilities, and complete audit trails.

## Table of Contents

1. [Key Principles](#key-principles)
2. [Architecture](#architecture)
3. [Confidence Scoring](#confidence-scoring)
4. [Workflows](#workflows)
5. [CLI Reference](#cli-reference)
6. [API Reference](#api-reference)
7. [Integration Guide](#integration-guide)

---

## Key Principles

### Never Auto-Merge

AI-generated code is **never** automatically merged without human oversight. All transformations undergo review based on confidence levels.

### Numeric Confidence Scoring

Instead of binary yes/no decisions, the system uses numeric confidence scores (0.0-1.0) computed from multiple signals:

- Model confidence
- Diff size
- Rule violations
- Similarity to existing code
- Historical acceptance rate
- Syntax validity
- Test coverage maintenance

### Full Before/After Snapshots

Every transformation captures complete before and after snapshots, enabling:

- Accurate diffs
- Reliable rollbacks
- Audit trail reconstruction

### Mandatory Review for Low Confidence

Transformations with confidence below the threshold (default 0.8) **must** undergo human review before application.

### Idempotent Rollback

Rollback operations can be called multiple times safely. Rolling back an already rolled-back transformation is a no-op.

### Complete Audit Trail

Every transformation records:

- Model used
- Prompt (hashed for privacy)
- Confidence signals
- Review decisions
- Timestamps
- Reviewers

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Transformation System                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────┐      ┌─────────────────────────┐ │
│  │ transformation_      │      │ transformation_         │ │
│  │ validation.py        │◄─────┤ service.py              │ │
│  │                      │      │                         │ │
│  │ • Data Models        │      │ • Lifecycle Mgmt        │ │
│  │ • Confidence Scoring │      │ • Persistence           │ │
│  │ • Diff Generation    │      │ • Review Workflow       │ │
│  └──────────────────────┘      │ • Statistics            │ │
│                                 └──────────┬──────────────┘ │
│                                            │                  │
│  ┌────────────────────────────────────────▼────────────────┐│
│  │              cli/commands/ai_transform.py                ││
│  │                                                           ││
│  │  list | show | approve | reject | apply | rollback |    ││
│  │  audit | stats                                           ││
│  └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  .crossbridge/   │
                    │  transformations/│
                    │                  │
                    │  • {id}.json     │
                    └──────────────────┘
```

### Data Flow

1. **Generation**: AI generates code → Service computes confidence → Creates transformation record
2. **Review**: Human reviews → Approves/Rejects → Updates status
3. **Application**: Apply approved → Writes to file system → Updates status
4. **Rollback**: Restore previous state → Updates status → Logs event

---

## Confidence Scoring

### Computation Algorithm

```python
base_score = model_confidence

# Apply penalties
if diff_size > 100: base_score -= 0.3
elif diff_size > 50: base_score -= 0.2
elif diff_size > 20: base_score -= 0.1

if rule_violations > 0:
    base_score -= min(rule_violations * 0.1, 0.3)

if similarity_to_existing < 0.6: base_score -= 0.2
elif similarity_to_existing < 0.8: base_score -= 0.1

if historical_acceptance_rate:
    base_score *= historical_acceptance_rate

if not syntax_valid:
    base_score -= 0.4

if not test_coverage_maintained:
    base_score -= 0.2

final_score = clamp(base_score, 0.0, 1.0)
```

### Confidence Levels

| Score Range | Level | Review Required |
|------------|-------|-----------------|
| 0.8 - 1.0 | HIGH | No (but recommended) |
| 0.5 - 0.79 | MEDIUM | Yes |
| 0.0 - 0.49 | LOW | Yes |

### Input Signals

| Signal | Description | Impact |
|--------|-------------|--------|
| `model_confidence` | Model's self-reported confidence | Base multiplier |
| `diff_size` | Number of lines changed | -0.1 to -0.3 penalty |
| `rule_violations` | Linting/style violations | -0.1 per violation |
| `similarity_to_existing` | Cosine similarity to codebase | -0.1 to -0.2 penalty |
| `historical_acceptance_rate` | Previous approval rate | Multiplier |
| `syntax_valid` | Code parses successfully | -0.4 penalty |
| `test_coverage_maintained` | Coverage not decreased | -0.2 penalty |

---

## Workflows

### 1. Generate & Review Workflow

```bash
# 1. Generate transformation (via code)
transformation = service.generate(
    operation="generate",
    artifact_type="test",
    artifact_path="tests/test_login.py",
    before_content="",
    after_content=ai_generated_code,
    model="gpt-4",
    prompt="Generate login test",
    signals=ConfidenceSignals(model_confidence=0.9, diff_size=45)
)

# 2. List pending reviews
$ crossbridge ai-transform list --needs-review

# 3. View details
$ crossbridge ai-transform show ai-abc123 --show-diff

# 4. Approve
$ crossbridge ai-transform approve ai-abc123 --reviewer john@example.com --comments "LGTM"

# 5. Apply
$ crossbridge ai-transform apply ai-abc123
```

### 2. Rejection Workflow

```bash
# 1. Review transformation
$ crossbridge ai-transform show ai-def456 --show-diff

# 2. Reject with reason
$ crossbridge ai-transform reject ai-def456 \
    --reviewer jane@example.com \
    --reason "Syntax errors in generated code"
```

### 3. Rollback Workflow

```bash
# 1. List applied transformations
$ crossbridge ai-transform list --status applied

# 2. Rollback specific transformation
$ crossbridge ai-transform rollback ai-ghi789

# 3. Verify rollback in audit trail
$ crossbridge ai-transform audit ai-ghi789
```

### 4. Audit & Analytics Workflow

```bash
# View audit trail for specific transformation
$ crossbridge ai-transform audit ai-abc123

# Get system-wide statistics
$ crossbridge ai-transform stats

# Export statistics as JSON
$ crossbridge ai-transform stats --format json > stats.json
```

---

## CLI Reference

### `crossbridge ai-transform list`

List transformations with optional filters.

```bash
crossbridge ai-transform list [OPTIONS]

Options:
  --status STATUS        Filter by status (pending_review, approved, rejected, applied, rolled_back)
  --needs-review         Show only transformations requiring review
  --format FORMAT        Output format: table (default), detailed, json
  --storage-dir PATH     Custom storage directory
```

**Example:**
```bash
$ crossbridge ai-transform list --needs-review
ID          Operation  Type    Confidence  Status          Needs Review
ai-abc123   generate   test    0.72       pending_review  Yes
ai-def456   modify     code    0.65       pending_review  Yes
```

---

### `crossbridge ai-transform show`

Display detailed information about a transformation.

```bash
crossbridge ai-transform show <ID> [OPTIONS]

Options:
  --show-diff            Display unified diff
  --format FORMAT        Output format: detailed (default), json
  --storage-dir PATH     Custom storage directory
```

**Example:**
```bash
$ crossbridge ai-transform show ai-abc123 --show-diff

Transformation: ai-abc123
Status: pending_review
Operation: generate
Artifact: tests/test_login.py (test)

Confidence: 0.72 (MEDIUM)
Signals:
  - Model Confidence: 0.90
  - Diff Size: 45 lines
  - Syntax Valid: Yes

Diff:
--- tests/test_login.py
+++ tests/test_login.py
@@ -0,0 +1,10 @@
+def test_login():
+    assert True
```

---

### `crossbridge ai-transform approve`

Approve a transformation.

```bash
crossbridge ai-transform approve <ID> [OPTIONS]

Options:
  --reviewer EMAIL       Reviewer email (required)
  --comments TEXT        Approval comments
  --apply                Apply immediately after approval
  --storage-dir PATH     Custom storage directory
```

**Example:**
```bash
$ crossbridge ai-transform approve ai-abc123 \
    --reviewer john@example.com \
    --comments "Tests look good" \
    --apply

✓ Transformation ai-abc123 approved
✓ Applied successfully
```

---

### `crossbridge ai-transform reject`

Reject a transformation.

```bash
crossbridge ai-transform reject <ID> [OPTIONS]

Options:
  --reviewer EMAIL       Reviewer email (required)
  --reason TEXT          Rejection reason (required)
  --storage-dir PATH     Custom storage directory
```

**Example:**
```bash
$ crossbridge ai-transform reject ai-def456 \
    --reviewer jane@example.com \
    --reason "Syntax errors found"

✗ Transformation ai-def456 rejected
```

---

### `crossbridge ai-transform apply`

Apply an approved transformation.

```bash
crossbridge ai-transform apply <ID> [OPTIONS]

Options:
  --storage-dir PATH     Custom storage directory
```

**Example:**
```bash
$ crossbridge ai-transform apply ai-abc123

✓ Applied transformation ai-abc123 to tests/test_login.py
```

---

### `crossbridge ai-transform rollback`

Rollback an applied transformation.

```bash
crossbridge ai-transform rollback <ID> [OPTIONS]

Options:
  --storage-dir PATH     Custom storage directory
  --yes                  Skip confirmation prompt
```

**Example:**
```bash
$ crossbridge ai-transform rollback ai-abc123

⚠ This will revert tests/test_login.py to its previous state.
Continue? [y/N]: y

↶ Rolled back transformation ai-abc123
```

---

### `crossbridge ai-transform audit`

Display audit trail for a transformation.

```bash
crossbridge ai-transform audit <ID> [OPTIONS]

Options:
  --format FORMAT        Output format: detailed (default), json
  --storage-dir PATH     Custom storage directory
```

**Example:**
```bash
$ crossbridge ai-transform audit ai-abc123

Audit Trail: ai-abc123

Transformation Details:
  Operation: generate
  Model: gpt-4
  Prompt Hash: 1a2b3c4d
  Confidence: 0.85

Timeline:
  Created: 2026-01-29 10:15:23
  Reviewed: 2026-01-29 10:30:45 (john@example.com)
  Applied: 2026-01-29 10:31:02

Review:
  Reviewer: john@example.com
  Decision: approved
  Comments: Looks good
```

---

### `crossbridge ai-transform stats`

Show transformation statistics.

```bash
crossbridge ai-transform stats [OPTIONS]

Options:
  --format FORMAT        Output format: detailed (default), json
  --storage-dir PATH     Custom storage directory
```

**Example:**
```bash
$ crossbridge ai-transform stats

Transformation Statistics

Total Transformations: 50

By Status:
  Approved: 30 (60.0%)
  Rejected: 10 (20.0%)
  Pending Review: 8 (16.0%)
  Applied: 2 (4.0%)

By Confidence Level:
  High (≥0.8): 35 (70.0%)
  Medium (0.5-0.79): 10 (20.0%)
  Low (<0.5): 5 (10.0%)

Rates:
  Approval Rate: 75.0%
  Rejection Rate: 25.0%
  Average Confidence: 0.78
```

---

## API Reference

### AITransformationService

Main service class for managing transformations.

#### `__init__(storage_dir, confidence_threshold=0.8)`

Initialize service with storage directory and confidence threshold.

```python
from core.ai.transformation_service import AITransformationService

service = AITransformationService(
    storage_dir=Path(".crossbridge/transformations"),
    confidence_threshold=0.8
)
```

#### `generate(...)`

Generate a new transformation with confidence scoring.

```python
transformation = service.generate(
    operation="generate",           # Operation type
    artifact_type="test",           # Artifact type (test, code, config)
    artifact_path="test_login.py",  # File path
    before_content="",              # Content before transformation
    after_content=ai_code,          # AI-generated content
    model="gpt-4",                  # Model used
    prompt="Generate test",         # Prompt given to model
    signals=ConfidenceSignals(      # Optional: override signals
        model_confidence=0.9,
        diff_size=45
    ),
    metadata={}                     # Optional: custom metadata
)
```

**Returns**: `AITransformation` object

#### `approve(transformation_id, reviewer, comments="")`

Approve a transformation.

```python
approved = service.approve(
    transformation_id="ai-abc123",
    reviewer="john@example.com",
    comments="LGTM"
)
```

**Returns**: Updated `AITransformation`

#### `reject(transformation_id, reviewer, comments)`

Reject a transformation. Comments are required.

```python
rejected = service.reject(
    transformation_id="ai-def456",
    reviewer="jane@example.com",
    comments="Syntax errors found"
)
```

**Returns**: Updated `AITransformation`

#### `apply(transformation_id, apply_fn=None)`

Apply an approved transformation. Optionally provide custom apply function.

```python
# Default: writes to file system
applied = service.apply("ai-abc123")

# Custom apply function
def custom_apply(transformation):
    # Custom logic here
    return True

applied = service.apply("ai-abc123", apply_fn=custom_apply)
```

**Returns**: Updated `AITransformation`

#### `rollback(transformation_id, rollback_fn=None)`

Rollback an applied transformation. Idempotent.

```python
# Default: restores from before_snapshot
rolled_back = service.rollback("ai-abc123")

# Custom rollback function
def custom_rollback(transformation):
    # Custom logic here
    return True

rolled_back = service.rollback("ai-abc123", rollback_fn=custom_rollback)
```

**Returns**: Updated `AITransformation`

#### `get_audit_trail(transformation_id)`

Get complete audit trail for a transformation.

```python
audit = service.get_audit_trail("ai-abc123")

# Returns dict with:
# - transformation_id
# - operation
# - model
# - prompt_hash
# - confidence
# - status
# - timestamps
# - review (if reviewed)
```

**Returns**: `dict`

#### `get_statistics()`

Get system-wide transformation statistics.

```python
stats = service.get_statistics()

# Returns dict with:
# - total_transformations
# - by_status (dict)
# - by_confidence (dict)
# - approval_rate
# - rejection_rate
# - average_confidence
```

**Returns**: `dict`

---

### Data Models

#### AITransformation

Main transformation data model.

**Attributes:**
- `id: str` - Unique identifier (ai-{uuid})
- `operation: str` - Operation type (generate, modify, refactor)
- `artifact_type: str` - Type of artifact (test, code, config)
- `artifact_path: str` - Path to artifact
- `before_snapshot: str` - Content before transformation
- `after_snapshot: str` - Content after transformation
- `diff: str` - Unified diff
- `confidence: float` - Confidence score (0.0-1.0)
- `requires_review: bool` - Whether review is required
- `status: TransformationStatus` - Current status
- `model_used: str` - AI model used
- `prompt_hash: str` - Hashed prompt (for privacy)
- `created_at: datetime` - Creation timestamp
- `review: Optional[AITransformationReview]` - Review record
- `metadata: dict` - Custom metadata
- `audit_trail: list` - List of audit events

**Methods:**
- `to_dict()` - Serialize to dictionary
- `from_dict(data)` - Deserialize from dictionary

#### ConfidenceSignals

Input signals for confidence computation.

**Attributes:**
- `model_confidence: float` - Model's self-reported confidence
- `similarity_to_existing: Optional[float]` - Similarity to codebase (0.0-1.0)
- `rule_violations: int` - Number of linting violations
- `historical_acceptance_rate: Optional[float]` - Historical approval rate
- `diff_size: int` - Number of lines changed
- `syntax_valid: bool` - Whether code parses successfully
- `test_coverage_maintained: bool` - Whether coverage is maintained

#### AITransformationReview

Review record.

**Attributes:**
- `transformation_id: str` - ID of reviewed transformation
- `reviewer: str` - Reviewer identifier (email)
- `decision: str` - Decision (approved/rejected)
- `comments: str` - Review comments
- `reviewed_at: datetime` - Review timestamp

---

## Integration Guide

### Basic Integration

```python
from core.ai.transformation_service import AITransformationService
from core.ai.transformation_validation import ConfidenceSignals

# Initialize service
service = AITransformationService()

# Generate transformation
transformation = service.generate(
    operation="generate",
    artifact_type="test",
    artifact_path="tests/test_feature.py",
    before_content="",
    after_content=ai_generated_code,
    model="gpt-4",
    prompt="Generate comprehensive test",
    signals=ConfidenceSignals(
        model_confidence=0.92,
        diff_size=50,
        syntax_valid=True
    )
)

# Check if review required
if transformation.requires_review:
    print(f"Review required (confidence: {transformation.confidence})")
else:
    # Auto-apply high confidence transformations
    service.apply(transformation.id)
```

### Custom Apply/Rollback Functions

```python
def custom_apply(transformation):
    """Custom apply logic"""
    # Example: Apply via git
    with open(transformation.artifact_path, 'w') as f:
        f.write(transformation.after_snapshot)
    
    os.system(f"git add {transformation.artifact_path}")
    os.system(f"git commit -m 'AI: {transformation.operation}'")
    return True

def custom_rollback(transformation):
    """Custom rollback logic"""
    # Example: Rollback via git
    os.system(f"git checkout HEAD~1 -- {transformation.artifact_path}")
    return True

# Use custom functions
service.apply(transformation.id, apply_fn=custom_apply)
service.rollback(transformation.id, rollback_fn=custom_rollback)
```

### Integration with Existing Workflows

```python
# Example: Integrate with test generation
def generate_test_with_validation(test_name, prompt):
    # Generate with AI
    ai_code = your_ai_model.generate(prompt)
    
    # Create transformation
    transformation = service.generate(
        operation="generate",
        artifact_type="test",
        artifact_path=f"tests/test_{test_name}.py",
        before_content="",
        after_content=ai_code,
        model="gpt-4",
        prompt=prompt,
        signals=ConfidenceSignals(
            model_confidence=your_ai_model.confidence,
            syntax_valid=check_syntax(ai_code),
            diff_size=len(ai_code.split('\n'))
        )
    )
    
    # Handle based on confidence
    if transformation.confidence >= 0.8:
        print(f"High confidence ({transformation.confidence}), auto-applying")
        service.apply(transformation.id)
    else:
        print(f"Low confidence ({transformation.confidence}), review required")
        print(f"Review with: crossbridge ai-transform show {transformation.id}")
    
    return transformation
```

---

## Best Practices

### 1. Set Appropriate Thresholds

Adjust confidence threshold based on risk tolerance:

```python
# Conservative (more reviews)
service = AITransformationService(confidence_threshold=0.9)

# Balanced (default)
service = AITransformationService(confidence_threshold=0.8)

# Aggressive (fewer reviews)
service = AITransformationService(confidence_threshold=0.6)
```

### 2. Always Provide Complete Signals

More signals = better confidence scoring:

```python
signals = ConfidenceSignals(
    model_confidence=0.92,
    similarity_to_existing=0.85,
    rule_violations=0,
    historical_acceptance_rate=0.90,
    diff_size=45,
    syntax_valid=True,
    test_coverage_maintained=True
)
```

### 3. Review Low Confidence Transformations

Never bypass review for low confidence:

```python
if transformation.requires_review:
    # Force human review
    print(f"Review required: crossbridge ai-transform show {transformation.id}")
    # Don't auto-apply!
```

### 4. Use Audit Trails for Learning

Analyze audit trails to improve confidence scoring:

```python
stats = service.get_statistics()
if stats['approval_rate'] < 0.5:
    print("Low approval rate - consider adjusting confidence signals")
```

### 5. Test Rollback Procedures

Regularly test rollback to ensure reliability:

```python
# Apply transformation
service.apply(transformation.id)

# Verify application
assert Path(transformation.artifact_path).read_text() == transformation.after_snapshot

# Test rollback
service.rollback(transformation.id)

# Verify rollback
assert Path(transformation.artifact_path).read_text() == transformation.before_snapshot
```

---

## Troubleshooting

### Issue: Transformations Not Persisting

**Symptom**: Transformations disappear after restart

**Solution**: Ensure storage directory is writable and persisted:

```python
service = AITransformationService(
    storage_dir=Path(".crossbridge/transformations")
)
# Verify directory exists
service.storage_dir.mkdir(parents=True, exist_ok=True)
```

---

### Issue: Confidence Always Low

**Symptom**: All transformations require review

**Solution**: Check if signals are being provided:

```python
# Bad: No signals provided
transformation = service.generate(..., signals=None)

# Good: Provide signals
transformation = service.generate(
    ...,
    signals=ConfidenceSignals(
        model_confidence=0.9,
        syntax_valid=True,
        diff_size=20
    )
)
```

---

### Issue: Cannot Reject Transformation

**Symptom**: `AITransformationError: Rejection reason required`

**Solution**: Always provide comments when rejecting:

```python
# Bad: Empty comments
service.reject(id, reviewer, comments="")

# Good: Provide reason
service.reject(id, reviewer, comments="Syntax errors found")
```

---

### Issue: Rollback Fails

**Symptom**: Rollback doesn't restore original content

**Solution**: Ensure before_snapshot was captured:

```python
# Verify before_snapshot exists
transformation = service.get_transformation(id)
assert transformation.before_snapshot, "No before snapshot!"

# Use custom rollback if needed
def safe_rollback(t):
    if not t.before_snapshot:
        raise ValueError("Cannot rollback: no before snapshot")
    Path(t.artifact_path).write_text(t.before_snapshot)
    return True

service.rollback(id, rollback_fn=safe_rollback)
```

---

## FAQ

**Q: Can I use this with models other than GPT-4?**

A: Yes, the system is model-agnostic. Just specify the model name when generating transformations.

**Q: How are prompts stored?**

A: Prompts are hashed (SHA256) for privacy. Only the hash is stored in the audit trail.

**Q: Can I bypass review for high confidence transformations?**

A: Yes, transformations with confidence ≥ threshold (default 0.8) don't require review. However, review is still recommended.

**Q: Is rollback truly idempotent?**

A: Yes, calling rollback multiple times on the same transformation is safe and won't cause errors.

**Q: Can I customize the confidence scoring algorithm?**

A: Currently, the algorithm is fixed. Future versions may support custom scoring functions.

**Q: What happens if I delete a transformation JSON file?**

A: The transformation will no longer appear in listings. The service loads transformations from JSON files on initialization.

**Q: Can multiple users review the same transformation?**

A: No, each transformation has a single review record. The first approve/reject is final.

**Q: How do I export transformation data?**

A: Use `--format json` with CLI commands or call `transformation.to_dict()` in code.

---

## License

This system is part of the CrossBridge testing framework and follows the same license.