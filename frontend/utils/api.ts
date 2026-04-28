interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status: number;
}

interface ApiOptions extends RequestInit {
  retries?: number;
  retryDelay?: number;
}

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const apiRequest = async <T = any>(
  url: string,
  options: ApiOptions = {},
): Promise<ApiResponse<T>> => {
  const { retries = 3, retryDelay = 1000, ...fetchOptions } = options;

  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const isFormData = typeof FormData !== "undefined" && fetchOptions.body instanceof FormData;
      const defaultHeaders: Record<string, string> = isFormData ? {} : { "Content-Type": "application/json" };

      const headers: Record<string, string> = {
        ...defaultHeaders,
      };

      // Add additional headers if provided
      if (fetchOptions.headers) {
        const additionalHeaders = fetchOptions.headers as Record<string, string>;
        Object.keys(additionalHeaders).forEach(key => {
          if (additionalHeaders[key] !== undefined) {
            headers[key] = additionalHeaders[key];
          }
        });
      }

      const response = await fetch(url, {
        headers,
        ...fetchOptions,
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const errorMessage =
          data?.error || data?.message || `HTTP ${response.status}`;
        throw new ApiError(errorMessage, response.status, data);
      }

      return {
        data,
        status: response.status,
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

  post: <T = any>(url: string, data?: any, options?: ApiOptions) =>
    apiRequest<T>(url, {
      method: "POST",
      body: (typeof FormData !== "undefined" && data instanceof FormData) ? data : (data ? JSON.stringify(data) : undefined),
      ...options,
    }),

  put: <T = any>(url: string, data?: any, options?: ApiOptions) =>
    apiRequest<T>(url, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
      ...options,
    }),

  delete: <T = any>(url: string, options?: ApiOptions) =>
    apiRequest<T>(url, { method: "DELETE", ...options }),
};

export { ApiError };
export type { ApiResponse };
