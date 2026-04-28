export interface ClassificationCache {
  id: number;
  timestamp: string;
  food: string;
  confidence: number;
  calories?: number;
  imageUrl?: string;
  cachedAt: string;
}

export interface OfflineStore {
  classifications: ClassificationCache[];
  lastSync?: string;
}

const OFFLINE_STORE_KEY = 'flavorsnap-offline-store';
const MAX_OFFLINE_ITEMS = 50;
const CACHE_EXPIRY_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

export interface PushSubscriptionOptions {
  userVisibleOnly: boolean;
  applicationServerKey?: ArrayBuffer | string;
}

export interface PerformanceMetrics {
  cacheHits: number;
  cacheMisses: number;
  networkRequests: number;
  offlineRequests: number;
  averageResponseTime: number;
  totalResponseTime: number;
  requestCount: number;
}

export interface OfflineAnalytics {
  type: string;
  timestamp: number;
  data?: any;
}

export interface CacheStrategy {
  name: string;
  pattern: RegExp;
  strategy: 'cache-first' | 'network-first' | 'stale-while-revalidate';
  maxAge: number;
  maxEntries: number;
}

export class PWAManager {
  private static instance: PWAManager;
  private deferredPrompt: BeforeInstallPromptEvent | null = null;
  private swRegistration: ServiceWorkerRegistration | null = null;
  private isInstalled: boolean = false;
  private offlineStore: OfflineStore = { classifications: [] };

  static getInstance(): PWAManager {
    if (!PWAManager.instance) {
      PWAManager.instance = new PWAManager();
    }
    return PWAManager.instance;
  }

  private constructor() {
    this.initializeServiceWorker();
    this.setupInstallPrompt();
    this.loadOfflineStore();
  }

  private loadOfflineStore() {
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(OFFLINE_STORE_KEY);
        if (stored) {
          this.offlineStore = JSON.parse(stored);
          // Clean expired entries
          this.cleanExpiredCache();
        }
      } catch (error) {
        console.error('Failed to load offline store:', error);
      }
    }
  }

  private saveOfflineStore() {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(OFFLINE_STORE_KEY, JSON.stringify(this.offlineStore));
      } catch (error) {
        console.error('Failed to save offline store:', error);
      }
    }
  }

  private cleanExpiredCache() {
    const now = Date.now();
    this.offlineStore.classifications = this.offlineStore.classifications.filter(
      item => now - new Date(item.cachedAt).getTime() < CACHE_EXPIRY_MS
    );
    this.saveOfflineStore();
  }

  private async initializeServiceWorker() {
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js', {
          scope: '/'
        });
        
        this.swRegistration = registration;
        console.log('Service Worker registered successfully:', registration);
        
        // Check for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                // New version available
                this.notifyUpdateAvailable();
              }
            });
          }
        });

        // Handle controller change (new service worker activated)
        navigator.serviceWorker.addEventListener('controllerchange', () => {
          console.log('Service Worker controller changed, reloading page');
          window.location.reload();
        });

      } catch (error) {
        console.error('Service Worker registration failed:', error);
      }
    }
  }

  private setupInstallPrompt() {
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        this.deferredPrompt = e as BeforeInstallPromptEvent;
        console.log('Install prompt ready');
      });

      window.addEventListener('appinstalled', () => {
        this.isInstalled = true;
        this.deferredPrompt = null;
        console.log('PWA installed successfully');
        this.trackInstallation();
      });
    }
  }

  // Check if app is running in standalone mode
  isStandalone(): boolean {
    if (typeof window === 'undefined') return false;
    
    return (
      window.matchMedia('(display-mode: standalone)').matches ||
      (window.navigator as any).standalone ||
      document.referrer.includes('android-app://')
    );
  }

  // Check if install prompt is available
  canInstall(): boolean {
    return this.deferredPrompt !== null && !this.isInstalled;
  }

  // Show install prompt
  async showInstallPrompt(): Promise<boolean> {
    if (!this.deferredPrompt) {
      console.log('Install prompt not available');
      return false;
    }

    try {
      await this.deferredPrompt.prompt();
      const { outcome } = await this.deferredPrompt.userChoice;
      
      console.log(`Install prompt ${outcome}`);
      this.deferredPrompt = null;
      
      return outcome === 'accepted';
    } catch (error) {
      console.error('Error showing install prompt:', error);
      return false;
    }
  }

  // Request notification permission
  async requestNotificationPermission(): Promise<NotificationPermission> {
    if (!('Notification' in window)) {
      console.log('This browser does not support notifications');
      return 'denied';
    }

    if (Notification.permission === 'granted') {
      return 'granted';
    }

    if (Notification.permission === 'denied') {
      return 'denied';
    }

    try {
      const permission = await Notification.requestPermission();
      console.log('Notification permission:', permission);
      return permission;
    } catch (error) {
      console.error('Error requesting notification permission:', error);
      return 'denied';
    }
  }

  // Subscribe to push notifications
  async subscribeToPushNotifications(
    publicVapidKey?: string
  ): Promise<PushSubscription | null> {
    if (!this.swRegistration) {
      console.log('Service Worker not registered');
      return null;
    }

    const permission = await this.requestNotificationPermission();
    if (permission !== 'granted') {
      console.log('Notification permission not granted');
      return null;
    }

    try {
      const subscription = await this.swRegistration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: publicVapidKey ? this.urlBase64ToUint8Array(publicVapidKey) as unknown as BufferSource : undefined
      });

      console.log('Push subscription successful:', subscription);
      return subscription;
    } catch (error) {
      console.error('Push subscription failed:', error);
      return null;
    }
  }

  // Unsubscribe from push notifications
  async unsubscribeFromPushNotifications(): Promise<boolean> {
    if (!this.swRegistration) {
      return false;
    }

    try {
      const subscription = await this.swRegistration.pushManager.getSubscription();
      if (subscription) {
        await subscription.unsubscribe();
        console.log('Unsubscribed from push notifications');
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error unsubscribing from push notifications:', error);
      return false;
    }
  }

  // Show local notification
  async showLocalNotification(
    title: string,
    options: NotificationOptions = {}
  ): Promise<void> {
    const permission = await this.requestNotificationPermission();
    if (permission !== 'granted') {
      console.log('Notification permission not granted');
      return;
    }

    if (this.swRegistration) {
      await this.swRegistration.showNotification(title, {
        icon: '/icons/icon-192x192.png',
        badge: '/icons/icon-72x72.png',
        ...options
      });
    } else {
      new Notification(title, {
        icon: '/icons/icon-192x192.png',
        badge: '/icons/icon-72x72.png',
        ...options
      });
    }
  }

  // Check for updates
  async checkForUpdates(): Promise<boolean> {
    if (!this.swRegistration) {
      return false;
    }

    try {
      await this.swRegistration.update();
      return true;
    } catch (error) {
      console.error('Error checking for updates:', error);
      return false;
    }
  }

  // Get current push subscription
  async getPushSubscription(): Promise<PushSubscription | null> {
    if (!this.swRegistration) {
      return null;
    }

    try {
      return await this.swRegistration.pushManager.getSubscription();
    } catch (error) {
      console.error('Error getting push subscription:', error);
      return null;
    }
  }

  // Register background sync
  async registerBackgroundSync(tag: string): Promise<boolean> {
    if (!this.swRegistration || !('sync' in this.swRegistration)) {
      console.log('Background sync not supported');
      return false;
    }

    try {
      await (this.swRegistration.sync as any).register(tag);
      console.log(`Background sync registered: ${tag}`);
      return true;
    } catch (error: unknown) {
      console.error('Error registering background sync:', error);
      return false;
    }
  }

  // Utility method to convert VAPID key
  private urlBase64ToUint8Array(base64String: string): Uint8Array {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  // Notify user about update availability
  private notifyUpdateAvailable() {
    if (typeof window !== 'undefined') {
      // You can show a custom UI here
      console.log('New version available!');
      
      // Show a simple notification
      this.showLocalNotification('Update Available', {
        body: 'A new version of FlavorSnap is available. Click to update.',
        requireInteraction: true
      });
    }
  }

  // Track installation for analytics
  private trackInstallation() {
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'pwa_installed', {
        event_category: 'PWA',
        event_label: 'FlavorSnap Installed'
      });
    }
  }

  // Get PWA installation status
  getInstallationStatus(): {
    isInstalled: boolean;
    isStandalone: boolean;
    canInstall: boolean;
  } {
    return {
      isInstalled: this.isInstalled,
      isStandalone: this.isStandalone(),
      canInstall: this.canInstall()
    };
  }

  // Offline classification caching
  async cacheClassification(classification: ClassificationCache): Promise<void> {
    try {
      // Add to offline store
      this.offlineStore.classifications.unshift(classification);
      
      // Limit cache size
      if (this.offlineStore.classifications.length > MAX_OFFLINE_ITEMS) {
        this.offlineStore.classifications = this.offlineStore.classifications.slice(0, MAX_OFFLINE_ITEMS);
      }
      
      this.saveOfflineStore();
      
      // Also cache in IndexedDB for larger storage
      await this.cacheInIndexedDB(classification);
      
      console.log('[PWA] Classification cached for offline access');
    } catch (error) {
      console.error('[PWA] Failed to cache classification:', error);
    }
  }

  // Get cached classifications
  getCachedClassifications(): ClassificationCache[] {
    return this.offlineStore.classifications;
  }

  // Get single cached classification by ID
  getCachedClassification(id: number): ClassificationCache | undefined {
    return this.offlineStore.classifications.find(c => c.id === id);
  }

  // Clear classification cache
  clearClassificationCache(): void {
    this.offlineStore.classifications = [];
    this.saveOfflineStore();
    this.clearIndexedDBCache();
    console.log('[PWA] Classification cache cleared');
  }

  // Check if online
  async isOnline(): Promise<boolean> {
    if (typeof window === 'undefined') return false;
    
    const online = navigator.onLine;
    if (!online) return false;
    
    // Additional check - try to reach the server
    try {
      const response = await fetch('/api/health', { 
        method: 'HEAD',
        cache: 'no-cache'
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  // Sync cached classifications when back online
  async syncCachedClassifications(syncFn?: (classifications: ClassificationCache[]) => Promise<void>): Promise<number> {
    const isOnline = await this.isOnline();
    if (!isOnline) {
      console.log('[PWA] Still offline, skipping sync');
      return 0;
    }

    const cached = this.getCachedClassifications();
    if (cached.length === 0) {
      console.log('[PWA] No cached classifications to sync');
      return 0;
    }

    try {
      if (syncFn) {
        await syncFn(cached);
      }
      
      // Update last sync time
      this.offlineStore.lastSync = new Date().toISOString();
      this.saveOfflineStore();
      
      console.log(`[PWA] Synced ${cached.length} classifications`);
      return cached.length;
    } catch (error) {
      console.error('[PWA] Sync failed:', error);
      return 0;
    }
  }

  // IndexedDB caching for larger storage
  private async cacheInIndexedDB(classification: ClassificationCache): Promise<void> {
    if (typeof indexedDB === 'undefined') return;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open('FlavorSnapDB', 1);
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const db = request.result;
        const transaction = db.transaction(['classifications'], 'readwrite');
        const store = transaction.objectStore('classifications');
        
        const putRequest = store.put(classification);
        putRequest.onsuccess = () => resolve();
        putRequest.onerror = () => reject(putRequest.error);
      };
      
      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains('classifications')) {
          db.createObjectStore('classifications', { keyPath: 'id' });
        }
      };
    });
  }

  private async clearIndexedDBCache(): Promise<void> {
    if (typeof indexedDB === 'undefined') return;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open('FlavorSnapDB', 1);
      
      request.onsuccess = () => {
        const db = request.result;
        const transaction = db.transaction(['classifications'], 'readwrite');
        const store = transaction.objectStore('classifications');
        
        const clearRequest = store.clear();
        clearRequest.onsuccess = () => resolve();
        clearRequest.onerror = () => reject(clearRequest.error);
      };
      
      request.onerror = () => reject(request.error);
    });
  }

  private async getAllFromIndexedDB(): Promise<ClassificationCache[]> {
    if (typeof indexedDB === 'undefined') return [];

    return new Promise((resolve, reject) => {
      const request = indexedDB.open('FlavorSnapDB', 1);
      
      request.onsuccess = () => {
        const db = request.result;
        const transaction = db.transaction(['classifications'], 'readonly');
        const store = transaction.objectStore('classifications');
        
        const getAllRequest = store.getAll();
        getAllRequest.onsuccess = () => resolve(getAllRequest.result);
        getAllRequest.onerror = () => reject(getAllRequest.error);
      };
      
      request.onerror = () => reject(request.error);
    });
  }
}

export const pwaManager = PWAManager.getInstance();
