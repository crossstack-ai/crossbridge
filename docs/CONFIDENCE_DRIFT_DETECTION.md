# Confidence Drift Detection System

## Overview

The Confidence Drift Detection System monitors changes in test confidence scores over time, identifying significant drifts that may indicate:
- Changes in test behavior or stability
- Degradation/improvement of signal quality
- Need for classifier recalibration
- Environmental changes affecting tests

**Status**: ✅ Complete (Commit: 0673eec)  
**Tests**: 31/31 passing  
**Demo**: `demo_confidence_drift.py`

---

## Key Features

### 1. Per-Test Drift Tracking
- Record confidence measurements over time
- Maintain historical data per test
- Support for metadata (failure_id, rule_score, signal_score)

### 2. Severity Classification (5 Levels)
- **NONE**: < 5% drift (no action needed)
- **LOW**: 5-10% drift (monitor)
- **MODERATE**: 10-20% drift (investigate)
- **HIGH**: 20-30% drift (urgent attention)
- **CRITICAL**: > 30% drift (immediate action)

### 3. Direction Detection (4 Types)
- **STABLE**: Minimal changes
- **INCREASING**: Confidence improving
- **DECREASING**: Confidence degrading
- **VOLATILE**: Frequent fluctuations

### 4. Trend Analysis
- Linear regression to detect patterns
- Classify trends: stable, gradually increasing/decreasing, strongly increasing/decreasing
- Predict future drift direction

### 5. Alert System
- Automatic alert generation for drifting tests
- Severity-based filtering
- Time-based alert queries (e.g., last 24 hours)
- Actionable recommendations per alert

### 6. Category-Level Aggregation
- Analyze drift across test categories
- Aggregate statistics (average drift, distribution by severity)
- Identify worst-performing categories

### 7. Time Window Filtering
- Short-term analysis (7 days)
- Medium-term analysis (30 days)
- Long-term analysis (90 days)
- Custom time windows supported

### 8. Integration with Explainability
- Extract confidence from `ConfidenceExplanation` objects
- Link drift to signal/rule changes
- Seamless integration with existing explainability system

---

## Architecture

### Core Components

```python
# Main drift detector
DriftDetector
  ├── record_confidence()          # Record measurements
  ├── detect_drift()                # Analyze drift for a test
  ├── detect_category_drift()       # Analyze category-level drift
  ├── get_all_drifting_tests()      # Get all drifting tests
  └── get_confidence_history()      # Retrieve history for visualization

# Alert manager
DriftAlertManager
  ├── check_for_alerts()            # Generate alerts for drifting tests
  └── get_recent_alerts()           # Query recent alerts

# Helper function
detect_drift_from_explanations()    # Build detector from explanations
```

### Data Models

```python
@dataclass
class ConfidenceRecord:
    test_name: str
    confidence: float           # 0.0-1.0
    category: str
    timestamp: datetime
    failure_id: Optional[str]
    rule_score: Optional[float]
    signal_score: Optional[float]

@dataclass
class DriftAnalysis:
    test_name: str
    current_confidence: float
    baseline_confidence: float
    drift_percentage: float     # e.g., 0.15 = 15% drift
    drift_absolute: float
    severity: DriftSeverity
    direction: DriftDirection
    is_drifting: bool
    measurements_count: int
    time_span: timedelta
    trend: str                  # "strongly_increasing", etc.
    recommendations: List[str]
    timestamp: datetime

@dataclass
class CategoryDriftSummary:
    category: str
    tests_analyzed: int
    drifting_tests: int
    avg_drift_percentage: float
    max_drift_test: Optional[str]
    max_drift_percentage: float
    drift_distribution: Dict[str, int]  # severity -> count
    timestamp: datetime

@dataclass
class DriftAlert:
    test_name: str
    severity: DriftSeverity
    drift_percentage: float
    message: str
    recommendations: List[str]
    timestamp: datetime
```

### Enumerations

```python
class DriftSeverity(Enum):
    NONE = "none"           # < 5%
    LOW = "low"             # 5-10%
    MODERATE = "moderate"   # 10-20%
    HIGH = "high"           # 20-30%
    CRITICAL = "critical"   # > 30%

class DriftDirection(Enum):
    STABLE = "stable"
    INCREASING = "increasing"
    DECREASING = "decreasing"
    VOLATILE = "volatile"
```

---

## Algorithm

### Drift Detection Process

1. **Data Collection**
   - Record confidence measurements over time
   - Require minimum 3 measurements for analysis

2. **Baseline Calculation**
   - Take earliest 1/3 of measurements
   - Calculate average confidence

3. **Current Calculation**
   - Take latest 1/3 of measurements
   - Calculate average confidence

4. **Drift Computation**
   - `drift_percentage = (current - baseline) / baseline`
   - `drift_absolute = current - baseline`

5. **Severity Classification**
   - Map drift percentage to severity level
   - Use configurable thresholds

6. **Direction Detection**
   - Calculate standard deviation (volatility check)
   - Compare first third vs last third
   - Classify: stable, increasing, decreasing, or volatile

7. **Trend Analysis**
   - Perform linear regression on measurements
   - Calculate slope to determine trend strength
   - Classify: stable, gradually/strongly increasing/decreasing

8. **Recommendation Generation**
   - Based on severity + direction + trend
   - Provide actionable next steps

### Example Drift Calculation

```
Measurements: [0.75, 0.75, 0.75, 0.88, 0.88]

Baseline (first 2): (0.75 + 0.75) / 2 = 0.75
Current (last 2):   (0.88 + 0.88) / 2 = 0.88

Drift %:  (0.88 - 0.75) / 0.75 = 0.173 = 17.3%
Severity: MODERATE (10-20%)
Direction: INCREASING
Trend: strongly_increasing
```

---

## Usage Examples

### Basic Usage

```python
from core.intelligence.confidence_drift import DriftDetector, DriftSeverity

# Create detector
detector = DriftDetector()

# Record measurements over time
detector.record_confidence("test_login", 0.75, "flaky")
detector.record_confidence("test_login", 0.76, "flaky")
detector.record_confidence("test_login", 0.88, "flaky")
detector.record_confidence("test_login", 0.90, "flaky")

# Detect drift
analysis = detector.detect_drift("test_login")
if analysis and analysis.is_drifting:
    print(f"Drift detected: {analysis.severity.value}")
    print(f"Direction: {analysis.direction.value}")
    print(f"Recommendations:")
    for rec in analysis.recommendations:
        print(f"  - {rec}")
```

### Alert System

```python
from core.intelligence.confidence_drift import DriftAlertManager

# Create alert manager
alert_manager = DriftAlertManager(detector)

# Check for alerts (moderate severity or higher)
alerts = alert_manager.check_for_alerts(min_severity=DriftSeverity.MODERATE)

for alert in alerts:
    print(f"ALERT: {alert.message}")
    print(f"Severity: {alert.severity.value}")
    print(f"Recommendations:")
    for rec in alert.recommendations:
        print(f"  - {rec}")
```

### Category-Level Analysis

```python
# Analyze drift for all tests in a category
summary = detector.detect_category_drift("flaky")

print(f"Category: {summary.category}")
print(f"Tests drifting: {summary.drifting_tests}/{summary.tests_analyzed}")
print(f"Average drift: {summary.avg_drift_percentage:.1%}")
print(f"Distribution:")
for severity, count in summary.drift_distribution.items():
    print(f"  {severity}: {count} tests")
```

### Time Window Filtering

```python
from datetime import timedelta

# Analyze last 7 days only
analysis_7d = detector.detect_drift("test_login", window=timedelta(days=7))

# Analyze last 30 days
analysis_30d = detector.detect_drift("test_login", window=timedelta(days=30))

# Analyze all data
analysis_all = detector.detect_drift("test_login")
```

### Integration with Explainability

```python
from core.intelligence.confidence_drift import detect_drift_from_explanations

# Build detector from explanations
explanations = [...]  # List of ConfidenceExplanation objects
detector = detect_drift_from_explanations(explanations)

# Now analyze drift
analysis = detector.detect_drift("test_name")
```

---

## Configuration

### Drift Thresholds

```python
from core.intelligence.confidence_drift import DriftThresholds, DriftDetector

# Custom thresholds
thresholds = DriftThresholds()
thresholds.LOW_DRIFT = 0.08        # 8% instead of 5%
thresholds.MODERATE_DRIFT = 0.15   # 15% instead of 10%
thresholds.HIGH_DRIFT = 0.25       # 25% instead of 20%
thresholds.CRITICAL_DRIFT = 0.35   # 35% instead of 30%

# Use custom thresholds
detector = DriftDetector(thresholds=thresholds)
```

### Available Thresholds

| Threshold | Default | Description |
|-----------|---------|-------------|
| `LOW_DRIFT` | 0.05 (5%) | Minimum drift for LOW severity |
| `MODERATE_DRIFT` | 0.10 (10%) | Minimum drift for MODERATE severity |
| `HIGH_DRIFT` | 0.20 (20%) | Minimum drift for HIGH severity |
| `CRITICAL_DRIFT` | 0.30 (30%) | Minimum drift for CRITICAL severity |
| `MIN_MEASUREMENTS` | 3 | Minimum measurements required |
| `VOLATILITY_THRESHOLD` | 0.15 | Threshold for volatile classification |
| `SHORT_TERM_WINDOW` | 7 days | Short-term analysis window |
| `MEDIUM_TERM_WINDOW` | 30 days | Medium-term analysis window |
| `LONG_TERM_WINDOW` | 90 days | Long-term analysis window |

---

## Recommendation Engine

The system generates actionable recommendations based on drift characteristics:

### Critical/High Severity
- "🚨 URGENT: Investigate root cause immediately"
- "Consider disabling test until investigation complete"
- "Review classification rules and signal weights"

### Decreasing Confidence
- "⚠️ Check for signal quality degradation"
- "Review recent changes to test or environment"
- "Verify data sources are still reliable"

### Increasing Confidence
- "✓ Confidence improving"
- "Validate: Are test conditions more stable?"
- "Document changes that improved stability"

### Volatile Behavior
- "⚡ High volatility detected"
- "Review signal consistency and environmental factors"
- "Consider test reliability improvements"

### Strong Trends
- "Strong trend detected: [direction]"
- "Consider recalibration if trend continues"
- "Monitor closely for next [X] days"

### Large Changes
- "Large confidence change (>20%)"
- "Review classification rules and signal weights"
- "Run additional test cycles to gather more data"

---

## Demo Script

Run `python demo_confidence_drift.py` to see:

1. **Basic Drift Detection** - Simple drift scenario
2. **Severity Levels** - LOW, MODERATE, HIGH, CRITICAL examples
3. **Drift Directions** - INCREASING, DECREASING, VOLATILE
4. **Trend Analysis** - Gradual vs strong trends
5. **Category Analysis** - Multi-test aggregation
6. **Time Windows** - Short/medium/long-term filtering
7. **Alert System** - Alert generation and filtering
8. **Integration** - Connection with explainability system
9. **Bulk Analysis** - Get all drifting tests

---

## Test Coverage

**Test File**: `tests/intelligence/test_confidence_drift.py`  
**Total Tests**: 31/31 passing ✅

### Test Classes

1. **TestConfidenceRecord** (3 tests)
   - Validation of confidence ranges

2. **TestDriftDetector** (9 tests)
   - Core drift detection logic
   - Severity classification
   - Direction detection

3. **TestTrendAnalysis** (4 tests)
   - Gradual vs strong trends
   - Increasing vs decreasing

4. **TestCategoryDrift** (2 tests)
   - Category-level aggregation
   - Empty category handling

5. **TestTimeWindows** (2 tests)
   - Time-based filtering
   - History retrieval

6. **TestDriftAlerts** (3 tests)
   - Alert generation
   - Severity filtering
   - Time-based queries

7. **TestRecommendations** (3 tests)
   - Critical drift recommendations
   - Decreasing drift recommendations
   - Volatile recommendations

8. **TestDriftFromExplanations** (1 test)
   - Integration with explainability

9. **TestUtilityMethods** (4 tests)
   - Get all drifting tests
   - Clear history
   - String representation

---

## Performance Considerations

### Memory Usage
- History stored in-memory per test
- Consider periodic cleanup for long-running systems
- Use time windows to limit analysis scope

### Computation
- Drift detection: O(n) where n = number of measurements
- Category analysis: O(m*n) where m = tests, n = measurements
- Linear regression: O(n) for trend analysis

### Optimization Tips
- Use time windows to limit data processed
- Clear old history periodically: `detector.clear_history("test_name")`
- Filter alerts by severity to reduce noise

---

## Future Enhancements

### Planned Features
1. **Persistence** - Save/load drift history to database
2. **Visualization** - Confidence trend charts
3. **Automated Actions** - Auto-disable tests on critical drift
4. **Machine Learning** - Predict future drift
5. **Correlation Analysis** - Link drift to code changes
6. **Dashboard Integration** - Grafana panels for drift monitoring
7. **CI/CD Integration** - Fail builds on critical drift

### API Endpoints (Future)
```
GET  /api/drift/tests/{test_name}           # Get drift analysis
GET  /api/drift/categories/{category}       # Get category drift
GET  /api/drift/alerts                      # Get active alerts
POST /api/drift/record                      # Record confidence
GET  /api/drift/trends/{test_name}          # Get trend data
```

---

## Integration Points

### With Explainability System
- Extract confidence from `ConfidenceExplanation`
- Link drift to signal/rule changes
- Provide explanations for drift causes

### With Intelligence Engine
- Monitor classifier confidence over time
- Detect model degradation
- Trigger recalibration when needed

### With CI/CD
- Fail builds on critical drift
- Generate drift reports in test results
- Alert teams via Slack/email

### With Dashboard
- Visualize drift trends over time
- Show category-level health metrics
- Display active alerts and recommendations

---

## Troubleshooting

### No Drift Detected
- Ensure minimum 3 measurements recorded
- Check if drift is below LOW threshold (< 5%)
- Verify timestamps are correct

### Unexpected Volatility
- Review measurement frequency
- Check for environmental factors
- Validate data source reliability

### False Alarms
- Adjust drift thresholds in configuration
- Increase minimum measurements requirement
- Use longer time windows for analysis

### Missing Measurements
- Verify `record_confidence()` is called
- Check timestamp filtering with time windows
- Ensure test names match exactly

---

## Related Documentation

- [Explainability System](./EXPLAINABILITY_SYSTEM.md)
- [Intelligence Engine](./INTELLIGENCE_ENGINE.md)
- [Flaky Test Detection](./FLAKY_DETECTION.md)

---

## Changelog

### Version 1.0.0 (2026-01-30) - Initial Release
- ✅ Per-test drift tracking
- ✅ 5-level severity classification
- ✅ 4-type direction detection
- ✅ Trend analysis with linear regression
- ✅ Alert system with recommendations
- ✅ Category-level aggregation
- ✅ Time window filtering
- ✅ Integration with explainability
- ✅ 31/31 tests passing
- ✅ Comprehensive demo script

**Commit**: 0673eec  
**Files**:
- `core/intelligence/confidence_drift.py` (673 lines)
- `tests/intelligence/test_confidence_drift.py` (585 lines)
- `demo_confidence_drift.py` (446 lines)
