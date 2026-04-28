import React, { useState, useEffect, Suspense } from 'react';
import { TrendingUp, Users, Activity, Download, Calendar, Filter, RefreshCw, Eye, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import AnalyticsCard from '../components/AnalyticsCard';

const UsageStatisticsChart = React.lazy(() => import('../components/UsageStatisticsChart'));
const ModelPerformanceChart = React.lazy(() => import('../components/ModelPerformanceChart'));
const UserEngagementChart = React.lazy(() => import('../components/UserEngagementChart'));
const RealTimeActivity = React.lazy(() => import('../components/RealTimeActivity'));

interface UsageStats {
  date: string;
  requests: number;
  users: number;
  accuracy: number;
}

interface ModelPerformance {
  model: string;
  accuracy: number;
  inferenceTime: number;
  confidence: number;
}

interface UserEngagement {
  category: string;
  value: number;
  color: string;
}

const activities = [
  {
    id: '1',
    type: 'classification' as const,
    title: 'Classification Request',
    description: 'Jollof Rice - 95.2% confidence',
    timestamp: '2 min ago'
  },
  {
    id: '2',
    type: 'model_update' as const,
    title: 'Model Update',
    description: 'Accuracy improved to 94.5%',
    timestamp: '15 min ago'
  },
  {
    id: '3',
    type: 'alert' as const,
    title: 'High Traffic Alert',
    description: '150+ requests in last hour',
    timestamp: '1 hour ago'
  }
];

const AnalyticsDashboard: React.FC = () => {
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [usageData, setUsageData] = useState<UsageStats[]>([]);
  const [modelPerformance, setModelPerformance] = useState<ModelPerformance[]>([]);
  const [userEngagement, setUserEngagement] = useState<UserEngagement[]>([]);

  // Mock data generation
  useEffect(() => {
    generateMockData();
  }, []);

  const generateMockData = () => {
    // Generate usage statistics
    const usage: UsageStats[] = [];
    for (let i = 29; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      usage.push({
        date: date.toLocaleDateString(),
        requests: Math.floor(Math.random() * 500) + 100,
        users: Math.floor(Math.random() * 200) + 50,
        accuracy: Math.random() * 10 + 85
      });
    }
    setUsageData(usage);

    // Generate model performance data
    setModelPerformance([
      { model: 'ResNet18', accuracy: 94.2, inferenceTime: 234, confidence: 87.5 },
      { model: 'ResNet34', accuracy: 95.1, inferenceTime: 312, confidence: 89.2 },
      { model: 'EfficientNet', accuracy: 93.8, inferenceTime: 189, confidence: 86.1 }
    ]);

    // Generate user engagement data
    setUserEngagement([
      { category: 'Akara', value: 23, color: '#FF6B6B' },
      { category: 'Bread', value: 19, color: '#4ECDC4' },
      { category: 'Egusi', value: 17, color: '#45B7D1' },
      { category: 'Moi Moi', value: 21, color: '#96CEB4' },
      { category: 'Rice and Stew', value: 12, color: '#FFEAA7' },
      { category: 'Yam', value: 8, color: '#DDA0DD' }
    ]);
  };

  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => {
      generateMockData();
      setIsLoading(false);
    }, 1000);
  };

  const handleExport = () => {
    const data = {
      usageData,
      modelPerformance,
      userEngagement,
      exportDate: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analytics-report-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const statsCards = [
    { title: 'Total Requests', value: '12,847', change: '+12.5%', icon: Activity, color: 'bg-blue-500' },
    { title: 'Active Users', value: '3,421', change: '+8.2%', icon: Users, color: 'bg-green-500' },
    { title: 'Avg Accuracy', value: '94.2%', change: '+2.1%', icon: CheckCircle, color: 'bg-purple-500' },
    { title: 'Response Time', value: '234ms', change: '-15ms', icon: Clock, color: 'bg-orange-500' }
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
            <p className="text-gray-600 mt-1">Monitor usage patterns, model performance, and user engagement</p>
          </div>
          <div className="flex gap-4">
            <button
              onClick={handleRefresh}
              className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={handleExport}
              className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
            >
              <Download className="w-4 h-4" />
              Export Report
            </button>
          </div>
        </div>


        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          {statsCards.map((stat, index) => (
            <AnalyticsCard key={index} {...stat} />
          ))}
        </div>

        {/* Date Range Filter */}
        <div className="mb-6">
          <div className="flex gap-4 items-center">
            <label className="text-sm font-medium text-gray-700">Start Date:</label>
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <label className="text-sm font-medium text-gray-700">End Date:</label>
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Usage Statistics */}
          <Suspense fallback={<div className="bg-white rounded-lg shadow-sm p-6"><div className="animate-pulse h-64 bg-gray-200 rounded"></div></div>}>
            <UsageStatisticsChart data={usageData} />
          </Suspense>

          {/* Model Performance */}
          <Suspense fallback={<div className="bg-white rounded-lg shadow-sm p-6"><div className="animate-pulse h-64 bg-gray-200 rounded"></div></div>}>
            <ModelPerformanceChart data={modelPerformance} />
          </Suspense>

          {/* User Engagement */}
          <Suspense fallback={<div className="bg-white rounded-lg shadow-sm p-6"><div className="animate-pulse h-64 bg-gray-200 rounded"></div></div>}>
            <UserEngagementChart data={userEngagement} />
          </Suspense>

          {/* Real-time Activity */}
          <Suspense fallback={<div className="bg-white rounded-lg shadow-sm p-6"><div className="animate-pulse h-32 bg-gray-200 rounded"></div></div>}>
            <RealTimeActivity activities={activities} />
          </Suspense>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
