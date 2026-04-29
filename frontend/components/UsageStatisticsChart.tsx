import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface UsageStats {
  date: string;
  requests: number;
  users: number;
  accuracy: number;
}

interface Props {
  data: UsageStats[];
}

const UsageStatisticsChart: React.FC<Props> = ({ data }) => {
  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Usage Statistics</h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="requests" stroke="#3B82F6" name="Requests" />
          <Line type="monotone" dataKey="users" stroke="#10B981" name="Active Users" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default UsageStatisticsChart;