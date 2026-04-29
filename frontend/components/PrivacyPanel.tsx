'use client';

import React, { useState } from 'react';
import { usePrivacy } from '@/hooks/usePrivacy';

interface PrivacySettings {
  marketing: boolean;
  analytics: boolean;
  processing: boolean;
  thirdParty: boolean;
  cookies: boolean;
}

export const PrivacyPanel: React.FC = () => {
  const { gdprCompliance, updateConsent } = usePrivacy();
  const [settings, setSettings] = useState<PrivacySettings>({
    marketing: false,
    analytics: true,
    processing: true,
    thirdParty: false,
    cookies: true,
  });
  const [dataRequest, setDataRequest] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const handleConsentChange = async (key: keyof PrivacySettings) => {
    const newSettings = { ...settings, [key]: !settings[key] };
    setSettings(newSettings);
    
    setLoading(true);
    try {
      await updateConsent(newSettings);
    } finally {
      setLoading(false);
    }
  };

  const handleDataExport = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/privacy/export', {
        method: 'GET',
      });
      const data = await response.json();
      
      // Download as JSON
      const href = URL.createObjectURL(new Blob([JSON.stringify(data)], { type: 'application/json' }));
      const link = document.createElement('a');
      link.href = href;
      link.download = 'my-data.json';
      link.click();
    } finally {
      setLoading(false);
    }
  };

  const handleDataDeletion = async () => {
    if (!confirm('Are you sure you want to delete all your data? This action cannot be undone.')) {
      return;
    }

    setLoading(true);
    try {
      await fetch('/api/privacy/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: dataRequest || 'User requested deletion' }),
      });
      alert('Your data deletion request has been submitted. It will be processed within 30 days.');
      setDataRequest('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h1 className="text-3xl font-bold mb-6 text-gray-900">Privacy Settings</h1>

      {/* Consent Management */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">Data Usage Consent</h2>
        
        <div className="space-y-4">
          <ConsentToggle
            label="Marketing & Personalization"
            description="Allow us to use your data to personalize your experience and send promotional content"
            checked={settings.marketing}
            onChange={() => handleConsentChange('marketing')}
            disabled={loading}
          />
          
          <ConsentToggle
            label="Analytics & Performance"
            description="Help us improve our service by tracking how you use it"
            checked={settings.analytics}
            onChange={() => handleConsentChange('analytics')}
            disabled={loading}
          />
          
          <ConsentToggle
            label="Food Recognition Processing"
            description="Required to provide food recognition and nutritional analysis"
            checked={settings.processing}
            onChange={() => handleConsentChange('processing')}
            disabled={loading}
            required
          />
          
          <ConsentToggle
            label="Third-Party Sharing"
            description="Allow sharing anonymized data with trusted partners for research"
            checked={settings.thirdParty}
            onChange={() => handleConsentChange('thirdParty')}
            disabled={loading}
          />
          
          <ConsentToggle
            label="Cookie Usage"
            description="Use cookies to remember your preferences and improve user experience"
            checked={settings.cookies}
            onChange={() => handleConsentChange('cookies')}
            disabled={loading}
          />
        </div>
      </section>

      {/* Data Access Requests */}
      <section className="mb-8 border-t pt-8">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">Your Data Rights</h2>
        
        <div className="space-y-3">
          <button
            onClick={handleDataExport}
            disabled={loading}
            className="w-full px-4 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white rounded-lg font-medium transition"
          >
            {loading ? 'Processing...' : 'Download My Data (GDPR)'}
          </button>
          
          <button
            onClick={() => window.location.href = '/privacy/portability'}
            className="w-full px-4 py-3 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition"
          >
            Request Data Portability
          </button>
        </div>
      </section>

      {/* Data Deletion */}
      <section className="mb-8 border-t pt-8">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">Delete Account & Data</h2>
        
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p className="text-sm text-gray-700 mb-4">
            Requesting data deletion will permanently remove all your personal information, usage history, and account data within 30 days.
          </p>
          
          <textarea
            value={dataRequest}
            onChange={(e) => setDataRequest(e.target.value)}
            placeholder="Optional: Tell us why you're deleting your account"
            className="w-full p-3 border border-gray-300 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-red-500"
            rows={3}
            disabled={loading}
          />
          
          <button
            onClick={handleDataDeletion}
            disabled={loading}
            className="w-full px-4 py-3 bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition"
          >
            {loading ? 'Processing...' : 'Request Data Deletion'}
          </button>
        </div>
      </section>

      {/* Privacy Information */}
      <section className="border-t pt-8">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">Privacy Information</h2>
        
        <div className="space-y-3 text-sm text-gray-600">
          <p>
            <strong>Last Updated:</strong> {new Date().toLocaleDateString()}
          </p>
          <p>
            <a href="/privacy-policy" className="text-blue-500 hover:underline">View our Privacy Policy</a>
          </p>
          <p>
            <a href="/cookie-policy" className="text-blue-500 hover:underline">View our Cookie Policy</a>
          </p>
          <p>
            <a href="/data-security" className="text-blue-500 hover:underline">View our Data Security Practices</a>
          </p>
        </div>
      </section>
    </div>
  );
};

interface ConsentToggleProps {
  label: string;
  description: string;
  checked: boolean;
  onChange: () => void;
  disabled?: boolean;
  required?: boolean;
}

const ConsentToggle: React.FC<ConsentToggleProps> = ({
  label,
  description,
  checked,
  onChange,
  disabled,
  required,
}) => (
  <div className="flex items-start p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition">
    <input
      type="checkbox"
      checked={checked}
      onChange={onChange}
      disabled={disabled || required}
      className="mt-1 w-5 h-5 text-blue-500 rounded focus:ring-2 focus:ring-blue-500"
    />
    <div className="ml-3 flex-1">
      <label className="block font-medium text-gray-900">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <p className="text-sm text-gray-600 mt-1">{description}</p>
    </div>
  </div>
);
