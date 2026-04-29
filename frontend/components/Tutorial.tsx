import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'next-i18next';
import { 
  TutorialStep, 
  TutorialState, 
  TutorialProgress, 
  TutorialAnalytics 
} from '../types';

interface TutorialProps {
  steps: TutorialStep[];
  onComplete?: (progress: TutorialProgress) => void;
  onSkip?: (reason: string) => void;
  onStepChange?: (stepIndex: number) => void;
  analytics?: {
    enabled: boolean;
    onProgress?: (analytics: TutorialAnalytics) => void;
  };
  autoStart?: boolean;
  showSkipButton?: boolean;
  showProgress?: boolean;
  allowKeyboardNavigation?: boolean;
  className?: string;
}

export function Tutorial({
  steps,
  onComplete,
  onSkip,
  onStepChange,
  analytics,
  autoStart = false,
  showSkipButton = true,
  showProgress = true,
  allowKeyboardNavigation = true,
  className = ''
}: TutorialProps) {
  const { t } = useTranslation('tutorial');
  const [tutorialState, setTutorialState] = useState<TutorialState>({
    isActive: autoStart,
    currentStep: 0,
    steps,
    isCompleted: false,
    isPaused: false,
    progress: 0
  });
  
  const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | null>(null);
  const [isInteracting, setIsInteracting] = useState(false);
  const [swipeDirection, setSwipeDirection] = useState<'left' | 'right' | null>(null);
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);
  
  const tutorialRef = useRef<HTMLDivElement>(null);
  const progressRef = useRef<TutorialProgress>({
    tutorialId: 'food-recognition-tutorial',
    startedAt: new Date(),
    currentStep: 0,
    totalSteps: steps.length,
    timeSpent: 0,
    skipped: false,
    interactions: []
  });

  // Calculate progress
  useEffect(() => {
    const progress = tutorialState.isCompleted ? 100 : (tutorialState.currentStep / tutorialState.steps.length) * 100;
    setTutorialState(prev => ({ ...prev, progress }));
  }, [tutorialState.currentStep, tutorialState.steps.length, tutorialState.isCompleted]);

  // Keyboard navigation
  useEffect(() => {
    if (!allowKeyboardNavigation || !tutorialState.isActive) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (isInteracting) return;

      switch (e.key) {
        case 'ArrowRight':
        case ' ':
          e.preventDefault();
          handleNext();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          handlePrevious();
          break;
        case 'Escape':
          e.preventDefault();
          handleSkip('user_cancelled');
          break;
        case 'Enter':
          e.preventDefault();
          handleStepAction();
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [allowKeyboardNavigation, tutorialState.isActive, tutorialState.currentStep, isInteracting]);

  // Touch/swipe handling for mobile
  useEffect(() => {
    if (!tutorialState.isActive) return;

    const handleTouchStart = (e: TouchEvent) => {
      setTouchStart({ x: e.touches[0].clientX, y: e.touches[0].clientY });
    };

    const handleTouchEnd = (e: TouchEvent) => {
      if (!touchStart) return;

      const touchEnd = { x: e.changedTouches[0].clientX, y: e.changedTouches[0].clientY };
      const deltaX = touchEnd.x - touchStart.x;
      const deltaY = touchEnd.y - touchStart.y;

      // Minimum swipe distance
      if (Math.abs(deltaX) > 50 && Math.abs(deltaY) < 100) {
        setSwipeDirection(deltaX > 0 ? 'right' : 'left');
        setTimeout(() => setSwipeDirection(null), 300);

        if (deltaX > 0) {
          handlePrevious();
        } else {
          handleNext();
        }
      }

      setTouchStart(null);
    };

    document.addEventListener('touchstart', handleTouchStart);
    document.addEventListener('touchend', handleTouchEnd);

    return () => {
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [tutorialState.isActive, touchStart]);

  // Update tooltip position
  useEffect(() => {
    if (!tutorialState.isActive || tutorialState.currentStep >= steps.length) return;

    const currentStepData = steps[tutorialState.currentStep];
    if (!currentStepData.target) return;

    const targetElement = document.querySelector(currentStepData.target);
    if (targetElement) {
      const rect = targetElement.getBoundingClientRect();
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;

      setTooltipPosition({
        x: rect.left + scrollLeft + rect.width / 2,
        y: rect.top + scrollTop
      });

      // Scroll target into view
      targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [tutorialState.currentStep, tutorialState.isActive, steps]);

  // Track analytics
  const trackInteraction = useCallback((action: string, data?: any) => {
    if (!analytics?.enabled) return;

    const interaction = {
      stepId: steps[tutorialState.currentStep].id,
      action,
      timestamp: new Date(),
      data
    };

    progressRef.current.interactions.push(interaction);

    if (analytics.onProgress) {
      analytics.onProgress({
        tutorialId: progressRef.current.tutorialId,
        userId: progressRef.current.userId,
        startedAt: progressRef.current.startedAt,
        completedAt: progressRef.current.completedAt,
        currentStep: tutorialState.currentStep,
        totalSteps: steps.length,
        completionRate: tutorialState.progress,
        averageTimePerStep: progressRef.current.timeSpent / Math.max(1, tutorialState.currentStep),
        dropOffPoints: [],
        interactions: progressRef.current.interactions
      });
    }
  }, [analytics, tutorialState.currentStep, tutorialState.progress, steps.length]);

  const handleNext = useCallback(() => {
    if (tutorialState.currentStep < steps.length - 1) {
      const nextStep = tutorialState.currentStep + 1;
      setTutorialState(prev => ({ ...prev, currentStep: nextStep }));
      progressRef.current.currentStep = nextStep;
      onStepChange?.(nextStep);
      trackInteraction('step_next', { from: tutorialState.currentStep, to: nextStep });
    } else {
      handleComplete();
    }
  }, [tutorialState.currentStep, steps.length, onStepChange, trackInteraction]);

  const handlePrevious = useCallback(() => {
    if (tutorialState.currentStep > 0) {
      const prevStep = tutorialState.currentStep - 1;
      setTutorialState(prev => ({ ...prev, currentStep: prevStep }));
      progressRef.current.currentStep = prevStep;
      onStepChange?.(prevStep);
      trackInteraction('step_previous', { from: tutorialState.currentStep, to: prevStep });
    }
  }, [tutorialState.currentStep, onStepChange, trackInteraction]);

  const handleSkip = useCallback((reason: string) => {
    progressRef.current.skipped = true;
    progressRef.current.skipReason = reason;
    progressRef.current.completedAt = new Date();
    
    setTutorialState(prev => ({
      ...prev,
      isActive: false,
      isCompleted: true,
      isPaused: false
    }));

    trackInteraction('tutorial_skip', { reason });
    onSkip?.(reason);
  }, [onSkip, trackInteraction]);

  const handleComplete = useCallback(() => {
    progressRef.current.completedAt = new Date();
    progressRef.current.timeSpent = (progressRef.current.completedAt.getTime() - progressRef.current.startedAt.getTime()) / 1000;
    
    setTutorialState(prev => ({
      ...prev,
      isActive: false,
      isCompleted: true,
      isPaused: false,
      progress: 100
    }));

    trackInteraction('tutorial_complete');
    onComplete?.(progressRef.current);
  }, [onComplete, trackInteraction]);

  const handleStepAction = useCallback(async () => {
    const currentStepData = steps[tutorialState.currentStep];
    if (!currentStepData.action) return;

    setIsInteracting(true);
    trackInteraction('step_action_start', currentStepData.action);

    try {
      switch (currentStepData.action.type) {
        case 'click':
          if (currentStepData.action.target) {
            const element = document.querySelector(currentStepData.action.target) as HTMLElement;
            if (element) {
              element.click();
              await new Promise(resolve => setTimeout(resolve, currentStepData.action.delay || 500));
            }
          }
          break;

        case 'input':
          if (currentStepData.action.target && currentStepData.action.value !== undefined) {
            const element = document.querySelector(currentStepData.action.target) as HTMLInputElement;
            if (element) {
              element.value = currentStepData.action.value;
              element.dispatchEvent(new Event('input', { bubbles: true }));
              await new Promise(resolve => setTimeout(resolve, currentStepData.action.delay || 500));
            }
          }
          break;

        case 'wait':
          await new Promise(resolve => setTimeout(resolve, currentStepData.action.delay || 1000));
          break;

        case 'navigate':
          if (currentStepData.action.target) {
            window.location.href = currentStepData.action.target;
          }
          break;
      }

      // Validate step if validation is defined
      if (currentStepData.validation) {
        const isValid = await validateStep(currentStepData.validation);
        if (isValid) {
          trackInteraction('step_action_complete', { validation: 'passed' });
          setTimeout(() => handleNext(), 500);
        } else {
          trackInteraction('step_action_failed', { validation: 'failed' });
        }
      } else {
        trackInteraction('step_action_complete');
        setTimeout(() => handleNext(), 500);
      }

    } catch (error) {
      trackInteraction('step_action_error', { error: error.message });
    } finally {
      setIsInteracting(false);
    }
  }, [tutorialState.currentStep, steps, handleNext, trackInteraction]);

  const validateStep = useCallback(async (validation: TutorialStep['validation']): Promise<boolean> => {
    if (!validation) return true;

    try {
      switch (validation.type) {
        case 'element_exists':
          const element = document.querySelector(validation.target);
          return !!element;

        case 'element_visible':
          const visibleElement = document.querySelector(validation.target) as HTMLElement;
          return visibleElement ? visibleElement.offsetParent !== null : false;

        case 'text_contains':
          const textElement = document.querySelector(validation.target) as HTMLElement;
          return textElement ? textElement.textContent?.includes(validation.value) : false;

        case 'custom':
          const customElement = document.querySelector(validation.target);
          return customElement ? validation.custom!(customElement) : false;

        default:
          return true;
      }
    } catch (error) {
      console.warn('Step validation failed:', error);
      return false;
    }
  }, []);

  const startTutorial = useCallback(() => {
    setTutorialState(prev => ({ ...prev, isActive: true }));
    progressRef.current.startedAt = new Date();
    trackInteraction('tutorial_start');
  }, [trackInteraction]);

  const pauseTutorial = useCallback(() => {
    setTutorialState(prev => ({ ...prev, isPaused: true }));
    trackInteraction('tutorial_pause');
  }, [trackInteraction]);

  const resumeTutorial = useCallback(() => {
    setTutorialState(prev => ({ ...prev, isPaused: false }));
    trackInteraction('tutorial_resume');
  }, [trackInteraction]);

  if (!tutorialState.isActive && !tutorialState.isCompleted) {
    return (
      <div className={`tutorial-start-container ${className}`}>
        <button
          onClick={startTutorial}
          className="tutorial-start-button bg-accent text-white px-6 py-3 rounded-lg hover:bg-accent/90 transition-colors"
          aria-label={t('start_tutorial')}
        >
          {t('start_tutorial')}
        </button>
      </div>
    );
  }

  if (tutorialState.isCompleted) {
    return (
      <div className={`tutorial-completion-container ${className}`}>
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-6 text-center">
          <div className="text-green-600 dark:text-green-400 text-6xl mb-4">🎉</div>
          <h3 className="text-xl font-semibold text-green-800 dark:text-green-200 mb-2">
            {t('tutorial_completed')}
          </h3>
          <p className="text-green-700 dark:text-green-300 mb-4">
            {t('tutorial_completion_message')}
          </p>
          <div className="flex justify-center gap-2">
            <button
              onClick={() => {
                setTutorialState(prev => ({ ...prev, currentStep: 0, isActive: true, isCompleted: false }));
                progressRef.current = {
                  tutorialId: 'food-recognition-tutorial',
                  startedAt: new Date(),
                  currentStep: 0,
                  totalSteps: steps.length,
                  timeSpent: 0,
                  skipped: false,
                  interactions: []
                };
              }}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              {t('retake_tutorial')}
            </button>
            <button
              onClick={() => setTutorialState(prev => ({ ...prev, isActive: false }))}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              {t('close')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  const currentStepData = tutorialState.currentStep < steps.length ? steps[tutorialState.currentStep] : null;

  return (
    <div 
      ref={tutorialRef}
      className={`tutorial-overlay fixed inset-0 z-50 ${className}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby="tutorial-title"
      aria-describedby="tutorial-description"
    >
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/50" onClick={() => showSkipButton && handleSkip('overlay_click')} />
      
      {/* Swipe indicator for mobile */}
      {swipeDirection && (
        <div className={`fixed top-1/2 -translate-y-1/2 z-50 pointer-events-none ${
          swipeDirection === 'left' ? 'left-4' : 'right-4'
        }`}>
          <div className="bg-white/90 rounded-full p-3 shadow-lg">
            {swipeDirection === 'left' ? (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            ) : (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            )}
          </div>
        </div>
      )}

      {currentStepData && (
        <>
          {/* Highlight target element */}
          {currentStepData.target && (
            <div
              className="tutorial-highlight absolute border-4 border-accent rounded-lg pointer-events-none transition-all duration-300"
              style={{
                display: tooltipPosition ? 'block' : 'none',
                left: tooltipPosition ? tooltipPosition.x - 100 : 0,
                top: tooltipPosition ? tooltipPosition.y - 50 : 0,
                width: 200,
                height: 100
              }}
            />
          )}

          {/* Tooltip */}
          <div
            className={`tutorial-tooltip absolute bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-sm mx-4 transition-all duration-300 ${
              currentStepData.position === 'center' ? 'top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2' : ''
            }`}
            style={{
              display: tooltipPosition && currentStepData.position !== 'center' ? 'block' : 'none',
              left: tooltipPosition ? tooltipPosition.x : 'auto',
              top: tooltipPosition ? tooltipPosition.y + 120 : 'auto',
              transform: tooltipPosition ? 'translateX(-50%)' : 'none'
            }}
          >
            {/* Progress bar */}
            {showProgress && (
              <div className="mb-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {t('step_progress', { current: tutorialState.currentStep + 1, total: steps.length })}
                  </span>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {Math.round(tutorialState.progress)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-accent h-2 rounded-full transition-all duration-300"
                    style={{ width: `${tutorialState.progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Step content */}
            <div className="mb-6">
              <h3 id="tutorial-title" className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                {currentStepData.title}
              </h3>
              <div id="tutorial-description" className="text-gray-700 dark:text-gray-300">
                {typeof currentStepData.content === 'string' ? (
                  <p>{currentStepData.content}</p>
                ) : (
                  currentStepData.content
                )}
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex justify-between items-center gap-3">
              <div className="flex gap-2">
                {tutorialState.currentStep > 0 && (
                  <button
                    onClick={handlePrevious}
                    disabled={isInteracting}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    aria-label={t('previous_step')}
                  >
                    {t('previous')}
                  </button>
                )}
              </div>

              <div className="flex gap-2">
                {currentStepData.action && (
                  <button
                    onClick={handleStepAction}
                    disabled={isInteracting}
                    className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    aria-label={t('perform_action')}
                  >
                    {isInteracting ? t('processing') : t('try_it')}
                  </button>
                )}

                {!currentStepData.action || tutorialState.currentStep === steps.length - 1 ? (
                  <button
                    onClick={handleNext}
                    disabled={isInteracting}
                    className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    aria-label={tutorialState.currentStep === steps.length - 1 ? t('complete_tutorial') : t('next_step')}
                  >
                    {tutorialState.currentStep === steps.length - 1 ? t('complete') : t('next')}
                  </button>
                ) : null}
              </div>
            </div>

            {/* Skip button */}
            {showSkipButton && currentStepData.skipable !== false && (
              <button
                onClick={() => handleSkip('user_skipped')}
                className="absolute top-2 right-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                aria-label={t('skip_tutorial')}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          {/* Keyboard navigation hint */}
          {allowKeyboardNavigation && (
            <div className="absolute bottom-4 left-4 bg-black/75 text-white px-3 py-2 rounded-lg text-sm">
              {t('keyboard_hints')}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default Tutorial;
