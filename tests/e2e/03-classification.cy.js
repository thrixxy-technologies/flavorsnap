/// <reference types="cypress" />

describe("Food Classification - Core Functionality", () => {
  beforeEach(() => {
    cy.clearAppData();
    cy.visit("/");
    cy.waitForPageLoad();
  });

  it("should classify an uploaded image successfully", () => {
    // Mock successful classification
    cy.fixture("test-responses.json").then((responses) => {
      cy.mockClassification(responses.successfulClassification);
    });

    // Upload image
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

    // Click classify button
    cy.contains("button", /classify|predict|analyze/i).click();

    // Wait for classification
    cy.wait("@mockClassify");

    // Verify results are displayed
    cy.contains(/moi moi/i, { timeout: 10000 }).should("be.visible");
    cy.contains(/confidence|%/i).should("be.visible");
  });

  it("should display loading state during classification", () => {
    // Delay the response to see loading state
    cy.intercept("POST", "**/predict", (req) => {
      req.reply((res) => {
        res.delay = 2000;
        res.send({
          statusCode: 200,
          body: {
            prediction: "Moi Moi",
            confidence: 0.91,
          },
        });
      });
    }).as("slowClassify");

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

    // Check for loading indicator
    cy.get(
      '[data-testid="loading"], [class*="loading"], [class*="spinner"]',
    ).should("be.visible");

    cy.wait("@slowClassify");
  });

  it("should display top predictions with confidence scores", () => {
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

    // Check for multiple predictions
    cy.contains(/moi moi/i).should("be.visible");
    cy.contains(/akara/i).should("be.visible");
    cy.contains(/bread/i).should("be.visible");

    // Check for confidence percentages
    cy.contains(/91%|0\.91/i).should("be.visible");
  });

  it("should handle low confidence predictions", () => {
    cy.fixture("test-responses.json").then((responses) => {
      cy.mockClassification(responses.lowConfidenceClassification);
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

    // Should show warning or low confidence indicator
    cy.contains(/low confidence|uncertain|not sure/i, { timeout: 5000 }).should(
      "exist",
    );
  });

  it("should allow classifying another image after results", () => {
    cy.fixture("test-responses.json").then((responses) => {
      cy.mockClassification(responses.successfulClassification);
    });

    // First classification
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

    // Look for "Try Another" or similar button
    cy.contains(
      "button",
      /try another|new|upload another|classify another/i,
    ).click();

    // Should be able to upload again
    cy.get('input[type="file"]').should("exist");
  });

  it("should handle API errors gracefully", () => {
    cy.intercept("POST", "**/predict", {
      statusCode: 500,
      body: {
        error: "Internal server error",
        message: "Model inference failed",
      },
    }).as("errorClassify");

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
    cy.wait("@errorClassify");

    // Should display error message
    cy.contains(/error|failed|try again/i, { timeout: 5000 }).should(
      "be.visible",
    );
  });

  it("should handle network timeout", () => {
    cy.intercept("POST", "**/predict", (req) => {
      req.destroy();
    }).as("timeoutClassify");

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

    // Should show timeout or network error
    cy.contains(/network|timeout|connection/i, { timeout: 15000 }).should(
      "be.visible",
    );
  });
});
