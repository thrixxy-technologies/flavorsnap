import schedule
import time
import threading
import logging
from typing import List
from etl_handlers import ETLJob, Extractors, Transformers, Loaders
from data_quality import DataQualityChecker

try:
    from monitoring import ETL_JOB_COUNT, ETL_JOB_DURATION, DATA_QUALITY_SCORE, RECORDS_PROCESSED
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

logger = logging.getLogger(__name__)

class DataPipelineOrchestrator:
    """Orchestrates and schedules data pipeline jobs."""
    def __init__(self):
        self.jobs: List[ETLJob] = []
        self._stop_event = threading.Event()
        self._scheduler_thread = None

    def add_job(self, job: ETLJob):
        """Register an ETL job."""
        self.jobs.append(job)

    def run_job(self, job: ETLJob):
        """Execute a specific job and record metrics."""
        start_time = time.time()
        logger.info(f"Orchestrator starting job: {job.name}")
        
        result = job.run()
        
        duration = time.time() - start_time
        status = result.get('status', 'failed')
        
        if METRICS_AVAILABLE:
            ETL_JOB_COUNT.labels(job_name=job.name, status=status).inc()
            ETL_JOB_DURATION.labels(job_name=job.name).observe(duration)
            
            if status == 'success':
                RECORDS_PROCESSED.labels(job_name=job.name).inc(result.get('records_processed', 0))
                DATA_QUALITY_SCORE.labels(job_name=job.name).set(result.get('quality_score', 0.0))

    def run_all_jobs(self):
        """Run all registered jobs sequentially."""
        for job in self.jobs:
            self.run_job(job)

    def start_scheduler(self, interval_minutes: int = 60):
        """Start the scheduler in a background thread."""
        schedule.every(interval_minutes).minutes.do(self.run_all_jobs)
        
        def run_schedule():
            logger.info(f"Data pipeline scheduler started (interval: {interval_minutes}m)")
            while not self._stop_event.is_set():
                schedule.run_pending()
                time.sleep(1)
                
        self._scheduler_thread = threading.Thread(target=run_schedule, daemon=True)
        self._scheduler_thread.start()

    def stop_scheduler(self):
        """Stop the background scheduler."""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._stop_event.set()
            self._scheduler_thread.join()
            logger.info("Data pipeline scheduler stopped")

# Example usage/initialization (can be imported and run from main app)
def init_default_pipeline() -> DataPipelineOrchestrator:
    orchestrator = DataPipelineOrchestrator()
    
    # Example Schema for User Data
    user_schema = {
        'user_id': 'int',
        'age': 'float',
        'score': 'float'
    }
    
    # Initialize components
    quality_checker = DataQualityChecker(schema=user_schema)
    
    # Create an example job
    # Here we define a dummy extractor for demonstration purposes if needed
    def dummy_extractor():
        import pandas as pd
        yield pd.DataFrame({'user_id': [1, 2, 3], 'age': [25.0, 30.0, 35.0], 'score': [0.8, 0.9, 0.7]})
        
    example_job = ETLJob(
        name="daily_user_metrics_sync",
        extractor=dummy_extractor,
        transformer=lambda df: Transformers.clean_missing_values(df),
        loader=lambda df: logger.info(f"Loaded {len(df)} records in dummy loader"),
        quality_checker=quality_checker
    )
    
    orchestrator.add_job(example_job)
    return orchestrator

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pipeline = init_default_pipeline()
    pipeline.run_all_jobs()
