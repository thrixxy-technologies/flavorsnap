import { useState, useEffect, useCallback, useRef } from 'react';
import { accessibilityTester, TestSuiteResult } from '../utils/accessibilityTester';
import type { WCAGLevel } from '../utils/a11yAudit';

export interface UseAccessibilityTestingOptions {
  /** Auto-run on mount */
  autoRun?: boolean;
  /** Enable continuous monitoring */
  monitor?: boolean;
  /** Monitoring interval in ms (default: 30000) */
  interval?: number;
  /** WCAG conformance level (default: 'AA') */
  wcagLevel?: WCAGLevel;
  /** Root element to test (default: document.body) */
  root?: Element | null;
}

export interface UseAccessibilityTestingReturn {
  result: TestSuiteResult | null;
  history: TestSuiteResult[];
  isRunning: boolean;
  isMonitoring: boolean;
  error: string | null;
  runTests: () => Promise<void>;
  startMonitoring: () => void;
  stopMonitoring: () => void;
  clearHistory: () => void;
}

export function useAccessibilityTesting(
  options: UseAccessibilityTestingOptions = {}
): UseAccessibilityTestingReturn {
  const {
    autoRun = false,
    monitor = false,
    interval = 30_000,
    wcagLevel = 'AA',
    root = null,
  } = options;

  const [result, setResult] = useState<TestSuiteResult | null>(null);
  const [history, setHistory] = useState<TestSuiteResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const runTests = useCallback(async () => {
    if (typeof window === 'undefined') return;
    setIsRunning(true);
    setError(null);
    try {
      const testRoot = root ?? document.body;
      const r = await accessibilityTester.runTests(testRoot, wcagLevel);
      if (mountedRef.current) {
        setResult(r);
        setHistory(accessibilityTester.getHistory());
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'Test run failed');
      }
    } finally {
      if (mountedRef.current) setIsRunning(false);
    }
  }, [root, wcagLevel]);

  const startMonitoring = useCallback(() => {
    if (typeof window === 'undefined') return;
    accessibilityTester.startMonitoring({
      interval,
      wcagLevel,
      root: root ?? undefined,
      onResult: (r) => {
        if (mountedRef.current) {
          setResult(r);
          setHistory(accessibilityTester.getHistory());
        }
      },
    });
    if (mountedRef.current) setIsMonitoring(true);
  }, [interval, wcagLevel, root]);

  const stopMonitoring = useCallback(() => {
    accessibilityTester.stopMonitoring();
    if (mountedRef.current) setIsMonitoring(false);
  }, []);

  const clearHistory = useCallback(() => {
    accessibilityTester.clearHistory();
    if (mountedRef.current) setHistory([]);
  }, []);

  // Auto-run on mount
  useEffect(() => {
    if (autoRun) runTests();
  }, [autoRun, runTests]);

  // Start monitoring if requested
  useEffect(() => {
    if (monitor) {
      startMonitoring();
      return () => stopMonitoring();
    }
  }, [monitor, startMonitoring, stopMonitoring]);

  return {
    result,
    history,
    isRunning,
    isMonitoring,
    error,
    runTests,
    startMonitoring,
    stopMonitoring,
    clearHistory,
  };
}
