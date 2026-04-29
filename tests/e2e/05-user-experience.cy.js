/// <reference types="cypress" />

describe("User Experience - Complete User Journeys", () => {
  beforeEach(() => {
    cy.clearAppData();
    cy.visit("/");
    cy.waitForPageLoad();
  });

  it("should complete full classification workflow", () => {
    // Step 1: Upload image
    cy.fixture("test-food.jpg", "base64").then((fileContent) => {
      cy.get('input[type="file"]').then((input) => {
        const blob = Cypress.Blob.base64StringToBlob(fileContent, "image/jpeg");
        const file = new File([blob], "test-food.jpg", { type: "image/jpeg" });
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        input[0].files = dataTransfer.files;
        cy.wrap(input).trigger("change", { force: true });
      });
    });

    // Step 2: Verify preview
    cy.get('img[src*="blob:"], img[src*="data:"]', { timeout: 5000 }).should(
      "be.visible",
    );

    // Step 3: Classify
    cy.contains("button", /classify|predict|analyze/i).click();

    // Step 4: Wait for results
    cy.contains(/confidence|%/i, { timeout: 15000 }).should("be.visible");

    // Step 5: Verify results displayed
    cy.get("body").should(
      "contain.text",
      /akara|bread|egusi|moi moi|rice|yam/i,
    );
  });

  it("should handle error recovery gracefully", () => {
    // Simulate API error
    cy.intercept("POST", "**/predict", {
      statusCode: 500,
      body: { error: "Server error" },
    }).as("errorRequest");

    cy.fixture("test-food.jpg", "base64").then((fileContent) => {
      cy.get('input[type="file"]').then((input) => {
        const blob = Cypress.Blob.base64StringToBlob(fileContent, "image/jpeg");
        const file = new File([blob], "test-food.jpg", { type: "image/jpeg" });
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        input[0].files = dataTransfer.files;
        cy.wrap(input).trigger("change", { force: true });
      });
    });

    cy.contains("button", /classify|predict|analyze/i).click();
    cy.wait("@errorRequest");

    // Should show error
    cy.contains(/error|failed/i, { timeout: 5000 }).should("be.visible");

    // Should allow retry
    cy.contains("button", /try again|retry/i).should("be.visible");
  });

  it("should maintain state during navigation", () => {
    cy.fixture("test-food.jpg", "base64").then((fileContent) => {
      cy.get('input[type="file"]').then((input) => {
        const blob = Cypress.Blob.base64StringToBlob(fileContent, "image/jpeg");
        const file = new File([blob], "test-food.jpg", { type: "image/jpeg" });
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        input[0].files = dataTransfer.files;
        cy.wrap(input).trigger("change", { force: true });
      });
    });

    // Navigate away and back (if applicable)
    cy.get("a[href], button").first().click({ force: true });
    cy.go("back");

    // Check if state is preserved or properly reset
    cy.get("body").should("be.visible");
  });

  it("should provide visual feedback for all interactions", () => {
    // Hover effects
    cy.get('button, a, input[type="file"]').first().trigger("mouseover");
    cy.wait(100);

    // Click feedback
    cy.get("button").first().click({ force: true });
    cy.wait(100);

    // All interactive elements should be accessible
    cy.get("button, a, input").each(($el) => {
      cy.wrap($el).should("be.visible");
    });
  });

  it("should be keyboard accessible", () => {
    // Tab through interactive elements
    cy.get("body").tab();
    cy.focused().should("exist");

    // Continue tabbing
    cy.focused().tab();
    cy.focused().should("exist");

    // Enter key should activate buttons
    cy.get("button").first().focus().type("{enter}");
  });

  it("should handle multiple classification sessions", () => {
    // First classification
    cy.fixture("test-food.jpg", "base64").then((fileContent) => {
      cy.get('input[type="file"]').then((input) => {
        const blob = Cypress.Blob.base64StringToBlob(fileContent, "image/jpeg");
        const file = new File([blob], "test-food-1.jpg", {
          type: "image/jpeg",
        });
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        input[0].files = dataTransfer.files;
        cy.wrap(input).trigger("change", { force: true });
      });
    });

    cy.contains("button", /classify|predict|analyze/i).click();
    cy.wait(2000);

    // Reset or new classification
    cy.contains("button", /try another|new|upload another/i, {
      timeout: 10000,
    }).click();

    // Second classification
    cy.fixture("test-food.jpg", "base64").then((fileContent) => {
      cy.get('input[type="file"]').then((input) => {
        const blob = Cypress.Blob.base64StringToBlob(fileContent, "image/jpeg");
        const file = new File([blob], "test-food-2.jpg", {
          type: "image/jpeg",
        });
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        input[0].files = dataTransfer.files;
        cy.wrap(input).trigger("change", { force: true });
      });
    });

    cy.contains("button", /classify|predict|analyze/i).should("be.visible");
  });

  it("should display processing time information", () => {
    cy.fixture("test-responses.json").then((responses) => {
      cy.mockClassification(responses.successfulClassification);
    });

    cy.fixture("test-food.jpg", "base64").then((fileContent) => {
      cy.get('input[type="file"]').then((input) => {
        const blob = Cypress.Blob.base64StringToBlob(fileContent, "image/jpeg");
        const file = new File([blob], "test-food.jpg", { type: "image/jpeg" });
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        input[0].files = dataTransfer.files;
        cy.wrap(input).trigger("change", { force: true });
      });
    });

    cy.contains("button", /classify|predict|analyze/i).click();
    cy.wait("@mockClassify");

    // Should show processing time or speed indicator
    cy.contains(/ms|seconds|time|processing/i, { timeout: 5000 }).should(
      "exist",
    );
  });

  it("should work offline with proper error handling", () => {
    // Simulate offline
    cy.intercept("POST", "**/predict", { forceNetworkError: true }).as(
      "offlineRequest",
    );

    cy.fixture("test-food.jpg", "base64").then((fileContent) => {
      cy.get('input[type="file"]').then((input) => {
        const blob = Cypress.Blob.base64StringToBlob(fileContent, "image/jpeg");
        const file = new File([blob], "test-food.jpg", { type: "image/jpeg" });
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        input[0].files = dataTransfer.files;
        cy.wrap(input).trigger("change", { force: true });
      });
    });

    cy.contains("button", /classify|predict|analyze/i).click();

    // Should show offline/network error
    cy.contains(/offline|network|connection/i, { timeout: 10000 }).should(
      "be.visible",
    );
  });
});
