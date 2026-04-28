import React, { useState } from 'react';
import { ClassificationResult } from './ClassificationResult';
import { ImageUpload } from './ImageUpload';

interface Prediction {
  class: string;
  confidence: number;
}

const mockPredictions: Prediction[] = [
  { class: 'Akara', confidence: 0.92 },
  { class: 'Bread', confidence: 0.05 },
  { class: 'Egusi', confidence: 0.02 },
  { class: 'Moi Moi', confidence: 0.01 }
];

const mediumConfidencePredictions: Prediction[] = [
  { class: 'Bread', confidence: 0.68 },
  { class: 'Akara', confidence: 0.22 },
  { class: 'Moi Moi', confidence: 0.10 }
];

const lowConfidencePredictions: Prediction[] = [
  { class: 'Egusi', confidence: 0.45 },
  { class: 'Moi Moi', confidence: 0.35 },
  { class: 'Akara', confidence: 0.20 }
];

export function ClassificationDemo() {
  const [selectedDemo, setSelectedDemo] = useState<'high' | 'medium' | 'low' | 'loading'>('high');
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);

  const handleImageSelect = (file: File, imageUrl: string) => {
    setUploadedImage(imageUrl);
    setSelectedDemo('high');
  };

  const getPredictions = (): Prediction[] => {
    switch (selectedDemo) {
      case 'high':
        return mockPredictions;
      case 'medium':
        return mediumConfidencePredictions;
      case 'low':
        return lowConfidencePredictions;
      case 'loading':
        return [];
      default:
        return mockPredictions;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-center text-gray-800 dark:text-gray-200 mb-8">
          Classification Result Animation Demo
        </h1>

        {/* Demo Controls */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-4">
            Demo Controls
          </h2>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <button
              onClick={() => setSelectedDemo('high')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedDemo === 'high'
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              High Confidence
            </button>
            <button
              onClick={() => setSelectedDemo('medium')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedDemo === 'medium'
                  ? 'bg-yellow-500 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              Medium Confidence
            </button>
            <button
              onClick={() => setSelectedDemo('low')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedDemo === 'low'
                  ? 'bg-red-500 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              Low Confidence
            </button>
            <button
              onClick={() => setSelectedDemo('loading')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedDemo === 'loading'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              Loading State
            </button>
          </div>

          {/* Feature Checklist */}
          <div className="border-t pt-4">
            <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-3">
              Features Implemented:
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs">✓</span>
                </div>
                <span className="text-gray-700 dark:text-gray-300">Circular progress indicator</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs">✓</span>
                </div>
                <span className="text-gray-700 dark:text-gray-300">Top 3 predictions breakdown</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs">✓</span>
                </div>
                <span className="text-gray-700 dark:text-gray-300">Particle effects (&gt;80% confidence)</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs">✓</span>
                </div>
                <span className="text-gray-700 dark:text-gray-300">Sound effects (high confidence)</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs">✓</span>
                </div>
                <span className="text-gray-700 dark:text-gray-300">60fps optimized animations</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs">✓</span>
                </div>
                <span className="text-gray-700 dark:text-gray-300">Reduced motion support</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs">✓</span>
                </div>
                <span className="text-gray-700 dark:text-gray-300">Loading skeleton states</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs">✓</span>
                </div>
                <span className="text-gray-700 dark:text-gray-300">Smooth confidence animations</span>
              </div>
            </div>
          </div>
        </div>

        {/* Image Upload Section */}
        {!uploadedImage && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8">
            <h2 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-4">
              Upload an Image
            </h2>
            <ImageUpload onImageSelect={handleImageSelect} />
          </div>
        )}

        {/* Classification Result */}
        <ClassificationResult
          predictions={getPredictions()}
          loading={selectedDemo === 'loading'}
          imageUrl={uploadedImage || undefined}
        />

        {/* Instructions */}
        <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-800 dark:text-blue-200 mb-3">
            How to Test
          </h3>
          <ul className="space-y-2 text-blue-700 dark:text-blue-300">
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>Click the confidence buttons to see different animation states</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>Try "High Confidence" to see particle effects and hear sound effects</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>Upload an image to see the component with real image preview</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>Test reduced motion by enabling it in your browser settings</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>Watch the circular progress animate smoothly from 0 to final confidence</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
