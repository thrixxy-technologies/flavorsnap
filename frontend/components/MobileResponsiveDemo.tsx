/**
 * Mobile Responsive Demo Component
 * Demonstrates mobile responsiveness features
 */

import { useState, useRef } from 'react';
import { useMobileResponsive, useTouchGestures, useOrientation } from '@/hooks/useMobileResponsive';

export function MobileResponsiveDemo() {
  const { isMobile, isTablet, isTouch, breakpoint, viewport } = useMobileResponsive();
  const orientation = useOrientation();
  const [swipeDirection, setSwipeDirection] = useState<string>('');
  const swipeAreaRef = useRef<HTMLDivElement>(null);

  useTouchGestures(swipeAreaRef, {
    onSwipeLeft: () => setSwipeDirection('Left'),
    onSwipeRight: () => setSwipeDirection('Right'),
    onSwipeUp: () => setSwipeDirection('Up'),
    onSwipeDown: () => setSwipeDirection('Down'),
    onTap: () => setSwipeDirection('Tap'),
  });

  return (
    <div className="responsive-container py-8">
      <h1 className="heading-responsive-xl mb-8 text-center">
        Mobile Responsiveness Demo
      </h1>

      {/* Device Info Card */}
      <div className="card-responsive mb-8 bg-white dark:bg-gray-800 shadow-lg">
        <h2 className="heading-responsive-lg mb-4">Device Information</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <p className="text-responsive">
              <strong>Device Type:</strong>{' '}
              {isMobile ? '📱 Mobile' : isTablet ? '📱 Tablet' : '💻 Desktop'}
            </p>
            <p className="text-responsive">
              <strong>Touch Support:</strong> {isTouch ? '✅ Yes' : '❌ No'}
            </p>
            <p className="text-responsive">
              <strong>Breakpoint:</strong> {breakpoint}
            </p>
          </div>
          <div className="space-y-2">
            <p className="text-responsive">
              <strong>Viewport:</strong> {viewport.width}x{viewport.height}
            </p>
            <p className="text-responsive">
              <strong>Orientation:</strong> {orientation}
            </p>
          </div>
        </div>
      </div>

      {/* Touch Target Demo */}
      <div className="card-responsive mb-8 bg-white dark:bg-gray-800 shadow-lg">
        <h2 className="heading-responsive-lg mb-4">Touch-Friendly Buttons</h2>
        <p className="text-responsive mb-4">
          All buttons meet the minimum 44x44px touch target size (WCAG AAA)
        </p>
        <div className="flex flex-wrap gap-4">
          <button className="
            touch-target
            bg-blue-500 text-white
            px-6 py-3 rounded-lg
            hover:bg-blue-600
            active:scale-95
            transition-all
          ">
            Standard Button (44px)
          </button>
          <button className="
            touch-target-comfortable
            bg-green-500 text-white
            px-8 py-4 rounded-lg
            hover:bg-green-600
            active:scale-95
            transition-all
          ">
            Primary Action (48px)
          </button>
          <button className="
            touch-target
            bg-purple-500 text-white
            px-6 py-3 rounded-lg
            hover:bg-purple-600
            touch-ripple
            transition-all
          ">
            With Ripple Effect
          </button>
        </div>
      </div>

      {/* Swipe Gesture Demo */}
      <div className="card-responsive mb-8 bg-white dark:bg-gray-800 shadow-lg">
        <h2 className="heading-responsive-lg mb-4">Touch Gestures</h2>
        <p className="text-responsive mb-4">
          Try swiping or tapping in the area below:
        </p>
        <div
          ref={swipeAreaRef}
          className="
            bg-gradient-to-br from-blue-100 to-purple-100
            dark:from-blue-900 dark:to-purple-900
            rounded-xl p-8
            min-h-[200px]
            flex items-center justify-center
            cursor-pointer
            select-none
            touch-manipulation
          "
        >
          <div className="text-center">
            <p className="text-2xl font-bold mb-2">
              {swipeDirection ? `${swipeDirection}!` : 'Swipe or Tap Here'}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {swipeDirection ? 'Try another gesture' : 'Touch to interact'}
            </p>
          </div>
        </div>
      </div>

      {/* Responsive Grid Demo */}
      <div className="card-responsive mb-8 bg-white dark:bg-gray-800 shadow-lg">
        <h2 className="heading-responsive-lg mb-4">Responsive Grid</h2>
        <p className="text-responsive mb-4">
          Grid adapts from 1 column (mobile) to 4 columns (desktop)
        </p>
        <div className="grid-responsive">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((num) => (
            <div
              key={num}
              className="
                bg-gradient-to-br from-indigo-500 to-purple-500
                text-white
                rounded-lg p-6
                text-center
                font-bold
                text-xl
              "
            >
              Item {num}
            </div>
          ))}
        </div>
      </div>

      {/* Responsive Typography Demo */}
      <div className="card-responsive mb-8 bg-white dark:bg-gray-800 shadow-lg">
        <h2 className="heading-responsive-lg mb-4">Responsive Typography</h2>
        <div className="space-y-4">
          <div>
            <h3 className="heading-responsive-xl">Extra Large Heading</h3>
            <p className="text-xs text-gray-500">Scales from 2rem to 3rem</p>
          </div>
          <div>
            <h4 className="heading-responsive-lg">Large Heading</h4>
            <p className="text-xs text-gray-500">Scales from 1.5rem to 2.5rem</p>
          </div>
          <div>
            <h5 className="heading-responsive-md">Medium Heading</h5>
            <p className="text-xs text-gray-500">Scales from 1.25rem to 1.875rem</p>
          </div>
          <div>
            <p className="text-responsive">
              Body text that scales responsively from 0.875rem to 1rem
            </p>
          </div>
        </div>
      </div>

      {/* Responsive Image Demo */}
      <div className="card-responsive mb-8 bg-white dark:bg-gray-800 shadow-lg">
        <h2 className="heading-responsive-lg mb-4">Responsive Images</h2>
        <p className="text-responsive mb-4">
          Images scale appropriately for different screen sizes
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((num) => (
            <div key={num} className="relative">
              <div className="
                img-mobile-optimized
                bg-gradient-to-br from-pink-400 to-orange-400
                rounded-lg
                flex items-center justify-center
                text-white font-bold text-2xl
              ">
                Image {num}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Mobile-Only / Desktop-Only Demo */}
      <div className="card-responsive mb-8 bg-white dark:bg-gray-800 shadow-lg">
        <h2 className="heading-responsive-lg mb-4">Conditional Visibility</h2>
        <div className="space-y-4">
          <div className="mobile-only bg-blue-100 dark:bg-blue-900 p-4 rounded-lg">
            <p className="text-responsive font-bold">
              📱 This content is only visible on mobile devices
            </p>
          </div>
          <div className="desktop-only bg-green-100 dark:bg-green-900 p-4 rounded-lg">
            <p className="text-responsive font-bold">
              💻 This content is only visible on desktop devices
            </p>
          </div>
        </div>
      </div>

      {/* Form Demo */}
      <div className="card-responsive mb-8 bg-white dark:bg-gray-800 shadow-lg">
        <h2 className="heading-responsive-lg mb-4">Mobile-Friendly Forms</h2>
        <p className="text-responsive mb-4">
          Form inputs use 16px font size to prevent iOS zoom
        </p>
        <form className="space-y-4">
          <div>
            <label className="block text-responsive font-medium mb-2">
              Text Input
            </label>
            <input
              type="text"
              placeholder="Enter text"
              className="
                w-full
                text-base
                min-h-[44px]
                px-4 py-3
                rounded-lg
                border-2 border-gray-300
                dark:border-gray-600
                focus:border-blue-500
                focus:outline-none
                transition-colors
              "
            />
          </div>
          <div>
            <label className="block text-responsive font-medium mb-2">
              Select Dropdown
            </label>
            <select className="
              w-full
              text-base
              min-h-[44px]
              px-4 py-3
              rounded-lg
              border-2 border-gray-300
              dark:border-gray-600
              focus:border-blue-500
              focus:outline-none
              transition-colors
            ">
              <option>Option 1</option>
              <option>Option 2</option>
              <option>Option 3</option>
            </select>
          </div>
          <div>
            <label className="block text-responsive font-medium mb-2">
              Textarea
            </label>
            <textarea
              placeholder="Enter message"
              rows={4}
              className="
                w-full
                text-base
                px-4 py-3
                rounded-lg
                border-2 border-gray-300
                dark:border-gray-600
                focus:border-blue-500
                focus:outline-none
                transition-colors
              "
            />
          </div>
          <button
            type="submit"
            className="
              touch-target-comfortable
              w-full sm:w-auto
              bg-blue-500 text-white
              px-8 py-4
              rounded-lg
              hover:bg-blue-600
              active:scale-95
              transition-all
              font-bold
            "
          >
            Submit Form
          </button>
        </form>
      </div>

      {/* Breakpoint Indicator */}
      <div className="card-responsive bg-gradient-to-r from-blue-500 to-purple-500 text-white">
        <h2 className="heading-responsive-lg mb-4">Current Breakpoint</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4">
          {['xs', 'sm', 'md', 'lg', 'xl', '2xl'].map((bp) => (
            <div
              key={bp}
              className={`
                p-4 rounded-lg text-center font-bold
                ${breakpoint === bp ? 'bg-white text-blue-500' : 'bg-white/20'}
              `}
            >
              {bp}
            </div>
          ))}
        </div>
        <p className="text-responsive mt-4 text-center">
          Current: <strong className="text-2xl">{breakpoint}</strong>
        </p>
      </div>
    </div>
  );
}

export default MobileResponsiveDemo;
