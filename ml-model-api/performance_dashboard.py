"""
Performance Dashboard for FlavorSnap Model Management
Provides visualization and comparison of model performance metrics
"""

import json
from typing import Dict, Any
from datetime import datetime

try:
    import panel as pn
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import pandas as pd
    import numpy as np
    import sqlite3
    from model_registry import ModelRegistry
    from ab_testing import ABTestManager
    DASHBOARD_AVAILABLE = True
except ImportError as e:
    print(f"Dashboard dependencies not available: {e}")
    DASHBOARD_AVAILABLE = False


class ModelPerformanceDashboard:
    """Interactive dashboard for model performance monitoring"""
    
    def __init__(self, model_registry: ModelRegistry, ab_test_manager: ABTestManager):
        self.model_registry = model_registry
        self.ab_test_manager = ab_test_manager
        pn.extension('plotly')
        
        # Initialize UI components
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup dashboard UI components"""
        
        # Header
        header = pn.pane.HTML("""
        <h1>🍲 FlavorSnap Model Performance Dashboard</h1>
        <p>Monitor and compare model versions, A/B tests, and performance metrics</p>
        """)
        
        # Tabs for different views
        tabs = pn.Tabs(
            ('Model Registry', self._create_registry_tab()),
            ('A/B Testing', self._create_ab_testing_tab()),
            ('Performance Comparison', self._create_comparison_tab()),
            ('Live Metrics', self._create_live_metrics_tab())
        )
        
        self.layout = pn.Column(header, tabs)
    
    def _create_registry_tab(self):
        """Create model registry tab"""
        
        # Model list
        model_list = self._get_model_table()
        
        # Model details
        model_details = pn.pane.Markdown("Select a model to view details")
        
        # Model selection widget
        model_select = pn.widgets.Select(
            name='Select Model',
            options=[''] + [m.version for m in self.model_registry.list_models()]
        )
        
        def update_model_details(event):
            if event.new:
                model = self.model_registry.get_model(event.new)
                if model:
                    details = f"""
                    ## Model Details: {model.version}
                    
                    **Description:** {model.description}
                    
                    **Created:** {model.created_at}
                    **Created By:** {model.created_by}
                    
                    **Performance:**
                    - Accuracy: {model.accuracy:.2%}' if model.accuracy else 'N/A'
                    - Loss: {model.loss:.4f}' if model.loss else 'N/A'
                    - Epochs Trained: {model.epochs_trained}
                    
                    **Status:**
                    - Active: {'✅' if model.is_active else '❌'}
                    - Stable: {'✅' if model.is_stable else '❌'}
                    
                    **Tags:** {', '.join(model.tags) if model.tags else 'None'}
                    
                    **Model Hash:** `{model.model_hash[:16]}...` if model.model_hash else 'N/A'
                    """
                    model_details.object = details
        
        model_select.param.watch(update_model_details, 'value')
        
        # Action buttons
        activate_btn = pn.widgets.Button(name='Activate Model', button_type='primary')
        mark_stable_btn = pn.widgets.Button(name='Mark as Stable', button_type='success')
        
        def activate_model(event):
            if model_select.value:
                success = self.model_registry.activate_model(model_select.value)
                if success:
                    pn.state.notifications.success(f"Model {model_select.value} activated")
                    model_list.object = self._get_model_table()
                else:
                    pn.state.notifications.error("Failed to activate model")
        
        def mark_stable(event):
            if model_select.value:
                success = self.model_registry.mark_stable(model_select.value, True)
                if success:
                    pn.state.notifications.success(f"Model {model_select.value} marked as stable")
                    model_list.object = self._get_model_table()
                else:
                    pn.state.notifications.error("Failed to mark model as stable")
        
        activate_btn.on_click(activate_model)
        mark_stable_btn.on_click(mark_stable)
        
        return pn.Column(
            pn.Row(model_select, activate_btn, mark_stable_btn),
            pn.Row(model_list, model_details)
        )
    
    def _create_ab_testing_tab(self):
        """Create A/B testing tab"""
        
        # Test creation form
        model_options = [m.version for m in self.model_registry.list_models()]
        
        model_a_select = pn.widgets.Select(name='Model A', options=model_options)
        model_b_select = pn.widgets.Select(name='Model B', options=model_options)
        traffic_split = pn.widgets.FloatSlider(
            name='Traffic Split (Model B %)',
            start=0.0,
            end=1.0,
            value=0.5,
            step=0.1
        )
        description = pn.widgets.TextAreaInput(name='Description', height=60)
        
        create_test_btn = pn.widgets.Button(name='Create A/B Test', button_type='primary')
        
        def create_test(event):
            if model_a_select.value and model_b_select.value:
                if model_a_select.value == model_b_select.value:
                    pn.state.notifications.error("Models must be different")
                    return
                
                test_id = self.ab_test_manager.create_test(
                    model_a_select.value,
                    model_b_select.value,
                    traffic_split.value,
                    description.value
                )
                pn.state.notifications.success(f"A/B Test created: {test_id[:8]}...")
                test_list.object = self._get_test_table()
            else:
                pn.state.notifications.error("Please select both models")
        
        create_test_btn.on_click(create_test)
        
        # Test list
        test_list = self._get_test_table()
        
        # Test details
        test_details = pn.pane.Markdown("Select a test to view details")
        
        test_select = pn.widgets.Select(name='Select Test', options=[''])
        
        def update_test_details(event):
            if event.new:
                try:
                    summary = self.ab_test_manager.get_test_summary(event.new)
                    details = self._format_test_summary(summary)
                    test_details.object = details
                except Exception as e:
                    test_details.object = f"Error loading test details: {e}"
        
        test_select.param.watch(update_test_details, 'value')
        
        # Update test options
        def update_test_options():
            tests = self.ab_test_manager.list_tests()
            test_select.options = [''] + [f"{t['test_id'][:8]}... ({t['status']})" for t in tests]
        
        update_test_options()
        
        return pn.Column(
            pn.pane.Markdown("### Create New A/B Test"),
            pn.Row(model_a_select, model_b_select, traffic_split),
            pn.Row(description, create_test_btn),
            pn.Divider(),
            pn.pane.Markdown("### Active Tests"),
            pn.Row(test_select, test_list),
            test_details
        )
    
    def _create_comparison_tab(self):
        """Create performance comparison tab"""
        
        # Model selection for comparison
        model_options = [m.version for m in self.model_registry.list_models()]
        
        compare_model_a = pn.widgets.Select(name='Model A', options=model_options)
        compare_model_b = pn.widgets.Select(name='Model B', options=model_options)
        
        compare_btn = pn.widgets.Button(name='Compare Models', button_type='primary')
        
        comparison_chart = pn.pane.Plotly()
        
        def compare_models(event):
            if compare_model_a.value and compare_model_b.value:
                chart = self._create_model_comparison_chart(
                    compare_model_a.value,
                    compare_model_b.value
                )
                comparison_chart.object = chart
            else:
                pn.state.notifications.error("Please select both models")
        
        compare_btn.on_click(compare_models)
        
        return pn.Column(
            pn.Row(compare_model_a, compare_model_b, compare_btn),
            comparison_chart
        )
    
    def _create_live_metrics_tab(self):
        """Create live metrics tab"""
        
        # Auto-refresh controls
        refresh_interval = pn.widgets.IntSlider(
            name='Refresh Interval (seconds)',
            start=5,
            end=60,
            value=10
        )
        
        auto_refresh = pn.widgets.Checkbox(name='Auto Refresh', value=True)
        
        # Metrics charts
        accuracy_chart = pn.pane.Plotly()
        confidence_chart = pn.pane.Plotly()
        volume_chart = pn.pane.Plotly()
        
        def update_metrics():
            # Update charts with latest data
            accuracy_chart.object = self._create_accuracy_timeline()
            confidence_chart.object = self._create_confidence_distribution()
            volume_chart.object = self._create_prediction_volume()
        
        # Initial load
        update_metrics()
        
        # Setup periodic refresh
        def periodic_callback():
            if auto_refresh.value:
                update_metrics()
        
        pn.state.add_periodic_callback(
            periodic_callback,
            period=refresh_interval.value * 1000
        )
        
        return pn.Column(
            pn.Row(refresh_interval, auto_refresh),
            pn.Row(accuracy_chart, confidence_chart),
            volume_chart
        )
    
    def _get_model_table(self):
        """Get model registry table"""
        models = self.model_registry.list_models()
        
        data = []
        for model in models:
            data.append({
                'Version': model.version,
                'Created': model.created_at[:10],
                'Accuracy': f"{model.accuracy:.2%}" if model.accuracy else 'N/A',
                'Active': '✅' if model.is_active else '❌',
                'Stable': '✅' if model.is_stable else '❌',
                'Description': model.description[:50] + '...' if len(model.description) > 50 else model.description
            })
        
        df = pd.DataFrame(data)
        return pn.widgets.Tabulator(df, show_index=False, pagination='remote')
    
    def _get_test_table(self):
        """Get A/B test table"""
        tests = self.ab_test_manager.list_tests()
        
        data = []
        for test in tests:
            data.append({
                'Test ID': test['test_id'][:8] + '...',
                'Model A': test['model_a_version'],
                'Model B': test['model_b_version'],
                'Split': f"{test['traffic_split']*100:.0f}%/{(1-test['traffic_split'])*100:.0f}%",
                'Status': test['status'],
                'Winner': test.get('winner', 'N/A'),
                'Started': test['start_time'][:10] if test['start_time'] else 'N/A'
            })
        
        df = pd.DataFrame(data)
        return pn.widgets.Tabulator(df, show_index=False, pagination='remote')
    
    def _format_test_summary(self, summary: Dict[str, Any]) -> str:
        """Format test summary for display"""
        config = summary['test_config']
        metrics_a = summary['model_a_metrics']
        metrics_b = summary['model_b_metrics']
        significance = summary['statistical_significance']
        
        return f"""
        ## A/B Test Summary: {config['test_id'][:8]}...
        
        **Configuration:**
        - Model A: {config['model_a_version']}
        - Model B: {config['model_b_version']}
        - Traffic Split: {config['traffic_split']*100:.0f}% / {(1-config['traffic_split'])*100:.0f}%
        - Status: {config['status']}
        - Started: {config['start_time'][:19]}
        
        **Performance:**
        - Model A Predictions: {metrics_a['total_predictions']}
        - Model B Predictions: {metrics_b['total_predictions']}
        - Model A Avg Confidence: {metrics_a['avg_confidence']:.3f}
        - Model B Avg Confidence: {metrics_b['avg_confidence']:.3f}
        - Model A Avg Processing Time: {metrics_a['avg_processing_time']:.3f}s
        - Model B Avg Processing Time: {metrics_b['avg_processing_time']:.3f}s
        
        **Statistical Significance:**
        - Significant: {'✅' if significance['significant'] else '❌'}
        - P-value: {significance.get('p_value', 'N/A')}
        - Confidence Threshold: {significance.get('confidence_threshold', 'N/A')}
        """
    
    def _create_model_comparison_chart(self, model_a: str, model_b: str):
        """Create comparison chart for two models"""
        
        # Get metrics from database
        with sqlite3.connect(self.model_registry.registry_path) as conn:
            # Get prediction data for both models
            query = """
                SELECT model_version, confidence, processing_time, timestamp
                FROM predictions
                WHERE model_version IN (?, ?)
                ORDER BY timestamp DESC
                LIMIT 1000
            """
            df = pd.read_sql_query(query, conn, params=(model_a, model_b))
        
        if df.empty:
            return go.Figure().add_annotation(
                text="No data available for comparison",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Confidence Distribution', 'Processing Time Distribution',
                          'Confidence Over Time', 'Prediction Volume'),
            specs=[[{"type": "histogram"}, {"type": "histogram"}],
                   [{"type": "scatter"}, {"type": "bar"}]]
        )
        
        # Confidence distribution
        for i, model in enumerate([model_a, model_b]):
            model_data = df[df['model_version'] == model]
            fig.add_trace(
                go.Histogram(
                    x=model_data['confidence'],
                    name=f'{model} Confidence',
                    opacity=0.7,
                    marker_color=['blue', 'red'][i]
                ),
                row=1, col=1
            )
        
        # Processing time distribution
        for i, model in enumerate([model_a, model_b]):
            model_data = df[df['model_version'] == model]
            fig.add_trace(
                go.Histogram(
                    x=model_data['processing_time'],
                    name=f'{model} Processing Time',
                    opacity=0.7,
                    marker_color=['blue', 'red'][i]
                ),
                row=1, col=2
            )
        
        # Confidence over time
        for i, model in enumerate([model_a, model_b]):
            model_data = df[df['model_version'] == model]
            fig.add_trace(
                go.Scatter(
                    x=model_data['timestamp'],
                    y=model_data['confidence'],
                    mode='markers',
                    name=f'{model} Confidence',
                    marker_color=['blue', 'red'][i],
                    opacity=0.6
                ),
                row=2, col=1
            )
        
        # Prediction volume
        volume_counts = df['model_version'].value_counts()
        fig.add_trace(
            go.Bar(
                x=volume_counts.index,
                y=volume_counts.values,
                name='Prediction Volume',
                marker_color=['blue', 'red']
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title=f"Model Comparison: {model_a} vs {model_b}",
            height=600,
            showlegend=True
        )
        
        return fig
    
    def _create_accuracy_timeline(self):
        """Create accuracy timeline chart"""
        # Placeholder implementation
        fig = go.Figure()
        fig.add_annotation(
            text="Accuracy timeline coming soon...",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    def _create_confidence_distribution(self):
        """Create confidence distribution chart"""
        # Placeholder implementation
        fig = go.Figure()
        fig.add_annotation(
            text="Confidence distribution coming soon...",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    def _create_prediction_volume(self):
        """Create prediction volume chart"""
        # Placeholder implementation
        fig = go.Figure()
        fig.add_annotation(
            text="Prediction volume coming soon...",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig
    
    def serve(self):
        """Serve the dashboard"""
        return self.layout.servable()


def create_dashboard():
    """Create and serve the dashboard"""
    if not DASHBOARD_AVAILABLE:
        return create_simple_dashboard()
    
    try:
        # Initialize components
        model_registry = ModelRegistry()
        ab_test_manager = ABTestManager(model_registry)
        
        # Create dashboard
        dashboard = ModelPerformanceDashboard(model_registry, ab_test_manager)
        
        # Serve
        return dashboard.serve()
    except Exception as e:
        print(f"Error creating full dashboard: {e}")
        return create_simple_dashboard()


def create_simple_dashboard():
    """Create a simple HTML dashboard when full dependencies aren't available"""
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FlavorSnap Performance Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }
            .metric { background: #f8f9fa; padding: 20px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }
            .endpoint { background: #e9ecef; padding: 15px; margin: 10px 0; border-radius: 5px; font-family: monospace; }
            .status { color: #28a745; font-weight: bold; }
            .warning { color: #ffc107; font-weight: bold; }
            .error { color: #dc3545; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🍲 FlavorSnap Performance Dashboard</h1>
            <p><strong>Status:</strong> <span class="warning">Limited Mode</span> - Full dashboard requires additional dependencies</p>
            
            <div class="metric">
                <h3>📊 Available Monitoring Endpoints</h3>
                <div class="endpoint">GET /metrics - Prometheus metrics</div>
                <div class="endpoint">GET /health/detailed - Detailed system health</div>
                <div class="endpoint">GET /api/info - API information</div>
            </div>
            
            <div class="metric">
                <h3>🔧 Installation Instructions</h3>
                <p>To enable the full interactive dashboard, install the required dependencies:</p>
                <div class="endpoint">pip install -r requirements-monitoring.txt</div>
            </div>
            
            <div class="metric">
                <h3>📈 Current Metrics</h3>
                <p>• HTTP Request Count: Available via /metrics</p>
                <p>• Request Duration: Available via /metrics</p>
                <p>• Model Inference Metrics: Available via /metrics</p>
                <p>• System Resources: Available via /health/detailed</p>
            </div>
            
            <div class="metric">
                <h3>🚀 Quick Start</h3>
                <p>1. Install monitoring dependencies: <code>pip install prometheus-client psutil</code></p>
                <p>2. Visit <a href="/metrics">/metrics</a> to see Prometheus metrics</p>
                <p>3. Visit <a href="/health/detailed">/health/detailed</a> for system health</p>
            </div>
            
            <p><small>Dashboard generated at: """ + datetime.now().isoformat() + """</small></p>
        </div>
    </body>
    </html>
    """
    
    from flask import Response
    return Response(html_content, mimetype='text/html')


if __name__ == "__main__":
    dashboard = create_dashboard()
    dashboard.show()
