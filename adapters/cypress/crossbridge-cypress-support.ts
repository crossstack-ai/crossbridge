/**
 * CrossBridge Cypress Support File
 * 
 * Add to cypress/support/e2e.ts:
 * import './crossbridge-cypress-support';
 */

// Hook into Cypress test lifecycle
beforeEach(function () {
  if (window.Cypress && this.currentTest) {
    cy.task('crossbridge:test:start', {
      test_name: this.currentTest.title,
      test_id: this.currentTest.id || this.currentTest.title,
      test_path: this.currentTest.titlePath()
    }, { log: false }).catch(() => {
      // Fail-open: ignore errors
    });
  }
});

afterEach(function () {
  if (window.Cypress && this.currentTest) {
    cy.task('crossbridge:test:end', {
      test_name: this.currentTest.title,
      test_id: this.currentTest.id || this.currentTest.title,
      status: this.currentTest.state === 'passed' ? 'PASS' : 'FAIL',
      elapsed_time_ms: this.currentTest.duration,
      error: this.currentTest.err?.message
    }, { log: false }).catch(() => {
      // Fail-open: ignore errors
    });
  }
});
