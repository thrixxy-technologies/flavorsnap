import React, { useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Play,
  RefreshCw,
  Activity,
  StopCircle,
  Trash2,
  Info,
} from 'lucide-react';
import { useAccessibilityTesting } from '../hooks/useAccessibilityTesting';
import type { WCAGLevel } from '../utils/a11yAudit';
import type { A11yIssue, IssueSeverity, TestSuiteResult } from '../utils/accessibilityTester';

// ─── Severity helpers ────────────────────────────────────────────────────────

const SEVERITY_CONFIG: Record<
  IssueSeverity,
  { label: string; color: string; icon: React.ReactNode }
> = {
  critical: {
    label: 'Critical',
    color: 'text-red-600',
    icon: <AlertCircle className="w-4 h-4 text-red-600" aria-hidden="true" />,
  },
  serious: {
    label: 'Serious',
    color: 'text-orange-500',
    icon: <AlertTriangle className="w-4 h-4 text-orange-500" aria-hidden="true" />,
  },
  moderate: {
    label: 'Moderate',
    color: 'text-yellow-500',
    icon: <AlertTriangle className="w-4 h-4 text-yellow-500" aria-hidden="true" />,
  },
  minor: {
    label: 'Minor',
    color: 'text-blue-500',
    icon: <Info className="w-4 h-4 text-blue-500" aria-hidden="true" />,
  },
};

function scoreColor(score: number): string {
  if (score >= 90) return 'text-green-600';
  if (score >= 70) return 'text-yellow-500';
  return 'text-red-600';
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function IssueRow({ issue }: { issue: A11yIssue }) {
  const [open, setOpen] = useState(false);
  const cfg = SEVERITY_CONFIG[issue.severity];

  return (
    <li className="border border-gray-200 dark:border-gray-700 rounded-md overflow-hidden">
      <button
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        {issue.passed ? (
          <CheckCircle className="w-4 h-4 text-green-500 shrink-0" aria-hidden="true" />
        ) : (
          cfg.icon
        )}
        <span className="flex-1 text-sm font-medium text-gray-800 dark:text-gray-200">
          {issue.message}
        </span>
        <span className={`text-xs font-semibold ${cfg.color} shrink-0`}>{cfg.label}</span>
        {open ? (
          <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" aria-hidden="true" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" aria-hidden="true" />
        )}
      </button>
      {open && (
        <div className="px-3 pb-3 pt-1 bg-gray-50 dark:bg-gray-800 text-xs space-y-1">
          <p>
            <span className="font-semibold">Rule:</span> {issue.rule}
          </p>
          <p>
            <span className="font-semibold">WCAG:</span> {issue.wcagCriteria}
          </p>
          {issue.selector && (
            <p>
              <span className="font-semibold">Selector:</span>{' '}
              <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">{issue.selector}</code>
            </p>
          )}
          {issue.element && (
            <details>
              <summary className="cursor-pointer font-semibold">Element HTML</summary>
              <pre className="mt-1 overflow-x-auto bg-gray-200 dark:bg-gray-700 p-2 rounded text-xs whitespace-pre-wrap break-all">
                {issue.element}
              </pre>
            </details>
          )}
        </div>
      )}
    </li>
  );
}

function ScoreRing({ score }: { score: number }) {
  const r = 28;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  return (
    <svg width="72" height="72" aria-label={`Accessibility score: ${score}`} role="img">
      <circle cx="36" cy="36" r={r} fill="none" stroke="#e5e7eb" strokeWidth="6" />
      <circle
        cx="36"
        cy="36"
        r={r}
        fill="none"
        stroke={score >= 90 ? '#16a34a' : score >= 70 ? '#eab308' : '#dc2626'}
        strokeWidth="6"
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
        transform="rotate(-90 36 36)"
      />
      <text
        x="36"
        y="41"
        textAnchor="middle"
        fontSize="14"
        fontWeight="bold"
        fill="currentColor"
        className={scoreColor(score)}
      >
        {score}
      </text>
    </svg>
  );
}

function ResultSummary({ result }: { result: TestSuiteResult }) {
  const bySeverity = (sev: IssueSeverity) =>
    result.issues.filter(i => !i.passed && i.severity === sev).length;

  return (
    <div className="flex flex-wrap items-center gap-4 p-4 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
      <ScoreRing score={result.score} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          WCAG {result.wcagLevel} &middot;{' '}
          {new Date(result.timestamp).toLocaleTimeString()}
        </p>
        <div className="flex flex-wrap gap-3 mt-1 text-sm">
          <span className="text-green-600 font-medium">{result.passed} passed</span>
          <span className="text-red-600 font-medium">{result.failed} failed</span>
        </div>
        <div className="flex flex-wrap gap-2 mt-2">
          {(['critical', 'serious', 'moderate', 'minor'] as IssueSeverity[]).map(sev => {
            const count = bySeverity(sev);
            if (count === 0) return null;
            return (
              <span
                key={sev}
                className={`text-xs font-semibold ${SEVERITY_CONFIG[sev].color}`}
              >
                {count} {SEVERITY_CONFIG[sev].label}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── Main component ──────────────────────────────────────────────────────────

export interface AccessibilityReportProps {
  wcagLevel?: WCAGLevel;
  autoRun?: boolean;
  monitor?: boolean;
  monitorInterval?: number;
  className?: string;
}

export function AccessibilityReport({
  wcagLevel = 'AA',
  autoRun = true,
  monitor = false,
  monitorInterval = 30_000,
  className = '',
}: AccessibilityReportProps) {
  const [filter, setFilter] = useState<'all' | 'failed' | 'passed'>('failed');
  const [severityFilter, setSeverityFilter] = useState<IssueSeverity | 'all'>('all');

  const { result, history, isRunning, isMonitoring, error, runTests, startMonitoring, stopMonitoring, clearHistory } =
    useAccessibilityTesting({
      autoRun,
      monitor,
      interval: monitorInterval,
      wcagLevel,
    });

  const filteredIssues = result?.issues.filter(i => {
    const passFilter = filter === 'all' || (filter === 'failed' ? !i.passed : i.passed);
    const sevFilter = severityFilter === 'all' || i.severity === severityFilter;
    return passFilter && sevFilter;
  }) ?? [];

  return (
    <section
      className={`space-y-4 ${className}`}
      aria-label="Accessibility Report"
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Accessibility Report
        </h2>
        <div className="flex items-center gap-2">
          {isMonitoring ? (
            <button
              onClick={stopMonitoring}
              className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-md bg-red-100 text-red-700 hover:bg-red-200 transition-colors"
              aria-label="Stop monitoring"
            >
              <StopCircle className="w-4 h-4" aria-hidden="true" />
              Stop
            </button>
          ) : (
            <button
              onClick={startMonitoring}
              className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-md bg-blue-100 text-blue-700 hover:bg-blue-200 transition-colors"
              aria-label="Start continuous monitoring"
            >
              <Activity className="w-4 h-4" aria-hidden="true" />
              Monitor
            </button>
          )}
          <button
            onClick={runTests}
            disabled={isRunning}
            className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-md bg-green-100 text-green-700 hover:bg-green-200 disabled:opacity-50 transition-colors"
            aria-label="Run accessibility tests"
          >
            {isRunning ? (
              <RefreshCw className="w-4 h-4 animate-spin" aria-hidden="true" />
            ) : (
              <Play className="w-4 h-4" aria-hidden="true" />
            )}
            {isRunning ? 'Running…' : 'Run Tests'}
          </button>
        </div>
      </div>

      {/* Status indicators */}
      {isMonitoring && (
        <p className="text-xs text-blue-600 dark:text-blue-400" role="status">
          ● Monitoring active — refreshing every {monitorInterval / 1000}s
        </p>
      )}
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}

      {/* Summary */}
      {result && <ResultSummary result={result} />}

      {/* Filters */}
      {result && (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filter issues">
          <select
            value={filter}
            onChange={e => setFilter(e.target.value as typeof filter)}
            className="text-sm border border-gray-300 dark:border-gray-600 rounded-md px-2 py-1 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
            aria-label="Filter by status"
          >
            <option value="all">All</option>
            <option value="failed">Failed</option>
            <option value="passed">Passed</option>
          </select>
          <select
            value={severityFilter}
            onChange={e => setSeverityFilter(e.target.value as typeof severityFilter)}
            className="text-sm border border-gray-300 dark:border-gray-600 rounded-md px-2 py-1 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
            aria-label="Filter by severity"
          >
            <option value="all">All severities</option>
            <option value="critical">Critical</option>
            <option value="serious">Serious</option>
            <option value="moderate">Moderate</option>
            <option value="minor">Minor</option>
          </select>
        </div>
      )}

      {/* Issue list */}
      {filteredIssues.length > 0 ? (
        <ul className="space-y-2" aria-label="Accessibility issues">
          {filteredIssues.map(issue => (
            <IssueRow key={issue.id} issue={issue} />
          ))}
        </ul>
      ) : result ? (
        <p className="text-sm text-gray-500 dark:text-gray-400 py-4 text-center">
          No issues match the current filter.
        </p>
      ) : null}

      {/* History */}
      {history.length > 1 && (
        <details className="mt-4">
          <summary className="cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-1">
            <ChevronRight className="w-4 h-4" aria-hidden="true" />
            Test history ({history.length} runs)
          </summary>
          <div className="mt-2 space-y-1">
            {history.map(h => (
              <div
                key={h.id}
                className="flex items-center justify-between text-xs px-3 py-1.5 rounded bg-gray-50 dark:bg-gray-800"
              >
                <span className="text-gray-500 dark:text-gray-400">
                  {new Date(h.timestamp).toLocaleTimeString()}
                </span>
                <span className={`font-semibold ${scoreColor(h.score)}`}>
                  Score: {h.score}
                </span>
                <span className="text-gray-500 dark:text-gray-400">
                  {h.failed} failed / {h.passed} passed
                </span>
              </div>
            ))}
          </div>
          <button
            onClick={clearHistory}
            className="mt-2 flex items-center gap-1 text-xs text-gray-500 hover:text-red-500 transition-colors"
            aria-label="Clear test history"
          >
            <Trash2 className="w-3 h-3" aria-hidden="true" />
            Clear history
          </button>
        </details>
      )}
    </section>
  );
}

export default AccessibilityReport;
