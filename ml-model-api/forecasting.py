"""
Forecasting Module for FlavorSnap
Implements various forecasting models for time series prediction
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class TimeSeriesForecaster:
    """Implements multiple forecasting models"""
    
    def __init__(self):
        self.models = {}
        self.fitted_models = {}
    
    def forecast_arima(self, series: pd.Series, steps: int = 30, 
                      order: Optional[Tuple[int, int, int]] = None) -> Dict[str, Any]:
        """
        ARIMA (AutoRegressive Integrated Moving Average) forecasting
        
        Args:
            series: Input time series
            steps: Number of steps to forecast
            order: ARIMA order (p, d, q). Auto-selected if None
        
        Returns:
            Forecast results with confidence intervals
        """
        try:
            from statsmodels.tsa.arima.model import ARIMA
            from statsmodels.tsa.stattools import adfuller
            
            clean_series = series.dropna()
            if len(clean_series) < 10:
                return {'error': 'Insufficient data for ARIMA', 'forecast': []}
            
            # Auto-select order if not provided
            if order is None:
                order = self._auto_select_arima_order(clean_series)
            
            # Fit ARIMA model
            model = ARIMA(clean_series, order=order)
            fitted_model = model.fit()
            
            # Generate forecast
            forecast_result = fitted_model.forecast(steps=steps)
            forecast_index = pd.date_range(
                start=clean_series.index[-1] + pd.Timedelta(days=1),
                periods=steps,
                freq=pd.infer_freq(clean_series.index) or 'D'
            )
            
            # Get confidence intervals
            forecast_df = fitted_model.get_forecast(steps=steps)
            conf_int = forecast_df.conf_int()
            
            # Store fitted model
            self.fitted_models['arima'] = fitted_model
            
            return {
                'model': 'ARIMA',
                'order': order,
                'forecast': pd.Series(forecast_result.values, index=forecast_index),
                'lower_bound': pd.Series(conf_int.iloc[:, 0].values, index=forecast_index),
                'upper_bound': pd.Series(conf_int.iloc[:, 1].values, index=forecast_index),
                'aic': float(fitted_model.aic),
                'bic': float(fitted_model.bic),
                'historical': clean_series,
                'steps': steps
            }
        except Exception as e:
            logger.error(f"ARIMA forecasting error: {e}")
            return {'error': str(e), 'forecast': []}
    
    def forecast_sarima(self, series: pd.Series, steps: int = 30,
                       order: Optional[Tuple[int, int, int]] = None,
                       seasonal_order: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        """
        SARIMA (Seasonal ARIMA) forecasting
        
        Args:
            series: Input time series
            steps: Number of steps to forecast
            order: ARIMA order (p, d, q)
            seasonal_order: Seasonal order (P, D, Q, s)
        
        Returns:
            Forecast results with confidence intervals
        """
        try:
            from statsmodels.tsa.statespace.sarimax import SARIMAX
            
            clean_series = series.dropna()
            if len(clean_series) < 20:
                return {'error': 'Insufficient data for SARIMA', 'forecast': []}
            
            # Auto-select orders if not provided
            if order is None:
                order = (1, 1, 1)
            if seasonal_order is None:
                seasonal_order = (1, 1, 1, 7)  # Weekly seasonality
            
            # Fit SARIMA model
            model = SARIMAX(clean_series, order=order, seasonal_order=seasonal_order)
            fitted_model = model.fit(disp=False)
            
            # Generate forecast
            forecast_result = fitted_model.forecast(steps=steps)
            forecast_index = pd.date_range(
                start=clean_series.index[-1] + pd.Timedelta(days=1),
                periods=steps,
                freq=pd.infer_freq(clean_series.index) or 'D'
            )
            
            # Get confidence intervals
            forecast_df = fitted_model.get_forecast(steps=steps)
            conf_int = forecast_df.conf_int()
            
            self.fitted_models['sarima'] = fitted_model
            
            return {
                'model': 'SARIMA',
                'order': order,
                'seasonal_order': seasonal_order,
                'forecast': pd.Series(forecast_result.values, index=forecast_index),
                'lower_bound': pd.Series(conf_int.iloc[:, 0].values, index=forecast_index),
                'upper_bound': pd.Series(conf_int.iloc[:, 1].values, index=forecast_index),
                'aic': float(fitted_model.aic),
                'bic': float(fitted_model.bic),
                'historical': clean_series,
                'steps': steps
            }
        except Exception as e:
            logger.error(f"SARIMA forecasting error: {e}")
            return {'error': str(e), 'forecast': []}
    
    def forecast_exponential_smoothing(self, series: pd.Series, steps: int = 30,
                                      seasonal: str = 'add',
                                      seasonal_periods: int = 7) -> Dict[str, Any]:
        """
        Exponential Smoothing (Holt-Winters) forecasting
        
        Args:
            series: Input time series
            steps: Number of steps to forecast
            seasonal: Seasonal component type ('add' or 'mul')
            seasonal_periods: Number of periods in a season
        
        Returns:
            Forecast results
        """
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            
            clean_series = series.dropna()
            if len(clean_series) < seasonal_periods * 2:
                return {'error': 'Insufficient data for Exponential Smoothing', 'forecast': []}
            
            # Fit model
            model = ExponentialSmoothing(
                clean_series,
                seasonal=seasonal,
                seasonal_periods=seasonal_periods,
                trend='add'
            )
            fitted_model = model.fit()
            
            # Generate forecast
            forecast_result = fitted_model.forecast(steps=steps)
            forecast_index = pd.date_range(
                start=clean_series.index[-1] + pd.Timedelta(days=1),
                periods=steps,
                freq=pd.infer_freq(clean_series.index) or 'D'
            )
            
            self.fitted_models['exp_smoothing'] = fitted_model
            
            return {
                'model': 'Exponential_Smoothing',
                'seasonal': seasonal,
                'seasonal_periods': seasonal_periods,
                'forecast': pd.Series(forecast_result.values, index=forecast_index),
                'aic': float(fitted_model.aic) if hasattr(fitted_model, 'aic') else None,
                'historical': clean_series,
                'steps': steps
            }
        except Exception as e:
            logger.error(f"Exponential Smoothing forecasting error: {e}")
            return {'error': str(e), 'forecast': []}
    
    def forecast_prophet(self, series: pd.Series, steps: int = 30,
                        yearly_seasonality: bool = True,
                        weekly_seasonality: bool = True,
                        daily_seasonality: bool = False) -> Dict[str, Any]:
        """
        Facebook Prophet forecasting
        
        Args:
            series: Input time series
            steps: Number of steps to forecast
            yearly_seasonality: Include yearly seasonality
            weekly_seasonality: Include weekly seasonality
            daily_seasonality: Include daily seasonality
        
        Returns:
            Forecast results with confidence intervals
        """
        try:
            from prophet import Prophet
            
            clean_series = series.dropna()
            if len(clean_series) < 10:
                return {'error': 'Insufficient data for Prophet', 'forecast': []}
            
            # Prepare data for Prophet
            df = pd.DataFrame({
                'ds': clean_series.index,
                'y': clean_series.values
            })
            
            # Initialize and fit model
            model = Prophet(
                yearly_seasonality=yearly_seasonality,
                weekly_seasonality=weekly_seasonality,
                daily_seasonality=daily_seasonality,
                interval_width=0.95
            )
            model.fit(df)
            
            # Create future dataframe
            future = model.make_future_dataframe(periods=steps)
            forecast = model.predict(future)
            
            # Extract forecast for future periods only
            forecast_future = forecast.tail(steps)
            
            self.fitted_models['prophet'] = model
            
            return {
                'model': 'Prophet',
                'forecast': pd.Series(
                    forecast_future['yhat'].values,
                    index=pd.to_datetime(forecast_future['ds'])
                ),
                'lower_bound': pd.Series(
                    forecast_future['yhat_lower'].values,
                    index=pd.to_datetime(forecast_future['ds'])
                ),
                'upper_bound': pd.Series(
                    forecast_future['yhat_upper'].values,
                    index=pd.to_datetime(forecast_future['ds'])
                ),
                'trend': pd.Series(
                    forecast_future['trend'].values,
                    index=pd.to_datetime(forecast_future['ds'])
                ),
                'historical': clean_series,
                'steps': steps,
                'full_forecast': forecast
            }
        except ImportError:
            logger.warning("Prophet not installed, skipping")
            return {'error': 'Prophet not installed', 'forecast': []}
        except Exception as e:
            logger.error(f"Prophet forecasting error: {e}")
            return {'error': str(e), 'forecast': []}
    
    def forecast_lstm(self, series: pd.Series, steps: int = 30,
                     lookback: int = 30, epochs: int = 50) -> Dict[str, Any]:
        """
        LSTM (Long Short-Term Memory) neural network forecasting
        
        Args:
            series: Input time series
            steps: Number of steps to forecast
            lookback: Number of past observations to use
            epochs: Training epochs
        
        Returns:
            Forecast results
        """
        try:
            import tensorflow as tf
            from tensorflow import keras
            from sklearn.preprocessing import MinMaxScaler
            
            clean_series = series.dropna()
            if len(clean_series) < lookback + 10:
                return {'error': 'Insufficient data for LSTM', 'forecast': []}
            
            # Normalize data
            scaler = MinMaxScaler()
            scaled_data = scaler.fit_transform(clean_series.values.reshape(-1, 1))
            
            # Prepare sequences
            X, y = [], []
            for i in range(lookback, len(scaled_data)):
                X.append(scaled_data[i-lookback:i, 0])
                y.append(scaled_data[i, 0])
            
            X, y = np.array(X), np.array(y)
            X = X.reshape((X.shape[0], X.shape[1], 1))
            
            # Build LSTM model
            model = keras.Sequential([
                keras.layers.LSTM(50, activation='relu', return_sequences=True, input_shape=(lookback, 1)),
                keras.layers.Dropout(0.2),
                keras.layers.LSTM(50, activation='relu'),
                keras.layers.Dropout(0.2),
                keras.layers.Dense(1)
            ])
            
            model.compile(optimizer='adam', loss='mse')
            
            # Train model
            model.fit(X, y, epochs=epochs, batch_size=32, verbose=0)
            
            # Generate forecast
            forecast_values = []
            current_sequence = scaled_data[-lookback:].reshape(1, lookback, 1)
            
            for _ in range(steps):
                next_pred = model.predict(current_sequence, verbose=0)
                forecast_values.append(next_pred[0, 0])
                current_sequence = np.append(current_sequence[:, 1:, :], next_pred.reshape(1, 1, 1), axis=1)
            
            # Inverse transform
            forecast_values = scaler.inverse_transform(np.array(forecast_values).reshape(-1, 1)).flatten()
            
            forecast_index = pd.date_range(
                start=clean_series.index[-1] + pd.Timedelta(days=1),
                periods=steps,
                freq=pd.infer_freq(clean_series.index) or 'D'
            )
            
            self.fitted_models['lstm'] = {'model': model, 'scaler': scaler, 'lookback': lookback}
            
            return {
                'model': 'LSTM',
                'forecast': pd.Series(forecast_values, index=forecast_index),
                'lookback': lookback,
                'epochs': epochs,
                'historical': clean_series,
                'steps': steps
            }
        except ImportError:
            logger.warning("TensorFlow not installed, skipping LSTM")
            return {'error': 'TensorFlow not installed', 'forecast': []}
        except Exception as e:
            logger.error(f"LSTM forecasting error: {e}")
            return {'error': str(e), 'forecast': []}
    
    def ensemble_forecast(self, series: pd.Series, steps: int = 30,
                         models: Optional[List[str]] = None,
                         weights: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Ensemble forecasting combining multiple models
        
        Args:
            series: Input time series
            steps: Number of steps to forecast
            models: List of models to use (None = all available)
            weights: Weights for each model (None = equal weights)
        
        Returns:
            Combined forecast results
        """
        try:
            if models is None:
                models = ['arima', 'exp_smoothing']
            
            forecasts = {}
            errors = {}
            
            # Generate forecasts from each model
            for model_name in models:
                if model_name == 'arima':
                    result = self.forecast_arima(series, steps)
                elif model_name == 'sarima':
                    result = self.forecast_sarima(series, steps)
                elif model_name == 'exp_smoothing':
                    result = self.forecast_exponential_smoothing(series, steps)
                elif model_name == 'prophet':
                    result = self.forecast_prophet(series, steps)
                else:
                    continue
                
                if 'error' not in result and 'forecast' in result:
                    forecasts[model_name] = result['forecast']
                else:
                    errors[model_name] = result.get('error', 'Unknown error')
            
            if not forecasts:
                return {'error': 'All models failed', 'model_errors': errors}
            
            # Combine forecasts
            if weights is None:
                weights = [1.0 / len(forecasts)] * len(forecasts)
            
            combined_forecast = pd.Series(0, index=list(forecasts.values())[0].index)
            for (model_name, forecast), weight in zip(forecasts.items(), weights):
                combined_forecast += forecast * weight
            
            # Calculate prediction intervals using forecast variance
            forecast_std = pd.Series(0, index=combined_forecast.index)
            for forecast in forecasts.values():
                forecast_std += (forecast - combined_forecast) ** 2
            forecast_std = np.sqrt(forecast_std / len(forecasts))
            
            return {
                'model': 'Ensemble',
                'models_used': list(forecasts.keys()),
                'weights': weights,
                'forecast': combined_forecast,
                'lower_bound': combined_forecast - 1.96 * forecast_std,
                'upper_bound': combined_forecast + 1.96 * forecast_std,
                'individual_forecasts': forecasts,
                'model_errors': errors if errors else None,
                'historical': series.dropna(),
                'steps': steps
            }
        except Exception as e:
            logger.error(f"Ensemble forecasting error: {e}")
            return {'error': str(e), 'forecast': []}
    
    def _auto_select_arima_order(self, series: pd.Series) -> Tuple[int, int, int]:
        """Auto-select ARIMA order using AIC"""
        try:
            from statsmodels.tsa.arima.model import ARIMA
            
            best_aic = np.inf
            best_order = (1, 1, 1)
            
            # Grid search over reasonable parameter ranges
            for p in range(0, 3):
                for d in range(0, 2):
                    for q in range(0, 3):
                        try:
                            model = ARIMA(series, order=(p, d, q))
                            fitted = model.fit()
                            if fitted.aic < best_aic:
                                best_aic = fitted.aic
                                best_order = (p, d, q)
                        except:
                            continue
            
            logger.info(f"Auto-selected ARIMA order: {best_order}")
            return best_order
        except Exception as e:
            logger.warning(f"Auto-selection failed: {e}, using default (1,1,1)")
            return (1, 1, 1)
    
    def evaluate_forecast(self, actual: pd.Series, predicted: pd.Series) -> Dict[str, float]:
        """
        Evaluate forecast accuracy
        
        Args:
            actual: Actual values
            predicted: Predicted values
        
        Returns:
            Dictionary with evaluation metrics
        """
        try:
            # Align series
            common_index = actual.index.intersection(predicted.index)
            if len(common_index) == 0:
                return {'error': 'No overlapping data points'}
            
            actual_aligned = actual.loc[common_index]
            predicted_aligned = predicted.loc[common_index]
            
            # Calculate metrics
            mae = np.mean(np.abs(actual_aligned - predicted_aligned))
            mse = np.mean((actual_aligned - predicted_aligned) ** 2)
            rmse = np.sqrt(mse)
            
            # MAPE (Mean Absolute Percentage Error)
            mape = np.mean(np.abs((actual_aligned - predicted_aligned) / actual_aligned)) * 100
            
            # R-squared
            ss_res = np.sum((actual_aligned - predicted_aligned) ** 2)
            ss_tot = np.sum((actual_aligned - np.mean(actual_aligned)) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            return {
                'mae': float(mae),
                'mse': float(mse),
                'rmse': float(rmse),
                'mape': float(mape),
                'r2': float(r2),
                'data_points': len(common_index)
            }
        except Exception as e:
            logger.error(f"Forecast evaluation error: {e}")
            return {'error': str(e)}


def calculate_forecast_confidence(forecast: pd.Series, historical: pd.Series,
                                 confidence_level: float = 0.95) -> Tuple[pd.Series, pd.Series]:
    """Calculate confidence intervals for forecast"""
    # Calculate historical volatility
    historical_std = historical.std()
    
    # Z-score for confidence level
    from scipy import stats
    z_score = stats.norm.ppf((1 + confidence_level) / 2)
    
    # Calculate intervals
    margin = z_score * historical_std
    lower_bound = forecast - margin
    upper_bound = forecast + margin
    
    return lower_bound, upper_bound


def cross_validate_forecast(series: pd.Series, forecaster: TimeSeriesForecaster,
                           n_splits: int = 5, horizon: int = 7) -> Dict[str, Any]:
    """Perform time series cross-validation"""
    from sklearn.model_selection import TimeSeriesSplit
    
    tscv = TimeSeriesSplit(n_splits=n_splits)
    scores = []
    
    for train_idx, test_idx in tscv.split(series):
        train = series.iloc[train_idx]
        test = series.iloc[test_idx[:horizon]]  # Only forecast 'horizon' steps
        
        # Forecast
        result = forecaster.forecast_arima(train, steps=len(test))
        if 'error' not in result:
            metrics = forecaster.evaluate_forecast(test, result['forecast'])
            scores.append(metrics)
    
    # Average scores
    avg_scores = {}
    if scores:
        for key in scores[0].keys():
            if key != 'error':
                avg_scores[f'avg_{key}'] = np.mean([s[key] for s in scores if key in s])
    
    return {
        'n_splits': n_splits,
        'horizon': horizon,
        'scores': scores,
        'average_scores': avg_scores
    }
