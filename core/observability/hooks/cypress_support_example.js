"""
CrossBridge Cypress Support File (Optional)

Add to cypress/support/e2e.js for automatic test tracking:

import 'crossbridge-cypress/support';

This provides automatic test start/end events without any changes to test code.
"""

// cypress/support/e2e.js
// This file runs before every spec file

// Automatically track test lifecycle
beforeEach(function() {
  // Emit test start event
  const test = {
    title: Cypress.currentTest.title,
    titlePath: Cypress.currentTest.titlePath,
    parent: {
      title: this.test?.parent?.title
    },
    invocationDetails: {
      relativeFile: Cypress.spec.relative
    },
    file: Cypress.spec.absolute
  };
  
  cy.task('crossbridge:testStart', test, { log: false }).then(() => {
    // Test tracking started
  });
});

afterEach(function() {
  // Emit test end event
  const test = {
    title: Cypress.currentTest.title,
    titlePath: Cypress.currentTest.titlePath,
    parent: {
      title: this.test?.parent?.title
    },
    invocationDetails: {
      relativeFile: Cypress.spec.relative
    },
    file: Cypress.spec.absolute,
    err: this.test?.err
  };
  
  const state = this.test?.state || 'passed'; // 'passed', 'failed', 'pending'
  
  cy.task('crossbridge:testEnd', { test, state }, { log: false }).then(() => {
    // Test tracking completed
  });
});
