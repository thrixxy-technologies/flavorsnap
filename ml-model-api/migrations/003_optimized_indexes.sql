BEGIN;

-- Additional optimized indexes for better query performance
-- These indexes support the new analytics queries with pagination and filtering

-- Composite indexes for common query patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_history_date_user
ON prediction_history (DATE(created_at), user_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_history_date_label
ON prediction_history (DATE(created_at), label);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_history_model_date
ON prediction_history (model_version, DATE(created_at));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_history_success_date
ON prediction_history (success, DATE(created_at));

-- Partial indexes for nullable columns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_history_confidence
ON prediction_history (confidence)
WHERE confidence IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_history_processing_time
ON prediction_history (processing_time)
WHERE processing_time IS NOT NULL;

-- Indexes for model performance metrics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_performance_date
ON model_performance_metrics (metric_date DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_performance_version_date
ON model_performance_metrics (model_version, metric_date DESC);

-- Index for JSONB queries (if needed for all_predictions)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_history_predictions_gin
ON prediction_history USING GIN (all_predictions)
WHERE all_predictions IS NOT NULL;

COMMIT;