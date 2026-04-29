import { HistoryEntry } from '../types';

export const FOOD_CLASSES = ['Akara', 'Bread', 'Egusi', 'Moi Moi', 'Rice and Stew', 'Yam'] as const;

export interface SearchFilters {
  query: string;
  categories: string[];
  confidenceMin: number;
  confidenceMax: number;
  dateFrom: string;
  dateTo: string;
  sortBy: 'date' | 'confidence' | 'relevance' | 'frequency';
  sortOrder: 'asc' | 'desc';
}

export const DEFAULT_FILTERS: SearchFilters = {
  query: '',
  categories: [],
  confidenceMin: 0,
  confidenceMax: 100,
  dateFrom: '',
  dateTo: '',
  sortBy: 'date',
  sortOrder: 'desc',
};

export function filterEntries(entries: HistoryEntry[], filters: SearchFilters): HistoryEntry[] {
  const q = filters.query.toLowerCase().trim();

  return entries.filter((entry) => {
    const label = (entry.prediction || entry.food || '').toLowerCase();
    const date = new Date(entry.timestamp).toLocaleDateString().toLowerCase();

    // Full-text search across food name and date
    if (q && !label.includes(q) && !date.includes(q)) return false;

    // Category filter
    if (filters.categories.length > 0 && !filters.categories.includes(entry.prediction || entry.food || '')) return false;

    // Confidence range
    const conf = entry.confidence * (entry.confidence <= 1 ? 100 : 1);
    if (conf < filters.confidenceMin || conf > filters.confidenceMax) return false;

    // Date range
    const ts = new Date(entry.timestamp).getTime();
    if (filters.dateFrom && ts < new Date(filters.dateFrom).getTime()) return false;
    if (filters.dateTo && ts > new Date(filters.dateTo + 'T23:59:59').getTime()) return false;

    return true;
  });
}

export function sortEntries(entries: HistoryEntry[], filters: SearchFilters): HistoryEntry[] {
  const { sortBy, sortOrder, query } = filters;
  const dir = sortOrder === 'asc' ? 1 : -1;

  if (sortBy === 'frequency') {
    const freq: Record<string, number> = {};
    entries.forEach((e) => {
      const k = e.prediction || e.food || '';
      freq[k] = (freq[k] || 0) + 1;
    });
    return [...entries].sort((a, b) => {
      const fa = freq[a.prediction || a.food || ''] || 0;
      const fb = freq[b.prediction || b.food || ''] || 0;
      return (fa - fb) * dir;
    });
  }

  if (sortBy === 'relevance' && query.trim()) {
    const q = query.toLowerCase();
    return [...entries].sort((a, b) => {
      const la = (a.prediction || a.food || '').toLowerCase();
      const lb = (b.prediction || b.food || '').toLowerCase();
      const sa = la.startsWith(q) ? 2 : la.includes(q) ? 1 : 0;
      const sb = lb.startsWith(q) ? 2 : lb.includes(q) ? 1 : 0;
      return (sa - sb) * -dir; // higher relevance first
    });
  }

  return [...entries].sort((a, b) => {
    if (sortBy === 'confidence') {
      const ca = a.confidence * (a.confidence <= 1 ? 100 : 1);
      const cb = b.confidence * (b.confidence <= 1 ? 100 : 1);
      return (ca - cb) * dir;
    }
    // default: date
    return (new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()) * dir;
  });
}

export function getSuggestions(entries: HistoryEntry[], query: string): string[] {
  if (!query.trim()) return [];
  const q = query.toLowerCase();
  const seen = new Set<string>();
  const suggestions: string[] = [];

  // Food class suggestions
  FOOD_CLASSES.forEach((cls) => {
    if (cls.toLowerCase().includes(q)) suggestions.push(cls);
  });

  // Date suggestions from history
  entries.forEach((e) => {
    const date = new Date(e.timestamp).toLocaleDateString();
    if (date.includes(q) && !seen.has(date)) {
      seen.add(date);
      suggestions.push(date);
    }
  });

  return suggestions.slice(0, 6);
}

export function getFrequencyMap(entries: HistoryEntry[]): Record<string, number> {
  return entries.reduce<Record<string, number>>((acc, e) => {
    const k = e.prediction || e.food || 'Unknown';
    acc[k] = (acc[k] || 0) + 1;
    return acc;
  }, {});
}
