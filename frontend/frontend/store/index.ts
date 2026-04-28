// Centralized store definition, reducer, context, and provider

import React from 'react';
import { hydrateState, persistState } from '@/frontend/utils/statePersistence';
import type { ClassificationResult as BaseClassificationResult } from '@/types';

// Re-export ClassificationResult from shared types for use throughout the store
export type { ClassificationResult } from '@/types';

// User preferences shape for the store's user slice
export interface UserPreferences {
  language: string;
  notifications: boolean;
}

// Slice interfaces
export interface UIState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
}

export interface ClassificationState {
  result: BaseClassificationResult | null;
  isLoading: boolean;
  error: string | null;
}

export interface UserState {
  preferences: UserPreferences;
}

// Root state shape
export interface AppState {
  version: number; // schema version, currently 1
  ui: UIState;
  classification: ClassificationState;
  user: UserState;
}

// Action discriminated union
export type AppAction =
  | { type: 'UI/SET_THEME'; payload: 'light' | 'dark' }
  | { type: 'UI/SET_SIDEBAR_OPEN'; payload: boolean }
  | { type: 'CLASSIFICATION/SET_RESULT'; payload: BaseClassificationResult }
  | { type: 'CLASSIFICATION/CLEAR' }
  | { type: 'USER/SET_PREFERENCES'; payload: Partial<UserPreferences> }
  | { type: '@@UNDO' }
  | { type: '@@REDO' }
  | { type: '@@HYDRATE'; payload: Partial<AppState> };

// History state for undo/redo (internal to StoreProvider, exported for testing)
export interface HistoryState {
  past: AppState[];    // undo stack, max 50 entries
  present: AppState;  // current state
  future: AppState[]; // redo stack
}

// Validation error emitted when a state transition fails schema validation
export interface ValidationError {
  field: string;
  message: string;
  received: unknown;
}

// Wrapper stored in localStorage
export interface PersistedPayload {
  version: number;
  state: AppState;
  savedAt: number;
}

// Context value exposed to consumers
export interface StoreContextValue {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
  canUndo: boolean;
  canRedo: boolean;
  undoDepth: number;
  redoDepth: number;
}

// Default state — used when no valid persisted state is available
export const DEFAULT_STATE: AppState = {
  version: 1,
  ui: {
    theme: 'light',
    sidebarOpen: false,
  },
  classification: {
    result: null,
    isLoading: false,
    error: null,
  },
  user: {
    preferences: {
      language: 'en',
      notifications: true,
    },
  },
};

// Validator — checks a state object against the AppState schema
export function validateState(state: unknown): ValidationError[] {
  const errors: ValidationError[] = [];

  // Must be a non-null, non-array object
  if (typeof state !== 'object' || state === null || Array.isArray(state)) {
    errors.push({ field: 'state', message: 'state must be a non-null object', received: state });
    return errors;
  }

  const s = state as Record<string, unknown>;

  // version: must be a number
  if (typeof s['version'] !== 'number') {
    errors.push({ field: 'version', message: 'version must be a number', received: s['version'] });
  }

  // ui: must be an object
  if (typeof s['ui'] !== 'object' || s['ui'] === null || Array.isArray(s['ui'])) {
    errors.push({ field: 'ui', message: 'ui must be a non-null object', received: s['ui'] });
  } else {
    const ui = s['ui'] as Record<string, unknown>;

    // ui.theme: must be 'light' or 'dark'
    if (ui['theme'] !== 'light' && ui['theme'] !== 'dark') {
      errors.push({ field: 'ui.theme', message: "ui.theme must be 'light' or 'dark'", received: ui['theme'] });
    }

    // ui.sidebarOpen: must be boolean
    if (typeof ui['sidebarOpen'] !== 'boolean') {
      errors.push({ field: 'ui.sidebarOpen', message: 'ui.sidebarOpen must be a boolean', received: ui['sidebarOpen'] });
    }
  }

  // classification: must be an object
  if (typeof s['classification'] !== 'object' || s['classification'] === null || Array.isArray(s['classification'])) {
    errors.push({ field: 'classification', message: 'classification must be a non-null object', received: s['classification'] });
  }

  // user: must be an object with preferences being an object
  if (typeof s['user'] !== 'object' || s['user'] === null || Array.isArray(s['user'])) {
    errors.push({ field: 'user', message: 'user must be a non-null object', received: s['user'] });
  } else {
    const user = s['user'] as Record<string, unknown>;

    if (typeof user['preferences'] !== 'object' || user['preferences'] === null || Array.isArray(user['preferences'])) {
      errors.push({ field: 'user.preferences', message: 'user.preferences must be a non-null object', received: user['preferences'] });
    }
  }

  return errors;
}

// Root reducer — pure function, handles all AppAction types
// Unknown/internal actions (@@UNDO, @@REDO, @@HYDRATE) are handled by HistoryManager, not here
export function rootReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'UI/SET_THEME':
      return { ...state, ui: { ...state.ui, theme: action.payload } };

    case 'UI/SET_SIDEBAR_OPEN':
      return { ...state, ui: { ...state.ui, sidebarOpen: action.payload } };

    case 'CLASSIFICATION/SET_RESULT':
      return { ...state, classification: { ...state.classification, result: action.payload } };

    case 'CLASSIFICATION/CLEAR':
      return { ...state, classification: { ...state.classification, result: null, error: null } };

    case 'USER/SET_PREFERENCES':
      return { ...state, user: { ...state.user, preferences: { ...state.user.preferences, ...action.payload } } };

    default:
      // @@UNDO, @@REDO, @@HYDRATE, and any unknown actions — return state unchanged
      return state;
  }
}

// HistoryManager — pure function for undo/redo logic
const MAX_HISTORY = 50;

export function createInitialHistory(state: AppState): HistoryState {
  return { past: [], present: state, future: [] };
}

export function historyReducer(history: HistoryState, action: AppAction): HistoryState {
  switch (action.type) {
    case '@@UNDO': {
      if (history.past.length === 0) return history; // no-op
      const previous = history.past[history.past.length - 1];
      const newPast = history.past.slice(0, -1);
      return { past: newPast, present: previous, future: [history.present, ...history.future] };
    }
    case '@@REDO': {
      if (history.future.length === 0) return history; // no-op
      const next = history.future[0];
      const newFuture = history.future.slice(1);
      return { past: [...history.past, history.present].slice(-MAX_HISTORY), present: next, future: newFuture };
    }
    case '@@HYDRATE': {
      const merged = { ...history.present, ...action.payload };
      return { ...history, present: merged };
    }
    default: {
      // undoable action — push present to past, compute new present, clear future
      const newPresent = rootReducer(history.present, action);
      const newPast = [...history.past, history.present].slice(-MAX_HISTORY);
      return { past: newPast, present: newPresent, future: [] };
    }
  }
}

// StoreContext — exported for advanced use (e.g. useContext in tests)
export const StoreContext = React.createContext<StoreContextValue>({
  state: DEFAULT_STATE,
  dispatch: () => {},
  canUndo: false,
  canRedo: false,
  undoDepth: 0,
  redoDepth: 0,
});

// StoreProvider props
export interface StoreProviderProps {
  children: React.ReactNode;
  onValidationError?: (errors: ValidationError[]) => void;
}

// StoreProvider — wraps the app with the centralized store
export function StoreProvider({ children, onValidationError }: StoreProviderProps): React.ReactElement {
  // Keep the latest callback in a ref so the dispatch closure never goes stale
  const onValidationErrorRef = React.useRef(onValidationError);
  onValidationErrorRef.current = onValidationError;

  const [history, baseDispatch] = React.useReducer(
    historyReducer,
    DEFAULT_STATE,
    createInitialHistory,
  );

  // Ref to hold the BroadcastChannel instance so it's accessible across effects
  const channelRef = React.useRef<BroadcastChannel | null>(null);

  // Ref to track the last state received via broadcast — used in the persist effect
  // to skip re-broadcasting that state
  const lastBroadcastStateRef = React.useRef<AppState | null>(null);

  // Wrapped dispatch: validate the next state before committing
  const dispatch = React.useCallback(
    (action: AppAction) => {
      const nextHistory = historyReducer(history, action);
      const errors = validateState(nextHistory.present);
      if (errors.length > 0) {
        onValidationErrorRef.current?.(errors);
        return; // reject — keep previous state
      }
      baseDispatch(action);
    },
    [history],
  );

  // Hydrate from localStorage on mount
  React.useEffect(() => {
    const persisted = hydrateState();
    if (persisted !== null) {
      baseDispatch({ type: '@@HYDRATE', payload: persisted });
    }
  }, []);

  // Cross-tab sync via BroadcastChannel (with storage event fallback)
  React.useEffect(() => {
    let storageHandler: ((e: StorageEvent) => void) | null = null;

    if (typeof BroadcastChannel !== 'undefined') {
      const channel = new BroadcastChannel('app_state_sync');
      channelRef.current = channel;

      channel.onmessage = (event) => {
        const incoming = event.data as Partial<AppState>;
        if (incoming && typeof incoming === 'object' && !Array.isArray(incoming)) {
          lastBroadcastStateRef.current = incoming as AppState;
          baseDispatch({ type: '@@HYDRATE', payload: incoming });
        }
      };
    } else {
      // Fallback: storage event for environments without BroadcastChannel
      storageHandler = (e: StorageEvent) => {
        if (e.key === 'app_state_v1' && e.newValue) {
          try {
            const payload = JSON.parse(e.newValue);
            if (payload?.state) {
              lastBroadcastStateRef.current = payload.state as AppState;
              baseDispatch({ type: '@@HYDRATE', payload: payload.state });
            }
          } catch {
            // silently discard malformed messages
          }
        }
      };
      window.addEventListener('storage', storageHandler);
    }

    return () => {
      channelRef.current?.close();
      channelRef.current = null;
      if (storageHandler) window.removeEventListener('storage', storageHandler);
    };
  }, []);

  // Persist on every state change and broadcast to other tabs (unless change came from broadcast)
  React.useEffect(() => {
    persistState(history.present);
    // Skip broadcasting if this state was received from another tab (prevent loops)
    const isReceivedBroadcast = lastBroadcastStateRef.current === history.present ||
      (lastBroadcastStateRef.current !== null &&
        JSON.stringify(lastBroadcastStateRef.current) === JSON.stringify(history.present));
    if (!isReceivedBroadcast && channelRef.current) {
      channelRef.current.postMessage(history.present);
    }
    // Clear the last broadcast state after we've checked it
    if (isReceivedBroadcast) {
      lastBroadcastStateRef.current = null;
    }
  }, [history.present]);

  const value: StoreContextValue = {
    state: history.present,
    dispatch,
    canUndo: history.past.length > 0,
    canRedo: history.future.length > 0,
    undoDepth: history.past.length,
    redoDepth: history.future.length,
  };

  return React.createElement(StoreContext.Provider, { value }, children);
}
