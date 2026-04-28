import * as fc from 'fast-check';
import { historyReducer, createInitialHistory, DEFAULT_STATE } from '@/frontend/store/index';
import type { AppState, AppAction, HistoryState } from '@/frontend/store/index';

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

// Only undoable actions (not @@UNDO, @@REDO, @@HYDRATE)
const arbUndoableAction: fc.Arbitrary<AppAction> = fc.oneof(
  fc.record({ type: fc.constant('UI/SET_THEME' as const), payload: fc.oneof(fc.constant('light' as const), fc.constant('dark' as const)) }),
  fc.record({ type: fc.constant('UI/SET_SIDEBAR_OPEN' as const), payload: fc.boolean() }),
  fc.record({ type: fc.constant('CLASSIFICATION/CLEAR' as const) }),
);

// Arbitrary for a HistoryState with at least one past entry
const arbHistoryWithPast: fc.Arbitrary<HistoryState> = fc.record({
  past: fc.array(arbAppState, { minLength: 1, maxLength: 10 }),
  present: arbAppState,
  future: fc.array(arbAppState, { minLength: 0, maxLength: 5 }),
});

// Arbitrary for a HistoryState with at least one future entry
const arbHistoryWithFuture: fc.Arbitrary<HistoryState> = fc.record({
  past: fc.array(arbAppState, { minLength: 0, maxLength: 5 }),
  present: arbAppState,
  future: fc.array(arbAppState, { minLength: 1, maxLength: 10 }),
});

// Feature: advanced-state-management, Property 5: Dispatch then undo is identity
describe('Property 5: Dispatch then undo is identity', () => {
  it('dispatching an undoable action then undoing returns the original state', () => {
    // Validates: Requirements 3.2
    fc.assert(
      fc.property(arbAppState, arbUndoableAction, (state, action) => {
        const initial = createInitialHistory(state);
        const afterDispatch = historyReducer(initial, action);
        const afterUndo = historyReducer(afterDispatch, { type: '@@UNDO' });
        expect(afterUndo.present).toEqual(state);
      }),
      { numRuns: 100 },
    );
  });
});

// Feature: advanced-state-management, Property 6: Undo then redo is identity
describe('Property 6: Undo then redo is identity', () => {
  it('undoing then redoing returns the state to what it was before undo', () => {
    // Validates: Requirements 3.3
    fc.assert(
      fc.property(arbHistoryWithPast, (history) => {
        const preUndoPresent = history.present;
        const afterUndo = historyReducer(history, { type: '@@UNDO' });
        const afterRedo = historyReducer(afterUndo, { type: '@@REDO' });
        expect(afterRedo.present).toEqual(preUndoPresent);
      }),
      { numRuns: 100 },
    );
  });
});

// Feature: advanced-state-management, Property 7: New action clears redo stack
describe('Property 7: New action clears redo stack', () => {
  it('dispatching an undoable action on a state with non-empty future clears the redo stack', () => {
    // Validates: Requirements 3.4
    fc.assert(
      fc.property(arbHistoryWithFuture, arbUndoableAction, (history, action) => {
        const afterDispatch = historyReducer(history, action);
        expect(afterDispatch.future).toHaveLength(0);
      }),
      { numRuns: 100 },
    );
  });
});

// Feature: advanced-state-management, Property 8: Undo stack bounded at 50
describe('Property 8: Undo stack bounded at 50', () => {
  it('dispatching more than 50 undoable actions never causes past to exceed 50 entries', () => {
    // Validates: Requirements 3.5
    fc.assert(
      fc.property(
        fc.array(arbUndoableAction, { minLength: 51, maxLength: 60 }),
        (actions) => {
          let history = createInitialHistory(DEFAULT_STATE);
          for (const action of actions) {
            history = historyReducer(history, action);
            expect(history.past.length).toBeLessThanOrEqual(50);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});

// Unit tests for undo/redo edge cases
describe('Undo/redo edge cases', () => {
  it('undo on empty stack is a no-op (Requirement 3.6)', () => {
    const initial = createInitialHistory(DEFAULT_STATE);
    expect(initial.past).toHaveLength(0);
    const afterUndo = historyReducer(initial, { type: '@@UNDO' });
    expect(afterUndo).toBe(initial); // same reference — no change
    expect(afterUndo.present).toEqual(DEFAULT_STATE);
  });

  it('redo on empty stack is a no-op (Requirement 3.7)', () => {
    const initial = createInitialHistory(DEFAULT_STATE);
    expect(initial.future).toHaveLength(0);
    const afterRedo = historyReducer(initial, { type: '@@REDO' });
    expect(afterRedo).toBe(initial); // same reference — no change
    expect(afterRedo.present).toEqual(DEFAULT_STATE);
  });
});
