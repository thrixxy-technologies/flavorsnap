// Core Accessibility Testing Engine
import { a11yAudit, WCAGLevel } from './a11yAudit';

export type IssueSeverity = 'critical' | 'serious' | 'moderate' | 'minor';

export interface A11yIssue {
  id: string;
  rule: string;
  severity: IssueSeverity;
  wcagCriteria: string;
  message: string;
  element?: string;
  selector?: string;
  passed: boolean;
}

export interface TestSuiteResult {
  id: string;
  name: string;
  timestamp: number;
  url: string;
  issues: A11yIssue[];
  passed: number;
  failed: number;
  score: number; // 0-100
  wcagLevel: WCAGLevel;
}

export interface MonitoringConfig {
  interval: number; // ms
  wcagLevel: WCAGLevel;
  root?: Element;
  onResult?: (result: TestSuiteResult) => void;
}

class AccessibilityTester {
  private static instance: AccessibilityTester;
  private monitoringTimer: ReturnType<typeof setInterval> | null = null;
  private history: TestSuiteResult[] = [];

  private constructor() {}

  static getInstance(): AccessibilityTester {
    if (!AccessibilityTester.instance) {
      AccessibilityTester.instance = new AccessibilityTester();
    }
    return AccessibilityTester.instance;
  }

  async runTests(
    root: Element = document.body,
    wcagLevel: WCAGLevel = 'AA'
  ): Promise<TestSuiteResult> {
    const issues = await a11yAudit.runAll(root, wcagLevel);
    const passed = issues.filter(i => i.passed).length;
    const failed = issues.filter(i => !i.passed).length;
    const total = issues.length;
    const score = total > 0 ? Math.round((passed / total) * 100) : 100;

    const result: TestSuiteResult = {
      id: `test-${Date.now()}`,
      name: 'Automated A11y Audit',
      timestamp: Date.now(),
      url: typeof window !== 'undefined' ? window.location.href : '',
      issues,
      passed,
      failed,
      score,
      wcagLevel,
    };

    this.history = [result, ...this.history].slice(0, 20);
    return result;
  }

  startMonitoring(config: MonitoringConfig): void {
    this.stopMonitoring();
    const run = async () => {
      const result = await this.runTests(config.root, config.wcagLevel);
      config.onResult?.(result);
    };
    run();
    this.monitoringTimer = setInterval(run, config.interval);
  }

  stopMonitoring(): void {
    if (this.monitoringTimer !== null) {
      clearInterval(this.monitoringTimer);
      this.monitoringTimer = null;
    }
  }

  isMonitoring(): boolean {
    return this.monitoringTimer !== null;
  }

  getHistory(): TestSuiteResult[] {
    return this.history;
  }

  clearHistory(): void {
    this.history = [];
  }
}

export const accessibilityTester = AccessibilityTester.getInstance();
