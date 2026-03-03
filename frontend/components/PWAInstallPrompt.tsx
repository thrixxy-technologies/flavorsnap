import { useState, useEffect } from 'react';
import { pwaManager } from '@/lib/pwa-utils';

export function PWAInstallPrompt() {
  const [canInstall, setCanInstall] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);
  const [showPrompt, setShowPrompt] = useState(false);
  const [installing, setInstalling] = useState(false);

  useEffect(() => {
    const checkStatus = () => {
      const status = pwaManager.getInstallationStatus();
      setCanInstall(status.canInstall);
      setIsInstalled(status.isInstalled);
      setIsStandalone(status.isStandalone);
    };

    checkStatus();

    // Check status periodically
    const interval = setInterval(checkStatus, 5000);

    // Show prompt after a delay if installable
    const timer = setTimeout(() => {
      if (pwaManager.canInstall() && !isStandalone) {
        setShowPrompt(true);
      }
    }, 10000); // Show after 10 seconds

    return () => {
      clearInterval(interval);
      clearTimeout(timer);
    };
  }, [isStandalone]);

  const handleInstall = async () => {
    setInstalling(true);
    
    try {
      const installed = await pwaManager.showInstallPrompt();
      if (installed) {
        setIsInstalled(true);
        setCanInstall(false);
        setShowPrompt(false);
      }
    } catch (error) {
      console.error('Installation failed:', error);
    } finally {
      setInstalling(false);
    }
  };

  const handleDismiss = () => {
    setShowPrompt(false);
    // Don't show again for this session
    sessionStorage.setItem('pwa-prompt-dismissed', 'true');
  };

  // Don't show if already installed, standalone, or dismissed
  if (isInstalled || isStandalone || !canInstall || !showPrompt) {
    return null;
  }

  // Check if user has dismissed in this session
  if (typeof window !== 'undefined' && sessionStorage.getItem('pwa-prompt-dismissed')) {
    return null;
  }

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 md:left-auto md:right-4 md:w-96">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <div className="w-12 h-12 bg-orange-100 dark:bg-orange-900 rounded-lg flex items-center justify-center">
              <svg
                className="w-6 h-6 text-orange-600 dark:text-orange-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"
                />
              </svg>
            </div>
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">
              Install FlavorSnap
            </h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Get the full experience with offline support and faster performance.
            </p>
          </div>
          
          <button
            onClick={handleDismiss}
            className="flex-shrink-0 p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <svg
              className="w-4 h-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
        
        <div className="mt-3 flex space-x-2">
          <button
            onClick={handleInstall}
            disabled={installing}
            className="flex-1 bg-orange-600 hover:bg-orange-700 disabled:bg-orange-400 text-white text-sm font-medium py-2 px-4 rounded-md transition-colors"
          >
            {installing ? 'Installing...' : 'Install'}
          </button>
          <button
            onClick={handleDismiss}
            className="flex-1 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 text-sm font-medium py-2 px-4 rounded-md transition-colors"
          >
            Not now
          </button>
        </div>
        
        <div className="mt-2 text-xs text-gray-400 dark:text-gray-500">
          Free • No ads • Works offline
        </div>
      </div>
    </div>
  );
}
