// Flexible dropdown with search, multi-select, virtual scrolling, and keyboard navigation

import React from 'react';
import '@/frontend/styles/dropdown.css';
import {
  DropdownOption,
  DropdownTheme,
  DEFAULT_DROPDOWN_THEME,
  groupOptions,
  getSelectionLabel,
} from '@/frontend/utils/dropdownUtils';
import { useDropdown } from '@/frontend/hooks/useDropdown';

export interface DropdownProps {
  options: DropdownOption[];
  /** Controlled selected values */
  value?: string[];
  defaultValue?: string[];
  onChange?: (value: string[]) => void;
  placeholder?: string;
  multi?: boolean;
  searchable?: boolean;
  /** Enable virtual scrolling for large lists */
  virtualScroll?: boolean;
  itemHeight?: number;
  /** Max height of the dropdown list in px */
  maxHeight?: number;
  disabled?: boolean;
  /** Show group labels when options have a `group` field */
  grouped?: boolean;
  /** Close list after selecting an item (defaults to true for single, false for multi) */
  closeOnSelect?: boolean;
  theme?: DropdownTheme;
  /** Stretch to full width of parent */
  fullWidth?: boolean;
  /** Accessible label for the trigger */
  'aria-label'?: string;
  id?: string;
  className?: string;
}

export function DropdownSystem({
  options,
  value,
  defaultValue,
  onChange,
  placeholder = 'Select...',
  multi = false,
  searchable = true,
  virtualScroll = false,
  itemHeight = 36,
  maxHeight = 240,
  disabled = false,
  grouped = false,
  closeOnSelect,
  theme = DEFAULT_DROPDOWN_THEME,
  fullWidth = false,
  'aria-label': ariaLabel,
  id,
  className = '',
}: DropdownProps) {
  const listId = React.useId();
  const searchId = React.useId();

  const {
    isOpen,
    selected,
    searchQuery,
    focusedIndex,
    filteredOptions,
    virtualState,
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
  } = useDropdown({
    options,
    multi,
    defaultValue,
    value,
    onChange,
    searchable,
    virtualScroll,
    itemHeight,
    containerHeight: maxHeight,
    theme,
    closeOnSelect,
  });

  // Apply theme CSS vars inline
  const cssVars = {
    '--dd-primary': theme.primary,
    '--dd-bg': theme.background,
    '--dd-surface': theme.surface,
    '--dd-text': theme.text,
    '--dd-border': theme.border,
    '--dd-hover': theme.hover,
    '--dd-selected': theme.selected,
    '--dd-disabled': theme.disabled,
    '--dd-radius': theme.radius,
    '--dd-item-height': `${itemHeight}px`,
  } as React.CSSProperties;

  const triggerLabel = getSelectionLabel(selected, options, placeholder);
  const hasSelection = selected.length > 0;

  // Scroll focused item into view
  React.useEffect(() => {
    if (!isOpen || focusedIndex < 0) return;
    const list = listRef.current;
    if (!list) return;
    const item = list.querySelector<HTMLElement>(`[data-index="${focusedIndex}"]`);
    item?.scrollIntoView({ block: 'nearest' });
  }, [focusedIndex, isOpen, listRef]);

  const groupedMap = React.useMemo(
    () => (grouped ? groupOptions(filteredOptions) : null),
    [grouped, filteredOptions],
  );

  const renderOption = (option: DropdownOption, index: number) => {
    const isSelected = selected.includes(option.value);
    const isFocused = focusedIndex === index;

    return (
      <li
        key={option.value}
        role="option"
        aria-selected={isSelected}
        aria-disabled={option.disabled}
        data-index={index}
        className={[
          'dd-option',
          isSelected ? 'dd-option--selected' : '',
          isFocused ? 'dd-option--focused' : '',
          option.disabled ? 'dd-option--disabled' : '',
        ]
          .filter(Boolean)
          .join(' ')}
        tabIndex={-1}
        onMouseEnter={() => setFocusedIndex(index)}
        onClick={() => !option.disabled && select(option.value)}
      >
        {multi && (
          <span className="dd-option-check" aria-hidden="true">
            {isSelected && (
              <svg className="dd-option-check-icon" viewBox="0 0 10 10" fill="none">
                <path d="M1.5 5l2.5 2.5 4.5-4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </span>
        )}
        <span className="dd-option-label">{option.label}</span>
      </li>
    );
  };

  const renderList = () => {
    if (filteredOptions.length === 0) {
      return <div className="dd-empty">No options found</div>;
    }

    if (grouped && groupedMap) {
      let globalIndex = 0;
      return (
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          aria-multiselectable={multi}
          aria-label={ariaLabel ?? 'Options'}
          className="dd-list"
        >
          {Array.from(groupedMap.entries()).map(([group, items]) => (
            <React.Fragment key={group}>
              {group && (
                <li role="presentation" className="dd-group-label" aria-hidden="true">
                  {group}
                </li>
              )}
              {items.map((option) => {
                const idx = globalIndex++;
                return renderOption(option, idx);
              })}
            </React.Fragment>
          ))}
        </ul>
      );
    }

    if (virtualScroll) {
      const { startIndex, endIndex, offsetY, totalHeight } = virtualState;
      const visible = filteredOptions.slice(startIndex, endIndex + 1);
      return (
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          aria-multiselectable={multi}
          aria-label={ariaLabel ?? 'Options'}
          className="dd-list"
          style={{ height: totalHeight, position: 'relative' }}
        >
          <li
            aria-hidden="true"
            className="dd-virtual-spacer"
            style={{ height: offsetY }}
          />
          {visible.map((option, i) => renderOption(option, startIndex + i))}
        </ul>
      );
    }

    return (
      <ul
        ref={listRef}
        id={listId}
        role="listbox"
        aria-multiselectable={multi}
        aria-label={ariaLabel ?? 'Options'}
        className="dd-list"
      >
        {filteredOptions.map((option, i) => renderOption(option, i))}
      </ul>
    );
  };

  return (
    <div
      data-dropdown
      className={['dd-root', fullWidth ? 'dd-root--full' : '', className].filter(Boolean).join(' ')}
      style={cssVars}
      id={id}
    >
      {/* Trigger */}
      <button
        ref={triggerRef}
        type="button"
        className={['dd-trigger', isOpen ? 'dd-trigger--open' : ''].filter(Boolean).join(' ')}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={isOpen ? listId : undefined}
        aria-label={ariaLabel}
        aria-disabled={disabled}
        disabled={disabled}
        onClick={toggle}
        onKeyDown={handleKeyDown}
      >
        {multi && hasSelection ? (
          <span className="dd-tags" aria-hidden="true">
            {selected.map((val) => {
              const label = options.find((o) => o.value === val)?.label ?? val;
              return (
                <span key={val} className="dd-tag">
                  <span className="dd-tag-label">{label}</span>
                  <button
                    type="button"
                    className="dd-tag-remove"
                    aria-label={`Remove ${label}`}
                    tabIndex={-1}
                    onClick={(e) => {
                      e.stopPropagation();
                      deselect(val);
                    }}
                  >
                    ×
                  </button>
                </span>
              );
            })}
          </span>
        ) : (
          <span className={['dd-trigger-label', !hasSelection ? 'dd-trigger-label--placeholder' : ''].filter(Boolean).join(' ')}>
            {triggerLabel}
          </span>
        )}

        <span className="dd-trigger-icons">
          {hasSelection && (
            <button
              type="button"
              className="dd-clear-btn"
              aria-label="Clear selection"
              tabIndex={-1}
              onClick={(e) => {
                e.stopPropagation();
                clearAll();
              }}
            >
              ×
            </button>
          )}
          <svg
            className={['dd-chevron', isOpen ? 'dd-chevron--open' : ''].filter(Boolean).join(' ')}
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
          >
            <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </button>

      {/* Live region for screen readers */}
      <span role="status" aria-live="polite" className="dd-sr-only">
        {isOpen ? `${filteredOptions.length} options available` : ''}
      </span>

      {/* Panel */}
      {isOpen && (
        <div className="dd-panel" role="presentation">
          {searchable && (
            <div className="dd-search-wrap">
              <input
                ref={searchRef}
                id={searchId}
                type="search"
                className="dd-search"
                placeholder="Search..."
                value={searchQuery}
                aria-label="Search options"
                aria-controls={listId}
                autoComplete="off"
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={handleKeyDown}
              />
            </div>
          )}

          <div
            className="dd-list-wrap"
            style={{ maxHeight }}
            onScroll={(e) => onScroll((e.target as HTMLElement).scrollTop)}
          >
            {renderList()}
          </div>

          {multi && hasSelection && (
            <div className="dd-footer">
              <span className="dd-footer-count">{selected.length} selected</span>
              <button type="button" className="dd-footer-clear" onClick={clearAll}>
                Clear all
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default DropdownSystem;
