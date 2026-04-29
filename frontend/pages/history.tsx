import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Download, Trash2, Clock } from 'lucide-react';
import { HistoryEntry } from '../types';
import { storage } from '../utils/storage';
import { exportToJSON, exportToCSV } from '../utils/exportUtils';
import { useSearch } from '../hooks/useSearch';
import SearchFilter from '../components/SearchFilter';

const HISTORY_KEY = 'classificationHistory';

function confidencePercent(entry: HistoryEntry): number {
  return Math.round(entry.confidence * (entry.confidence <= 1 ? 100 : 1));
}

function confidenceColor(pct: number): string {
  if (pct >= 80) return 'bg-green-100 text-green-800';
  if (pct >= 60) return 'bg-yellow-100 text-yellow-800';
  return 'bg-red-100 text-red-800';
}

export default function History() {
  const router = useRouter();
  const [allEntries, setAllEntries] = useState<HistoryEntry[]>([]);
  const { filters, results, suggestions, updateFilter, resetFilters } = useSearch(allEntries);

  useEffect(() => {
    setAllEntries(storage.get<HistoryEntry[]>(HISTORY_KEY, []));
  }, []);

  const clearHistory = () => {
    if (!confirm('Clear all classification history?')) return;
    storage.remove(HISTORY_KEY);
    setAllEntries([]);
  };

  const removeEntry = (id: number) => {
    const updated = allEntries.filter((e) => e.id !== id);
    storage.set(HISTORY_KEY, updated);
    setAllEntries(updated);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-blue-50 py-8">
      <div className="max-w-4xl mx-auto px-4 space-y-6">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <button
              onClick={() => router.push('/')}
              className="text-blue-600 hover:text-blue-800 text-sm mb-1"
            >
              ← Back to Home
            </button>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
              <Clock className="w-7 h-7 text-orange-500" aria-hidden />
              Classification History
            </h1>
          </div>

          {allEntries.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => exportToJSON(results, 'flavorsnap-history')}
                className="flex items-center gap-1.5 px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-orange-400"
                aria-label="Export filtered results as JSON"
              >
                <Download className="w-4 h-4" /> JSON
              </button>
              <button
                onClick={() => exportToCSV(results, 'flavorsnap-history')}
                className="flex items-center gap-1.5 px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-orange-400"
                aria-label="Export filtered results as CSV"
              >
                <Download className="w-4 h-4" /> CSV
              </button>
              <button
                onClick={clearHistory}
                className="flex items-center gap-1.5 px-3 py-2 text-sm bg-red-50 border border-red-200 text-red-600 rounded-lg hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-400"
                aria-label="Clear all history"
              >
                <Trash2 className="w-4 h-4" /> Clear all
              </button>
            </div>
          )}
        </div>

        {/* Search & Filter */}
        <SearchFilter
          filters={filters}
          suggestions={suggestions}
          resultCount={results.length}
          totalCount={allEntries.length}
          onUpdate={updateFilter}
          onReset={resetFilters}
        />

        {/* Results */}
        {allEntries.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-xl shadow-sm border border-gray-200">
            <Clock className="w-12 h-12 text-gray-300 mx-auto mb-3" aria-hidden />
            <p className="text-gray-500 text-lg font-medium">No classifications yet</p>
            <p className="text-gray-400 text-sm mt-1">Classify a food image to see it here.</p>
            <button
              onClick={() => router.push('/classify')}
              className="mt-4 px-5 py-2 bg-orange-500 text-white rounded-lg text-sm font-semibold hover:bg-orange-600 focus:outline-none focus:ring-2 focus:ring-orange-400"
            >
              Classify an image
            </button>
          </div>
        ) : results.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-xl shadow-sm border border-gray-200">
            <p className="text-gray-500">No results match your filters.</p>
            <button
              onClick={resetFilters}
              className="mt-3 text-sm text-orange-600 hover:underline focus:outline-none"
            >
              Reset filters
            </button>
          </div>
        ) : (
          <ul className="space-y-3" aria-label="Classification history results">
            {results.map((entry) => {
              const pct = confidencePercent(entry);
              const label = entry.prediction || entry.food || 'Unknown';
              return (
                <li
                  key={entry.id}
                  className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex flex-wrap items-center justify-between gap-3 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center shrink-0 text-orange-600 font-bold text-sm">
                      {label.charAt(0)}
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-gray-900 truncate">{label}</p>
                      <p className="text-xs text-gray-500">
                        {new Date(entry.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${confidenceColor(pct)}`}>
                      {pct}% confidence
                    </span>
                    <button
                      onClick={() => removeEntry(entry.id)}
                      className="text-gray-400 hover:text-red-500 focus:outline-none focus:ring-2 focus:ring-red-400 rounded p-1"
                      aria-label={`Remove ${label} entry`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
