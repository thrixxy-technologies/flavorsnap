/// <reference types="cypress" />

describe("Homepage - Landing and Navigation", () => {
  beforeEach(() => {
    cy.clearAppData();
    cy.visit("/");
    cy.waitForPageLoad();
  });

  it("should load the homepage successfully", () => {
    cy.url().should("eq", `${Cypress.config("baseUrl")}/`);
    cy.get("body").should("be.visible");
  });

  it("should display the main heading and branding", () => {
    cy.contains(/FlavorSnap|Food Classification/i).should("be.visible");
  });

  it("should show the file upload area", () => {
    cy.get('input[type="file"]').should("exist");
    cy.contains(/upload|drag|drop/i).should("be.visible");
  });

  it("should display navigation elements", () => {
    // Check for common navigation items
    cy.get("nav, header").should("exist");
  });

  it("should be responsive on mobile devices", () => {
    cy.checkResponsive("mobile");
    cy.get("body").should("be.visible");
    cy.get('input[type="file"]').should("exist");
  });

  it("should be responsive on tablet devices", () => {
    cy.checkResponsive("tablet");
    cy.get("body").should("be.visible");
    cy.get('input[type="file"]').should("exist");
  });

  it("should have proper meta tags for SEO", () => {
    cy.document().then((doc) => {
      expect(doc.querySelector("title")).to.exist;
      expect(doc.querySelector('meta[name="description"]')).to.exist;
    });
  });

  it("should not have console errors on load", () => {
    cy.window().then((win) => {
      cy.spy(win.console, "error");
    });
    cy.reload();
    cy.window().then((win) => {
      expect(win.console.error).to.have.callCount(0);
    });
  });
});
