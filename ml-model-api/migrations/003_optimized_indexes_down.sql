BEGIN;

-- Drop optimized indexes (rollback for migration 003)

DROP INDEX CONCURRENTLY IF EXISTS idx_prediction_history_date_user;
DROP INDEX CONCURRENTLY IF EXISTS idx_prediction_history_date_label;
DROP INDEX CONCURRENTLY IF EXISTS idx_prediction_history_model_date;
DROP INDEX CONCURRENTLY IF EXISTS idx_prediction_history_success_date;
DROP INDEX CONCURRENTLY IF EXISTS idx_prediction_history_confidence;
DROP INDEX CONCURRENTLY IF EXISTS idx_prediction_history_processing_time;
DROP INDEX CONCURRENTLY IF EXISTS idx_model_performance_date;
DROP INDEX CONCURRENTLY IF EXISTS idx_model_performance_version_date;
DROP INDEX CONCURRENTLY IF EXISTS idx_prediction_history_predictions_gin;

COMMIT;