// Feature: advanced-state-management, Property 1: Reducer purity
// Validates: Requirements 1.2

import * as fc from 'fast-check';
import { rootReducer, DEFAULT_STATE } from '@/frontend/store/index';
import type { AppState, AppAction } from '@/frontend/store/index';

// Arbitraries

const arbAppState: fc.Arbitrary<AppState> = fc.record({
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

const arbAppAction: fc.Arbitrary<AppAction> = fc.oneof(
  fc.record({ type: fc.constant('UI/SET_THEME' as const), payload: fc.oneof(fc.constant('light' as const), fc.constant('dark' as const)) }),
  fc.record({ type: fc.constant('UI/SET_SIDEBAR_OPEN' as const), payload: fc.boolean() }),
  fc.record({ type: fc.constant('CLASSIFICATION/CLEAR' as const) }),
  fc.record({ type: fc.constant('@@UNDO' as const) }),
  fc.record({ type: fc.constant('@@REDO' as const) }),
);

// Property test

describe('rootReducer — Property 1: Reducer purity', () => {
  it('calling reducer twice with same inputs produces deeply equal outputs', () => {
    fc.assert(
      fc.property(arbAppState, arbAppAction, (state, action) => {
        const result1 = rootReducer(state, action as AppAction);
        const result2 = rootReducer(state, action as AppAction);
        expect(result1).toEqual(result2);
      }),
      { numRuns: 100 },
    );
  });
});

// Unit tests

describe('rootReducer — unit tests', () => {
  it('UI/SET_THEME updates theme', () => {
    const state: AppState = { ...DEFAULT_STATE, ui: { ...DEFAULT_STATE.ui, theme: 'light' } };
    const next = rootReducer(state, { type: 'UI/SET_THEME', payload: 'dark' });
    expect(next.ui.theme).toBe('dark');
    // other fields unchanged
    expect(next.ui.sidebarOpen).toBe(state.ui.sidebarOpen);
  });

  it('UI/SET_SIDEBAR_OPEN updates sidebarOpen', () => {
    const state: AppState = { ...DEFAULT_STATE, ui: { ...DEFAULT_STATE.ui, sidebarOpen: false } };
    const next = rootReducer(state, { type: 'UI/SET_SIDEBAR_OPEN', payload: true });
    expect(next.ui.sidebarOpen).toBe(true);
  });

  it('CLASSIFICATION/CLEAR clears result and error', () => {
    const state: AppState = {
      ...DEFAULT_STATE,
      classification: { result: null, isLoading: false, error: 'some error' },
    };
    const next = rootReducer(state, { type: 'CLASSIFICATION/CLEAR' });
    expect(next.classification.result).toBeNull();
    expect(next.classification.error).toBeNull();
  });

  it('@@UNDO returns same state reference (no-op in reducer)', () => {
    const next = rootReducer(DEFAULT_STATE, { type: '@@UNDO' });
    expect(next).toBe(DEFAULT_STATE);
  });
});
