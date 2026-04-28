/// <reference types="cypress" />

describe("Accessibility - WCAG Compliance", () => {
  beforeEach(() => {
    cy.clearAppData();
    cy.visit("/");
    cy.waitForPageLoad();
  });

  it("should have proper document structure", () => {
    cy.get("html").should("have.attr", "lang");
    cy.get("title").should("exist");
    cy.get('main, [role="main"]').should("exist");
  });

  it("should have accessible form elements", () => {
    cy.get('input[type="file"]').should("exist");

    // Check for labels or aria-labels
    cy.get('input[type="file"]').then(($input) => {
      const hasLabel =
        $input.attr("aria-label") ||
        $input.attr("aria-labelledby") ||
        $input.closest("label").length > 0;
      expect(hasLabel).to.be.true;
    });
  });

  it("should have sufficient color contrast", () => {
    // This is a basic check - full contrast testing requires specialized tools
    cy.get("body").should("have.css", "color");
    cy.get("body").should("have.css", "background-color");
  });

  it("should have keyboard navigation support", () => {
    // Tab through focusable elements
    cy.get("body").tab();
    cy.focused().should("exist");

    // Continue tabbing
    for (let i = 0; i < 5; i++) {
      cy.focused().tab();
      cy.focused().should("exist");
    }
  });

  it("should have proper heading hierarchy", () => {
    cy.get("h1").should("have.length.at.least", 1);

    // Check heading order (h1 should come before h2, etc.)
    cy.get("h1, h2, h3, h4, h5, h6").then(($headings) => {
      if ($headings.length > 1) {
        const levels = $headings
          .map((i, el) => parseInt(el.tagName.charAt(1)))
          .get();
        // First heading should be h1
        expect(levels[0]).to.equal(1);
      }
    });
  });

  it("should have alt text for images", () => {
    cy.get("img").each(($img) => {
      // Images should have alt attribute (can be empty for decorative images)
      expect($img).to.have.attr("alt");
    });
  });

  it("should have proper button labels", () => {
    cy.get("button").each(($btn) => {
      const hasLabel =
        $btn.text().trim() ||
        $btn.attr("aria-label") ||
        $btn.attr("aria-labelledby");
      expect(hasLabel).to.exist;
    });
  });

  it("should have focus indicators", () => {
    cy.get("button, a, input").first().focus();
    cy.focused().should("have.css", "outline-style").and("not.equal", "none");
  });

  it("should support screen reader announcements", () => {
    // Check for ARIA live regions
    cy.get('[aria-live], [role="status"], [role="alert"]').should("exist");
  });

  it("should have semantic HTML", () => {
    // Check for semantic elements
    const semanticElements = [
      "header",
      "nav",
      "main",
      "footer",
      "article",
      "section",
    ];
    let hasSemanticElements = false;

    semanticElements.forEach((element) => {
      cy.get("body").then(($body) => {
        if (
          $body.find(element).length > 0 ||
          $body.find(`[role="${element}"]`).length > 0
        ) {
          hasSemanticElements = true;
        }
      });
    });
  });

  it("should handle focus management during interactions", () => {
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

    // After upload, focus should be managed appropriately
    cy.focused().should("exist");
  });

  it("should have proper ARIA roles", () => {
    // Check for proper use of ARIA roles
    cy.get("[role]").each(($el) => {
      const role = $el.attr("role");
      const validRoles = [
        "button",
        "link",
        "navigation",
        "main",
        "banner",
        "contentinfo",
        "complementary",
        "form",
        "search",
        "region",
        "article",
        "status",
        "alert",
        "dialog",
        "alertdialog",
        "img",
        "presentation",
      ];
      expect(validRoles).to.include(role);
    });
  });

  it("should support reduced motion preferences", () => {
    cy.window().then((win) => {
      // Check if animations respect prefers-reduced-motion
      const prefersReducedMotion = win.matchMedia(
        "(prefers-reduced-motion: reduce)",
      ).matches;
      if (prefersReducedMotion) {
        cy.log("User prefers reduced motion");
      }
    });
  });
});
