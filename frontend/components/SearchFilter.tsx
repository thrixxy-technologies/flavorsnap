import { useRef, useState } from 'react';
import { Search, X, ChevronDown, SlidersHorizontal } from 'lucide-react';
import { SearchFilters, FOOD_CLASSES } from '../utils/filterUtils';

interface Props {
  filters: SearchFilters;
  suggestions: string[];
  resultCount: number;
  totalCount: number;
  onUpdate: <K extends keyof SearchFilters>(key: K, value: SearchFilters[K]) => void;
  onReset: () => void;
}

export default function SearchFilter({ filters, suggestions, resultCount, totalCount, onUpdate, onReset }: Props) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const hasActiveFilters =
    filters.query ||
    filters.categories.length > 0 ||
    filters.confidenceMin > 0 ||
    filters.confidenceMax < 100 ||
    filters.dateFrom ||
    filters.dateTo;

  const toggleCategory = (cat: string) => {
    const next = filters.categories.includes(cat)
      ? filters.categories.filter((c) => c !== cat)
      : [...filters.categories, cat];
    onUpdate('categories', next);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 space-y-4">
      {/* Search bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" aria-hidden />
        <input
          ref={inputRef}
          type="search"
          value={filters.query}
          onChange={(e) => onUpdate('query', e.target.value)}
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
          placeholder="Search by food name or date…"
          className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
          aria-label="Search classifications"
          aria-autocomplete="list"
          aria-expanded={showSuggestions && suggestions.length > 0}
        />
        {filters.query && (
          <button
            onClick={() => onUpdate('query', '')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            aria-label="Clear search"
          >
            <X className="w-4 h-4" />
          </button>
        )}

        {/* Autocomplete dropdown */}
        {showSuggestions && suggestions.length > 0 && (
          <ul
            role="listbox"
            className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden"
          >
            {suggestions.map((s) => (
              <li
                key={s}
                role="option"
                aria-selected={false}
                onMouseDown={() => {
                  onUpdate('query', s);
                  setShowSuggestions(false);
                }}
                className="px-4 py-2 text-sm cursor-pointer hover:bg-orange-50 hover:text-orange-700"
              >
                {s}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Sort + Advanced toggle row */}
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-xs font-medium text-gray-500 shrink-0">Sort by</label>
        <select
          value={filters.sortBy}
          onChange={(e) => onUpdate('sortBy', e.target.value as SearchFilters['sortBy'])}
          className="text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-orange-400"
          aria-label="Sort by"
        >
          <option value="date">Date</option>
          <option value="confidence">Confidence</option>
          <option value="relevance">Relevance</option>
          <option value="frequency">Frequency</option>
        </select>
        <select
          value={filters.sortOrder}
          onChange={(e) => onUpdate('sortOrder', e.target.value as SearchFilters['sortOrder'])}
          className="text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-orange-400"
          aria-label="Sort order"
        >
          <option value="desc">Newest first</option>
          <option value="asc">Oldest first</option>
        </select>

        <button
          onClick={() => setShowAdvanced((v) => !v)}
          className="ml-auto flex items-center gap-1 text-sm text-gray-600 hover:text-orange-600 focus:outline-none focus:ring-2 focus:ring-orange-400 rounded px-2 py-1"
          aria-expanded={showAdvanced}
        >
          <SlidersHorizontal className="w-4 h-4" />
          Filters
          <ChevronDown className={`w-3 h-3 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
        </button>

        {hasActiveFilters && (
          <button
            onClick={onReset}
            className="text-xs text-red-500 hover:text-red-700 focus:outline-none focus:ring-2 focus:ring-red-400 rounded px-2 py-1"
          >
            Reset all
          </button>
        )}
      </div>

      {/* Advanced filters */}
      {showAdvanced && (
        <div className="space-y-4 pt-2 border-t border-gray-100">
          {/* Category chips */}
          <div>
            <p className="text-xs font-medium text-gray-500 mb-2">Food categories</p>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by food category">
              {FOOD_CLASSES.map((cat) => {
                const active = filters.categories.includes(cat);
                return (
                  <button
                    key={cat}
                    onClick={() => toggleCategory(cat)}
                    aria-pressed={active}
                    className={`px-3 py-1 rounded-full text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-orange-400 ${
                      active
                        ? 'bg-orange-500 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-orange-100 hover:text-orange-700'
                    }`}
                  >
                    {cat}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Confidence range */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-500 block mb-1">
                Min confidence: {filters.confidenceMin}%
              </label>
              <input
                type="range"
                min={0}
                max={100}
                value={filters.confidenceMin}
                onChange={(e) => onUpdate('confidenceMin', Number(e.target.value))}
                className="w-full accent-orange-500"
                aria-label="Minimum confidence"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 block mb-1">
                Max confidence: {filters.confidenceMax}%
              </label>
              <input
                type="range"
                min={0}
                max={100}
                value={filters.confidenceMax}
                onChange={(e) => onUpdate('confidenceMax', Number(e.target.value))}
                className="w-full accent-orange-500"
                aria-label="Maximum confidence"
              />
            </div>
          </div>

          {/* Date range */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-500 block mb-1">From date</label>
              <input
                type="date"
                value={filters.dateFrom}
                onChange={(e) => onUpdate('dateFrom', e.target.value)}
                className="w-full text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-orange-400"
                aria-label="Filter from date"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 block mb-1">To date</label>
              <input
                type="date"
                value={filters.dateTo}
                onChange={(e) => onUpdate('dateTo', e.target.value)}
                className="w-full text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-orange-400"
                aria-label="Filter to date"
              />
            </div>
          </div>
        </div>
      )}

      {/* Result count */}
      <p className="text-xs text-gray-500" aria-live="polite">
        Showing <span className="font-semibold text-gray-700">{resultCount}</span> of{' '}
        <span className="font-semibold text-gray-700">{totalCount}</span> results
      </p>
    </div>
  );
}
