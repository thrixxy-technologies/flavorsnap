// ***********************************************
// Custom commands for FlavorSnap E2E tests
// ***********************************************

/**
 * Upload a file to the image upload component
 * @param {string} fileName - Name of the file in fixtures folder
 * @param {string} mimeType - MIME type of the file
 */
Cypress.Commands.add("uploadFile", (fileName, mimeType = "image/jpeg") => {
  cy.fixture(fileName, "base64").then((fileContent) => {
    cy.get('input[type="file"]').attachFile({
      fileContent,
      fileName,
      mimeType,
      encoding: "base64",
    });
  });
});

/**
 * Wait for API response and verify status
 * @param {string} url - API endpoint URL pattern
 * @param {number} statusCode - Expected status code
 */
Cypress.Commands.add("waitForApiResponse", (url, statusCode = 200) => {
  cy.intercept("POST", url).as("apiRequest");
  cy.wait("@apiRequest").its("response.statusCode").should("eq", statusCode);
});

/**
 * Check if element is visible and contains text
 * @param {string} selector - CSS selector
 * @param {string} text - Expected text content
 */
Cypress.Commands.add(
  "shouldContainText",
  { prevSubject: true },
  (subject, text) => {
    cy.wrap(subject).should("be.visible").and("contain", text);
  },
);

/**
 * Verify classification result
 * @param {string} expectedLabel - Expected food label
 * @param {number} minConfidence - Minimum confidence threshold
 */
Cypress.Commands.add(
  "verifyClassification",
  (expectedLabel, minConfidence = 0) => {
    cy.get('[data-testid="prediction-label"]')
      .should("be.visible")
      .and("contain", expectedLabel);

    if (minConfidence > 0) {
      cy.get('[data-testid="confidence-score"]')
        .invoke("text")
        .then((text) => {
          const confidence = parseFloat(text.replace("%", ""));
          expect(confidence).to.be.at.least(minConfidence);
        });
    }
  },
);

/**
 * Check API health status
 */
Cypress.Commands.add("checkApiHealth", () => {
  cy.request({
    method: "GET",
    url: `${Cypress.env("apiUrl")}/health`,
    failOnStatusCode: false,
  }).then((response) => {
    expect(response.status).to.eq(200);
    expect(response.body).to.have.property("status");
  });
});

/**
 * Mock API classification response
 * @param {object} response - Mock response data
 */
Cypress.Commands.add("mockClassification", (response) => {
  cy.intercept("POST", "**/predict", {
    statusCode: 200,
    body: response,
  }).as("mockClassify");
});

/**
 * Clear all local storage and cookies
 */
Cypress.Commands.add("clearAppData", () => {
  cy.clearLocalStorage();
  cy.clearCookies();
});

/**
 * Wait for page to be fully loaded
 */
Cypress.Commands.add("waitForPageLoad", () => {
  cy.window().its("document.readyState").should("eq", "complete");
});

/**
 * Check responsive design at different viewports
 * @param {string} device - Device name (mobile, tablet, desktop)
 */
Cypress.Commands.add("checkResponsive", (device) => {
  const viewports = {
    mobile: [375, 667],
    tablet: [768, 1024],
    desktop: [1280, 720],
  };

  const [width, height] = viewports[device] || viewports.desktop;
  cy.viewport(width, height);
});

/**
 * Take a screenshot with timestamp
 * @param {string} name - Screenshot name
 */
Cypress.Commands.add("screenshotWithTimestamp", (name) => {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  cy.screenshot(`${name}-${timestamp}`);
});
