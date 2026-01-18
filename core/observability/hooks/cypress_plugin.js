/**
 * CrossBridge Cypress Plugin
 * 
 * Works with existing Cypress tests WITHOUT migration
 * 
 * Design Contract:
 * - Pure observer (sidecar)
 * - Zero changes to existing tests
 * - Tests run normally if CrossBridge unavailable
 * 
 * Installation:
 * 1. npm install crossbridge-cypress
 * 2. Add to cypress.config.js:
 *    const crossbridge = require('crossbridge-cypress');
 * 
 *    module.exports = defineConfig({
 *      e2e: {
 *        setupNodeEvents(on, config) {
 *          crossbridge.register(on, {
 *            enabled: true,
 *            dbHost: '10.55.12.99',
 *            applicationVersion: 'v2.0.0'
 *          });
 *        }
 *      }
 *    });
 */

const { Client } = require('pg');

class CrossBridgeCypressObserver {
  constructor(config = {}) {
    this.enabled = config.enabled !== false;
    this.testStartTimes = new Map();
    
    if (!this.enabled) {
      console.log('[CrossBridge] Disabled - tests run normally');
      return;
    }
    
    // Database configuration
    this.dbConfig = {
      host: config.dbHost || process.env.CROSSBRIDGE_DB_HOST || '10.55.12.99',
      port: parseInt(config.dbPort || process.env.CROSSBRIDGE_DB_PORT || '5432'),
      database: config.dbName || process.env.CROSSBRIDGE_DB_NAME || 'udp-native-webservices-automation',
      user: config.dbUser || process.env.CROSSBRIDGE_DB_USER || 'postgres',
      password: config.dbPassword || process.env.CROSSBRIDGE_DB_PASSWORD || 'admin'
    };
    
    // Application metadata
    this.applicationVersion = config.applicationVersion || process.env.CROSSBRIDGE_APPLICATION_VERSION || 'unknown';
    this.productName = config.productName || process.env.CROSSBRIDGE_PRODUCT_NAME || 'CypressApp';
    this.environment = config.environment || process.env.CROSSBRIDGE_ENVIRONMENT || 'test';
    
    // Initialize database connection
    this.dbClient = null;
    this.initializeDatabase();
  }
  
  async initializeDatabase() {
    try {
      this.dbClient = new Client(this.dbConfig);
      await this.dbClient.connect();
      console.log('[CrossBridge] Observer connected - monitoring test execution');
    } catch (error) {
      console.error('[CrossBridge] Database connection failed - tests continue normally:', error.message);
      this.enabled = false;
    }
  }
  
  async emitTestStart(test) {
    if (!this.enabled || !this.dbClient) return;
    
    try {
      const testId = this.getTestId(test);
      const testName = test.title;
      const filePath = test.invocationDetails?.relativeFile || test.file || 'unknown';
      
      this.testStartTimes.set(testId, Date.now());
      
      // Extract metadata from test
      const metadata = {
        suite: test.parent?.title,
        tags: test.tags || [],
        browser: test.browser || 'electron'
      };
      
      const query = `
        INSERT INTO test_execution_event 
        (test_id, test_name, framework, file_path, status, 
         application_version, product_name, environment, event_type, event_timestamp, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
      `;
      
      await this.dbClient.query(query, [
        testId,
        testName,
        'cypress',
        filePath,
        'running',
        this.applicationVersion,
        this.productName,
        this.environment,
        'test_start',
        new Date(),
        JSON.stringify(metadata)
      ]);
      
    } catch (error) {
      // Never fail the test
      console.error('[CrossBridge] Event emission failed (non-blocking):', error.message);
    }
  }
  
  async emitTestEnd(test, state) {
    if (!this.enabled || !this.dbClient) return;
    
    try {
      const testId = this.getTestId(test);
      const testName = test.title;
      const filePath = test.invocationDetails?.relativeFile || test.file || 'unknown';
      
      const startTime = this.testStartTimes.get(testId) || Date.now();
      const durationMs = Date.now() - startTime;
      const durationSeconds = durationMs / 1000;
      
      // Map Cypress state to CrossBridge status
      let status = 'passed';
      let errorMessage = null;
      let stackTrace = null;
      
      if (state === 'failed') {
        status = 'failed';
        errorMessage = test.err?.message || 'Test failed';
        stackTrace = test.err?.stack || '';
      } else if (state === 'pending' || state === 'skipped') {
        status = 'skipped';
      }
      
      const query = `
        INSERT INTO test_execution_event 
        (test_id, test_name, framework, file_path, status, duration_seconds,
         error_message, stack_trace,
         application_version, product_name, environment, event_type, event_timestamp)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
      `;
      
      await this.dbClient.query(query, [
        testId,
        testName,
        'cypress',
        filePath,
        status,
        durationSeconds,
        errorMessage,
        stackTrace,
        this.applicationVersion,
        this.productName,
        this.environment,
        'test_end',
        new Date()
      ]);
      
      // Cleanup
      this.testStartTimes.delete(testId);
      
    } catch (error) {
      // Never fail the test
      console.error('[CrossBridge] Event emission failed (non-blocking):', error.message);
    }
  }
  
  getTestId(test) {
    // Generate unique test ID from suite hierarchy
    const parts = [];
    let current = test.parent;
    while (current) {
      if (current.title) {
        parts.unshift(current.title);
      }
      current = current.parent;
    }
    parts.push(test.title);
    return parts.join('.');
  }
  
  async disconnect() {
    if (this.dbClient) {
      try {
        await this.dbClient.end();
        console.log('[CrossBridge] Observer disconnected');
      } catch (error) {
        // Ignore
      }
    }
  }
}

/**
 * Register CrossBridge observer with Cypress
 * 
 * @param {*} on - Cypress plugin events
 * @param {*} config - CrossBridge configuration
 */
function register(on, config = {}) {
  const observer = new CrossBridgeCypressObserver(config);
  
  // Hook into Cypress events
  on('before:run', async (details) => {
    // Suite started - ensure database connection
    if (observer.enabled && !observer.dbClient) {
      await observer.initializeDatabase();
    }
  });
  
  on('after:run', async (results) => {
    // Suite finished - cleanup
    await observer.disconnect();
  });
  
  on('before:spec', async (spec) => {
    // Spec file started
  });
  
  on('after:spec', async (spec, results) => {
    // Spec file finished - process all tests
    if (results && results.tests) {
      for (const test of results.tests) {
        // Cypress provides test state in results
        const state = test.state; // 'passed', 'failed', 'pending'
        
        // We don't have before:test hook, so emit both start and end
        // Or we can rely on task() calls from support file
      }
    }
  });
  
  // Register tasks that can be called from test code
  on('task', {
    'crossbridge:testStart': async (test) => {
      await observer.emitTestStart(test);
      return null;
    },
    
    'crossbridge:testEnd': async ({ test, state }) => {
      await observer.emitTestEnd(test, state);
      return null;
    }
  });
  
  return observer;
}

module.exports = {
  CrossBridgeCypressObserver,
  register
};
