import { useState, useEffect, useCallback, useRef } from 'react';
import { TutorialState, TutorialStep, TutorialProgress, TutorialAnalytics } from '../types';

interface UseTutorialOptions {
  steps: TutorialStep[];
  autoStart?: boolean;
  analytics?: {
    enabled: boolean;
    userId?: string;
    onProgress?: (analytics: TutorialAnalytics) => void;
  };
  storage?: {
    enabled: boolean;
    key: string;
  };
}

interface UseTutorialReturn {
  state: TutorialState;
  start: () => void;
  pause: () => void;
  resume: () => void;
  next: () => void;
  previous: () => void;
  skip: (reason?: string) => void;
  reset: () => void;
  goToStep: (stepIndex: number) => void;
  progress: TutorialProgress;
  isCompleted: boolean;
  canGoNext: boolean;
  canGoPrevious: boolean;
}

export function useTutorial({
  steps,
  autoStart = false,
  analytics,
  storage
}: UseTutorialOptions): UseTutorialReturn {
  const [state, setState] = useState<TutorialState>({
    isActive: autoStart,
    currentStep: 0,
    steps,
    isCompleted: false,
    isPaused: false,
    progress: 0
  });

  const progressRef = useRef<TutorialProgress>({
    tutorialId: 'tutorial',
    startedAt: new Date(),
    currentStep: 0,
    totalSteps: steps.length,
    timeSpent: 0,
    skipped: false,
    interactions: []
  });

  // Load saved progress from storage
  useEffect(() => {
    if (!storage?.enabled) return;

    try {
      const saved = localStorage.getItem(storage.key);
      if (saved) {
        const parsed = JSON.parse(saved);
        setState(prev => ({
          ...prev,
          currentStep: parsed.currentStep || 0,
          isCompleted: parsed.isCompleted || false
        }));
        progressRef.current.currentStep = parsed.currentStep || 0;
      }
    } catch (error) {
      console.warn('Failed to load tutorial progress:', error);
    }
  }, [storage?.key, storage?.enabled]);

  // Save progress to storage
  const saveProgress = useCallback(() => {
    if (!storage?.enabled) return;

    try {
      const toSave = {
        currentStep: state.currentStep,
        isCompleted: state.isCompleted
      };
      localStorage.setItem(storage.key, JSON.stringify(toSave));
    } catch (error) {
      console.warn('Failed to save tutorial progress:', error);
    }
  }, [state.currentStep, state.isCompleted, storage]);

  // Auto-save when state changes
  useEffect(() => {
    saveProgress();
  }, [saveProgress]);

  // Calculate progress
  useEffect(() => {
    const progress = state.isCompleted ? 100 : (state.currentStep / steps.length) * 100;
    setState(prev => ({ ...prev, progress }));
  }, [state.currentStep, steps.length, state.isCompleted]);

  // Track analytics
  const trackInteraction = useCallback((action: string, data?: any) => {
    if (!analytics?.enabled) return;

    const interaction = {
      stepId: steps[state.currentStep].id,
      action,
      timestamp: new Date(),
      data
    };

    progressRef.current.interactions.push(interaction);

    if (analytics.onProgress) {
      const currentTime = new Date();
      const timeSpent = (currentTime.getTime() - progressRef.current.startedAt.getTime()) / 1000;

      analytics.onProgress({
        tutorialId: progressRef.current.tutorialId,
        userId: analytics.userId,
        startedAt: progressRef.current.startedAt,
        completedAt: state.isCompleted ? currentTime : undefined,
        currentStep: state.currentStep,
        totalSteps: steps.length,
        completionRate: state.progress,
        averageTimePerStep: timeSpent / Math.max(1, state.currentStep),
        dropOffPoints: [],
        interactions: progressRef.current.interactions
      });
    }
  }, [analytics, state.currentStep, state.isCompleted, state.progress, steps]);

  const start = useCallback(() => {
    setState(prev => ({ ...prev, isActive: true, isPaused: false }));
    progressRef.current.startedAt = new Date();
    trackInteraction('tutorial_start');
  }, [trackInteraction]);

  const pause = useCallback(() => {
    setState(prev => ({ ...prev, isPaused: true }));
    trackInteraction('tutorial_pause');
  }, [trackInteraction]);

  const resume = useCallback(() => {
    setState(prev => ({ ...prev, isPaused: false }));
    trackInteraction('tutorial_resume');
  }, [trackInteraction]);

  const next = useCallback(() => {
    if (state.currentStep < steps.length - 1) {
      const nextStep = state.currentStep + 1;
      setState(prev => ({ ...prev, currentStep: nextStep }));
      progressRef.current.currentStep = nextStep;
      trackInteraction('step_next', { from: state.currentStep, to: nextStep });
    } else {
      complete();
    }
  }, [state.currentStep, steps.length, trackInteraction]);

  const previous = useCallback(() => {
    if (state.currentStep > 0) {
      const prevStep = state.currentStep - 1;
      setState(prev => ({ ...prev, currentStep: prevStep }));
      progressRef.current.currentStep = prevStep;
      trackInteraction('step_previous', { from: state.currentStep, to: prevStep });
    }
  }, [state.currentStep, trackInteraction]);

  const skip = useCallback((reason = 'user_skipped') => {
    progressRef.current.skipped = true;
    progressRef.current.skipReason = reason;
    progressRef.current.completedAt = new Date();
    
    setState(prev => ({
      ...prev,
      isActive: false,
      isCompleted: true,
      isPaused: false
    }));

    trackInteraction('tutorial_skip', { reason });
  }, [trackInteraction]);

  const reset = useCallback(() => {
    setState(prev => ({
      ...prev,
      currentStep: 0,
      isActive: false,
      isCompleted: false,
      isPaused: false,
      progress: 0
    }));

    progressRef.current = {
      tutorialId: 'tutorial',
      startedAt: new Date(),
      currentStep: 0,
      totalSteps: steps.length,
      timeSpent: 0,
      skipped: false,
      interactions: []
    };

    // Clear saved progress
    if (storage?.enabled) {
      try {
        localStorage.removeItem(storage.key);
      } catch (error) {
        console.warn('Failed to clear tutorial progress:', error);
      }
    }

    trackInteraction('tutorial_reset');
  }, [steps.length, storage?.key, storage?.enabled, trackInteraction]);

  const goToStep = useCallback((stepIndex: number) => {
    if (stepIndex >= 0 && stepIndex < steps.length) {
      setState(prev => ({ ...prev, currentStep: stepIndex }));
      progressRef.current.currentStep = stepIndex;
      trackInteraction('step_goto', { from: state.currentStep, to: stepIndex });
    }
  }, [steps.length, state.currentStep, trackInteraction]);

  const complete = useCallback(() => {
    progressRef.current.completedAt = new Date();
    const currentTime = progressRef.current.completedAt;
    progressRef.current.timeSpent = (currentTime.getTime() - progressRef.current.startedAt.getTime()) / 1000;
    
    setState(prev => ({
      ...prev,
      isActive: false,
      isCompleted: true,
      isPaused: false,
      progress: 100
    }));

    trackInteraction('tutorial_complete');
  }, [trackInteraction]);

  const canGoNext = state.currentStep < steps.length - 1;
  const canGoPrevious = state.currentStep > 0;

  return {
    state,
    start,
    pause,
    resume,
    next,
    previous,
    skip,
    reset,
    goToStep,
    progress: progressRef.current,
    isCompleted: state.isCompleted,
    canGoNext,
    canGoPrevious
  };
}

export default useTutorial;
