
import React, { useState } from 'react';

interface SecurityLog {
  id: string;
  event: string;
  status: 'success' | 'warning' | 'danger';
  timestamp: string;
  ip: string;
}

export const SecurityPanel: React.FC = () => {
  const [logs] = useState<SecurityLog[]>([
    { id: '1', event: 'Login attempt', status: 'success', timestamp: new Date().toISOString(), ip: '192.168.1.1' },
    { id: '2', event: 'File shared with external user', status: 'warning', timestamp: new Date(Date.now() - 3600000).toISOString(), ip: '192.168.1.1' },
    { id: '3', event: 'Suspicious login attempt', status: 'danger', timestamp: new Date(Date.now() - 7200000).toISOString(), ip: '45.12.34.11' },
  ]);

  return (
    <div className="p-8 bg-slate-50 dark:bg-slate-950 min-h-screen">
      <div className="max-w-5xl mx-auto">
        <header className="mb-10">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">Security Center</h1>
          <p className="text-slate-500 dark:text-slate-400">Monitor your account security and review activity logs.</p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800">
            <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-2xl flex items-center justify-center mb-4 text-green-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04kM12 20.944a11.955 11.955 0 01-8.618-3.04A11.952 11.952 0 0012 21.48a11.952 11.952 0 008.618-3.576 11.955 11.955 0 01-8.618 3.04z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">SSL/TLS</h3>
            <p className="text-sm text-green-600 dark:text-green-400 font-semibold">Active & Secure</p>
          </div>

          <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800">
            <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center mb-4 text-blue-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">2FA</h3>
            <p className="text-sm text-blue-600 dark:text-blue-400 font-semibold">Enabled</p>
          </div>

          <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800">
            <div className="w-12 h-12 bg-amber-100 dark:bg-amber-900/30 rounded-2xl flex items-center justify-center mb-4 text-amber-600">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Vulnerability Scan</h3>
            <p className="text-sm text-amber-600 dark:text-amber-400 font-semibold">Scheduled for Tomorrow</p>
          </div>
        </div>

        <section>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Security Audit Log</h2>
            <button className="text-sm text-blue-600 font-bold hover:underline">Download CSV</button>
          </div>

          <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 overflow-hidden">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800">
                  <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Event</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Status</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Timestamp</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="px-6 py-4 font-semibold text-slate-800 dark:text-slate-100">{log.event}</td>
                    <td className="px-6 py-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${
                        log.status === 'success' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                        log.status === 'warning' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' :
                        'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      }`}>
                        {log.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-500 text-sm">{new Date(log.timestamp).toLocaleString()}</td>
                    <td className="px-6 py-4 text-slate-500 font-mono text-sm">{log.ip}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
};
