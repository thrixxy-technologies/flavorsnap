// Hook for DataTable state management

import React from 'react';
import {
  ColumnDef,
  SortState,
  FilterState,
  PaginationState,
  TableTheme,
  DEFAULT_TABLE_THEME,
  sortRows,
  filterRows,
  paginateRows,
  totalPages,
  getVirtualRows,
  nextSortDirection,
  exportCSV,
  exportJSON,
} from '@/frontend/utils/tableUtils';

export interface UseTableOptions<T extends Record<string, unknown>> {
  data: T[];
  columns: ColumnDef<T>[];
  defaultSort?: SortState;
  defaultFilters?: FilterState;
  defaultPageSize?: number;
  /** Enable virtual scrolling (disables pagination) */
  virtualScroll?: boolean;
  rowHeight?: number;
  containerHeight?: number;
  theme?: TableTheme;
  /** Controlled selection */
  selectedRows?: Set<string>;
  rowKey?: (row: T) => string;
  onSelectionChange?: (keys: Set<string>) => void;
}

export interface ColumnWidthMap {
  [key: string]: number;
}

export interface UseTableReturn<T extends Record<string, unknown>> {
  // Processed data
  processedRows: T[];
  visibleRows: T[];
  totalCount: number;
  filteredCount: number;
  // Sort
  sort: SortState;
  setSort: (key: string) => void;
  // Filters
  filters: FilterState;
  setFilter: (key: string, value: string) => void;
  clearFilters: () => void;
  // Pagination
  pagination: PaginationState;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  pageCount: number;
  // Column widths
  columnWidths: ColumnWidthMap;
  setColumnWidth: (key: string, width: number) => void;
  // Selection
  selectedKeys: Set<string>;
  toggleRow: (key: string) => void;
  toggleAll: () => void;
  isAllSelected: boolean;
  isIndeterminate: boolean;
  // Virtual scroll
  virtualState: { startIndex: number; endIndex: number; offsetY: number; totalHeight: number };
  onScroll: (scrollTop: number) => void;
  // Export
  exportAsCSV: (filename?: string) => void;
  exportAsJSON: (filename?: string) => void;
  // Theme
  theme: TableTheme;
}

export function useTable<T extends Record<string, unknown>>({
  data,
  columns,
  defaultSort = { key: '', direction: null },
  defaultFilters = {},
  defaultPageSize = 10,
  virtualScroll = false,
  rowHeight = 44,
  containerHeight = 480,
  theme = DEFAULT_TABLE_THEME,
  selectedRows,
  rowKey = (row) => String(row.id ?? JSON.stringify(row)),
  onSelectionChange,
}: UseTableOptions<T>): UseTableReturn<T> {
  const isControlledSelection = selectedRows !== undefined;

  const [sort, setSortState] = React.useState<SortState>(defaultSort);
  const [filters, setFiltersState] = React.useState<FilterState>(defaultFilters);
  const [pagination, setPagination] = React.useState<PaginationState>({
    page: 1,
    pageSize: defaultPageSize,
  });
  const [internalSelected, setInternalSelected] = React.useState<Set<string>>(new Set());
  const [columnWidths, setColumnWidths] = React.useState<ColumnWidthMap>(() =>
    Object.fromEntries(columns.filter((c) => c.width).map((c) => [c.key, c.width!])),
  );
  const [scrollTop, setScrollTop] = React.useState(0);

  const selectedKeys = isControlledSelection ? selectedRows! : internalSelected;

  // Reset to page 1 when filters/sort change
  React.useEffect(() => {
    setPagination((p) => ({ ...p, page: 1 }));
  }, [filters, sort]);

  const filteredRows = React.useMemo(() => filterRows(data, filters), [data, filters]);
  const sortedRows = React.useMemo(
    () => sortRows(filteredRows, sort, columns),
    [filteredRows, sort, columns],
  );

  const visibleRows = React.useMemo(() => {
    if (virtualScroll) return sortedRows;
    return paginateRows(sortedRows, pagination.page, pagination.pageSize);
  }, [virtualScroll, sortedRows, pagination]);

  const virtualState = React.useMemo(() => {
    if (!virtualScroll) {
      return { startIndex: 0, endIndex: visibleRows.length - 1, offsetY: 0, totalHeight: visibleRows.length * rowHeight };
    }
    return getVirtualRows(sortedRows.length, scrollTop, containerHeight, rowHeight);
  }, [virtualScroll, sortedRows.length, scrollTop, containerHeight, rowHeight, visibleRows.length]);

  const setSort = React.useCallback((key: string) => {
    setSortState((prev) => {
      if (prev.key !== key) return { key, direction: 'asc' };
      return { key, direction: nextSortDirection(prev.direction) };
    });
  }, []);

  const setFilter = React.useCallback((key: string, value: string) => {
    setFiltersState((prev) => ({ ...prev, [key]: value }));
  }, []);

  const clearFilters = React.useCallback(() => setFiltersState({}), []);

  const setPage = React.useCallback((page: number) => {
    setPagination((p) => ({ ...p, page }));
  }, []);

  const setPageSize = React.useCallback((pageSize: number) => {
    setPagination({ page: 1, pageSize });
  }, []);

  const setColumnWidth = React.useCallback((key: string, width: number) => {
    const col = columns.find((c) => c.key === key);
    const min = col?.minWidth ?? 40;
    const max = col?.maxWidth ?? 800;
    setColumnWidths((prev) => ({ ...prev, [key]: Math.min(max, Math.max(min, width)) }));
  }, [columns]);

  const updateSelection = React.useCallback((next: Set<string>) => {
    if (!isControlledSelection) setInternalSelected(next);
    onSelectionChange?.(next);
  }, [isControlledSelection, onSelectionChange]);

  const toggleRow = React.useCallback((key: string) => {
    const next = new Set(selectedKeys);
    if (next.has(key)) next.delete(key); else next.add(key);
    updateSelection(next);
  }, [selectedKeys, updateSelection]);

  const visibleKeys = React.useMemo(() => visibleRows.map(rowKey), [visibleRows, rowKey]);
  const isAllSelected = visibleKeys.length > 0 && visibleKeys.every((k) => selectedKeys.has(k));
  const isIndeterminate = !isAllSelected && visibleKeys.some((k) => selectedKeys.has(k));

  const toggleAll = React.useCallback(() => {
    if (isAllSelected) {
      const next = new Set(selectedKeys);
      visibleKeys.forEach((k) => next.delete(k));
      updateSelection(next);
    } else {
      const next = new Set(selectedKeys);
      visibleKeys.forEach((k) => next.add(k));
      updateSelection(next);
    }
  }, [isAllSelected, selectedKeys, visibleKeys, updateSelection]);

  const onScroll = React.useCallback((top: number) => setScrollTop(top), []);

  const exportAsCSV = React.useCallback((filename?: string) => {
    exportCSV(sortedRows, columns, filename);
  }, [sortedRows, columns]);

  const exportAsJSON = React.useCallback((filename?: string) => {
    exportJSON(sortedRows, filename);
  }, [sortedRows]);

  return {
    processedRows: sortedRows,
    visibleRows,
    totalCount: data.length,
    filteredCount: filteredRows.length,
    sort,
    setSort,
    filters,
    setFilter,
    clearFilters,
    pagination,
    setPage,
    setPageSize,
    pageCount: totalPages(filteredRows.length, pagination.pageSize),
    columnWidths,
    setColumnWidth,
    selectedKeys,
    toggleRow,
    toggleAll,
    isAllSelected,
    isIndeterminate,
    virtualState,
    onScroll,
    exportAsCSV,
    exportAsJSON,
    theme,
  };
}
