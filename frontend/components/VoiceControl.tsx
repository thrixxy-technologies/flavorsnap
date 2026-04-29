"use client";
import React, { useEffect, useState } from 'react';
import { useVoiceCommands, VoiceCommand, Language } from '@/hooks/useVoiceCommands';

interface VoiceControlProps {
  onCommand: (command: VoiceCommand) => void;
  className?: string;
  showLanguageSelector?: boolean;
  disabled?: boolean;
}

export const VoiceControl: React.FC<VoiceControlProps> = ({
  onCommand,
  className = '',
  showLanguageSelector = true,
  disabled = false,
}) => {
  const {
    isListening,
    isSupported,
    transcript,
    status,
    error,
    language,
    startListening,
    stopListening,
    toggleListening,
    changeLanguage,
    phrases,
  } = useVoiceCommands();

  const [lastCommand, setLastCommand] = useState<VoiceCommand | null>(null);

  // Process commands and notify parent
  useEffect(() => {
    if (transcript && !isListening) {
      const command = processTranscript(transcript);
      if (command) {
        setLastCommand(command);
        onCommand(command);
      }
    }
  }, [transcript, isListening, onCommand]);

  const processTranscript = (text: string): VoiceCommand | null => {
    const lowerText = text.toLowerCase();
    
    // Simple command matching (in real implementation, use more sophisticated matching)
    if (lowerText.includes('upload') || lowerText.includes('open') || lowerText.includes('camera')) {
      return 'upload';
    }
    if (lowerText.includes('classify') || lowerText.includes('analyze') || lowerText.includes('identify')) {
      return 'classify';
    }
    if (lowerText.includes('reset') || lowerText.includes('clear') || lowerText.includes('start over')) {
      return 'reset';
    }
    if (lowerText.includes('help')) {
      return 'help';
    }
    if (lowerText.includes('cancel') || lowerText.includes('stop')) {
      return 'cancel';
    }
    
    return null;
  };

  const handleLanguageChange = (newLanguage: Language) => {
    changeLanguage(newLanguage);
  };

  if (!isSupported) {
    return (
      <div className={`p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg ${className}`}>
        <div className="flex items-center gap-2 text-yellow-800 dark:text-yellow-200">
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <span className="text-sm">{phrases.notSupported}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Voice Control Button */}
      <button
        onClick={toggleListening}
        disabled={disabled}
        className={`
          relative inline-flex items-center justify-center gap-2 px-4 py-3 rounded-lg
          transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-500
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105 active:scale-95'}
          ${isListening 
            ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse' 
            : 'bg-indigo-500 hover:bg-indigo-600 text-white'
          }
        `}
        aria-label={isListening ? 'Stop listening' : 'Start voice control'}
      >
        {/* Microphone Icon */}
        <svg 
          className="w-5 h-5" 
          fill="currentColor" 
          viewBox="0 0 20 20"
          xmlns="http://www.w3.org/2000/svg"
        >
          {isListening ? (
            // Recording icon
            <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
          ) : (
            // Microphone icon
            <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
          )}
        </svg>
        
        <span className="font-medium">
          {isListening ? phrases.listening : phrases.ready}
        </span>
        
        {/* Visual feedback for listening */}
        {isListening && (
          <span className="absolute top-0 right-0 w-3 h-3 bg-red-500 rounded-full animate-ping" />
        )}
      </button>

      {/* Status and Transcript */}
      {(status || transcript || error) && (
        <div className="space-y-2">
          {status && (
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {status}
            </div>
          )}
          
          {transcript && (
            <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                "{transcript}"
              </div>
              {lastCommand && (
                <div className="text-xs text-indigo-600 dark:text-indigo-400 mt-1">
                  Command: {lastCommand}
                </div>
              )}
            </div>
          )}
          
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <div className="text-sm text-red-800 dark:text-red-200">
                {error}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Language Selector */}
      {showLanguageSelector && (
        <div className="flex flex-wrap gap-2">
          <span className="text-sm text-gray-600 dark:text-gray-400 self-center">
            Language:
          </span>
          {(['en', 'fr', 'ar', 'yo'] as Language[]).map((lang) => (
            <button
              key={lang}
              onClick={() => handleLanguageChange(lang)}
              className={`
                px-3 py-1 text-sm rounded-lg transition-colors
                ${language === lang
                  ? 'bg-indigo-500 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                }
              `}
            >
              {lang === 'en' ? 'English' : 
               lang === 'fr' ? 'Français' : 
               lang === 'ar' ? 'العربية' : 
               'Yorùbá'}
            </button>
          ))}
        </div>
      )}

      {/* Help Text */}
      <div className="text-xs text-gray-500 dark:text-gray-400">
        {phrases.commands}
      </div>
    </div>
  );
};
