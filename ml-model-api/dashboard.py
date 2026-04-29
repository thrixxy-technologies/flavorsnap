"""
Advanced Monitoring Dashboard for FlavorSnap
Real-time dashboard with comprehensive metrics and alert visualization
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio
import aiohttp
import aiofiles
from flask import Flask, render_template_string, jsonify, request
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DashboardConfig:
    """Dashboard configuration"""
    title: str = "FlavorSnap Monitoring Dashboard"
    refresh_interval: int = 30  # seconds
    theme: str = "light"
    widgets: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.widgets is None:
            self.widgets = []


class MonitoringDashboard:
    """Advanced monitoring dashboard"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = DashboardConfig(**config.get('dashboard', {}))
        self.app = Flask(__name__)
        self.setup_routes()
        
        # External integrations
        self.metrics_collector = None
        self.alert_manager = None
        self.health_checker = None
        
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        async def dashboard():
            """Main dashboard page"""
            return await self.render_dashboard()
        
        @self.app.route('/api/metrics/<metric_name>')
        async def get_metrics(metric_name):
            """Get metrics data"""
            hours = request.args.get('hours', 24, type=int)
            return await self.get_metrics_data(metric_name, hours)
        
        @self.app.route('/api/alerts')
        async def get_alerts():
            """Get active alerts"""
            return await self.get_alerts_data()
        
        @self.app.route('/api/health')
        async def get_health():
            """Get health status"""
            return await self.get_health_data()
        
        @self.app.route('/api/system-overview')
        async def get_system_overview():
            """Get system overview"""
            return await self.get_system_overview_data()
        
        @self.app.route('/api/performance')
        async def get_performance():
            """Get performance metrics"""
            hours = request.args.get('hours', 24, type=int)
            return await self.get_performance_data(hours)
        
        @self.app.route('/config')
        async def dashboard_config():
            """Get dashboard configuration"""
            return jsonify(asdict(self.config))
    
    async def render_dashboard(self) -> str:
        """Render main dashboard HTML"""
        template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 2rem;
            font-weight: 600;
        }
        
        .header .subtitle {
            opacity: 0.9;
            margin-top: 0.5rem;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        .card-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #2c3e50;
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            margin: 1rem 0;
        }
        
        .metric-change {
            font-size: 0.875rem;
            font-weight: 500;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
        }
        
        .metric-change.positive {
            background-color: #d4edda;
            color: #155724;
        }
        
        .metric-change.negative {
            background-color: #f8d7da;
            color: #721c24;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 0.5rem;
        }
        
        .status-healthy { background-color: #28a745; }
        .status-warning { background-color: #ffc107; }
        .status-critical { background-color: #dc3545; }
        
        .chart-container {
            height: 400px;
            margin: 1rem 0;
        }
        
        .alert-item {
            padding: 0.75rem;
            border-left: 4px solid;
            margin-bottom: 0.5rem;
            background-color: #f8f9fa;
            border-radius: 4px;
        }
        
        .alert-critical { border-left-color: #dc3545; }
        .alert-high { border-left-color: #fd7e14; }
        .alert-medium { border-left-color: #ffc107; }
        .alert-low { border-left-color: #6c757d; }
        
        .refresh-button {
            background: #667eea;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: background 0.2s ease;
        }
        
        .refresh-button:hover {
            background: #5a6fd8;
        }
        
        .loading {
            opacity: 0.6;
            pointer-events: none;
        }
        
        .last-updated {
            font-size: 0.875rem;
            color: #6c757d;
            margin-top: 1rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <div class="subtitle">Real-time monitoring and alerting</div>
    </div>
    
    <div class="container">
        <div class="grid">
            <!-- System Overview Card -->
            <div class="card">
                <h2 class="card-title">
                    <span class="status-indicator" id="system-status"></span>
                    System Status
                </h2>
                <div id="system-overview">
                    <div class="loading">Loading...</div>
                </div>
            </div>
            
            <!-- CPU Usage Card -->
            <div class="card">
                <h2 class="card-title">CPU Usage</h2>
                <div class="metric-value" id="cpu-value">--%</div>
                <div class="metric-change" id="cpu-change">--</div>
                <div class="chart-container" id="cpu-chart"></div>
            </div>
            
            <!-- Memory Usage Card -->
            <div class="card">
                <h2 class="card-title">Memory Usage</h2>
                <div class="metric-value" id="memory-value">--%</div>
                <div class="metric-change" id="memory-change">--</div>
                <div class="chart-container" id="memory-chart"></div>
            </div>
            
            <!-- Active Alerts Card -->
            <div class="card">
                <h2 class="card-title">Active Alerts</h2>
                <div class="metric-value" id="alerts-count">--</div>
                <div id="alerts-list">
                    <div class="loading">Loading...</div>
                </div>
            </div>
        </div>
        
        <!-- Performance Charts -->
        <div class="card">
            <h2 class="card-title">Performance Overview</h2>
            <div class="chart-container" id="performance-chart"></div>
        </div>
        
        <!-- Health Check Results -->
        <div class="card">
            <h2 class="card-title">Health Checks</h2>
            <div id="health-checks">
                <div class="loading">Loading...</div>
            </div>
        </div>
        
        <div class="last-updated">
            Last updated: <span id="last-updated">--</span>
            <button class="refresh-button" onclick="refreshDashboard()">Refresh</button>
        </div>
    </div>
    
    <script>
        let refreshInterval;
        
        async function refreshDashboard() {
            try {
                document.body.classList.add('loading');
                
                // Update system overview
                await updateSystemOverview();
                
                // Update metrics
                await updateMetrics();
                
                // Update alerts
                await updateAlerts();
                
                // Update health
                await updateHealth();
                
                // Update performance
                await updatePerformance();
                
                // Update timestamp
                document.getElementById('last-updated').textContent = new Date().toLocaleString();
                
            } catch (error) {
                console.error('Error refreshing dashboard:', error);
            } finally {
                document.body.classList.remove('loading');
            }
        }
        
        async function updateSystemOverview() {
            try {
                const response = await axios.get('/api/system-overview');
                const data = response.data;
                
                // Update system status indicator
                const statusElement = document.getElementById('system-status');
                statusElement.className = `status-indicator status-${data.overall_status}`;
                
                // Update system overview content
                const overviewElement = document.getElementById('system-overview');
                overviewElement.innerHTML = `
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                        <div>
                            <strong>Overall Status:</strong> ${data.overall_status.toUpperCase()}
                        </div>
                        <div>
                            <strong>Active Alerts:</strong> ${data.active_alerts}
                        </div>
                        <div>
                            <strong>Services:</strong> ${data.services_healthy}/${data.services_total}
                        </div>
                        <div>
                            <strong>Uptime:</strong> ${data.uptime}
                        </div>
                    </div>
                `;
            } catch (error) {
                console.error('Error updating system overview:', error);
            }
        }
        
        async function updateMetrics() {
            try {
                // Update CPU metrics
                await updateMetric('cpu', 'cpu-value', 'cpu-change', 'cpu-chart');
                
                // Update Memory metrics
                await updateMetric('memory', 'memory-value', 'memory-change', 'memory-chart');
                
            } catch (error) {
                console.error('Error updating metrics:', error);
            }
        }
        
        async function updateMetric(metricName, valueElementId, changeElementId, chartElementId) {
            try {
                const response = await axios.get(`/api/metrics/${metricName}?hours=1`);
                const data = response.data;
                
                // Update current value
                const currentValue = data.current.toFixed(1);
                document.getElementById(valueElementId).textContent = `${currentValue}%`;
                
                // Update change indicator
                const changeElement = document.getElementById(changeElementId);
                if (data.trend === 'increasing') {
                    changeElement.textContent = '↑ Trending up';
                    changeElement.className = 'metric-change negative';
                } else if (data.trend === 'decreasing') {
                    changeElement.textContent = '↓ Trending down';
                    changeElement.className = 'metric-change positive';
                } else {
                    changeElement.textContent = '→ Stable';
                    changeElement.className = 'metric-change';
                }
                
                // Update chart
                const chartData = data.history.map(point => ({
                    x: point.timestamp,
                    y: point.value
                }));
                
                const trace = {
                    x: chartData.map(d => d.x),
                    y: chartData.map(d => d.y),
                    type: 'scatter',
                    mode: 'lines',
                    name: metricName.charAt(0).toUpperCase() + metricName.slice(1),
                    line: { color: '#667eea', width: 2 }
                };
                
                const layout = {
                    height: 300,
                    margin: { t: 20, r: 20, b: 40, l: 50 },
                    yaxis: { title: `${metricName.charAt(0).toUpperCase() + metricName.slice(1)} (%)` },
                    showlegend: false
                };
                
                Plotly.newPlot(chartElementId, [trace], layout, {responsive: true});
                
            } catch (error) {
                console.error(`Error updating ${metricName} metric:`, error);
            }
        }
        
        async function updateAlerts() {
            try {
                const response = await axios.get('/api/alerts');
                const alerts = response.data;
                
                // Update alerts count
                document.getElementById('alerts-count').textContent = alerts.length;
                
                // Update alerts list
                const alertsListElement = document.getElementById('alerts-list');
                if (alerts.length === 0) {
                    alertsListElement.innerHTML = '<div style="text-align: center; color: #6c757d;">No active alerts</div>';
                } else {
                    alertsListElement.innerHTML = alerts.map(alert => `
                        <div class="alert-item alert-${alert.severity.toLowerCase()}">
                            <strong>${alert.title}</strong>
                            <div style="font-size: 0.875rem; margin-top: 0.25rem;">
                                ${alert.message}
                            </div>
                            <div style="font-size: 0.75rem; color: #6c757d; margin-top: 0.25rem;">
                                ${new Date(alert.created_at).toLocaleString()}
                            </div>
                        </div>
                    `).join('');
                }
                
            } catch (error) {
                console.error('Error updating alerts:', error);
            }
        }
        
        async function updateHealth() {
            try {
                const response = await axios.get('/api/health');
                const health = response.data;
                
                const healthElement = document.getElementById('health-checks');
                healthElement.innerHTML = Object.entries(health.checks).map(([checkName, checkData]) => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid #e9ecef;">
                        <div>
                            <span class="status-indicator status-${checkData.status}"></span>
                            <strong>${checkName.charAt(0).toUpperCase() + checkName.slice(1)}</strong>
                        </div>
                        <div style="font-size: 0.875rem; color: #6c757d;">
                            ${checkData.message}
                        </div>
                    </div>
                `).join('');
                
            } catch (error) {
                console.error('Error updating health:', error);
            }
        }
        
        async function updatePerformance() {
            try {
                const response = await axios.get('/api/performance?hours=24');
                const data = response.data;
                
                const traces = Object.entries(data).map(([metricName, metricData]) => ({
                    x: metricData.history.map(point => point.timestamp),
                    y: metricData.history.map(point => point.value),
                    type: 'scatter',
                    mode: 'lines',
                    name: metricName,
                    line: { width: 2 }
                }));
                
                const layout = {
                    height: 400,
                    margin: { t: 20, r: 20, b: 40, l: 50 },
                    xaxis: { title: 'Time' },
                    yaxis: { title: 'Value' },
                    legend: { x: 0, y: 1 }
                };
                
                Plotly.newPlot('performance-chart', traces, layout, {responsive: true});
                
            } catch (error) {
                console.error('Error updating performance:', error);
            }
        }
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            refreshDashboard();
            
            // Set up auto-refresh
            refreshInterval = setInterval(refreshDashboard, {{ refresh_interval }} * 1000);
        });
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', function() {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
        });
    </script>
</body>
</html>
        '''
        
        return render_template_string(template, title=self.config.title, refresh_interval=self.config.refresh_interval)
    
    async def get_metrics_data(self, metric_name: str, hours: int) -> Dict[str, Any]:
        """Get metrics data for dashboard"""
        if not self.metrics_collector:
            return {'error': 'Metrics collector not available'}
        
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # Get metrics from collector
            metrics = self.metrics_collector.query_metrics(metric_name, start_time, end_time)
            
            if not metrics:
                return {'error': 'No metrics data available'}
            
            # Get summary
            summary = self.metrics_collector.get_metric_summary(metric_name, hours)
            
            # Prepare history data
            history = [
                {
                    'timestamp': metric.timestamp.isoformat(),
                    'value': metric.value
                }
                for metric in metrics[-100:]  # Last 100 points
            ]
            
            return {
                'current': summary.get('latest', 0),
                'trend': summary.get('trend', 'stable'),
                'summary': summary,
                'history': history
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics data for {metric_name}: {e}")
            return {'error': str(e)}
    
    async def get_alerts_data(self) -> List[Dict[str, Any]]:
        """Get active alerts data"""
        if not self.alert_manager:
            return []
        
        try:
            active_alerts = self.alert_manager.get_active_alerts()
            
            return [
                {
                    'id': alert.id,
                    'title': alert.title,
                    'message': alert.message,
                    'severity': alert.severity,
                    'created_at': alert.created_at.isoformat(),
                    'status': alert.status,
                    'assignee': alert.assignee
                }
                for alert in active_alerts
            ]
            
        except Exception as e:
            logger.error(f"Error getting alerts data: {e}")
            return []
    
    async def get_health_data(self) -> Dict[str, Any]:
        """Get health check data"""
        if not self.health_checker:
            return {'error': 'Health checker not available'}
        
        try:
            health_results = self.health_checker.run_all_checks()
            return health_results
        except Exception as e:
            logger.error(f"Error getting health data: {e}")
            return {'error': str(e)}
    
    async def get_system_overview_data(self) -> Dict[str, Any]:
        """Get system overview data"""
        try:
            # Get current metrics
            cpu_summary = self.metrics_collector.get_metric_summary('cpu_usage', 5) if self.metrics_collector else {}
            memory_summary = self.metrics_collector.get_metric_summary('memory_usage', 5) if self.metrics_collector else {}
            
            # Get active alerts
            active_alerts = len(self.alert_manager.get_active_alerts()) if self.alert_manager else 0
            
            # Get health status
            health_results = self.health_checker.run_all_checks() if self.health_checker else {}
            overall_status = health_results.get('overall_status', 'unknown')
            
            # Count services
            services_total = len(health_results.get('checks', {}))
            services_healthy = len([
                check for check in health_results.get('checks', {}).values()
                if check.get('status') == 'healthy'
            ])
            
            # Calculate uptime (placeholder)
            uptime = "2 days, 14 hours"
            
            return {
                'overall_status': overall_status,
                'active_alerts': active_alerts,
                'services_total': services_total,
                'services_healthy': services_healthy,
                'uptime': uptime,
                'cpu_usage': cpu_summary.get('latest', 0),
                'memory_usage': memory_summary.get('latest', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting system overview data: {e}")
            return {'error': str(e)}
    
    async def get_performance_data(self, hours: int) -> Dict[str, Any]:
        """Get performance metrics data"""
        if not self.metrics_collector:
            return {'error': 'Metrics collector not available'}
        
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            performance_metrics = ['cpu_usage', 'memory_usage', 'http_request_duration', 'model_inference_time']
            performance_data = {}
            
            for metric_name in performance_metrics:
                metrics = self.metrics_collector.query_metrics(metric_name, start_time, end_time)
                
                if metrics:
                    history = [
                        {
                            'timestamp': metric.timestamp.isoformat(),
                            'value': metric.value
                        }
                        for metric in metrics[-100:]  # Last 100 points
                    ]
                    
                    performance_data[metric_name] = {
                        'history': history,
                        'summary': self.metrics_collector.get_metric_summary(metric_name, hours)
                    }
            
            return performance_data
            
        except Exception as e:
            logger.error(f"Error getting performance data: {e}")
            return {'error': str(e)}
    
    def set_integrations(self, metrics_collector=None, alert_manager=None, health_checker=None):
        """Set external integrations"""
        self.metrics_collector = metrics_collector
        self.alert_manager = alert_manager
        self.health_checker = health_checker
    
    def run(self, host='0.0.0.0', port=8080, debug=False):
        """Run the dashboard server"""
        logger.info(f"Starting monitoring dashboard on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)


class DashboardGenerator:
    """Generate static dashboard reports"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_dir = Path(config.get('output_dir', 'dashboard_reports'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_html_report(self, metrics_data: Dict[str, Any], alerts_data: List[Dict[str, Any]], 
                           health_data: Dict[str, Any]) -> str:
        """Generate comprehensive HTML report"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FlavorSnap Monitoring Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 8px; margin-bottom: 2rem; }
        .section { background: white; padding: 1.5rem; margin-bottom: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
        .metric-card { background: #f8f9fa; padding: 1rem; border-radius: 6px; text-align: center; }
        .metric-value { font-size: 2rem; font-weight: bold; color: #667eea; }
        .metric-label { font-size: 0.875rem; color: #6c757d; margin-top: 0.5rem; }
        .chart { height: 400px; margin: 1rem 0; }
        .alert-item { padding: 0.75rem; margin: 0.5rem 0; border-left: 4px solid; background: #f8f9fa; border-radius: 4px; }
        .alert-critical { border-left-color: #dc3545; }
        .alert-high { border-left-color: #fd7e14; }
        .alert-medium { border-left-color: #ffc107; }
        .alert-low { border-left-color: #6c757d; }
        .health-item { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid #e9ecef; }
        .status-healthy { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-unhealthy { color: #dc3545; }
    </style>
</head>
<body>
    <div class="header">
        <h1>FlavorSnap Monitoring Report</h1>
        <p>Generated on: {{ timestamp }}</p>
    </div>
    
    <div class="section">
        <h2>System Overview</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value">{{ system_status }}</div>
                <div class="metric-label">System Status</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ active_alerts }}</div>
                <div class="metric-label">Active Alerts</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ cpu_usage }}%</div>
                <div class="metric-label">CPU Usage</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ memory_usage }}%</div>
                <div class="metric-label">Memory Usage</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>Performance Metrics</h2>
        <div id="performance-chart" class="chart"></div>
    </div>
    
    <div class="section">
        <h2>Active Alerts</h2>
        {% if alerts %}
            {% for alert in alerts %}
            <div class="alert-item alert-{{ alert.severity.lower() }}">
                <strong>{{ alert.title }}</strong>
                <p>{{ alert.message }}</p>
                <small>{{ alert.created_at }}</small>
            </div>
            {% endfor %}
        {% else %}
            <p>No active alerts</p>
        {% endif %}
    </div>
    
    <div class="section">
        <h2>Health Checks</h2>
        {% for check_name, check_data in health_checks.items() %}
        <div class="health-item">
            <div>
                <span class="status-{{ check_data.status }}"></span>
                <strong>{{ check_name }}</strong>
            </div>
            <div>{{ check_data.message }}</div>
        </div>
        {% endfor %}
    </div>
    
    <script>
        // Performance chart
        const performanceData = {{ performance_chart_data | safe }};
        const traces = Object.entries(performanceData).map(([name, data]) => ({
            x: data.map(d => d.timestamp),
            y: data.map(d => d.value),
            type: 'scatter',
            mode: 'lines',
            name: name
        }));
        
        const layout = {
            title: 'Performance Metrics (24 hours)',
            xaxis: { title: 'Time' },
            yaxis: { title: 'Value' }
        };
        
        Plotly.newPlot('performance-chart', traces, layout);
    </script>
</body>
</html>
        '''
        
        # Prepare data for template
        system_status = health_data.get('overall_status', 'unknown').upper()
        active_alerts = len(alerts_data)
        cpu_usage = metrics_data.get('cpu_usage', {}).get('latest', 0)
        memory_usage = metrics_data.get('memory_usage', {}).get('latest', 0)
        
        # Prepare performance chart data
        performance_chart_data = {}
        for metric_name, metric_data in metrics_data.items():
            if 'history' in metric_data:
                performance_chart_data[metric_name] = metric_data['history']
        
        # Generate HTML
        from jinja2 import Template
        template = Template(html_template)
        html_content = template.render(
            timestamp=timestamp,
            system_status=system_status,
            active_alerts=active_alerts,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            alerts=alerts_data,
            health_checks=health_data.get('checks', {}),
            performance_chart_data=json.dumps(performance_chart_data)
        )
        
        # Save report
        report_file = self.output_dir / f"monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Generated HTML report: {report_file}")
        return str(report_file)
    
    def generate_json_report(self, metrics_data: Dict[str, Any], alerts_data: List[Dict[str, Any]], 
                          health_data: Dict[str, Any]) -> str:
        """Generate JSON report"""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'system_overview': {
                'status': health_data.get('overall_status', 'unknown'),
                'active_alerts': len(alerts_data),
                'services_healthy': len([
                    check for check in health_data.get('checks', {}).values()
                    if check.get('status') == 'healthy'
                ]),
                'services_total': len(health_data.get('checks', {}))
            },
            'metrics': metrics_data,
            'alerts': alerts_data,
            'health_checks': health_data
        }
        
        # Save JSON report
        report_file = self.output_dir / f"monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Generated JSON report: {report_file}")
        return str(report_file)


# Global dashboard instance
monitoring_dashboard = None


def initialize_dashboard(config: Dict[str, Any]) -> MonitoringDashboard:
    """Initialize global monitoring dashboard"""
    global monitoring_dashboard
    monitoring_dashboard = MonitoringDashboard(config)
    return monitoring_dashboard


def get_dashboard() -> Optional[MonitoringDashboard]:
    """Get global dashboard instance"""
    return monitoring_dashboard
