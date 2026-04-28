// ***********************************************************
// This file is processed and loaded automatically before test files.
// You can change the location of this file or turn off automatically
// serving support files with the 'supportFile' configuration option.
// ***********************************************************

// Import commands.js using ES2015 syntax:
import "./commands";

// Alternatively you can use CommonJS syntax:
// require('./commands')

// Hide fetch/XHR logs for cleaner test output
const app = window.top;
if (!app.document.head.querySelector("[data-hide-command-log-request]")) {
  const style = app.document.createElement("style");
  style.innerHTML =
    ".command-name-request, .command-name-xhr { display: none }";
  style.setAttribute("data-hide-command-log-request", "");
  app.document.head.appendChild(style);
}

// Global before hook
before(() => {
  cy.log("Starting E2E Test Suite");
});

// Global after hook
after(() => {
  cy.log("E2E Test Suite Completed");
});

// Handle uncaught exceptions
Cypress.on("uncaught:exception", (err, runnable) => {
  // Returning false here prevents Cypress from failing the test
  // Only for specific known errors that don't affect test validity
  if (err.message.includes("ResizeObserver loop")) {
    return false;
  }
  return true;
});
