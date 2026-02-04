/**
 * CrossBridge Playwright Reporter for remote sidecar integration
 * 
 * Usage in playwright.config.ts:
 * 
 * import { CrossBridgeReporter } from './crossbridge-playwright-reporter';
 * 
 * export default defineConfig({
 *   reporter: [
 *     ['list'],
 *     [CrossBridgeReporter]
 *   ]
 * });
 * 
 * Environment Variables:
 * - CROSSBRIDGE_ENABLED: Set to "true" to enable
 * - CROSSBRIDGE_SIDECAR_HOST: Sidecar server hostname (default: localhost)
 * - CROSSBRIDGE_SIDECAR_PORT: Sidecar server port (default: 8765)
 */

import type {
  FullConfig,
  FullResult,
  Reporter,
  Suite,
  TestCase,
  TestResult,
} from '@playwright/test/reporter';

export class CrossBridgeReporter implements Reporter {
  private enabled: boolean;
  private apiUrl: string;
  private timeout: number = 2000;
  
  constructor() {
    this.enabled = process.env.CROSSBRIDGE_ENABLED?.toLowerCase() === 'true';
    
    if (this.enabled) {
      const host = process.env.CROSSBRIDGE_SIDECAR_HOST || process.env.CROSSBRIDGE_API_HOST || 'localhost';
      const port = process.env.CROSSBRIDGE_SIDECAR_PORT || process.env.CROSSBRIDGE_API_PORT || '8765';
      this.apiUrl = `http://${host}:${port}/events`;
      
      // Check health
      this.checkHealth(host, port);
    }
  }
  
  private async checkHealth(host: string, port: string): Promise<void> {
    try {
      const healthUrl = `http://${host}:${port}/health`;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);
      
      const response = await fetch(healthUrl, {
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (response.ok) {
        console.log(`✅ CrossBridge Playwright reporter connected to ${host}:${port}`);
      } else {
        this.enabled = false;
      }
    } catch (error) {
      console.log(`⚠️ CrossBridge Playwright reporter failed to connect: ${error}`);
      this.enabled = false;
    }
  }
  
  private async sendEvent(eventType: string, data: any): Promise<void> {
    if (!this.enabled) {
      return;
    }
    
    try {
      const event = {
        event_type: eventType,
        framework: 'playwright',
        data: data,
        timestamp: new Date().toISOString()
      };
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);
      
      await fetch(this.apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(event),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
    } catch (error) {
      // Fail-open: never block test execution
    }
  }
  
  onBegin(config: FullConfig, suite: Suite): void {
    this.sendEvent('suite_start', {
      total_tests: suite.allTests().length,
      workers: config.workers,
      project_names: config.projects.map(p => p.name)
    });
  }
  
  onTestBegin(test: TestCase, result: TestResult): void {
    this.sendEvent('test_start', {
      test_name: test.title,
      test_id: test.id,
      file: test.location.file,
      line: test.location.line,
      project: test.parent.project()?.name
    });
  }
  
  onTestEnd(test: TestCase, result: TestResult): void {
    const status = result.status === 'passed' ? 'PASS' :
                   result.status === 'failed' ? 'FAIL' :
                   result.status === 'timedOut' ? 'TIMEOUT' :
                   'SKIP';
    
    this.sendEvent('test_end', {
      test_name: test.title,
      test_id: test.id,
      status: status,
      elapsed_time_ms: result.duration,
      retry_count: result.retry,
      error: result.error?.message
    });
  }
  
  onEnd(result: FullResult): void {
    this.sendEvent('suite_end', {
      status: result.status,
      duration_ms: result.duration
    });
  }
}

export default CrossBridgeReporter;
