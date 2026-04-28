# Quick Start Guide - Advanced Time Series Analysis

## Installation

```bash
cd flavorsnap/ml-model-api
pip install -r requirements.txt
```

## Start the API

```bash
python3 app.py
```

The API will be available at `http://localhost:5000`

## Quick API Examples

### 1. Get Time Series Data
```bash
curl "http://localhost:5000/analytics/timeseries?start_date=2024-01-01&end_date=2024-12-31&metric=total_requests&aggregation=daily"
```

### 2. Analyze Trend
```bash
curl "http://localhost:5000/analytics/trend?start_date=2024-01-01&end_date=2024-12-31&metric=total_requests&method=linear"
```

### 3. Detect Seasonality
```bash
curl "http://localhost:5000/analytics/seasonality?start_date=2024-01-01&end_date=2024-12-31&metric=total_requests&model=additive"
```

### 4. Forecast Future Values
```bash
curl "http://localhost:5000/analytics/forecast?metric=total_requests&steps=30&model=arima"
```

### 5. Detect Anomalies
```bash
curl "http://localhost:5000/analytics/anomalies?start_date=2024-01-01&end_date=2024-12-31&metric=total_requests&method=zscore&threshold=3.0"
```

### 6. Get Visualization Data
```bash
curl "http://localhost:5000/analytics/visualization?start_date=2024-01-01&end_date=2024-12-31&metrics=total_requests&metrics=avg_confidence"
```

### 7. Get Performance Metrics
```bash
curl "http://localhost:5000/analytics/performance-metrics?start_date=2024-01-01&end_date=2024-12-31"
```

## Python Client Example

```python
import requests

base_url = "http://localhost:5000"

# Analyze trend
response = requests.get(f"{base_url}/analytics/trend", params={
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "metric": "total_requests",
    "method": "linear"
})

trend_data = response.json()
print(f"Trend Direction: {trend_data['trend']['direction']}")
print(f"Trend Strength: {trend_data['trend']['strength']}")

# Forecast
response = requests.get(f"{base_url}/analytics/forecast", params={
    "metric": "total_requests",
    "steps": 30,
    "model": "ensemble"
})

forecast_data = response.json()
print(f"Forecast Model: {forecast_data['model']}")
print(f"Next 30 days forecast: {forecast_data['forecast']['values'][:5]}...")
```

## Generate Visualizations

```bash
python3 visualization_examples.py --dashboard --output-dir ./visualizations
```

This will create 5 visualization files:
- `01_timeseries_trend.png` - Time series with trend line
- `02_seasonality.png` - Seasonal decomposition
- `03_forecast.png` - Forecast with confidence intervals
- `04_anomalies.png` - Anomaly detection
- `05_multi_metric.png` - Multi-metric comparison

## Available Metrics

- `total_requests` - Total number of requests
- `unique_users` - Number of unique users
- `avg_confidence` - Average prediction confidence
- `avg_processing_time` - Average processing time
- `successful_requests` - Number of successful requests
- `failed_requests` - Number of failed requests
- `success_rate` - Success rate percentage
- `failure_rate` - Failure rate percentage

## Available Models

### Trend Analysis Methods
- `linear` - Linear regression
- `polynomial` - Polynomial regression
- `exponential` - Exponential trend
- `moving_average` - Moving average trend

### Forecasting Models
- `arima` - AutoRegressive Integrated Moving Average
- `sarima` - Seasonal ARIMA
- `exp_smoothing` - Exponential Smoothing (Holt-Winters)
- `prophet` - Facebook Prophet (requires prophet package)
- `lstm` - LSTM Neural Network (requires tensorflow)
- `ensemble` - Combines multiple models (recommended)

### Anomaly Detection Methods
- `zscore` - Z-score based detection
- `iqr` - Interquartile Range method
- `isolation_forest` - Isolation Forest algorithm

## Common Parameters

- `start_date` - Start date in YYYY-MM-DD format
- `end_date` - End date in YYYY-MM-DD format
- `metric` - Metric to analyze
- `aggregation` - Time aggregation: `hourly`, `daily`, `weekly`, `monthly`
- `method` - Analysis method
- `model` - Forecasting model
- `steps` - Number of forecast steps
- `threshold` - Anomaly detection threshold

## Testing

Run the test suite:
```bash
python3 test_time_series.py
```

## Documentation

- **Complete Documentation**: `TIME_SERIES_README.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
- **This Quick Start**: `QUICK_START.md`

## Troubleshooting

### Missing Dependencies
```bash
pip install pandas scipy statsmodels scikit-learn
```

### Optional Dependencies
```bash
pip install prophet tensorflow ruptures
```

### Database Connection Issues
Ensure `DATABASE_URL` or `POSTGRES_DSN` environment variable is set:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/flavorsnap"
```

## Support

For detailed documentation, see `TIME_SERIES_README.md`
For implementation details, see `IMPLEMENTATION_SUMMARY.md`
