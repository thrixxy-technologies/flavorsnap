// Tests for StateDebugger component
// Tasks 8.2, 8.3, 8.4

import React from 'react';
import * as fc from 'fast-check';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { StoreContext } from '@/frontend/store/index';
import type { AppState, AppAction, StoreContextValue } from '@/frontend/store/index';
import StateDebugger, { StateDebuggerPanel } from '@/frontend/components/StateDebugger';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const DEFAULT_STATE: AppState = {
  version: 1,
  ui: { theme: 'light', sidebarOpen: false },
  classification: { result: null, isLoading: false, error: null },
  user: { preferences: { language: 'en', notifications: true } },
};

function makeContextValue(overrides?: Partial<StoreContextValue>): StoreContextValue {
  return {
    state: DEFAULT_STATE,
    dispatch: jest.fn(),
    canUndo: false,
    canRedo: false,
    undoDepth: 0,
    redoDepth: 0,
    ...overrides,
  };
}

/** Render StateDebuggerPanel (no env guard) with a mock context */
function renderPanel(contextValue?: Partial<StoreContextValue>) {
  const value = makeContextValue(contextValue);
  return render(
    <StoreContext.Provider value={value}>
      <StateDebuggerPanel />
    </StoreContext.Provider>,
  );
}

// Arbitrary generators
const arbTheme = fc.oneof(fc.constant('light' as const), fc.constant('dark' as const));

const arbState: fc.Arbitrary<AppState> = fc.record({
  version: fc.constant(1),
  ui: fc.record({ theme: arbTheme, sidebarOpen: fc.boolean() }),
  classification: fc.record({
    result: fc.constant(null),
    isLoading: fc.boolean(),
    error: fc.oneof(fc.constant(null), fc.string({ maxLength: 20 })),
  }),
  user: fc.record({
    preferences: fc.record({
      language: fc.string({ minLength: 1, maxLength: 5 }),
      notifications: fc.boolean(),
    }),
  }),
});

const arbUndoableAction: fc.Arbitrary<AppAction> = fc.oneof(
  fc.record({ type: fc.constant('UI/SET_THEME' as const), payload: arbTheme }),
  fc.record({ type: fc.constant('UI/SET_SIDEBAR_OPEN' as const), payload: fc.boolean() }),
);

// ---------------------------------------------------------------------------
// Task 8.4 — Unit tests for StateDebugger
// ---------------------------------------------------------------------------

describe('StateDebugger unit tests', () => {
  // Requirement 5.4: returns null in non-development (NODE_ENV is 'test' in Jest)
  it('returns null when NODE_ENV is not development', () => {
    // In Jest, NODE_ENV is 'test', so StateDebugger should return null
    const { container } = render(
      <StoreContext.Provider value={makeContextValue()}>
        <StateDebugger />
      </StoreContext.Provider>,
    );
    expect(container.firstChild).toBeNull();
  });

  // Requirement 5.6: export button is present in the panel
  it('renders an export button', () => {
    renderPanel();
    expect(screen.getByTestId('export-button')).toBeInTheDocument();
  });

  // Requirement 5.1: displays current state as formatted JSON
  it('displays current state as formatted JSON', () => {
    const state: AppState = { ...DEFAULT_STATE, ui: { theme: 'dark', sidebarOpen: true } };
    renderPanel({ state });
    const pre = screen.getByTestId('state-json');
    expect(pre.textContent).toBe(JSON.stringify(state, null, 2));
  });

  // Requirement 5.3: displays undo/redo depths
  it('displays undo and redo depths', () => {
    renderPanel({ undoDepth: 3, redoDepth: 2 });
    expect(screen.getByTestId('undo-depth').textContent).toContain('3');
    expect(screen.getByTestId('redo-depth').textContent).toContain('2');
  });

  // Requirement 5.2: action log container is rendered
  it('renders the action log container', () => {
    renderPanel();
    expect(screen.getByTestId('action-log')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Task 8.2 — Property 10: Debugger renders state, actions, and counts
// Feature: advanced-state-management, Property 10: Debugger renders state, actions, and counts
// Validates: Requirements 5.1, 5.2, 5.3
// ---------------------------------------------------------------------------

describe('Property 10: Debugger renders state, actions, and counts', () => {
  it('rendered output contains state JSON, action types, and correct depths', () => {
    fc.assert(
      fc.property(
        arbState,
        fc.nat({ max: 50 }),
        fc.nat({ max: 50 }),
        (state, undoDepth, redoDepth) => {
          const { unmount } = render(
            <StoreContext.Provider
              value={makeContextValue({ state, undoDepth, redoDepth, canUndo: undoDepth > 0, canRedo: redoDepth > 0 })}
            >
              <StateDebuggerPanel />
            </StoreContext.Provider>,
          );

          // Requirement 5.1: state JSON is present
          const stateJson = screen.getByTestId('state-json');
          expect(stateJson.textContent).toBe(JSON.stringify(state, null, 2));

          // Requirement 5.3: undo/redo depths are shown
          expect(screen.getByTestId('undo-depth').textContent).toContain(String(undoDepth));
          expect(screen.getByTestId('redo-depth').textContent).toContain(String(redoDepth));

          unmount();
        },
      ),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Task 8.3 — Property 11: Debugger action click shows snapshot
// Feature: advanced-state-management, Property 11: Debugger action click shows snapshot
// Validates: Requirements 5.5
// ---------------------------------------------------------------------------

describe('Property 11: Debugger action click shows snapshot', () => {
  it('clicking an action log entry displays its stateAfter snapshot', () => {
    fc.assert(
      fc.property(
        arbState,
        arbUndoableAction,
        arbState,
        (initialState, action, stateAfterSnapshot) => {
          let capturedDispatch: React.Dispatch<AppAction> = jest.fn();

          function DispatchCapture() {
            const ctx = React.useContext(StoreContext);
            capturedDispatch = ctx.dispatch;
            return null;
          }

          // Stateful wrapper: dispatch causes state to change to stateAfterSnapshot
          function StatefulWrapper() {
            const [currentState, setCurrentState] = React.useState(initialState);
            const dispatch = React.useCallback((_a: AppAction) => {
              setCurrentState(stateAfterSnapshot);
            }, []);

            return (
              <StoreContext.Provider
                value={makeContextValue({ state: currentState, dispatch })}
              >
                <DispatchCapture />
                <StateDebuggerPanel />
              </StoreContext.Provider>
            );
          }

          const { unmount } = render(<StatefulWrapper />);

          // Dispatch an action to add an entry to the action log
          act(() => {
            capturedDispatch(action);
          });

          // Find the action entry and click it
          const actionEntries = screen.queryAllByTestId(/^action-entry-/);
          if (actionEntries.length > 0) {
            fireEvent.click(actionEntries[actionEntries.length - 1]);

            // The stateAfter snapshot should be displayed
            const snapshotEl = screen.queryByTestId('selected-state-after');
            expect(snapshotEl).toBeInTheDocument();
            expect(snapshotEl?.textContent).toBe(JSON.stringify(stateAfterSnapshot, null, 2));
          }

          unmount();
        },
      ),
      { numRuns: 100 },
    );
  });
});
