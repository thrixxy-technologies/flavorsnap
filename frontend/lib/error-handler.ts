export enum ErrorType {
  NETWORK_ERROR = 'NETWORK_ERROR',
  UPLOAD_ERROR = 'UPLOAD_ERROR',
  CLASSIFICATION_ERROR = 'CLASSIFICATION_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  OFFLINE_ERROR = 'OFFLINE_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  FILE_SIZE_ERROR = 'FILE_SIZE_ERROR',
  FILE_TYPE_ERROR = 'FILE_TYPE_ERROR',
  QUOTA_EXCEEDED_ERROR = 'QUOTA_EXCEEDED_ERROR',
}

export interface ErrorInfo {
  type: ErrorType;
  message: string;
  userMessage: string;
  retryable: boolean;
  retryDelay?: number;
  maxRetries?: number;
  timestamp: number;
  context?: Record<string, any>;
}

export class ErrorHandler {
  private static instance: ErrorHandler;
  private errorLog: ErrorInfo[] = [];
  private retryCallbacks: Map<string, () => Promise<any>> = new Map();
  private maxLogSize = 100;

  static getInstance(): ErrorHandler {
    if (!ErrorHandler.instance) {
      ErrorHandler.instance = new ErrorHandler();
    }
    return ErrorHandler.instance;
  }

  private constructor() {
    // Set up online/offline event listeners
    if (typeof window !== 'undefined') {
      window.addEventListener('online', this.handleOnline.bind(this));
      window.addEventListener('offline', this.handleOffline.bind(this));
    }
  }

  private handleOnline() {
    console.log('Connection restored');
    // Auto-retry failed operations when coming back online
    this.retryFailedOperations();
  }

  private handleOffline() {
    console.log('Connection lost');
    // Notify user about offline status
    this.createError(ErrorType.OFFLINE_ERROR, 'Connection lost', {
      userMessage: 'You appear to be offline. Please check your internet connection.',
      retryable: false,
    });
  }

  createError(
    type: ErrorType,
    technicalMessage: string,
    options: {
      userMessage?: string;
      retryable?: boolean;
      retryDelay?: number;
      maxRetries?: number;
      context?: Record<string, any>;
    } = {}
  ): ErrorInfo {
    const errorInfo: ErrorInfo = {
      type,
      message: technicalMessage,
      userMessage: options.userMessage || this.getDefaultUserMessage(type),
      retryable: options.retryable ?? this.isRetryableError(type),
      retryDelay: options.retryDelay || this.getDefaultRetryDelay(type),
      maxRetries: options.maxRetries || this.getDefaultMaxRetries(type),
      timestamp: Date.now(),
      context: options.context,
    };

    this.logError(errorInfo);
    return errorInfo;
  }

  private getDefaultUserMessage(type: ErrorType): string {
    switch (type) {
      case ErrorType.NETWORK_ERROR:
        return 'Network connection failed. Please check your internet connection and try again.';
      case ErrorType.UPLOAD_ERROR:
        return 'Failed to upload image. Please try again or select a different image.';
      case ErrorType.CLASSIFICATION_ERROR:
        return 'AI classification service is temporarily unavailable. Please try again in a few moments.';
      case ErrorType.VALIDATION_ERROR:
        return 'Invalid image format. Please upload a valid image file (JPG, PNG, GIF, WebP).';
      case ErrorType.OFFLINE_ERROR:
        return 'You are currently offline. Please check your internet connection.';
      case ErrorType.TIMEOUT_ERROR:
        return 'Request timed out. Please try again.';
      case ErrorType.SERVER_ERROR:
        return 'Server error occurred. Our team has been notified and is working on a fix.';
      case ErrorType.FILE_SIZE_ERROR:
        return 'Image file is too large. Please upload an image smaller than 10MB.';
      case ErrorType.FILE_TYPE_ERROR:
        return 'Invalid file type. Please upload an image file.';
      case ErrorType.QUOTA_EXCEEDED_ERROR:
        return 'You have exceeded the upload limit. Please try again later.';
      default:
        return 'An unexpected error occurred. Please try again.';
    }
  }

  private isRetryableError(type: ErrorType): boolean {
    return [
      ErrorType.NETWORK_ERROR,
      ErrorType.UPLOAD_ERROR,
      ErrorType.CLASSIFICATION_ERROR,
      ErrorType.TIMEOUT_ERROR,
      ErrorType.SERVER_ERROR,
    ].includes(type);
  }

  private getDefaultRetryDelay(type: ErrorType): number {
    switch (type) {
      case ErrorType.NETWORK_ERROR:
        return 2000; // 2 seconds
      case ErrorType.CLASSIFICATION_ERROR:
        return 5000; // 5 seconds
      case ErrorType.TIMEOUT_ERROR:
        return 3000; // 3 seconds
      case ErrorType.SERVER_ERROR:
        return 10000; // 10 seconds
      default:
        return 1000; // 1 second
    }
  }

  private getDefaultMaxRetries(type: ErrorType): number {
    switch (type) {
      case ErrorType.NETWORK_ERROR:
        return 3;
      case ErrorType.CLASSIFICATION_ERROR:
        return 2;
      case ErrorType.TIMEOUT_ERROR:
        return 2;
      case ErrorType.SERVER_ERROR:
        return 1;
      default:
        return 1;
    }
  }

  private logError(error: ErrorInfo) {
    this.errorLog.push(error);
    
    // Keep log size manageable
    if (this.errorLog.length > this.maxLogSize) {
      this.errorLog = this.errorLog.slice(-this.maxLogSize);
    }

    // Log to console for debugging
    console.error('Error logged:', {
      type: error.type,
      message: error.message,
      userMessage: error.userMessage,
      timestamp: new Date(error.timestamp).toISOString(),
      context: error.context,
    });

    // In production, you would send this to your error monitoring service
    // this.sendToMonitoringService(error);
  }

  getErrorLog(): ErrorInfo[] {
    return [...this.errorLog];
  }

  clearErrorLog() {
    this.errorLog = [];
  }

  registerRetryCallback(id: string, callback: () => Promise<any>) {
    this.retryCallbacks.set(id, callback);
  }

  unregisterRetryCallback(id: string) {
    this.retryCallbacks.delete(id);
  }

  async retryOperation(id: string): Promise<any> {
    const callback = this.retryCallbacks.get(id);
    if (!callback) {
      throw new Error('No retry callback registered for this operation');
    }

    try {
      return await callback();
    } catch (error) {
      throw error;
    }
  }

  private async retryFailedOperations() {
    for (const [id, callback] of this.retryCallbacks) {
      try {
        await callback();
      } catch (error) {
        console.error('Auto-retry failed:', error);
      }
    }
  }

  isOnline(): boolean {
    return typeof navigator !== 'undefined' ? navigator.onLine : true;
  }

  // Utility method to handle API responses
  handleApiResponse(response: Response, data: any): ErrorInfo | null {
    if (response.ok) {
      return null;
    }

    let errorType = ErrorType.SERVER_ERROR;
    let userMessage = '';

    switch (response.status) {
      case 400:
        errorType = ErrorType.VALIDATION_ERROR;
        break;
      case 401:
        userMessage = 'Authentication required. Please log in and try again.';
        break;
      case 403:
        userMessage = 'You do not have permission to perform this action.';
        break;
      case 404:
        userMessage = 'The requested resource was not found.';
        break;
      case 413:
        errorType = ErrorType.FILE_SIZE_ERROR;
        break;
      case 415:
        errorType = ErrorType.FILE_TYPE_ERROR;
        break;
      case 429:
        errorType = ErrorType.QUOTA_EXCEEDED_ERROR;
        break;
      case 500:
      case 502:
      case 503:
      case 504:
        errorType = ErrorType.SERVER_ERROR;
        break;
    }

    return this.createError(errorType, `HTTP ${response.status}: ${response.statusText}`, {
      userMessage: userMessage || data?.error || this.getDefaultUserMessage(errorType),
      context: { status: response.status, statusText: response.statusText, data },
    });
  }

  // Utility method to handle network errors
  handleNetworkError(error: any): ErrorInfo {
    if (error.name === 'AbortError') {
      return this.createError(ErrorType.TIMEOUT_ERROR, 'Request was aborted', {
        context: { originalError: error },
      });
    }

    if (!navigator.onLine) {
      return this.createError(ErrorType.OFFLINE_ERROR, 'Network is offline');
    }

    return this.createError(ErrorType.NETWORK_ERROR, 'Network request failed', {
      context: { originalError: error },
    });
  }
}

export const errorHandler = ErrorHandler.getInstance();
