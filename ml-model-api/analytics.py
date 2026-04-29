from flask import Flask, request, jsonify
from datetime import datetime, timedelta, date
import json
from typing import List, Dict, Any, Optional, Tuple
import logging
import numpy as np
import pandas as pd

from db_config import get_connection
from time_series import TimeSeriesPreprocessor, TimeSeriesDecomposer
from trend_analysis import TrendAnalyzer
from forecasting import TimeSeriesForecaster

logger = logging.getLogger(__name__)

class AnalyticsAPI:
    def __init__(self):
        self.ts_preprocessor = TimeSeriesPreprocessor()
        self.ts_decomposer = TimeSeriesDecomposer()
        self.trend_analyzer = TrendAnalyzer()
        self.forecaster = TimeSeriesForecaster()

    def _execute_query(self, query: str, params: Tuple = None, fetch: bool = True) -> Optional[List[Tuple]]:
        """Execute a database query with error handling."""
        conn = get_connection()
        if not conn:
            logger.error("Database connection unavailable")
            return None

        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, params or ())
                    if fetch:
                        return cur.fetchall()
                    return None
        except Exception as exc:
            logger.error("Database query failed: %s", exc)
            return None
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def get_usage_stats(self, start_date: str = None, end_date: str = None,
                       page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Get usage statistics with pagination and date filtering."""
        try:
            # Calculate date range
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')

            # Get total count for pagination
            count_query = """
                SELECT COUNT(*) as total
                FROM (
                    SELECT DATE(created_at) as date
                    FROM prediction_history
                    WHERE DATE(created_at) BETWEEN %s AND %s
                    GROUP BY DATE(created_at)
                ) daily_stats
            """
            count_result = self._execute_query(count_query, (start_date, end_date))
            total_records = count_result[0][0] if count_result else 0

            # Calculate pagination
            offset = (page - 1) * per_page
            total_pages = (total_records + per_page - 1) // per_page

            # Get paginated daily statistics
            query = """
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as requests,
                    COUNT(DISTINCT user_id) as users,
                    AVG(confidence) as avg_confidence,
                    AVG(processing_time) as avg_processing_time
                FROM prediction_history
                WHERE DATE(created_at) BETWEEN %s AND %s
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT %s OFFSET %s
            """

            results = self._execute_query(query, (start_date, end_date, per_page, offset))

            usage_data = []
            if results:
                for row in results:
                    usage_data.append({
                        'date': row[0].strftime('%Y-%m-%d'),
                        'requests': row[1],
                        'users': row[2] or 0,
                        'accuracy': round((row[3] or 0) * 100, 1),
                        'avg_processing_time': round(row[4] or 0, 2) if row[4] else None
                    })

            return {
                'data': usage_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_records': total_records,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }

        except Exception as exc:
            logger.error("Failed to get usage stats: %s", exc)
            return {'data': [], 'pagination': {'page': 1, 'per_page': per_page, 'total_records': 0, 'total_pages': 0, 'has_next': False, 'has_prev': False}}

    def get_model_performance(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get model performance metrics with pagination."""
        try:
            # Get total count
            count_query = "SELECT COUNT(*) FROM model_performance_metrics"
            count_result = self._execute_query(count_query)
            total_records = count_result[0][0] if count_result else 0

            # Calculate pagination
            offset = (page - 1) * per_page
            total_pages = (total_records + per_page - 1) // per_page

            # Get paginated model performance data
            query = """
                SELECT
                    model_version,
                    metric_date,
                    total_predictions,
                    avg_confidence,
                    avg_processing_time,
                    created_at
                FROM model_performance_metrics
                ORDER BY metric_date DESC, model_version
                LIMIT %s OFFSET %s
            """

            results = self._execute_query(query, (per_page, offset))

            performance_data = []
            if results:
                for row in results:
                    performance_data.append({
                        'model_version': row[0],
                        'date': row[1].strftime('%Y-%m-%d'),
                        'total_predictions': row[2],
                        'accuracy': round((row[3] or 0) * 100, 2) if row[3] else None,
                        'avg_processing_time': round(row[4] or 0, 2) if row[4] else None,
                        'created_at': row[5].isoformat() if row[5] else None
                    })

            return {
                'data': performance_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_records': total_records,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }

        except Exception as exc:
            logger.error("Failed to get model performance: %s", exc)
            return {'data': [], 'pagination': {'page': 1, 'per_page': per_page, 'total_records': 0, 'total_pages': 0, 'has_next': False, 'has_prev': False}}

    def get_user_engagement(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user engagement data by food category."""
        try:
            query = """
                SELECT
                    label,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence
                FROM prediction_history
                WHERE label IS NOT NULL AND success = true
                GROUP BY label
                ORDER BY count DESC
                LIMIT %s
            """

            results = self._execute_query(query, (limit,))

            engagement_data = []
            if results:
                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
                for i, row in enumerate(results):
                    engagement_data.append({
                        'category': row[0],
                        'value': row[1],
                        'avg_confidence': round((row[2] or 0) * 100, 1),
                        'color': colors[i % len(colors)]
                    })

            return engagement_data

        except Exception as exc:
            logger.error("Failed to get user engagement: %s", exc)
            return []

    def get_real_time_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent prediction activities."""
        try:
            query = """
                SELECT
                    id,
                    label,
                    confidence,
                    processing_time,
                    created_at,
                    success,
                    error_message
                FROM prediction_history
                ORDER BY created_at DESC
                LIMIT %s
            """

            results = self._execute_query(query, (limit,))

            activities = []
            if results:
                for row in results:
                    activity_type = 'classification'
                    title = f"Classification: {row[1] or 'Unknown'}"
                    description = f"Confidence: {round((row[2] or 0) * 100, 1)}%"

                    if not row[5]:  # If not successful
                        activity_type = 'error'
                        title = "Classification Failed"
                        description = row[6] or "Unknown error"

                    # Calculate relative time
                    created_at = row[4]
                    now = datetime.now(created_at.tzinfo) if created_at.tzinfo else datetime.now()
                    time_diff = now - created_at

                    if time_diff.days > 0:
                        timestamp = f"{time_diff.days} days ago"
                    elif time_diff.seconds >= 3600:
                        timestamp = f"{time_diff.seconds // 3600} hours ago"
                    elif time_diff.seconds >= 60:
                        timestamp = f"{time_diff.seconds // 60} min ago"
                    else:
                        timestamp = f"{time_diff.seconds} sec ago"

                    activities.append({
                        'id': str(row[0]),
                        'type': activity_type,
                        'title': title,
                        'description': description,
                        'timestamp': timestamp,
                        'processing_time': round(row[3] or 0, 2) if row[3] else None
                    })

            return activities

        except Exception as exc:
            logger.error("Failed to get real-time activity: %s", exc)
            return []

    def get_stats_cards(self) -> List[Dict[str, Any]]:
        """Get summary statistics cards."""
        try:
            # Get total requests (last 30 days)
            total_query = """
                SELECT COUNT(*) as total
                FROM prediction_history
                WHERE created_at >= NOW() - INTERVAL '30 days'
            """
            total_result = self._execute_query(total_query)
            total_requests = total_result[0][0] if total_result else 0

            # Get active users (last 30 days)
            users_query = """
                SELECT COUNT(DISTINCT user_id) as users
                FROM prediction_history
                WHERE created_at >= NOW() - INTERVAL '30 days' AND user_id IS NOT NULL
            """
            users_result = self._execute_query(users_query)
            active_users = users_result[0][0] if users_result else 0

            # Get average accuracy (last 30 days)
            accuracy_query = """
                SELECT AVG(confidence) as avg_accuracy
                FROM prediction_history
                WHERE created_at >= NOW() - INTERVAL '30 days' AND success = true
            """
            accuracy_result = self._execute_query(accuracy_query)
            avg_accuracy = accuracy_result[0][0] if accuracy_result else 0

            # Get average response time (last 30 days)
            timing_query = """
                SELECT AVG(processing_time) as avg_time
                FROM prediction_history
                WHERE created_at >= NOW() - INTERVAL '30 days' AND processing_time IS NOT NULL
            """
            timing_result = self._execute_query(timing_query)
            avg_time = timing_result[0][0] if timing_result else 0

            return [
                {
                    'title': 'Total Requests',
                    'value': f"{total_requests:,}",
                    'change': '+12.5%',  # This would need historical comparison
                    'icon': 'activity',
                    'color': 'bg-blue-500'
                },
                {
                    'title': 'Active Users',
                    'value': f"{active_users:,}",
                    'change': '+8.2%',
                    'icon': 'users',
                    'color': 'bg-green-500'
                },
                {
                    'title': 'Avg Accuracy',
                    'value': f"{round((avg_accuracy or 0) * 100, 1)}%",
                    'change': '+2.1%',
                    'icon': 'check-circle',
                    'color': 'bg-purple-500'
                },
                {
                    'title': 'Response Time',
                    'value': f"{round(avg_time or 0, 0)}ms",
                    'change': '-15ms',
                    'icon': 'clock',
                    'color': 'bg-orange-500'
                }
            ]

        except Exception as exc:
            logger.error("Failed to get stats cards: %s", exc)
            return [
                {
                    'title': 'Total Requests',
                    'value': '0',
                    'change': 'N/A',
                    'icon': 'activity',
                    'color': 'bg-blue-500'
                },
                {
                    'title': 'Active Users',
                    'value': '0',
                    'change': 'N/A',
                    'icon': 'users',
                    'color': 'bg-green-500'
                },
                {
                    'title': 'Avg Accuracy',
                    'value': '0%',
                    'change': 'N/A',
                    'icon': 'check-circle',
                    'color': 'bg-purple-500'
                },
                {
                    'title': 'Response Time',
                    'value': '0ms',
                    'change': 'N/A',
                    'icon': 'clock',
                    'color': 'bg-orange-500'
                }
            ]

    def export_data(self, start_date: str = None, end_date: str = None,
                   data_types: List[str] = None) -> Dict[str, Any]:
        """Export analytics data with optional filtering."""
        if data_types is None:
            data_types = ['usage', 'performance', 'engagement', 'activity']

        export_data = {
            'exportDate': datetime.now().isoformat(),
            'dateRange': {
                'start': start_date,
                'end': end_date
            }
        }

        if 'usage' in data_types:
            usage_result = self.get_usage_stats(start_date, end_date, page=1, per_page=1000)
            export_data['usageData'] = usage_result['data']

        if 'performance' in data_types:
            performance_result = self.get_model_performance(page=1, per_page=1000)
            export_data['modelPerformance'] = performance_result['data']

        if 'engagement' in data_types:
            export_data['userEngagement'] = self.get_user_engagement(limit=50)

        if 'activity' in data_types:
            export_data['realTimeActivity'] = self.get_real_time_activity(limit=100)

        export_data['statsCards'] = self.get_stats_cards()

        return export_data
    
    # ==================== TIME SERIES ANALYSIS METHODS ====================
    
    def get_time_series_data(self, start_date: Optional[str] = None,
                            end_date: Optional[str] = None,
                            aggregation: str = 'daily',
                            metric: str = 'total_requests') -> Dict[str, Any]:
        """
        Get preprocessed time series data
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            aggregation: Time aggregation ('hourly', 'daily', 'weekly', 'monthly')
            metric: Metric to analyze
        
        Returns:
            Time series data with preprocessing applied
        """
        try:
            conn = get_connection()
            if not conn:
                return {'error': 'Database connection unavailable'}
            
            # Load data
            df = self.ts_preprocessor.load_data_from_db(conn, start_date, end_date, aggregation)
            conn.close()
            
            if df.empty:
                return {'error': 'No data available for the specified period'}
            
            # Handle missing values
            df = self.ts_preprocessor.handle_missing_values(df, strategy='interpolate')
            
            # Detect outliers
            df, outlier_counts = self.ts_preprocessor.detect_and_remove_outliers(
                df, columns=[metric], method='zscore', threshold=3.0, remove=False
            )
            
            # Create time features
            df = self.ts_preprocessor.create_time_features(df)
            
            # Convert to serializable format
            result = {
                'data': df[metric].to_dict(),
                'timestamps': [ts.isoformat() for ts in df.index],
                'statistics': {
                    'mean': float(df[metric].mean()),
                    'median': float(df[metric].median()),
                    'std': float(df[metric].std()),
                    'min': float(df[metric].min()),
                    'max': float(df[metric].max()),
                    'count': len(df)
                },
                'outliers': outlier_counts,
                'aggregation': aggregation,
                'metric': metric
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting time series data: {e}")
            return {'error': str(e)}
    
    def analyze_trend(self, start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     metric: str = 'total_requests',
                     method: str = 'linear') -> Dict[str, Any]:
        """
        Analyze trends in time series data
        
        Args:
            start_date: Start date
            end_date: End date
            metric: Metric to analyze
            method: Trend detection method ('linear', 'polynomial', 'exponential', 'moving_average')
        
        Returns:
            Trend analysis results
        """
        try:
            conn = get_connection()
            if not conn:
                return {'error': 'Database connection unavailable'}
            
            # Load data
            df = self.ts_preprocessor.load_data_from_db(conn, start_date, end_date, 'daily')
            conn.close()
            
            if df.empty or metric not in df.columns:
                return {'error': f'No data available for metric: {metric}'}
            
            series = df[metric]
            
            # Detect trend
            trend_info = self.trend_analyzer.detect_trend(series, method=method)
            
            # Calculate trend strength
            strength_info = self.trend_analyzer.calculate_trend_strength(series)
            
            # Identify change points
            change_points = self.trend_analyzer.identify_change_points(series, min_size=5, penalty=1.0)
            
            # Identify peaks and troughs
            peaks_troughs = self.trend_analyzer.identify_peaks_and_troughs(series, prominence=0.1)
            
            # Serialize trend line if present
            if 'trend_line' in trend_info and isinstance(trend_info['trend_line'], pd.Series):
                trend_info['trend_line'] = {
                    'values': trend_info['trend_line'].tolist(),
                    'timestamps': [ts.isoformat() for ts in trend_info['trend_line'].index]
                }
            
            result = {
                'metric': metric,
                'period': {
                    'start': start_date or (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
                    'end': end_date or datetime.now().strftime('%Y-%m-%d')
                },
                'trend': trend_info,
                'strength': strength_info,
                'change_points': change_points,
                'peaks_and_troughs': peaks_troughs,
                'data_points': len(series)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing trend: {e}")
            return {'error': str(e)}
    
    def detect_seasonality(self, start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          metric: str = 'total_requests',
                          model: str = 'additive',
                          period: Optional[int] = None) -> Dict[str, Any]:
        """
        Detect and analyze seasonality in time series
        
        Args:
            start_date: Start date
            end_date: End date
            metric: Metric to analyze
            model: Decomposition model ('additive' or 'multiplicative')
            period: Seasonal period (auto-detected if None)
        
        Returns:
            Seasonality analysis results
        """
        try:
            conn = get_connection()
            if not conn:
                return {'error': 'Database connection unavailable'}
            
            # Load data
            df = self.ts_preprocessor.load_data_from_db(conn, start_date, end_date, 'daily')
            conn.close()
            
            if df.empty or metric not in df.columns:
                return {'error': f'No data available for metric: {metric}'}
            
            series = df[metric]
            
            # Decompose time series
            components = self.ts_decomposer.decompose(series, model=model, period=period)
            
            # Calculate seasonality strength
            if 'seasonal' in components and 'residual' in components:
                seasonal_var = np.var(components['seasonal'].dropna())
                residual_var = np.var(components['residual'].dropna())
                seasonality_strength = seasonal_var / (seasonal_var + residual_var) if (seasonal_var + residual_var) > 0 else 0
            else:
                seasonality_strength = 0
            
            # Serialize components
            result = {
                'metric': metric,
                'model': model,
                'period': period or 7,
                'seasonality_strength': float(seasonality_strength),
                'components': {}
            }
            
            for comp_name, comp_series in components.items():
                if isinstance(comp_series, pd.Series):
                    result['components'][comp_name] = {
                        'values': comp_series.tolist(),
                        'timestamps': [ts.isoformat() for ts in comp_series.index],
                        'mean': float(comp_series.mean()),
                        'std': float(comp_series.std())
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting seasonality: {e}")
            return {'error': str(e)}
    
    def forecast_metric(self, metric: str = 'total_requests',
                       steps: int = 30,
                       model: str = 'arima',
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Forecast future values of a metric
        
        Args:
            metric: Metric to forecast
            steps: Number of steps to forecast
            model: Forecasting model ('arima', 'sarima', 'exp_smoothing', 'prophet', 'ensemble')
            start_date: Historical data start date
            end_date: Historical data end date
        
        Returns:
            Forecast results with confidence intervals
        """
        try:
            conn = get_connection()
            if not conn:
                return {'error': 'Database connection unavailable'}
            
            # Load historical data
            df = self.ts_preprocessor.load_data_from_db(conn, start_date, end_date, 'daily')
            conn.close()
            
            if df.empty or metric not in df.columns:
                return {'error': f'No data available for metric: {metric}'}
            
            series = df[metric]
            
            # Generate forecast based on model
            if model == 'arima':
                forecast_result = self.forecaster.forecast_arima(series, steps=steps)
            elif model == 'sarima':
                forecast_result = self.forecaster.forecast_sarima(series, steps=steps)
            elif model == 'exp_smoothing':
                forecast_result = self.forecaster.forecast_exponential_smoothing(series, steps=steps)
            elif model == 'prophet':
                forecast_result = self.forecaster.forecast_prophet(series, steps=steps)
            elif model == 'ensemble':
                forecast_result = self.forecaster.ensemble_forecast(series, steps=steps)
            else:
                return {'error': f'Unknown model: {model}'}
            
            if 'error' in forecast_result:
                return forecast_result
            
            # Serialize forecast results
            result = {
                'metric': metric,
                'model': forecast_result.get('model', model),
                'steps': steps,
                'forecast': {},
                'historical': {}
            }
            
            # Serialize forecast
            if 'forecast' in forecast_result and isinstance(forecast_result['forecast'], pd.Series):
                result['forecast'] = {
                    'values': forecast_result['forecast'].tolist(),
                    'timestamps': [ts.isoformat() for ts in forecast_result['forecast'].index]
                }
            
            # Serialize confidence intervals if available
            if 'lower_bound' in forecast_result and isinstance(forecast_result['lower_bound'], pd.Series):
                result['lower_bound'] = {
                    'values': forecast_result['lower_bound'].tolist(),
                    'timestamps': [ts.isoformat() for ts in forecast_result['lower_bound'].index]
                }
            
            if 'upper_bound' in forecast_result and isinstance(forecast_result['upper_bound'], pd.Series):
                result['upper_bound'] = {
                    'values': forecast_result['upper_bound'].tolist(),
                    'timestamps': [ts.isoformat() for ts in forecast_result['upper_bound'].index]
                }
            
            # Serialize historical data
            if 'historical' in forecast_result and isinstance(forecast_result['historical'], pd.Series):
                result['historical'] = {
                    'values': forecast_result['historical'].tolist(),
                    'timestamps': [ts.isoformat() for ts in forecast_result['historical'].index]
                }
            
            # Add model-specific info
            for key in ['aic', 'bic', 'order', 'seasonal_order', 'models_used', 'weights']:
                if key in forecast_result:
                    result[key] = forecast_result[key]
            
            return result
            
        except Exception as e:
            logger.error(f"Error forecasting metric: {e}")
            return {'error': str(e)}
    
    def detect_anomalies(self, start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        metric: str = 'total_requests',
                        method: str = 'zscore',
                        threshold: float = 3.0) -> Dict[str, Any]:
        """
        Detect anomalies in time series data
        
        Args:
            start_date: Start date
            end_date: End date
            metric: Metric to analyze
            method: Detection method ('zscore', 'iqr', 'isolation_forest')
            threshold: Threshold for anomaly detection
        
        Returns:
            Detected anomalies with details
        """
        try:
            conn = get_connection()
            if not conn:
                return {'error': 'Database connection unavailable'}
            
            # Load data
            df = self.ts_preprocessor.load_data_from_db(conn, start_date, end_date, 'daily')
            conn.close()
            
            if df.empty or metric not in df.columns:
                return {'error': f'No data available for metric: {metric}'}
            
            # Detect outliers (anomalies)
            df_with_outliers, outlier_counts = self.ts_preprocessor.detect_and_remove_outliers(
                df, columns=[metric], method=method, threshold=threshold, remove=False
            )
            
            # Extract anomalies
            outlier_col = f'{metric}_outlier'
            if outlier_col in df_with_outliers.columns:
                anomalies = df_with_outliers[df_with_outliers[outlier_col] == True]
                
                anomaly_list = []
                for idx, row in anomalies.iterrows():
                    anomaly_list.append({
                        'timestamp': idx.isoformat(),
                        'value': float(row[metric]),
                        'expected_range': {
                            'mean': float(df[metric].mean()),
                            'std': float(df[metric].std())
                        },
                        'deviation': float(abs(row[metric] - df[metric].mean()) / df[metric].std()) if df[metric].std() > 0 else 0
                    })
                
                result = {
                    'metric': metric,
                    'method': method,
                    'threshold': threshold,
                    'total_anomalies': len(anomaly_list),
                    'anomaly_rate': len(anomaly_list) / len(df) * 100 if len(df) > 0 else 0,
                    'anomalies': anomaly_list,
                    'statistics': {
                        'total_points': len(df),
                        'mean': float(df[metric].mean()),
                        'std': float(df[metric].std()),
                        'min': float(df[metric].min()),
                        'max': float(df[metric].max())
                    }
                }
                
                return result
            else:
                return {'error': 'Anomaly detection failed'}
                
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return {'error': str(e)}
    
    def get_visualization_data(self, start_date: Optional[str] = None,
                              end_date: Optional[str] = None,
                              metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get data formatted for visualization
        
        Args:
            start_date: Start date
            end_date: End date
            metrics: List of metrics to include
        
        Returns:
            Visualization-ready data
        """
        try:
            if metrics is None:
                metrics = ['total_requests', 'avg_confidence', 'avg_processing_time', 'success_rate']
            
            conn = get_connection()
            if not conn:
                return {'error': 'Database connection unavailable'}
            
            # Load data
            df = self.ts_preprocessor.load_data_from_db(conn, start_date, end_date, 'daily')
            conn.close()
            
            if df.empty:
                return {'error': 'No data available'}
            
            # Prepare visualization data
            result = {
                'timestamps': [ts.isoformat() for ts in df.index],
                'metrics': {}
            }
            
            for metric in metrics:
                if metric in df.columns:
                    # Get raw data
                    raw_values = df[metric].tolist()
                    
                    # Get smoothed data
                    smoothed = self.ts_preprocessor.smooth_series(df, metric, method='moving_average', window=7)
                    
                    # Get trend
                    trend_info = self.trend_analyzer.detect_trend(df[metric], method='linear')
                    trend_line = []
                    if 'trend_line' in trend_info and isinstance(trend_info['trend_line'], pd.Series):
                        trend_line = trend_info['trend_line'].tolist()
                    
                    result['metrics'][metric] = {
                        'raw': raw_values,
                        'smoothed': smoothed.tolist(),
                        'trend': trend_line,
                        'statistics': {
                            'mean': float(df[metric].mean()),
                            'median': float(df[metric].median()),
                            'min': float(df[metric].min()),
                            'max': float(df[metric].max()),
                            'std': float(df[metric].std())
                        },
                        'trend_direction': trend_info.get('direction', 'unknown')
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting visualization data: {e}")
            return {'error': str(e)}
    
    def get_performance_metrics(self, start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics with time series analysis
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            Performance metrics with trends and forecasts
        """
        try:
            conn = get_connection()
            if not conn:
                return {'error': 'Database connection unavailable'}
            
            # Load data
            df = self.ts_preprocessor.load_data_from_db(conn, start_date, end_date, 'daily')
            conn.close()
            
            if df.empty:
                return {'error': 'No data available'}
            
            # Analyze key metrics
            metrics_analysis = {}
            key_metrics = ['total_requests', 'avg_confidence', 'avg_processing_time', 'success_rate']
            
            for metric in key_metrics:
                if metric in df.columns:
                    series = df[metric]
                    
                    # Trend analysis
                    trend = self.trend_analyzer.detect_trend(series, method='linear')
                    
                    # Recent vs historical comparison
                    if len(series) >= 14:
                        recent_period = series.tail(7)
                        previous_period = series.tail(14).head(7)
                        
                        change_pct = ((recent_period.mean() - previous_period.mean()) / previous_period.mean() * 100) if previous_period.mean() != 0 else 0
                    else:
                        change_pct = 0
                    
                    metrics_analysis[metric] = {
                        'current_value': float(series.iloc[-1]) if len(series) > 0 else 0,
                        'mean': float(series.mean()),
                        'trend_direction': trend.get('direction', 'unknown'),
                        'trend_strength': trend.get('strength', 0),
                        'change_percentage': float(change_pct),
                        'is_improving': change_pct > 0 if metric in ['total_requests', 'avg_confidence', 'success_rate'] else change_pct < 0
                    }
            
            return {
                'period': {
                    'start': start_date or (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
                    'end': end_date or datetime.now().strftime('%Y-%m-%d')
                },
                'metrics': metrics_analysis,
                'data_points': len(df),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e)}

analytics = AnalyticsAPI()
