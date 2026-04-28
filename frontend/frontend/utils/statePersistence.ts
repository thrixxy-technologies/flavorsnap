// localStorage persistence and hydration utilities
import { storage } from '@/utils/storage';
import type { AppState, PersistedPayload } from '@/frontend/store/index';
import { validateState } from '@/frontend/store/index';

export const STORAGE_KEY = 'app_state_v1';
export const SCHEMA_VERSION = 1;

// Minimal debounce implementation (lodash not available as a dependency)
function debounce<T extends (...args: Parameters<T>) => void>(
  fn: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timer !== null) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      fn(...args);
    }, wait);
  };
}

// Internal (non-debounced) write — exported for testing
export function _persistStateImmediate(state: AppState): void {
  try {
    const payload: PersistedPayload = {
      version: SCHEMA_VERSION,
      state,
      savedAt: Date.now(),
    };
    storage.set(STORAGE_KEY, payload);
  } catch (error) {
    console.warn('statePersistence: failed to persist state', error);
  }
}

// Serialize and persist state — debounced at 300ms
export const persistState: (state: AppState) => void = debounce(
  _persistStateImmediate,
  300
);

// Load and validate state from localStorage; returns null on failure
export function hydrateState(): Partial<AppState> | null {
  try {
    const payload = storage.get<PersistedPayload | null>(STORAGE_KEY, null);

    if (payload === null || typeof payload !== 'object') {
      return null;
    }

    // Version check
    if (payload.version !== SCHEMA_VERSION) {
      return null;
    }

    // Schema validation
    const errors = validateState(payload.state);
    if (errors.length > 0) {
      return null;
    }

    return payload.state;
  } catch (error) {
    console.warn('statePersistence: failed to hydrate state', error);
    return null;
  }
}

// Clear persisted state
export function clearPersistedState(): void {
  storage.remove(STORAGE_KEY);
}
