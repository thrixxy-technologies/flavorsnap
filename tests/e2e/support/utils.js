/**
 * Utility functions for E2E tests
 */

/**
 * Generate a random test image file
 * @param {string} name - File name
 * @param {number} width - Image width
 * @param {number} height - Image height
 * @returns {File} Generated image file
 */
export function generateTestImage(
  name = "test.jpg",
  width = 224,
  height = 224,
) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");

  // Draw a simple pattern
  ctx.fillStyle = "#FF6B6B";
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = "#4ECDC4";
  ctx.fillRect(width / 4, height / 4, width / 2, height / 2);

  return new Promise((resolve) => {
    canvas.toBlob((blob) => {
      resolve(new File([blob], name, { type: "image/jpeg" }));
    }, "image/jpeg");
  });
}

/**
 * Wait for element with custom timeout
 * @param {string} selector - CSS selector
 * @param {number} timeout - Timeout in milliseconds
 */
export function waitForElement(selector, timeout = 10000) {
  return cy.get(selector, { timeout }).should("exist");
}

/**
 * Check if API is available
 * @param {string} url - API URL
 * @returns {Promise<boolean>} API availability status
 */
export function checkApiAvailability(url) {
  return cy
    .request({
      method: "GET",
      url: `${url}/health`,
      failOnStatusCode: false,
    })
    .then((response) => {
      return response.status === 200;
    });
}

/**
 * Mock successful classification response
 * @param {string} label - Food label
 * @param {number} confidence - Confidence score (0-1)
 */
export function mockSuccessfulClassification(
  label = "Moi Moi",
  confidence = 0.91,
) {
  return {
    prediction: label,
    confidence: confidence,
    predictions: [
      { label: label, confidence: confidence },
      { label: "Akara", confidence: 0.06 },
      { label: "Bread", confidence: 0.03 },
    ],
    processing_time_ms: 18.247,
    filename: "test-food.jpg",
  };
}

/**
 * Get random food class
 * @returns {string} Random food class name
 */
export function getRandomFoodClass() {
  const classes = [
    "Akara",
    "Bread",
    "Egusi",
    "Moi Moi",
    "Rice and Stew",
    "Yam",
  ];
  return classes[Math.floor(Math.random() * classes.length)];
}

/**
 * Format confidence score for display
 * @param {number} confidence - Confidence score (0-1)
 * @returns {string} Formatted confidence string
 */
export function formatConfidence(confidence) {
  return `${(confidence * 100).toFixed(1)}%`;
}

/**
 * Simulate slow network
 * @param {number} delay - Delay in milliseconds
 */
export function simulateSlowNetwork(delay = 2000) {
  cy.intercept("**/*", (req) => {
    req.reply((res) => {
      res.delay = delay;
    });
  });
}

/**
 * Simulate network error
 */
export function simulateNetworkError() {
  cy.intercept("**/*", { forceNetworkError: true });
}

/**
 * Get viewport dimensions
 * @returns {Object} Viewport width and height
 */
export function getViewportDimensions() {
  return cy.window().then((win) => {
    return {
      width: win.innerWidth,
      height: win.innerHeight,
    };
  });
}

/**
 * Check if element is in viewport
 * @param {string} selector - CSS selector
 * @returns {boolean} Whether element is in viewport
 */
export function isInViewport(selector) {
  return cy.get(selector).then(($el) => {
    const rect = $el[0].getBoundingClientRect();
    return (
      rect.top >= 0 &&
      rect.left >= 0 &&
      rect.bottom <= Cypress.config("viewportHeight") &&
      rect.right <= Cypress.config("viewportWidth")
    );
  });
}

/**
 * Scroll element into view
 * @param {string} selector - CSS selector
 */
export function scrollIntoView(selector) {
  return cy.get(selector).scrollIntoView();
}

/**
 * Take screenshot with context
 * @param {string} name - Screenshot name
 * @param {Object} context - Additional context information
 */
export function screenshotWithContext(name, context = {}) {
  const timestamp = new Date().toISOString();
  const contextStr = Object.entries(context)
    .map(([key, value]) => `${key}:${value}`)
    .join("_");

  const filename = `${name}_${contextStr}_${timestamp}`;
  return cy.screenshot(filename);
}

/**
 * Wait for all images to load
 */
export function waitForImages() {
  return cy.get("img").each(($img) => {
    cy.wrap($img)
      .should("be.visible")
      .and(($img) => {
        expect($img[0].naturalWidth).to.be.greaterThan(0);
      });
  });
}

/**
 * Check for console errors
 * @returns {Array} Console errors
 */
export function getConsoleErrors() {
  const errors = [];
  cy.window().then((win) => {
    const originalError = win.console.error;
    win.console.error = (...args) => {
      errors.push(args);
      originalError.apply(win.console, args);
    };
  });
  return errors;
}

/**
 * Clear all app data (localStorage, sessionStorage, cookies)
 */
export function clearAllAppData() {
  cy.clearLocalStorage();
  cy.clearCookies();
  cy.window().then((win) => {
    win.sessionStorage.clear();
  });
}

/**
 * Set localStorage item
 * @param {string} key - Storage key
 * @param {*} value - Storage value
 */
export function setLocalStorage(key, value) {
  cy.window().then((win) => {
    win.localStorage.setItem(key, JSON.stringify(value));
  });
}

/**
 * Get localStorage item
 * @param {string} key - Storage key
 * @returns {*} Storage value
 */
export function getLocalStorage(key) {
  return cy.window().then((win) => {
    const value = win.localStorage.getItem(key);
    return value ? JSON.parse(value) : null;
  });
}

/**
 * Measure page load performance
 * @returns {Object} Performance metrics
 */
export function measurePageLoadPerformance() {
  return cy.window().then((win) => {
    const perfData = win.performance.timing;
    const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
    const connectTime = perfData.responseEnd - perfData.requestStart;
    const renderTime = perfData.domComplete - perfData.domLoading;

    return {
      pageLoadTime,
      connectTime,
      renderTime,
    };
  });
}

/**
 * Check accessibility violations (basic check)
 * @returns {Array} Accessibility issues
 */
export function checkBasicAccessibility() {
  const issues = [];

  // Check for images without alt text
  cy.get("img:not([alt])").then(($imgs) => {
    if ($imgs.length > 0) {
      issues.push(`${$imgs.length} images without alt text`);
    }
  });

  // Check for buttons without labels
  cy.get("button:not([aria-label]):not(:has(text))").then(($btns) => {
    if ($btns.length > 0) {
      issues.push(`${$btns.length} buttons without labels`);
    }
  });

  return issues;
}
