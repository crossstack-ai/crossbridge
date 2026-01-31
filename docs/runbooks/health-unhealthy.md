# Runbook: CrossBridge Health Unhealthy

## Alert

**Alert Name:** `CrossBridgeUnhealthy`  
**Severity:** Critical  
**Description:** CrossBridge has been in unhealthy state for more than 2 minutes

---

## Impact

- Test execution may be blocked or failing
- Data collection and persistence affected
- Intelligence features unavailable
- CI/CD pipelines may fail

---

## Diagnosis

### 1. Check Overall Health

```bash
# Get detailed health status
curl -s http://localhost:9090/health/v2 | jq .

# Check which components are unhealthy
curl -s http://localhost:9090/health/v2 | jq '.components | to_entries | map(select(.value.status != "healthy"))'
```

### 2. Check Component-Specific Health

```bash
# Check each component
for component in orchestrator database plugin_system event_queue; do
  echo "=== $component ==="
  curl -s http://localhost:9090/health/component/$component | jq '.'
done
```

### 3. Check Logs

```bash
# Docker
docker logs crossbridge --tail 100

# Kubernetes
kubectl logs -l app=crossbridge --tail=100

# System logs
journalctl -u crossbridge -n 100
```

### 4. Check Metrics

```bash
# Get Prometheus metrics
curl -s http://localhost:9090/metrics | grep -E "(error|unhealthy|failed)"
```

---

## Common Causes & Remediation

### Cause 1: Database Connection Failed

**Symptoms:**
- Database component shows `unhealthy`
- Error: `Unable to connect to database`

**Remediation:**
```bash
# Check database connectivity
psql -h $CROSSBRIDGE_DB_HOST -U $CROSSBRIDGE_DB_USER -d $CROSSBRIDGE_DB_NAME -c "SELECT 1;"

# If connection fails:
# 1. Verify database is running
docker ps | grep postgres
kubectl get pods | grep postgres

# 2. Check network connectivity
ping $CROSSBRIDGE_DB_HOST
telnet $CROSSBRIDGE_DB_HOST 5432

# 3. Verify credentials
echo $CROSSBRIDGE_DB_PASSWORD

# 4. Restart database if needed
docker restart postgres
kubectl rollout restart deployment/postgres
```

### Cause 2: Queue Overload

**Symptoms:**
- Event queue component shows `unhealthy`
- `sidecar_queue_utilization > 0.95`
- High event drop rate

**Remediation:**
```bash
# Check queue stats
curl -s http://localhost:9090/health/v2 | jq '.components.event_queue.metrics'

# Immediate fix: Increase queue size
# Edit crossbridge.yml
max_queue_size: 20000  # Increase from 10000

# Or set via environment
export CROSSBRIDGE_MAX_QUEUE_SIZE=20000

# Restart CrossBridge
docker restart crossbridge
kubectl rollout restart deployment/crossbridge

# Long-term: Enable adaptive sampling
# Edit crossbridge.yml
sampling:
  enabled: true
  adaptive: true
  rates:
    events: 0.5
```

### Cause 3: Resource Exhaustion

**Symptoms:**
- High CPU or memory usage
- `cpu_over_budget` or `memory_over_budget`
- Profiling auto-disabled

**Remediation:**
```bash
# Check resource usage
curl -s http://localhost:9090/metrics | grep -E "sidecar_(cpu|memory)"

# Increase resource limits (Docker)
docker update --cpus="2.0" --memory="4g" crossbridge

# Increase resource limits (Kubernetes)
kubectl edit deployment crossbridge
# Update resources.limits.cpu and resources.limits.memory

# Reduce load temporarily
# Disable profiling
export CROSSBRIDGE_PROFILING_ENABLED=false

# Increase CPU budget
export CROSSBRIDGE_MAX_CPU_PERCENT=15.0
```

### Cause 4: High Error Rate

**Symptoms:**
- Error rate > 10%
- Multiple component errors
- Failed test executions

**Remediation:**
```bash
# Check error details
curl -s http://localhost:9090/health/v2 | jq '.components[].errors'

# Check error logs
docker logs crossbridge 2>&1 | grep -i error | tail -50

# Common fixes:
# 1. Restart service
docker restart crossbridge

# 2. Check dependencies
curl http://dependency-service/health

# 3. Roll back if recent deployment
kubectl rollout undo deployment/crossbridge

# 4. Check configuration
cat /opt/crossbridge/crossbridge.yml
```

---

## Escalation

### Level 1: Immediate Actions (5 min)

1. Check health endpoint for specific component failures
2. Review last 100 log lines
3. Verify database and dependencies are up
4. Restart CrossBridge if simple component failure

### Level 2: Investigation (15 min)

1. Analyze error patterns in logs
2. Check resource usage trends
3. Review recent deployments/changes
4. Check Prometheus metrics for anomalies

### Level 3: Engineering Escalation (30 min)

If unhealthy state persists after L1/L2:
1. Page on-call SRE engineer
2. Create incident ticket
3. Gather diagnostics bundle:
   ```bash
   # Create diagnostics bundle
   mkdir -p /tmp/crossbridge-diagnostics
   curl -s http://localhost:9090/health/v2 > /tmp/crossbridge-diagnostics/health.json
   curl -s http://localhost:9090/metrics > /tmp/crossbridge-diagnostics/metrics.txt
   docker logs crossbridge > /tmp/crossbridge-diagnostics/logs.txt 2>&1
   tar -czf crossbridge-diagnostics-$(date +%Y%m%d-%H%M%S).tar.gz /tmp/crossbridge-diagnostics/
   ```

---

## Prevention

### 1. Set Up Monitoring

```yaml
# prometheus-alerts.yml
- alert: CrossBridgeDegraded
  expr: crossbridge_health_status{status="degraded"} == 1
  for: 5m
  annotations:
    summary: "CrossBridge degraded - take action before unhealthy"
```

### 2. Configure Resource Buffers

```yaml
# crossbridge.yml
resources:
  max_cpu_percent: 10.0     # Leave 90% for tests
  max_memory_mb: 2048       # 2GB budget
  
queue:
  max_size: 10000
  warn_threshold: 8000      # Alert at 80%
```

### 3. Enable Fail-Open

```yaml
# crossbridge.yml
sidecar:
  fail_open: true  # Never block tests
  timeout_ms: 5000
```

### 4. Regular Health Checks

```bash
# Add to cron
*/5 * * * * curl -f http://localhost:9090/health || echo "CrossBridge unhealthy" | mail -s "ALERT" oncall@company.com
```

---

## Recovery Verification

After remediation, verify health recovery:

```bash
# 1. Check health status
curl -s http://localhost:9090/health/v2 | jq '.status'
# Expected: "healthy"

# 2. Check all components healthy
curl -s http://localhost:9090/health/v2 | jq '.summary'
# Expected: all components healthy

# 3. Monitor for 5 minutes
for i in {1..10}; do
  STATUS=$(curl -s http://localhost:9090/health | jq -r '.status')
  echo "$(date): $STATUS"
  sleep 30
done

# 4. Check SLIs recovered
curl -s http://localhost:9090/sli | jq '.slis | to_entries | map(select(.value.status != "healthy"))'
# Expected: empty array

# 5. Verify test execution works
crossbridge exec run --framework pytest --strategy smoke
```

---

## Related Runbooks

- [Health Degraded](health-degraded.md)
- [Database Connection Failed](database-connection-failed.md)
- [Queue Critical](queue-critical.md)
- [High CPU Usage](high-cpu.md)
- [High Error Rate](error-rate-critical.md)

---

## Post-Incident

1. **Document** - Record what happened, cause, and resolution
2. **Review** - Analyze why alerts didn't catch it earlier
3. **Improve** - Add monitoring/alerts to prevent recurrence
4. **Share** - Update runbook with learnings
