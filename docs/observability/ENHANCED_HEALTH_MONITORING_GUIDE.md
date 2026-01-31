# CrossBridge Enhanced Health Monitoring System

> **Complete guide to using CrossBridge's v2 health check system**

## Overview

CrossBridge includes a production-ready enhanced health monitoring system that provides:

- **Versioned Health API** - `/health`, `/health/v1`, `/health/v2`
- **Sub-component tracking** - Monitor orchestrator, adapters, plugins, database, queues
- **SLI/SLO support** - Service Level Indicators with targets and compliance tracking
- **Historical trends** - Track health over time with anomaly detection
- **Kubernetes-compatible** - Liveness (`/live`) and readiness (`/ready`) probes
- **Prometheus integration** - Native metrics export at `/metrics`

---

## Table of Contents

1. [Architecture](#architecture)
2. [Health Endpoints](#health-endpoints)
3. [Integration Guide](#integration-guide)
4. [Prometheus & Alerting](#prometheus--alerting)
5. [CI/CD Integration](#cicd-integration)
6. [Extending the System](#extending-the-system)
7. [Troubleshooting](#troubleshooting)

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│            EnhancedHealthMonitor (Singleton)             │
├─────────────────────────────────────────────────────────┤
│  • Component Registration & Tracking                     │
│  • SLI/SLO Management                                    │
│  • Historical Data Collection                            │
│  • Trend Analysis                                        │
└──────────────────┬──────────────────────────────────────┘
                   │
         ┌─────────┴──────────┐
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌────────────────────┐
│  HTTP Endpoints │  │  Health Checkers   │
├─────────────────┤  ├────────────────────┤
│ /health/v1      │  │ • Orchestrator     │
│ /health/v2      │  │ • Database         │
│ /ready          │  │ • Event Queue      │
│ /live           │  │ • Plugin System    │
│ /metrics        │  │ • Adapters         │
│ /sli            │  │ • Semantic Engine  │
└─────────────────┘  └────────────────────┘
```

### Key Files

- `core/observability/health_v2.py` - Enhanced health monitor core
- `core/observability/health_endpoints.py` - HTTP endpoint handlers
- `core/observability/health_monitor.py` - Base health monitoring
- `core/sidecar/health.py` - Sidecar-specific health checks
- `core/runtime/health.py` - Runtime health check framework

---

## Health Endpoints

### GET /health (v1 - Backward Compatible)

Simple health status for legacy systems.

**Request:**
```bash
curl http://localhost:9090/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1738454400.123,
  "uptime_seconds": 3600.5,
  "components": {
    "orchestrator": "healthy",
    "database": "healthy",
    "plugin_system": "healthy",
    "event_queue": "degraded"
  }
}
```

**Status Codes:**
- `200 OK` - System is healthy or degraded
- `503 Service Unavailable` - System is unhealthy
- `500 Internal Server Error` - Unknown status

---

### GET /health/v2 (Enhanced)

Comprehensive health status with detailed metrics, SLIs, and trends.

**Request:**
```bash
curl http://localhost:9090/health/v2 | jq .
```

**Response:**
```json
{
  "version": "2.0",
  "status": "healthy",
  "timestamp": 1738454400.123,
  "timestamp_iso": "2026-02-01T10:00:00.123Z",
  "uptime_seconds": 3600.5,
  
  "components": {
    "orchestrator": {
      "component": "orchestrator",
      "component_type": "orchestrator",
      "status": "healthy",
      "message": "Orchestrator running normally",
      "last_check_time": 1738454399.5,
      "last_check_timestamp": "2026-02-01T09:59:59.5Z",
      "metrics": {
        "execution_queue_size": {
          "value": 5,
          "unit": "count",
          "threshold_warning": 50,
          "threshold_critical": 100,
          "status": "healthy"
        },
        "active_executions": {
          "value": 2,
          "unit": "count",
          "threshold_warning": 10,
          "threshold_critical": 20,
          "status": "healthy"
        }
      },
      "errors": [],
      "warnings": []
    },
    "database": {
      "component": "database",
      "component_type": "database",
      "status": "healthy",
      "message": "Database connection active",
      "last_check_time": 1738454399.8,
      "last_check_timestamp": "2026-02-01T09:59:59.8Z",
      "metrics": {
        "connection_pool_active": {
          "value": 3,
          "unit": "connections",
          "threshold_warning": 8,
          "threshold_critical": 10,
          "status": "healthy"
        },
        "query_latency_p95": {
          "value": 15.5,
          "unit": "milliseconds",
          "threshold_warning": 100,
          "threshold_critical": 500,
          "status": "healthy"
        }
      },
      "errors": [],
      "warnings": []
    },
    "event_queue": {
      "component": "event_queue",
      "component_type": "event_queue",
      "status": "degraded",
      "message": "Queue utilization above warning threshold",
      "last_check_time": 1738454400.0,
      "last_check_timestamp": "2026-02-01T10:00:00.0Z",
      "metrics": {
        "queue_size": {
          "value": 7500,
          "unit": "events",
          "threshold_warning": 5000,
          "threshold_critical": 10000,
          "status": "degraded"
        },
        "utilization": {
          "value": 75.0,
          "unit": "percent",
          "threshold_warning": 70,
          "threshold_critical": 90,
          "status": "degraded"
        }
      },
      "errors": [],
      "warnings": ["Queue size above warning threshold"]
    }
  },
  
  "summary": {
    "total_components": 6,
    "healthy": 5,
    "degraded": 1,
    "unhealthy": 0,
    "unknown": 0
  },
  
  "slis": {
    "availability": {
      "name": "availability",
      "description": "System availability (uptime)",
      "current_value": 99.95,
      "target_value": 99.9,
      "unit": "percent",
      "status": "healthy",
      "measurement_window": "last_hour",
      "compliance": true
    },
    "latency_p95": {
      "name": "latency_p95",
      "description": "95th percentile event processing latency",
      "current_value": 45.2,
      "target_value": 100.0,
      "unit": "milliseconds",
      "status": "healthy",
      "measurement_window": "last_5_minutes",
      "compliance": true
    },
    "error_rate": {
      "name": "error_rate",
      "description": "Error rate across all operations",
      "current_value": 0.15,
      "target_value": 1.0,
      "unit": "percent",
      "status": "healthy",
      "measurement_window": "last_5_minutes",
      "compliance": true
    }
  },
  
  "trends": {
    "last_5_minutes": {
      "available": true,
      "window_seconds": 300,
      "checks_count": 10,
      "avg_healthy_percentage": 91.67,
      "latest_status": "healthy",
      "trend": "stable"
    },
    "last_hour": {
      "available": true,
      "window_seconds": 3600,
      "checks_count": 120,
      "avg_healthy_percentage": 95.83,
      "latest_status": "healthy",
      "trend": "improving"
    }
  }
}
```

---

### GET /ready (Readiness Probe)

Kubernetes-compatible readiness check. Returns 200 if system is ready to accept requests.

**Request:**
```bash
curl http://localhost:9090/ready
```

**Response:**
```json
{
  "ready": true,
  "status": "healthy",
  "timestamp": 1738454400.123
}
```

**Status Codes:**
- `200 OK` - System is ready (healthy or degraded)
- `503 Service Unavailable` - System is not ready (unhealthy)

**Kubernetes Usage:**
```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 9090
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

---

### GET /live (Liveness Probe)

Basic liveness check - is the process running?

**Request:**
```bash
curl http://localhost:9090/live
```

**Response:**
```json
{
  "alive": true,
  "timestamp": 1738454400.123
}
```

**Status Codes:**
- `200 OK` - Process is alive

**Kubernetes Usage:**
```yaml
livenessProbe:
  httpGet:
    path: /live
    port: 9090
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

---

### GET /metrics (Prometheus)

Prometheus-formatted metrics export.

**Request:**
```bash
curl http://localhost:9090/metrics
```

**Response:**
```
# HELP crossbridge_health_status Overall health status (1=healthy, 0=unhealthy)
# TYPE crossbridge_health_status gauge
crossbridge_health_status{status="healthy"} 1

# HELP crossbridge_component_health_status Component health status
# TYPE crossbridge_component_health_status gauge
crossbridge_component_health_status{component="orchestrator",status="healthy"} 1
crossbridge_component_health_status{component="database",status="healthy"} 1
crossbridge_component_health_status{component="event_queue",status="degraded"} 1

# HELP crossbridge_sli_availability_percent Availability SLI
# TYPE crossbridge_sli_availability_percent gauge
crossbridge_sli_availability_percent 99.95

# HELP crossbridge_sli_latency_p95_ms Latency P95 SLI
# TYPE crossbridge_sli_latency_p95_ms gauge
crossbridge_sli_latency_p95_ms 45.2
```

---

## Integration Guide

### Python Integration

#### Registering a Component

```python
from core.observability.health_v2 import (
    get_health_monitor,
    ComponentType,
    HealthStatus,
    HealthMetric
)

# Get global health monitor
monitor = get_health_monitor()

# Register your component
monitor.register_component(
    component="my_service",
    component_type=ComponentType.ADAPTER_REGISTRY,
    check_func=my_health_check  # Your health check function
)
```

#### Updating Component Health

```python
from core.observability.health_v2 import get_health_monitor, HealthStatus, HealthMetric

monitor = get_health_monitor()

# Update health status
monitor.update_component_health(
    component="my_service",
    status=HealthStatus.HEALTHY,
    message="Service operating normally",
    metrics={
        "requests_per_second": HealthMetric(
            name="requests_per_second",
            value=150.5,
            unit="req/sec",
            threshold_warning=200.0,
            threshold_critical=300.0
        ),
        "error_rate": HealthMetric(
            name="error_rate",
            value=0.05,
            unit="percent",
            threshold_warning=1.0,
            threshold_critical=5.0
        )
    },
    errors=[],
    warnings=[]
)
```

#### Updating SLIs

```python
from core.observability.health_v2 import get_health_monitor

monitor = get_health_monitor()

# Update availability SLI
monitor.update_sli("availability", 99.95)

# Update latency SLI
monitor.update_sli("latency_p95", 45.2)

# Update error rate SLI
monitor.update_sli("error_rate", 0.15)
```

---

### Docker Integration

#### docker-compose.yml

```yaml
version: "3.9"

services:
  crossbridge:
    image: crossbridge/crossbridge:0.2.0
    ports:
      - "9090:9090"  # Health endpoint port
    environment:
      - CROSSBRIDGE_HEALTH_ENABLED=true
      - CROSSBRIDGE_HEALTH_PORT=9090
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/ready"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## Prometheus & Alerting

### Prometheus Configuration

See [`monitoring/prometheus/prometheus.yml`](../../monitoring/prometheus/prometheus.yml) for complete configuration.

**Quick Setup:**

```bash
# Start Prometheus
docker run -d \
  --name prometheus \
  -p 9091:9090 \
  -v $(pwd)/monitoring/prometheus:/etc/prometheus \
  prom/prometheus:latest \
  --config.file=/etc/prometheus/prometheus.yml
```

### Alert Rules

See [`monitoring/prometheus/alerts.yml`](../../monitoring/prometheus/alerts.yml) for all alert rules.

**Example Alerts:**
- `CrossBridgeUnhealthy` - System is unhealthy for >2 minutes
- `CrossBridgeDown` - Cannot reach health endpoint
- `ComponentUnhealthy` - Individual component failure
- `AvailabilitySLOBreach` - Availability below 99.9%
- `QueueSaturation` - Event queue >90% full

### Alertmanager Setup

See [`monitoring/prometheus/alertmanager.yml`](../../monitoring/prometheus/alertmanager.yml) for notification configuration.

**Supported Channels:**
- Email
- Slack
- PagerDuty
- OpsGenie (custom webhook)

**Start Alertmanager:**

```bash
docker run -d \
  --name alertmanager \
  -p 9093:9093 \
  -v $(pwd)/monitoring/prometheus:/etc/alertmanager \
  prom/alertmanager:latest \
  --config.file=/etc/alertmanager/alertmanager.yml
```

---

## CI/CD Integration

### Health Gate in CI/CD

Block CI pipeline if CrossBridge is unhealthy:

```bash
#!/bin/bash
# check-health.sh

HEALTH_URL="http://crossbridge:9090/health/v2"
MAX_RETRIES=3
RETRY_DELAY=5

for i in $(seq 1 $MAX_RETRIES); do
  echo "Checking CrossBridge health (attempt $i/$MAX_RETRIES)..."
  
  RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/health.json "$HEALTH_URL")
  HTTP_CODE="${RESPONSE: -3}"
  
  if [ "$HTTP_CODE" = "200" ]; then
    STATUS=$(jq -r '.status' /tmp/health.json)
    
    if [ "$STATUS" = "healthy" ]; then
      echo "✅ CrossBridge is healthy"
      exit 0
    elif [ "$STATUS" = "degraded" ]; then
      echo "⚠️  CrossBridge is degraded but operational"
      exit 0
    else
      echo "❌ CrossBridge is unhealthy: $STATUS"
      jq '.components | to_entries | map(select(.value.status != "healthy"))' /tmp/health.json
      exit 1
    fi
  else
    echo "❌ Health check failed with HTTP $HTTP_CODE"
  fi
  
  if [ $i -lt $MAX_RETRIES ]; then
    echo "Retrying in ${RETRY_DELAY}s..."
    sleep $RETRY_DELAY
  fi
done

echo "❌ Health check failed after $MAX_RETRIES attempts"
exit 1
```

### GitHub Actions

```yaml
name: Test with CrossBridge

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      crossbridge:
        image: crossbridge/crossbridge:0.2.0
        ports:
          - 9090:9090
        options: >-
          --health-cmd "curl -f http://localhost:9090/ready"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Wait for CrossBridge
        run: |
          ./scripts/check-health.sh
        
      - name: Run Tests
        run: |
          pytest tests/
```

### GitLab CI

```yaml
test:
  image: python:3.11
  services:
    - name: crossbridge/crossbridge:0.2.0
      alias: crossbridge
  variables:
    CROSSBRIDGE_URL: http://crossbridge:9090
  before_script:
    - curl --retry 10 --retry-delay 5 --retry-connrefused http://crossbridge:9090/ready
  script:
    - pytest tests/
```

---

## Extending the System

### Adding Custom Components

```python
from core.observability.health_v2 import (
    get_health_monitor,
    ComponentType,
    HealthStatus,
    HealthMetric,
    ComponentHealthStatus
)

class MyCustomComponent:
    def __init__(self):
        self.monitor = get_health_monitor()
        
        # Register component
        self.monitor.register_component(
            component="my_custom_component",
            component_type=ComponentType.ADAPTER_REGISTRY,
            check_func=self._check_health
        )
    
    def _check_health(self) -> ComponentHealthStatus:
        """Custom health check logic."""
        try:
            # Your health check logic
            is_healthy = self._perform_checks()
            
            return ComponentHealthStatus(
                component="my_custom_component",
                component_type=ComponentType.ADAPTER_REGISTRY,
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
                message="Component is operational" if is_healthy else "Component failed",
                last_check_time=time.time(),
                metrics={
                    "custom_metric": HealthMetric(
                        name="custom_metric",
                        value=100.0,
                        unit="percent",
                        threshold_warning=80.0,
                        threshold_critical=60.0
                    )
                }
            )
        except Exception as e:
            return ComponentHealthStatus(
                component="my_custom_component",
                component_type=ComponentType.ADAPTER_REGISTRY,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                last_check_time=time.time(),
                errors=[str(e)]
            )
```

### Adding Custom SLIs

```python
from core.observability.health_v2 import get_health_monitor, SLI, HealthStatus

monitor = get_health_monitor()

# Add custom SLI
monitor._slis['custom_throughput'] = SLI(
    name='custom_throughput',
    description='Custom throughput metric',
    current_value=0.0,
    target_value=1000.0,
    unit='req/sec',
    status=HealthStatus.UNKNOWN,
    measurement_window='last_5_minutes'
)

# Update it periodically
monitor.update_sli('custom_throughput', 1250.5)
```

---

## Troubleshooting

### Health Endpoint Not Responding

```bash
# Check if process is running
ps aux | grep crossbridge

# Check port binding
netstat -tlnp | grep 9090

# Check logs
docker logs crossbridge --tail 100

# Test direct connection
curl -v http://localhost:9090/health
```

### Component Showing Unhealthy

```bash
# Get detailed component status
curl -s http://localhost:9090/health/v2 | jq '.components.database'

# Check component metrics
curl -s http://localhost:9090/health/v2 | jq '.components.database.metrics'

# Check errors and warnings
curl -s http://localhost:9090/health/v2 | jq '.components.database.errors'
```

### SLI Not Updating

```python
# Verify SLI is registered
from core.observability.health_v2 import get_health_monitor

monitor = get_health_monitor()
print(monitor._slis.keys())

# Update SLI manually
monitor.update_sli("availability", 99.95)

# Check updated value
health = monitor.get_health_v2()
print(health['slis']['availability'])
```

---

## Best Practices

1. **Register components early** - During initialization, not runtime
2. **Update health frequently** - Every 15-30 seconds
3. **Use meaningful metrics** - Track what matters for your component
4. **Set appropriate thresholds** - Warning before critical
5. **Provide actionable messages** - Help operators understand issues
6. **Monitor SLIs continuously** - Track compliance over time
7. **Test health checks** - Verify they detect real failures
8. **Document runbooks** - Link from alerts to resolution steps

---

## API Reference

Full API documentation: [API Reference](../api/health-api.md)

---

## Related Documentation

- [Runbooks](../runbooks/) - Incident response procedures
- [Prometheus Alerts](../../monitoring/prometheus/alerts.yml) - Alert rules
- [Sidecar Integration](../quick-start/SIDECAR_INTEGRATION_GUIDE.md) - Observer mode setup
- [Docker Guide](../DOCKER_GUIDE.md) - Container deployment

---

## Support

- **Issues**: https://github.com/crossstack-ai/crossbridge/issues
- **Discussions**: https://github.com/crossstack-ai/crossbridge/discussions
- **Email**: support@crossstack.ai
