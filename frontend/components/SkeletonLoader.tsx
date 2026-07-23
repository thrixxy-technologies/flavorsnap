/**
 * SkeletonLoader Component
 * Provides skeleton loading states for async operations.
 */

import React from 'react';

interface SkeletonLoaderProps {
  type?: 'card' | 'text' | 'chart' | 'table' | 'image';
  count?: number;
  className?: string;
}

export function SkeletonLoader({ type = 'card', count = 1, className = '' }: SkeletonLoaderProps) {
  const items = Array.from({ length: count }, (_, i) => i);

  return (
    <>
      {items.map((i) => (
        <div key={i} className={`animate-pulse ${className}`}>
          {type === 'card' && <SkeletonCard />}
          {type === 'text' && <SkeletonText />}
          {type === 'chart' && <SkeletonChart />}
          {type === 'table' && <SkeletonTable />}
          {type === 'image' && <SkeletonImage />}
        </div>
      ))}
    </>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 space-y-4">
      <div className="h-6 bg-gray-200 rounded w-1/3"></div>
      <div className="h-4 bg-gray-200 rounded w-full"></div>
      <div className="h-4 bg-gray-200 rounded w-2/3"></div>
      <div className="h-20 bg-gray-200 rounded-lg"></div>
    </div>
  );
}

function SkeletonText() {
  return (
    <div className="space-y-2">
      <div className="h-4 bg-gray-200 rounded w-full"></div>
      <div className="h-4 bg-gray-200 rounded w-5/6"></div>
      <div className="h-4 bg-gray-200 rounded w-4/6"></div>
    </div>
  );
}

function SkeletonChart() {
  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
      <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
      <div className="h-48 bg-gray-200 rounded-lg flex items-end gap-2 p-4">
        {[60, 80, 45, 90, 70, 50, 85].map((h, i) => (
          <div key={i} className="bg-gray-300 rounded-t flex-1" style={{ height: `${h}%` }}></div>
        ))}
      </div>
    </div>
  );
}

function SkeletonTable() {
  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
      <div className="space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex gap-4">
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/6"></div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SkeletonImage() {
  return (
    <div className="bg-gray-200 rounded-xl aspect-video w-full"></div>
  );
}

export default SkeletonLoader;
