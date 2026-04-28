
import dynamic from 'next/dynamic';
import React from 'react';

/**
 * Helper for lazy loading components with a consistent loading state.
 */
export const lazyLoad = (importFn: () => Promise<any>, options: { ssr?: boolean } = {}) => {
  return dynamic(importFn, {
    loading: () => React.createElement('div', { 
      className: "animate-pulse bg-slate-200 dark:bg-slate-800 rounded-xl h-48 w-full" 
    }),
    ssr: options.ssr ?? true,
  });
};

/**
 * Utility to optimize image URLs (e.g., using a CDN or proxy).
 */
export const optimizeImageUrl = (url: string, width: number = 800): string => {
  if (!url) return '';
  if (url.startsWith('data:') || url.startsWith('blob:')) return url;
  
  // Example CDN optimization logic
  return `${url}?w=${width}&q=75&auto=format`;
};

/**
 * Performance monitoring utility.
 */
export const reportWebVitals = (metric: any) => {
  if (process.env.NODE_ENV === 'production') {
    // In a real app, send to analytics
    console.debug('Web Vital:', metric);
  }
};
