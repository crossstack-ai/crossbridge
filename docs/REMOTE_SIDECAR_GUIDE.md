# CrossBridge Remote Sidecar - Complete Guide

## Overview

The CrossBridge Remote Sidecar enables distributed test execution monitoring across multiple machines. The sidecar observer runs on a dedicated server, while test runners on different machines send events via HTTP.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Sidecar Observer Server                   │
│                    (crossbridge-sidecar)                     │
│                                                              │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐               │
│  │ FastAPI    │→ │ Observer │→ │ Database │               │
│  │ REST API   │  │  Engine  │  │ (Postgres)│               │
│  └────────────┘  └──────────┘  └──────────┘               │
│        ↑                                                     │
│    Port 8765                                                │
└─────────────────────────────────────────────────────────────┘
         ↑         ↑         ↑         ↑         ↑
         │         │         │         │         │
    HTTP │    HTTP │    HTTP │    HTTP │    HTTP │
         │         │         │         │         │
┌────────┴─┐  ┌───┴────┐  ┌─┴────┐  ┌─┴────┐  ┌─┴────┐
│ Robot    │  │ Pytest │  │TestNG│  │Cypress│  │Playwrt│
│ Runner 1 │  │Runner 2│  │Runner│  │Runner│  │Runner │
└──────────┘  └────────┘  └──────┘  └──────┘  └───────┘
```

## Deployment Options

### Option 1: Docker Compose (Recommended)

**1. Deploy the remote sidecar server:**

```bash
cd /path/to/crossbridge

# Start sidecar observer + PostgreSQL + Grafana
docker-compose -f docker-compose-remote-sidecar.yml up -d

# Check health
curl http://localhost:8765/health

# View logs
docker-compose -f docker-compose-remote-sidecar.yml logs -f crossbridge-sidecar
```

**2. Configure test runners to connect:**

On each test execution machine, set environment variables:

```bash
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_SIDECAR_HOST=<sidecar-server-ip>
export CROSSBRIDGE_SIDECAR_PORT=8765
```

### Option 2: CLI Command

**1. Start sidecar observer on server:**

```bash
# Install dependencies
pip install -r requirements.txt

# Start sidecar in observer mode
python -m crossbridge sidecar start \
  --mode observer \
  --host 0.0.0.0 \
  --port 8765

# Or using run_cli.py
python run_cli.py sidecar start --mode observer --host 0.0.0.0 --port 8765
```

**2. Test connection from client machine:**

```bash
python -m crossbridge sidecar test-connection \
  --host <sidecar-server-ip> \
  --port 8765
```

**3. Check sidecar status:**

```bash
python -m crossbridge sidecar status \
  --host <sidecar-server-ip> \
  --port 8765
```

## Framework-Specific Integration

### Robot Framework

**1. Copy listener to your project:**

```bash
cp adapters/robot/crossbridge_listener.py <your-project>/
```

**2. Configure environment:**

```bash
export PYTHONPATH=$PYTHONPATH:<your-project>
export ROBOT_LISTENER=crossbridge_listener.CrossBridgeListener
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_SIDECAR_HOST=192.168.1.100
export CROSSBRIDGE_SIDECAR_PORT=8765
```

**3. Run tests:**

```bash
robot tests/
```

### Pytest

**1. Copy plugin to your project:**

```bash
cp adapters/pytest/crossbridge_plugin.py <your-project>/
```

**2. Configure environment:**

```bash
export PYTHONPATH=$PYTHONPATH:<your-project>
export PYTEST_PLUGINS=crossbridge_plugin
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_SIDECAR_HOST=192.168.1.100
export CROSSBRIDGE_SIDECAR_PORT=8765
```

**3. Run tests:**

```bash
pytest tests/
```

### TestNG (Java)

**1. Copy listener to your project:**

```bash
cp adapters/java/CrossBridgeTestNGListener.java \
   src/main/java/com/crossbridge/sidecar/
```

**2. Add to testng.xml:**

```xml
<!DOCTYPE suite SYSTEM "https://testng.org/testng-1.0.dtd">
<suite name="Test Suite">
  <listeners>
    <listener class-name="com.crossbridge.sidecar.CrossBridgeTestNGListener"/>
  </listeners>
  
  <test name="MyTests">
    <classes>
      <class name="com.example.MyTest"/>
    </classes>
  </test>
</suite>
```

**3. Run with environment variables:**

```bash
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_SIDECAR_HOST=192.168.1.100
export CROSSBRIDGE_SIDECAR_PORT=8765

mvn test -DsuiteXmlFile=testng.xml
```

**Or via Maven command line:**

```bash
mvn test -Dlistener=com.crossbridge.sidecar.CrossBridgeTestNGListener \
         -DCROSSBRIDGE_ENABLED=true \
         -DCROSSBRIDGE_SIDECAR_HOST=192.168.1.100 \
         -DCROSSBRIDGE_SIDECAR_PORT=8765
```

### JUnit 5 (Java)

**1. Copy extension to your project:**

```bash
cp adapters/java/CrossBridgeJUnit5Extension.java \
   src/main/java/com/crossbridge/sidecar/
```

**2. Add to test classes:**

```java
import com.crossbridge.sidecar.CrossBridgeJUnit5Extension;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;

@ExtendWith(CrossBridgeJUnit5Extension.class)
public class MyTest {
    @Test
    public void testExample() {
        // Your test code
    }
}
```

**Or register globally** in `src/test/resources/META-INF/services/org.junit.jupiter.api.extension.Extension`:

```
com.crossbridge.sidecar.CrossBridgeJUnit5Extension
```

**3. Run with environment variables:**

```bash
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_SIDECAR_HOST=192.168.1.100
export CROSSBRIDGE_SIDECAR_PORT=8765

mvn test
```

### Playwright (TypeScript/JavaScript)

**1. Copy reporter to your project:**

```bash
cp adapters/playwright/crossbridge-playwright-reporter.ts \
   <your-project>/
```

**2. Add to playwright.config.ts:**

```typescript
import { defineConfig } from '@playwright/test';
import { CrossBridgeReporter } from './crossbridge-playwright-reporter';

export default defineConfig({
  reporter: [
    ['list'],
    [CrossBridgeReporter]
  ],
  // ... other config
});
```

**3. Run with environment variables:**

```bash
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_SIDECAR_HOST=192.168.1.100
export CROSSBRIDGE_SIDECAR_PORT=8765

npx playwright test
```

### Cypress (TypeScript/JavaScript)

**1. Copy plugin files to your project:**

```bash
cp adapters/cypress/crossbridge-cypress-plugin.ts \
   <your-project>/cypress/
cp adapters/cypress/crossbridge-cypress-support.ts \
   <your-project>/cypress/support/
```

**2. Add to cypress.config.ts:**

```typescript
import { defineConfig } from 'cypress';
import { setupCrossBridgePlugin } from './cypress/crossbridge-cypress-plugin';

export default defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      setupCrossBridgePlugin(on, config);
      return config;
    },
  },
});
```

**3. Add to cypress/support/e2e.ts:**

```typescript
import './crossbridge-cypress-support';
```

**4. Run with environment variables:**

```bash
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_SIDECAR_HOST=192.168.1.100
export CROSSBRIDGE_SIDECAR_PORT=8765

npx cypress run
```

## Jenkins Integration

### Jenkinsfile Example

```groovy
pipeline {
    agent any
    
    environment {
        CROSSBRIDGE_ENABLED = 'true'
        CROSSBRIDGE_SIDECAR_HOST = '192.168.1.100'  // Your sidecar server
        CROSSBRIDGE_SIDECAR_PORT = '8765'
    }
    
    stages {
        stage('Test') {
            parallel {
                stage('Robot Tests') {
                    steps {
                        sh '''
                            export ROBOT_LISTENER=crossbridge_listener.CrossBridgeListener
                            robot tests/
                        '''
                    }
                }
                stage('Pytest Tests') {
                    steps {
                        sh '''
                            export PYTEST_PLUGINS=crossbridge_plugin
                            pytest tests/
                        '''
                    }
                }
                stage('TestNG Tests') {
                    steps {
                        sh '''
                            mvn test -DsuiteXmlFile=testng.xml
                        '''
                    }
                }
            }
        }
    }
}
```

## API Endpoints

The remote sidecar exposes the following REST API:

### Health Check
```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "uptime_seconds": 3600.5,
  "version": "0.2.0"
}
```

### Send Single Event
```bash
POST /events
Content-Type: application/json

{
  "event_type": "test_start",
  "framework": "robot",
  "data": {
    "test_name": "Login Test",
    "test_id": "tests/login.robot::Login Test"
  },
  "timestamp": "2025-01-31T12:00:00Z"
}
```

### Send Batch Events
```bash
POST /events/batch
Content-Type: application/json

{
  "events": [
    {
      "event_type": "test_start",
      "framework": "robot",
      "data": {...}
    },
    {
      "event_type": "test_end",
      "framework": "robot",
      "data": {...}
    }
  ]
}
```

### Get Statistics
```bash
GET /stats
```

Response:
```json
{
  "total_events": 1234,
  "events_by_type": {
    "test_start": 500,
    "test_end": 500,
    "suite_start": 117,
    "suite_end": 117
  },
  "events_by_framework": {
    "robot": 800,
    "pytest": 434
  }
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CROSSBRIDGE_ENABLED` | Enable sidecar integration | `false` |
| `CROSSBRIDGE_SIDECAR_HOST` | Sidecar server hostname | `localhost` |
| `CROSSBRIDGE_SIDECAR_PORT` | Sidecar server port | `8765` |
| `CROSSBRIDGE_MODE` | Mode: `observer` or `client` | `client` |
| `CROSSBRIDGE_LOG_LEVEL` | Logging level | `INFO` |

### crossbridge.yml Configuration

```yaml
sidecar:
  mode: observer
  host: 0.0.0.0
  port: 8765
  
  # Resource limits
  max_queue_size: 10000
  max_memory_mb: 100
  max_cpu_percent: 5.0
  
  # Batch processing
  batch_size: 50
  batch_timeout_seconds: 1.0
  
  # Retry configuration
  max_retries: 3
  retry_delay_seconds: 1.0
  retry_backoff_multiplier: 2.0

database:
  host: postgres
  port: 5432
  name: crossbridge
  user: crossbridge
  password: ${DB_PASSWORD}

observability:
  grafana_url: http://grafana:3000
  slack_webhook_url: ${SLACK_WEBHOOK_URL}
```

## Monitoring

### Grafana Dashboards

Access Grafana at `http://<sidecar-host>:3000` (default credentials: admin/admin)

Pre-configured dashboards show:
- Event throughput (events/sec)
- Event latency distribution
- Framework breakdown
- Test success/failure rates
- System resource usage

### Logs

View sidecar logs:

```bash
# Docker Compose
docker-compose -f docker-compose-remote-sidecar.yml logs -f crossbridge-sidecar

# CLI mode
tail -f crossbridge-data/logs/sidecar.log
```

## Troubleshooting

### Connection Issues

**Problem:** Tests can't connect to sidecar

**Solutions:**
1. Check sidecar is running: `curl http://<host>:8765/health`
2. Verify firewall allows port 8765
3. Check network connectivity: `ping <sidecar-host>`
4. Test connection: `python -m crossbridge sidecar test-connection --host <host> --port 8765`

### Events Not Appearing

**Problem:** Tests run but no events in dashboard

**Solutions:**
1. Verify `CROSSBRIDGE_ENABLED=true` is set
2. Check listener/plugin is loaded (look for ✅ message in test output)
3. Review sidecar logs for errors
4. Test with: `curl -X POST http://<host>:8765/events -H "Content-Type: application/json" -d '{"event_type":"test","data":{}}'`

### Performance Issues

**Problem:** Sidecar slowing down tests

**Solutions:**
1. Increase batch size: `batch_size: 100`
2. Reduce event sampling rate
3. Scale sidecar horizontally (multiple instances behind load balancer)
4. Check database performance

## Security Considerations

### Production Deployment

1. **Enable HTTPS:** Use reverse proxy (nginx/traefik) with SSL certificates
2. **Authentication:** Add API key validation
3. **Network Isolation:** Deploy in private subnet, expose via VPN
4. **Firewall Rules:** Restrict access to known test runner IPs
5. **Database Security:** Use strong passwords, enable SSL connections

### Example nginx Configuration

```nginx
server {
    listen 443 ssl;
    server_name crossbridge.example.com;
    
    ssl_certificate /etc/ssl/certs/crossbridge.crt;
    ssl_certificate_key /etc/ssl/private/crossbridge.key;
    
    location / {
        proxy_pass http://localhost:8765;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # API key authentication
        if ($http_x_api_key != "your-secret-key") {
            return 401;
        }
    }
}
```

## Performance Tuning

### High-Volume Scenarios

For large-scale deployments (>1000 tests/hour):

1. **Increase batch size:**
   ```yaml
   sidecar:
     batch_size: 200
     batch_timeout_seconds: 2.0
   ```

2. **Scale database:**
   - Use PostgreSQL connection pooling
   - Enable write-ahead logging (WAL)
   - Increase shared_buffers

3. **Deploy multiple sidecar instances:**
   - Use load balancer (HAProxy/AWS ALB)
   - Share database backend
   - Enable sticky sessions

4. **Optimize network:**
   - Deploy sidecar in same region/datacenter as test runners
   - Use low-latency network connections
   - Consider Redis for event queuing

## Support

For issues or questions:
- GitHub Issues: https://github.com/crossstack/crossbridge/issues
- Documentation: https://crossbridge.dev/docs
- Email: support@crossstack.ai
