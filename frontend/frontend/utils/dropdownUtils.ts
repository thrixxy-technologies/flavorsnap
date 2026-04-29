// Dropdown utility functions and types

export interface DropdownOption {
  value: string;
  label: string;
  disabled?: boolean;
  group?: string;
  meta?: Record<string, unknown>;
}

export interface DropdownTheme {
  primary: string;
  background: string;
  surface: string;
  text: string;
  border: string;
  hover: string;
  selected: string;
  disabled: string;
  radius: string;
}

export const DEFAULT_DROPDOWN_THEME: DropdownTheme = {
  primary: '#3b82f6',
  background: '#ffffff',
  surface: '#f9fafb',
  text: '#111827',
  border: '#e5e7eb',
  hover: '#f3f4f6',
  selected: '#dbeafe',
  disabled: '#9ca3af',
  radius: '0.375rem',
};

export const DARK_DROPDOWN_THEME: DropdownTheme = {
  primary: '#60a5fa',
  background: '#111827',
  surface: '#1f2937',
  text: '#f9fafb',
  border: '#374151',
  hover: '#374151',
  selected: '#1e3a5f',
  disabled: '#6b7280',
  radius: '0.375rem',
};

/** Filter options by search query (label match, case-insensitive) */
export function filterOptions(options: DropdownOption[], query: string): DropdownOption[] {
  if (!query.trim()) return options;
  const lower = query.toLowerCase();
  return options.filter((o) => o.label.toLowerCase().includes(lower));
}

/** Group options by their `group` field */
export function groupOptions(options: DropdownOption[]): Map<string, DropdownOption[]> {
  const map = new Map<string, DropdownOption[]>();
  for (const option of options) {
    const key = option.group ?? '';
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(option);
  }
  return map;
}

/** Toggle a value in a multi-select array */
export function toggleSelection(selected: string[], value: string): string[] {
  return selected.includes(value)
    ? selected.filter((v) => v !== value)
    : [...selected, value];
}

/** Get display label for selected values */
export function getSelectionLabel(
  selected: string[],
  options: DropdownOption[],
  placeholder = 'Select...',
  maxDisplay = 2,
): string {
  if (selected.length === 0) return placeholder;
  const labels = selected
    .map((v) => options.find((o) => o.value === v)?.label ?? v)
    .slice(0, maxDisplay);
  const extra = selected.length - maxDisplay;
  return extra > 0 ? `${labels.join(', ')} +${extra}` : labels.join(', ');
}

/** Virtual scroll: compute which items are visible in the viewport */
export function getVirtualItems(
  totalCount: number,
  scrollTop: number,
  containerHeight: number,
  itemHeight: number,
  overscan = 3,
): { startIndex: number; endIndex: number; offsetY: number } {
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const visibleCount = Math.ceil(containerHeight / itemHeight);
  const endIndex = Math.min(totalCount - 1, startIndex + visibleCount + overscan * 2);
  return { startIndex, endIndex, offsetY: startIndex * itemHeight };
}

/** Returns the next focusable index, skipping disabled options */
export function getNextFocusIndex(
  options: DropdownOption[],
  current: number,
  direction: 1 | -1,
): number {
  let next = current + direction;
  while (next >= 0 && next < options.length) {
    if (!options[next].disabled) return next;
    next += direction;
  }
  return current;
}
