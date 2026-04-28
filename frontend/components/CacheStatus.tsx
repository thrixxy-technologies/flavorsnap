import React, { useState, useEffect } from 'react';
import { 
  Database, 
  HardDrive, 
  Wifi, 
  WifiOff, 
  RefreshCw, 
  Trash2, 
  Download, 
  Upload, 
  Activity, 
  TrendingUp, 
  AlertCircle, 
  CheckCircle, 
  Clock, 
  Zap, 
  BarChart3, 
  PieChart, 
  Settings, 
  X,
  Info,
  Filter,
  Calendar
} from 'lucide-react';
import { useCache } from '../hooks/useCache';

interface CacheStatusProps {
  className?: string;
  showDetails?: boolean;
  compact?: boolean;
}

interface CacheHeatmapData {
  timestamp: number;
  size: number;
  hits: number;
}

const CacheStatus: React.FC<CacheStatusProps> = ({ 
  className = '', 
  showDetails = false,
  compact = false 
}) => {
  const { 
    state, 
    refreshStats, 
    clear, 
    optimize, 
    invalidateByTag, 
    preloadResources, 
    warmCache,
    getSWStats,
    clearSWCache,
    exportCacheData,
    importCacheData 
  } = useCache();

  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'analytics' | 'management'>('overview');
  const [swStats, setSwStats] = useState<any>(null);
  const [heatmapData, setHeatmapData] = useState<CacheHeatmapData[]>([]);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [isPreloading, setIsPreloading] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);

  useEffect(() => {
    // Generate heatmap data
    const generateHeatmapData = () => {
      const now = Date.now();
      const data: CacheHeatmapData[] = [];
      
      for (let i = 0; i < 24; i++) {
        const timestamp = now - (i * 60 * 60 * 1000); // Last 24 hours
        const size = Math.random() * 10 * 1024 * 1024; // Random size up to 10MB
        const hits = Math.floor(Math.random() * 100);
        
        data.push({ timestamp, size, hits });
      }
      
      setHeatmapData(data.reverse());
    };

    generateHeatmapData();
    const interval = setInterval(generateHeatmapData, 60000); // Update every minute

    return () => clearInterval(interval);
  }, []);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatNumber = (num: number): string => {
    return new Intl.NumberFormat().format(num);
  };

  const handleOptimize = async () => {
    setIsOptimizing(true);
    try {
      await optimize();
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleClear = async () => {
    if (confirm('Are you sure you want to clear all cache? This action cannot be undone.')) {
      setIsClearing(true);
      try {
        await clear();
      } finally {
        setIsClearing(false);
      }
    }
  };

  const handlePreload = async () => {
    setIsPreloading(true);
    try {
      const resources = [
        { url: '/api/food/classify', priority: 10 },
        { url: '/api/user/preferences', priority: 8 },
        { url: '/api/analytics/stats', priority: 6 }
      ];
      await preloadResources(resources);
    } finally {
      setIsPreloading(false);
    }
  };

  const handleSWStats = async () => {
    try {
      const stats = await getSWStats();
      setSwStats(stats);
    } catch (error) {
      console.error('Failed to get SW stats:', error);
    }
  };

  const handleExport = () => {
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
      console.error('Failed to export cache data:', error);
    }
  };

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      await importCacheData(text);
      setShowImportDialog(false);
    } catch (error) {
      console.error('Failed to import cache data:', error);
      alert('Failed to import cache data. Please check the file format.');
    }
  };

  const getCacheHealthColor = (hitRate: number): string => {
    if (hitRate >= 80) return 'text-green-600';
    if (hitRate >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getCacheHealthIcon = (hitRate: number) => {
    if (hitRate >= 80) return <CheckCircle className="w-4 h-4 text-green-600" />;
    if (hitRate >= 60) return <AlertCircle className="w-4 h-4 text-yellow-600" />;
    return <AlertCircle className="w-4 h-4 text-red-600" />;
  };

  const renderCompact = () => (
    <div className={`flex items-center gap-2 p-2 bg-white rounded-lg border ${className}`}>
      <div className="flex items-center gap-1">
        {state.isOnline ? (
          <Wifi className="w-4 h-4 text-green-500" />
        ) : (
          <WifiOff className="w-4 h-4 text-red-500" />
        )}
        <Database className="w-4 h-4 text-blue-500" />
      </div>
      
      <div className="flex items-center gap-2 text-sm">
        <span className="font-medium">{formatBytes(state.stats.totalSize)}</span>
        <span className={`font-medium ${getCacheHealthColor(state.stats.hitRate)}`}>
          {state.stats.hitRate.toFixed(1)}%
        </span>
      </div>
      
      <button
        onClick={() => setExpanded(!expanded)}
        className="p-1 hover:bg-gray-100 rounded"
      >
        <Settings className="w-4 h-4 text-gray-500" />
      </button>
    </div>
  );

  const renderFull = () => (
    <div className={`bg-white rounded-lg shadow-lg ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-blue-500" />
              <h3 className="text-lg font-semibold">Cache Status</h3>
            </div>
            
            <div className="flex items-center gap-2">
              {getCacheHealthIcon(state.stats.hitRate)}
              <span className={`font-medium ${getCacheHealthColor(state.stats.hitRate)}`}>
                {state.stats.hitRate.toFixed(1)}% hit rate
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {state.isOnline ? (
              <Wifi className="w-4 h-4 text-green-500" />
            ) : (
              <WifiOff className="w-4 h-4 text-red-500" />
            )}
            
            {state.serviceWorkerActive && (
              <div className="w-2 h-2 bg-green-500 rounded-full" title="Service Worker Active" />
            )}
            
            <button
              onClick={refreshStats}
              className="p-1 hover:bg-gray-100 rounded"
              title="Refresh stats"
            >
              <RefreshCw className="w-4 h-4 text-gray-500" />
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex">
          {(['overview', 'analytics', 'management'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {activeTab === 'overview' && (
          <div className="space-y-4">
            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-3 bg-blue-50 rounded-lg">
                <HardDrive className="w-6 h-6 text-blue-500 mx-auto mb-1" />
                <div className="text-2xl font-bold text-blue-900">
                  {formatBytes(state.stats.totalSize)}
                </div>
                <div className="text-xs text-blue-600">Total Size</div>
              </div>
              
              <div className="text-center p-3 bg-green-50 rounded-lg">
                <Database className="w-6 h-6 text-green-500 mx-auto mb-1" />
                <div className="text-2xl font-bold text-green-900">
                  {formatNumber(state.stats.totalEntries)}
                </div>
                <div className="text-xs text-green-600">Entries</div>
              </div>
              
              <div className="text-center p-3 bg-purple-50 rounded-lg">
                <TrendingUp className="w-6 h-6 text-purple-500 mx-auto mb-1" />
                <div className="text-2xl font-bold text-purple-900">
                  {state.stats.hitRate.toFixed(1)}%
                </div>
                <div className="text-xs text-purple-600">Hit Rate</div>
              </div>
              
              <div className="text-center p-3 bg-orange-50 rounded-lg">
                <Zap className="w-6 h-6 text-orange-500 mx-auto mb-1" />
                <div className="text-2xl font-bold text-orange-900">
                  {state.analytics.averageAccessTime.toFixed(1)}ms
                </div>
                <div className="text-xs text-orange-600">Avg Access</div>
              </div>
            </div>

            {/* Priority Distribution */}
            <div>
              <h4 className="font-medium mb-2">Priority Distribution</h4>
              <div className="space-y-2">
                {Object.entries(state.stats.entriesByPriority).map(([priority, count]) => (
                  <div key={priority} className="flex items-center justify-between">
                    <span className="text-sm capitalize">{priority}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-32 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full"
                          style={{
                            width: `${(count / state.stats.totalEntries) * 100}%`
                          }}
                        />
                      </div>
                      <span className="text-sm text-gray-600 w-8">{count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Size by Type */}
            <div>
              <h4 className="font-medium mb-2">Size by Type</h4>
              <div className="space-y-2">
                {Object.entries(state.stats.sizeByType).slice(0, 5).map(([type, size]) => (
                  <div key={type} className="flex items-center justify-between">
                    <span className="text-sm capitalize">{type}</span>
                    <span className="text-sm text-gray-600">{formatBytes(size)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="space-y-4">
            {/* Performance Metrics */}
            <div>
              <h4 className="font-medium mb-2">Performance Metrics</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-500">Cache Hits</div>
                  <div className="text-lg font-semibold">{formatNumber(state.analytics.hits)}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Cache Misses</div>
                  <div className="text-lg font-semibold">{formatNumber(state.analytics.misses)}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Evictions</div>
                  <div className="text-lg font-semibold">{formatNumber(state.analytics.evictions)}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">Compression Savings</div>
                  <div className="text-lg font-semibold">{formatNumber(state.analytics.compressionHits)}</div>
                </div>
              </div>
            </div>

            {/* Hot Keys */}
            <div>
              <h4 className="font-medium mb-2">Hot Keys</h4>
              <div className="space-y-2">
                {state.analytics.hotKeys.slice(0, 5).map((hotKey, index) => (
                  <div key={index} className="flex items-center justify-between text-sm">
                    <span className="font-mono text-gray-600 truncate">{hotKey.key}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-gray-500">{hotKey.accessCount} hits</span>
                      <Clock className="w-3 h-3 text-gray-400" />
                      <span className="text-gray-400">
                        {new Date(hotKey.lastAccessed).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Size History */}
            <div>
              <h4 className="font-medium mb-2">Size History (24h)</h4>
              <div className="h-32 bg-gray-100 rounded-lg p-2">
                <BarChart3 className="w-full h-full text-gray-400" />
                {/* In a real implementation, this would render an actual chart */}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'management' && (
          <div className="space-y-4">
            {/* Quick Actions */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <button
                onClick={handleOptimize}
                disabled={isOptimizing}
                className="flex items-center gap-2 px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${isOptimizing ? 'animate-spin' : ''}`} />
                Optimize
              </button>
              
              <button
                onClick={handlePreload}
                disabled={isPreloading}
                className="flex items-center gap-2 px-3 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
              >
                <Download className={`w-4 h-4 ${isPreloading ? 'animate-spin' : ''}`} />
                Preload
              </button>
              
              <button
                onClick={handleClear}
                disabled={isClearing}
                className="flex items-center gap-2 px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50"
              >
                <Trash2 className={`w-4 h-4 ${isClearing ? 'animate-spin' : ''}`} />
                Clear
              </button>
              
              <button
                onClick={handleExport}
                className="flex items-center gap-2 px-3 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600"
              >
                <Upload className="w-4 h-4" />
                Export
              </button>
              
              <button
                onClick={() => setShowImportDialog(true)}
                className="flex items-center gap-2 px-3 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600"
              >
                <Download className="w-4 h-4" />
                Import
              </button>
              
              <button
                onClick={handleSWStats}
                className="flex items-center gap-2 px-3 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
              >
                <Activity className="w-4 h-4" />
                SW Stats
              </button>
            </div>

            {/* Service Worker Stats */}
            {swStats && (
              <div>
                <h4 className="font-medium mb-2">Service Worker Stats</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-gray-500">Static Cache</div>
                    <div className="font-semibold">{swStats.static || 0} entries</div>
                  </div>
                  <div>
                    <div className="text-gray-500">Dynamic Cache</div>
                    <div className="font-semibold">{swStats.dynamic || 0} entries</div>
                  </div>
                  <div>
                    <div className="text-gray-500">API Cache</div>
                    <div className="font-semibold">{swStats.api || 0} entries</div>
                  </div>
                  <div>
                    <div className="text-gray-500">Uptime</div>
                    <div className="font-semibold">{Math.floor(swStats.uptime / 1000 / 60)}m</div>
                  </div>
                </div>
              </div>
            )}

            {/* Cache Rules */}
            <div>
              <h4 className="font-medium mb-2">Cache Rules</h4>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span>Auto-cleanup</span>
                  <span className="text-green-600">Enabled</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Compression</span>
                  <span className="text-green-600">Enabled</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Background Sync</span>
                  <span className={state.isOnline ? 'text-green-600' : 'text-gray-400'}>
                    {state.isOnline ? 'Active' : 'Offline'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Import Dialog */}
      {showImportDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Import Cache Data</h3>
            <input
              type="file"
              accept=".json"
              onChange={handleImport}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setShowImportDialog(false)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => setShowImportDialog(false)}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                Import
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return compact ? renderCompact() : renderFull();
};

export default CacheStatus;
