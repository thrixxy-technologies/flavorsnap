import React from 'react';

import { AppError } from '../types';

interface ErrorMessageProps {
  message?: string;
  error?: AppError | string;
  onRetry?: () => void;
  onDismiss?: () => void;
  variant?: 'inline' | 'modal' | 'toast';
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  message,
  error,
  onRetry,
  onDismiss,
  variant = 'inline',
}) => {
  const displayMessage = message || (typeof error === 'string' ? error : error?.message) || 'An unexpected error occurred';
  const displayCode = typeof error === 'object' ? error?.code : undefined;
  if (variant === 'toast') {
    return (
      <div className="fixed bottom-4 right-4 max-w-sm bg-red-50 border border-red-200 rounded-lg shadow-lg p-4 z-50">
        <div className="flex items-start">
          <div className="shrink-0">
            <svg
              className="h-5 w-5 text-red-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3 flex-1">
            <p className="text-sm text-red-800">
              {displayMessage}
              {displayCode && <span className="block text-xs font-mono mt-1 opacity-70">Error code: {displayCode}</span>}
            </p>
          </div>
          <div className="ml-auto pl-3">
            <div className="-mx-1.5 -my-1.5">
              {onDismiss && (
                <button
                  onClick={onDismiss}
                  className="inline-flex rounded-md p-1.5 text-red-500 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                  aria-label="Dismiss error message"
                >
                  <span className="sr-only">Dismiss</span>
                  <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>
        {onRetry && (
          <div className="mt-3 flex">
            <button
              onClick={onRetry}
              className="text-sm text-red-800 underline hover:text-red-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              aria-label="Retry the last action"
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    );
  }

  if (variant === 'modal') {
    return (
      <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
          <div className="p-6">
            <div className="flex items-center mb-4">
              <div className="shrink-0">
                <svg
                  className="h-6 w-6 text-red-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <h3 className="ml-3 text-lg font-medium text-gray-900">
                Error
              </h3>
            </div>
            <p className="text-gray-600 mb-6">
              {displayMessage}
              {displayCode && <span className="block text-xs font-mono mt-2 text-gray-400">Error code: {displayCode}</span>}
            </p>
            <div className="flex space-x-3">
              {onRetry && (
                <button
                  onClick={onRetry}
                  className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  aria-label="Retry the last action"
                >
                  Try Again
                </button>
              )}
              {onDismiss && (
                <button
                  onClick={onDismiss}
                  className="flex-1 bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                  aria-label="Close error dialog"
                >
                  Close
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Default inline variant
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className="h-5 w-5 text-red-400"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <p className="text-sm text-red-800">
            {displayMessage}
            {displayCode && <span className="block text-xs font-mono mt-1 opacity-70">Error code: {displayCode}</span>}
          </p>
        </div>
        {onDismiss && (
          <div className="ml-auto pl-3">
            <button
              onClick={onDismiss}
              className="inline-flex text-red-400 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              aria-label="Dismiss error message"
            >
              <span className="sr-only">Dismiss</span>
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        )}
      </div>
      {onRetry && (
        <div className="mt-3">
          <button
            onClick={onRetry}
            className="text-sm text-red-800 underline hover:text-red-900 font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            aria-label="Retry the last action"
          >
            Try Again
          </button>
        </div>
      )}
    </div>
  );
};
