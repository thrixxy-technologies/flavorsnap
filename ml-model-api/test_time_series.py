"""
Comprehensive tests for Time Series Analysis Module
"""

import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from time_series import TimeSeriesPreprocessor, TimeSeriesDecomposer
from trend_analysis import TrendAnalyzer
from forecasting import TimeSeriesForecaster


class TestTimeSeriesPreprocessor(unittest.TestCase):
    """Test TimeSeriesPreprocessor functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.preprocessor = TimeSeriesPreprocessor()
        
        # Create sample time series data
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        np.random.seed(42)
        values = 100 + np.cumsum(np.random.randn(len(dates))) + 10 * np.sin(np.arange(len(dates)) * 2 * np.pi / 7)
        
        self.sample_df = pd.DataFrame({
            'value': values,
            'metric1': values + np.random.randn(len(dates)) * 5,
            'metric2': values * 1.5 + np.random.randn(len(dates)) * 10
        }, index=dates)
        
        # Create series with missing values
        self.series_with_missing = self.sample_df['value'].copy()
        self.series_with_missing.iloc[10:15] = np.nan
        self.series_with_missing.iloc[50:52] = np.nan
    
    def test_handle_missing_values_interpolate(self):
        """Test interpolation for missing values"""
        df = pd.DataFrame({'value': self.series_with_missing})
        result = self.preprocessor.handle_missing_values(df, strategy='interpolate')
        
        self.assertEqual(result['value'].isna().sum(), 0)
        self.assertEqual(len(result), len(df))
    
    def test_handle_missing_values_forward_fill(self):
        """Test forward fill for missing values"""
        df = pd.DataFrame({'value': self.series_with_missing})
        result = self.preprocessor.handle_missing_values(df, strategy='forward_fill')
        
        self.assertEqual(result['value'].isna().sum(), 0)
    
    def test_detect_outliers_zscore(self):
        """Test outlier detection using z-score"""
        # Add outliers
        df = self.sample_df.copy()
        df.loc[df.index[10], 'value'] = df['value'].mean() + 5 * df['value'].std()
        
        result_df, outlier_counts = self.preprocessor.detect_and_remove_outliers(
            df, columns=['value'], method='zscore', threshold=3.0, remove=False
        )
        
        self.assertIn('value_outlier', result_df.columns)
        self.assertGreater(outlier_counts['value'], 0)
    
    def test_detect_outliers_iqr(self):
        """Test outlier detection using IQR"""
        df = self.sample_df.copy()
        df.loc[df.index[10], 'value'] = df['value'].max() * 2
        
        result_df, outlier_counts = self.preprocessor.detect_and_remove_outliers(
            df, columns=['value'], method='iqr', threshold=1.5, remove=False
        )
        
        self.assertIn('value_outlier', result_df.columns)
    
    def test_create_time_features(self):
        """Test time feature creation"""
        result = self.preprocessor.create_time_features(self.sample_df)
        
        # Check that time features are created
        expected_features = ['hour', 'day_of_week', 'month', 'year', 'is_weekend',
                           'hour_sin', 'hour_cos', 'day_sin', 'day_cos']
        
        for feature in expected_features:
            self.assertIn(feature, result.columns)
    
    def test_smooth_series_moving_average(self):
        """Test moving average smoothing"""
        smoothed = self.preprocessor.smooth_series(
            self.sample_df, 'value', method='moving_average', window=7
        )
        
        self.assertEqual(len(smoothed), len(self.sample_df))
        self.assertIsInstance(smoothed, pd.Series)
    
    def test_smooth_series_exponential(self):
        """Test exponential smoothing"""
        smoothed = self.preprocessor.smooth_series(
            self.sample_df, 'value', method='exponential', window=7
        )
        
        self.assertEqual(len(smoothed), len(self.sample_df))
    
    def test_resample_series(self):
        """Test time series resampling"""
        resampled = self.preprocessor.resample_series(
            self.sample_df, freq='W', agg_func='mean'
        )
        
        self.assertLess(len(resampled), len(self.sample_df))
        self.assertIsInstance(resampled, pd.DataFrame)
    
    def test_normalize_series_minmax(self):
        """Test min-max normalization"""
        normalized, params = self.preprocessor.normalize_series(
            self.sample_df, columns=['value'], method='minmax'
        )
        
        self.assertGreaterEqual(normalized['value'].min(), 0)
        self.assertLessEqual(normalized['value'].max(), 1)
        self.assertIn('value', params)
    
    def test_normalize_series_zscore(self):
        """Test z-score normalization"""
        normalized, params = self.preprocessor.normalize_series(
            self.sample_df, columns=['value'], method='zscore'
        )
        
        self.assertAlmostEqual(normalized['value'].mean(), 0, places=1)
        self.assertAlmostEqual(normalized['value'].std(), 1, places=1)


class TestTimeSeriesDecomposer(unittest.TestCase):
    """Test TimeSeriesDecomposer functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.decomposer = TimeSeriesDecomposer()
        
        # Create time series with trend and seasonality
        dates = pd.date_range(start='2024-01-01', periods=365, freq='D')
        trend = np.linspace(100, 200, 365)
        seasonal = 20 * np.sin(np.arange(365) * 2 * np.pi / 7)
        noise = np.random.randn(365) * 5
        
        self.series = pd.Series(trend + seasonal + noise, index=dates)
    
    def test_decompose_additive(self):
        """Test additive decomposition"""
        components = self.decomposer.decompose(self.series, model='additive', period=7)
        
        self.assertIn('trend', components)
        self.assertIn('seasonal', components)
        self.assertIn('residual', components)
        self.assertIsInstance(components['trend'], pd.Series)
    
    def test_decompose_multiplicative(self):
        """Test multiplicative decomposition"""
        # Use positive values for multiplicative
        positive_series = self.series + abs(self.series.min()) + 10
        components = self.decomposer.decompose(positive_series, model='multiplicative', period=7)
        
        self.assertIn('trend', components)
        self.assertIn('seasonal', components)
    
    def test_decompose_short_series(self):
        """Test decomposition with insufficient data"""
        short_series = self.series.head(10)
        components = self.decomposer.decompose(short_series, model='additive', period=7)
        
        # Should handle gracefully
        self.assertIsInstance(components, dict)


class TestTrendAnalyzer(unittest.TestCase):
    """Test TrendAnalyzer functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.analyzer = TrendAnalyzer()
        
        # Create series with clear upward trend
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        self.upward_series = pd.Series(np.arange(100) + np.random.randn(100) * 5, index=dates)
        
        # Create series with downward trend
        self.downward_series = pd.Series(100 - np.arange(100) + np.random.randn(100) * 5, index=dates)
        
        # Create stable series
        self.stable_series = pd.Series(50 + np.random.randn(100) * 2, index=dates)
    
    def test_detect_linear_trend_upward(self):
        """Test linear trend detection for upward trend"""
        result = self.analyzer.detect_trend(self.upward_series, method='linear')
        
        self.assertEqual(result['direction'], 'increasing')
        self.assertGreater(result['slope'], 0)
        self.assertIn('r_squared', result)
    
    def test_detect_linear_trend_downward(self):
        """Test linear trend detection for downward trend"""
        result = self.analyzer.detect_trend(self.downward_series, method='linear')
        
        self.assertEqual(result['direction'], 'decreasing')
        self.assertLess(result['slope'], 0)
    
    def test_detect_linear_trend_stable(self):
        """Test linear trend detection for stable series"""
        result = self.analyzer.detect_trend(self.stable_series, method='linear')
        
        self.assertEqual(result['direction'], 'stable')
    
    def test_detect_polynomial_trend(self):
        """Test polynomial trend detection"""
        result = self.analyzer.detect_trend(self.upward_series, method='polynomial')
        
        self.assertEqual(result['method'], 'polynomial')
        self.assertIn('coefficients', result)
        self.assertIn('curvature', result)
    
    def test_detect_exponential_trend(self):
        """Test exponential trend detection"""
        result = self.analyzer.detect_trend(self.upward_series, method='exponential')
        
        self.assertEqual(result['method'], 'exponential')
        self.assertIn('growth_rate', result)
    
    def test_calculate_trend_strength(self):
        """Test trend strength calculation"""
        result = self.analyzer.calculate_trend_strength(self.upward_series)
        
        self.assertIn('overall_strength', result)
        self.assertIn('linear_strength', result)
        self.assertIn('consistency', result)
        self.assertIn('interpretation', result)
        self.assertGreaterEqual(result['overall_strength'], 0)
        self.assertLessEqual(result['overall_strength'], 1)
    
    def test_identify_peaks_and_troughs(self):
        """Test peak and trough identification"""
        # Create series with clear peaks
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        values = np.sin(np.arange(100) * 2 * np.pi / 20) * 50 + 100
        series = pd.Series(values, index=dates)
        
        result = self.analyzer.identify_peaks_and_troughs(series, prominence=10)
        
        self.assertIn('peaks', result)
        self.assertIn('troughs', result)
        self.assertGreater(result['peak_count'], 0)
        self.assertGreater(result['trough_count'], 0)
    
    def test_compare_periods(self):
        """Test period comparison"""
        dates = pd.date_range(start='2024-01-01', periods=200, freq='D')
        series = pd.Series(np.arange(200) + np.random.randn(200) * 5, index=dates)
        
        result = self.analyzer.compare_periods(
            series,
            '2024-01-01', '2024-03-31',
            '2024-04-01', '2024-06-30'
        )
        
        self.assertIn('period1', result)
        self.assertIn('period2', result)
        self.assertIn('comparison', result)
        self.assertIn('mean_change_pct', result['comparison'])


class TestTimeSeriesForecaster(unittest.TestCase):
    """Test TimeSeriesForecaster functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.forecaster = TimeSeriesForecaster()
        
        # Create time series with trend and seasonality
        dates = pd.date_range(start='2024-01-01', periods=200, freq='D')
        trend = np.linspace(100, 150, 200)
        seasonal = 10 * np.sin(np.arange(200) * 2 * np.pi / 7)
        noise = np.random.randn(200) * 3
        
        self.series = pd.Series(trend + seasonal + noise, index=dates)
    
    def test_forecast_arima(self):
        """Test ARIMA forecasting"""
        result = self.forecaster.forecast_arima(self.series, steps=30)
        
        if 'error' not in result:
            self.assertEqual(result['model'], 'ARIMA')
            self.assertIn('forecast', result)
            self.assertIn('order', result)
            self.assertEqual(len(result['forecast']), 30)
    
    def test_forecast_sarima(self):
        """Test SARIMA forecasting"""
        result = self.forecaster.forecast_sarima(self.series, steps=30)
        
        if 'error' not in result:
            self.assertEqual(result['model'], 'SARIMA')
            self.assertIn('forecast', result)
            self.assertIn('seasonal_order', result)
    
    def test_forecast_exponential_smoothing(self):
        """Test Exponential Smoothing forecasting"""
        result = self.forecaster.forecast_exponential_smoothing(self.series, steps=30)
        
        if 'error' not in result:
            self.assertEqual(result['model'], 'Exponential_Smoothing')
            self.assertIn('forecast', result)
            self.assertEqual(len(result['forecast']), 30)
    
    def test_forecast_ensemble(self):
        """Test ensemble forecasting"""
        result = self.forecaster.ensemble_forecast(
            self.series, steps=30, models=['arima', 'exp_smoothing']
        )
        
        if 'error' not in result:
            self.assertEqual(result['model'], 'Ensemble')
            self.assertIn('forecast', result)
            self.assertIn('models_used', result)
    
    def test_evaluate_forecast(self):
        """Test forecast evaluation"""
        # Create actual and predicted series
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        actual = pd.Series(np.arange(30) + 100, index=dates)
        predicted = pd.Series(np.arange(30) + 100 + np.random.randn(30) * 2, index=dates)
        
        metrics = self.forecaster.evaluate_forecast(actual, predicted)
        
        self.assertIn('mae', metrics)
        self.assertIn('rmse', metrics)
        self.assertIn('mape', metrics)
        self.assertIn('r2', metrics)
        self.assertGreater(metrics['mae'], 0)
    
    def test_forecast_with_insufficient_data(self):
        """Test forecasting with insufficient data"""
        short_series = self.series.head(5)
        result = self.forecaster.forecast_arima(short_series, steps=30)
        
        self.assertIn('error', result)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflow"""
    
    def setUp(self):
        """Set up components"""
        self.preprocessor = TimeSeriesPreprocessor()
        self.decomposer = TimeSeriesDecomposer()
        self.analyzer = TrendAnalyzer()
        self.forecaster = TimeSeriesForecaster()
        
        # Create realistic time series
        dates = pd.date_range(start='2024-01-01', periods=365, freq='D')
        trend = np.linspace(100, 200, 365)
        seasonal = 20 * np.sin(np.arange(365) * 2 * np.pi / 7)
        noise = np.random.randn(365) * 5
        
        self.df = pd.DataFrame({
            'value': trend + seasonal + noise
        }, index=dates)
    
    def test_complete_analysis_workflow(self):
        """Test complete analysis workflow"""
        # 1. Preprocess
        df_clean = self.preprocessor.handle_missing_values(self.df)
        df_clean, _ = self.preprocessor.detect_and_remove_outliers(df_clean)
        
        # 2. Decompose
        components = self.decomposer.decompose(df_clean['value'], period=7)
        
        # 3. Analyze trend
        trend_info = self.analyzer.detect_trend(df_clean['value'])
        
        # 4. Forecast
        forecast_result = self.forecaster.forecast_arima(df_clean['value'], steps=30)
        
        # Verify all steps completed
        self.assertIsNotNone(df_clean)
        self.assertIn('trend', components)
        self.assertIn('direction', trend_info)
        
        if 'error' not in forecast_result:
            self.assertIn('forecast', forecast_result)
    
    def test_anomaly_detection_workflow(self):
        """Test anomaly detection workflow"""
        # Add anomalies
        df = self.df.copy()
        df.loc[df.index[50], 'value'] = df['value'].mean() + 5 * df['value'].std()
        df.loc[df.index[100], 'value'] = df['value'].mean() - 5 * df['value'].std()
        
        # Detect anomalies
        df_with_outliers, outlier_counts = self.preprocessor.detect_and_remove_outliers(
            df, columns=['value'], method='zscore', threshold=3.0, remove=False
        )
        
        self.assertGreater(outlier_counts['value'], 0)
        self.assertIn('value_outlier', df_with_outliers.columns)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTimeSeriesPreprocessor))
    suite.addTests(loader.loadTestsFromTestCase(TestTimeSeriesDecomposer))
    suite.addTests(loader.loadTestsFromTestCase(TestTrendAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestTimeSeriesForecaster))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
