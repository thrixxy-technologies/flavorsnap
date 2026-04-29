"""
Trend Analysis Module for FlavorSnap
Identifies and analyzes trends in time series data
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import logging
from scipy import stats
from scipy.signal import find_peaks
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyzes trends in time series data"""
    
    def __init__(self):
        self.trend_methods = ['linear', 'polynomial', 'exponential', 'moving_average']
    
    def detect_trend(self, series: pd.Series, method: str = 'linear') -> Dict[str, Any]:
        """
        Detect trend in time series
        
        Args:
            series: Input time series
            method: Trend detection method
        
        Returns:
            Dictionary with trend information
        """
        if series.empty or len(series) < 3:
            return {'trend': 'insufficient_data', 'direction': 'unknown', 'strength': 0}
        
        # Remove NaN values
        clean_series = series.dropna()
        if len(clean_series) < 3:
            return {'trend': 'insufficient_data', 'direction': 'unknown', 'strength': 0}
        
        x = np.arange(len(clean_series))
        y = clean_series.values
        
        if method == 'linear':
            return self._linear_trend(x, y, clean_series.index)
        elif method == 'polynomial':
            return self._polynomial_trend(x, y, clean_series.index, degree=2)
        elif method == 'exponential':
            return self._exponential_trend(x, y, clean_series.index)
        elif method == 'moving_average':
            return self._moving_average_trend(clean_series)
        else:
            logger.warning(f"Unknown method '{method}', using linear")
            return self._linear_trend(x, y, clean_series.index)
    
    def _linear_trend(self, x: np.ndarray, y: np.ndarray, 
                     index: pd.Index) -> Dict[str, Any]:
        """Detect linear trend using least squares regression"""
        try:
            # Perform linear regression
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            # Calculate trend line
            trend_line = slope * x + intercept
            
            # Determine trend direction and strength
            if abs(slope) < std_err:
                direction = 'stable'
            elif slope > 0:
                direction = 'increasing'
            else:
                direction = 'decreasing'
            
            # R-squared as strength measure
            strength = r_value ** 2
            
            # Calculate percentage change
            if y[0] != 0:
                pct_change = ((y[-1] - y[0]) / abs(y[0])) * 100
            else:
                pct_change = 0
            
            return {
                'method': 'linear',
                'direction': direction,
                'strength': float(strength),
                'slope': float(slope),
                'intercept': float(intercept),
                'r_squared': float(r_value ** 2),
                'p_value': float(p_value),
                'std_error': float(std_err),
                'trend_line': pd.Series(trend_line, index=index),
                'percentage_change': float(pct_change),
                'is_significant': p_value < 0.05
            }
        except Exception as e:
            logger.error(f"Error in linear trend detection: {e}")
            return {'trend': 'error', 'direction': 'unknown', 'strength': 0}
    
    def _polynomial_trend(self, x: np.ndarray, y: np.ndarray, 
                         index: pd.Index, degree: int = 2) -> Dict[str, Any]:
        """Detect polynomial trend"""
        try:
            # Fit polynomial
            coefficients = np.polyfit(x, y, degree)
            polynomial = np.poly1d(coefficients)
            trend_line = polynomial(x)
            
            # Calculate R-squared
            ss_res = np.sum((y - trend_line) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            # Determine direction from derivative at midpoint
            derivative = np.polyder(polynomial)
            mid_point = len(x) // 2
            slope_at_mid = derivative(mid_point)
            
            if abs(slope_at_mid) < 0.01:
                direction = 'stable'
            elif slope_at_mid > 0:
                direction = 'increasing'
            else:
                direction = 'decreasing'
            
            return {
                'method': 'polynomial',
                'degree': degree,
                'direction': direction,
                'strength': float(r_squared),
                'coefficients': [float(c) for c in coefficients],
                'r_squared': float(r_squared),
                'trend_line': pd.Series(trend_line, index=index),
                'curvature': 'convex' if coefficients[0] > 0 else 'concave'
            }
        except Exception as e:
            logger.error(f"Error in polynomial trend detection: {e}")
            return {'trend': 'error', 'direction': 'unknown', 'strength': 0}
    
    def _exponential_trend(self, x: np.ndarray, y: np.ndarray, 
                          index: pd.Index) -> Dict[str, Any]:
        """Detect exponential trend"""
        try:
            # Avoid log of non-positive values
            if np.any(y <= 0):
                y_shifted = y - np.min(y) + 1
            else:
                y_shifted = y
            
            # Fit exponential: y = a * exp(b * x)
            log_y = np.log(y_shifted)
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, log_y)
            
            # Calculate trend line
            trend_line = np.exp(intercept) * np.exp(slope * x)
            
            # Adjust back if we shifted
            if np.any(y <= 0):
                trend_line = trend_line + np.min(y) - 1
            
            direction = 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'
            
            return {
                'method': 'exponential',
                'direction': direction,
                'strength': float(r_value ** 2),
                'growth_rate': float(slope),
                'r_squared': float(r_value ** 2),
                'p_value': float(p_value),
                'trend_line': pd.Series(trend_line, index=index),
                'is_significant': p_value < 0.05
            }
        except Exception as e:
            logger.error(f"Error in exponential trend detection: {e}")
            return {'trend': 'error', 'direction': 'unknown', 'strength': 0}
    
    def _moving_average_trend(self, series: pd.Series, window: int = 7) -> Dict[str, Any]:
        """Detect trend using moving average"""
        try:
            ma = series.rolling(window=window, center=True).mean()
            
            # Calculate slope of moving average
            x = np.arange(len(ma.dropna()))
            y = ma.dropna().values
            
            if len(x) < 2:
                return {'trend': 'insufficient_data', 'direction': 'unknown', 'strength': 0}
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            if abs(slope) < std_err:
                direction = 'stable'
            elif slope > 0:
                direction = 'increasing'
            else:
                direction = 'decreasing'
            
            return {
                'method': 'moving_average',
                'window': window,
                'direction': direction,
                'strength': float(r_value ** 2),
                'slope': float(slope),
                'trend_line': ma,
                'is_significant': p_value < 0.05
            }
        except Exception as e:
            logger.error(f"Error in moving average trend detection: {e}")
            return {'trend': 'error', 'direction': 'unknown', 'strength': 0}
    
    def identify_change_points(self, series: pd.Series, 
                              min_size: int = 5, 
                              penalty: float = 1.0) -> List[Dict[str, Any]]:
        """
        Identify change points in time series where trend changes
        
        Args:
            series: Input time series
            min_size: Minimum segment size
            penalty: Penalty for adding change points (higher = fewer points)
        
        Returns:
            List of change point information
        """
        try:
            import ruptures as rpt
            
            # Prepare data
            signal = series.dropna().values.reshape(-1, 1)
            
            if len(signal) < min_size * 2:
                logger.warning("Series too short for change point detection")
                return []
            
            # Detect change points using Pelt algorithm
            algo = rpt.Pelt(model="rbf", min_size=min_size, jump=1).fit(signal)
            change_points = algo.predict(pen=penalty)
            
            # Remove the last point (end of series)
            if change_points and change_points[-1] == len(signal):
                change_points = change_points[:-1]
            
            # Create change point information
            results = []
            clean_index = series.dropna().index
            
            for i, cp in enumerate(change_points):
                if cp < len(clean_index):
                    # Calculate trend before and after
                    start_idx = change_points[i-1] if i > 0 else 0
                    end_idx = cp
                    
                    before_segment = signal[start_idx:end_idx]
                    after_segment = signal[end_idx:min(end_idx + min_size, len(signal))]
                    
                    before_mean = float(np.mean(before_segment))
                    after_mean = float(np.mean(after_segment))
                    
                    change_magnitude = after_mean - before_mean
                    change_pct = (change_magnitude / before_mean * 100) if before_mean != 0 else 0
                    
                    results.append({
                        'index': int(cp),
                        'timestamp': clean_index[cp],
                        'before_mean': before_mean,
                        'after_mean': after_mean,
                        'change_magnitude': float(change_magnitude),
                        'change_percentage': float(change_pct),
                        'change_type': 'increase' if change_magnitude > 0 else 'decrease'
                    })
            
            logger.info(f"Identified {len(results)} change points")
            return results
            
        except ImportError:
            logger.warning("ruptures package not available, using simple method")
            return self._simple_change_point_detection(series, min_size)
        except Exception as e:
            logger.error(f"Error in change point detection: {e}")
            return []
    
    def _simple_change_point_detection(self, series: pd.Series, 
                                      window: int = 5) -> List[Dict[str, Any]]:
        """Simple change point detection using rolling statistics"""
        try:
            # Calculate rolling mean and std
            rolling_mean = series.rolling(window=window).mean()
            rolling_std = series.rolling(window=window).std()
            
            # Calculate z-score of differences
            diff = series.diff()
            z_scores = np.abs((diff - rolling_mean) / (rolling_std + 1e-10))
            
            # Find peaks in z-scores
            peaks, properties = find_peaks(z_scores.fillna(0), height=2.0, distance=window)
            
            results = []
            for peak in peaks:
                if peak < len(series):
                    results.append({
                        'index': int(peak),
                        'timestamp': series.index[peak],
                        'z_score': float(z_scores.iloc[peak]),
                        'value': float(series.iloc[peak]),
                        'change_type': 'significant_change'
                    })
            
            return results
        except Exception as e:
            logger.error(f"Error in simple change point detection: {e}")
            return []
    
    def calculate_trend_strength(self, series: pd.Series) -> Dict[str, float]:
        """
        Calculate various measures of trend strength
        
        Args:
            series: Input time series
        
        Returns:
            Dictionary with trend strength metrics
        """
        try:
            clean_series = series.dropna()
            if len(clean_series) < 3:
                return {'strength': 0, 'consistency': 0, 'monotonicity': 0}
            
            # Linear trend strength (R-squared)
            x = np.arange(len(clean_series))
            y = clean_series.values
            _, _, r_value, _, _ = stats.linregress(x, y)
            linear_strength = r_value ** 2
            
            # Trend consistency (percentage of consecutive increases/decreases)
            diff = np.diff(y)
            increases = np.sum(diff > 0)
            decreases = np.sum(diff < 0)
            consistency = max(increases, decreases) / len(diff) if len(diff) > 0 else 0
            
            # Monotonicity (Spearman correlation)
            spearman_corr, _ = stats.spearmanr(x, y)
            monotonicity = abs(spearman_corr)
            
            # Overall trend strength (weighted average)
            overall_strength = (linear_strength * 0.4 + consistency * 0.3 + monotonicity * 0.3)
            
            return {
                'overall_strength': float(overall_strength),
                'linear_strength': float(linear_strength),
                'consistency': float(consistency),
                'monotonicity': float(monotonicity),
                'interpretation': self._interpret_strength(overall_strength)
            }
        except Exception as e:
            logger.error(f"Error calculating trend strength: {e}")
            return {'strength': 0, 'consistency': 0, 'monotonicity': 0}
    
    def _interpret_strength(self, strength: float) -> str:
        """Interpret trend strength value"""
        if strength >= 0.8:
            return 'very_strong'
        elif strength >= 0.6:
            return 'strong'
        elif strength >= 0.4:
            return 'moderate'
        elif strength >= 0.2:
            return 'weak'
        else:
            return 'very_weak'
    
    def compare_periods(self, series: pd.Series, 
                       period1_start: str, period1_end: str,
                       period2_start: str, period2_end: str) -> Dict[str, Any]:
        """
        Compare trends between two time periods
        
        Args:
            series: Input time series
            period1_start, period1_end: First period boundaries
            period2_start, period2_end: Second period boundaries
        
        Returns:
            Comparison results
        """
        try:
            # Extract periods
            period1 = series[period1_start:period1_end]
            period2 = series[period2_start:period2_end]
            
            if period1.empty or period2.empty:
                return {'error': 'One or both periods have no data'}
            
            # Analyze each period
            trend1 = self.detect_trend(period1, method='linear')
            trend2 = self.detect_trend(period2, method='linear')
            
            # Calculate statistics
            stats1 = {
                'mean': float(period1.mean()),
                'median': float(period1.median()),
                'std': float(period1.std()),
                'min': float(period1.min()),
                'max': float(period1.max())
            }
            
            stats2 = {
                'mean': float(period2.mean()),
                'median': float(period2.median()),
                'std': float(period2.std()),
                'min': float(period2.min()),
                'max': float(period2.max())
            }
            
            # Calculate changes
            mean_change = ((stats2['mean'] - stats1['mean']) / stats1['mean'] * 100) if stats1['mean'] != 0 else 0
            
            # Statistical test for difference
            t_stat, p_value = stats.ttest_ind(period1.dropna(), period2.dropna())
            
            return {
                'period1': {
                    'start': period1_start,
                    'end': period1_end,
                    'trend': trend1,
                    'statistics': stats1,
                    'data_points': len(period1)
                },
                'period2': {
                    'start': period2_start,
                    'end': period2_end,
                    'trend': trend2,
                    'statistics': stats2,
                    'data_points': len(period2)
                },
                'comparison': {
                    'mean_change_pct': float(mean_change),
                    'trend_direction_change': trend1.get('direction') != trend2.get('direction'),
                    't_statistic': float(t_stat),
                    'p_value': float(p_value),
                    'significantly_different': p_value < 0.05,
                    'interpretation': 'improved' if mean_change > 0 else 'declined' if mean_change < 0 else 'stable'
                }
            }
        except Exception as e:
            logger.error(f"Error comparing periods: {e}")
            return {'error': str(e)}
    
    def identify_peaks_and_troughs(self, series: pd.Series, 
                                   prominence: float = 0.1) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identify peaks (local maxima) and troughs (local minima) in time series
        
        Args:
            series: Input time series
            prominence: Minimum prominence of peaks/troughs
        
        Returns:
            Dictionary with peaks and troughs information
        """
        try:
            clean_series = series.dropna()
            values = clean_series.values
            
            # Find peaks
            peaks, peak_properties = find_peaks(values, prominence=prominence)
            
            # Find troughs (peaks in inverted series)
            troughs, trough_properties = find_peaks(-values, prominence=prominence)
            
            # Format results
            peak_list = []
            for i, peak_idx in enumerate(peaks):
                peak_list.append({
                    'index': int(peak_idx),
                    'timestamp': clean_series.index[peak_idx],
                    'value': float(values[peak_idx]),
                    'prominence': float(peak_properties['prominences'][i])
                })
            
            trough_list = []
            for i, trough_idx in enumerate(troughs):
                trough_list.append({
                    'index': int(trough_idx),
                    'timestamp': clean_series.index[trough_idx],
                    'value': float(values[trough_idx]),
                    'prominence': float(trough_properties['prominences'][i])
                })
            
            logger.info(f"Identified {len(peak_list)} peaks and {len(trough_list)} troughs")
            
            return {
                'peaks': peak_list,
                'troughs': trough_list,
                'peak_count': len(peak_list),
                'trough_count': len(trough_list),
                'volatility': len(peak_list) + len(trough_list)
            }
        except Exception as e:
            logger.error(f"Error identifying peaks and troughs: {e}")
            return {'peaks': [], 'troughs': [], 'peak_count': 0, 'trough_count': 0}


def analyze_growth_rate(series: pd.Series, periods: int = 1) -> pd.Series:
    """Calculate growth rate over specified periods"""
    return series.pct_change(periods=periods) * 100


def calculate_momentum(series: pd.Series, window: int = 14) -> pd.Series:
    """Calculate momentum indicator"""
    return series.diff(window)


def calculate_rate_of_change(series: pd.Series, window: int = 14) -> pd.Series:
    """Calculate rate of change indicator"""
    return ((series - series.shift(window)) / series.shift(window)) * 100
