import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { 
  Users, 
  Brain, 
  Shield, 
  TrendingUp, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  Trophy,
  Activity,
  Network,
  Lock,
  Award,
  BarChart3
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

interface FederatedTrainingStats {
  current_status: string;
  current_round: number;
  total_participants: number;
  completed_rounds: number;
  global_accuracy: number;
  global_loss: number;
  total_rewards_distributed: number;
  participant_stats: Record<string, {
    reputation_score: number;
    contribution_count: number;
    total_rewards: number;
    status: string;
  }>;
}

interface ValidationReport {
  report_id: string;
  task_id: string;
  validator_address: string;
  validation_type: string;
  status: string;
  accuracy_score?: number;
  confidence_score: number;
  timestamp: string;
}

interface Participant {
  participant_id: string;
  address: string;
  reputation_score: number;
  contribution_count: number;
  total_rewards: number;
  status: string;
  data_size: number;
  computation_power: number;
}

interface FederatedTrainingProps {
  userAddress?: string;
  onParticipate?: () => void;
  onValidate?: () => void;
}

const FederatedTraining: React.FC<FederatedTrainingProps> = ({ 
  userAddress, 
  onParticipate, 
  onValidate 
}) => {
  const [stats, setStats] = useState<FederatedTrainingStats | null>(null);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [validations, setValidations] = useState<ValidationReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedParticipant, setSelectedParticipant] = useState<Participant | null>(null);
  const [trainingHistory, setTrainingHistory] = useState<any[]>([]);

  useEffect(() => {
    fetchFederatedData();
    const interval = setInterval(fetchFederatedData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchFederatedData = async () => {
    try {
      setLoading(true);
      
      // Fetch training statistics
      const statsResponse = await fetch('/api/federated/stats');
      const statsData = await statsResponse.json();
      setStats(statsData);

      // Fetch participants
      const participantsResponse = await fetch('/api/federated/participants');
      const participantsData = await participantsResponse.json();
      setParticipants(participantsData.participants || []);

      // Fetch recent validations
      const validationsResponse = await fetch('/api/federated/validations');
      const validationsData = await validationsResponse.json();
      setValidations(validationsData.validations || []);

      // Fetch training history
      const historyResponse = await fetch('/api/federated/history');
      const historyData = await historyResponse.json();
      setTrainingHistory(historyData.history || []);

    } catch (error) {
      console.error('Failed to fetch federated data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500';
      case 'training': return 'bg-blue-500';
      case 'aggregating': return 'bg-orange-500';
      case 'validating': return 'bg-purple-500';
      case 'failed': return 'bg-red-500';
      case 'idle': return 'bg-gray-500';
      default: return 'bg-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4" />;
      case 'training': return <Brain className="w-4 h-4" />;
      case 'failed': return <AlertCircle className="w-4 h-4" />;
      default: return <Activity className="w-4 h-4" />;
    }
  };

  const getReputationBadge = (score: number) => {
    if (score >= 0.8) return <Badge className="bg-purple-500">Expert</Badge>;
    if (score >= 0.6) return <Badge className="bg-blue-500">Advanced</Badge>;
    if (score >= 0.4) return <Badge className="bg-green-500">Intermediate</Badge>;
    return <Badge variant="outline">Beginner</Badge>;
  };

  const OverviewTab = () => (
    <div className="space-y-6">
      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Training Status</p>
                <p className="text-2xl font-bold capitalize">{stats?.current_status || 'Unknown'}</p>
              </div>
              <div className={`p-2 rounded-full ${getStatusColor(stats?.current_status || '')}`}>
                {getStatusIcon(stats?.current_status || '')}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Current Round</p>
                <p className="text-2xl font-bold">{stats?.current_round || 0}</p>
              </div>
              <TrendingUp className="w-8 h-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Global Accuracy</p>
                <p className="text-2xl font-bold">{((stats?.global_accuracy || 0) * 100).toFixed(1)}%</p>
              </div>
              <Brain className="w-8 h-8 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Active Participants</p>
                <p className="text-2xl font-bold">{stats?.total_participants || 0}</p>
              </div>
              <Users className="w-8 h-8 text-purple-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Training Progress */}
      {stats?.current_status === 'training' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Training Progress
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Round {stats?.current_round || 0} Progress</span>
                  <span>{((stats?.completed_rounds || 0) / 10 * 100).toFixed(0)}%</span>
                </div>
                <Progress value={(stats?.completed_rounds || 0) / 10 * 100} />
              </div>
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Global Loss:</span>
                  <span className="ml-2 font-medium">{(stats?.global_loss || 0).toFixed(4)}</span>
                </div>
                <div>
                  <span className="text-gray-600">Rewards Distributed:</span>
                  <span className="ml-2 font-medium">{stats?.total_rewards_distributed || 0} tokens</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Action Buttons */}
      <div className="flex gap-4">
        <Button onClick={onParticipate} disabled={!userAddress}>
          <Users className="w-4 h-4 mr-2" />
          Participate in Training
        </Button>
        <Button variant="outline" onClick={onValidate} disabled={!userAddress}>
          <Shield className="w-4 h-4 mr-2" />
          Validate Models
        </Button>
      </div>

      {!userAddress && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Please connect your wallet to participate in federated training or model validation.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );

  const ParticipantsTab = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="w-5 h-5" />
            Training Participants ({participants.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {participants.map((participant) => (
              <div
                key={participant.participant_id}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 cursor-pointer"
                onClick={() => setSelectedParticipant(participant)}
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                    <Users className="w-5 h-5 text-blue-600" />
                  </div>
                  
                  <div>
                    <p className="font-medium">{participant.participant_id}</p>
                    <p className="text-sm text-gray-500">
                      {participant.address.slice(0, 6)}...{participant.address.slice(-4)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {getReputationBadge(participant.reputation_score)}
                  
                  <div className="text-right">
                    <p className="text-sm font-medium">{participant.contribution_count} contributions</p>
                    <p className="text-sm text-gray-500">{participant.total_rewards.toFixed(1)} tokens earned</p>
                  </div>
                  
                  <Badge className={participant.status === 'active' ? 'bg-green-500' : 'bg-gray-500'}>
                    {participant.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Participant Details Dialog */}
      <Dialog open={!!selectedParticipant} onOpenChange={() => setSelectedParticipant(null)}>
        <DialogContent className="max-w-2xl">
          {selectedParticipant && (
            <>
              <DialogHeader>
                <DialogTitle>Participant Details</DialogTitle>
              </DialogHeader>
              
              <div className="space-y-6">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center">
                    <Users className="w-8 h-8 text-blue-600" />
                  </div>
                  
                  <div>
                    <h3 className="text-lg font-semibold">{selectedParticipant.participant_id}</h3>
                    <p className="text-gray-500">{selectedParticipant.address}</p>
                    {getReputationBadge(selectedParticipant.reputation_score)}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Card>
                    <CardContent className="p-4">
                      <div className="flex items-center gap-2">
                        <Trophy className="w-5 h-5 text-yellow-500" />
                        <span className="font-medium">Reputation Score</span>
                      </div>
                      <p className="text-2xl font-bold">{(selectedParticipant.reputation_score * 100).toFixed(1)}%</p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="p-4">
                      <div className="flex items-center gap-2">
                        <BarChart3 className="w-5 h-5 text-blue-500" />
                        <span className="font-medium">Contributions</span>
                      </div>
                      <p className="text-2xl font-bold">{selectedParticipant.contribution_count}</p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="p-4">
                      <div className="flex items-center gap-2">
                        <Award className="w-5 h-5 text-green-500" />
                        <span className="font-medium">Total Rewards</span>
                      </div>
                      <p className="text-2xl font-bold">{selectedParticipant.total_rewards.toFixed(1)} tokens</p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="p-4">
                      <div className="flex items-center gap-2">
                        <Network className="w-5 h-5 text-purple-500" />
                        <span className="font-medium">Data Size</span>
                      </div>
                      <p className="text-2xl font-bold">{(selectedParticipant.data_size / 1000).toFixed(1)}K samples</p>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );

  const ValidationTab = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Recent Validations ({validations.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {validations.map((validation) => (
              <div key={validation.report_id} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-4">
                  <div className={`p-2 rounded-full ${getStatusColor(validation.status)}`}>
                    {getStatusIcon(validation.status)}
                  </div>
                  
                  <div>
                    <p className="font-medium">{validation.validation_type.replace('_', ' ').toUpperCase()}</p>
                    <p className="text-sm text-gray-500">
                      Validator: {validation.validator_address.slice(0, 6)}...{validation.validator_address.slice(-4)}
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  {validation.accuracy_score && (
                    <p className="font-medium">{(validation.accuracy_score * 100).toFixed(1)}% accuracy</p>
                  )}
                  <p className="text-sm text-gray-500">
                    Confidence: {(validation.confidence_score * 100).toFixed(1)}%
                  </p>
                  <p className="text-xs text-gray-400">
                    {new Date(validation.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const AnalyticsTab = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Training Progress Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Training Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trainingHistory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="round" />
                <YAxis />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="accuracy" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  name="Accuracy"
                />
                <Line 
                  type="monotone" 
                  dataKey="loss" 
                  stroke="#ef4444" 
                  strokeWidth={2}
                  name="Loss"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Participant Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Participant Reputation Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={[
                { range: '0-20', count: participants.filter(p => p.reputation_score < 0.2).length },
                { range: '20-40', count: participants.filter(p => p.reputation_score >= 0.2 && p.reputation_score < 0.4).length },
                { range: '40-60', count: participants.filter(p => p.reputation_score >= 0.4 && p.reputation_score < 0.6).length },
                { range: '60-80', count: participants.filter(p => p.reputation_score >= 0.6 && p.reputation_score < 0.8).length },
                { range: '80-100', count: participants.filter(p => p.reputation_score >= 0.8).length },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#8b5cf6" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Network Statistics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="w-5 h-5" />
            Network Statistics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600">{participants.length}</div>
              <p className="text-gray-600">Active Participants</p>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">
                {((stats?.global_accuracy || 0) * 100).toFixed(1)}%
              </div>
              <p className="text-gray-600">Global Accuracy</p>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-600">{stats?.total_rewards_distributed || 0}</div>
              <p className="text-gray-600">Tokens Distributed</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Federated Learning</h2>
        <div className="flex items-center gap-2">
          <Lock className="w-4 h-4 text-green-600" />
          <span className="text-sm text-gray-600">Privacy-Preserving</span>
          <Shield className="w-4 h-4 text-blue-600" />
          <span className="text-sm text-gray-600">Blockchain Validated</span>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="participants">Participants</TabsTrigger>
          <TabsTrigger value="validation">Validation</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewTab />
        </TabsContent>

        <TabsContent value="participants">
          <ParticipantsTab />
        </TabsContent>

        <TabsContent value="validation">
          <ValidationTab />
        </TabsContent>

        <TabsContent value="analytics">
          <AnalyticsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default FederatedTraining;
