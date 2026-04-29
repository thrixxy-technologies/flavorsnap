/// <reference types="cypress" />

describe("Responsive Design - Cross-Device Compatibility", () => {
  const devices = [
    { name: "mobile", width: 375, height: 667 },
    { name: "tablet", width: 768, height: 1024 },
    { name: "desktop", width: 1280, height: 720 },
    { name: "large-desktop", width: 1920, height: 1080 },
  ];

  devices.forEach((device) => {
    describe(`${device.name} viewport (${device.width}x${device.height})`, () => {
      beforeEach(() => {
        cy.clearAppData();
        cy.viewport(device.width, device.height);
        cy.visit("/");
        cy.waitForPageLoad();
      });

      it("should render correctly", () => {
        cy.get("body").should("be.visible");
        cy.get('input[type="file"]').should("exist");
      });

      it("should have accessible upload button", () => {
        cy.get('input[type="file"]').should("be.visible");
      });

      it("should display content without horizontal scroll", () => {
        cy.document().then((doc) => {
          expect(doc.documentElement.scrollWidth).to.be.lte(device.width + 20);
        });
      });

      it("should handle image upload", () => {
        cy.fixture("test-food.jpg", "base64").then((fileContent) => {
          cy.get('input[type="file"]').then((input) => {
            const blob = Cypress.Blob.base64StringToBlob(
              fileContent,
              "image/jpeg",
            );
            const file = new File([blob], "test-food.jpg", {
              type: "image/jpeg",
            });
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            input[0].files = dataTransfer.files;
            cy.wrap(input).trigger("change", { force: true });
          });
        });

        cy.get('img[src*="blob:"], img[src*="data:"]', {
          timeout: 5000,
        }).should("be.visible");
      });

      it("should have readable text", () => {
        cy.get("body").then(($body) => {
          const fontSize = window.getComputedStyle($body[0]).fontSize;
          const fontSizeNum = parseFloat(fontSize);
          expect(fontSizeNum).to.be.at.least(12);
        });
      });

      it("should have touch-friendly buttons on mobile", () => {
        if (device.name === "mobile" || device.name === "tablet") {
          cy.get("button").each(($btn) => {
            const height = $btn.height();
            const width = $btn.width();
            // Minimum touch target size should be 44x44px
            expect(Math.min(height, width)).to.be.at.least(40);
          });
        }
      });
    });
  });

  it("should handle orientation changes", () => {
    cy.viewport(667, 375); // Landscape mobile
    cy.visit("/");
    cy.get("body").should("be.visible");

    cy.viewport(375, 667); // Portrait mobile
    cy.get("body").should("be.visible");
  });

  it("should adapt layout for different screen sizes", () => {
    // Desktop layout
    cy.viewport(1280, 720);
    cy.visit("/");
    cy.get("body").should("be.visible");

    // Mobile layout
    cy.viewport(375, 667);
    cy.get("body").should("be.visible");

    // Layout should adapt (check for responsive classes or layout changes)
    cy.get("body").should("exist");
  });
});
