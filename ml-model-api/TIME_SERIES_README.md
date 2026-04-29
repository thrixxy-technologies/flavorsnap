# Advanced Time Series Analysis for FlavorSnap

## Overview

This module provides comprehensive time series analysis capabilities for the FlavorSnap ML API, including trend analysis, seasonality detection, forecasting, and anomaly detection.

## Features

### 1. Time Series Preprocessing (`time_series.py`)

#### TimeSeriesPreprocessor
- **Data Loading**: Load time series data from database with flexible aggregation
- **Missing Value Handling**: Multiple strategies (forward fill, backward fill, interpolation, mean, median)
- **Outlier Detection**: Z-score, IQR, and isolation forest methods
- **Time Feature Engineering**: Extract hour, day, week, month, cyclical features
- **Smoothing**: Moving average, exponential smoothing, Savitzky-Golay filter
- **Resampling**: Convert between different time frequencies
- **Normalization**: Min-max, z-score, and robust scaling

#### TimeSeriesDecomposer
- **Decomposition**: Separate time series into trend, seasonal, and residual components
- **Auto-detection**: Automatically detect seasonal periods using autocorrelation

### 2. Trend Analysis (`trend_analysis.py`)

#### TrendAnalyzer
- **Trend Detection**: Linear, polynomial, exponential, and moving average methods
- **Change Point Detection**: Identify significant shifts in trends
- **Trend Strength**: Calculate multiple measures of trend strength
- **Period Comparison**: Compare trends between different time periods
- **Peaks and Troughs**: Identify local maxima and minima
- **Growth Rate Analysis**: Calculate momentum and rate of change

### 3. Forecasting (`forecasting.py`)

#### TimeSeriesForecaster
- **ARIMA**: AutoRegressive Integrated Moving Average with auto-parameter selection
- **SARIMA**: Seasonal ARIMA for data with seasonality
- **Exponential Smoothing**: Holt-Winters method for trend and seasonality
- **Prophet**: Facebook's Prophet for robust forecasting with holidays
- **LSTM**: Deep learning approach for complex patterns
- **Ensemble**: Combine multiple models for improved accuracy
- **Evaluation**: MAE, MSE, RMSE, MAPE, R² metrics
- **Cross-validation**: Time series cross-validation for model validation

### 4. Analytics Integration (`analytics.py`)

Enhanced AnalyticsAPI with time series capabilities:
- Comprehensive time series data retrieval
- Trend analysis with multiple methods
- Seasonality detection and decomposition
- Multi-model forecasting
- Anomaly detection
- Visualization-ready data formatting
- Performance metrics with trends

## API Endpoints

### Time Series Data
```
GET /analytics/timeseries
Parameters:
  - start_date: Start date (YYYY-MM-DD)
  - end_date: End date (YYYY-MM-DD)
  - aggregation: hourly|daily|weekly|monthly (default: daily)
  - metric: Metric to analyze (default: total_requests)

Response:
{
  "data": {...},
  "timestamps": [...],
  "statistics": {...},
  "outliers": {...},
  "aggregation": "daily",
  "metric": "total_requests"
}
```

### Trend Analysis
```
GET /analytics/trend
Parameters:
  - start_date: Start date
  - end_date: End date
  - metric: Metric to analyze
  - method: linear|polynomial|exponential|moving_average

Response:
{
  "metric": "total_requests",
  "trend": {
    "direction": "increasing",
    "strength": 0.85,
    "slope": 12.5,
    "r_squared": 0.85,
    "trend_line": {...}
  },
  "strength": {...},
  "change_points": [...],
  "peaks_and_troughs": {...}
}
```

### Seasonality Detection
```
GET /analytics/seasonality
Parameters:
  - start_date: Start date
  - end_date: End date
  - metric: Metric to analyze
  - model: additive|multiplicative
  - period: Seasonal period (auto-detected if not provided)

Response:
{
  "metric": "total_requests",
  "model": "additive",
  "period": 7,
  "seasonality_strength": 0.65,
  "components": {
    "trend": {...},
    "seasonal": {...},
    "residual": {...}
  }
}
```

### Forecasting
```
GET /analytics/forecast
Parameters:
  - metric: Metric to forecast
  - steps: Number of steps to forecast (default: 30)
  - model: arima|sarima|exp_smoothing|prophet|ensemble
  - start_date: Historical data start
  - end_date: Historical data end

Response:
{
  "metric": "total_requests",
  "model": "ARIMA",
  "steps": 30,
  "forecast": {
    "values": [...],
    "timestamps": [...]
  },
  "lower_bound": {...},
  "upper_bound": {...},
  "historical": {...}
}
```

### Anomaly Detection
```
GET /analytics/anomalies
Parameters:
  - start_date: Start date
  - end_date: End date
  - metric: Metric to analyze
  - method: zscore|iqr|isolation_forest
  - threshold: Detection threshold (default: 3.0)

Response:
{
  "metric": "total_requests",
  "method": "zscore",
  "total_anomalies": 5,
  "anomaly_rate": 2.5,
  "anomalies": [
    {
      "timestamp": "2024-01-15T00:00:00",
      "value": 1500,
      "expected_range": {...},
      "deviation": 3.5
    }
  ],
  "statistics": {...}
}
```

### Visualization Data
```
GET /analytics/visualization
Parameters:
  - start_date: Start date
  - end_date: End date
  - metrics: List of metrics (can be repeated)

Response:
{
  "timestamps": [...],
  "metrics": {
    "total_requests": {
      "raw": [...],
      "smoothed": [...],
      "trend": [...],
      "statistics": {...},
      "trend_direction": "increasing"
    }
  }
}
```

### Performance Metrics
```
GET /analytics/performance-metrics
Parameters:
  - start_date: Start date
  - end_date: End date

Response:
{
  "period": {...},
  "metrics": {
    "total_requests": {
      "current_value": 1250,
      "mean": 1100,
      "trend_direction": "increasing",
      "trend_strength": 0.75,
      "change_percentage": 15.5,
      "is_improving": true
    }
  }
}
```

## Usage Examples

### Python Client Example

```python
import requests

base_url = "http://localhost:5000"

# Get time series data
response = requests.get(f"{base_url}/analytics/timeseries", params={
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "aggregation": "daily",
    "metric": "total_requests"
})
data = response.json()

# Analyze trends
response = requests.get(f"{base_url}/analytics/trend", params={
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "metric": "total_requests",
    "method": "linear"
})
trend = response.json()

# Forecast future values
response = requests.get(f"{base_url}/analytics/forecast", params={
    "metric": "total_requests",
    "steps": 30,
    "model": "arima"
})
forecast = response.json()

# Detect anomalies
response = requests.get(f"{base_url}/analytics/anomalies", params={
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "metric": "total_requests",
    "method": "zscore",
    "threshold": 3.0
})
anomalies = response.json()
```

### JavaScript/Frontend Example

```javascript
// Fetch and visualize time series data
async function fetchTimeSeriesData() {
  const response = await fetch('/analytics/timeseries?' + new URLSearchParams({
    start_date: '2024-01-01',
    end_date: '2024-12-31',
    aggregation: 'daily',
    metric: 'total_requests'
  }));
  
  const data = await response.json();
  
  // Use with Chart.js or similar
  const chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.timestamps,
      datasets: [{
        label: 'Total Requests',
        data: Object.values(data.data)
      }]
    }
  });
}

// Get forecast
async function getForecast() {
  const response = await fetch('/analytics/forecast?' + new URLSearchParams({
    metric: 'total_requests',
    steps: 30,
    model: 'ensemble'
  }));
  
  const forecast = await response.json();
  
  // Visualize forecast with confidence intervals
  plotForecast(forecast);
}
```

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure database is configured with prediction_history table

3. Start the Flask application:
```bash
python app.py
```

## Dependencies

- **pandas**: Data manipulation and time series handling
- **numpy**: Numerical computations
- **scipy**: Statistical functions
- **statsmodels**: ARIMA, SARIMA, seasonal decomposition
- **scikit-learn**: Machine learning utilities
- **prophet**: Facebook Prophet forecasting (optional)
- **tensorflow**: LSTM neural networks (optional)
- **ruptures**: Change point detection (optional)

## Performance Considerations

1. **Data Volume**: For large datasets, consider:
   - Using aggregation to reduce data points
   - Implementing caching for frequently accessed analyses
   - Running heavy computations asynchronously

2. **Model Selection**:
   - ARIMA/SARIMA: Good for < 10,000 points
   - Prophet: Handles missing data and outliers well
   - LSTM: Best for complex patterns but requires more data
   - Ensemble: Most robust but slower

3. **Caching**: Consider caching:
   - Preprocessed time series data
   - Trend analysis results
   - Forecast results (with TTL)

## Best Practices

1. **Data Quality**:
   - Always check for missing values
   - Handle outliers appropriately
   - Validate date ranges

2. **Model Selection**:
   - Start with simple models (ARIMA)
   - Use ensemble for production
   - Validate with cross-validation

3. **Forecasting**:
   - Don't forecast too far into the future
   - Always provide confidence intervals
   - Re-train models regularly

4. **Anomaly Detection**:
   - Adjust thresholds based on domain knowledge
   - Combine multiple detection methods
   - Investigate detected anomalies

## Troubleshooting

### Common Issues

1. **Insufficient Data Error**:
   - Ensure at least 30 data points for basic analysis
   - Use longer time periods for seasonal analysis

2. **Model Fitting Failures**:
   - Check for non-stationary data
   - Try different model parameters
   - Use ensemble method as fallback

3. **Slow Performance**:
   - Reduce data points through aggregation
   - Use simpler models
   - Implement caching

## Future Enhancements

- [ ] Real-time streaming analysis
- [ ] Multi-variate time series analysis
- [ ] Automated model selection
- [ ] Advanced visualization dashboards
- [ ] Alert system for anomalies
- [ ] Model performance monitoring
- [ ] A/B testing for forecasting models

## Contributing

When adding new features:
1. Follow existing code structure
2. Add comprehensive docstrings
3. Include error handling
4. Add tests
5. Update this documentation

## License

Part of the FlavorSnap project.
