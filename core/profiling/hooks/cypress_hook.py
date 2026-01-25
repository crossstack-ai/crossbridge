"""
"""
Cypress Plugin for Performance Profiling

Integrates with Cypress test runner to capture performance metrics.
"""

from typing import Dict, Any
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)

CYPRESS_PLUGIN_JS = """
// Save as: cypress/plugins/crossbridge-profiling.js
// Register in cypress.config.js

const axios = require('axios');

const CROSSBRIDGE_API = process.env.CROSSBRIDGE_API_URL || 'http://localhost:8080/profiling';
const RUN_ID = process.env.CROSSBRIDGE_RUN_ID || generateRunId();

function generateRunId() {
  return `run_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

async function sendEvent(event) {
  try {
    // Send to CrossBridge profiling API or write to file
    console.log('[CrossBridge Profiling]', event);
    
    // Optional: Send to remote endpoint
    if (process.env.CROSSBRIDGE_PROFILING_ENABLED === 'true') {
      await axios.post(CROSSBRIDGE_API, event, {
        timeout: 1000,
        validateStatus: () => true // Don't throw on any status
      });
    }
  } catch (error) {
    // Silent failure - profiling should never break tests
    console.debug('[CrossBridge Profiling] Failed to send event:', error.message);
  }
}

module.exports = (on, config) => {
  // Track test lifecycle
  on('before:run', async (details) => {
    await sendEvent({
      run_id: RUN_ID,
      event_type: 'run_start',
      framework: 'cypress',
      specs: details.specs.length,
      browser: details.browser.name,
      timestamp: Date.now()
    });
  });

  on('after:run', async (results) => {
    await sendEvent({
      run_id: RUN_ID,
      event_type: 'run_end',
      framework: 'cypress',
      total_tests: results.totalTests,
      passed: results.totalPassed,
      failed: results.totalFailed,
      duration_ms: results.totalDuration,
      timestamp: Date.now()
    });
  });

  on('before:spec', async (spec) => {
    await sendEvent({
      run_id: RUN_ID,
      event_type: 'spec_start',
      framework: 'cypress',
      spec: spec.relative,
      timestamp: Date.now()
    });
  });

  on('after:spec', async (spec, results) => {
    if (results && results.stats) {
      await sendEvent({
        run_id: RUN_ID,
        event_type: 'spec_end',
        framework: 'cypress',
        spec: spec.relative,
        tests: results.stats.tests,
        passed: results.stats.passes,
        failed: results.stats.failures,
        duration_ms: results.stats.duration,
        timestamp: Date.now()
      });
    }
  });

  // Register custom tasks for test-level tracking
  on('task', {
    'crossbridge:testStart': async ({ testId, testTitle }) => {
      await sendEvent({
        run_id: RUN_ID,
        test_id: testId,
        event_type: 'test_start',
        framework: 'cypress',
        title: testTitle,
        timestamp: Date.now()
      });
      return null;
    },

    'crossbridge:testEnd': async ({ testId, testTitle, duration, status, error }) => {
      await sendEvent({
        run_id: RUN_ID,
        test_id: testId,
        event_type: 'test_end',
        framework: 'cypress',
        title: testTitle,
        duration_ms: duration,
        status: status,
        error: error,
        timestamp: Date.now()
      });
      return null;
    },

    'crossbridge:httpCall': async ({ testId, endpoint, method, statusCode, duration }) => {
      await sendEvent({
        run_id: RUN_ID,
        test_id: testId,
        event_type: 'http_request',
        framework: 'cypress',
        endpoint: endpoint,
        method: method,
        status_code: statusCode,
        duration_ms: duration,
        timestamp: Date.now()
      });
      return null;
    }
  });

  return config;
};
"""

CYPRESS_SUPPORT_JS = """
// Save as: cypress/support/crossbridge-profiling.js
// Import in cypress/support/e2e.js: import './crossbridge-profiling'

let testStartTime;

beforeEach(function() {
  testStartTime = Date.now();
  
  const testId = `${Cypress.spec.name}::${this.currentTest.title}`;
  
  // Track test start
  cy.task('crossbridge:testStart', {
    testId: testId,
    testTitle: this.currentTest.title
  }, { log: false }).catch(() => {
    // Silent failure
  });
});

afterEach(function() {
  const duration = Date.now() - testStartTime;
  const testId = `${Cypress.spec.name}::${this.currentTest.title}`;
  
  const status = this.currentTest.state === 'passed' ? 'passed' : 'failed';
  const error = this.currentTest.err ? this.currentTest.err.message : null;
  
  // Track test end
  cy.task('crossbridge:testEnd', {
    testId: testId,
    testTitle: this.currentTest.title,
    duration: duration,
    status: status,
    error: error
  }, { log: false }).catch(() => {
    // Silent failure
  });
});

// Intercept HTTP requests to track performance
Cypress.on('window:before:load', (win) => {
  const originalFetch = win.fetch;
  
  win.fetch = function(...args) {
    const startTime = Date.now();
    const url = typeof args[0] === 'string' ? args[0] : args[0].url;
    const method = args[1]?.method || 'GET';
    
    return originalFetch.apply(this, args).then((response) => {
      const duration = Date.now() - startTime;
      
      // Track HTTP call (async, non-blocking)
      cy.task('crossbridge:httpCall', {
        testId: `${Cypress.spec.name}::${Cypress.currentTest?.title || 'unknown'}`,
        endpoint: url,
        method: method,
        statusCode: response.status,
        duration: duration
      }, { log: false }).catch(() => {});
      
      return response;
    });
  };
});
"""

# Python helper for writing events to PostgreSQL
logger = logging.getLogger(__name__)


def create_cypress_profiling_files(output_dir: str = "cypress") -> Dict[str, str]:
    """
    Create Cypress profiling integration files.
    
    Args:
        output_dir: Directory to write files to
    
    Returns:
        Dictionary mapping filenames to their content
    """
    return {
        "plugins/crossbridge-profiling.js": CYPRESS_PLUGIN_JS,
        "support/crossbridge-profiling.js": CYPRESS_SUPPORT_JS,
    }
