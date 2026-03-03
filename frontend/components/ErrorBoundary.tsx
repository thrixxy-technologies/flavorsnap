import React, { Component, ErrorInfo, ReactNode } from 'react';
import { analytics } from '@/utils/analytics';
import { errorHandler, ErrorType } from '@/lib/error-handler';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  errorCount: number;
  customError?: any;
  retryCount: number;
  maxRetries: number;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { 
      hasError: false, 
      errorCount: 0,
      retryCount: 0,
      maxRetries: 3
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return { 
      hasError: true, 
      error, 
      errorCount: 0,
      retryCount: 0,
      maxRetries: 3
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const customError = errorHandler.createError(ErrorType.CLASSIFICATION_ERROR, error.message, {
      userMessage: 'Something went wrong while processing your request. Please try again.',
      context: {
        componentStack: errorInfo.componentStack,
        errorBoundary: true,
        errorCount: this.state.errorCount + 1,
      },
    });

    this.setState((prevState) => ({
      error,
      errorInfo,
      customError,
      errorCount: prevState.errorCount + 1,
    }));

    // Track error in analytics
    analytics.trackError(error, errorInfo, true);

    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    // Track repeated errors
    if (this.state.errorCount > 2) {
      analytics.event({
        action: 'repeated_error',
        category: 'Error',
        label: error.message,
        value: this.state.errorCount,
      });
    }
  }

  handleRetry = () => {
    if (this.state.retryCount >= this.state.maxRetries) {
      // Max retries reached, suggest page reload
      return;
    }

    analytics.event({
      action: 'error_retry',
      category: 'User_Interaction',
      label: this.state.error?.message || 'unknown',
      value: this.state.retryCount + 1,
    });

    this.setState((prevState) => ({
      hasError: false, 
      error: undefined, 
      errorInfo: undefined,
      customError: undefined,
      retryCount: prevState.retryCount + 1,
    }));
  };

  canRetry = () => {
    return this.state.retryCount < this.state.maxRetries;
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-gray-50 p-4 sm:p-6">
          <div className="mx-auto w-full max-w-md rounded-lg bg-white p-6 text-center shadow-lg sm:p-8">
            <div className="mb-4">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
                <svg
                  className="h-8 w-8 text-red-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <h2 className="mb-2 text-2xl font-bold text-gray-900">Something went wrong</h2>
              <p className="mb-6 text-gray-600">
                We&apos;re sorry, but something unexpected happened. The error has been logged and we&apos;ll look into it.
              </p>
              
              {!this.canRetry() && (
                <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                  <p className="text-sm text-yellow-800 dark:text-yellow-200">
                    Multiple retry attempts failed. Please try reloading the page.
                  </p>
                </div>
              )}
            </div>

            <div className="space-y-3">
              {this.canRetry() && (
                <button
                  onClick={this.handleRetry}
                  className="w-full bg-accent hover:bg-accent/90 text-white font-medium py-2 px-4 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2"
                >
                  Try Again {this.state.retryCount > 0 && `(${this.state.retryCount}/${this.state.maxRetries})`}
                </button>
              )}
              
              <button
                onClick={this.handleRetry}
                className="min-h-[44px] w-full rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
              >
                Reload Page
              </button>
              
              <button
                onClick={() => window.location.reload()}
                className="min-h-[44px] w-full rounded-lg bg-gray-200 px-4 py-2 text-gray-800 transition-colors hover:bg-gray-300"
              >
                Go Back
              </button>
            </div>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mt-6 text-left">
                <summary className="mb-2 cursor-pointer text-sm font-medium text-gray-700">
                  Error Details (Development Only)
                </summary>
                <div className="max-h-40 overflow-auto rounded bg-gray-100 p-3 font-mono text-xs">
                  <div className="mb-2 font-bold text-red-600">
                    {this.state.error.toString()}
                  </div>
                  {this.state.errorInfo && (
                    <>
                      <div className="font-semibold mb-2">Component Stack:</div>
                      <pre className="whitespace-pre-wrap">
                        {this.state.errorInfo.componentStack}
                      </pre>
                    </>
                  )}
                  
                  <div className="font-semibold mb-2 mt-3">Retry Info:</div>
                  <div>Attempts: {this.state.retryCount}/{this.state.maxRetries}</div>
                  <div>Error Count: {this.state.errorCount}</div>
                </div>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
