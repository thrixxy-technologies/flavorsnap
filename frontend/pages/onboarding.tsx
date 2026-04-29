import React, { useState, useEffect } from 'react';
import { useTranslation } from 'next-i18next';
import Tutorial from '../components/Tutorial';
import { TutorialStep } from '../types';
import { api } from '../utils/api';

// Sample images for practice mode
const SAMPLE_IMAGES = [
  {
    id: 'sample-1',
    name: 'Jollof Rice',
    url: '/api/sample-images/jollof-rice.jpg',
    description: 'Classic Nigerian jollof rice with plantains'
  },
  {
    id: 'sample-2', 
    name: 'Egusi Soup',
    url: '/api/sample-images/egusi-soup.jpg',
    description: 'Traditional egusi soup with fufu'
  },
  {
    id: 'sample-3',
    name: 'Suya',
    url: '/api/sample-images/suya.jpg', 
    description: 'Spicy Nigerian suya meat'
  }
];

const Onboarding: React.FC = () => {
  const { t } = useTranslation('onboarding');
  const [tutorialStarted, setTutorialStarted] = useState(false);
  const [practiceMode, setPracticeMode] = useState(false);
  const [selectedSample, setSelectedSample] = useState<string | null>(null);
  const [recognitionResult, setRecognitionResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Tutorial steps for food recognition
  const tutorialSteps: TutorialStep[] = [
    {
      id: 'welcome',
      title: t('steps.welcome.title'),
      content: (
        <div>
          <p className="mb-4">{t('steps.welcome.content')}</p>
          <div className="bg-accent/10 p-4 rounded-lg">
            <h4 className="font-semibold mb-2">{t('steps.welcome.features_title')}</h4>
            <ul className="list-disc list-inside space-y-1 text-sm">
              <li>{t('steps.welcome.feature_1')}</li>
              <li>{t('steps.welcome.feature_2')}</li>
              <li>{t('steps.welcome.feature_3')}</li>
            </ul>
          </div>
        </div>
      ),
      position: 'center',
      skipable: true
    },
    {
      id: 'upload-area',
      title: t('steps.upload.title'),
      content: t('steps.upload.content'),
      target: '[data-testid="image-upload-area"]',
      position: 'top',
      action: {
        type: 'wait',
        delay: 2000
      },
      validation: {
        type: 'element_visible',
        target: '[data-testid="image-upload-area"]'
      }
    },
    {
      id: 'select-image',
      title: t('steps.select.title'),
      content: t('steps.select.content'),
      target: '[data-testid="file-input"]',
      position: 'bottom',
      action: {
        type: 'click',
        target: '[data-testid="file-input"]',
        delay: 1000
      }
    },
    {
      id: 'upload-progress',
      title: t('steps.progress.title'),
      content: t('steps.progress.content'),
      target: '[data-testid="upload-progress"]',
      position: 'top',
      skipable: true
    },
    {
      id: 'recognition-results',
      title: t('steps.results.title'),
      content: t('steps.results.content'),
      target: '[data-testid="recognition-results"]',
      position: 'bottom',
      validation: {
        type: 'element_visible',
        target: '[data-testid="recognition-results"]'
      }
    },
    {
      id: 'confidence-scores',
      title: t('steps.confidence.title'),
      content: t('steps.confidence.content'),
      target: '[data-testid="confidence-scores"]',
      position: 'left'
    },
    {
      id: 'practice-mode',
      title: t('steps.practice.title'),
      content: (
        <div>
          <p className="mb-4">{t('steps.practice.content')}</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {SAMPLE_IMAGES.map(sample => (
              <div
                key={sample.id}
                className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                  selectedSample === sample.id 
                    ? 'border-accent bg-accent/10' 
                    : 'border-gray-300 hover:border-accent/50'
                }`}
                onClick={() => setSelectedSample(sample.id)}
              >
                <img 
                  src={sample.url} 
                  alt={sample.name}
                  className="w-full h-32 object-cover rounded mb-2"
                />
                <h4 className="font-semibold text-sm">{sample.name}</h4>
                <p className="text-xs text-gray-600 dark:text-gray-400">{sample.description}</p>
              </div>
            ))}
          </div>
        </div>
      ),
      position: 'center',
      action: {
        type: 'click',
        target: '[data-testid="sample-image"]',
        delay: 1000
      }
    },
    {
      id: 'completion',
      title: t('steps.completion.title'),
      content: (
        <div>
          <p className="mb-4">{t('steps.completion.content')}</p>
          <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
            <h4 className="font-semibold text-green-800 dark:text-green-200 mb-2">
              {t('steps.completion.certificate_title')}
            </h4>
            <p className="text-green-700 dark:text-green-300">
              {t('steps.completion.certificate_content')}
            </p>
          </div>
        </div>
      ),
      position: 'center',
      skipable: false
    }
  ];

  const handleTutorialComplete = (progress: any) => {
    setTutorialStarted(false);
    
    // Save completion to analytics
    if (progress.interactions) {
      api.post('/api/analytics/tutorial-completion', {
        tutorialId: 'food-recognition-onboarding',
        userId: progress.userId,
        duration: progress.timeSpent,
        steps: progress.totalSteps,
        interactions: progress.interactions,
        completedAt: progress.completedAt
      }).catch(error => {
        console.warn('Failed to save tutorial analytics:', error);
      });
    }
  };

  const handleTutorialSkip = (reason: string) => {
    setTutorialStarted(false);
    
    // Track skip reason
    api.post('/api/analytics/tutorial-skip', {
      tutorialId: 'food-recognition-onboarding',
      reason,
      timestamp: new Date()
    }).catch(error => {
      console.warn('Failed to save tutorial skip analytics:', error);
    });
  };

  const handleSampleImageSelect = async (sampleId: string) => {
    const sample = SAMPLE_IMAGES.find(s => s.id === sampleId);
    if (!sample) return;

    setIsLoading(true);
    setSelectedSample(sampleId);

    try {
      // Simulate food recognition API call
      const response = await api.post('/api/classify', {
        imageUrl: sample.url,
        isSample: true
      });

      setRecognitionResult(response.data);
    } catch (error) {
      console.error('Failed to classify sample image:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const startPracticeMode = () => {
    setPracticeMode(true);
    setTutorialStarted(false);
  };

  const restartTutorial = () => {
    setTutorialStarted(true);
    setPracticeMode(false);
    setSelectedSample(null);
    setRecognitionResult(null);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            {t('title')}
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            {t('subtitle')}
          </p>
        </div>

        {/* Tutorial or Practice Mode */}
        {!tutorialStarted && !practiceMode && (
          <div className="max-w-4xl mx-auto">
            <div className="grid md:grid-cols-2 gap-8 mb-8">
              {/* Tutorial Option */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
                <div className="text-center mb-4">
                  <div className="w-16 h-16 bg-accent/10 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                    </svg>
                  </div>
                  <h3 className="text-xl font-semibold mb-2">{t('guided_tutorial')}</h3>
                  <p className="text-gray-600 dark:text-gray-400 mb-6">
                    {t('guided_tutorial_description')}
                  </p>
                </div>
                <button
                  onClick={() => setTutorialStarted(true)}
                  className="w-full bg-accent text-white py-3 rounded-lg hover:bg-accent/90 transition-colors font-medium"
                  aria-label={t('start_guided_tutorial')}
                >
                  {t('start_tutorial')}
                </button>
              </div>

              {/* Practice Mode Option */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
                <div className="text-center mb-4">
                  <div className="w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg className="w-8 h-8 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <h3 className="text-xl font-semibold mb-2">{t('practice_mode')}</h3>
                  <p className="text-gray-600 dark:text-gray-400 mb-6">
                    {t('practice_mode_description')}
                  </p>
                </div>
                <button
                  onClick={startPracticeMode}
                  className="w-full bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 transition-colors font-medium"
                  aria-label={t('start_practice_mode')}
                >
                  {t('start_practice')}
                </button>
              </div>
            </div>

            {/* Quick Access */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h3 className="text-lg font-semibold mb-4">{t('quick_access')}</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <button
                  onClick={() => setTutorialStarted(true)}
                  className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-accent/50 hover:bg-accent/5 transition-colors text-center"
                >
                  <svg className="w-6 h-6 mx-auto mb-2 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span className="text-sm font-medium">{t('quick_start')}</span>
                </button>
                <button
                  onClick={startPracticeMode}
                  className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-accent/50 hover:bg-accent/5 transition-colors text-center"
                >
                  <svg className="w-6 h-6 mx-auto mb-2 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  <span className="text-sm font-medium">{t('samples')}</span>
                </button>
                <button
                  className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-accent/50 hover:bg-accent/5 transition-colors text-center"
                  onClick={() => window.location.href = '/help'}
                >
                  <svg className="w-6 h-6 mx-auto mb-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-sm font-medium">{t('help')}</span>
                </button>
                <button
                  className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-accent/50 hover:bg-accent/5 transition-colors text-center"
                  onClick={() => window.location.href = '/settings'}
                >
                  <svg className="w-6 h-6 mx-auto mb-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c-.94 1.543.826 3.31 2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c.94-1.543-.826-3.31-2.37-2.37a1.724 1.724 0 00-2.572-1.065z" />
                  </svg>
                  <span className="text-sm font-medium">{t('settings')}</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Practice Mode */}
        {practiceMode && (
          <div className="max-w-4xl mx-auto">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-semibold">{t('practice_mode')}</h2>
                <button
                  onClick={() => setPracticeMode(false)}
                  className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                  aria-label={t('exit_practice')}
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="grid md:grid-cols-2 gap-8">
                {/* Sample Images */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">{t('sample_images')}</h3>
                  <div className="space-y-4">
                    {SAMPLE_IMAGES.map(sample => (
                      <div
                        key={sample.id}
                        data-testid="sample-image"
                        className={`border rounded-lg p-4 cursor-pointer transition-all ${
                          selectedSample === sample.id
                            ? 'border-accent bg-accent/10'
                            : 'border-gray-200 dark:border-gray-700 hover:border-accent/50'
                        } ${isLoading && selectedSample === sample.id ? 'opacity-50' : ''}`}
                        onClick={() => !isLoading && handleSampleImageSelect(sample.id)}
                      >
                        <div className="flex items-center space-x-4">
                          <img
                            src={sample.url}
                            alt={sample.name}
                            className="w-20 h-20 object-cover rounded"
                          />
                          <div className="flex-1">
                            <h4 className="font-semibold">{sample.name}</h4>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              {sample.description}
                            </p>
                          </div>
                          {selectedSample === sample.id && (
                            <div className="text-accent">
                              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Recognition Results */}
                <div>
                  <h3 className="text-lg font-semibold mb-4">{t('recognition_results')}</h3>
                  {recognitionResult ? (
                    <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
                      <div className="space-y-3">
                        <div className="flex justify-between items-center">
                          <span className="font-medium">{t('predicted_class')}</span>
                          <span className="text-accent font-semibold">
                            {recognitionResult.predictedClass}
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="font-medium">{t('confidence')}</span>
                          <span className="text-accent">
                            {(recognitionResult.confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                        {recognitionResult.allPredictions && (
                          <div>
                            <h4 className="font-medium mb-2">{t('all_predictions')}</h4>
                            <div className="space-y-2">
                              {recognitionResult.allPredictions.map((pred: any, index: number) => (
                                <div key={index} className="flex justify-between items-center">
                                  <span>{pred.class}</span>
                                  <span className="text-sm text-gray-600 dark:text-gray-400">
                                    {(pred.confidence * 100).toFixed(1)}%
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <svg className="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      <p>{t('select_image_to_start')}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tutorial Component */}
        {tutorialStarted && (
          <Tutorial
            steps={tutorialSteps}
            onComplete={handleTutorialComplete}
            onSkip={handleTutorialSkip}
            analytics={{
              enabled: true,
              onProgress: (analytics) => {
                console.log('Tutorial progress:', analytics);
              }
            }}
            autoStart={true}
            showSkipButton={true}
            showProgress={true}
            allowKeyboardNavigation={true}
          />
        )}

        {/* Restart Options */}
        {(tutorialStarted || practiceMode) && (
          <div className="text-center mt-8">
            <button
              onClick={restartTutorial}
              className="text-accent hover:text-accent/80 transition-colors"
            >
              {t('restart_onboarding')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Onboarding;
