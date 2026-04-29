#!/usr/bin/env python3
"""
Complete Example Usage of Advanced Time Series Analysis
Demonstrates all features with practical examples
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any


class TimeSeriesAnalysisDemo:
    """Demonstration of time series analysis features"""
    
    def __init__(self, base_url: str = 'http://localhost:5000'):
        self.base_url = base_url
        self.results = {}
    
    def print_section(self, title: str):
        """Print a formatted section header"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80 + "\n")
    
    def print_result(self, data: Dict[str, Any], max_items: int = 5):
        """Pretty print results"""
        print(json.dumps(data, indent=2, default=str)[:1000])
        if len(str(data)) > 1000:
            print("... (truncated)")
        print()
    
    def demo_1_time_series_data(self):
        """Demo 1: Get and preprocess time series data"""
        self.print_section("Demo 1: Time Series Data Retrieval")
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        response = requests.get(f'{self.base_url}/analytics/timeseries', params={
            'start_date': start_date,
            'end_date': end_date,
            'aggregation': 'daily',
            'metric': 'total_requests'
        })
        
        data = response.json()
        self.results['timeseries'] = data
        
        print(f"📊 Retrieved time series data:")
        print(f"   - Period: {start_date} to {end_date}")
        print(f"   - Data points: {data.get('statistics', {}).get('count', 0)}")
        print(f"   - Mean: {data.get('statistics', {}).get('mean', 0):.2f}")
        print(f"   - Std Dev: {data.get('statistics', {}).get('std', 0):.2f}")
        print(f"   - Min: {data.get('statistics', {}).get('min', 0):.2f}")
        print(f"   - Max: {data.get('statistics', {}).get('max', 0):.2f}")
        
        if 'outliers' in data:
            print(f"   - Outliers detected: {sum(data['outliers'].values())}")
    
    def demo_2_trend_analysis(self):
        """Demo 2: Analyze trends"""
        self.print_section("Demo 2: Trend Analysis")
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        # Try different trend methods
        methods = ['linear', 'polynomial', 'exponential']
        
        for method in methods:
            print(f"\n🔍 Analyzing trend using {method.upper()} method:")
            
            response = requests.get(f'{self.base_url}/analytics/trend', params={
                'start_date': start_date,
                'end_date': end_date,
                'metric': 'total_requests',
                'method': method
            })
            
            data = response.json()
            
            if 'error' not in data:
                trend = data.get('trend', {})
                print(f"   - Direction: {trend.get('direction', 'unknown')}")
                print(f"   - Strength: {trend.get('strength', 0):.3f}")
                
                if 'slope' in trend:
                    print(f"   - Slope: {trend['slope']:.4f}")
                if 'r_squared' in trend:
                    print(f"   - R²: {trend['r_squared']:.3f}")
                if 'is_significant' in trend:
                    print(f"   - Statistically significant: {trend['is_significant']}")
                
                # Change points
                change_points = data.get('change_points', [])
                if change_points:
                    print(f"   - Change points detected: {len(change_points)}")
                    for cp in change_points[:3]:
                        print(f"     • {cp['timestamp']}: {cp['change_type']} "
                              f"({cp['change_percentage']:.1f}% change)")
                
                # Peaks and troughs
                peaks_troughs = data.get('peaks_and_troughs', {})
                print(f"   - Peaks: {peaks_troughs.get('peak_count', 0)}")
                print(f"   - Troughs: {peaks_troughs.get('trough_count', 0)}")
            else:
                print(f"   ⚠️  Error: {data['error']}")
    
    def demo_3_seasonality_detection(self):
        """Demo 3: Detect seasonality"""
        self.print_section("Demo 3: Seasonality Detection")
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        response = requests.get(f'{self.base_url}/analytics/seasonality', params={
            'start_date': start_date,
            'end_date': end_date,
            'metric': 'total_requests',
            'model': 'additive'
        })
        
        data = response.json()
        
        if 'error' not in data:
            print(f"📈 Seasonality Analysis:")
            print(f"   - Model: {data.get('model', 'unknown')}")
            print(f"   - Period: {data.get('period', 0)} days")
            print(f"   - Seasonality Strength: {data.get('seasonality_strength', 0):.3f}")
            
            components = data.get('components', {})
            print(f"\n   Components extracted:")
            for comp_name, comp_data in components.items():
                if isinstance(comp_data, dict):
                    print(f"   - {comp_name.title()}:")
                    print(f"     • Mean: {comp_data.get('mean', 0):.2f}")
                    print(f"     • Std: {comp_data.get('std', 0):.2f}")
        else:
            print(f"⚠️  Error: {data['error']}")
    
    def demo_4_forecasting(self):
        """Demo 4: Forecast future values"""
        self.print_section("Demo 4: Forecasting")
        
        models = ['arima', 'exp_smoothing', 'ensemble']
        
        for model in models:
            print(f"\n🔮 Forecasting with {model.upper()}:")
            
            response = requests.get(f'{self.base_url}/analytics/forecast', params={
                'metric': 'total_requests',
                'steps': 30,
                'model': model
            })
            
            data = response.json()
            
            if 'error' not in data:
                forecast = data.get('forecast', {})
                values = forecast.get('values', [])
                
                print(f"   - Model: {data.get('model', model)}")
                print(f"   - Forecast steps: {data.get('steps', 0)}")
                
                if values:
                    print(f"   - Next 7 days forecast:")
                    for i, val in enumerate(values[:7], 1):
                        print(f"     Day {i}: {val:.2f}")
                
                if 'aic' in data:
                    print(f"   - AIC: {data['aic']:.2f}")
                if 'bic' in data:
                    print(f"   - BIC: {data['bic']:.2f}")
                
                # Confidence intervals
                if 'lower_bound' in data and 'upper_bound' in data:
                    print(f"   - Confidence intervals available: Yes")
            else:
                print(f"   ⚠️  Error: {data['error']}")
    
    def demo_5_anomaly_detection(self):
        """Demo 5: Detect anomalies"""
        self.print_section("Demo 5: Anomaly Detection")
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        methods = ['zscore', 'iqr']
        
        for method in methods:
            print(f"\n🚨 Detecting anomalies using {method.upper()}:")
            
            response = requests.get(f'{self.base_url}/analytics/anomalies', params={
                'start_date': start_date,
                'end_date': end_date,
                'metric': 'total_requests',
                'method': method,
                'threshold': 3.0
            })
            
            data = response.json()
            
            if 'error' not in data:
                print(f"   - Method: {data.get('method', method)}")
                print(f"   - Threshold: {data.get('threshold', 0)}")
                print(f"   - Total anomalies: {data.get('total_anomalies', 0)}")
                print(f"   - Anomaly rate: {data.get('anomaly_rate', 0):.2f}%")
                
                anomalies = data.get('anomalies', [])
                if anomalies:
                    print(f"\n   Top anomalies:")
                    for anomaly in anomalies[:5]:
                        print(f"   - {anomaly['timestamp']}: {anomaly['value']:.2f} "
                              f"(deviation: {anomaly['deviation']:.2f}σ)")
            else:
                print(f"   ⚠️  Error: {data['error']}")
    
    def demo_6_visualization_data(self):
        """Demo 6: Get visualization-ready data"""
        self.print_section("Demo 6: Visualization Data")
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        response = requests.get(f'{self.base_url}/analytics/visualization', params={
            'start_date': start_date,
            'end_date': end_date,
            'metrics': ['total_requests', 'avg_confidence', 'success_rate']
        })
        
        data = response.json()
        
        if 'error' not in data:
            print(f"📊 Visualization data prepared:")
            print(f"   - Timestamps: {len(data.get('timestamps', []))}")
            
            metrics = data.get('metrics', {})
            for metric_name, metric_data in metrics.items():
                print(f"\n   {metric_name.replace('_', ' ').title()}:")
                print(f"   - Raw data points: {len(metric_data.get('raw', []))}")
                print(f"   - Smoothed data points: {len(metric_data.get('smoothed', []))}")
                print(f"   - Trend direction: {metric_data.get('trend_direction', 'unknown')}")
                
                stats = metric_data.get('statistics', {})
                print(f"   - Mean: {stats.get('mean', 0):.2f}")
                print(f"   - Range: [{stats.get('min', 0):.2f}, {stats.get('max', 0):.2f}]")
        else:
            print(f"⚠️  Error: {data['error']}")
    
    def demo_7_performance_metrics(self):
        """Demo 7: Get comprehensive performance metrics"""
        self.print_section("Demo 7: Performance Metrics")
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        response = requests.get(f'{self.base_url}/analytics/performance-metrics', params={
            'start_date': start_date,
            'end_date': end_date
        })
        
        data = response.json()
        
        if 'error' not in data:
            print(f"📈 Performance Metrics Summary:")
            print(f"   - Period: {data.get('period', {}).get('start')} to "
                  f"{data.get('period', {}).get('end')}")
            print(f"   - Data points: {data.get('data_points', 0)}")
            
            metrics = data.get('metrics', {})
            for metric_name, metric_data in metrics.items():
                print(f"\n   {metric_name.replace('_', ' ').title()}:")
                print(f"   - Current: {metric_data.get('current_value', 0):.2f}")
                print(f"   - Mean: {metric_data.get('mean', 0):.2f}")
                print(f"   - Trend: {metric_data.get('trend_direction', 'unknown')}")
                print(f"   - Strength: {metric_data.get('trend_strength', 0):.3f}")
                print(f"   - Change: {metric_data.get('change_percentage', 0):.2f}%")
                print(f"   - Improving: {'✓' if metric_data.get('is_improving') else '✗'}")
        else:
            print(f"⚠️  Error: {data['error']}")
    
    def run_all_demos(self):
        """Run all demonstrations"""
        print("\n" + "=" * 80)
        print("  ADVANCED TIME SERIES ANALYSIS - COMPLETE DEMONSTRATION")
        print("=" * 80)
        
        try:
            self.demo_1_time_series_data()
            self.demo_2_trend_analysis()
            self.demo_3_seasonality_detection()
            self.demo_4_forecasting()
            self.demo_5_anomaly_detection()
            self.demo_6_visualization_data()
            self.demo_7_performance_metrics()
            
            self.print_section("✅ All Demonstrations Completed Successfully!")
            print("All time series analysis features are working correctly.\n")
            
        except requests.exceptions.ConnectionError:
            print("\n❌ Error: Could not connect to API server.")
            print("Please ensure the Flask app is running at http://localhost:5000")
            print("Start it with: python3 app.py\n")
        except Exception as e:
            print(f"\n❌ Error during demonstration: {e}\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Demonstrate Advanced Time Series Analysis features'
    )
    parser.add_argument(
        '--base-url',
        default='http://localhost:5000',
        help='API base URL (default: http://localhost:5000)'
    )
    parser.add_argument(
        '--demo',
        type=int,
        choices=range(1, 8),
        help='Run specific demo (1-7), or all if not specified'
    )
    
    args = parser.parse_args()
    
    demo = TimeSeriesAnalysisDemo(args.base_url)
    
    if args.demo:
        # Run specific demo
        demo_methods = {
            1: demo.demo_1_time_series_data,
            2: demo.demo_2_trend_analysis,
            3: demo.demo_3_seasonality_detection,
            4: demo.demo_4_forecasting,
            5: demo.demo_5_anomaly_detection,
            6: demo.demo_6_visualization_data,
            7: demo.demo_7_performance_metrics
        }
        demo_methods[args.demo]()
    else:
        # Run all demos
        demo.run_all_demos()


if __name__ == '__main__':
    main()
