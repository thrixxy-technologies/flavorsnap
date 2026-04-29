"""
Advanced Reporting System for FlavorSnap Testing and Quality Assurance
Comprehensive test reporting with analytics and insights
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import pandas as pd
import numpy as np
from jinja2 import Template
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder

logger = logging.getLogger(__name__)


@dataclass
class TestReport:
    """Comprehensive test report"""
    timestamp: datetime
    title: str
    summary: Dict[str, Any]
    test_suites: Dict[str, Any]
    quality_gates: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    security_findings: Dict[str, Any]
    coverage_data: Dict[str, Any]
    recommendations: List[str]
    trends: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)


@dataclass
class ReportConfig:
    """Report configuration"""
    title: str = "FlavorSnap Quality Report"
    include_trends: bool = True
    include_recommendations: bool = True
    include_artifacts: bool = True
    output_formats: List[str] = field(default_factory=lambda: ["html", "json"])
    template_dir: str = "templates"
    output_dir: str = "reports"


class TestReportingEngine:
    """Advanced test reporting engine"""
    
    def __init__(self, config: ReportConfig):
        self.config = config
        self.report_history = []
        self.templates = {}
        
        # Ensure output directory exists
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Load templates
        self._load_templates()
    
    def _load_templates(self):
        """Load report templates"""
        template_dir = Path(self.config.template_dir)
        
        # Default HTML template
        self.templates['html'] = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background-color: #f8f9fa; 
            color: #333;
        }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 2rem; 
            border-radius: 12px; 
            margin-bottom: 2rem; 
            text-align: center;
        }
        .header h1 { margin: 0; font-size: 2.5rem; }
        .header p { margin: 0.5rem 0 0 0; opacity: 0.9; }
        .summary-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 1.5rem; 
            margin-bottom: 2rem; 
        }
        .metric-card { 
            background: white; 
            padding: 1.5rem; 
            border-radius: 12px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
            text-align: center; 
            transition: transform 0.2s ease;
        }
        .metric-card:hover { transform: translateY(-2px); }
        .metric-value { 
            font-size: 2.5rem; 
            font-weight: bold; 
            margin: 0.5rem 0; 
        }
        .metric-value.success { color: #28a745; }
        .metric-value.warning { color: #ffc107; }
        .metric-value.danger { color: #dc3545; }
        .metric-label { 
            font-size: 0.875rem; 
            color: #6c757d; 
            text-transform: uppercase; 
            letter-spacing: 0.5px;
        }
        .section { 
            background: white; 
            padding: 2rem; 
            margin-bottom: 2rem; 
            border-radius: 12px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .section h2 { 
            margin: 0 0 1.5rem 0; 
            color: #2c3e50; 
            font-size: 1.75rem;
        }
        .chart-container { 
            height: 400px; 
            margin: 1rem 0; 
        }
        .status-badge { 
            padding: 0.25rem 0.75rem; 
            border-radius: 20px; 
            font-size: 0.75rem; 
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-passed { 
            background: #d4edda; 
            color: #155724; 
        }
        .status-failed { 
            background: #f8d7da; 
            color: #721c24; 
        }
        .status-warning { 
            background: #fff3cd; 
            color: #856404; 
        }
        .test-suite { 
            border: 1px solid #e9ecef; 
            border-radius: 8px; 
            padding: 1rem; 
            margin-bottom: 1rem;
        }
        .test-suite-header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 0.5rem;
        }
        .test-suite-title { 
            font-weight: 600; 
            color: #2c3e50;
        }
        .progress-bar { 
            width: 100%; 
            height: 8px; 
            background: #e9ecef; 
            border-radius: 4px; 
            overflow: hidden;
        }
        .progress-fill { 
            height: 100%; 
            background: linear-gradient(90deg, #28a745, #20c997); 
            transition: width 0.3s ease;
        }
        .recommendations { 
            background: #f8f9fa; 
            border-left: 4px solid #667eea; 
            padding: 1rem; 
            margin: 0.5rem 0;
        }
        .recommendations h4 { 
            margin: 0 0 0.5rem 0; 
            color: #667eea;
        }
        .recommendations ul { 
            margin: 0; 
            padding-left: 1.5rem;
        }
        .recommendations li { 
            margin-bottom: 0.25rem; 
            color: #495057;
        }
        .trend-chart { 
            height: 300px; 
            margin: 1rem 0;
        }
        .footer { 
            text-align: center; 
            padding: 2rem; 
            color: #6c757d; 
            font-size: 0.875rem;
        }
        @media (max-width: 768px) {
            .summary-grid { grid-template-columns: 1fr; }
            .metric-value { font-size: 2rem; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p>Generated on {{ timestamp }} | Overall Status: 
            {% if overall_status == 'passed' %}✅ PASSED{% else %}❌ FAILED{% endif %}
        </p>
    </div>
    
    <!-- Summary Metrics -->
    <div class="summary-grid">
        <div class="metric-card">
            <div class="metric-value {{ summary.success_rate_class }}">{{ "%.1f"|format(summary.success_rate) }}%</div>
            <div class="metric-label">Success Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value {{ summary.total_tests_class }}">{{ summary.total_tests }}</div>
            <div class="metric-label">Total Tests</div>
        </div>
        <div class="metric-card">
            <div class="metric-value {{ summary.coverage_class }}">{{ "%.1f"|format(summary.coverage) }}%</div>
            <div class="metric-label">Code Coverage</div>
        </div>
        <div class="metric-card">
            <div class="metric-value {{ summary.duration_class }}">{{ "%.1f"|format(summary.duration) }}s</div>
            <div class="metric-label">Duration</div>
        </div>
    </div>
    
    <!-- Test Suites -->
    {% if test_suites %}
    <div class="section">
        <h2>Test Suites</h2>
        {% for suite_name, suite_data in test_suites.items() %}
        <div class="test-suite">
            <div class="test-suite-header">
                <div class="test-suite-title">{{ suite_data.name or suite_name }}</div>
                <span class="status-badge status-{{ suite_data.status }}">{{ suite_data.status.upper() }}</span>
            </div>
            <p>{{ suite_data.description }}</p>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {{ suite_data.passed_percentage }}%"></div>
            </div>
            <p>{{ suite_data.passed }}/{{ suite_data.total }} tests passed ({{ "%.1f"|format(suite_data.passed_percentage) }}%)</p>
            {% if suite_data.coverage %}
            <p>Coverage: {{ "%.1f"|format(suite_data.coverage) }}%</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    <!-- Quality Gates -->
    {% if quality_gates %}
    <div class="section">
        <h2>Quality Gates</h2>
        {% for gate_name, gate_data in quality_gates.items() %}
        <div class="test-suite">
            <div class="test-suite-header">
                <div class="test-suite-title">{{ gate_name }}</div>
                <span class="status-badge status-{{ gate_data.status }}">{{ gate_data.status.upper() }}</span>
            </div>
            <p>Score: {{ "%.1f"|format(gate_data.score) }}%</p>
            {% if gate_data.failed_conditions %}
            <p><strong>Failed Conditions:</strong></p>
            <ul>
                {% for condition in gate_data.failed_conditions %}
                <li>{{ condition }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    <!-- Performance Metrics -->
    {% if performance_metrics %}
    <div class="section">
        <h2>Performance Metrics</h2>
        <div id="performance-chart" class="chart-container"></div>
    </div>
    {% endif %}
    
    <!-- Coverage Data -->
    {% if coverage_data %}
    <div class="section">
        <h2>Code Coverage</h2>
        <div id="coverage-chart" class="chart-container"></div>
    </div>
    {% endif %}
    
    <!-- Trends -->
    {% if trends and include_trends %}
    <div class="section">
        <h2>Historical Trends</h2>
        <div id="trends-chart" class="trend-chart"></div>
    </div>
    {% endif %}
    
    <!-- Recommendations -->
    {% if recommendations and include_recommendations %}
    <div class="section">
        <h2>Recommendations</h2>
        {% for recommendation in recommendations %}
        <div class="recommendations">
            <h4>💡 Recommendation</h4>
            <p>{{ recommendation }}</p>
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    <div class="footer">
        <p>Generated by FlavorSnap Test Reporting System | 
           Report ID: {{ report_id }} | 
           View source code on GitHub
        </p>
    </div>
    
    <script>
        // Performance Chart
        {% if performance_metrics %}
        const performanceData = {{ performance_metrics.chart_data | safe }};
        const performanceTrace = {
            x: performanceData.map(d => d.metric),
            y: performanceData.map(d => d.value),
            type: 'bar',
            marker: {
                color: performanceData.map(d => d.value > 1000 ? '#dc3545' : '#28a745')
            }
        };
        
        const performanceLayout = {
            title: 'Performance Metrics',
            xaxis: { title: 'Metric' },
            yaxis: { title: 'Value (ms)' },
            showlegend: false
        };
        
        Plotly.newPlot('performance-chart', [performanceTrace], performanceLayout);
        {% endif %}
        
        // Coverage Chart
        {% if coverage_data %}
        const coverageData = {{ coverage_data.chart_data | safe }};
        const coverageTrace = {
            labels: coverageData.map(d => d.module),
            values: coverageData.map(d => d.coverage),
            type: 'pie',
            hole: 0.4,
            marker: {
                colors: coverageData.map(d => d.coverage > 80 ? '#28a745' : d.coverage > 60 ? '#ffc107' : '#dc3545')
            }
        };
        
        const coverageLayout = {
            title: 'Code Coverage by Module',
            showlegend: true
        };
        
        Plotly.newPlot('coverage-chart', [coverageTrace], coverageLayout);
        {% endif %}
        
        // Trends Chart
        {% if trends and include_trends %}
        const trendsData = {{ trends.chart_data | safe }};
        const trendsTrace = {
            x: trendsData.map(d => d.date),
            y: trendsData.map(d => d.score),
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Quality Score',
            line: { color: '#667eea', width: 3 }
        };
        
        const trendsLayout = {
            title: 'Quality Score Trends (Last 30 Days)',
            xaxis: { title: 'Date' },
            yaxis: { title: 'Score (%)' },
            showlegend: true
        };
        
        Plotly.newPlot('trends-chart', [trendsTrace], trendsLayout);
        {% endif %}
    </script>
</body>
</html>
        '''
    
    def generate_comprehensive_report(self, test_results: Dict[str, Any], 
                                     quality_gate_results: Dict[str, Any],
                                     metrics: Dict[str, Any],
                                     trends: Dict[str, Any] = None) -> TestReport:
        """Generate comprehensive test report"""
        timestamp = datetime.now()
        
        # Calculate summary metrics
        summary = self._calculate_summary(test_results, quality_gate_results, metrics)
        
        # Process test suites
        test_suites = self._process_test_suites(test_results)
        
        # Process quality gates
        quality_gates = self._process_quality_gates(quality_gate_results)
        
        # Process performance metrics
        performance_metrics = self._process_performance_metrics(metrics)
        
        # Process coverage data
        coverage_data = self._process_coverage_data(metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(summary, test_suites, quality_gates)
        
        # Create report
        report = TestReport(
            timestamp=timestamp,
            title=self.config.title,
            summary=summary,
            test_suites=test_suites,
            quality_gates=quality_gates,
            performance_metrics=performance_metrics,
            security_findings={},  # TODO: Implement security findings processing
            coverage_data=coverage_data,
            recommendations=recommendations,
            trends=trends or {}
        )
        
        # Store in history
        self.report_history.append(report)
        
        # Keep only last 100 reports
        if len(self.report_history) > 100:
            self.report_history = self.report_history[-100:]
        
        return report
    
    def _calculate_summary(self, test_results: Dict[str, Any], 
                           quality_gate_results: Dict[str, Any],
                           metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary metrics"""
        summary = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'skipped_tests': 0,
            'error_tests': 0,
            'success_rate': 0.0,
            'coverage': 0.0,
            'duration': 0.0,
            'quality_gates_passed': 0,
            'quality_gates_total': 0
        }
        
        # Aggregate test results
        for suite_name, suite_data in test_results.items():
            if isinstance(suite_data, dict):
                summary['total_tests'] += suite_data.get('total_tests', 0)
                summary['passed_tests'] += suite_data.get('passed_tests', 0)
                summary['failed_tests'] += suite_data.get('failed_tests', 0)
                summary['skipped_tests'] += suite_data.get('skipped_tests', 0)
                summary['error_tests'] += suite_data.get('error_tests', 0)
                summary['duration'] += suite_data.get('total_duration', 0.0)
        
        # Calculate success rate
        if summary['total_tests'] > 0:
            summary['success_rate'] = (summary['passed_tests'] / summary['total_tests']) * 100
        
        # Get coverage
        summary['coverage'] = metrics.get('coverage', 0.0)
        
        # Aggregate quality gates
        for gate_name, gate_result in quality_gate_results.items():
            summary['quality_gates_total'] += 1
            if gate_result.get('passed', False):
                summary['quality_gates_passed'] += 1
        
        # Add styling classes
        summary['success_rate_class'] = self._get_metric_class(summary['success_rate'])
        summary['total_tests_class'] = self._get_metric_class(summary['success_rate'])
        summary['coverage_class'] = self._get_metric_class(summary['coverage'])
        summary['duration_class'] = 'warning' if summary['duration'] > 300 else 'success'
        
        return summary
    
    def _get_metric_class(self, value: float) -> str:
        """Get CSS class for metric value"""
        if value >= 90:
            return 'success'
        elif value >= 70:
            return 'warning'
        else:
            return 'danger'
    
    def _process_test_suites(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process test suite data"""
        processed_suites = {}
        
        for suite_name, suite_data in test_results.items():
            if isinstance(suite_data, dict):
                total_tests = suite_data.get('total_tests', 0)
                passed_tests = suite_data.get('passed_tests', 0)
                
                processed_suites[suite_name] = {
                    'name': suite_data.get('name', suite_name),
                    'description': suite_data.get('description', ''),
                    'total': total_tests,
                    'passed': passed_tests,
                    'failed': suite_data.get('failed_tests', 0),
                    'skipped': suite_data.get('skipped_tests', 0),
                    'errors': suite_data.get('error_tests', 0),
                    'passed_percentage': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                    'coverage': suite_data.get('coverage', 0.0),
                    'duration': suite_data.get('total_duration', 0.0),
                    'status': 'passed' if passed_tests == total_tests and total_tests > 0 else 'failed'
                }
        
        return processed_suites
    
    def _process_quality_gates(self, quality_gate_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process quality gate results"""
        processed_gates = {}
        
        for gate_name, gate_result in quality_gate_results.items():
            if isinstance(gate_result, dict):
                processed_gates[gate_name] = {
                    'status': 'passed' if gate_result.get('passed', False) else 'failed',
                    'score': gate_result.get('score', 0.0),
                    'passed_conditions': gate_result.get('passed_conditions', []),
                    'failed_conditions': gate_result.get('failed_conditions', []),
                    'skipped_conditions': gate_result.get('skipped_conditions', []),
                    'error_conditions': gate_result.get('error_conditions', [])
                }
        
        return processed_gates
    
    def _process_performance_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Process performance metrics for visualization"""
        performance_metrics = {
            'chart_data': [
                {'metric': 'API Response Time', 'value': metrics.get('api_response_time_p95', 0)},
                {'metric': 'Database Query Time', 'value': metrics.get('db_query_time_avg', 0)},
                {'metric': 'Memory Usage', 'value': metrics.get('memory_usage', 0)},
                {'metric': 'CPU Usage', 'value': metrics.get('cpu_usage', 0)}
            ]
        }
        
        return performance_metrics
    
    def _process_coverage_data(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Process coverage data for visualization"""
        coverage_data = {
            'chart_data': [
                {'module': 'Core', 'coverage': metrics.get('core_coverage', 0)},
                {'module': 'API', 'coverage': metrics.get('api_coverage', 0)},
                {'module': 'Models', 'coverage': metrics.get('models_coverage', 0)},
                {'module': 'Utils', 'coverage': metrics.get('utils_coverage', 0)}
            ]
        }
        
        return coverage_data
    
    def _generate_recommendations(self, summary: Dict[str, Any], 
                                  test_suites: Dict[str, Any],
                                  quality_gates: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # Test coverage recommendations
        if summary['coverage'] < 80:
            recommendations.append(
                f"Improve code coverage from {summary['coverage']:.1f}% to at least 80%"
            )
        
        # Success rate recommendations
        if summary['success_rate'] < 95:
            recommendations.append(
                f"Address test failures to improve success rate from {summary['success_rate']:.1f}% to at least 95%"
            )
        
        # Test suite specific recommendations
        for suite_name, suite_data in test_suites.items():
            if suite_data['passed_percentage'] < 90:
                recommendations.append(
                    f"Fix failing tests in {suite_data['name']} suite (current: {suite_data['passed_percentage']:.1f}% pass rate)"
                )
        
        # Quality gate recommendations
        for gate_name, gate_data in quality_gates.items():
            if gate_data['status'] == 'failed':
                recommendations.append(
                    f"Address quality gate failures in {gate_name}"
                )
        
        # Performance recommendations
        if summary['duration'] > 300:  # 5 minutes
            recommendations.append(
                "Optimize test execution time to reduce feedback delay"
            )
        
        # Add general recommendations if none specific
        if not recommendations:
            recommendations.extend([
                "Consider adding more edge case tests to improve robustness",
                "Implement automated security scanning in CI/CD pipeline",
                "Set up performance regression testing"
            ])
        
        return recommendations
    
    def export_report(self, report: TestReport, formats: List[str] = None) -> List[str]:
        """Export report in specified formats"""
        if formats is None:
            formats = self.config.output_formats
        
        output_files = []
        timestamp = report.timestamp.strftime('%Y%m%d_%H%M%S')
        
        for format_type in formats:
            if format_type == 'html':
                html_file = self._export_html_report(report, timestamp)
                output_files.append(html_file)
            elif format_type == 'json':
                json_file = self._export_json_report(report, timestamp)
                output_files.append(json_file)
            elif format_type == 'pdf':
                pdf_file = self._export_pdf_report(report, timestamp)
                output_files.append(pdf_file)
            elif format_type == 'xml':
                xml_file = self._export_xml_report(report, timestamp)
                output_files.append(xml_file)
        
        return output_files
    
    def _export_html_report(self, report: TestReport, timestamp: str) -> str:
        """Export HTML report"""
        template = Template(self.templates['html'])
        
        html_content = template.render(
            title=report.title,
            timestamp=report.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            overall_status='passed' if all(gate['status'] == 'passed' for gate in report.quality_gates.values()) else 'failed',
            summary=report.summary,
            test_suites=report.test_suites,
            quality_gates=report.quality_gates,
            performance_metrics=report.performance_metrics,
            coverage_data=report.coverage_data,
            trends=report.trends,
            include_trends=self.config.include_trends,
            include_recommendations=self.config.include_recommendations,
            recommendations=report.recommendations,
            report_id=f"report_{timestamp}"
        )
        
        output_file = Path(self.config.output_dir) / f"test_report_{timestamp}.html"
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"HTML report exported: {output_file}")
        return str(output_file)
    
    def _export_json_report(self, report: TestReport, timestamp: str) -> str:
        """Export JSON report"""
        report_data = {
            'timestamp': report.timestamp.isoformat(),
            'title': report.title,
            'summary': report.summary,
            'test_suites': report.test_suites,
            'quality_gates': report.quality_gates,
            'performance_metrics': report.performance_metrics,
            'security_findings': report.security_findings,
            'coverage_data': report.coverage_data,
            'recommendations': report.recommendations,
            'trends': report.trends,
            'artifacts': report.artifacts
        }
        
        output_file = Path(self.config.output_dir) / f"test_report_{timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"JSON report exported: {output_file}")
        return str(output_file)
    
    def _export_pdf_report(self, report: TestReport, timestamp: str) -> str:
        """Export PDF report (placeholder)"""
        # In a real implementation, this would use a PDF library like WeasyPrint
        output_file = Path(self.config.output_dir) / f"test_report_{timestamp}.pdf"
        
        # Create a simple text-based PDF placeholder
        content = f"""
        {report.title}
        Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        
        SUMMARY
        =======
        Total Tests: {report.summary.get('total_tests', 0)}
        Success Rate: {report.summary.get('success_rate', 0):.1f}%
        Code Coverage: {report.summary.get('coverage', 0):.1f}%
        Duration: {report.summary.get('duration', 0):.1f}s
        
        TEST SUITES
        ===========
        """
        
        for suite_name, suite_data in report.test_suites.items():
            content += f"\n{suite_name}: {suite_data.get('passed', 0)}/{suite_data.get('total', 0)} passed"
        
        content += f"\n\nRECOMMENDATIONS\n================\n"
        for rec in report.recommendations:
            content += f"- {rec}\n"
        
        with open(output_file.with_suffix('.txt'), 'w') as f:
            f.write(content)
        
        logger.info(f"PDF report (text placeholder) exported: {output_file}")
        return str(output_file)
    
    def _export_xml_report(self, report: TestReport, timestamp: str) -> str:
        """Export XML report"""
        import xml.etree.ElementTree as ET
        
        root = ET.Element('test_report')
        root.set('timestamp', report.timestamp.isoformat())
        root.set('title', report.title)
        
        # Summary
        summary_elem = ET.SubElement(root, 'summary')
        for key, value in report.summary.items():
            elem = ET.SubElement(summary_elem, key)
            elem.text = str(value)
        
        # Test suites
        test_suites_elem = ET.SubElement(root, 'test_suites')
        for suite_name, suite_data in report.test_suites.items():
            suite_elem = ET.SubElement(test_suites_elem, 'suite')
            suite_elem.set('name', suite_name)
            for key, value in suite_data.items():
                elem = ET.SubElement(suite_elem, key)
                elem.text = str(value)
        
        # Quality gates
        quality_gates_elem = ET.SubElement(root, 'quality_gates')
        for gate_name, gate_data in report.quality_gates.items():
            gate_elem = ET.SubElement(quality_gates_elem, 'gate')
            gate_elem.set('name', gate_name)
            for key, value in gate_data.items():
                elem = ET.SubElement(gate_elem, key)
                if isinstance(value, list):
                    for item in value:
                    item_elem = ET.SubElement(elem, 'item')
                    item_elem.text = str(item)
                else:
                    elem.text = str(value)
        
        # Recommendations
        recommendations_elem = ET.SubElement(root, 'recommendations')
        for rec in report.recommendations:
            rec_elem = ET.SubElement(recommendations_elem, 'recommendation')
            rec_elem.text = rec
        
        output_file = Path(self.config.output_dir) / f"test_report_{timestamp}.xml"
        tree = ET.ElementTree(root)
        tree.write(output_file, encoding='utf-8', xml_declaration=True)
        
        logger.info(f"XML report exported: {output_file}")
        return str(output_file)
    
    def generate_trend_analysis(self, days: int = 30) -> Dict[str, Any]:
        """Generate trend analysis from historical reports"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_reports = [
            report for report in self.report_history
            if report.timestamp >= cutoff_date
        ]
        
        if not recent_reports:
            return {}
        
        # Calculate trends
        trends = {
            'dates': [r.timestamp.strftime('%Y-%m-%d') for r in recent_reports],
            'success_rates': [r.summary.get('success_rate', 0) for r in recent_reports],
            'coverage_rates': [r.summary.get('coverage', 0) for r in recent_reports],
            'durations': [r.summary.get('duration', 0) for r in recent_reports],
            'quality_scores': [
                sum(gate.get('score', 0) for gate in r.quality_gates.values()) / len(r.quality_gates)
                if r.quality_gates else 0
                for r in recent_reports
            ]
        }
        
        # Calculate trend statistics
        trends['statistics'] = {
            'avg_success_rate': np.mean(trends['success_rates']),
            'avg_coverage': np.mean(trends['coverage_rates']),
            'avg_duration': np.mean(trends['durations']),
            'avg_quality_score': np.mean(trends['quality_scores']),
            'success_rate_trend': self._calculate_trend(trends['success_rates']),
            'coverage_trend': self._calculate_trend(trends['coverage_rates']),
            'quality_score_trend': self._calculate_trend(trends['quality_scores'])
        }
        
        return trends
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction"""
        if len(values) < 2:
            return 'stable'
        
        # Simple linear regression to determine trend
        x = list(range(len(values)))
        y = values
        
        n = len(values)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        
        # Calculate slope
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        if slope > 0.5:
            return 'improving'
        elif slope < -0.5:
            return 'declining'
        else:
            return 'stable'
    
    def get_report_summary(self, report_id: str = None) -> Optional[Dict[str, Any]]:
        """Get summary of a specific report"""
        if report_id:
            for report in self.report_history:
                if f"report_{report.timestamp.strftime('%Y%m%d_%H%M%S')}" == report_id:
                    return {
                        'id': report_id,
                        'timestamp': report.timestamp.isoformat(),
                        'title': report.title,
                        'summary': report.summary,
                        'overall_status': 'passed' if all(gate['status'] == 'passed' for gate in report.quality_gates.values()) else 'failed'
                    }
        else:
            # Return latest report summary
            if self.report_history:
                latest = self.report_history[-1]
                return {
                    'id': f"report_{latest.timestamp.strftime('%Y%m%d_%H%M%S')}",
                    'timestamp': latest.timestamp.isoformat(),
                    'title': latest.title,
                    'summary': latest.summary,
                    'overall_status': 'passed' if all(gate['status'] == 'passed' for gate in latest.quality_gates.values()) else 'failed'
                }
        
        return None


# Global reporting engine instance
reporting_engine = None


def initialize_reporting(config: ReportConfig) -> TestReportingEngine:
    """Initialize global reporting engine"""
    global reporting_engine
    reporting_engine = TestReportingEngine(config)
    return reporting_engine


def get_reporting_engine() -> Optional[TestReportingEngine]:
    """Get global reporting engine instance"""
    return reporting_engine
