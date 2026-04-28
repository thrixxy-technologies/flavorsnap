import { useState, useEffect, useCallback, useRef } from 'react';
import { cacheManager, CacheEntry, CacheStats, CacheAnalytics } from '../utils/cacheManager';

export interface UseCacheOptions {
  enableServiceWorker?: boolean;
  enableBackgroundSync?: boolean;
  enablePreloading?: boolean;
  defaultTTL?: number;
  maxCacheSize?: number;
}

export interface CacheState {
  stats: CacheStats;
  analytics: CacheAnalytics;
  isOnline: boolean;
  serviceWorkerSupported: boolean;
  serviceWorkerActive: boolean;
  preloadQueue: Array<{ url: string; priority: number }>;
  backgroundSyncQueue: Array<{ id: string; data: any; timestamp: number }>;
}

export interface UseCacheReturn {
  // Cache operations
  get: (key: string) => Promise<any>;
  set: (key: string, value: any, options?: {
    ttl?: number;
    priority?: 'low' | 'medium' | 'high' | 'critical';
    tags?: string[];
    metadata?: Record<string, any>;
  }) => Promise<void>;
  delete: (key: string) => Promise<boolean>;
  clear: () => Promise<void>;
  has: (key: string) => boolean;
  
  // Cache management
  invalidateByTag: (tag: string) => Promise<number>;
  invalidateByPattern: (pattern: RegExp) => Promise<number>;
  preloadResources: (resources: Array<{ url: string; priority?: number }>) => Promise<void>;
  warmCache: (patterns: string[]) => Promise<void>;
  optimize: () => Promise<void>;
  
  // Service worker operations
  getSWStats: () => Promise<any>;
  clearSWCache: (cacheName?: string) => Promise<void>;
  preloadSWResources: (resources: string[]) => Promise<void>;
  warmSWCache: (patterns: string[]) => Promise<void>;
  invalidateSWCache: (pattern: string) => Promise<void>;
  
  // State and analytics
  state: CacheState;
  refreshStats: () => void;
  exportCacheData: () => string;
  importCacheData: (data: string) => Promise<void>;
}

const DEFAULT_OPTIONS: UseCacheOptions = {
  enableServiceWorker: true,
  enableBackgroundSync: true,
  enablePreloading: true,
  defaultTTL: 24 * 60 * 60 * 1000, // 24 hours
  maxCacheSize: 50 * 1024 * 1024 // 50MB
};

export const useCache = (options: UseCacheOptions = {}): UseCacheReturn => {
  const mergedOptions = { ...DEFAULT_OPTIONS, ...options };
  const [state, setState] = useState<CacheState>({
    stats: {
      totalEntries: 0,
      totalSize: 0,
      hitRate: 0,
      missRate: 0,
      evictions: 0,
      compressionSavings: 0,
      oldestEntry: 0,
      newestEntry: 0,
      entriesByPriority: {},
      sizeByType: {}
    },
    analytics: {
      hits: 0,
      misses: 0,
      evictions: 0,
      sets: 0,
      gets: 0,
      deletes: 0,
      compressionHits: 0,
      compressionMisses: 0,
      averageAccessTime: 0,
      hotKeys: [],
      sizeHistory: []
    },
    isOnline: navigator.onLine,
    serviceWorkerSupported: 'serviceWorker' in navigator,
    serviceWorkerActive: false,
    preloadQueue: [],
    backgroundSyncQueue: []
  });

  const serviceWorkerRef = useRef<ServiceWorker | null>(null);
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize service worker
  useEffect(() => {
    if (mergedOptions.enableServiceWorker && state.serviceWorkerSupported) {
      registerServiceWorker();
    }

    // Set up online/offline listeners
    const handleOnline = () => {
      setState(prev => ({ ...prev, isOnline: true }));
      if (mergedOptions.enableBackgroundSync) {
        syncBackgroundQueue();
      }
    };

    const handleOffline = () => {
      setState(prev => ({ ...prev, isOnline: false }));
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Set up periodic stats refresh
    refreshIntervalRef.current = setInterval(() => {
      refreshStats();
    }, 5000); // Refresh every 5 seconds

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [mergedOptions.enableServiceWorker, mergedOptions.enableBackgroundSync, state.serviceWorkerSupported]);

  const registerServiceWorker = async () => {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js');
      
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New service worker is available, show update notification
              showUpdateNotification();
            }
          });
        }
      });

      registration.addEventListener('controllerchange', () => {
        window.location.reload();
      });

      // Check if service worker is active
      if (registration.active) {
        serviceWorkerRef.current = registration.active;
        setState(prev => ({ ...prev, serviceWorkerActive: true }));
      }

      // Listen for messages from service worker
      navigator.serviceWorker.addEventListener('message', handleSWMessage);

    } catch (error) {
      console.error('Failed to register service worker:', error);
    }
  };

  const handleSWMessage = (event: MessageEvent) => {
    const { type, data } = event.data;
    
    switch (type) {
      case 'CACHE_UPDATE':
        setState(prev => ({ ...prev, stats: data.stats }));
        break;
      case 'BACKGROUND_SYNC':
        handleBackgroundSync(data);
        break;
      case 'CACHE_INVALIDATED':
        handleCacheInvalidation(data);
        break;
      default:
        console.log('Unknown service worker message:', type, data);
    }
  };

  const showUpdateNotification = () => {
    // In a real implementation, this would show a notification to the user
    console.log('New version available! Please refresh the page.');
  };

  const handleBackgroundSync = (data?: any) => {
    if (data && mergedOptions.enableBackgroundSync) {
      // Handle background sync data
      console.log('Background sync received:', data);
    }
  };

  const handleCacheInvalidation = (data: { pattern: string; count: number }) => {
    console.log(`Cache invalidated: ${data.count} entries matching ${data.pattern}`);
    refreshStats();
  };

  const syncBackgroundQueue = async () => {
    if (state.backgroundSyncQueue.length > 0) {
      try {
        // Sync with service worker
        if (serviceWorkerRef.current) {
          serviceWorkerRef.current.postMessage({
            type: 'BACKGROUND_SYNC',
            payload: { queue: state.backgroundSyncQueue }
          });
        }
        
        setState(prev => ({ ...prev, backgroundSyncQueue: [] }));
      } catch (error) {
        console.error('Failed to sync background queue:', error);
      }
    }
  };

  const refreshStats = useCallback(() => {
    const stats = cacheManager.getStats();
    const analytics = cacheManager.getAnalytics();
    
    setState(prev => ({
      ...prev,
      stats,
      analytics
    }));
  }, []);

  // Cache operations
  const get = useCallback(async (key: string): Promise<any> => {
    try {
      return await cacheManager.get(key);
    } catch (error) {
      console.error('Cache get error:', error);
      return null;
    }
  }, []);

  const set = useCallback(async (
    key: string, 
    value: any, 
    options: {
      ttl?: number;
      priority?: 'low' | 'medium' | 'high' | 'critical';
      tags?: string[];
      metadata?: Record<string, any>;
    } = {}
  ): Promise<void> => {
    try {
      await cacheManager.set(key, value, {
        ttl: options.ttl || mergedOptions.defaultTTL,
        priority: options.priority || 'medium',
        tags: options.tags,
        metadata: options.metadata
      });
      
      refreshStats();
    } catch (error) {
      console.error('Cache set error:', error);
      
      // Add to background sync queue if offline
      if (!state.isOnline && mergedOptions.enableBackgroundSync) {
        setState(prev => ({
          ...prev,
          backgroundSyncQueue: [...prev.backgroundSyncQueue, {
            id: `cache-${Date.now()}`,
            data: { key, value, options },
            timestamp: Date.now()
          }]
        }));
      }
    }
  }, [mergedOptions.defaultTTL, mergedOptions.enableBackgroundSync, state.isOnline]);

  const delete = useCallback(async (key: string): Promise<boolean> => {
    try {
      const result = cacheManager.delete(key);
      refreshStats();
      return result;
    } catch (error) {
      console.error('Cache delete error:', error);
      return false;
    }
  }, [refreshStats]);

  const clear = useCallback(async (): Promise<void> => {
    try {
      cacheManager.clear();
      refreshStats();
    } catch (error) {
      console.error('Cache clear error:', error);
    }
  }, [refreshStats]);

  const has = useCallback((key: string): boolean => {
    return cacheManager.has(key);
  }, []);

  // Cache management
  const invalidateByTag = useCallback(async (tag: string): Promise<number> => {
    try {
      const count = cacheManager.invalidateByTag(tag);
      refreshStats();
      return count;
    } catch (error) {
      console.error('Cache invalidate by tag error:', error);
      return 0;
    }
  }, [refreshStats]);

  const invalidateByPattern = useCallback(async (pattern: RegExp): Promise<number> => {
    try {
      const count = cacheManager.invalidateByPattern(pattern);
      refreshStats();
      return count;
    } catch (error) {
      console.error('Cache invalidate by pattern error:', error);
      return 0;
    }
  }, [refreshStats]);

  const preloadResources = useCallback(async (resources: Array<{ url: string; priority?: number }>): Promise<void> => {
    try {
      const cacheResources = resources.map(r => ({
        key: r.url,
        url: r.url,
        priority: r.priority || 1
      }));
      
      await cacheManager.preloadResources(cacheResources);
      
      // Also preload with service worker if available
      if (serviceWorkerRef.current && mergedOptions.enablePreloading) {
        const urls = resources.map(r => r.url);
        await preloadSWResources(urls);
      }
      
      refreshStats();
    } catch (error) {
      console.error('Preload resources error:', error);
    }
  }, [mergedOptions.enablePreloading]);

  const warmCache = useCallback(async (patterns: string[]): Promise<void> => {
    try {
      await cacheManager.warmCache(patterns);
      
      // Also warm with service worker if available
      if (serviceWorkerRef.current) {
        await warmSWCache(patterns);
      }
      
      refreshStats();
    } catch (error) {
      console.error('Warm cache error:', error);
    }
  }, []);

  const optimize = useCallback(async (): Promise<void> => {
    try {
      await cacheManager.optimize();
      refreshStats();
    } catch (error) {
      console.error('Cache optimize error:', error);
    }
  }, [refreshStats]);

  // Service worker operations
  const getSWStats = useCallback(async (): Promise<any> => {
    if (!serviceWorkerRef.current) {
      return null;
    }
    
    return new Promise((resolve) => {
      const messageChannel = new MessageChannel();
      
      messageChannel.port1.onmessage = (event) => {
        resolve(event.data);
      };
      
      serviceWorkerRef.current!.postMessage({
        type: 'CACHE_STATS'
      }, [messageChannel.port2]);
    });
  }, []);

  const clearSWCache = useCallback(async (cacheName?: string): Promise<void> => {
    if (!serviceWorkerRef.current) {
      return;
    }
    
    return new Promise((resolve, reject) => {
      const messageChannel = new MessageChannel();
      
      messageChannel.port1.onmessage = (event) => {
        if (event.data.success) {
          resolve();
        } else {
          reject(new Error(event.data.error));
        }
      });
      
      serviceWorkerRef.current!.postMessage({
        type: 'CLEAR_CACHE',
        payload: { cacheName }
      }, [messageChannel.port2]);
    });
  }, []);

  const preloadSWResources = useCallback(async (resources: string[]): Promise<void> => {
    if (!serviceWorkerRef.current) {
      return;
    }
    
    return new Promise((resolve, reject) => {
      const messageChannel = new MessageChannel();
      
      messageChannel.port1.onmessage = (event) => {
        if (event.data.success) {
          resolve();
        } else {
          reject(new Error(event.data.error));
        }
      });
      
      serviceWorkerRef.current!.postMessage({
        type: 'PRELOAD_RESOURCES',
        payload: { resources }
      }, [messageChannel.port2]);
    });
  }, []);

  const warmSWCache = useCallback(async (patterns: string[]): Promise<void> => {
    if (!serviceWorkerRef.current) {
      return;
    }
    
    return new Promise((resolve, reject) => {
      const messageChannel = new MessageChannel();
      
      messageChannel.port1.onmessage = (event) => {
        if (event.data.success) {
          resolve();
        } else {
          reject(new Error(event.data.error));
        }
      });
      
      serviceWorkerRef.current!.postMessage({
        type: 'WARM_CACHE',
        payload: { patterns }
      }, [messageChannel.port2]);
    });
  }, []);

  const invalidateSWCache = useCallback(async (pattern: string): Promise<void> => {
    if (!serviceWorkerRef.current) {
      return;
    }
    
    return new Promise((resolve, reject) => {
      const messageChannel = new MessageChannel();
      
      messageChannel.port1.onmessage = (event) => {
        if (event.data.success) {
          resolve();
        } else {
          reject(new Error(event.data.error));
        }
      };
      
      serviceWorkerRef.current!.postMessage({
        type: 'INVALIDATE_CACHE',
        payload: { pattern }
      }, [messageChannel.port2]);
    });
  }, []);

  // Data export/import
  const exportCacheData = useCallback((): string => {
    const data = {
      stats: state.stats,
      analytics: state.analytics,
      timestamp: Date.now(),
      version: '1.0'
    };
    
    return JSON.stringify(data, null, 2);
  }, [state.stats, state.analytics]);

  const importCacheData = useCallback(async (data: string): Promise<void> => {
    try {
      const parsed = JSON.parse(data);
      
      // Validate data structure
      if (!parsed.stats || !parsed.analytics) {
        throw new Error('Invalid cache data format');
      }
      
      // Update state with imported data
      setState(prev => ({
        ...prev,
        stats: { ...prev.stats, ...parsed.stats },
        analytics: { ...prev.analytics, ...parsed.analytics }
      }));
      
    } catch (error) {
      console.error('Failed to import cache data:', error);
      throw error;
    }
  }, []);

  return {
    // Cache operations
    get,
    set,
    delete,
    clear,
    has,
    
    // Cache management
    invalidateByTag,
    invalidateByPattern,
    preloadResources,
    warmCache,
    optimize,
    
    // Service worker operations
    getSWStats,
    clearSWCache,
    preloadSWResources,
    warmSWCache,
    invalidateSWCache,
    
    // State and analytics
    state,
    refreshStats,
    exportCacheData,
    importCacheData
  };
};

export default useCache;
