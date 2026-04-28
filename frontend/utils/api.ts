import { ApiErrorResponse } from "../types";

// Input sanitization utilities for frontend
class InputSanitizer {
  /**
   * Sanitize string input to prevent XSS attacks
   */
  static sanitizeString(text: string, maxLength: number = 1000): string {
    if (!text || typeof text !== 'string') return '';

    // Remove null bytes and control characters
    text = text.replace(/\x00/g, '').replace(/\r/g, '').replace(/\n/g, ' ');

    // Remove HTML tags (basic XSS protection)
    text = text.replace(/<[^>]*>/g, '');

    // Remove dangerous protocols
    text = text.replace(/(javascript|vbscript|data|file):/gi, '');

    // Remove potential script injection patterns
    text = text.replace(/<script[^>]*>.*?<\/script>/gi, '');
    text = text.replace(/on\w+\s*=/gi, '');

    // Remove SQL injection patterns
    text = text.replace(/\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b/gi, '');

    // Remove command injection patterns
    text = text.replace(/[;&|`$()<>]/g, '');

    return text.substring(0, maxLength).trim();
  }

  /**
   * Sanitize filename for file uploads
   */
  static sanitizeFilename(filename: string): string {
    if (!filename || typeof filename !== 'string') return '';

    // Remove path traversal attempts
    filename = filename.replace(/.*[/\\]/, '');

    // Remove dangerous characters
    filename = filename.replace(/[<>:"/\\|?*\x00-\x1f]/g, '');

    // Limit length
    return filename.substring(0, 255);
  }

  /**
   * Sanitize email input
   */
  static sanitizeEmail(email: string): string {
    if (!email || typeof email !== 'string') return '';

    // Basic email validation and sanitization
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!emailRegex.test(email)) return '';

    return email.toLowerCase().substring(0, 254);
  }

  /**
   * Sanitize URL input
   */
  static sanitizeUrl(url: string): string {
    if (!url || typeof url !== 'string') return '';

    // Remove dangerous protocols
    url = url.replace(/(javascript|vbscript|data|file):/gi, '');

    // Basic URL validation
    if (!/^https?:\/\//.test(url)) return '';

    return url.substring(0, 2000);
  }

  /**
   * Sanitize numeric input within bounds
   */
  static sanitizeNumber(value: any, min: number = -1000000, max: number = 1000000): number | null {
    const num = typeof value === 'string' ? parseFloat(value) : Number(value);
    if (isNaN(num) || !isFinite(num)) return null;
    return Math.max(min, Math.min(max, num));
  }

  /**
   * Sanitize boolean input
   */
  static sanitizeBoolean(value: any): boolean {
    return Boolean(value);
  }

  /**
   * Sanitize object/array data recursively
   */
  static sanitizeObject(data: any, maxDepth: number = 5, currentDepth: number = 0): any {
    if (currentDepth >= maxDepth) return null;

    if (typeof data === 'string') {
      return this.sanitizeString(data);
    }

    if (typeof data === 'number') {
      return this.sanitizeNumber(data);
    }

    if (typeof data === 'boolean') {
      return data;
    }

    if (Array.isArray(data)) {
      return data.slice(0, 100).map(item => this.sanitizeObject(item, maxDepth, currentDepth + 1));
    }

    if (data && typeof data === 'object') {
      const sanitized: any = {};
      for (const [key, value] of Object.entries(data)) {
        const sanitizedKey = this.sanitizeString(key, 100);
        if (sanitizedKey) {
          sanitized[sanitizedKey] = this.sanitizeObject(value, maxDepth, currentDepth + 1);
        }
      }
      return sanitized;
    }

    return null; // Skip unsupported types
  }

  /**
   * Validate file before upload
   */
  static validateFile(file: File): { valid: boolean; error?: string } {
    // Check file size (10MB limit)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      return { valid: false, error: `File size exceeds ${maxSize / (1024 * 1024)}MB limit` };
    }

    // Check file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      return { valid: false, error: 'Unsupported file type. Allowed: JPG, PNG, WebP' };
    }

    // Sanitize filename
    const sanitizedName = this.sanitizeFilename(file.name);
    if (!sanitizedName) {
      return { valid: false, error: 'Invalid filename' };
    }

    return { valid: true };
  }
}

interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status: number;
  progress?: number; // Progress percentage (0-100)
  cached?: boolean; // Whether response came from cache
}

interface ApiOptions extends RequestInit {
  retries?: number;
  retryDelay?: number;
  skipCache?: boolean; // Skip cache for this request
}

interface CacheEntry<T = any> {
  data: T;
  timestamp: number;
  ttl: number;
}

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: ApiErrorResponse,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Cache configuration
const CACHE_CONFIG = {
  defaultTTL: 60 * 60 * 1000, // 1 hour in milliseconds
  maxEntries: 100, // Maximum cache entries
  storageKey: 'flavorsnap_api_cache',
};

// In-memory cache for faster access
let memoryCache: Map<string, CacheEntry> = new Map();

// Load cache from localStorage on module load
const loadCacheFromStorage = () => {
  try {
    const stored = localStorage.getItem(CACHE_CONFIG.storageKey);
    if (stored) {
      const parsed = JSON.parse(stored);
      memoryCache = new Map(Object.entries(parsed));
      // Clean expired entries
      cleanExpiredCache();
    }
  } catch (error) {
    console.warn('Failed to load cache from localStorage:', error);
  }
};

// Save cache to localStorage
const saveCacheToStorage = () => {
  try {
    const cacheObject = Object.fromEntries(memoryCache);
    localStorage.setItem(CACHE_CONFIG.storageKey, JSON.stringify(cacheObject));
  } catch (error) {
    console.warn('Failed to save cache to localStorage:', error);
  }
};

// Clean expired cache entries
const cleanExpiredCache = () => {
  const now = Date.now();
  const expiredKeys: string[] = [];

  for (const [key, entry] of memoryCache.entries()) {
    if (now > entry.timestamp + entry.ttl) {
      expiredKeys.push(key);
    }
  }

  expiredKeys.forEach(key => memoryCache.delete(key));

  if (expiredKeys.length > 0) {
    console.log(`Cleaned ${expiredKeys.length} expired cache entries`);
    saveCacheToStorage();
  }
};

// Generate cache key from image data
const generateCacheKey = (imageData: ArrayBuffer | string): string => {
  if (typeof imageData === 'string') {
    // If it's already a hash, use it directly
    return `img_${imageData}`;
  }

  // Generate hash from ArrayBuffer
  const hashBuffer = crypto.subtle.digestSync('SHA-256', imageData);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return `img_${hashHex}`;
};

// Get cached response
const getCachedResponse = <T>(cacheKey: string): ApiResponse<T> | null => {
  const entry = memoryCache.get(cacheKey);
  if (!entry) return null;

  const now = Date.now();
  if (now > entry.timestamp + entry.ttl) {
    memoryCache.delete(cacheKey);
    saveCacheToStorage();
    return null;
  }

  console.log(`Cache hit for key: ${cacheKey.substring(0, 12)}...`);
  return {
    data: entry.data,
    status: 200,
    cached: true
  };
};

// Cache response
const cacheResponse = <T>(cacheKey: string, data: T, ttl?: number) => {
  const entry: CacheEntry<T> = {
    data,
    timestamp: Date.now(),
    ttl: ttl || CACHE_CONFIG.defaultTTL
  };

  // Enforce max entries limit (simple LRU-like behavior)
  if (memoryCache.size >= CACHE_CONFIG.maxEntries) {
    const firstKey = memoryCache.keys().next().value;
    memoryCache.delete(firstKey);
  }

  memoryCache.set(cacheKey, entry);
  saveCacheToStorage();
  console.log(`Cached response for key: ${cacheKey.substring(0, 12)}...`);
};

// Initialize cache
loadCacheFromStorage();

// Clean cache periodically
setInterval(cleanExpiredCache, 5 * 60 * 1000); // Every 5 minutes

const apiRequest = async <T = any>(
  url: string,
  options: ApiOptions = {},
  onProgress?: (progress: number, status?: string) => void, // Progress callback with status
): Promise<ApiResponse<T>> => {
  const { retries = 3, retryDelay = 1000, skipCache = false, ...fetchOptions } = options;

  let lastError: Error | null = null;

  // Check cache for prediction requests with image data
  if (!skipCache && url.includes('/predict') && fetchOptions.body instanceof FormData) {
    try {
      // Extract image data from FormData for hashing
      const imageFile = fetchOptions.body.get('image') as File;
      if (imageFile) {
        const imageData = await imageFile.arrayBuffer();
        const cacheKey = generateCacheKey(imageData);

        // Check for cached response
        const cachedResponse = getCachedResponse<T>(cacheKey);
        if (cachedResponse) {
          if (onProgress) onProgress(100, 'cached');
          return cachedResponse;
        }
      }
    } catch (error) {
      console.warn('Cache check failed:', error);
    }
  }

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const isFormData = typeof FormData !== "undefined" && fetchOptions.body instanceof FormData;
      const defaultHeaders: Record<string, string> = isFormData ? {} : { "Content-Type": "application/json" };

      // Sanitize data before sending
      let sanitizedBody = fetchOptions.body;
      if (!isFormData && fetchOptions.body) {
        if (typeof fetchOptions.body === 'string') {
          try {
            const parsedData = JSON.parse(fetchOptions.body);
            const sanitizedData = InputSanitizer.sanitizeObject(parsedData);
            sanitizedBody = JSON.stringify(sanitizedData);
          } catch {
            // If not valid JSON, sanitize as string
            sanitizedBody = InputSanitizer.sanitizeString(fetchOptions.body);
          }
        } else if (typeof fetchOptions.body === 'object') {
          const sanitizedData = InputSanitizer.sanitizeObject(fetchOptions.body);
          sanitizedBody = JSON.stringify(sanitizedData);
        }
      } else if (isFormData && fetchOptions.body instanceof FormData) {
        // Sanitize FormData entries
        const sanitizedFormData = new FormData();
        for (const [key, value] of (fetchOptions.body as FormData).entries()) {
          const sanitizedKey = InputSanitizer.sanitizeString(key, 100);
          if (value instanceof File) {
            // Validate file
            const validation = InputSanitizer.validateFile(value);
            if (!validation.valid) {
              throw new Error(validation.error);
            }
            // Create new file with sanitized name
            const sanitizedFile = new File([value], InputSanitizer.sanitizeFilename(value.name), {
              type: value.type,
              lastModified: value.lastModified
            });
            sanitizedFormData.append(sanitizedKey, sanitizedFile);
          } else if (typeof value === 'string') {
            sanitizedFormData.append(sanitizedKey, InputSanitizer.sanitizeString(value));
          } else {
            sanitizedFormData.append(sanitizedKey, value);
          }
        }
        sanitizedBody = sanitizedFormData;
      }

      // Sanitize URL
      const sanitizedUrl = InputSanitizer.sanitizeUrl(url);
      if (!sanitizedUrl) {
        throw new Error('Invalid URL');
      }

      // Track upload progress for FormData
      if (isFormData && onProgress && sanitizedBody instanceof FormData) {
        const xhr = new XMLHttpRequest();

        return new Promise((resolve, reject) => {
          xhr.open(fetchOptions.method || 'POST', url);

          // Set headers
          Object.entries(defaultHeaders).forEach(([key, value]) => {
            if (value) xhr.setRequestHeader(key, value);
          });

          // Progress tracking
          xhr.upload.addEventListener('loadstart', () => {
            onProgress(0, 'starting');
          });

          xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable && onProgress) {
              const progress = Math.round((e.loaded / e.total) * 100);
              onProgress(progress, progress < 100 ? 'uploading' : 'processing');
            }
          });

          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              onProgress(100, 'complete');
              try {
                const data = JSON.parse(xhr.responseText);

                // Cache successful prediction responses
                if (url.includes('/predict') && fetchOptions.body instanceof FormData) {
                  try {
                    const imageFile = fetchOptions.body.get('image') as File;
                    if (imageFile) {
                      imageFile.arrayBuffer().then(imageData => {
                        const cacheKey = generateCacheKey(imageData);
                        cacheResponse(cacheKey, data);
                      });
                    }
                  } catch (cacheError) {
                    console.warn('Failed to cache response:', cacheError);
                  }
                }

                resolve({ data, status: xhr.status, cached: false });
              } catch {
                resolve({ data: undefined, status: xhr.status, cached: false });
              }
            } else {
              try {
                const data = JSON.parse(xhr.responseText);
                reject(new ApiError(data.error || `HTTP ${xhr.status}`, xhr.status, data));
              } catch {
                reject(new ApiError(`HTTP ${xhr.status}`, xhr.status));
              }
            }
          };

          xhr.onerror = () => reject(new ApiError('Network error', 0));

          // Send FormData directly
          xhr.send(fetchOptions.body as XMLHttpRequestBodyInit);
        });
      }

      // If it's not FormData but onProgress is provided, simulate a slow progress
      // for better UX during JSON/fetch requests
      let progressInterval: NodeJS.Timeout | null = null;
      if (!isFormData && onProgress) {
        let currentProgress = 0;
        onProgress(0, 'starting');
        progressInterval = setInterval(() => {
          currentProgress += Math.random() * 15;
          if (currentProgress > 95) {
            if (progressInterval) clearInterval(progressInterval);
            currentProgress = 95;
            onProgress(95, 'processing');
          } else {
            onProgress(Math.round(currentProgress), 'loading');
          }
        }, 300);
      }

      const response = await fetch(sanitizedUrl, {
        ...fetchOptions,
        body: sanitizedBody,
        headers: {
          ...defaultHeaders,
          ...(fetchOptions.headers as Record<string, string>),
        },
      });

      if (progressInterval) {
        clearInterval(progressInterval);
        if (onProgress) onProgress(100, 'complete');
      }

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const errorMessage =
          (data as ApiErrorResponse)?.error || (data as ApiErrorResponse)?.message || `HTTP ${response.status}`;
        throw new ApiError(errorMessage, response.status, data);
      }

      // Cache successful prediction responses
      if (url.includes('/predict') && !skipCache) {
        try {
          // For fetch requests, we can't easily get the image data for hashing
          // The server-side caching will handle this case
        } catch (cacheError) {
          console.warn('Failed to cache response:', cacheError);
        }
      }

      return {
        data: data as T,
        status: response.status,
        cached: false
      };
    } catch (error) {
      lastError =
        error instanceof Error ? error : new Error("Unknown error occurred");

      // Don't retry on client errors (4xx) except for 429 (rate limit)
      if (
        lastError instanceof ApiError &&
        lastError.status >= 400 &&
        lastError.status < 500 &&
        lastError.status !== 429
      ) {
        break;
      }

      // If this is the last attempt, don't wait
      if (attempt < retries) {
        await sleep(retryDelay * Math.pow(2, attempt)); // Exponential backoff
      }
    }
  }

  return {
    error: lastError?.message || "Request failed",
    status: lastError instanceof ApiError ? lastError.status : 500,
    cached: false
  };
};

// Enhanced upload with progress tracking
const uploadWithProgress = async (
  url: string,
  formData: FormData,
  options: {
    onProgress?: (progress: { loaded: number; total: number }) => void;
    signal?: AbortSignal;
    headers?: Record<string, string>;
  } = {}
): Promise<ApiResponse> => {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    
    // Progress tracking
    if (options.onProgress) {
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          options.onProgress!({
            loaded: event.loaded,
            total: event.total
          });
        }
      });
    }
    
    // Load completion
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          resolve({
            data,
            status: xhr.status
          });
        } catch (error) {
          resolve({
            data: xhr.responseText,
            status: xhr.status
          });
        }
      } else {
        try {
          const data = JSON.parse(xhr.responseText);
          reject(new ApiError(
            data?.error || data?.message || `HTTP ${xhr.status}`,
            xhr.status,
            data
          ));
        } catch {
          reject(new ApiError(`HTTP ${xhr.status}`, xhr.status));
        }
      }
    });
    
    // Error handling
    xhr.addEventListener('error', () => {
      reject(new ApiError('Network error', 0));
    });
    
    xhr.addEventListener('abort', () => {
      reject(new ApiError('Upload cancelled', 0));
    });
    
    // Configure and send
    xhr.open('POST', url);
    
    // Set headers
    if (options.headers) {
      Object.entries(options.headers).forEach(([key, value]) => {
        xhr.setRequestHeader(key, value);
      });
    }
    
    // Handle abort signal
    if (options.signal) {
      options.signal.addEventListener('abort', () => {
        xhr.abort();
      });
    }
    
    xhr.send(formData);
  });
};

// API methods with error handling
export const api = {
  get: <T = any>(url: string, options?: ApiOptions) =>
    apiRequest<T>(url, { method: "GET", ...options }),

  post: <T = any>(url: string, data?: any, options?: ApiOptions, onProgress?: (progress: number, status?: string) => void) =>
    apiRequest<T>(url, {
      method: "POST",
      body: (typeof FormData !== "undefined" && data instanceof FormData) ? data : (data ? JSON.stringify(data) : undefined),
      ...options,
    }, onProgress),

  put: <T = any>(url: string, data?: any, options?: ApiOptions, onProgress?: (progress: number, status?: string) => void) =>
    apiRequest<T>(url, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
      ...options,
    }, onProgress),

  delete: <T = any>(url: string, options?: ApiOptions) =>
    apiRequest<T>(url, { method: "DELETE", ...options }),

  // Cache management methods
  cache: {
    clear: () => {
      memoryCache.clear();
      localStorage.removeItem(CACHE_CONFIG.storageKey);
      console.log('Cache cleared');
    },

    getStats: () => {
      cleanExpiredCache();
      return {
        entries: memoryCache.size,
        maxEntries: CACHE_CONFIG.maxEntries,
        defaultTTL: CACHE_CONFIG.defaultTTL
      };
    },

    setTTL: (ttlMs: number) => {
      CACHE_CONFIG.defaultTTL = ttlMs;
      console.log(`Cache TTL set to ${ttlMs}ms`);
    }
  }
};

export { ApiError };
export type { ApiResponse };
export { InputSanitizer };
