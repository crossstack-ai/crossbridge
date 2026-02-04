/**
 * CrossBridge Jest Reporter
 * Universal sidecar adapter for Jest test monitoring.
 * 
 * Usage:
 *   Add to jest.config.js:
 *   module.exports = {
 *     reporters: ['default', '<rootDir>/crossbridge_reporter.js']
 *   };
 */

const http = require('http');

class CrossBridgeReporter {
  constructor(globalConfig, options) {
    this.globalConfig = globalConfig;
    this.options = options;
    this.enabled = process.env.CROSSBRIDGE_ENABLED === 'true';
    this.apiHost = process.env.CROSSBRIDGE_SIDECAR_HOST || process.env.CROSSBRIDGE_API_HOST || 'localhost';
    this.apiPort = process.env.CROSSBRIDGE_SIDECAR_PORT || process.env.CROSSBRIDGE_API_PORT || '8765';
    this.sessionStartTime = null;
    
    if (this.enabled) {
      this._checkConnection();
    }
  }
  
  _checkConnection() {
    const options = {
      hostname: this.apiHost,
      port: this.apiPort,
      path: '/health',
      method: 'GET',
      timeout: 2000
    };
    
    const req = http.request(options, (res) => {
      if (res.statusCode === 200) {
        console.log(`✅ CrossBridge jest reporter connected to ${this.apiHost}:${this.apiPort}`);
      } else {
        this.enabled = false;
      }
    });
    
    req.on('error', () => {
      this.enabled = false;
    });
    
    req.end();
  }
  
  _sendEvent(eventType, data) {
    if (!this.enabled) {
      return;
    }
    
    const event = {
      event_type: eventType,
      framework: 'jest',
      data: data,
      timestamp: new Date().toISOString()
    };
    
    const postData = JSON.stringify(event);
    const options = {
      hostname: this.apiHost,
      port: this.apiPort,
      path: '/events',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      },
      timeout: 2000
    };
    
    const req = http.request(options);
    req.on('error', () => {});  // Silent fail
    req.write(postData);
    req.end();
  }
  
  onRunStart(results, options) {
    this.sessionStartTime = Date.now();
    this._sendEvent('session_start', {
      num_total_test_suites: results.numTotalTestSuites,
      num_total_tests: results.numTotalTests,
    });
  }
  
  onTestStart(test) {
    this._sendEvent('test_start', {
      test_name: test.path,
      test_id: test.path,
    });
  }
  
  onTestResult(test, testResult, results) {
    testResult.testResults.forEach((result) => {
      const status = result.status === 'passed' ? 'PASS' : 'FAIL';
      const message = result.failureMessages.join('\n');
      
      this._sendEvent('test_end', {
        test_name: result.fullName,
        test_id: `${test.path}::${result.fullName}`,
        status: status,
        message: message,
        elapsed_time: result.duration / 1000.0,
      });
    });
  }
  
  onRunComplete(contexts, results) {
    const elapsed = (Date.now() - this.sessionStartTime) / 1000.0;
    this._sendEvent('session_finish', {
      num_total_tests: results.numTotalTests,
      num_passed_tests: results.numPassedTests,
      num_failed_tests: results.numFailedTests,
      elapsed_time: elapsed,
    });
  }
}

module.exports = CrossBridgeReporter;
