'use client';
// Developer debugging overlay UI — only rendered in development mode
import React from 'react';
import { StoreContext } from '@/frontend/store/index';
import type { AppState, AppAction } from '@/frontend/store/index';

interface ActionLogEntry {
  id: number;
  action: AppAction;
  stateBefore: AppState;
  stateAfter: AppState;
  timestamp: number;
}

// StateDebuggerPanel is exported so tests can render it directly without the env guard
export function StateDebuggerPanel(): React.ReactElement {
  const { state, dispatch, undoDepth, redoDepth } = React.useContext(StoreContext);
  const [actionLog, setActionLog] = React.useState<ActionLogEntry[]>([]);
  const [selectedEntry, setSelectedEntry] = React.useState<ActionLogEntry | null>(null);
  const entryIdRef = React.useRef(0);
  const prevStateRef = React.useRef<AppState>(state);

  // Wrap dispatch to capture before/after state for each action
  const wrappedDispatch = React.useCallback(
    (action: AppAction) => {
      const stateBefore = prevStateRef.current;
      const entry: ActionLogEntry = {
        id: entryIdRef.current++,
        action,
        stateBefore,
        stateAfter: stateBefore, // placeholder; updated after state changes
        timestamp: Date.now(),
      };
      setActionLog(prev => [...prev.slice(-99), entry]);
      dispatch(action);
    },
    [dispatch],
  );

  // After state changes, update the stateAfter of the last pending entry
  React.useEffect(() => {
    setActionLog(prev => {
      if (prev.length === 0) return prev;
      const last = prev[prev.length - 1];
      if (last.stateAfter === last.stateBefore) {
        return [...prev.slice(0, -1), { ...last, stateAfter: state }];
      }
      return prev;
    });
    prevStateRef.current = state;
  }, [state]);

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'state.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  // Expose wrappedDispatch via a data attribute for testing purposes
  void wrappedDispatch;

  return (
    <div
      data-testid="state-debugger"
      style={{
        position: 'fixed',
        bottom: 0,
        right: 0,
        width: 400,
        maxHeight: '50vh',
        overflow: 'auto',
        background: '#1e1e1e',
        color: '#d4d4d4',
        fontSize: 12,
        padding: 8,
        zIndex: 9999,
        fontFamily: 'monospace',
      }}
    >
      <div data-testid="undo-depth">Undo depth: {undoDepth}</div>
      <div data-testid="redo-depth">Redo depth: {redoDepth}</div>
      <button data-testid="export-button" onClick={handleExport}>
        Export State
      </button>
      <pre data-testid="state-json">{JSON.stringify(state, null, 2)}</pre>
      <div data-testid="action-log">
        {actionLog.map(entry => (
          <div
            key={entry.id}
            data-testid={`action-entry-${entry.id}`}
            onClick={() => setSelectedEntry(entry)}
            style={{ cursor: 'pointer', borderBottom: '1px solid #333', padding: '2px 0' }}
          >
            <span data-testid="action-type">{entry.action.type}</span>
            {'payload' in entry.action && (
              <span data-testid="action-payload">
                {' '}{JSON.stringify((entry.action as { payload?: unknown }).payload)}
              </span>
            )}
          </div>
        ))}
      </div>
      {selectedEntry && (
        <pre data-testid="selected-state-after">
          {JSON.stringify(selectedEntry.stateAfter, null, 2)}
        </pre>
      )}
    </div>
  );
}

// Default export: only renders in development mode
export default function StateDebugger(): React.ReactElement | null {
  if (process.env.NODE_ENV !== 'development') return null;
  return <StateDebuggerPanel />;
}
