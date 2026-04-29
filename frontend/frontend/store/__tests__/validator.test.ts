// Feature: advanced-state-management, Property 13: Validator rejects malformed state
// Validates: Requirements 7.4

import * as fc from 'fast-check';
import { validateState, DEFAULT_STATE } from '@/frontend/store/index';

// Arbitrary for values that are definitely not 'light' or 'dark'
const arbBadTheme = fc.oneof(
  fc.string().filter(s => s !== 'light' && s !== 'dark'),
  fc.integer(),
  fc.boolean(),
  fc.constant(null),
  fc.constant(undefined),
);

// Arbitrary for non-boolean values
const arbNonBoolean = fc.oneof(
  fc.string(),
  fc.integer(),
  fc.constant(null),
  fc.constant(undefined),
  fc.record({}),
);

// Arbitrary for non-number values
const arbNonNumber = fc.oneof(
  fc.string(),
  fc.boolean(),
  fc.constant(null),
  fc.constant(undefined),
);

// Arbitrary for non-object values (primitives, null, arrays)
const arbNonObject = fc.oneof(
  fc.string(),
  fc.integer(),
  fc.boolean(),
  fc.constant(null),
  fc.constant(undefined),
  fc.array(fc.anything()),
);

describe('validateState — Property 13: Validator rejects malformed state', () => {
  // Positive test: valid DEFAULT_STATE returns empty array
  it('returns empty array for valid DEFAULT_STATE', () => {
    expect(validateState(DEFAULT_STATE)).toHaveLength(0);
  });

  // null, undefined, primitives
  it('rejects null, undefined, and primitives', () => {
    fc.assert(
      fc.property(
        fc.oneof(
          fc.constant(null),
          fc.constant(undefined),
          fc.string(),
          fc.integer(),
          fc.boolean(),
          fc.array(fc.anything()),
        ),
        (malformed) => {
          return validateState(malformed).length > 0;
        },
      ),
      { numRuns: 100 },
    );
  });

  // Objects missing `version`
  it('rejects objects missing version', () => {
    fc.assert(
      fc.property(
        fc.record({
          ui: fc.constant({ theme: 'light' as const, sidebarOpen: false }),
          classification: fc.constant({ result: null, isLoading: false, error: null }),
          user: fc.constant({ preferences: { language: 'en', notifications: true } }),
        }),
        (malformed) => {
          return validateState(malformed).length > 0;
        },
      ),
      { numRuns: 100 },
    );
  });

  // Objects with `version` as non-number
  it('rejects objects with version as non-number', () => {
    fc.assert(
      fc.property(
        arbNonNumber,
        (badVersion) => {
          const malformed = {
            version: badVersion,
            ui: { theme: 'light', sidebarOpen: false },
            classification: { result: null, isLoading: false, error: null },
            user: { preferences: { language: 'en', notifications: true } },
          };
          return validateState(malformed).length > 0;
        },
      ),
      { numRuns: 100 },
    );
  });

  // Objects missing `ui`
  it('rejects objects missing ui', () => {
    fc.assert(
      fc.property(
        fc.record({
          version: fc.constant(1),
          classification: fc.constant({ result: null, isLoading: false, error: null }),
          user: fc.constant({ preferences: { language: 'en', notifications: true } }),
        }),
        (malformed) => {
          return validateState(malformed).length > 0;
        },
      ),
      { numRuns: 100 },
    );
  });

  // Objects with ui.theme not being 'light' or 'dark'
  it('rejects objects with ui.theme not being light or dark', () => {
    fc.assert(
      fc.property(
        arbBadTheme,
        (badTheme) => {
          const malformed = {
            version: 1,
            ui: { theme: badTheme, sidebarOpen: false },
            classification: { result: null, isLoading: false, error: null },
            user: { preferences: { language: 'en', notifications: true } },
          };
          return validateState(malformed).length > 0;
        },
      ),
      { numRuns: 100 },
    );
  });

  // Objects with ui.sidebarOpen not being boolean
  it('rejects objects with ui.sidebarOpen not being boolean', () => {
    fc.assert(
      fc.property(
        arbNonBoolean,
        (badSidebarOpen) => {
          const malformed = {
            version: 1,
            ui: { theme: 'light', sidebarOpen: badSidebarOpen },
            classification: { result: null, isLoading: false, error: null },
            user: { preferences: { language: 'en', notifications: true } },
          };
          return validateState(malformed).length > 0;
        },
      ),
      { numRuns: 100 },
    );
  });

  // Objects missing `classification`
  it('rejects objects missing classification', () => {
    fc.assert(
      fc.property(
        fc.record({
          version: fc.constant(1),
          ui: fc.constant({ theme: 'light' as const, sidebarOpen: false }),
          user: fc.constant({ preferences: { language: 'en', notifications: true } }),
        }),
        (malformed) => {
          return validateState(malformed).length > 0;
        },
      ),
      { numRuns: 100 },
    );
  });

  // Objects missing `user`
  it('rejects objects missing user', () => {
    fc.assert(
      fc.property(
        fc.record({
          version: fc.constant(1),
          ui: fc.constant({ theme: 'light' as const, sidebarOpen: false }),
          classification: fc.constant({ result: null, isLoading: false, error: null }),
        }),
        (malformed) => {
          return validateState(malformed).length > 0;
        },
      ),
      { numRuns: 100 },
    );
  });

  // Arbitrary objects with non-object ui field
  it('rejects objects with ui as a non-object', () => {
    fc.assert(
      fc.property(
        arbNonObject,
        (badUi) => {
          const malformed = {
            version: 1,
            ui: badUi,
            classification: { result: null, isLoading: false, error: null },
            user: { preferences: { language: 'en', notifications: true } },
          };
          return validateState(malformed).length > 0;
        },
      ),
      { numRuns: 100 },
    );
  });

  // Arbitrary objects with non-object classification field
  it('rejects objects with classification as a non-object', () => {
    fc.assert(
      fc.property(
        arbNonObject,
        (badClassification) => {
          const malformed = {
            version: 1,
            ui: { theme: 'light', sidebarOpen: false },
            classification: badClassification,
            user: { preferences: { language: 'en', notifications: true } },
          };
          return validateState(malformed).length > 0;
        },
      ),
      { numRuns: 100 },
    );
  });

  // Arbitrary objects with non-object user field
  it('rejects objects with user as a non-object', () => {
    fc.assert(
      fc.property(
        arbNonObject,
        (badUser) => {
          const malformed = {
            version: 1,
            ui: { theme: 'light', sidebarOpen: false },
            classification: { result: null, isLoading: false, error: null },
            user: badUser,
          };
          return validateState(malformed).length > 0;
        },
      ),
      { numRuns: 100 },
    );
  });
});
