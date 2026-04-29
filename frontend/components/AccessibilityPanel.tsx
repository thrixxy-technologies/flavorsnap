import React, { useState, useEffect, useRef } from 'react';
import { 
  Eye, 
  EyeOff, 
  Type, 
  MousePointer, 
  Keyboard, 
  Volume2, 
  VolumeX, 
  Contrast, 
  Sun, 
  Moon, 
  Settings, 
  X, 
  Check, 
  ChevronRight,
  AlertCircle,
  HelpCircle,
  Zap,
  Target
} from 'lucide-react';

export interface AccessibilitySettings {
  // Visual settings
  highContrast: boolean;
  largeText: boolean;
  reducedMotion: boolean;
  focusVisible: boolean;
  darkMode: boolean;
  
  // Navigation settings
  keyboardNavigation: boolean;
  skipLinks: boolean;
  focusTraps: boolean;
  
  // Screen reader settings
  screenReaderOptimized: boolean;
  ariaLabels: boolean;
  liveRegions: boolean;
  
  // Interaction settings
  clickDelay: boolean;
  hoverDelay: boolean;
  errorAnnouncements: boolean;
  
  // Font settings
  fontSize: number;
  lineHeight: number;
  letterSpacing: number;
  
  // Color settings
  colorBlindness: 'none' | 'protanopia' | 'deuteranopia' | 'tritanopia';
  saturation: number;
}

interface AccessibilityPanelProps {
  className?: string;
  onSettingsChange?: (settings: AccessibilitySettings) => void;
  isOpen?: boolean;
  onClose?: () => void;
}

const DEFAULT_SETTINGS: AccessibilitySettings = {
  highContrast: false,
  largeText: false,
  reducedMotion: false,
  focusVisible: true,
  darkMode: false,
  keyboardNavigation: true,
  skipLinks: true,
  focusTraps: false,
  screenReaderOptimized: false,
  ariaLabels: true,
  liveRegions: true,
  clickDelay: false,
  hoverDelay: false,
  errorAnnouncements: true,
  fontSize: 16,
  lineHeight: 1.5,
  letterSpacing: 0,
  colorBlindness: 'none',
  saturation: 100
};

const AccessibilityPanel: React.FC<AccessibilityPanelProps> = ({
  className = '',
  onSettingsChange,
  isOpen = false,
  onClose
}) => {
  const [settings, setSettings] = useState<AccessibilitySettings>(DEFAULT_SETTINGS);
  const [activeSection, setActiveSection] = useState<string>('visual');
  const [testMode, setTestMode] = useState<string>('');
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const savedSettings = localStorage.getItem('accessibility-settings');
    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings);
        setSettings({ ...DEFAULT_SETTINGS, ...parsed });
      } catch (error) {
        console.error('Failed to load accessibility settings:', error);
      }
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('accessibility-settings', JSON.stringify(settings));
    onSettingsChange?.(settings);
    applyAccessibilitySettings(settings);
  }, [settings, onSettingsChange]);

  useEffect(() => {
    if (isOpen && panelRef.current) {
      panelRef.current.focus();
    }
  }, [isOpen]);

  const applyAccessibilitySettings = (currentSettings: AccessibilitySettings) => {
    const root = document.documentElement;
    
    // Apply visual settings
    root.setAttribute('data-high-contrast', currentSettings.highContrast.toString());
    root.setAttribute('data-large-text', currentSettings.largeText.toString());
    root.setAttribute('data-reduced-motion', currentSettings.reducedMotion.toString());
    root.setAttribute('data-focus-visible', currentSettings.focusVisible.toString());
    root.setAttribute('data-dark-mode', currentSettings.darkMode.toString());
    
    // Apply font settings
    root.style.setProperty('--font-size-base', `${currentSettings.fontSize}px`);
    root.style.setProperty('--line-height-base', currentSettings.lineHeight.toString());
    root.style.setProperty('--letter-spacing-base', `${currentSettings.letterSpacing}px`);
    
    // Apply color settings
    root.setAttribute('data-color-blindness', currentSettings.colorBlindness);
    root.style.setProperty('--saturation', `${currentSettings.saturation}%`);
    
    // Apply screen reader optimizations
    root.setAttribute('data-screen-reader', currentSettings.screenReaderOptimized.toString());
    root.setAttribute('data-aria-labels', currentSettings.ariaLabels.toString());
    root.setAttribute('data-live-regions', currentSettings.liveRegions.toString());
    
    // Add CSS classes for immediate visual feedback
    document.body.classList.toggle('high-contrast', currentSettings.highContrast);
    document.body.classList.toggle('large-text', currentSettings.largeText);
    document.body.classList.toggle('reduced-motion', currentSettings.reducedMotion);
    document.body.classList.toggle('dark-mode', currentSettings.darkMode);
    document.body.classList.toggle('screen-reader-opt', currentSettings.screenReaderOptimized);
  };

  const updateSetting = <K extends keyof AccessibilitySettings>(
    key: K,
    value: AccessibilitySettings[K]
  ) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const resetSettings = () => {
    setSettings(DEFAULT_SETTINGS);
  };

  const runAccessibilityTest = (testType: string) => {
    setTestMode(testType);
    
    switch (testType) {
      case 'keyboard':
        announceToScreenReader('Keyboard navigation test started. Use Tab key to navigate.');
        break;
      case 'contrast':
        announceToScreenReader('High contrast test activated. Check visibility of all elements.');
        break;
      case 'screen-reader':
        announceToScreenReader('Screen reader test started. Listening for announcements.');
        break;
      case 'focus':
        announceToScreenReader('Focus indicator test started. Tab through elements to check focus visibility.');
        break;
      default:
        break;
    }
    
    setTimeout(() => setTestMode(''), 5000);
  };

  const announceToScreenReader = (message: string) => {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    document.body.appendChild(announcement);
    
    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  };

  const sections = [
    {
      id: 'visual',
      title: 'Visual',
      icon: <Eye className="w-4 h-4" />,
      description: 'Adjust visual appearance'
    },
    {
      id: 'navigation',
      title: 'Navigation',
      icon: <Keyboard className="w-4 h-4" />,
      description: 'Keyboard and navigation options'
    },
    {
      id: 'screen-reader',
      title: 'Screen Reader',
      icon: <Volume2 className="w-4 h-4" />,
      description: 'Screen reader optimizations'
    },
    {
      id: 'interaction',
      title: 'Interaction',
      icon: <MousePointer className="w-4 h-4" />,
      description: 'Interaction preferences'
    },
    {
      id: 'testing',
      title: 'Testing',
      icon: <Target className="w-4 h-4" />,
      description: 'Test accessibility features'
    }
  ];

  const renderVisualSettings = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">High Contrast</h4>
          <p className="text-sm text-gray-500">Increase contrast for better visibility</p>
        </div>
        <button
          onClick={() => updateSetting('highContrast', !settings.highContrast)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.highContrast ? 'bg-blue-600' : 'bg-gray-200'
          }`}
          role="switch"
          aria-checked={settings.highContrast}
          aria-label="Toggle high contrast mode"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.highContrast ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">Large Text</h4>
          <p className="text-sm text-gray-500">Increase font size for better readability</p>
        </div>
        <button
          onClick={() => updateSetting('largeText', !settings.largeText)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.largeText ? 'bg-blue-600' : 'bg-gray-200'
          }`}
          role="switch"
          aria-checked={settings.largeText}
          aria-label="Toggle large text mode"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.largeText ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">Reduced Motion</h4>
          <p className="text-sm text-gray-500">Minimize animations and transitions</p>
        </div>
        <button
          onClick={() => updateSetting('reducedMotion', !settings.reducedMotion)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.reducedMotion ? 'bg-blue-600' : 'bg-gray-200'
          }`}
          role="switch"
          aria-checked={settings.reducedMotion}
          aria-label="Toggle reduced motion"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.reducedMotion ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">Dark Mode</h4>
          <p className="text-sm text-gray-500">Switch to dark color theme</p>
        </div>
        <button
          onClick={() => updateSetting('darkMode', !settings.darkMode)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.darkMode ? 'bg-blue-600' : 'bg-gray-200'
          }`}
          role="switch"
          aria-checked={settings.darkMode}
          aria-label="Toggle dark mode"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.darkMode ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      <div>
        <h4 className="font-medium mb-2">Font Size</h4>
        <div className="flex items-center gap-2">
          <button
            onClick={() => updateSetting('fontSize', Math.max(12, settings.fontSize - 2))}
            className="p-1 rounded hover:bg-gray-100"
            aria-label="Decrease font size"
          >
            <Type className="w-4 h-4" />
          </button>
          <span className="px-3 py-1 bg-gray-100 rounded text-sm min-w-[60px] text-center">
            {settings.fontSize}px
          </span>
          <button
            onClick={() => updateSetting('fontSize', Math.min(24, settings.fontSize + 2))}
            className="p-1 rounded hover:bg-gray-100"
            aria-label="Increase font size"
          >
            <Type className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div>
        <h4 className="font-medium mb-2">Color Blindness Mode</h4>
        <select
          value={settings.colorBlindness}
          onChange={(e) => updateSetting('colorBlindness', e.target.value as any)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Select color blindness mode"
        >
          <option value="none">None</option>
          <option value="protanopia">Protanopia (Red-blind)</option>
          <option value="deuteranopia">Deuteranopia (Green-blind)</option>
          <option value="tritanopia">Tritanopia (Blue-blind)</option>
        </select>
      </div>
    </div>
  );

  const renderNavigationSettings = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">Keyboard Navigation</h4>
          <p className="text-sm text-gray-500">Enable keyboard shortcuts and navigation</p>
        </div>
        <button
          onClick={() => updateSetting('keyboardNavigation', !settings.keyboardNavigation)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.keyboardNavigation ? 'bg-blue-600' : 'bg-gray-200'
          }`}
          role="switch"
          aria-checked={settings.keyboardNavigation}
          aria-label="Toggle keyboard navigation"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.keyboardNavigation ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">Skip Links</h4>
          <p className="text-sm text-gray-500">Show skip links for quick navigation</p>
        </div>
        <button
          onClick={() => updateSetting('skipLinks', !settings.skipLinks)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.skipLinks ? 'bg-blue-600' : 'bg-gray-200'
          }`}
          role="switch"
          aria-checked={settings.skipLinks}
          aria-label="Toggle skip links"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.skipLinks ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">Focus Traps</h4>
          <p className="text-sm text-gray-500">Trap focus within modal dialogs</p>
        </div>
        <button
          onClick={() => updateSetting('focusTraps', !settings.focusTraps)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.focusTraps ? 'bg-blue-600' : 'bg-gray-200'
          }`}
          role="switch"
          aria-checked={settings.focusTraps}
          aria-label="Toggle focus traps"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.focusTraps ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>
    </div>
  );

  const renderScreenReaderSettings = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">Screen Reader Optimized</h4>
          <p className="text-sm text-gray-500">Optimize interface for screen readers</p>
        </div>
        <button
          onClick={() => updateSetting('screenReaderOptimized', !settings.screenReaderOptimized)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.screenReaderOptimized ? 'bg-blue-600' : 'bg-gray-200'
          }`}
          role="switch"
          aria-checked={settings.screenReaderOptimized}
          aria-label="Toggle screen reader optimization"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.screenReaderOptimized ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">ARIA Labels</h4>
          <p className="text-sm text-gray-500">Enhance ARIA labels and descriptions</p>
        </div>
        <button
          onClick={() => updateSetting('ariaLabels', !settings.ariaLabels)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.ariaLabels ? 'bg-blue-600' : 'bg-gray-200'
          }`}
          role="switch"
          aria-checked={settings.ariaLabels}
          aria-label="Toggle ARIA labels"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.ariaLabels ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">Live Regions</h4>
          <p className="text-sm text-gray-500">Announce dynamic content changes</p>
        </div>
        <button
          onClick={() => updateSetting('liveRegions', !settings.liveRegions)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.liveRegions ? 'bg-blue-600' : 'bg-gray-200'
          }`}
          role="switch"
          aria-checked={settings.liveRegions}
          aria-label="Toggle live regions"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.liveRegions ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">Error Announcements</h4>
          <p className="text-sm text-gray-500">Announce form errors and validation messages</p>
        </div>
        <button
          onClick={() => updateSetting('errorAnnouncements', !settings.errorAnnouncements)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.errorAnnouncements ? 'bg-blue-600' : 'bg-gray-200'
          }`}
          role="switch"
          aria-checked={settings.errorAnnouncements}
          aria-label="Toggle error announcements"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.errorAnnouncements ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>
    </div>
  );

  const renderInteractionSettings = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">Click Delay</h4>
          <p className="text-sm text-gray-500">Add delay to prevent accidental clicks</p>
        </div>
        <button
          onClick={() => updateSetting('clickDelay', !settings.clickDelay)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.clickDelay ? 'bg-blue-600' : 'bg-gray-200'
          }`}
          role="switch"
          aria-checked={settings.clickDelay}
          aria-label="Toggle click delay"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.clickDelay ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">Hover Delay</h4>
          <p className="text-sm text-gray-500">Add delay to hover interactions</p>
        </div>
        <button
          onClick={() => updateSetting('hoverDelay', !settings.hoverDelay)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            settings.hoverDelay ? 'bg-blue-600' : 'bg-gray-200'
          }`}
          role="switch"
          aria-checked={settings.hoverDelay}
          aria-label="Toggle hover delay"
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.hoverDelay ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>
    </div>
  );

  const renderTestingTools = () => (
    <div className="space-y-4">
      <div className="bg-blue-50 p-4 rounded-lg">
        <h4 className="font-medium text-blue-900 mb-2">Accessibility Testing Tools</h4>
        <p className="text-sm text-blue-700 mb-4">
          Test different accessibility features to ensure they work correctly
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={() => runAccessibilityTest('keyboard')}
          className={`p-3 rounded-lg border transition-colors ${
            testMode === 'keyboard' 
              ? 'bg-blue-50 border-blue-300 text-blue-700' 
              : 'border-gray-300 hover:bg-gray-50'
          }`}
          aria-label="Run keyboard navigation test"
        >
          <Keyboard className="w-5 h-5 mx-auto mb-1" />
          <span className="text-sm">Keyboard Test</span>
        </button>

        <button
          onClick={() => runAccessibilityTest('contrast')}
          className={`p-3 rounded-lg border transition-colors ${
            testMode === 'contrast' 
              ? 'bg-blue-50 border-blue-300 text-blue-700' 
              : 'border-gray-300 hover:bg-gray-50'
          }`}
          aria-label="Run contrast test"
        >
          <Contrast className="w-5 h-5 mx-auto mb-1" />
          <span className="text-sm">Contrast Test</span>
        </button>

        <button
          onClick={() => runAccessibilityTest('screen-reader')}
          className={`p-3 rounded-lg border transition-colors ${
            testMode === 'screen-reader' 
              ? 'bg-blue-50 border-blue-300 text-blue-700' 
              : 'border-gray-300 hover:bg-gray-50'
          }`}
          aria-label="Run screen reader test"
        >
          <Volume2 className="w-5 h-5 mx-auto mb-1" />
          <span className="text-sm">Screen Reader</span>
        </button>

        <button
          onClick={() => runAccessibilityTest('focus')}
          className={`p-3 rounded-lg border transition-colors ${
            testMode === 'focus' 
              ? 'bg-blue-50 border-blue-300 text-blue-700' 
              : 'border-gray-300 hover:bg-gray-50'
          }`}
          aria-label="Run focus indicator test"
        >
          <Target className="w-5 h-5 mx-auto mb-1" />
          <span className="text-sm">Focus Test</span>
        </button>
      </div>

      {testMode && (
        <div className="bg-green-50 p-3 rounded-lg border border-green-200">
          <div className="flex items-center gap-2">
            <Check className="w-4 h-4 text-green-600" />
            <span className="text-sm text-green-700">
              {testMode} test is running...
            </span>
          </div>
        </div>
      )}
    </div>
  );

  const renderContent = () => {
    switch (activeSection) {
      case 'visual':
        return renderVisualSettings();
      case 'navigation':
        return renderNavigationSettings();
      case 'screen-reader':
        return renderScreenReaderSettings();
      case 'interaction':
        return renderInteractionSettings();
      case 'testing':
        return renderTestingTools();
      default:
        return renderVisualSettings();
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div
        ref={panelRef}
        className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="accessibility-panel-title"
        tabIndex={-1}
      >
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Settings className="w-6 h-6 text-gray-600" />
              <h2 id="accessibility-panel-title" className="text-xl font-semibold">
                Accessibility Settings
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="Close accessibility panel"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="flex h-[600px]">
          {/* Sidebar */}
          <div className="w-64 border-r border-gray-200 p-4">
            <nav role="navigation" aria-label="Accessibility sections">
              <ul className="space-y-2">
                {sections.map(section => (
                  <li key={section.id}>
                    <button
                      onClick={() => setActiveSection(section.id)}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors text-left ${
                        activeSection === section.id
                          ? 'bg-blue-50 text-blue-700 border border-blue-200'
                          : 'hover:bg-gray-50 text-gray-700'
                      }`}
                      aria-current={activeSection === section.id ? 'page' : undefined}
                    >
                      {section.icon}
                      <div>
                        <div className="font-medium">{section.title}</div>
                        <div className="text-xs text-gray-500">{section.description}</div>
                      </div>
                      <ChevronRight className="w-4 h-4 ml-auto" />
                    </button>
                  </li>
                ))}
              </ul>
            </nav>

            <div className="mt-6 pt-6 border-t border-gray-200">
              <button
                onClick={resetSettings}
                className="w-full px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                aria-label="Reset all accessibility settings to default"
              >
                Reset to Default
              </button>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 p-6 overflow-y-auto">
            <div className="max-w-2xl">
              {renderContent()}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <HelpCircle className="w-4 h-4" />
              <span>Need help? Visit our accessibility guide</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Settings saved automatically</span>
              <Check className="w-4 h-4 text-green-500" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AccessibilityPanel;
