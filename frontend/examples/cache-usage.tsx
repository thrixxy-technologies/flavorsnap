import React, { useEffect, useState } from 'react';
import CacheStatus from '../components/CacheStatus';
import { useCache } from '../hooks/useCache';

const CacheUsageExample: React.FC = () => {
  const {
    get,
    set,
    delete: deleteCache,
    clear,
    has,
    invalidateByTag,
    invalidateByPattern,
    preloadResources,
    warmCache,
    optimize,
    state,
    refreshStats,
    exportCacheData,
    importCacheData
  } = useCache({
    enableServiceWorker: true,
    enableBackgroundSync: true,
    enablePreloading: true,
    defaultTTL: 60 * 60 * 1000, // 1 hour
    maxCacheSize: 100 * 1024 * 1024 // 100MB
  });

  const [testData, setTestData] = useState<string>('');
  const [cacheKey, setCacheKey] = useState<string>('test-key');
  const [testResults, setTestResults] = useState<string[]>([]);

  useEffect(() => {
    // Add test result to display
    const addResult = (message: string) => {
      setTestResults(prev => [...prev.slice(-4), `${new Date().toLocaleTimeString()}: ${message}`]);
    };

    // Demonstrate cache operations
    const demonstrateCache = async () => {
      try {
        // Set some test data
        await set('user-profile', {
          name: 'John Doe',
          email: 'john@example.com',
          preferences: {
            theme: 'dark',
            language: 'en'
          }
        }, {
          priority: 'high',
          tags: ['user', 'profile'],
          metadata: { type: 'user-data' }
        });
        addResult('Cached user profile with high priority');

        // Get the cached data
        const profile = await get('user-profile');
        if (profile) {
          addResult(`Retrieved user profile: ${profile.name}`);
        }

        // Check if key exists
        const exists = has('user-profile');
        addResult(`Key exists check: ${exists}`);

        // Cache an image
        await set('sample-image', new ArrayBuffer(1024), {
          priority: 'medium',
          tags: ['image'],
          metadata: { type: 'image', size: 1024 }
        });
        addResult('Cached sample image (1KB)');

        // Test cache invalidation
        const invalidated = await invalidateByTag('user');
        addResult(`Invalidated ${invalidated} entries with 'user' tag`);

        // Test pattern invalidation
        const patternInvalidated = await invalidateByPattern(/user-/);
        addResult(`Invalidated ${patternInvalidated} entries matching pattern`);

        // Preload resources
        await preloadResources([
          { url: '/api/food/classify', priority: 10 },
          { url: '/api/user/preferences', priority: 8 },
          { url: '/api/analytics/stats', priority: 6 }
        ]);
        addResult('Preloaded 3 resources');

        // Warm cache
        await warmCache([
          '/api/food/categories',
          '/api/user/settings',
          '/api/notifications'
        ]);
        addResult('Warmed cache with 3 API patterns');

        // Optimize cache
        await optimize();
        addResult('Optimized cache structure');

      } catch (error) {
        addResult(`Error: ${error.message}`);
      }
    };

    // Run demonstration after component mounts
    setTimeout(demonstrateCache, 1000);
  }, [get, set, has, invalidateByTag, invalidateByPattern, preloadResources, warmCache, optimize]);

  const handleSetCache = async () => {
    if (!cacheKey || !testData) {
      alert('Please enter both key and data');
      return;
    }

    try {
      await set(cacheKey, testData, {
        priority: 'medium',
        tags: ['manual'],
        metadata: { type: 'manual-test' }
      });
      setTestData('');
      setCacheKey('');
      alert('Data cached successfully!');
    } catch (error) {
      alert(`Failed to cache data: ${error.message}`);
    }
  };

  const handleGetCache = async () => {
    if (!cacheKey) {
      alert('Please enter a cache key');
      return;
    }

    try {
      const data = await get(cacheKey);
      if (data) {
        alert(`Retrieved data: ${JSON.stringify(data, null, 2)}`);
      } else {
        alert('No data found for this key');
      }
    } catch (error) {
      alert(`Failed to get data: ${error.message}`);
    }
  };

  const handleDeleteCache = async () => {
    if (!cacheKey) {
      alert('Please enter a cache key');
      return;
    }

    try {
      const deleted = await deleteCache(cacheKey);
      alert(deleted ? 'Data deleted successfully!' : 'No data found to delete');
      setCacheKey('');
    } catch (error) {
      alert(`Failed to delete data: ${error.message}`);
    }
  };

  const handleClearCache = async () => {
    if (confirm('Are you sure you want to clear all cache?')) {
      try {
        await clear();
        setTestResults([]);
        alert('Cache cleared successfully!');
      } catch (error) {
        alert(`Failed to clear cache: ${error.message}`);
      }
    }
  };

  const handleExportCache = () => {
    try {
      const data = exportCacheData();
      const blob = new Blob([data], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cache-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      alert(`Failed to export cache: ${error.message}`);
    }
  };

  const handleImportCache = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      await importCacheData(text);
      alert('Cache data imported successfully!');
      refreshStats();
    } catch (error) {
      alert(`Failed to import cache: ${error.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <header>
          <h1 className="text-3xl font-bold text-gray-900">Intelligent Caching Demo</h1>
          <p className="text-gray-600">
            Advanced multi-level caching with service workers, memory management, and analytics
          </p>
        </header>

        {/* Cache Status Component */}
        <CacheStatus showDetails={true} />

        {/* Cache Operations */}
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Cache Operations</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Manual Cache Operations */}
            <div>
              <h3 className="text-lg font-medium mb-3">Manual Operations</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cache Key
                  </label>
                  <input
                    type="text"
                    value={cacheKey}
                    onChange={(e) => setCacheKey(e.target.value)}
                    placeholder="Enter cache key"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cache Data (JSON)
                  </label>
                  <textarea
                    value={testData}
                    onChange={(e) => setTestData(e.target.value)}
                    placeholder='{"key": "value"}'
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div className="flex gap-2">
                  <button
                    onClick={handleSetCache}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                  >
                    Set Cache
                  </button>
                  <button
                    onClick={handleGetCache}
                    className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                  >
                    Get Cache
                  </button>
                  <button
                    onClick={handleDeleteCache}
                    className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>

            {/* Advanced Operations */}
            <div>
              <h3 className="text-lg font-medium mb-3">Advanced Operations</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={optimize}
                    className="px-3 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600"
                  >
                    Optimize
                  </button>
                  <button
                    onClick={() => invalidateByTag('test')}
                    className="px-3 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
                  >
                    Invalidate Tag
                  </button>
                  <button
                    onClick={() => invalidateByPattern(/test-/)}
                    className="px-3 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600"
                  >
                    Invalidate Pattern
                  </button>
                  <button
                    onClick={handleClearCache}
                    className="px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
                  >
                    Clear All
                  </button>
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={handleExportCache}
                    className="px-3 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600"
                  >
                    Export
                  </button>
                  <label className="px-3 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 text-center cursor-pointer">
                    Import
                    <input
                      type="file"
                      accept=".json"
                      onChange={handleImportCache}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Test Results */}
        {testResults.length > 0 && (
          <section className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Test Results</h2>
            <div className="space-y-2">
              {testResults.map((result, index) => (
                <div
                  key={index}
                  className="p-3 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <code className="text-sm text-gray-700">{result}</code>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Cache Configuration */}
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Cache Configuration</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div>
              <h3 className="font-medium mb-2">Performance</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>Hit Rate:</span>
                  <span className="font-medium">{state.stats.hitRate.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Avg Access:</span>
                  <span className="font-medium">{state.analytics.averageAccessTime.toFixed(1)}ms</span>
                </div>
                <div className="flex justify-between">
                  <span>Entries:</span>
                  <span className="font-medium">{state.stats.totalEntries}</span>
                </div>
              </div>
            </div>

            <div>
              <h3 className="font-medium mb-2">Storage</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>Total Size:</span>
                  <span className="font-medium">{(state.stats.totalSize / 1024 / 1024).toFixed(2)} MB</span>
                </div>
                <div className="flex justify-between">
                  <span>Max Size:</span>
                  <span className="font-medium">100 MB</span>
                </div>
                <div className="flex justify-between">
                  <span>Usage:</span>
                  <span className="font-medium">
                    {((state.stats.totalSize / (100 * 1024 * 1024)) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>

            <div>
              <h3 className="font-medium mb-2">Service Worker</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>Status:</span>
                  <span className={`font-medium ${state.serviceWorkerActive ? 'text-green-600' : 'text-gray-500'}`}>
                    {state.serviceWorkerActive ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Online:</span>
                  <span className={`font-medium ${state.isOnline ? 'text-green-600' : 'text-red-600'}`}>
                    {state.isOnline ? 'Online' : 'Offline'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Background Sync:</span>
                  <span className="font-medium">
                    {state.backgroundSyncQueue.length} pending
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Priority Distribution */}
        <section className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Priority Distribution</h2>
          <div className="space-y-3">
            {Object.entries(state.stats.entriesByPriority).map(([priority, count]) => (
              <div key={priority} className="flex items-center justify-between">
                <span className="font-medium capitalize">{priority}</span>
                <div className="flex items-center gap-3">
                  <div className="w-48 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{
                        width: `${(count / state.stats.totalEntries) * 100}%`
                      }}
                    />
                  </div>
                  <span className="text-sm text-gray-600 w-12">{count}</span>
                  <span className="text-sm text-gray-500">
                    ({((count / state.stats.totalEntries) * 100).toFixed(1)}%)
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};

export default CacheUsageExample;
