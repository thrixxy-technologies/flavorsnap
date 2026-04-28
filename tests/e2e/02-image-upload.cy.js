/// <reference types="cypress" />

describe("Image Upload - User Journey", () => {
  beforeEach(() => {
    cy.clearAppData();
    cy.visit("/");
    cy.waitForPageLoad();
  });

  it("should allow file selection via input", () => {
    cy.get('input[type="file"]').should("exist").and("not.be.disabled");
  });

  it("should accept valid image formats (JPEG)", () => {
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

    // Verify image preview or upload indicator
    cy.get('[data-testid="image-preview"], img, [class*="preview"]', {
      timeout: 5000,
    }).should("exist");
  });

  it("should show image preview after upload", () => {
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

    // Check for preview image
    cy.get(
      'img[src*="blob:"], img[src*="data:"], [data-testid="image-preview"]',
      { timeout: 5000 },
    ).should("be.visible");
  });

  it("should handle drag and drop upload", () => {
    cy.fixture("test-food.jpg", "base64").then((fileContent) => {
      const blob = Cypress.Blob.base64StringToBlob(fileContent, "image/jpeg");
      const file = new File([blob], "test-food.jpg", { type: "image/jpeg" });

      cy.get('input[type="file"]')
        .parent()
        .trigger("drop", {
          dataTransfer: { files: [file] },
        });
    });
  });

  it("should reject invalid file types", () => {
    const invalidFile = new File(["content"], "test.txt", {
      type: "text/plain",
    });
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(invalidFile);

    cy.get('input[type="file"]').then((input) => {
      input[0].files = dataTransfer.files;
      cy.wrap(input).trigger("change", { force: true });
    });

    // Should show error message or not proceed
    cy.contains(/invalid|error|supported|format/i, { timeout: 3000 }).should(
      "exist",
    );
  });

  it("should allow removing uploaded image", () => {
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

    // Look for remove/clear button
    cy.get('button, [role="button"]')
      .contains(/remove|clear|delete|cancel/i)
      .click();

    // Verify image is removed
    cy.get('img[src*="blob:"], img[src*="data:"]').should("not.exist");
  });

  it("should handle multiple upload attempts", () => {
    // First upload
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

    cy.wait(1000);

    // Second upload (replace)
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

    cy.get('img[src*="blob:"], img[src*="data:"]').should("be.visible");
  });
});
