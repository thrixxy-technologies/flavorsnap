import React, { useEffect, useState } from 'react';
import AccessibilityPanel from '../components/AccessibilityPanel';
import { useAccessibility } from '../hooks/useAccessibility';
import { a11yUtils } from '../utils/a11yUtils';

const AccessibilityExample: React.FC = () => {
  const {
    settings,
    updateSetting,
    addKeyboardShortcut,
    announceToScreenReader,
    trapFocus,
    addSkipLink,
    runAccessibilityTest,
    detectScreenReader,
    detectHighContrast,
    detectReducedMotion
  } = useAccessibility();

  const [showPanel, setShowPanel] = useState(false);
  const [testResults, setTestResults] = useState<any>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Add keyboard shortcuts
    const cleanupAltA = addKeyboardShortcut({
      key: 'a',
      altKey: true,
      action: () => setShowPanel(true),
      description: 'Open accessibility panel',
      global: true
    });

    const cleanupEscape = addKeyboardShortcut({
      key: 'Escape',
      action: () => {
        setShowPanel(false);
        setModalOpen(false);
      },
      description: 'Close dialogs',
      global: true
    });

    // Add skip links
    addSkipLink('main-content', 'Skip to main content');
    addSkipLink('navigation', 'Skip to navigation');

    // Detect user preferences
    const screenReaderActive = detectScreenReader();
    const highContrastMode = detectHighContrast();
    const reducedMotionPreferred = detectReducedMotion();

    console.log('Accessibility Detection:', {
      screenReaderActive,
      highContrastMode,
      reducedMotionPreferred
    });

    return () => {
      cleanupAltA();
      cleanupEscape();
    };
  }, [addKeyboardShortcut, addSkipLink, detectScreenReader, detectHighContrast, detectReducedMotion]);

  const handleRunTests = async () => {
    const results = await runAccessibilityTest('comprehensive');
    setTestResults(results);
    announceToScreenReader('Accessibility tests completed');
  };

  const handleModalOpen = () => {
    setModalOpen(true);
    if (modalRef.current) {
      const focusTrap = trapFocus(modalRef.current);
      focusTrap.activate();
    }
  };

  const handleModalClose = () => {
    setModalOpen(false);
  };

  const handleAnnounce = () => {
    announceToScreenReader('This is a test announcement for screen readers');
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Skip Links */}
      <nav id="navigation" className="mb-6">
        <h1 className="text-2xl font-bold">Accessibility Demo</h1>
        <p className="text-gray-600">Explore comprehensive accessibility features</p>
      </nav>

      {/* Main Content */}
      <main id="main-content" className="max-w-4xl mx-auto space-y-6">
        <section>
          <h2 className="text-xl font-semibold mb-4">Current Settings</h2>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className={`w-12 h-12 rounded-full mx-auto mb-2 ${
                  settings.highContrast ? 'bg-yellow-400' : 'bg-gray-200'
                }`} />
                <p className="text-sm font-medium">High Contrast</p>
                <p className="text-xs text-gray-500">{settings.highContrast ? 'On' : 'Off'}</p>
              </div>
              <div className="text-center">
                <div className={`w-12 h-12 rounded-full mx-auto mb-2 ${
                  settings.largeText ? 'bg-blue-400' : 'bg-gray-200'
                }`} />
                <p className="text-sm font-medium">Large Text</p>
                <p className="text-xs text-gray-500">{settings.largeText ? 'On' : 'Off'}</p>
              </div>
              <div className="text-center">
                <div className={`w-12 h-12 rounded-full mx-auto mb-2 ${
                  settings.reducedMotion ? 'bg-green-400' : 'bg-gray-200'
                }`} />
                <p className="text-sm font-medium">Reduced Motion</p>
                <p className="text-xs text-gray-500">{settings.reducedMotion ? 'On' : 'Off'}</p>
              </div>
              <div className="text-center">
                <div className={`w-12 h-12 rounded-full mx-auto mb-2 ${
                  settings.darkMode ? 'bg-purple-400' : 'bg-gray-200'
                }`} />
                <p className="text-sm font-medium">Dark Mode</p>
                <p className="text-xs text-gray-500">{settings.darkMode ? 'On' : 'Off'}</p>
              </div>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <button
              onClick={() => setShowPanel(true)}
              className="p-4 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-300"
              aria-label="Open accessibility settings panel"
            >
              <Settings className="w-6 h-6 mx-auto mb-2" />
              <span>Accessibility Panel</span>
            </button>

            <button
              onClick={handleRunTests}
              className="p-4 bg-green-500 text-white rounded-lg hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-300"
              aria-label="Run accessibility tests"
            >
              <Target className="w-6 h-6 mx-auto mb-2" />
              <span>Run Tests</span>
            </button>

            <button
              onClick={handleAnnounce}
              className="p-4 bg-purple-500 text-white rounded-lg hover:bg-purple-600 focus:outline-none focus:ring-2 focus:ring-purple-300"
              aria-label="Test screen reader announcement"
            >
              <Volume2 className="w-6 h-6 mx-auto mb-2" />
              <span>Test Announcement</span>
            </button>

            <button
              onClick={() => updateSetting('highContrast', !settings.highContrast)}
              className="p-4 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 focus:outline-none focus:ring-2 focus:ring-yellow-300"
              aria-label="Toggle high contrast mode"
            >
              <Eye className="w-6 h-6 mx-auto mb-2" />
              <span>Toggle Contrast</span>
            </button>

            <button
              onClick={() => updateSetting('largeText', !settings.largeText)}
              className="p-4 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-300"
              aria-label="Toggle large text mode"
            >
              <Type className="w-6 h-6 mx-auto mb-2" />
              <span>Toggle Text Size</span>
            </button>

            <button
              onClick={handleModalOpen}
              className="p-4 bg-red-500 text-white rounded-lg hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-300"
              aria-label="Open focus trap modal demo"
            >
              <Lock className="w-6 h-6 mx-auto mb-2" />
              <span>Focus Trap Demo</span>
            </button>
          </div>
        </section>

        {/* Test Results */}
        {testResults && (
          <section>
            <h2 className="text-xl font-semibold mb-4">Test Results</h2>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="space-y-3">
                {testResults.map((result: any, index: number) => (
                  <div
                    key={index}
                    className={`p-3 rounded-lg border ${
                      result.passed
                        ? 'bg-green-50 border-green-200'
                        : 'bg-red-50 border-red-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="font-medium">{result.type}</h3>
                      <span className={`px-2 py-1 rounded text-xs ${
                        result.passed
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {result.passed ? 'Pass' : 'Fail'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{result.message}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* Interactive Demo */}
        <section>
          <h2 className="text-xl font-semibold mb-4">Interactive Demo</h2>
          <div className="bg-white rounded-lg shadow p-6 space-y-4">
            <div>
              <label htmlFor="demo-input" className="block text-sm font-medium mb-2">
                Accessible Input
              </label>
              <input
                id="demo-input"
                type="text"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Type something..."
                aria-describedby="demo-help"
              />
              <p id="demo-help" className="text-sm text-gray-500 mt-1">
                This input has proper labeling and description
              </p>
            </div>

            <div>
              <label htmlFor="demo-select" className="block text-sm font-medium mb-2">
                Accessible Select
              </label>
              <select
                id="demo-select"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-describedby="select-help"
              >
                <option>Option 1</option>
                <option>Option 2</option>
                <option>Option 3</option>
              </select>
              <p id="select-help" className="text-sm text-gray-500 mt-1">
                This select has proper labeling and description
              </p>
            </div>

            <div className="flex gap-4">
              <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-300">
                Primary Action
              </button>
              <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-300">
                Secondary Action
              </button>
              <button className="px-4 py-2 text-blue-500 underline hover:no-underline focus:outline-none focus:ring-2 focus:ring-blue-300">
                Link Action
              </button>
            </div>
          </div>
        </section>

        {/* Keyboard Shortcuts */}
        <section>
          <h2 className="text-xl font-semibold mb-4">Keyboard Shortcuts</h2>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Open Accessibility Panel</span>
                <kbd className="px-2 py-1 bg-gray-100 rounded text-sm">Alt + A</kbd>
              </div>
              <div className="flex justify-between">
                <span>Close Dialogs</span>
                <kbd className="px-2 py-1 bg-gray-100 rounded text-sm">Escape</kbd>
              </div>
              <div className="flex justify-between">
                <span>Toggle High Contrast</span>
                <kbd className="px-2 py-1 bg-gray-100 rounded text-sm">Alt + H</kbd>
              </div>
              <div className="flex justify-between">
                <span>Toggle Large Text</span>
                <kbd className="px-2 py-1 bg-gray-100 rounded text-sm">Alt + L</kbd>
              </div>
              <div className="flex justify-between">
                <span>Toggle Dark Mode</span>
                <kbd className="px-2 py-1 bg-gray-100 rounded text-sm">Alt + D</kbd>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Accessibility Panel */}
      <AccessibilityPanel
        isOpen={showPanel}
        onClose={() => setShowPanel(false)}
        onSettingsChange={(newSettings) => {
          console.log('Settings changed:', newSettings);
        }}
      />

      {/* Focus Trap Modal Demo */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div
            ref={modalRef}
            className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
          >
            <h3 id="modal-title" className="text-lg font-semibold mb-4">
              Focus Trap Demo
            </h3>
            <p className="text-gray-600 mb-6">
              This modal demonstrates focus trapping. Use Tab to navigate and Escape to close.
            </p>
            <div className="space-y-4">
              <button className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-300">
                Button 1
              </button>
              <button className="w-full px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-300">
                Button 2
              </button>
              <button className="w-full px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 focus:outline-none focus:ring-2 focus:ring-purple-300">
                Button 3
              </button>
              <button
                onClick={handleModalClose}
                className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-300"
              >
                Close Modal
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="mt-12 py-6 border-t border-gray-200">
        <div className="text-center text-sm text-gray-500">
          <p>Accessibility Demo - Press Alt+A to open accessibility settings</p>
          <p className="mt-2">
            Detected: {detectScreenReader() ? 'Screen Reader' : ''} 
            {detectHighContrast() ? 'High Contrast' : ''} 
            {detectReducedMotion() ? 'Reduced Motion' : ''}
          </p>
        </div>
      </footer>
    </div>
  );
};

export default AccessibilityExample;
