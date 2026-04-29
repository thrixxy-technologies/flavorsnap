'use client';

import React, { useEffect, useState } from 'react';
import { useVoiceRecognition } from '@/hooks/useVoiceRecognition';

export const VoiceInterface: React.FC = () => {
  const {
    isListening,
    transcript,
    confidence,
    language,
    error,
    startListening,
    stopListening,
    changeLanguage,
    getSupportedLanguages,
    convertTextToSpeech,
  } = useVoiceRecognition();

  const [supportedLanguages, setSupportedLanguages] = useState<any[]>([]);
  const [feedbackText, setFeedbackText] = useState('');

  useEffect(() => {
    setSupportedLanguages(getSupportedLanguages());
  }, [getSupportedLanguages]);

  const handleLanguageChange = (newLanguage: string) => {
    changeLanguage(newLanguage as any);
    convertTextToSpeech(`Language changed to ${newLanguage}`, newLanguage as any);
  };

  const handleListenClick = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
      convertTextToSpeech('Listening...', language);
    }
  };

  const handleClearTranscript = () => {
    setFeedbackText('');
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-gradient-to-b from-blue-50 to-indigo-50 rounded-lg shadow-lg">
      <h1 className="text-3xl font-bold mb-6 text-center text-gray-900">🎤 Voice Recognition</h1>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
          <p>{error}</p>
        </div>
      )}

      {/* Language Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Language
        </label>
        <select
          value={language}
          onChange={(e) => handleLanguageChange(e.target.value)}
          className="w-full p-3 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {supportedLanguages.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.name}
            </option>
          ))}
        </select>
      </div>

      {/* Transcript Display */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Transcript
        </label>
        <div className="p-4 bg-white border-2 border-gray-300 rounded-lg min-h-24 max-h-48 overflow-y-auto">
          <p className="text-gray-800 leading-relaxed">
            {transcript || <span className="text-gray-400">Start speaking...</span>}
          </p>
          {confidence > 0 && (
            <p className="text-xs text-gray-500 mt-2">
              Confidence: {(confidence * 100).toFixed(1)}%
            </p>
          )}
        </div>
      </div>

      {/* Listening Indicator */}
      <div className="mb-6 flex items-center justify-center">
        <div
          className={`w-16 h-16 rounded-full flex items-center justify-center transition-all ${
            isListening
              ? 'bg-red-500 animate-pulse'
              : 'bg-gray-300'
          }`}
        >
          <span className="text-white text-2xl">
            {isListening ? '🔴' : '⭕'}
          </span>
        </div>
      </div>

      {/* Main Controls */}
      <div className="grid grid-cols-2 gap-3 mb-6">
        <button
          onClick={handleListenClick}
          className={`px-6 py-3 rounded-lg font-bold text-white transition transform ${
            isListening
              ? 'bg-red-500 hover:bg-red-600 active:scale-95'
              : 'bg-blue-500 hover:bg-blue-600 active:scale-95'
          }`}
        >
          {isListening ? '⏹️ Stop' : '🎤 Listen'}
        </button>
        <button
          onClick={handleClearTranscript}
          className="px-6 py-3 bg-gray-500 hover:bg-gray-600 text-white rounded-lg font-bold transition transform active:scale-95"
        >
          🗑️ Clear
        </button>
      </div>

      {/* Quick Commands */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Quick Voice Commands</h3>
        <div className="grid grid-cols-2 gap-2">
          {[
            { label: 'Recognize', text: 'recognize' },
            { label: 'Nutrition', text: 'show nutrition' },
            { label: 'Recipes', text: 'show recipes' },
            { label: 'History', text: 'show history' },
          ].map((cmd) => (
            <button
              key={cmd.label}
              onClick={() => {
                setFeedbackText(cmd.text);
                convertTextToSpeech(`${cmd.label} command activated`, language);
              }}
              className="p-2 bg-indigo-100 hover:bg-indigo-200 text-indigo-700 rounded-lg text-sm font-medium transition"
            >
              {cmd.label}
            </button>
          ))}
        </div>
      </div>

      {/* Feedback Section */}
      {feedbackText && (
        <div className="p-4 bg-green-100 border border-green-400 text-green-700 rounded-lg">
          <p className="font-medium">✓ Command Recognized</p>
          <p className="text-sm mt-1">{feedbackText}</p>
        </div>
      )}

      {/* Info Box */}
      <div className="mt-6 p-4 bg-blue-100 border border-blue-300 rounded-lg text-sm text-blue-800">
        <p className="font-medium mb-2">💡 Tips:</p>
        <ul className="list-disc list-inside space-y-1 text-xs">
          <li>Speak clearly and naturally</li>
          <li>Wait for the listening indicator before speaking</li>
          <li>Try commands like "recognize" or "nutrition"</li>
          <li>Your voice data is encrypted and private</li>
        </ul>
      </div>
    </div>
  );
};
