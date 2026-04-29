export interface CacheEntry {
  key: string;
  value: any;
  timestamp: number;
  expiresAt?: number;
  size: number;
  accessCount: number;
  lastAccessed: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
  tags: string[];
  metadata?: Record<string, any>;
}

export interface CacheConfig {
  maxSize: number; // in bytes
  maxEntries: number;
  defaultTTL: number; // in milliseconds
  cleanupInterval: number; // in milliseconds
  compressionThreshold: number; // in bytes
  enableCompression: boolean;
  enableEncryption: boolean;
  enableAnalytics: boolean;
}

export interface CacheStats {
  totalEntries: number;
  totalSize: number;
  hitRate: number;
  missRate: number;
  evictions: number;
  compressionSavings: number;
  oldestEntry: number;
  newestEntry: number;
  entriesByPriority: Record<string, number>;
  sizeByType: Record<string, number>;
}

export interface CacheAnalytics {
  hits: number;
  misses: number;
  evictions: number;
  sets: number;
  gets: number;
  deletes: number;
  compressionHits: number;
  compressionMisses: number;
  averageAccessTime: number;
  hotKeys: Array<{ key: string; accessCount: number; lastAccessed: number }>;
  sizeHistory: Array<{ timestamp: number; size: number }>;
}

export type CacheStrategy = 'lru' | 'lfu' | 'ttl' | 'priority' | 'adaptive';

export interface CacheInvalidationRule {
  id: string;
  name: string;
  condition: (entry: CacheEntry) => boolean;
  action: 'evict' | 'refresh' | 'compress';
  priority: number;
  enabled: boolean;
}

class CacheManager {
  private static instance: CacheManager;
  private memoryCache: Map<string, CacheEntry> = new Map();
  private diskCache: Map<string, CacheEntry> = new Map();
  private analytics: CacheAnalytics;
  private cleanupTimer?: NodeJS.Timeout;
  private config: CacheConfig;
  private invalidationRules: Map<string, CacheInvalidationRule> = new Map();
  private preloadQueue: Array<{ key: string; url: string; priority: number }> = [];
  private isOnline: boolean = true;

  private constructor() {
    this.analytics = {
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
    };

    this.config = {
      maxSize: 50 * 1024 * 1024, // 50MB
      maxEntries: 1000,
      defaultTTL: 24 * 60 * 60 * 1000, // 24 hours
      cleanupInterval: 60 * 1000, // 1 minute
      compressionThreshold: 1024, // 1KB
      enableCompression: true,
      enableEncryption: false,
      enableAnalytics: true
    };

    this.initializeCache();
    this.setupEventListeners();
  }

  public static getInstance(): CacheManager {
    if (!CacheManager.instance) {
      CacheManager.instance = new CacheManager();
    }
    return CacheManager.instance;
  }

  private initializeCache(): void {
    // Load cache from localStorage if available
    try {
      const savedCache = localStorage.getItem('cache-data');
      if (savedCache) {
        const parsed = JSON.parse(savedCache);
        this.diskCache = new Map(parsed.diskCache || []);
        this.analytics = { ...this.analytics, ...parsed.analytics };
      }
    } catch (error) {
      console.warn('Failed to load cache from localStorage:', error);
    }

    // Start cleanup timer
    this.cleanupTimer = setInterval(() => {
      this.cleanup();
    }, this.config.cleanupInterval);

    // Detect online/offline status
    this.isOnline = navigator.onLine;
  }

  private setupEventListeners(): void {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.syncWithServiceWorker();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
    });

    // Save cache to localStorage periodically
    setInterval(() => {
      this.persistCache();
    }, 5 * 60 * 1000); // Every 5 minutes

    // Save cache on page unload
    window.addEventListener('beforeunload', () => {
      this.persistCache();
    });
  }

  private persistCache(): void {
    try {
      const cacheData = {
        diskCache: Array.from(this.diskCache.entries()),
        analytics: this.analytics
      };
      localStorage.setItem('cache-data', JSON.stringify(cacheData));
    } catch (error) {
      console.warn('Failed to persist cache:', error);
    }
  }

  public async set(
    key: string,
    value: any,
    options: {
      ttl?: number;
      priority?: 'low' | 'medium' | 'high' | 'critical';
      tags?: string[];
      metadata?: Record<string, any>;
      strategy?: CacheStrategy;
    } = {}
  ): Promise<void> {
    const startTime = performance.now();
    
    try {
      const serializedValue = await this.serializeValue(value);
      const size = this.calculateSize(serializedValue);
      const now = Date.now();

      const entry: CacheEntry = {
        key,
        value: serializedValue,
        timestamp: now,
        expiresAt: options.ttl ? now + options.ttl : now + this.config.defaultTTL,
        size,
        accessCount: 0,
        lastAccessed: now,
        priority: options.priority || 'medium',
        tags: options.tags || [],
        metadata: options.metadata
      };

      // Check if we need to make space
      await this.ensureSpace(size);

      // Store in appropriate cache level
      if (this.shouldStoreInMemory(entry)) {
        this.memoryCache.set(key, entry);
      } else {
        this.diskCache.set(key, entry);
      }

      // Update analytics
      this.analytics.sets++;
      this.updateSizeHistory();

      // Apply invalidation rules
      this.applyInvalidationRules(entry);

    } catch (error) {
      console.error('Failed to set cache entry:', error);
      throw error;
    } finally {
      this.updateAverageAccessTime(performance.now() - startTime);
    }
  }

  public async get(key: string): Promise<any | null> {
    const startTime = performance.now();

    try {
      // Check memory cache first
      let entry = this.memoryCache.get(key);
      
      if (!entry) {
        // Check disk cache
        entry = this.diskCache.get(key);
        
        if (entry && this.shouldPromoteToMemory(entry)) {
          this.memoryCache.set(key, entry);
          this.diskCache.delete(key);
        }
      }

      if (!entry) {
        this.analytics.misses++;
        return null;
      }

      // Check expiration
      if (entry.expiresAt && Date.now() > entry.expiresAt) {
        this.delete(key);
        this.analytics.misses++;
        return null;
      }

      // Update access statistics
      entry.accessCount++;
      entry.lastAccessed = Date.now();
      this.analytics.hits++;

      // Update hot keys tracking
      this.updateHotKeys(key, entry);

      // Deserialize and return value
      return await this.deserializeValue(entry.value);

    } catch (error) {
      console.error('Failed to get cache entry:', error);
      this.analytics.misses++;
      return null;
    } finally {
      this.updateAverageAccessTime(performance.now() - startTime);
    }
  }

  public delete(key: string): boolean {
    const memoryDeleted = this.memoryCache.delete(key);
    const diskDeleted = this.diskCache.delete(key);
    
    if (memoryDeleted || diskDeleted) {
      this.analytics.deletes++;
      this.updateSizeHistory();
      return true;
    }
    
    return false;
  }

  public clear(): void {
    this.memoryCache.clear();
    this.diskCache.clear();
    this.analytics = {
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
    };
    this.updateSizeHistory();
  }

  public has(key: string): boolean {
    return this.memoryCache.has(key) || this.diskCache.has(key);
  }

  public getStats(): CacheStats {
    const allEntries = [...this.memoryCache.values(), ...this.diskCache.values()];
    const totalSize = allEntries.reduce((sum, entry) => sum + entry.size, 0);
    const totalRequests = this.analytics.hits + this.analytics.misses;
    const hitRate = totalRequests > 0 ? (this.analytics.hits / totalRequests) * 100 : 0;
    const missRate = totalRequests > 0 ? (this.analytics.misses / totalRequests) * 100 : 0;

    const entriesByPriority = allEntries.reduce((acc, entry) => {
      acc[entry.priority] = (acc[entry.priority] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const sizeByType = allEntries.reduce((acc, entry) => {
      const type = entry.metadata?.type || 'unknown';
      acc[type] = (acc[type] || 0) + entry.size;
      return acc;
    }, {} as Record<string, number>);

    const timestamps = allEntries.map(entry => entry.timestamp);
    const oldestEntry = timestamps.length > 0 ? Math.min(...timestamps) : 0;
    const newestEntry = timestamps.length > 0 ? Math.max(...timestamps) : 0;

    return {
      totalEntries: allEntries.length,
      totalSize,
      hitRate: Math.round(hitRate * 100) / 100,
      missRate: Math.round(missRate * 100) / 100,
      evictions: this.analytics.evictions,
      compressionSavings: this.analytics.compressionHits,
      oldestEntry,
      newestEntry,
      entriesByPriority,
      sizeByType
    };
  }

  public getAnalytics(): CacheAnalytics {
    return { ...this.analytics };
  }

  public updateConfig(newConfig: Partial<CacheConfig>): void {
    this.config = { ...this.config, ...newConfig };
    
    // Restart cleanup timer if interval changed
    if (newConfig.cleanupInterval) {
      if (this.cleanupTimer) {
        clearInterval(this.cleanupTimer);
      }
      this.cleanupTimer = setInterval(() => {
        this.cleanup();
      }, this.config.cleanupInterval);
    }
  }

  public addInvalidationRule(rule: CacheInvalidationRule): void {
    this.invalidationRules.set(rule.id, rule);
  }

  public removeInvalidationRule(ruleId: string): boolean {
    return this.invalidationRules.delete(ruleId);
  }

  public async preloadResources(resources: Array<{ key: string; url: string; priority?: number }>): Promise<void> {
    const sortedResources = resources.sort((a, b) => (b.priority || 0) - (a.priority || 0));
    
    for (const resource of sortedResources) {
      try {
        if (!this.has(resource.key)) {
          const response = await fetch(resource.url);
          if (response.ok) {
            const data = await response.arrayBuffer();
            await this.set(resource.key, data, {
              priority: resource.priority > 8 ? 'critical' : resource.priority > 5 ? 'high' : 'medium',
              tags: ['preloaded'],
              metadata: { type: 'preloaded', url: resource.url }
            });
          }
        }
      } catch (error) {
        console.warn(`Failed to preload resource ${resource.key}:`, error);
      }
    }
  }

  public async warmCache(patterns: string[]): Promise<void> {
    for (const pattern of patterns) {
      try {
        const response = await fetch(pattern);
        if (response.ok) {
          const data = await response.json();
          await this.set(pattern, data, {
            priority: 'medium',
            tags: ['warmed'],
            metadata: { type: 'warmed', pattern }
          });
        }
      } catch (error) {
        console.warn(`Failed to warm cache for pattern ${pattern}:`, error);
      }
    }
  }

  public invalidateByTag(tag: string): number {
    let invalidated = 0;
    
    for (const [key, entry] of this.memoryCache) {
      if (entry.tags.includes(tag)) {
        this.memoryCache.delete(key);
        invalidated++;
      }
    }
    
    for (const [key, entry] of this.diskCache) {
      if (entry.tags.includes(tag)) {
        this.diskCache.delete(key);
        invalidated++;
      }
    }
    
    this.updateSizeHistory();
    return invalidated;
  }

  public invalidateByPattern(pattern: RegExp): number {
    let invalidated = 0;
    const regex = new RegExp(pattern);
    
    for (const [key, entry] of this.memoryCache) {
      if (regex.test(key)) {
        this.memoryCache.delete(key);
        invalidated++;
      }
    }
    
    for (const [key, entry] of this.diskCache) {
      if (regex.test(key)) {
        this.diskCache.delete(key);
        invalidated++;
      }
    }
    
    this.updateSizeHistory();
    return invalidated;
  }

  public getHotKeys(limit: number = 10): Array<{ key: string; accessCount: number; lastAccessed: number }> {
    return this.analytics.hotKeys
      .sort((a, b) => b.accessCount - a.accessCount)
      .slice(0, limit);
  }

  public async optimize(): Promise<void> {
    // Promote frequently accessed items to memory
    const diskEntries = Array.from(this.diskCache.values())
      .sort((a, b) => b.accessCount - a.accessCount)
      .slice(0, Math.floor(this.config.maxEntries * 0.3)); // Top 30%

    for (const entry of diskEntries) {
      if (this.shouldStoreInMemory(entry)) {
        this.memoryCache.set(entry.key, entry);
        this.diskCache.delete(entry.key);
      }
    }

    // Compress large entries
    for (const [key, entry] of this.diskCache) {
      if (entry.size > this.config.compressionThreshold && this.config.enableCompression) {
        try {
          const compressed = await this.compressValue(entry.value);
          entry.value = compressed;
          entry.size = this.calculateSize(compressed);
          this.analytics.compressionHits++;
        } catch (error) {
          this.analytics.compressionMisses++;
        }
      }
    }
  }

  private async ensureSpace(requiredSize: number): Promise<void> {
    const currentSize = this.getCurrentSize();
    
    if (currentSize + requiredSize <= this.config.maxSize) {
      return;
    }

    // Evict entries based on strategy
    const entriesToEvict = this.selectEntriesForEviction(requiredSize);
    
    for (const entry of entriesToEvict) {
      this.memoryCache.delete(entry.key);
      this.diskCache.delete(entry.key);
      this.analytics.evictions++;
    }
  }

  private selectEntriesForEviction(requiredSize: number): CacheEntry[] {
    const allEntries = [...this.memoryCache.values(), ...this.diskCache.values()];
    
    // Sort by priority and last accessed time
    const sorted = allEntries.sort((a, b) => {
      const priorityOrder = { low: 0, medium: 1, high: 2, critical: 3 };
      const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
      if (priorityDiff !== 0) return priorityDiff;
      return a.lastAccessed - b.lastAccessed;
    });

    const entriesToEvict: CacheEntry[] = [];
    let freedSpace = 0;

    for (const entry of sorted) {
      if (freedSpace >= requiredSize) break;
      if (entry.priority === 'critical') continue; // Don't evict critical entries
      
      entriesToEvict.push(entry);
      freedSpace += entry.size;
    }

    return entriesToEvict;
  }

  private cleanup(): void {
    const now = Date.now();
    let cleaned = 0;

    // Clean expired entries
    for (const [key, entry] of this.memoryCache) {
      if (entry.expiresAt && now > entry.expiresAt) {
        this.memoryCache.delete(key);
        cleaned++;
      }
    }

    for (const [key, entry] of this.diskCache) {
      if (entry.expiresAt && now > entry.expiresAt) {
        this.diskCache.delete(key);
        cleaned++;
      }
    }

    // Apply invalidation rules
    for (const rule of this.invalidationRules.values()) {
      if (rule.enabled) {
        for (const [key, entry] of this.memoryCache) {
          if (rule.condition(entry)) {
            if (rule.action === 'evict') {
              this.memoryCache.delete(key);
              cleaned++;
            }
          }
        }
        
        for (const [key, entry] of this.diskCache) {
          if (rule.condition(entry)) {
            if (rule.action === 'evict') {
              this.diskCache.delete(key);
              cleaned++;
            }
          }
        }
      }
    }

    if (cleaned > 0) {
      this.updateSizeHistory();
    }
  }

  private shouldStoreInMemory(entry: CacheEntry): boolean {
    const memorySize = this.getMemorySize();
    return (
      entry.priority === 'critical' ||
      entry.priority === 'high' ||
      (entry.size < this.config.compressionThreshold && memorySize < this.config.maxSize * 0.5)
    );
  }

  private shouldPromoteToMemory(entry: CacheEntry): boolean {
    return (
      entry.accessCount > 5 &&
      entry.priority !== 'low' &&
      (Date.now() - entry.lastAccessed) < 30 * 60 * 1000 // Accessed within last 30 minutes
    );
  }

  private getCurrentSize(): number {
    const memorySize = this.getMemorySize();
    const diskSize = this.getDiskSize();
    return memorySize + diskSize;
  }

  private getMemorySize(): number {
    return Array.from(this.memoryCache.values()).reduce((sum, entry) => sum + entry.size, 0);
  }

  private getDiskSize(): number {
    return Array.from(this.diskCache.values()).reduce((sum, entry) => sum + entry.size, 0);
  }

  private async serializeValue(value: any): Promise<any> {
    if (this.config.enableCompression && this.calculateSize(value) > this.config.compressionThreshold) {
      return await this.compressValue(value);
    }
    return value;
  }

  private async deserializeValue(value: any): Promise<any> {
    // Check if value is compressed
    if (typeof value === 'string' && value.startsWith('compressed:')) {
      return await this.decompressValue(value);
    }
    return value;
  }

  private async compressValue(value: any): Promise<string> {
    // Simple compression simulation - in real implementation use proper compression
    return 'compressed:' + JSON.stringify(value);
  }

  private async decompressValue(compressed: string): Promise<any> {
    // Simple decompression simulation
    const json = compressed.replace('compressed:', '');
    return JSON.parse(json);
  }

  private calculateSize(value: any): number {
    if (typeof value === 'string') {
      return value.length * 2; // UTF-16
    } else if (value instanceof ArrayBuffer) {
      return value.byteLength;
    } else {
      return JSON.stringify(value).length * 2;
    }
  }

  private updateAverageAccessTime(accessTime: number): void {
    const totalOperations = this.analytics.sets + this.analytics.gets;
    this.analytics.averageAccessTime = 
      (this.analytics.averageAccessTime * (totalOperations - 1) + accessTime) / totalOperations;
  }

  private updateHotKeys(key: string, entry: CacheEntry): void {
    const existing = this.analytics.hotKeys.find(hot => hot.key === key);
    if (existing) {
      existing.accessCount = entry.accessCount;
      existing.lastAccessed = entry.lastAccessed;
    } else {
      this.analytics.hotKeys.push({
        key,
        accessCount: entry.accessCount,
        lastAccessed: entry.lastAccessed
      });
    }
    
    // Keep only top 50 hot keys
    this.analytics.hotKeys.sort((a, b) => b.accessCount - a.accessCount);
    this.analytics.hotKeys = this.analytics.hotKeys.slice(0, 50);
  }

  private updateSizeHistory(): void {
    const now = Date.now();
    const size = this.getCurrentSize();
    
    this.analytics.sizeHistory.push({ timestamp: now, size });
    
    // Keep only last 24 hours of history
    const twentyFourHoursAgo = now - (24 * 60 * 60 * 1000);
    this.analytics.sizeHistory = this.analytics.sizeHistory.filter(
      entry => entry.timestamp > twentyFourHoursAgo
    );
  }

  private applyInvalidationRules(entry: CacheEntry): void {
    for (const rule of this.invalidationRules.values()) {
      if (rule.enabled && rule.condition(entry)) {
        // Apply rule action
        switch (rule.action) {
          case 'evict':
            this.delete(entry.key);
            break;
          case 'refresh':
            // Trigger refresh logic
            break;
          case 'compress':
            if (entry.size > this.config.compressionThreshold) {
              this.compressValue(entry.value);
            }
            break;
        }
      }
    }
  }

  private async syncWithServiceWorker(): Promise<void> {
    if ('serviceWorker' in navigator && 'caches' in window) {
      try {
        const cache = await caches.open('flavorsnap-cache');
        const keys = await cache.keys();
        
        for (const request of keys) {
          const response = await cache.match(request);
          if (response) {
            const key = request.url;
            const data = await response.arrayBuffer();
            await this.set(key, data, {
              priority: 'medium',
              tags: ['service-worker'],
              metadata: { type: 'service-worker-sync' }
            });
          }
        }
      } catch (error) {
        console.warn('Failed to sync with service worker:', error);
      }
    }
  }

  public destroy(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
    }
    this.persistCache();
  }
}

export const cacheManager = CacheManager.getInstance();

export default cacheManager;
