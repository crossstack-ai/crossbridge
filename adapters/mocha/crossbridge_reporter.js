/**
 * CrossBridge Mocha Reporter
 * Universal sidecar adapter for Mocha test monitoring.
 * 
 * Usage:
 *   mocha --reporter crossbridge_reporter.js tests/
 */

const http = require('http');
const Mocha = require('mocha');

const {
  EVENT_RUN_BEGIN,
  EVENT_RUN_END,
  EVENT_TEST_BEGIN,
  EVENT_TEST_PASS,
  EVENT_TEST_FAIL,
} = Mocha.Runner.constants;

class CrossBridgeReporter {
  constructor(runner, options) {
    this._runner = runner;
    this._options = options;
    this.enabled = process.env.CROSSBRIDGE_ENABLED === 'true';
    this.apiHost = process.env.CROSSBRIDGE_SIDECAR_HOST || process.env.CROSSBRIDGE_API_HOST || 'localhost';
    this.apiPort = process.env.CROSSBRIDGE_SIDECAR_PORT || process.env.CROSSBRIDGE_API_PORT || '8765';
    this.sessionStartTime = null;
    this.stats = {
      passes: 0,
      failures: 0,
      tests: 0
    };
    
    if (this.enabled) {
      this._checkConnection();
    }
    
    runner
      .on(EVENT_RUN_BEGIN, () => this.onRunBegin())
      .on(EVENT_TEST_BEGIN, (test) => this.onTestBegin(test))
      .on(EVENT_TEST_PASS, (test) => this.onTestPass(test))
      .on(EVENT_TEST_FAIL, (test, err) => this.onTestFail(test, err))
      .on(EVENT_RUN_END, () => this.onRunEnd());
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
        console.log(`✅ CrossBridge mocha reporter connected to ${this.apiHost}:${this.apiPort}`);
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
      framework: 'mocha',
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
  
  onRunBegin() {
    this.sessionStartTime = Date.now();
    this._sendEvent('session_start', {
      total_tests: this._runner.total
    });
  }
  
  onTestBegin(test) {
    this._sendEvent('test_start', {
      test_name: test.fullTitle(),
      test_id: test.file + '::' + test.fullTitle(),
    });
  }
  
  onTestPass(test) {
    this.stats.passes++;
    this.stats.tests++;
    this._sendEvent('test_end', {
      test_name: test.fullTitle(),
      test_id: test.file + '::' + test.fullTitle(),
      status: 'PASS',
      message: '',
      elapsed_time: test.duration / 1000.0,
    });
  }
  
  onTestFail(test, err) {
    this.stats.failures++;
    this.stats.tests++;
    this._sendEvent('test_end', {
      test_name: test.fullTitle(),
      test_id: test.file + '::' + test.fullTitle(),
      status: 'FAIL',
      message: err.message || '',
      elapsed_time: test.duration / 1000.0,
    });
  }
  
  onRunEnd() {
    const elapsed = (Date.now() - this.sessionStartTime) / 1000.0;
    this._sendEvent('session_finish', {
      num_total_tests: this.stats.tests,
      num_passed_tests: this.stats.passes,
      num_failed_tests: this.stats.failures,
      elapsed_time: elapsed,
    });
  }
}

module.exports = CrossBridgeReporter;
