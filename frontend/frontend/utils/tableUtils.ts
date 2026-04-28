// Table utility functions and types

export type SortDirection = 'asc' | 'desc' | null;

export interface ColumnDef<T = Record<string, unknown>> {
  key: string;
  header: string;
  /** Custom cell renderer */
  render?: (value: unknown, row: T) => React.ReactNode;
  /** Enable sorting for this column */
  sortable?: boolean;
  /** Enable filtering for this column */
  filterable?: boolean;
  /** Initial width in px */
  width?: number;
  minWidth?: number;
  maxWidth?: number;
  /** Align cell content */
  align?: 'left' | 'center' | 'right';
  /** Custom sort comparator */
  comparator?: (a: unknown, b: unknown) => number;
}

export interface SortState {
  key: string;
  direction: SortDirection;
}

export interface FilterState {
  [columnKey: string]: string;
}

export interface PaginationState {
  page: number;
  pageSize: number;
}

export interface TableTheme {
  primary: string;
  background: string;
  surface: string;
  text: string;
  border: string;
  hover: string;
  selected: string;
  headerBg: string;
  radius: string;
}

export const DEFAULT_TABLE_THEME: TableTheme = {
  primary: '#3b82f6',
  background: '#ffffff',
  surface: '#f9fafb',
  text: '#111827',
  border: '#e5e7eb',
  hover: '#f3f4f6',
  selected: '#dbeafe',
  headerBg: '#f3f4f6',
  radius: '0.5rem',
};

/** Sort rows by a column key and direction */
export function sortRows<T extends Record<string, unknown>>(
  rows: T[],
  sort: SortState,
  columns: ColumnDef<T>[],
): T[] {
  if (!sort.direction) return rows;
  const col = columns.find((c) => c.key === sort.key);
  const multiplier = sort.direction === 'asc' ? 1 : -1;

  return [...rows].sort((a, b) => {
    const av = a[sort.key];
    const bv = b[sort.key];
    if (col?.comparator) return col.comparator(av, bv) * multiplier;
    return defaultCompare(av, bv) * multiplier;
  });
}

function defaultCompare(a: unknown, b: unknown): number {
  if (a == null && b == null) return 0;
  if (a == null) return -1;
  if (b == null) return 1;
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' });
}

/** Filter rows by column filter values */
export function filterRows<T extends Record<string, unknown>>(
  rows: T[],
  filters: FilterState,
): T[] {
  const activeFilters = Object.entries(filters).filter(([, v]) => v.trim() !== '');
  if (activeFilters.length === 0) return rows;
  return rows.filter((row) =>
    activeFilters.every(([key, query]) => {
      const val = row[key];
      return String(val ?? '').toLowerCase().includes(query.toLowerCase());
    }),
  );
}

/** Paginate rows */
export function paginateRows<T>(rows: T[], page: number, pageSize: number): T[] {
  const start = (page - 1) * pageSize;
  return rows.slice(start, start + pageSize);
}

/** Total page count */
export function totalPages(totalRows: number, pageSize: number): number {
  return Math.max(1, Math.ceil(totalRows / pageSize));
}

/** Virtual scroll: compute visible row range */
export function getVirtualRows(
  totalCount: number,
  scrollTop: number,
  containerHeight: number,
  rowHeight: number,
  overscan = 5,
): { startIndex: number; endIndex: number; offsetY: number; totalHeight: number } {
  const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
  const visibleCount = Math.ceil(containerHeight / rowHeight);
  const endIndex = Math.min(totalCount - 1, startIndex + visibleCount + overscan * 2);
  return {
    startIndex,
    endIndex,
    offsetY: startIndex * rowHeight,
    totalHeight: totalCount * rowHeight,
  };
}

/** Cycle sort direction: null → asc → desc → null */
export function nextSortDirection(current: SortDirection): SortDirection {
  if (current === null) return 'asc';
  if (current === 'asc') return 'desc';
  return null;
}

// ── Export utilities ──

/** Convert rows to CSV string */
export function rowsToCSV<T extends Record<string, unknown>>(
  rows: T[],
  columns: ColumnDef<T>[],
): string {
  const exportCols = columns.filter((c) => !c.render || typeof c.render !== 'function');
  const header = exportCols.map((c) => csvEscape(c.header)).join(',');
  const body = rows.map((row) =>
    exportCols.map((c) => csvEscape(String(row[c.key] ?? ''))).join(','),
  );
  return [header, ...body].join('\n');
}

function csvEscape(value: string): string {
  if (/[",\n\r]/.test(value)) return `"${value.replace(/"/g, '""')}"`;
  return value;
}

/** Trigger a browser download */
export function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Export rows as CSV download */
export function exportCSV<T extends Record<string, unknown>>(
  rows: T[],
  columns: ColumnDef<T>[],
  filename = 'export.csv',
): void {
  downloadFile(rowsToCSV(rows, columns), filename, 'text/csv;charset=utf-8;');
}

/** Export rows as JSON download */
export function exportJSON<T extends Record<string, unknown>>(
  rows: T[],
  filename = 'export.json',
): void {
  downloadFile(JSON.stringify(rows, null, 2), filename, 'application/json');
}
