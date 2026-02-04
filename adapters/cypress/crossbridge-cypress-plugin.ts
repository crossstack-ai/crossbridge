/**
 * CrossBridge Cypress Plugin for remote sidecar integration
 * 
 * Usage in cypress.config.ts:
 * 
 * import { setupCrossBridgePlugin, crossBridgeEvents } from './crossbridge-cypress-plugin';
 * 
 * export default defineConfig({
 *   e2e: {
 *     setupNodeEvents(on, config) {
 *       setupCrossBridgePlugin(on, config);
 *       return config;
 *     },
 *   },
 * });
 * 
 * And in cypress/support/e2e.ts:
 * import './crossbridge-cypress-support';
 * 
 * Environment Variables:
 * - CROSSBRIDGE_ENABLED: Set to "true" to enable
 * - CROSSBRIDGE_SIDECAR_HOST: Sidecar server hostname (default: localhost)
 * - CROSSBRIDGE_SIDECAR_PORT: Sidecar server port (default: 8765)
 */

interface CrossBridgeConfig {
  enabled: boolean;
  apiUrl: string;
  timeout: number;
}

let config: CrossBridgeConfig;

async function initializeCrossBridge(): Promise<void> {
  const enabled = process.env.CROSSBRIDGE_ENABLED?.toLowerCase() === 'true';
  
  if (enabled) {
    const host = process.env.CROSSBRIDGE_SIDECAR_HOST || process.env.CROSSBRIDGE_API_HOST || 'localhost';
    const port = process.env.CROSSBRIDGE_SIDECAR_PORT || process.env.CROSSBRIDGE_API_PORT || '8765';
    const apiUrl = `http://${host}:${port}/events`;
    const timeout = 2000;
    
    // Check health
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);
      
      const response = await fetch(`http://${host}:${port}/health`, {
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (response.ok) {
        console.log(`✅ CrossBridge Cypress plugin connected to ${host}:${port}`);
        config = { enabled: true, apiUrl, timeout };
      } else {
        config = { enabled: false, apiUrl, timeout };
      }
    } catch (error) {
      console.log(`⚠️ CrossBridge Cypress plugin failed to connect: ${error}`);
      config = { enabled: false, apiUrl, timeout };
    }
  } else {
    config = { enabled: false, apiUrl: '', timeout: 2000 };
  }
}

async function sendEvent(eventType: string, data: any): Promise<void> {
  if (!config?.enabled) {
    return;
  }
  
  try {
    const event = {
      event_type: eventType,
      framework: 'cypress',
      data: data,
      timestamp: new Date().toISOString()
    };
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeout);
    
    await fetch(config.apiUrl, {
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

export function setupCrossBridgePlugin(
  on: Cypress.PluginEvents,
  pluginConfig: Cypress.PluginConfigOptions
): void {
  // Initialize on plugin load
  initializeCrossBridge().then(() => {
    console.log('CrossBridge plugin initialized');
  });
  
  // Listen to Cypress events
  on('before:run', async (details) => {
    await sendEvent('run_start', {
      specs: details.specs.map(s => s.relative),
      browser: details.browser.name,
      browser_version: details.browser.version
    });
  });
  
  on('after:run', async (results) => {
    await sendEvent('run_end', {
      total_duration_ms: results?.totalDuration,
      total_tests: results?.totalTests,
      total_passed: results?.totalPassed,
      total_failed: results?.totalFailed,
      total_pending: results?.totalPending,
      total_skipped: results?.totalSkipped
    });
  });
  
  on('before:spec', async (spec) => {
    await sendEvent('spec_start', {
      spec_name: spec.name,
      spec_relative: spec.relative,
      spec_absolute: spec.absolute
    });
  });
  
  on('after:spec', async (spec, results) => {
    await sendEvent('spec_end', {
      spec_name: spec.name,
      stats: results?.stats
    });
  });
  
  // Task for sending test events from browser context
  on('task', {
    'crossbridge:test:start': async (data) => {
      await sendEvent('test_start', data);
      return null;
    },
    'crossbridge:test:end': async (data) => {
      await sendEvent('test_end', data);
      return null;
    }
  });
}

// Export for use in support file
export const crossBridgeEvents = {
  testStart: (test: any) => {
    if (typeof cy !== 'undefined') {
      cy.task('crossbridge:test:start', {
        test_name: test.title,
        test_id: test.id,
        test_path: test.titlePath
      }, { log: false });
    }
  },
  testEnd: (test: any) => {
    if (typeof cy !== 'undefined') {
      cy.task('crossbridge:test:end', {
        test_name: test.title,
        test_id: test.id,
        status: test.state === 'passed' ? 'PASS' : 'FAIL',
        elapsed_time_ms: test.duration,
        error: test.err?.message
      }, { log: false });
    }
  }
};
