import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'next-i18next';

interface Prediction {
  class: string;
  confidence: number;
}

interface ClassificationResultProps {
  predictions: Prediction[];
  loading?: boolean;
  imageUrl?: string;
}

export function ClassificationResult({ predictions = [], loading = false, imageUrl }: ClassificationResultProps) {
  const { t } = useTranslation('common');
  const [animatedConfidence, setAnimatedConfidence] = useState(0);
  const [showParticles, setShowParticles] = useState(false);
  const [isReducedMotion, setIsReducedMotion] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const animationRef = useRef<number | null>(null);

  // Check for reduced motion preference
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setIsReducedMotion(mediaQuery.matches);
    
    const handleChange = (e: MediaQueryListEvent) => {
      setIsReducedMotion(e.matches);
    };
    
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  // Animate confidence score
  useEffect(() => {
    if (predictions.length > 0 && !loading) {
      const targetConfidence = predictions[0]?.confidence || 0;
      const duration = isReducedMotion ? 0 : 1500; // 1.5s animation
      const startTime = Date.now();
      
      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function for smooth animation
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        setAnimatedConfidence(targetConfidence * easeOutQuart);
        
        if (progress < 1) {
          animationRef.current = requestAnimationFrame(animate);
        }
      };
      
      if (duration > 0) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        setAnimatedConfidence(targetConfidence);
      }
      
      // Show particles for high confidence
      if (targetConfidence > 0.8 && !isReducedMotion) {
        setShowParticles(true);
        setTimeout(() => setShowParticles(false), 3000);
      }
      
      // Play sound effect for high confidence
      if (targetConfidence > 0.8 && !isReducedMotion) {
        playSuccessSound();
      }
    }
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [predictions, loading, isReducedMotion]);

  const playSuccessSound = useCallback(() => {
    // Create a simple success sound using Web Audio API
    try {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.setValueAtTime(523.25, audioContext.currentTime); // C5
      oscillator.frequency.setValueAtTime(659.25, audioContext.currentTime + 0.1); // E5
      oscillator.frequency.setValueAtTime(783.99, audioContext.currentTime + 0.2); // G5
      
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.3);
    } catch (error) {
      console.log('Audio playback not supported');
    }
  }, []);

  const getConfidenceColor = (confidence: number) => {
    if (confidence > 0.8) return 'text-green-500';
    if (confidence > 0.6) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getProgressColor = (confidence: number) => {
    if (confidence > 0.8) return '#10b981'; // green-500
    if (confidence > 0.6) return '#eab308'; // yellow-500
    return '#ef4444'; // red-500
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className="w-full max-w-md mx-auto p-6 bg-white dark:bg-gray-800 rounded-2xl shadow-lg">
        <div className="animate-pulse">
          <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg mb-4"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
        </div>
      </div>
    );
  }

  if (predictions.length === 0) {
    return null;
  }

  const topPrediction = predictions[0];
  const top3Predictions = predictions.slice(0, 3);

  return (
    <div className="w-full max-w-md mx-auto p-6 bg-white dark:bg-gray-800 rounded-2xl shadow-lg relative overflow-hidden">
      {/* Particle Effects */}
      {showParticles && !isReducedMotion && (
        <div className="absolute inset-0 pointer-events-none">
          {[...Array(12)].map((_, i) => (
            <div
              key={i}
              className="absolute w-2 h-2 bg-yellow-400 rounded-full animate-ping"
              style={{
                left: `${20 + (i % 4) * 20}%`,
                top: `${20 + Math.floor(i / 4) * 20}%`,
                animationDelay: `${i * 0.1}s`,
                animationDuration: '1.5s'
              }}
            />
          ))}
        </div>
      )}

      {/* Main Result */}
      <div className="text-center mb-6">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-2">
          {t('classification_result')}
        </h3>
        
        {/* Circular Progress Indicator */}
        <div className="relative inline-flex items-center justify-center w-32 h-32 mb-4">
          <svg className="transform -rotate-90 w-32 h-32">
            {/* Background circle */}
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke="currentColor"
              strokeWidth="8"
              fill="none"
              className="text-gray-200 dark:text-gray-700"
            />
            {/* Progress circle */}
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke={getProgressColor(animatedConfidence)}
              strokeWidth="8"
              fill="none"
              strokeDasharray={`${2 * Math.PI * 56}`}
              strokeDashoffset={`${2 * Math.PI * 56 * (1 - animatedConfidence)}`}
              className={`transition-all duration-300 ${!isReducedMotion ? 'ease-out' : ''}`}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-3xl font-bold ${getConfidenceColor(animatedConfidence)}`}>
              {Math.round(animatedConfidence * 100)}%
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {t('confidence')}
            </span>
          </div>
        </div>

        {/* Top Prediction */}
        <div className="mb-4">
          <h4 className="text-2xl font-bold text-gray-800 dark:text-gray-200">
            {topPrediction.class}
          </h4>
          <p className={`text-sm font-medium ${getConfidenceColor(topPrediction.confidence)}`}>
            {Math.round(topPrediction.confidence * 100)}% {t('confidence')}
          </p>
        </div>
      </div>

      {/* Top 3 Predictions Breakdown */}
      <div className="space-y-3">
        <h4 className="text-sm font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
          {t('top_predictions')}
        </h4>
        {top3Predictions.map((prediction, index) => (
          <div key={index} className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold ${
                index === 0 ? 'bg-yellow-500' : 
                index === 1 ? 'bg-gray-400' : 
                'bg-orange-600'
              }`}>
                {index + 1}
              </div>
              <span className="text-gray-700 dark:text-gray-300 font-medium">
                {prediction.class}
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${!isReducedMotion ? 'ease-out' : ''}`}
                  style={{
                    width: `${prediction.confidence * 100}%`,
                    backgroundColor: getProgressColor(prediction.confidence)
                  }}
                />
              </div>
              <span className={`text-sm font-medium ${getConfidenceColor(prediction.confidence)} w-12 text-right`}>
                {Math.round(prediction.confidence * 100)}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Image Preview */}
      {imageUrl && (
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <div className="relative w-full h-32 rounded-lg overflow-hidden">
            <img
              src={imageUrl}
              alt="Classified food"
              className="w-full h-full object-cover"
            />
          </div>
        </div>
      )}
    </div>
  );
}
