import { useState, useEffect, useMemo, useCallback } from 'react';
import { HistoryEntry } from '../types';
import { SearchFilters, DEFAULT_FILTERS, filterEntries, sortEntries, getSuggestions } from '../utils/filterUtils';
import { storage } from '../utils/storage';

const PREFS_KEY = 'flavorsnap_search_prefs';

export function useSearch(entries: HistoryEntry[]) {
  const [filters, setFilters] = useState<SearchFilters>(() =>
    storage.get<SearchFilters>(PREFS_KEY, DEFAULT_FILTERS)
  );
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // Persist preferences (exclude transient query)
  useEffect(() => {
    const { query, ...prefs } = filters;
    storage.set(PREFS_KEY, { ...DEFAULT_FILTERS, ...prefs });
  }, [filters]);

  // Autocomplete suggestions
  useEffect(() => {
    setSuggestions(getSuggestions(entries, filters.query));
  }, [entries, filters.query]);

  const results = useMemo(() => {
    const filtered = filterEntries(entries, filters);
    return sortEntries(filtered, filters);
  }, [entries, filters]);

  const updateFilter = useCallback(<K extends keyof SearchFilters>(key: K, value: SearchFilters[K]) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
    storage.remove(PREFS_KEY);
  }, []);

  return { filters, results, suggestions, updateFilter, resetFilters };
}
