import React, { useState, useEffect, useCallback } from 'react';
import { Upload, Download, Shield, Database, Activity, DollarSign, CheckCircle, AlertCircle, XCircle, Clock, Users, HardDrive } from 'lucide-react';
import { toast } from 'react-hot-toast';

interface StorageFile {
  cid: string;
  name: string;
  size: number;
  contentHash: string;
  timestamp: string;
  owner: string;
  permissions: Record<string, string>;
  metadata: Record<string, any>;
  replicas: string[];
  verificationStatus: 'pending' | 'verified' | 'failed';
  accessCount: number;
  lastAccessed?: string;
  costEstimate: number;
}

interface StorageMetrics {
  uploadSpeed: number;
  downloadSpeed: number;
  latency: number;
  successRate: number;
  totalOperations: number;
  failedOperations: number;
  averageFileSize: number;
  storageEfficiency: number;
  totalFiles: number;
  totalSize: number;
  totalCost: number;
}

interface OptimizationReport {
  filesOptimized: number;
  spaceSaved: number;
  costReduction: number;
  recommendations: string[];
}

const StorageManager: React.FC = () => {
  const [files, setFiles] = useState<StorageFile[]>([]);
  const [metrics, setMetrics] = useState<StorageMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<StorageFile | null>(null);
  const [optimizationReport, setOptimizationReport] = useState<OptimizationReport | null>(null);
  const [activeTab, setActiveTab] = useState<'files' | 'metrics' | 'optimization'>('files');

  // Fetch files and metrics on component mount
  useEffect(() => {
    fetchFiles();
    fetchMetrics();
    const interval = setInterval(() => {
      fetchMetrics();
    }, 30000); // Update metrics every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchFiles = async () => {
    try {
      const response = await fetch('/api/storage/files');
      const data = await response.json();
      setFiles(data.files || []);
    } catch (error) {
      console.error('Failed to fetch files:', error);
      toast.error('Failed to load files');
    }
  };

  const fetchMetrics = async () => {
    try {
      const response = await fetch('/api/storage/metrics');
      const data = await response.json();
      setMetrics(data);
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/storage/upload', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        toast.success(`File uploaded successfully! CID: ${result.cid}`);
        fetchFiles();
        fetchMetrics();
      } else {
        const error = await response.json();
        toast.error(`Upload failed: ${error.message}`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      toast.error('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleFileDownload = async (file: StorageFile) => {
    try {
      const response = await fetch(`/api/storage/download/${file.cid}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = file.name;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        toast.success('File downloaded successfully');
        fetchFiles(); // Update access count
      } else {
        toast.error('Download failed');
      }
    } catch (error) {
      console.error('Download error:', error);
      toast.error('Download failed');
    }
  };

  const handleVerifyFile = async (file: StorageFile) => {
    try {
      const response = await fetch(`/api/storage/verify/${file.cid}`, {
        method: 'POST',
      });

      if (response.ok) {
        const result = await response.json();
        if (result.verified) {
          toast.success('File verified successfully');
        } else {
          toast.error('File verification failed');
        }
        fetchFiles();
      } else {
        toast.error('Verification request failed');
      }
    } catch (error) {
      console.error('Verification error:', error);
      toast.error('Verification failed');
    }
  };

  const handleDeleteFile = async (file: StorageFile) => {
    if (!confirm(`Are you sure you want to delete ${file.name}?`)) return;

    try {
      const response = await fetch(`/api/storage/delete/${file.cid}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        toast.success('File deleted successfully');
        fetchFiles();
        fetchMetrics();
      } else {
        toast.error('Delete failed');
      }
    } catch (error) {
      console.error('Delete error:', error);
      toast.error('Delete failed');
    }
  };

  const handleOptimizeStorage = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/storage/optimize', {
        method: 'POST',
      });

      if (response.ok) {
        const report = await response.json();
        setOptimizationReport(report);
        toast.success('Storage optimization completed');
        fetchFiles();
        fetchMetrics();
      } else {
        toast.error('Optimization failed');
      }
    } catch (error) {
      console.error('Optimization error:', error);
      toast.error('Optimization failed');
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatSpeed = (mbps: number): string => {
    return `${mbps.toFixed(2)} Mbps`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'verified':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-yellow-500" />;
    }
  };

  const renderFilesTab = () => (
    <div className="space-y-6">
      {/* Upload Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <Upload className="w-5 h-5 mr-2" />
          Upload File
        </h3>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
          <input
            type="file"
            onChange={handleFileUpload}
            disabled={uploading}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="cursor-pointer inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            {uploading ? 'Uploading...' : 'Choose File'}
          </label>
          <p className="mt-2 text-sm text-gray-500">
            Upload files to decentralized IPFS storage
          </p>
        </div>
      </div>

      {/* Files List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold flex items-center">
            <Database className="w-5 h-5 mr-2" />
            Stored Files ({files.length})
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Size
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Access Count
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cost
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {files.map((file) => (
                <tr key={file.cid} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{file.name}</div>
                      <div className="text-xs text-gray-500">{file.cid.slice(0, 16)}...</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatFileSize(file.size)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      {getStatusIcon(file.verificationStatus)}
                      <span className="ml-2 text-sm">{file.verificationStatus}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {file.accessCount}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${file.costEstimate.toFixed(4)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleFileDownload(file)}
                        className="text-indigo-600 hover:text-indigo-900"
                        title="Download"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleVerifyFile(file)}
                        className="text-green-600 hover:text-green-900"
                        title="Verify"
                      >
                        <Shield className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteFile(file)}
                        className="text-red-600 hover:text-red-900"
                        title="Delete"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {files.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No files stored yet
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const renderMetricsTab = () => (
    <div className="space-y-6">
      {metrics ? (
        <>
          {/* Performance Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Activity className="w-8 h-8 text-blue-500" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Upload Speed</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {formatSpeed(metrics.uploadSpeed)}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Download className="w-8 h-8 text-green-500" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Download Speed</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {formatSpeed(metrics.downloadSpeed)}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Clock className="w-8 h-8 text-yellow-500" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Latency</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {metrics.latency.toFixed(0)}ms
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <CheckCircle className="w-8 h-8 text-green-500" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Success Rate</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {(metrics.successRate * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Storage Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <HardDrive className="w-8 h-8 text-purple-500" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Files</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {metrics.totalFiles}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Database className="w-8 h-8 text-indigo-500" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Size</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {formatFileSize(metrics.totalSize)}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <DollarSign className="w-8 h-8 text-green-500" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Cost</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    ${metrics.totalCost.toFixed(2)}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Activity className="w-8 h-8 text-orange-500" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Efficiency</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {(metrics.storageEfficiency * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Operations Summary */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Operations Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <p className="text-sm text-gray-500">Total Operations</p>
                <p className="text-xl font-semibold">{metrics.totalOperations}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Failed Operations</p>
                <p className="text-xl font-semibold text-red-600">{metrics.failedOperations}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Average File Size</p>
                <p className="text-xl font-semibold">{formatFileSize(metrics.averageFileSize)}</p>
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
          Loading metrics...
        </div>
      )}
    </div>
  );

  const renderOptimizationTab = () => (
    <div className="space-y-6">
      {/* Optimization Controls */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <Activity className="w-5 h-5 mr-2" />
          Storage Optimization
        </h3>
        <button
          onClick={handleOptimizeStorage}
          disabled={loading}
          className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
        >
          {loading ? 'Optimizing...' : 'Optimize Storage'}
        </button>
        <p className="mt-2 text-sm text-gray-500">
          Analyze and optimize storage performance and cost
        </p>
      </div>

      {/* Optimization Report */}
      {optimizationReport && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Optimization Report</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-green-600">{optimizationReport.filesOptimized}</p>
              <p className="text-sm text-gray-500">Files Optimized</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-blue-600">{formatFileSize(optimizationReport.spaceSaved)}</p>
              <p className="text-sm text-gray-500">Space Saved</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-purple-600">${optimizationReport.costReduction.toFixed(2)}</p>
              <p className="text-sm text-gray-500">Cost Reduction</p>
            </div>
          </div>
          
          {optimizationReport.recommendations.length > 0 && (
            <div>
              <h4 className="font-semibold mb-2">Recommendations</h4>
              <ul className="list-disc list-inside space-y-1">
                {optimizationReport.recommendations.map((recommendation, index) => (
                  <li key={index} className="text-sm text-gray-600">{recommendation}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Storage Health */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Storage Health</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Replication Status</span>
            <div className="flex items-center">
              <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
              <span className="text-sm">Healthy</span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Content Verification</span>
            <div className="flex items-center">
              <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
              <span className="text-sm">Active</span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Network Connectivity</span>
            <div className="flex items-center">
              <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
              <span className="text-sm">Connected</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 flex items-center">
              <Database className="w-8 h-8 mr-3 text-indigo-600" />
              Decentralized Storage Manager
            </h1>
            <p className="mt-2 text-gray-600">
              Manage IPFS-based decentralized storage with verification and optimization
            </p>
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200 mb-6">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('files')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'files'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Files
              </button>
              <button
                onClick={() => setActiveTab('metrics')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'metrics'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Metrics
              </button>
              <button
                onClick={() => setActiveTab('optimization')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'optimization'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Optimization
              </button>
            </nav>
          </div>

          {/* Tab Content */}
          {activeTab === 'files' && renderFilesTab()}
          {activeTab === 'metrics' && renderMetricsTab()}
          {activeTab === 'optimization' && renderOptimizationTab()}
        </div>
      </div>
    </div>
  );
};

export default StorageManager;
