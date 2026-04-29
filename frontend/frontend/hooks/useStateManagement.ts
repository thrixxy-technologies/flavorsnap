// React hook for consuming state with selector support

import React from 'react';
import { StoreContext } from '@/frontend/store/index';
import type { AppState, AppAction } from '@/frontend/store/index';

// Generic selector hook — only re-renders when selected slice changes
export function useStateManagement<T>(
  selector: (state: AppState) => T,
  equalityFn: (a: T, b: T) => boolean = Object.is,
): T {
  const { state } = React.useContext(StoreContext);
  const selectedRef = React.useRef<T>(selector(state));
  const selected = selector(state);

  if (!equalityFn(selectedRef.current, selected)) {
    selectedRef.current = selected;
  }

  return selectedRef.current;
}

// Dispatch hook
export function useDispatch(): React.Dispatch<AppAction> {
  const { dispatch } = React.useContext(StoreContext);
  return dispatch;
}

// Undo/redo convenience hook
export function useUndoRedo(): {
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
} {
  const { dispatch, canUndo, canRedo } = React.useContext(StoreContext);

  const undo = React.useCallback(() => dispatch({ type: '@@UNDO' }), [dispatch]);
  const redo = React.useCallback(() => dispatch({ type: '@@REDO' }), [dispatch]);

  return { undo, redo, canUndo, canRedo };
}
