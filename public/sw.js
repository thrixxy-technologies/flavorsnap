// Service Worker for Advanced Caching
const CACHE_NAME = 'flavorsnap-cache-v1';
const STATIC_CACHE_NAME = 'flavorsnap-static-v1';
const DYNAMIC_CACHE_NAME = 'flavorsnap-dynamic-v1';
const API_CACHE_NAME = 'flavorsnap-api-v1';

// Cache configuration
const CACHE_CONFIG = {
  maxSize: 100 * 1024 * 1024, // 100MB
  maxEntries: 1000,
  defaultTTL: 24 * 60 * 60 * 1000, // 24 hours
  cleanupInterval: 60 * 60 * 1000, // 1 hour
  enableCompression: true,
  enableAnalytics: true
};

// Cache strategies
const CACHE_STRATEGIES = {
  // Cache first strategy for static assets
  static: 'cache-first',
  // Network first strategy for API calls
  api: 'network-first',
  // Stale while revalidate for dynamic content
  dynamic: 'stale-while-revalidate',
  // Network only for real-time data
  realtime: 'network-only',
  // Cache only for offline fallbacks
  offline: 'cache-only'
};

// Critical resources to cache immediately
const CRITICAL_RESOURCES = [
  '/',
  '/_next/static/css/app.css',
  '/_next/static/chunks/main.js',
  '/_next/static/chunks/webpack.js',
  '/_next/static/chunks/framework.js',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png'
];

// API endpoints to cache
const API_ENDPOINTS = [
  '/api/food/classify',
  '/api/user/preferences',
  '/api/analytics/stats',
  '/api/notifications'
];

// Static assets to cache
const STATIC_ASSETS = [
  /\.(js|css|png|jpg|jpeg|gif|svg|webp|ico)$/,
  /\.(woff|woff2|ttf|eot)$/,
  /\.(mp4|webm|ogg|mp3|wav)$/
];

// Cache analytics
let cacheAnalytics = {
  hits: 0,
  misses: 0,
  evictions: 0,
  networkRequests: 0,
  cachedResponses: 0,
  errors: 0,
  startTime: Date.now()
};

// Install event - cache critical resources
self.addEventListener('install', (event) => {
  console.log('Service Worker: Installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME).then((cache) => {
      console.log('Service Worker: Caching critical resources');
      return cache.addAll(CRITICAL_RESOURCES);
    }).then(() => {
      console.log('Service Worker: Critical resources cached');
      return self.skipWaiting();
    }).catch((error) => {
      console.error('Service Worker: Failed to cache critical resources:', error);
    })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('Service Worker: Activating...');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && 
              cacheName !== STATIC_CACHE_NAME && 
              cacheName !== DYNAMIC_CACHE_NAME && 
              cacheName !== API_CACHE_NAME) {
            console.log('Service Worker: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('Service Worker: Old caches cleaned up');
      return self.clients.claim();
    }).catch((error) => {
      console.error('Service Worker: Failed to clean up old caches:', error);
    })
  );
});

// Fetch event - handle network requests
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-HTTP requests
  if (!request.url.startsWith('http')) {
    return;
  }
  
  // Handle different request types
  if (isStaticAsset(request.url)) {
    event.respondWith(handleStaticRequest(request));
  } else if (isAPIRequest(request.url)) {
    event.respondWith(handleAPIRequest(request));
  } else if (isDynamicContent(request.url)) {
    event.respondWith(handleDynamicRequest(request));
  } else {
    event.respondWith(handleDefaultRequest(request));
  }
  
  // Update analytics
  cacheAnalytics.networkRequests++;
});

// Handle static asset requests (Cache First)
async function handleStaticRequest(request) {
  try {
    const cache = await caches.open(STATIC_CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      cacheAnalytics.hits++;
      
      // Update cache in background
      updateCacheInBackground(request, STATIC_CACHE_NAME);
      
      return cachedResponse;
    }
    
    cacheAnalytics.misses++;
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const responseClone = networkResponse.clone();
      await cache.put(request, responseClone);
    }
    
    return networkResponse;
    
  } catch (error) {
    console.error('Service Worker: Static request failed:', error);
    cacheAnalytics.errors++;
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

// Handle API requests (Network First)
async function handleAPIRequest(request) {
  try {
    const cache = await caches.open(API_CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    try {
      const networkResponse = await fetch(request);
      cacheAnalytics.networkRequests++;
      
      if (networkResponse.ok) {
        const responseClone = networkResponse.clone();
        await cache.put(request, responseClone);
        cacheAnalytics.cachedResponses++;
      }
      
      return networkResponse;
      
    } catch (networkError) {
      // Network failed, try cache
      if (cachedResponse) {
        console.log('Service Worker: Network failed, using cached API response');
        cacheAnalytics.hits++;
        return cachedResponse;
      }
      
      throw networkError;
    }
    
  } catch (error) {
    console.error('Service Worker: API request failed:', error);
    cacheAnalytics.errors++;
    
    // Try to get from cache as fallback
    const cache = await caches.open(API_CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    return new Response('Offline - No cached data available', { 
      status: 503, 
      statusText: 'Service Unavailable' 
    });
  }
}

// Handle dynamic content (Stale While Revalidate)
async function handleDynamicRequest(request) {
  try {
    const cache = await caches.open(DYNAMIC_CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    // Always try network first for dynamic content
    const networkPromise = fetch(request).then((networkResponse) => {
      if (networkResponse.ok) {
        const responseClone = networkResponse.clone();
        cache.put(request, responseClone);
        cacheAnalytics.cachedResponses++;
      }
      return networkResponse;
    }).catch((error) => {
      console.error('Service Worker: Network request failed:', error);
      cacheAnalytics.errors++;
      throw error;
    });
    
    // Return cached response immediately if available
    if (cachedResponse) {
      cacheAnalytics.hits++;
      
      // Update cache in background
      networkPromise.catch(() => {}); // Ignore errors for background update
      
      return cachedResponse;
    }
    
    // No cached response, wait for network
    cacheAnalytics.misses++;
    return await networkPromise;
    
  } catch (error) {
    console.error('Service Worker: Dynamic request failed:', error);
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

// Handle default requests (Network First with Cache Fallback)
async function handleDefaultRequest(request) {
  try {
    const cache = await caches.open(DYNAMIC_CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    try {
      const networkResponse = await fetch(request);
      
      if (networkResponse.ok) {
        const responseClone = networkResponse.clone();
        await cache.put(request, responseClone);
        cacheAnalytics.cachedResponses++;
      }
      
      return networkResponse;
      
    } catch (networkError) {
      if (cachedResponse) {
        console.log('Service Worker: Network failed, using cached response');
        cacheAnalytics.hits++;
        return cachedResponse;
      }
      
      throw networkError;
    }
    
  } catch (error) {
    console.error('Service Worker: Default request failed:', error);
    cacheAnalytics.errors++;
    
    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/offline.html') || new Response('Offline', {
        status: 503,
        statusText: 'Service Unavailable'
      });
    }
    
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

// Update cache in background
async function updateCacheInBackground(request, cacheName) {
  try {
    const cache = await caches.open(cacheName);
    const response = await fetch(request);
    
    if (response.ok) {
      await cache.put(request, response);
    }
  } catch (error) {
    console.log('Service Worker: Background cache update failed:', error);
  }
}

// Helper functions
function isStaticAsset(url) {
  return STATIC_ASSETS.some(pattern => pattern.test(url));
}

function isAPIRequest(url) {
  return API_ENDPOINTS.some(endpoint => url.includes(endpoint));
}

function isDynamicContent(url) {
  return url.includes('/api/') && !isAPIRequest(url);
}

// Message handling for cache management
self.addEventListener('message', (event) => {
  const { type, payload } = event.data;
  
  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
      
    case 'CACHE_STATS':
      event.ports[0].postMessage(getCacheStats());
      break;
      
    case 'CLEAR_CACHE':
      clearCache(payload.cacheName).then(() => {
        event.ports[0].postMessage({ success: true });
      }).catch((error) => {
        event.ports[0].postMessage({ success: false, error: error.message });
      });
      break;
      
    case 'PRELOAD_RESOURCES':
      preloadResources(payload.resources).then(() => {
        event.ports[0].postMessage({ success: true });
      }).catch((error) => {
        event.ports[0].postMessage({ success: false, error: error.message });
      });
      break;
      
    case 'WARM_CACHE':
      warmCache(payload.patterns).then(() => {
        event.ports[0].postMessage({ success: true });
      }).catch((error) => {
        event.ports[0].postMessage({ success: false, error: error.message });
      });
      break;
      
    case 'INVALIDATE_CACHE':
      invalidateCache(payload.pattern).then(() => {
        event.ports[0].postMessage({ success: true });
      }).catch((error) => {
        event.ports[0].postMessage({ success: false, error: error.message });
      });
      break;
      
    default:
      console.warn('Service Worker: Unknown message type:', type);
  }
});

// Get cache statistics
function getCacheStats() {
  return Promise.all([
    caches.open(STATIC_CACHE_NAME).then(cache => cache.keys()),
    caches.open(DYNAMIC_CACHE_NAME).then(cache => cache.keys()),
    caches.open(API_CACHE_NAME).then(cache => cache.keys())
  ]).then(([staticKeys, dynamicKeys, apiKeys]) => {
    return {
      static: staticKeys.length,
      dynamic: dynamicKeys.length,
      api: apiKeys.length,
      total: staticKeys.length + dynamicKeys.length + apiKeys.length,
      analytics: cacheAnalytics,
      uptime: Date.now() - cacheAnalytics.startTime
    };
  });
}

// Clear specific cache
async function clearCache(cacheName) {
  if (cacheName) {
    return caches.delete(cacheName);
  }
  
  // Clear all caches
  const cacheNames = await caches.keys();
  return Promise.all(cacheNames.map(name => caches.delete(name)));
}

// Preload resources
async function preloadResources(resources) {
  const cache = await caches.open(DYNAMIC_CACHE_NAME);
  
  const preloadPromises = resources.map(async (resource) => {
    try {
      const response = await fetch(resource);
      if (response.ok) {
        await cache.put(resource, response);
      }
    } catch (error) {
      console.warn('Failed to preload resource:', resource, error);
    }
  });
  
  return Promise.all(preloadPromises);
}

// Warm cache with patterns
async function warmCache(patterns) {
  const cache = await caches.open(DYNAMIC_CACHE_NAME);
  
  const warmPromises = patterns.map(async (pattern) => {
    try {
      const response = await fetch(pattern);
      if (response.ok) {
        await cache.put(pattern, response);
      }
    } catch (error) {
      console.warn('Failed to warm cache for pattern:', pattern, error);
    }
  });
  
  return Promise.all(warmPromises);
}

// Invalidate cache by pattern
async function invalidateCache(pattern) {
  const cacheNames = await caches.keys();
  const regex = new RegExp(pattern);
  
  const invalidationPromises = cacheNames.map(async (cacheName) => {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    
    const keysToDelete = keys.filter(key => regex.test(key.url));
    
    return Promise.all(keysToDelete.map(key => cache.delete(key)));
  });
  
  return Promise.all(invalidationPromises);
}

// Periodic cache cleanup
setInterval(async () => {
  try {
    console.log('Service Worker: Performing periodic cache cleanup');
    
    // Clean up expired entries
    const cacheNames = await caches.keys();
    
    for (const cacheName of cacheNames) {
      const cache = await caches.open(cacheName);
      const keys = await cache.keys();
      
      // Delete entries older than TTL
      const now = Date.now();
      const keysToDelete = [];
      
      for (const key of keys) {
        const response = await cache.match(key);
        if (response) {
          const cacheTime = response.headers.get('cache-time');
          if (cacheTime) {
            const age = now - parseInt(cacheTime);
            if (age > CACHE_CONFIG.defaultTTL) {
              keysToDelete.push(key);
            }
          }
        }
      }
      
      await Promise.all(keysToDelete.map(key => cache.delete(key)));
      cacheAnalytics.evictions += keysToDelete.length;
    }
    
    console.log('Service Worker: Cache cleanup completed');
  } catch (error) {
    console.error('Service Worker: Cache cleanup failed:', error);
  }
}, CACHE_CONFIG.cleanupInterval);

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

async function doBackgroundSync() {
  try {
    console.log('Service Worker: Performing background sync');
    
    // Sync pending actions
    const pendingActions = await getPendingActions();
    
    for (const action of pendingActions) {
      try {
        await performAction(action);
        await removePendingAction(action.id);
      } catch (error) {
        console.error('Failed to perform action:', action, error);
      }
    }
    
    console.log('Service Worker: Background sync completed');
  } catch (error) {
    console.error('Service Worker: Background sync failed:', error);
  }
}

// Placeholder functions for pending actions
async function getPendingActions() {
  // In a real implementation, this would get pending actions from IndexedDB
  return [];
}

async function removePendingAction(id) {
  // In a real implementation, this would remove the action from IndexedDB
}

async function performAction(action) {
  // In a real implementation, this would perform the action
  return fetch(action.url, {
    method: action.method,
    headers: action.headers,
    body: action.body
  });
}

// Push notification handling
self.addEventListener('push', (event) => {
  if (event.data) {
    const data = event.data.json();
    
    const options = {
      body: data.body,
      icon: '/icons/icon-192x192.png',
      badge: '/icons/icon-96x96.png',
      tag: data.tag,
      data: data.data,
      requireInteraction: data.requireInteraction || false
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  if (event.notification.data && event.notification.data.url) {
    event.waitUntil(
      clients.openWindow(event.notification.data.url)
    );
  }
});

console.log('Service Worker: Loaded and ready');
