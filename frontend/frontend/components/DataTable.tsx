// Powerful table component with sorting, filtering, pagination, virtual scrolling,
// column resizing, export, and full accessibility support.

import React from 'react';
import '@/frontend/styles/table.css';
import {
  ColumnDef,
  TableTheme,
  DEFAULT_TABLE_THEME,
} from '@/frontend/utils/tableUtils';
import { useTable, UseTableOptions } from '@/frontend/hooks/useTable';

export interface DataTableProps<T extends Record<string, unknown>>
  extends Omit<UseTableOptions<T>, 'theme'> {
  /** Show column filter inputs below headers */
  showFilters?: boolean;
  /** Show export buttons */
  showExport?: boolean;
  /** Show row selection checkboxes */
  selectable?: boolean;
  /** Caption for the table (accessibility) */
  caption?: string;
  theme?: TableTheme;
  className?: string;
  exportFilename?: string;
  /** Page size options for the page-size selector */
  pageSizeOptions?: number[];
  /** Aria label for the table */
  'aria-label'?: string;
}

export function DataTable<T extends Record<string, unknown>>({
  data,
  columns,
  defaultSort,
  defaultFilters,
  defaultPageSize = 10,
  virtualScroll = false,
  rowHeight = 44,
  containerHeight = 480,
  theme = DEFAULT_TABLE_THEME,
  selectable = false,
  selectedRows,
  rowKey = (row) => String(row.id ?? JSON.stringify(row)),
  onSelectionChange,
  showFilters = true,
  showExport = true,
  caption,
  className = '',
  exportFilename = 'table-export',
  pageSizeOptions = [10, 25, 50, 100],
  'aria-label': ariaLabel,
}: DataTableProps<T>) {
  const tableId = React.useId();
  const captionId = React.useId();
  const liveId = React.useId();

  const {
    visibleRows,
    filteredCount,
    totalCount,
    sort,
    setSort,
    filters,
    setFilter,
    clearFilters,
    pagination,
    setPage,
    setPageSize,
    pageCount,
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
  } = useTable({
    data,
    columns,
    defaultSort,
    defaultFilters,
    defaultPageSize,
    virtualScroll,
    rowHeight,
    containerHeight,
    theme,
    selectedRows,
    rowKey,
    onSelectionChange,
  });

  // Column resize drag state
  const resizingRef = React.useRef<{ key: string; startX: number; startWidth: number } | null>(null);

  const startResize = React.useCallback(
    (e: React.MouseEvent, key: string) => {
      e.preventDefault();
      const startWidth = columnWidths[key] ?? 120;
      resizingRef.current = { key, startX: e.clientX, startWidth };

      const onMove = (ev: MouseEvent) => {
        if (!resizingRef.current) return;
        const delta = ev.clientX - resizingRef.current.startX;
        setColumnWidth(resizingRef.current.key, resizingRef.current.startWidth + delta);
      };
      const onUp = () => {
        resizingRef.current = null;
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
      };
      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
    },
    [columnWidths, setColumnWidth],
  );

  const cssVars = {
    '--tbl-primary': theme.primary,
    '--tbl-bg': theme.background,
    '--tbl-surface': theme.surface,
    '--tbl-text': theme.text,
    '--tbl-border': theme.border,
    '--tbl-hover': theme.hover,
    '--tbl-selected': theme.selected,
    '--tbl-header-bg': theme.headerBg,
    '--tbl-radius': theme.radius,
    '--tbl-row-height': `${rowHeight}px`,
  } as React.CSSProperties;

  const hasActiveFilters = Object.values(filters).some((v) => v.trim() !== '');

  // Rows to render (virtual or paginated)
  const renderRows = virtualScroll
    ? visibleRows.slice(virtualState.startIndex, virtualState.endIndex + 1)
    : visibleRows;

  return (
    <div
      className={['tbl-root', className].filter(Boolean).join(' ')}
      style={cssVars}
    >
      {/* Toolbar */}
      <div className="tbl-toolbar" role="toolbar" aria-label="Table controls">
        <div className="tbl-toolbar-info" aria-live="polite" id={liveId}>
          {hasActiveFilters
            ? `${filteredCount} of ${totalCount} rows`
            : `${totalCount} rows`}
          {selectedKeys.size > 0 && ` · ${selectedKeys.size} selected`}
        </div>
        <div className="tbl-toolbar-actions">
          {hasActiveFilters && (
            <button
              type="button"
              className="tbl-btn tbl-btn--ghost"
              onClick={clearFilters}
              aria-label="Clear all filters"
            >
              Clear filters
            </button>
          )}
          {showExport && (
            <>
              <button
                type="button"
                className="tbl-btn tbl-btn--ghost"
                onClick={() => exportAsCSV(`${exportFilename}.csv`)}
                aria-label="Export as CSV"
              >
                Export CSV
              </button>
              <button
                type="button"
                className="tbl-btn tbl-btn--ghost"
                onClick={() => exportAsJSON(`${exportFilename}.json`)}
                aria-label="Export as JSON"
              >
                Export JSON
              </button>
            </>
          )}
        </div>
      </div>

      {/* Table scroll container */}
      <div
        className="tbl-scroll"
        style={virtualScroll ? { height: containerHeight, overflowY: 'auto' } : undefined}
        onScroll={virtualScroll ? (e) => onScroll((e.target as HTMLElement).scrollTop) : undefined}
        role="region"
        aria-label={ariaLabel ?? caption ?? 'Data table'}
      >
        <table
          id={tableId}
          className="tbl-table"
          role="grid"
          aria-labelledby={caption ? captionId : undefined}
          aria-label={!caption ? (ariaLabel ?? 'Data table') : undefined}
          aria-rowcount={filteredCount}
          aria-colcount={columns.length + (selectable ? 1 : 0)}
        >
          {caption && (
            <caption id={captionId} className="tbl-caption">
              {caption}
            </caption>
          )}

          <colgroup>
            {selectable && <col style={{ width: 44 }} />}
            {columns.map((col) => (
              <col
                key={col.key}
                style={columnWidths[col.key] ? { width: columnWidths[col.key] } : undefined}
              />
            ))}
          </colgroup>

          <thead className="tbl-thead">
            {/* Header row */}
            <tr role="row">
              {selectable && (
                <th
                  scope="col"
                  className="tbl-th tbl-th--check"
                  aria-label="Select all rows"
                >
                  <input
                    type="checkbox"
                    className="tbl-checkbox"
                    checked={isAllSelected}
                    ref={(el) => { if (el) el.indeterminate = isIndeterminate; }}
                    onChange={toggleAll}
                    aria-label="Select all visible rows"
                  />
                </th>
              )}
              {columns.map((col) => {
                const isSorted = sort.key === col.key && sort.direction !== null;
                return (
                  <th
                    key={col.key}
                    scope="col"
                    className={[
                      'tbl-th',
                      col.sortable ? 'tbl-th--sortable' : '',
                      isSorted ? 'tbl-th--sorted' : '',
                      col.align ? `tbl-th--${col.align}` : '',
                    ].filter(Boolean).join(' ')}
                    aria-sort={
                      isSorted
                        ? sort.direction === 'asc' ? 'ascending' : 'descending'
                        : col.sortable ? 'none' : undefined
                    }
                    style={columnWidths[col.key] ? { width: columnWidths[col.key] } : undefined}
                  >
                    <div className="tbl-th-inner">
                      {col.sortable ? (
                        <button
                          type="button"
                          className="tbl-sort-btn"
                          onClick={() => setSort(col.key)}
                          aria-label={`Sort by ${col.header}${isSorted ? `, currently ${sort.direction}` : ''}`}
                        >
                          <span>{col.header}</span>
                          <SortIcon direction={isSorted ? sort.direction : null} />
                        </button>
                      ) : (
                        <span>{col.header}</span>
                      )}
                      {/* Resize handle */}
                      <div
                        className="tbl-resize-handle"
                        role="separator"
                        aria-label={`Resize ${col.header} column`}
                        aria-orientation="vertical"
                        tabIndex={0}
                        onMouseDown={(e) => startResize(e, col.key)}
                        onKeyDown={(e) => {
                          const w = columnWidths[col.key] ?? 120;
                          if (e.key === 'ArrowRight') setColumnWidth(col.key, w + 10);
                          if (e.key === 'ArrowLeft') setColumnWidth(col.key, w - 10);
                        }}
                      />
                    </div>
                  </th>
                );
              })}
            </tr>

            {/* Filter row */}
            {showFilters && (
              <tr role="row" className="tbl-filter-row">
                {selectable && <th scope="col" className="tbl-th tbl-th--check" />}
                {columns.map((col) => (
                  <th key={col.key} scope="col" className="tbl-th tbl-th--filter">
                    {col.filterable !== false && (
                      <input
                        type="search"
                        className="tbl-filter-input"
                        value={filters[col.key] ?? ''}
                        onChange={(e) => setFilter(col.key, e.target.value)}
                        placeholder={`Filter ${col.header}`}
                        aria-label={`Filter by ${col.header}`}
                      />
                    )}
                  </th>
                ))}
              </tr>
            )}
          </thead>

          <tbody className="tbl-tbody">
            {/* Virtual scroll spacer */}
            {virtualScroll && virtualState.offsetY > 0 && (
              <tr aria-hidden="true" style={{ height: virtualState.offsetY }}>
                <td colSpan={columns.length + (selectable ? 1 : 0)} />
              </tr>
            )}

            {renderRows.length === 0 ? (
              <tr role="row">
                <td
                  colSpan={columns.length + (selectable ? 1 : 0)}
                  className="tbl-empty"
                  role="gridcell"
                >
                  No data to display
                </td>
              </tr>
            ) : (
              renderRows.map((row, rowIdx) => {
                const key = rowKey(row);
                const isSelected = selectedKeys.has(key);
                const ariaRowIndex = virtualScroll
                  ? virtualState.startIndex + rowIdx + 2 // +2: 1-based + header
                  : (pagination.page - 1) * pagination.pageSize + rowIdx + 2;

                return (
                  <tr
                    key={key}
                    role="row"
                    aria-rowindex={ariaRowIndex}
                    aria-selected={selectable ? isSelected : undefined}
                    className={[
                      'tbl-tr',
                      isSelected ? 'tbl-tr--selected' : '',
                    ].filter(Boolean).join(' ')}
                    onClick={selectable ? () => toggleRow(key) : undefined}
                  >
                    {selectable && (
                      <td role="gridcell" className="tbl-td tbl-td--check">
                        <input
                          type="checkbox"
                          className="tbl-checkbox"
                          checked={isSelected}
                          onChange={() => toggleRow(key)}
                          aria-label={`Select row ${ariaRowIndex - 1}`}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </td>
                    )}
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        role="gridcell"
                        className={[
                          'tbl-td',
                          col.align ? `tbl-td--${col.align}` : '',
                        ].filter(Boolean).join(' ')}
                      >
                        {col.render
                          ? col.render(row[col.key], row)
                          : String(row[col.key] ?? '')}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}

            {/* Virtual scroll bottom spacer */}
            {virtualScroll && (() => {
              const bottomOffset =
                virtualState.totalHeight - virtualState.offsetY - (renderRows.length * rowHeight);
              return bottomOffset > 0 ? (
                <tr aria-hidden="true" style={{ height: bottomOffset }}>
                  <td colSpan={columns.length + (selectable ? 1 : 0)} />
                </tr>
              ) : null;
            })()}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {!virtualScroll && (
        <div className="tbl-pagination" role="navigation" aria-label="Table pagination">
          <div className="tbl-page-size">
            <label htmlFor={`${tableId}-page-size`} className="tbl-page-size-label">
              Rows per page:
            </label>
            <select
              id={`${tableId}-page-size`}
              className="tbl-page-size-select"
              value={pagination.pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              aria-label="Rows per page"
            >
              {pageSizeOptions.map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>

          <span className="tbl-page-info" aria-live="polite">
            Page {pagination.page} of {pageCount}
          </span>

          <div className="tbl-page-btns">
            <button
              type="button"
              className="tbl-btn tbl-btn--icon"
              onClick={() => setPage(1)}
              disabled={pagination.page === 1}
              aria-label="First page"
            >
              «
            </button>
            <button
              type="button"
              className="tbl-btn tbl-btn--icon"
              onClick={() => setPage(pagination.page - 1)}
              disabled={pagination.page === 1}
              aria-label="Previous page"
            >
              ‹
            </button>
            <PageNumbers
              current={pagination.page}
              total={pageCount}
              onSelect={setPage}
            />
            <button
              type="button"
              className="tbl-btn tbl-btn--icon"
              onClick={() => setPage(pagination.page + 1)}
              disabled={pagination.page === pageCount}
              aria-label="Next page"
            >
              ›
            </button>
            <button
              type="button"
              className="tbl-btn tbl-btn--icon"
              onClick={() => setPage(pageCount)}
              disabled={pagination.page === pageCount}
              aria-label="Last page"
            >
              »
            </button>
          </div>
        </div>
      )}

      {/* Screen reader live region */}
      <span role="status" aria-live="polite" className="tbl-sr-only">
        {`Showing ${renderRows.length} rows`}
      </span>
    </div>
  );
}

// ── Sub-components ──

function SortIcon({ direction }: { direction: 'asc' | 'desc' | null }) {
  return (
    <span className="tbl-sort-icon" aria-hidden="true">
      {direction === 'asc' && '↑'}
      {direction === 'desc' && '↓'}
      {direction === null && '↕'}
    </span>
  );
}

function PageNumbers({
  current,
  total,
  onSelect,
}: {
  current: number;
  total: number;
  onSelect: (page: number) => void;
}) {
  const pages = buildPageRange(current, total);
  return (
    <>
      {pages.map((p, i) =>
        p === '...' ? (
          <span key={`ellipsis-${i}`} className="tbl-page-ellipsis" aria-hidden="true">
            …
          </span>
        ) : (
          <button
            key={p}
            type="button"
            className={['tbl-btn tbl-btn--page', p === current ? 'tbl-btn--page-active' : ''].filter(Boolean).join(' ')}
            onClick={() => onSelect(p as number)}
            aria-label={`Page ${p}`}
            aria-current={p === current ? 'page' : undefined}
          >
            {p}
          </button>
        ),
      )}
    </>
  );
}

function buildPageRange(current: number, total: number): (number | '...')[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages: (number | '...')[] = [1];
  if (current > 3) pages.push('...');
  for (let p = Math.max(2, current - 1); p <= Math.min(total - 1, current + 1); p++) {
    pages.push(p);
  }
  if (current < total - 2) pages.push('...');
  pages.push(total);
  return pages;
}

export default DataTable;
