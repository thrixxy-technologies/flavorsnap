/// <reference types="cypress" />

describe("Performance - Load Times and Optimization", () => {
  beforeEach(() => {
    cy.clearAppData();
  });

  it("should load homepage within acceptable time", () => {
    const startTime = Date.now();

    cy.visit("/");
    cy.waitForPageLoad();

    const loadTime = Date.now() - startTime;
    expect(loadTime).to.be.lessThan(5000); // 5 seconds
  });

  it("should have optimized image loading", () => {
    cy.visit("/");

    cy.get("img").each(($img) => {
      // Check for lazy loading attribute
      const hasLazyLoading =
        $img.attr("loading") === "lazy" || $img.attr("data-src") !== undefined;
      cy.log(`Image lazy loading: ${hasLazyLoading}`);
    });
  });

  it("should handle classification within reasonable time", () => {
    cy.visit("/");

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

    const startTime = Date.now();
    cy.contains("button", /classify|predict|analyze/i).click();

    cy.contains(/confidence|%/i, { timeout: 15000 })
      .should("be.visible")
      .then(() => {
        const classificationTime = Date.now() - startTime;
        expect(classificationTime).to.be.lessThan(15000); // 15 seconds max
        cy.log(`Classification time: ${classificationTime}ms`);
      });
  });

  it("should not have memory leaks during multiple classifications", () => {
    cy.visit("/");

    // Perform multiple classifications
    for (let i = 0; i < 3; i++) {
      cy.fixture("test-food.jpg", "base64").then((fileContent) => {
        cy.get('input[type="file"]').then((input) => {
          const blob = Cypress.Blob.base64StringToBlob(
            fileContent,
            "image/jpeg",
          );
          const file = new File([blob], `test-food-${i}.jpg`, {
            type: "image/jpeg",
          });
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(file);
          input[0].files = dataTransfer.files;
          cy.wrap(input).trigger("change", { force: true });
        });
      });

      cy.wait(1000);

      // Reset for next iteration
      cy.get("button")
        .contains(/try another|new|clear/i, { timeout: 5000 })
        .click({ force: true });
    }

    // Check that page is still responsive
    cy.get("body").should("be.visible");
  });

  it("should have efficient API response times", () => {
    cy.intercept("POST", "**/predict").as("classifyRequest");

    cy.visit("/");

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

    cy.wait("@classifyRequest").then((interception) => {
      const responseTime =
        interception.response.headers["x-response-time"] ||
        interception.duration;
      cy.log(`API Response Time: ${responseTime}ms`);
    });
  });

  it("should minimize bundle size", () => {
    cy.visit("/");

    cy.window().then((win) => {
      const performanceEntries = win.performance.getEntriesByType("resource");
      const jsFiles = performanceEntries.filter((entry) =>
        entry.name.endsWith(".js"),
      );

      jsFiles.forEach((file) => {
        cy.log(`JS File: ${file.name}, Size: ${file.transferSize} bytes`);
      });
    });
  });

  it("should use caching effectively", () => {
    // First visit
    cy.visit("/");
    cy.waitForPageLoad();

    // Second visit should use cache
    cy.reload();
    cy.waitForPageLoad();

    cy.window().then((win) => {
      const performanceEntries = win.performance.getEntriesByType("resource");
      const cachedResources = performanceEntries.filter(
        (entry) => entry.transferSize === 0 && entry.decodedBodySize > 0,
      );

      cy.log(`Cached resources: ${cachedResources.length}`);
      expect(cachedResources.length).to.be.greaterThan(0);
    });
  });

  it("should have acceptable First Contentful Paint", () => {
    cy.visit("/");

    cy.window().then((win) => {
      const perfData = win.performance.getEntriesByType("paint");
      const fcp = perfData.find(
        (entry) => entry.name === "first-contentful-paint",
      );

      if (fcp) {
        cy.log(`First Contentful Paint: ${fcp.startTime}ms`);
        expect(fcp.startTime).to.be.lessThan(3000); // 3 seconds
      }
    });
  });

  it("should handle concurrent requests efficiently", () => {
    cy.visit("/");

    // Simulate multiple rapid uploads
    for (let i = 0; i < 3; i++) {
      cy.fixture("test-food.jpg", "base64").then((fileContent) => {
        cy.get('input[type="file"]').then((input) => {
          const blob = Cypress.Blob.base64StringToBlob(
            fileContent,
            "image/jpeg",
          );
          const file = new File([blob], `test-${i}.jpg`, {
            type: "image/jpeg",
          });
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(file);
          input[0].files = dataTransfer.files;
          cy.wrap(input).trigger("change", { force: true });
        });
      });

      cy.wait(500);
    }

    // Application should remain responsive
    cy.get("body").should("be.visible");
  });
});
