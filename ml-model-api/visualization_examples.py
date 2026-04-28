"""
Visualization Examples for Time Series Analysis
Demonstrates how to create visualizations using the time series analysis API
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import json


class TimeSeriesVisualizer:
    """Helper class for creating time series visualizations"""
    
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url
    
    def plot_time_series_with_trend(self, metric='total_requests', 
                                   start_date=None, end_date=None,
                                   save_path=None):
        """
        Plot time series data with trend line
        
        Args:
            metric: Metric to plot
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            save_path: Path to save figure (optional)
        """
        # Fetch data
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'metric': metric
        }
        
        # Get time series data
        ts_response = requests.get(f'{self.base_url}/analytics/timeseries', params=params)
        ts_data = ts_response.json()
        
        # Get trend analysis
        trend_response = requests.get(f'{self.base_url}/analytics/trend', params=params)
        trend_data = trend_response.json()
        
        if 'error' in ts_data or 'error' in trend_data:
            print(f"Error fetching data: {ts_data.get('error', trend_data.get('error'))}")
            return
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # Parse timestamps
        timestamps = [datetime.fromisoformat(ts) for ts in ts_data['timestamps']]
        values = list(ts_data['data'].values())
        
        # Plot raw data
        ax.plot(timestamps, values, 'o-', label='Actual', alpha=0.6, markersize=3)
        
        # Plot trend line if available
        if 'trend' in trend_data and 'trend_line' in trend_data['trend']:
            trend_line = trend_data['trend']['trend_line']
            if 'values' in trend_line:
                trend_timestamps = [datetime.fromisoformat(ts) for ts in trend_line['timestamps']]
                ax.plot(trend_timestamps, trend_line['values'], 'r--', 
                       label=f"Trend ({trend_data['trend']['direction']})", linewidth=2)
        
        # Formatting
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel(metric.replace('_', ' ').title(), fontsize=12)
        ax.set_title(f'Time Series Analysis: {metric.replace("_", " ").title()}', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved to {save_path}")
        else:
            plt.show()
    
    def plot_seasonality_decomposition(self, metric='total_requests',
                                      start_date=None, end_date=None,
                                      save_path=None):
        """
        Plot seasonal decomposition components
        
        Args:
            metric: Metric to analyze
            start_date: Start date
            end_date: End date
            save_path: Path to save figure
        """
        # Fetch seasonality data
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'metric': metric,
            'model': 'additive'
        }
        
        response = requests.get(f'{self.base_url}/analytics/seasonality', params=params)
        data = response.json()
        
        if 'error' in data:
            print(f"Error: {data['error']}")
            return
        
        # Create subplots
        fig, axes = plt.subplots(4, 1, figsize=(14, 10))
        
        components = data['components']
        
        # Plot each component
        for idx, (comp_name, comp_data) in enumerate(components.items()):
            if idx >= 4:
                break
            
            timestamps = [datetime.fromisoformat(ts) for ts in comp_data['timestamps']]
            values = comp_data['values']
            
            axes[idx].plot(timestamps, values, linewidth=1.5)
            axes[idx].set_ylabel(comp_name.title(), fontsize=11)
            axes[idx].grid(True, alpha=0.3)
            
            if idx == 0:
                axes[idx].set_title(f'Seasonal Decomposition: {metric.replace("_", " ").title()}',
                                  fontsize=14, fontweight='bold')
            
            if idx < 3:
                axes[idx].set_xticklabels([])
            else:
                axes[idx].set_xlabel('Date', fontsize=11)
                axes[idx].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                plt.setp(axes[idx].xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved to {save_path}")
        else:
            plt.show()
    
    def plot_forecast_with_confidence(self, metric='total_requests',
                                     steps=30, model='ensemble',
                                     save_path=None):
        """
        Plot forecast with confidence intervals
        
        Args:
            metric: Metric to forecast
            steps: Number of steps to forecast
            model: Forecasting model
            save_path: Path to save figure
        """
        # Fetch forecast
        params = {
            'metric': metric,
            'steps': steps,
            'model': model
        }
        
        response = requests.get(f'{self.base_url}/analytics/forecast', params=params)
        data = response.json()
        
        if 'error' in data:
            print(f"Error: {data['error']}")
            return
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # Plot historical data
        if 'historical' in data:
            hist_timestamps = [datetime.fromisoformat(ts) for ts in data['historical']['timestamps']]
            hist_values = data['historical']['values']
            ax.plot(hist_timestamps, hist_values, 'o-', label='Historical', 
                   alpha=0.6, markersize=3, color='blue')
        
        # Plot forecast
        forecast_timestamps = [datetime.fromisoformat(ts) for ts in data['forecast']['timestamps']]
        forecast_values = data['forecast']['values']
        ax.plot(forecast_timestamps, forecast_values, 'o-', label='Forecast',
               markersize=4, color='red', linewidth=2)
        
        # Plot confidence intervals if available
        if 'lower_bound' in data and 'upper_bound' in data:
            lower_values = data['lower_bound']['values']
            upper_values = data['upper_bound']['values']
            ax.fill_between(forecast_timestamps, lower_values, upper_values,
                           alpha=0.2, color='red', label='95% Confidence Interval')
        
        # Formatting
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel(metric.replace('_', ' ').title(), fontsize=12)
        ax.set_title(f'Forecast: {metric.replace("_", " ").title()} ({model.upper()})',
                    fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved to {save_path}")
        else:
            plt.show()
    
    def plot_anomalies(self, metric='total_requests',
                      start_date=None, end_date=None,
                      method='zscore', threshold=3.0,
                      save_path=None):
        """
        Plot time series with anomalies highlighted
        
        Args:
            metric: Metric to analyze
            start_date: Start date
            end_date: End date
            method: Anomaly detection method
            threshold: Detection threshold
            save_path: Path to save figure
        """
        # Fetch time series data
        ts_params = {
            'start_date': start_date,
            'end_date': end_date,
            'metric': metric
        }
        ts_response = requests.get(f'{self.base_url}/analytics/timeseries', params=ts_params)
        ts_data = ts_response.json()
        
        # Fetch anomalies
        anomaly_params = {
            'start_date': start_date,
            'end_date': end_date,
            'metric': metric,
            'method': method,
            'threshold': threshold
        }
        anomaly_response = requests.get(f'{self.base_url}/analytics/anomalies', params=anomaly_params)
        anomaly_data = anomaly_response.json()
        
        if 'error' in ts_data or 'error' in anomaly_data:
            print(f"Error fetching data")
            return
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # Plot time series
        timestamps = [datetime.fromisoformat(ts) for ts in ts_data['timestamps']]
        values = list(ts_data['data'].values())
        ax.plot(timestamps, values, 'o-', label='Normal', alpha=0.6, markersize=3)
        
        # Highlight anomalies
        if anomaly_data['total_anomalies'] > 0:
            anomaly_timestamps = [datetime.fromisoformat(a['timestamp']) 
                                 for a in anomaly_data['anomalies']]
            anomaly_values = [a['value'] for a in anomaly_data['anomalies']]
            ax.scatter(anomaly_timestamps, anomaly_values, color='red', s=100,
                      marker='X', label='Anomalies', zorder=5)
        
        # Add mean and std bands
        mean = ts_data['statistics']['mean']
        std = ts_data['statistics']['std']
        ax.axhline(y=mean, color='green', linestyle='--', alpha=0.5, label='Mean')
        ax.axhline(y=mean + threshold * std, color='orange', linestyle=':', alpha=0.5)
        ax.axhline(y=mean - threshold * std, color='orange', linestyle=':', alpha=0.5,
                  label=f'±{threshold}σ')
        
        # Formatting
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel(metric.replace('_', ' ').title(), fontsize=12)
        ax.set_title(f'Anomaly Detection: {metric.replace("_", " ").title()} '
                    f'({anomaly_data["total_anomalies"]} anomalies found)',
                    fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved to {save_path}")
        else:
            plt.show()
    
    def plot_multiple_metrics_comparison(self, metrics=None,
                                        start_date=None, end_date=None,
                                        save_path=None):
        """
        Plot multiple metrics for comparison
        
        Args:
            metrics: List of metrics to compare
            start_date: Start date
            end_date: End date
            save_path: Path to save figure
        """
        if metrics is None:
            metrics = ['total_requests', 'avg_confidence', 'success_rate']
        
        # Fetch visualization data
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'metrics': metrics
        }
        
        response = requests.get(f'{self.base_url}/analytics/visualization', params=params)
        data = response.json()
        
        if 'error' in data:
            print(f"Error: {data['error']}")
            return
        
        # Create subplots
        n_metrics = len(metrics)
        fig, axes = plt.subplots(n_metrics, 1, figsize=(14, 4 * n_metrics))
        
        if n_metrics == 1:
            axes = [axes]
        
        timestamps = [datetime.fromisoformat(ts) for ts in data['timestamps']]
        
        for idx, metric in enumerate(metrics):
            if metric not in data['metrics']:
                continue
            
            metric_data = data['metrics'][metric]
            
            # Plot raw and smoothed data
            axes[idx].plot(timestamps, metric_data['raw'], 'o-', 
                          label='Raw', alpha=0.4, markersize=2)
            axes[idx].plot(timestamps, metric_data['smoothed'], '-',
                          label='Smoothed (7-day MA)', linewidth=2)
            
            # Plot trend if available
            if metric_data['trend']:
                axes[idx].plot(timestamps, metric_data['trend'], '--',
                             label=f"Trend ({metric_data['trend_direction']})",
                             linewidth=2, color='red')
            
            # Formatting
            axes[idx].set_ylabel(metric.replace('_', ' ').title(), fontsize=11)
            axes[idx].legend(loc='upper left')
            axes[idx].grid(True, alpha=0.3)
            
            if idx == 0:
                axes[idx].set_title('Multi-Metric Comparison', fontsize=14, fontweight='bold')
            
            if idx < n_metrics - 1:
                axes[idx].set_xticklabels([])
            else:
                axes[idx].set_xlabel('Date', fontsize=11)
                axes[idx].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                plt.setp(axes[idx].xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved to {save_path}")
        else:
            plt.show()


def create_dashboard(base_url='http://localhost:5000', output_dir='./visualizations'):
    """
    Create a complete dashboard with all visualizations
    
    Args:
        base_url: API base URL
        output_dir: Directory to save visualizations
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    visualizer = TimeSeriesVisualizer(base_url)
    
    # Calculate date range (last 90 days)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    print("Creating Time Series Dashboard...")
    
    # 1. Time series with trend
    print("1. Generating time series with trend...")
    visualizer.plot_time_series_with_trend(
        metric='total_requests',
        start_date=start_date,
        end_date=end_date,
        save_path=f'{output_dir}/01_timeseries_trend.png'
    )
    
    # 2. Seasonal decomposition
    print("2. Generating seasonal decomposition...")
    visualizer.plot_seasonality_decomposition(
        metric='total_requests',
        start_date=start_date,
        end_date=end_date,
        save_path=f'{output_dir}/02_seasonality.png'
    )
    
    # 3. Forecast
    print("3. Generating forecast...")
    visualizer.plot_forecast_with_confidence(
        metric='total_requests',
        steps=30,
        model='ensemble',
        save_path=f'{output_dir}/03_forecast.png'
    )
    
    # 4. Anomaly detection
    print("4. Generating anomaly detection...")
    visualizer.plot_anomalies(
        metric='total_requests',
        start_date=start_date,
        end_date=end_date,
        save_path=f'{output_dir}/04_anomalies.png'
    )
    
    # 5. Multi-metric comparison
    print("5. Generating multi-metric comparison...")
    visualizer.plot_multiple_metrics_comparison(
        metrics=['total_requests', 'avg_confidence', 'success_rate'],
        start_date=start_date,
        end_date=end_date,
        save_path=f'{output_dir}/05_multi_metric.png'
    )
    
    print(f"\nDashboard created successfully! Visualizations saved to {output_dir}/")


if __name__ == '__main__':
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate time series visualizations')
    parser.add_argument('--base-url', default='http://localhost:5000',
                       help='API base URL')
    parser.add_argument('--output-dir', default='./visualizations',
                       help='Output directory for visualizations')
    parser.add_argument('--dashboard', action='store_true',
                       help='Create complete dashboard')
    
    args = parser.parse_args()
    
    if args.dashboard:
        create_dashboard(args.base_url, args.output_dir)
    else:
        # Create individual visualization
        visualizer = TimeSeriesVisualizer(args.base_url)
        visualizer.plot_time_series_with_trend()
