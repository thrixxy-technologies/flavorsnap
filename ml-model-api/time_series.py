"""
Time Series Analysis Module for FlavorSnap
Handles time series preprocessing, decomposition, and data preparation
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from scipy import signal
from scipy.stats import zscore
from collections import defaultdict

logger = logging.getLogger(__name__)


class TimeSeriesPreprocessor:
    """Handles time series data preprocessing and cleaning"""
    
    def __init__(self):
        self.missing_value_strategies = ['forward_fill', 'backward_fill', 'interpolate', 'mean', 'median']
    
    def load_data_from_db(self, conn, start_date: Optional[str] = None, 
                         end_date: Optional[str] = None, 
                         aggregation: str = 'daily') -> pd.DataFrame:
        """
        Load time series data from database
        
        Args:
            conn: Database connection
            start_date: Start date for data retrieval (YYYY-MM-DD)
            end_date: End date for data retrieval (YYYY-MM-DD)
            aggregation: Time aggregation level ('hourly', 'daily', 'weekly', 'monthly')
        
        Returns:
            DataFrame with time series data
        """
        try:
            # Set default date range if not provided
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            # Define aggregation format
            agg_formats = {
                'hourly': "DATE_TRUNC('hour', created_at)",
                'daily': "DATE_TRUNC('day', created_at)",
                'weekly': "DATE_TRUNC('week', created_at)",
                'monthly': "DATE_TRUNC('month', created_at)"
            }
            
            time_trunc = agg_formats.get(aggregation, agg_formats['daily'])
            
            query = f"""
                SELECT
                    {time_trunc} as timestamp,
                    COUNT(*) as total_requests,
                    COUNT(DISTINCT user_id) as unique_users,
                    AVG(confidence) as avg_confidence,
                    AVG(processing_time) as avg_processing_time,
                    SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as successful_requests,
                    SUM(CASE WHEN success = false THEN 1 ELSE 0 END) as failed_requests,
                    COUNT(DISTINCT label) as unique_labels,
                    MAX(confidence) as max_confidence,
                    MIN(confidence) as min_confidence,
                    STDDEV(confidence) as std_confidence,
                    STDDEV(processing_time) as std_processing_time
                FROM prediction_history
                WHERE created_at BETWEEN %s AND %s
                GROUP BY {time_trunc}
                ORDER BY timestamp
            """
            
            with conn.cursor() as cur:
                cur.execute(query, (start_date, end_date))
                results = cur.fetchall()
                
                if not results:
                    logger.warning("No data found for the specified date range")
                    return pd.DataFrame()
                
                # Create DataFrame
                df = pd.DataFrame(results, columns=[
                    'timestamp', 'total_requests', 'unique_users', 'avg_confidence',
                    'avg_processing_time', 'successful_requests', 'failed_requests',
                    'unique_labels', 'max_confidence', 'min_confidence',
                    'std_confidence', 'std_processing_time'
                ])
                
                # Convert timestamp to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                # Calculate derived metrics
                df['success_rate'] = df['successful_requests'] / df['total_requests']
                df['failure_rate'] = df['failed_requests'] / df['total_requests']
                
                logger.info(f"Loaded {len(df)} time series records from {start_date} to {end_date}")
                return df
                
        except Exception as e:
            logger.error(f"Error loading time series data: {e}")
            return pd.DataFrame()
    
    def handle_missing_values(self, df: pd.DataFrame, strategy: str = 'interpolate',
                             columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Handle missing values in time series data
        
        Args:
            df: Input DataFrame
            strategy: Strategy for handling missing values
            columns: Specific columns to process (None = all numeric columns)
        
        Returns:
            DataFrame with missing values handled
        """
        if df.empty:
            return df
        
        df_copy = df.copy()
        
        if columns is None:
            columns = df_copy.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            if col not in df_copy.columns:
                continue
                
            if strategy == 'forward_fill':
                df_copy[col] = df_copy[col].ffill()
            elif strategy == 'backward_fill':
                df_copy[col] = df_copy[col].bfill()
            elif strategy == 'interpolate':
                df_copy[col] = df_copy[col].interpolate(method='linear', limit_direction='both')
            elif strategy == 'mean':
                df_copy[col] = df_copy[col].fillna(df_copy[col].mean())
            elif strategy == 'median':
                df_copy[col] = df_copy[col].fillna(df_copy[col].median())
            else:
                logger.warning(f"Unknown strategy '{strategy}', using interpolation")
                df_copy[col] = df_copy[col].interpolate(method='linear', limit_direction='both')
        
        logger.info(f"Handled missing values using strategy: {strategy}")
        return df_copy
    
    def detect_and_remove_outliers(self, df: pd.DataFrame, columns: Optional[List[str]] = None,
                                   method: str = 'zscore', threshold: float = 3.0,
                                   remove: bool = False) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """
        Detect and optionally remove outliers from time series data
        
        Args:
            df: Input DataFrame
            columns: Columns to check for outliers
            method: Detection method ('zscore', 'iqr', 'isolation_forest')
            threshold: Threshold for outlier detection
            remove: Whether to remove outliers or just flag them
        
        Returns:
            Tuple of (processed DataFrame, outlier counts dict)
        """
        if df.empty:
            return df, {}
        
        df_copy = df.copy()
        outlier_counts = {}
        
        if columns is None:
            columns = df_copy.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            if col not in df_copy.columns:
                continue
            
            if method == 'zscore':
                z_scores = np.abs(zscore(df_copy[col].dropna()))
                outliers = z_scores > threshold
                outlier_mask = pd.Series(False, index=df_copy.index)
                outlier_mask.loc[df_copy[col].notna()] = outliers
                
            elif method == 'iqr':
                Q1 = df_copy[col].quantile(0.25)
                Q3 = df_copy[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                outlier_mask = (df_copy[col] < lower_bound) | (df_copy[col] > upper_bound)
            
            else:
                logger.warning(f"Unknown method '{method}', using zscore")
                z_scores = np.abs(zscore(df_copy[col].dropna()))
                outliers = z_scores > threshold
                outlier_mask = pd.Series(False, index=df_copy.index)
                outlier_mask.loc[df_copy[col].notna()] = outliers
            
            outlier_counts[col] = outlier_mask.sum()
            
            if remove and outlier_counts[col] > 0:
                df_copy.loc[outlier_mask, col] = np.nan
                logger.info(f"Removed {outlier_counts[col]} outliers from column '{col}'")
            else:
                df_copy[f'{col}_outlier'] = outlier_mask
        
        return df_copy, outlier_counts
    
    def create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create time-based features from timestamp index
        
        Args:
            df: Input DataFrame with datetime index
        
        Returns:
            DataFrame with additional time features
        """
        if df.empty or not isinstance(df.index, pd.DatetimeIndex):
            return df
        
        df_copy = df.copy()
        
        # Extract time components
        df_copy['hour'] = df_copy.index.hour
        df_copy['day_of_week'] = df_copy.index.dayofweek
        df_copy['day_of_month'] = df_copy.index.day
        df_copy['day_of_year'] = df_copy.index.dayofyear
        df_copy['week_of_year'] = df_copy.index.isocalendar().week
        df_copy['month'] = df_copy.index.month
        df_copy['quarter'] = df_copy.index.quarter
        df_copy['year'] = df_copy.index.year
        
        # Create cyclical features for better ML model performance
        df_copy['hour_sin'] = np.sin(2 * np.pi * df_copy['hour'] / 24)
        df_copy['hour_cos'] = np.cos(2 * np.pi * df_copy['hour'] / 24)
        df_copy['day_sin'] = np.sin(2 * np.pi * df_copy['day_of_week'] / 7)
        df_copy['day_cos'] = np.cos(2 * np.pi * df_copy['day_of_week'] / 7)
        df_copy['month_sin'] = np.sin(2 * np.pi * df_copy['month'] / 12)
        df_copy['month_cos'] = np.cos(2 * np.pi * df_copy['month'] / 12)
        
        # Boolean features
        df_copy['is_weekend'] = df_copy['day_of_week'].isin([5, 6]).astype(int)
        df_copy['is_month_start'] = df_copy.index.is_month_start.astype(int)
        df_copy['is_month_end'] = df_copy.index.is_month_end.astype(int)
        df_copy['is_quarter_start'] = df_copy.index.is_quarter_start.astype(int)
        df_copy['is_quarter_end'] = df_copy.index.is_quarter_end.astype(int)
        
        logger.info("Created time-based features")
        return df_copy
    
    def smooth_series(self, df: pd.DataFrame, column: str, 
                     method: str = 'moving_average', window: int = 7) -> pd.Series:
        """
        Apply smoothing to a time series
        
        Args:
            df: Input DataFrame
            column: Column to smooth
            method: Smoothing method ('moving_average', 'exponential', 'savgol')
            window: Window size for smoothing
        
        Returns:
            Smoothed series
        """
        if column not in df.columns:
            logger.error(f"Column '{column}' not found in DataFrame")
            return pd.Series()
        
        series = df[column].copy()
        
        if method == 'moving_average':
            smoothed = series.rolling(window=window, center=True).mean()
        elif method == 'exponential':
            smoothed = series.ewm(span=window, adjust=False).mean()
        elif method == 'savgol':
            # Savitzky-Golay filter
            if len(series) >= window:
                smoothed = pd.Series(
                    signal.savgol_filter(series.ffill(), window, 3),
                    index=series.index
                )
            else:
                logger.warning(f"Series too short for Savgol filter, using moving average")
                smoothed = series.rolling(window=min(window, len(series)), center=True).mean()
        else:
            logger.warning(f"Unknown smoothing method '{method}', using moving average")
            smoothed = series.rolling(window=window, center=True).mean()
        
        return smoothed
    
    def resample_series(self, df: pd.DataFrame, freq: str = 'D', 
                       agg_func: str = 'mean') -> pd.DataFrame:
        """
        Resample time series to different frequency
        
        Args:
            df: Input DataFrame with datetime index
            freq: Target frequency ('H'=hourly, 'D'=daily, 'W'=weekly, 'M'=monthly)
            agg_func: Aggregation function ('mean', 'sum', 'min', 'max', 'median')
        
        Returns:
            Resampled DataFrame
        """
        if df.empty or not isinstance(df.index, pd.DatetimeIndex):
            return df
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        if agg_func == 'mean':
            resampled = df[numeric_cols].resample(freq).mean()
        elif agg_func == 'sum':
            resampled = df[numeric_cols].resample(freq).sum()
        elif agg_func == 'min':
            resampled = df[numeric_cols].resample(freq).min()
        elif agg_func == 'max':
            resampled = df[numeric_cols].resample(freq).max()
        elif agg_func == 'median':
            resampled = df[numeric_cols].resample(freq).median()
        else:
            logger.warning(f"Unknown aggregation function '{agg_func}', using mean")
            resampled = df[numeric_cols].resample(freq).mean()
        
        logger.info(f"Resampled series to frequency '{freq}' using '{agg_func}'")
        return resampled
    
    def normalize_series(self, df: pd.DataFrame, columns: Optional[List[str]] = None,
                        method: str = 'minmax') -> Tuple[pd.DataFrame, Dict[str, Dict[str, float]]]:
        """
        Normalize time series data
        
        Args:
            df: Input DataFrame
            columns: Columns to normalize (None = all numeric columns)
            method: Normalization method ('minmax', 'zscore', 'robust')
        
        Returns:
            Tuple of (normalized DataFrame, normalization parameters)
        """
        if df.empty:
            return df, {}
        
        df_copy = df.copy()
        norm_params = {}
        
        if columns is None:
            columns = df_copy.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            if col not in df_copy.columns:
                continue
            
            if method == 'minmax':
                min_val = df_copy[col].min()
                max_val = df_copy[col].max()
                if max_val - min_val > 0:
                    df_copy[col] = (df_copy[col] - min_val) / (max_val - min_val)
                    norm_params[col] = {'min': min_val, 'max': max_val, 'method': 'minmax'}
                    
            elif method == 'zscore':
                mean_val = df_copy[col].mean()
                std_val = df_copy[col].std()
                if std_val > 0:
                    df_copy[col] = (df_copy[col] - mean_val) / std_val
                    norm_params[col] = {'mean': mean_val, 'std': std_val, 'method': 'zscore'}
                    
            elif method == 'robust':
                median_val = df_copy[col].median()
                q75 = df_copy[col].quantile(0.75)
                q25 = df_copy[col].quantile(0.25)
                iqr = q75 - q25
                if iqr > 0:
                    df_copy[col] = (df_copy[col] - median_val) / iqr
                    norm_params[col] = {'median': median_val, 'iqr': iqr, 'method': 'robust'}
        
        logger.info(f"Normalized {len(columns)} columns using '{method}' method")
        return df_copy, norm_params


class TimeSeriesDecomposer:
    """Decomposes time series into trend, seasonal, and residual components"""
    
    def __init__(self):
        pass
    
    def decompose(self, series: pd.Series, model: str = 'additive', 
                 period: Optional[int] = None) -> Dict[str, pd.Series]:
        """
        Decompose time series into components
        
        Args:
            series: Input time series
            model: Decomposition model ('additive' or 'multiplicative')
            period: Seasonal period (auto-detected if None)
        
        Returns:
            Dictionary with 'trend', 'seasonal', 'residual' components
        """
        try:
            from statsmodels.tsa.seasonal import seasonal_decompose
            
            # Auto-detect period if not provided
            if period is None:
                period = self._detect_period(series)
            
            # Ensure we have enough data points
            if len(series) < 2 * period:
                logger.warning(f"Series too short for decomposition with period {period}")
                return {
                    'trend': series,
                    'seasonal': pd.Series(0, index=series.index),
                    'residual': pd.Series(0, index=series.index)
                }
            
            # Perform decomposition
            decomposition = seasonal_decompose(
                series.ffill(),
                model=model,
                period=period,
                extrapolate_trend='freq'
            )
            
            return {
                'trend': decomposition.trend,
                'seasonal': decomposition.seasonal,
                'residual': decomposition.resid,
                'observed': series
            }
            
        except Exception as e:
            logger.error(f"Error in time series decomposition: {e}")
            return {
                'trend': series,
                'seasonal': pd.Series(0, index=series.index),
                'residual': pd.Series(0, index=series.index)
            }
    
    def _detect_period(self, series: pd.Series) -> int:
        """Auto-detect seasonal period using autocorrelation"""
        try:
            from statsmodels.tsa.stattools import acf
            
            # Calculate autocorrelation
            autocorr = acf(series.dropna(), nlags=min(len(series) // 2, 365))
            
            # Find peaks in autocorrelation
            peaks = []
            for i in range(1, len(autocorr) - 1):
                if autocorr[i] > autocorr[i-1] and autocorr[i] > autocorr[i+1]:
                    peaks.append((i, autocorr[i]))
            
            if peaks:
                # Return the lag with highest autocorrelation
                period = max(peaks, key=lambda x: x[1])[0]
                logger.info(f"Auto-detected period: {period}")
                return period
            
            # Default periods based on data frequency
            return 7  # Default to weekly seasonality
            
        except Exception as e:
            logger.warning(f"Period auto-detection failed: {e}, using default")
            return 7


# Utility functions
def calculate_rolling_statistics(df: pd.DataFrame, column: str, 
                                 windows: List[int] = [7, 14, 30]) -> pd.DataFrame:
    """Calculate rolling statistics for a column"""
    df_copy = df.copy()
    
    for window in windows:
        df_copy[f'{column}_rolling_mean_{window}'] = df[column].rolling(window=window).mean()
        df_copy[f'{column}_rolling_std_{window}'] = df[column].rolling(window=window).std()
        df_copy[f'{column}_rolling_min_{window}'] = df[column].rolling(window=window).min()
        df_copy[f'{column}_rolling_max_{window}'] = df[column].rolling(window=window).max()
    
    return df_copy


def calculate_lag_features(df: pd.DataFrame, column: str, 
                          lags: List[int] = [1, 7, 14, 30]) -> pd.DataFrame:
    """Create lagged features for time series prediction"""
    df_copy = df.copy()
    
    for lag in lags:
        df_copy[f'{column}_lag_{lag}'] = df[column].shift(lag)
    
    return df_copy
