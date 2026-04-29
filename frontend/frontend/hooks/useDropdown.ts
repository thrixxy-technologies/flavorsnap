// Hook for dropdown state management

import React from 'react';
import {
  DropdownOption,
  DropdownTheme,
  DEFAULT_DROPDOWN_THEME,
  filterOptions,
  toggleSelection,
  getNextFocusIndex,
  getVirtualItems,
} from '@/frontend/utils/dropdownUtils';

export interface UseDropdownOptions {
  options: DropdownOption[];
  multi?: boolean;
  defaultValue?: string[];
  value?: string[];
  onChange?: (value: string[]) => void;
  searchable?: boolean;
  virtualScroll?: boolean;
  itemHeight?: number;
  containerHeight?: number;
  theme?: DropdownTheme;
  closeOnSelect?: boolean;
}

export interface VirtualState {
  startIndex: number;
  endIndex: number;
  offsetY: number;
  totalHeight: number;
}

export interface UseDropdownReturn {
  // State
  isOpen: boolean;
  selected: string[];
  searchQuery: string;
  focusedIndex: number;
  filteredOptions: DropdownOption[];
  theme: DropdownTheme;
  virtualState: VirtualState;
  // Actions
  open: () => void;
  close: () => void;
  toggle: () => void;
  select: (value: string) => void;
  deselect: (value: string) => void;
  clearAll: () => void;
  setSearch: (query: string) => void;
  setFocusedIndex: (index: number) => void;
  onScroll: (scrollTop: number) => void;
  // Keyboard handler
  handleKeyDown: (e: React.KeyboardEvent) => void;
  // Refs
  triggerRef: React.RefObject<HTMLButtonElement | null>;
  listRef: React.RefObject<HTMLUListElement | null>;
  searchRef: React.RefObject<HTMLInputElement | null>;
}

export function useDropdown({
  options,
  multi = false,
  defaultValue = [],
  value,
  onChange,
  searchable = true,
  virtualScroll = false,
  itemHeight = 36,
  containerHeight = 240,
  theme = DEFAULT_DROPDOWN_THEME,
  closeOnSelect = !multi,
}: UseDropdownOptions): UseDropdownReturn {
  const isControlled = value !== undefined;
  const [internalSelected, setInternalSelected] = React.useState<string[]>(defaultValue);
  const selected = isControlled ? value! : internalSelected;

  const [isOpen, setIsOpen] = React.useState(false);
  const [searchQuery, setSearchQueryState] = React.useState('');
  const [focusedIndex, setFocusedIndex] = React.useState(-1);
  const [scrollTop, setScrollTop] = React.useState(0);

  const triggerRef = React.useRef<HTMLButtonElement>(null);
  const listRef = React.useRef<HTMLUListElement>(null);
  const searchRef = React.useRef<HTMLInputElement>(null);

  const filteredOptions = React.useMemo(
    () => (searchable ? filterOptions(options, searchQuery) : options),
    [options, searchQuery, searchable],
  );

  const virtualState = React.useMemo<VirtualState>(() => {
    if (!virtualScroll) {
      return { startIndex: 0, endIndex: filteredOptions.length - 1, offsetY: 0, totalHeight: filteredOptions.length * itemHeight };
    }
    const { startIndex, endIndex, offsetY } = getVirtualItems(
      filteredOptions.length,
      scrollTop,
      containerHeight,
      itemHeight,
    );
    return { startIndex, endIndex, offsetY, totalHeight: filteredOptions.length * itemHeight };
  }, [virtualScroll, filteredOptions.length, scrollTop, containerHeight, itemHeight]);

  // Close on outside click
  React.useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (!triggerRef.current?.closest('[data-dropdown]')?.contains(target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen]);

  // Focus search input when opened
  React.useEffect(() => {
    if (isOpen && searchable) {
      setTimeout(() => searchRef.current?.focus(), 0);
    }
    if (!isOpen) {
      setSearchQueryState('');
      setFocusedIndex(-1);
    }
  }, [isOpen, searchable]);

  const updateSelected = React.useCallback(
    (next: string[]) => {
      if (!isControlled) setInternalSelected(next);
      onChange?.(next);
    },
    [isControlled, onChange],
  );

  const open = React.useCallback(() => setIsOpen(true), []);
  const close = React.useCallback(() => {
    setIsOpen(false);
    triggerRef.current?.focus();
  }, []);
  const toggle = React.useCallback(() => setIsOpen((v) => !v), []);

  const select = React.useCallback(
    (val: string) => {
      const option = options.find((o) => o.value === val);
      if (option?.disabled) return;
      const next = multi ? toggleSelection(selected, val) : [val];
      updateSelected(next);
      if (closeOnSelect) close();
    },
    [options, multi, selected, updateSelected, closeOnSelect, close],
  );

  const deselect = React.useCallback(
    (val: string) => updateSelected(selected.filter((v) => v !== val)),
    [selected, updateSelected],
  );

  const clearAll = React.useCallback(() => updateSelected([]), [updateSelected]);

  const setSearch = React.useCallback((query: string) => {
    setSearchQueryState(query);
    setFocusedIndex(0);
  }, []);

  const onScroll = React.useCallback((top: number) => setScrollTop(top), []);

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          if (!isOpen) { open(); return; }
          setFocusedIndex((i) => getNextFocusIndex(filteredOptions, i, 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setFocusedIndex((i) => getNextFocusIndex(filteredOptions, i, -1));
          break;
        case 'Enter':
        case ' ':
          e.preventDefault();
          if (!isOpen) { open(); return; }
          if (focusedIndex >= 0 && filteredOptions[focusedIndex]) {
            select(filteredOptions[focusedIndex].value);
          }
          break;
        case 'Escape':
          e.preventDefault();
          close();
          break;
        case 'Tab':
          close();
          break;
        case 'Home':
          e.preventDefault();
          setFocusedIndex(getNextFocusIndex(filteredOptions, -1, 1));
          break;
        case 'End':
          e.preventDefault();
          setFocusedIndex(getNextFocusIndex(filteredOptions, filteredOptions.length, -1));
          break;
      }
    },
    [isOpen, open, close, select, focusedIndex, filteredOptions],
  );

  return {
    isOpen,
    selected,
    searchQuery,
    focusedIndex,
    filteredOptions,
    theme,
    virtualState,
    open,
    close,
    toggle,
    select,
    deselect,
    clearAll,
    setSearch,
    setFocusedIndex,
    onScroll,
    handleKeyDown,
    triggerRef,
    listRef,
    searchRef,
  };
}
