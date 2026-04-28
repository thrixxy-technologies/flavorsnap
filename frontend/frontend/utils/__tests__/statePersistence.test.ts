// Feature: advanced-state-management
// Tests for statePersistence utilities: Properties 2, 3, 4, and edge cases

import * as fc from 'fast-check';
import {
  _persistStateImmediate,
  hydrateState,
  clearPersistedState,
  STORAGE_KEY,
  SCHEMA_VERSION,
} from '@/frontend/utils/statePersistence';
import { DEFAULT_STATE } from '@/frontend/store/index';
import type { AppState } from '@/frontend/store/index';

// ---------------------------------------------------------------------------
// Shared arbitrary for valid AppState objects
// ---------------------------------------------------------------------------
const arbAppState = fc.record({
  version: fc.constant(1),
  ui: fc.record({
    theme: fc.oneof(fc.constant('light' as const), fc.constant('dark' as const)),
    sidebarOpen: fc.boolean(),
  }),
  classification: fc.record({
    result: fc.constant(null),
    isLoading: fc.boolean(),
    error: fc.oneof(fc.constant(null), fc.string()),
  }),
  user: fc.record({
    preferences: fc.record({
      language: fc.string({ minLength: 1, maxLength: 10 }),
      notifications: fc.boolean(),
    }),
  }),
});

// ---------------------------------------------------------------------------
// Reset localStorage between every test
// ---------------------------------------------------------------------------
beforeEach(() => {
  localStorage.clear();
});

// ---------------------------------------------------------------------------
// Property 2: Persistence round-trip
// Validates: Requirements 2.3
// ---------------------------------------------------------------------------
describe('Property 2: Persistence round-trip', () => {
  // Feature: advanced-state-management, Property 2: Persistence round-trip
  it('serializing then deserializing produces a deeply equal state', () => {
    fc.assert(
      fc.property(arbAppState, (state: AppState) => {
        localStorage.clear();
        _persistStateImmediate(state);
        const hydrated = hydrateState();
        expect(hydrated).toEqual(state);
      }),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 3: Hydration merges persisted fields
// Validates: Requirements 2.1
// ---------------------------------------------------------------------------
describe('Property 3: Hydration merges persisted fields', () => {
  // Feature: advanced-state-management, Property 3: Hydration merges persisted fields
  it('every field present in the persisted payload equals the persisted value after merge', () => {
    fc.assert(
      fc.property(arbAppState, (state: AppState) => {
        localStorage.clear();
        _persistStateImmediate(state);
        const hydrated = hydrateState();

        // hydrateState must return a non-null result for valid states
        expect(hydrated).not.toBeNull();

        // Merge with DEFAULT_STATE (simulating what the store does on init)
        const merged: AppState = { ...DEFAULT_STATE, ...(hydrated as Partial<AppState>) };

        // Every top-level field from the persisted state must be preserved
        expect(merged.version).toEqual(state.version);
        expect(merged.ui).toEqual(state.ui);
        expect(merged.classification).toEqual(state.classification);
        expect(merged.user).toEqual(state.user);
      }),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 4: Version mismatch discards persisted state
// Validates: Requirements 2.6
// ---------------------------------------------------------------------------
describe('Property 4: Version mismatch discards persisted state', () => {
  // Feature: advanced-state-management, Property 4: Version mismatch discards persisted state
  it('returns null for any payload whose version !== SCHEMA_VERSION', () => {
    // Generate version numbers that are NOT equal to SCHEMA_VERSION
    const arbMismatchedVersion = fc.integer().filter((v) => v !== SCHEMA_VERSION);

    fc.assert(
      fc.property(arbAppState, arbMismatchedVersion, (state: AppState, badVersion: number) => {
        localStorage.clear();

        // Manually write a payload with the wrong version
        const payload = {
          version: badVersion,
          state,
          savedAt: Date.now(),
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));

        const result = hydrateState();
        expect(result).toBeNull();
      }),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Task 3.5: Unit tests for persistence edge cases
// ---------------------------------------------------------------------------
describe('Persistence edge cases', () => {
  // Requirement 2.4: localStorage unavailable — no crash, returns null
  describe('localStorage unavailable', () => {
    it('_persistStateImmediate does not throw when storage.set throws', () => {
      const storageModule = require('@/utils/storage');
      const originalSet = storageModule.storage.set;
      storageModule.storage.set = () => { throw new Error('localStorage unavailable'); };

      try {
        expect(() => _persistStateImmediate(DEFAULT_STATE)).not.toThrow();
      } finally {
        storageModule.storage.set = originalSet;
      }
    });

    it('hydrateState returns null when storage.get throws', () => {
      const storageModule = require('@/utils/storage');
      const originalGet = storageModule.storage.get;
      storageModule.storage.get = () => { throw new Error('localStorage unavailable'); };

      try {
        const result = hydrateState();
        expect(result).toBeNull();
      } finally {
        storageModule.storage.get = originalGet;
      }
    });
  });

  // Property 14 / Requirement 7.5: Invalid hydration payload uses default state
  it('hydrateState returns null for an invalid (schema-failing) payload', () => {
    // Write a payload that passes version check but fails schema validation
    const invalidPayload = {
      version: SCHEMA_VERSION,
      state: {
        version: 1,
        ui: { theme: 'invalid-theme', sidebarOpen: 'not-a-boolean' },
        // missing classification and user
      },
      savedAt: Date.now(),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(invalidPayload));

    const result = hydrateState();
    expect(result).toBeNull();
  });

  // Requirement 2.5: Versioned key is used
  it('persists state under the versioned key STORAGE_KEY', () => {
    _persistStateImmediate(DEFAULT_STATE);

    const raw = localStorage.getItem(STORAGE_KEY);
    expect(raw).not.toBeNull();

    const parsed = JSON.parse(raw!);
    expect(parsed).toHaveProperty('version', SCHEMA_VERSION);
    expect(parsed).toHaveProperty('state');
    expect(parsed).toHaveProperty('savedAt');
  });

  it('STORAGE_KEY contains a version suffix', () => {
    expect(STORAGE_KEY).toMatch(/v\d+/);
  });
});
