// FlavorSnap Service Worker for PWA functionality
const CACHE_NAME = 'flavorsnap-v1';
const STATIC_CACHE_NAME = 'flavorsnap-static-v1';
const IMAGE_CACHE_NAME = 'flavorsnap-images-v1';
const API_CACHE_NAME = 'flavorsnap-api-v1';

// Cache strategy configuration
const CACHE_STRATEGIES = {
  static: {
    cacheName: STATIC_CACHE_NAME,
    maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
    maxEntries: 100
  },
  images: {
    cacheName: IMAGE_CACHE_NAME,
    maxAge: 30 * 24 * 60 * 60 * 1000, // 30 days
    maxEntries: 200
  },
  api: {
    cacheName: API_CACHE_NAME,
    maxAge: 5 * 60 * 1000, // 5 minutes
    maxEntries: 50
  }
};

// Resources to cache on install
const STATIC_RESOURCES = [
  '/',
  '/static/css/main.css',
  '/static/css/charts.css',
  '/static/css/controls.css',
  '/static/css/error.css',
  '/static/css/themes.css',
  '/static/js/charts.js',
  '/static/js/preprocessing.js',
  '/static/js/image_viewer.js',
  '/static/js/keyboard_shortcuts.js',
  '/static/js/progress_tracker.js',
  '/static/js/theme-toggle.js',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// Install event - cache static resources
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker');
  
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching static resources');
        return cache.addAll(STATIC_RESOURCES);
      })
      .then(() => {
        console.log('[SW] Static resources cached successfully');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] Failed to cache static resources:', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== STATIC_CACHE_NAME && 
                cacheName !== IMAGE_CACHE_NAME && 
                cacheName !== API_CACHE_NAME) {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('[SW] Service worker activated');
        return self.clients.claim();
      })
  );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Handle different types of requests
  if (url.origin === self.location.origin) {
    // Same origin requests
    if (url.pathname.startsWith('/static/')) {
      // Static assets - cache first strategy
      event.respondWith(cacheFirst(request, CACHE_STRATEGIES.static));
    } else if (url.pathname.startsWith('/api/')) {
      // API requests - network first strategy with offline fallback
      event.respondWith(networkFirst(request, CACHE_STRATEGIES.api));
    } else {
      // Page requests - network first with offline fallback
      event.respondWith(networkFirst(request, CACHE_STRATEGIES.static));
    }
  } else {
    // Cross-origin requests (images, external APIs)
    if (request.destination === 'image') {
      event.respondWith(cacheFirst(request, CACHE_STRATEGIES.images));
    } else {
      // Let browser handle other cross-origin requests
      return;
    }
  }
});

// Cache First strategy
async function cacheFirst(request, strategy) {
  try {
    const cache = await caches.open(strategy.cacheName);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      // Return cached response and update in background
      updateCacheInBackground(request, cache);
      return cachedResponse;
    }
    
    // Not in cache, fetch from network
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      // Cache the response
      const responseToCache = networkResponse.clone();
      await cache.put(request, responseToCache);
    }
    
    return networkResponse;
  } catch (error) {
    console.error('[SW] Cache First strategy failed:', error);
    return createOfflineResponse(request);
  }
}

// Network First strategy
async function networkFirst(request, strategy) {
  try {
    const cache = await caches.open(strategy.cacheName);
    
    try {
      // Try network first
      const networkResponse = await fetch(request);
      
      if (networkResponse.ok) {
        // Cache the response
        const responseToCache = networkResponse.clone();
        await cache.put(request, responseToCache);
      }
      
      return networkResponse;
    } catch (networkError) {
      // Network failed, try cache
      console.log('[SW] Network failed, trying cache:', networkError);
      const cachedResponse = await cache.match(request);
      
      if (cachedResponse) {
        return cachedResponse;
      }
      
      // Nothing in cache, return offline response
      return createOfflineResponse(request);
    }
  } catch (error) {
    console.error('[SW] Network First strategy failed:', error);
    return createOfflineResponse(request);
  }
}

// Update cache in background
async function updateCacheInBackground(request, cache) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      await cache.put(request, networkResponse);
    }
  } catch (error) {
    console.log('[SW] Background update failed:', error);
  }
}

// Create offline response
function createOfflineResponse(request) {
  const url = new URL(request.url);
  
  if (request.destination === 'image') {
    // Return a placeholder image for image requests
    return new Response(
      '<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#f0f0f0"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="#666">Offline</text></svg>',
      {
        headers: { 'Content-Type': 'image/svg+xml' }
      }
    );
  } else if (url.pathname.startsWith('/api/')) {
    // Return offline API response
    return new Response(
      JSON.stringify({
        error: 'Offline',
        message: 'No internet connection. Please check your connection and try again.',
        offline: true
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  } else {
    // Return offline page for navigation requests
    return new Response(
      `
      <!DOCTYPE html>
      <html>
      <head>
        <title>FlavorSnap - Offline</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
          body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
          .offline-container { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
          .icon { font-size: 48px; margin-bottom: 20px; }
          h1 { color: #333; margin-bottom: 10px; }
          p { color: #666; line-height: 1.6; }
          .retry-btn { background: #2196F3; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-top: 20px; }
        </style>
      </head>
      <body>
        <div class="offline-container">
          <div class="icon">📱</div>
          <h1>You're Offline</h1>
          <p>FlavorSnap is currently unavailable because you're not connected to the internet.</p>
          <p>Some features may still work with cached data.</p>
          <button class="retry-btn" onclick="window.location.reload()">Retry</button>
        </div>
      </body>
      </html>
      `,
      {
        status: 503,
        headers: { 'Content-Type': 'text/html' }
      }
    );
  }
}

// Background sync for queued operations
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync event:', event.tag);
  
  if (event.tag === 'background-sync-classifications') {
    event.waitUntil(syncClassifications());
  }
});

// Sync queued classifications
async function syncClassifications() {
  try {
    const cache = await caches.open(API_CACHE_NAME);
    const queuedRequests = await cache.keys();
    
    for (const request of queuedRequests) {
      if (request.url.includes('/api/classify')) {
        try {
          const response = await fetch(request);
          if (response.ok) {
            await cache.delete(request);
            console.log('[SW] Synced classification request');
          }
        } catch (error) {
          console.log('[SW] Failed to sync classification request:', error);
        }
      }
    }
  } catch (error) {
    console.error('[SW] Background sync failed:', error);
  }
}

// Push notification handling
self.addEventListener('push', (event) => {
  console.log('[SW] Push event received');
  
  const options = {
    body: event.data ? event.data.text() : 'FlavorSnap notification',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/icon-96x96.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'Open FlavorSnap',
        icon: '/static/icons/icon-96x96.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('FlavorSnap', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification click received');
  
  event.notification.close();
  
  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/')
    );
  } else {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Message handling for cache management
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_UPDATE') {
    updateCache(event.data.url);
  }
});

// Update specific cache
async function updateCache(url) {
  try {
    const cache = await caches.open(STATIC_CACHE_NAME);
    const response = await fetch(url);
    if (response.ok) {
      await cache.put(url, response);
      console.log('[SW] Cache updated for:', url);
    }
  } catch (error) {
    console.error('[SW] Failed to update cache:', error);
  }
}

console.log('[SW] FlavorSnap Service Worker loaded');
