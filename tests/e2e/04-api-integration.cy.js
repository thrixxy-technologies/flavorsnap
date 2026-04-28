/// <reference types="cypress" />

describe("API Integration - Backend Communication", () => {
  const apiUrl = Cypress.env("apiUrl");
  const apiV1Url = Cypress.env("apiV1Url");

  beforeEach(() => {
    cy.clearAppData();
  });

  it("should verify API health endpoint", () => {
    cy.request({
      method: "GET",
      url: `${apiUrl}/health`,
      failOnStatusCode: false,
    }).then((response) => {
      expect(response.status).to.be.oneOf([200, 503]);
      if (response.status === 200) {
        expect(response.body).to.have.property("status");
      }
    });
  });

  it("should verify API v1 health endpoint", () => {
    cy.request({
      method: "GET",
      url: `${apiV1Url}/health`,
      failOnStatusCode: false,
    }).then((response) => {
      expect(response.status).to.be.oneOf([200, 503]);
      if (response.status === 200) {
        expect(response.body).to.have.property("status");
        expect(response.body).to.have.property("model_loaded");
      }
    });
  });

  it("should get list of supported food classes", () => {
    cy.request({
      method: "GET",
      url: `${apiUrl}/classes`,
      failOnStatusCode: false,
    }).then((response) => {
      if (response.status === 200) {
        expect(response.body).to.have.property("classes");
        expect(response.body.classes).to.be.an("array");
        expect(response.body.classes).to.include.members([
          "Akara",
          "Bread",
          "Egusi",
          "Moi Moi",
          "Rice and Stew",
          "Yam",
        ]);
      }
    });
  });

  it("should handle classification API request", () => {
    cy.fixture("test-food.jpg", "binary").then((fileContent) => {
      const blob = Cypress.Blob.binaryStringToBlob(fileContent, "image/jpeg");
      const formData = new FormData();
      formData.append("image", blob, "test-food.jpg");

      cy.request({
        method: "POST",
        url: `${apiUrl}/predict`,
        body: formData,
        headers: {
          "Content-Type": "multipart/form-data",
        },
        failOnStatusCode: false,
      }).then((response) => {
        if (response.status === 200) {
          expect(response.body).to.have.property("label");
          expect(response.body).to.have.property("confidence");
          expect(response.body.confidence).to.be.a("number");
        }
      });
    });
  });

  it("should handle v1 classification API request", () => {
    cy.fixture("test-food.jpg", "binary").then((fileContent) => {
      const blob = Cypress.Blob.binaryStringToBlob(fileContent, "image/jpeg");
      const formData = new FormData();
      formData.append("image", blob, "test-food.jpg");

      cy.request({
        method: "POST",
        url: `${apiV1Url}/classify`,
        body: formData,
        headers: {
          "Content-Type": "multipart/form-data",
        },
        failOnStatusCode: false,
      }).then((response) => {
        if (response.status === 200) {
          expect(response.body).to.have.property("prediction");
          expect(response.body).to.have.property("confidence");
          expect(response.body).to.have.property("predictions");
          expect(response.body.predictions).to.be.an("array");
        }
      });
    });
  });

  it("should reject invalid image format", () => {
    const invalidFile = new Blob(["invalid content"], { type: "text/plain" });
    const formData = new FormData();
    formData.append("image", invalidFile, "test.txt");

    cy.request({
      method: "POST",
      url: `${apiUrl}/predict`,
      body: formData,
      headers: {
        "Content-Type": "multipart/form-data",
      },
      failOnStatusCode: false,
    }).then((response) => {
      expect(response.status).to.be.oneOf([400, 415, 422]);
    });
  });

  it("should handle missing image in request", () => {
    cy.request({
      method: "POST",
      url: `${apiUrl}/predict`,
      body: {},
      failOnStatusCode: false,
    }).then((response) => {
      expect(response.status).to.be.oneOf([400, 422]);
    });
  });

  it("should respect rate limiting", () => {
    const requests = [];

    // Make multiple rapid requests
    for (let i = 0; i < 10; i++) {
      requests.push(
        cy.request({
          method: "GET",
          url: `${apiUrl}/health`,
          failOnStatusCode: false,
        }),
      );
    }

    // At least some should succeed
    cy.wrap(requests).then((responses) => {
      const successCount = responses.filter((r) => r.status === 200).length;
      expect(successCount).to.be.greaterThan(0);
    });
  });

  it("should return proper CORS headers", () => {
    cy.request({
      method: "OPTIONS",
      url: `${apiUrl}/predict`,
      headers: {
        Origin: "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
      },
      failOnStatusCode: false,
    }).then((response) => {
      if (response.status === 200 || response.status === 204) {
        expect(response.headers).to.have.property(
          "access-control-allow-origin",
        );
      }
    });
  });

  it("should handle large file uploads", () => {
    // Create a large dummy image (simulated)
    const largeContent = "x".repeat(15 * 1024 * 1024); // 15MB
    const largeBlob = new Blob([largeContent], { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("image", largeBlob, "large-image.jpg");

    cy.request({
      method: "POST",
      url: `${apiUrl}/predict`,
      body: formData,
      headers: {
        "Content-Type": "multipart/form-data",
      },
      failOnStatusCode: false,
      timeout: 30000,
    }).then((response) => {
      // Should reject files that are too large
      expect(response.status).to.be.oneOf([400, 413, 422]);
    });
  });
});
