"""
Test Automation Framework for FlavorSnap
Automated test execution, scheduling, and CI/CD integration
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import schedule
import threading
import requests
from jinja2 import Template
import yaml

logger = logging.getLogger(__name__)


@dataclass
class TestJob:
    """Test job configuration"""
    id: str
    name: str
    description: str
    test_type: str  # unit, integration, performance, security, e2e
    command: List[str]
    working_directory: str
    environment: Dict[str, str] = field(default_factory=dict)
    timeout: int = 300  # seconds
    retry_count: int = 0
    retry_delay: int = 60  # seconds
    schedule: str = ""  # cron-like schedule
    enabled: bool = True
    dependencies: List[str] = field(default_factory=list)
    notifications: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class TestExecution:
    """Test execution result"""
    job_id: str
    execution_id: str
    status: str  # running, passed, failed, cancelled, timeout
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    artifacts: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    error_message: str = ""
    retry_count: int = 0


@dataclass
class AutomationConfig:
    """Automation configuration"""
    max_concurrent_jobs: int = 4
    default_timeout: int = 300
    artifact_retention_days: int = 30
    notification_channels: List[str] = field(default_factory=list)
    ci_integration: Dict[str, Any] = field(default_factory=dict)
    scheduling_enabled: bool = True
    auto_retry: bool = True
    cleanup_enabled: bool = True


class TestAutomationEngine:
    """Advanced test automation engine"""
    
    def __init__(self, config: AutomationConfig):
        self.config = config
        self.jobs = {}
        self.executions = {}
        self.scheduler = schedule
        self.scheduler_thread = None
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent_jobs)
        self.running_jobs = {}
        self.stop_event = threading.Event()
        
        # Artifact management
        self.artifact_dir = Path("test_artifacts")
        self.artifact_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self._load_jobs()
        
        # Start scheduler
        if config.scheduling_enabled:
            self._start_scheduler()
    
    def _load_jobs(self):
        """Load test jobs from configuration files"""
        job_files = [
            "test_jobs.yaml",
            "test_jobs.json",
            "config/test_jobs.yaml"
        ]
        
        for job_file in job_files:
            if Path(job_file).exists():
                try:
                    with open(job_file) as f:
                        if job_file.endswith('.yaml') or job_file.endswith('.yml'):
                            data = yaml.safe_load(f)
                        else:
                            data = json.load(f)
                    
                    for job_data in data.get('jobs', []):
                        job = TestJob(**job_data)
                        self.jobs[job.id] = job
                        logger.info(f"Loaded test job: {job.name}")
                        
                except Exception as e:
                    logger.error(f"Failed to load jobs from {job_file}: {e}")
        
        # Create default jobs if none found
        if not self.jobs:
            self._create_default_jobs()
    
    def _create_default_jobs(self):
        """Create default test jobs"""
        default_jobs = [
            TestJob(
                id="unit_tests",
                name="Unit Tests",
                description="Run all unit tests",
                test_type="unit",
                command=[sys.executable, "-m", "pytest", "tests/unit", "-v"],
                working_directory=".",
                schedule="0 */6 * * *",  # Every 6 hours
                artifacts=["reports/unit_tests.xml", "reports/unit_tests.html"]
            ),
            TestJob(
                id="integration_tests",
                name="Integration Tests",
                description="Run integration tests",
                test_type="integration",
                command=[sys.executable, "-m", "pytest", "tests/integration", "-v"],
                working_directory=".",
                schedule="0 2 * * *",  # Daily at 2 AM
                dependencies=["unit_tests"],
                artifacts=["reports/integration_tests.xml", "reports/integration_tests.html"]
            ),
            TestJob(
                id="performance_tests",
                name="Performance Tests",
                description="Run performance benchmarks",
                test_type="performance",
                command=[sys.executable, "-m", "pytest", "tests/performance", "-v"],
                working_directory=".",
                schedule="0 3 * * 0",  # Weekly on Sunday at 3 AM
                artifacts=["reports/performance_tests.json", "reports/performance_tests.html"]
            ),
            TestJob(
                id="security_tests",
                name="Security Tests",
                description="Run security vulnerability tests",
                test_type="security",
                command=[sys.executable, "-m", "pytest", "tests/security", "-v"],
                working_directory=".",
                schedule="0 4 * * *",  # Daily at 4 AM
                artifacts=["reports/security_tests.xml", "reports/security_tests.html"]
            ),
            TestJob(
                id="api_tests",
                name="API Tests",
                description="Run API endpoint tests",
                test_type="e2e",
                command=[sys.executable, "-m", "pytest", "tests/api", "-v"],
                working_directory=".",
                schedule="0 */4 * * *",  # Every 4 hours
                artifacts=["reports/api_tests.xml", "reports/api_tests.html"]
            )
        ]
        
        for job in default_jobs:
            self.jobs[job.id] = job
            logger.info(f"Created default test job: {job.name}")
    
    def _start_scheduler(self):
        """Start the job scheduler"""
        def run_scheduler():
            while not self.stop_event.is_set():
                self.scheduler.run_pending()
                time.sleep(60)  # Check every minute
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Test job scheduler started")
    
    def add_job(self, job: TestJob):
        """Add a new test job"""
        self.jobs[job.id] = job
        
        # Schedule the job if it has a schedule
        if job.schedule and self.config.scheduling_enabled:
            try:
                # Parse cron-like schedule
                self._schedule_job(job)
            except Exception as e:
                logger.error(f"Failed to schedule job {job.id}: {e}")
        
        logger.info(f"Added test job: {job.name}")
    
    def _schedule_job(self, job: TestJob):
        """Schedule a job using cron-like syntax"""
        # Simple cron parser for common patterns
        if job.schedule == "hourly":
            self.scheduler.every().hour.do(self._run_scheduled_job, job.id)
        elif job.schedule == "daily":
            self.scheduler.every().day.at("00:00").do(self._run_scheduled_job, job.id)
        elif job.schedule.startswith("0 */"):
            # Every N hours
            hours = job.schedule.split()[1]
            self.scheduler.every(int(hours)).hours.do(self._run_scheduled_job, job.id)
        elif job.schedule.startswith("0 2"):
            # Daily at specific time
            self.scheduler.every().day.at("02:00").do(self._run_scheduled_job, job.id)
        else:
            logger.warning(f"Unsupported schedule format: {job.schedule}")
    
    def _run_scheduled_job(self, job_id: str):
        """Run a scheduled job"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            if job.enabled:
                asyncio.create_task(self.execute_job(job_id))
    
    async def execute_job(self, job_id: str, execution_context: Dict[str, Any] = None) -> TestExecution:
        """Execute a test job"""
        if job_id not in self.jobs:
            raise ValueError(f"Job not found: {job_id}")
        
        job = self.jobs[job_id]
        
        # Check dependencies
        if job.dependencies:
            for dep_id in job.dependencies:
                if not await self._check_dependency(dep_id):
                    raise ValueError(f"Dependency not satisfied: {dep_id}")
        
        # Check if job is already running
        if job_id in self.running_jobs:
            logger.warning(f"Job {job_id} is already running")
            return self.running_jobs[job_id]
        
        execution_id = f"{job_id}_{int(time.time())}"
        execution = TestExecution(
            job_id=job_id,
            execution_id=execution_id,
            status="running",
            start_time=datetime.now()
        )
        
        self.executions[execution_id] = execution
        self.running_jobs[job_id] = execution
        
        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(job.environment)
            if execution_context:
                env.update(execution_context.get('environment', {}))
            
            # Prepare working directory
            work_dir = Path(job.working_directory).resolve()
            work_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Executing job {job_id} (execution {execution_id})")
            
            # Run the command
            process = await asyncio.create_subprocess_exec(
                *job.command,
                cwd=work_dir,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=job.timeout
                )
                
                execution.exit_code = process.returncode
                execution.stdout = stdout.decode('utf-8')
                execution.stderr = stderr.decode('utf-8')
                
            except asyncio.TimeoutError:
                process.kill()
                execution.status = "timeout"
                execution.error_message = f"Job timed out after {job.timeout} seconds"
                logger.error(f"Job {job_id} timed out")
            
        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            logger.error(f"Job {job_id} failed: {e}")
        
        finally:
            execution.end_time = datetime.now()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            
            # Determine final status
            if execution.status == "running":
                if execution.exit_code == 0:
                    execution.status = "passed"
                else:
                    execution.status = "failed"
                    execution.error_message = f"Process exited with code {execution.exit_code}"
            
            # Collect artifacts
            await self._collect_artifacts(job, execution)
            
            # Calculate metrics
            execution.metrics = self._calculate_metrics(execution)
            
            # Remove from running jobs
            if job_id in self.running_jobs:
                del self.running_jobs[job_id]
            
            # Send notifications
            await self._send_notifications(job, execution)
            
            # Retry if failed and auto-retry is enabled
            if (execution.status == "failed" and 
                self.config.auto_retry and 
                execution.retry_count < job.retry_count):
                
                logger.info(f"Retrying job {job_id} (attempt {execution.retry_count + 1})")
                execution.retry_count += 1
                
                await asyncio.sleep(job.retry_delay)
                return await self.execute_job(job_id, execution_context)
            
            logger.info(f"Job {job_id} completed: {execution.status}")
            return execution
    
    async def _check_dependency(self, dep_id: str) -> bool:
        """Check if a dependency job has passed"""
        # Get latest execution of dependency
        dep_executions = [
            exec for exec in self.executions.values()
            if exec.job_id == dep_id
        ]
        
        if not dep_executions:
            return False
        
        latest_execution = max(dep_executions, key=lambda x: x.start_time)
        return latest_execution.status == "passed"
    
    async def _collect_artifacts(self, job: TestJob, execution: TestExecution):
        """Collect job artifacts"""
        for artifact_pattern in job.artifacts:
            try:
                # Find matching files
                artifact_files = list(Path(".").glob(artifact_pattern))
                
                for artifact_file in artifact_files:
                    if artifact_file.exists():
                        # Copy to artifact directory
                        artifact_name = f"{execution.execution_id}_{artifact_file.name}"
                        artifact_path = self.artifact_dir / artifact_name
                        
                        import shutil
                        shutil.copy2(artifact_file, artifact_path)
                        
                        execution.artifacts[artifact_file.name] = str(artifact_path)
                        logger.debug(f"Collected artifact: {artifact_path}")
                        
            except Exception as e:
                logger.error(f"Failed to collect artifact {artifact_pattern}: {e}")
    
    def _calculate_metrics(self, execution: TestExecution) -> Dict[str, float]:
        """Calculate execution metrics"""
        metrics = {
            "duration": execution.duration,
            "exit_code": execution.exit_code,
            "stdout_length": len(execution.stdout),
            "stderr_length": len(execution.stderr),
            "artifact_count": len(execution.artifacts)
        }
        
        # Parse test results from stdout if available
        if "passed" in execution.stdout.lower():
            try:
                # Extract test count from pytest output
                lines = execution.stdout.split('\n')
                for line in lines:
                    if 'passed' in line and 'failed' in line:
                        # Parse "X passed, Y failed" format
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'passed' and i > 0:
                                metrics["tests_passed"] = float(parts[i-1])
                            elif part == 'failed' and i > 0:
                                metrics["tests_failed"] = float(parts[i-1])
                        break
            except Exception:
                pass
        
        return metrics
    
    async def _send_notifications(self, job: TestJob, execution: TestExecution):
        """Send job execution notifications"""
        if not job.notifications:
            return
        
        # Prepare notification data
        notification_data = {
            "job_name": job.name,
            "job_id": job.id,
            "execution_id": execution.execution_id,
            "status": execution.status,
            "duration": execution.duration,
            "start_time": execution.start_time.isoformat(),
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "error_message": execution.error_message,
            "metrics": execution.metrics,
            "artifacts": list(execution.artifacts.keys())
        }
        
        # Send to configured channels
        for channel in job.notifications.get('channels', []):
            try:
                if channel == "slack":
                    await self._send_slack_notification(notification_data, job.notifications.get('slack', {}))
                elif channel == "email":
                    await self._send_email_notification(notification_data, job.notifications.get('email', {}))
                elif channel == "webhook":
                    await self._send_webhook_notification(notification_data, job.notifications.get('webhook', {}))
                    
            except Exception as e:
                logger.error(f"Failed to send {channel} notification: {e}")
    
    async def _send_slack_notification(self, data: Dict[str, Any], config: Dict[str, Any]):
        """Send Slack notification"""
        webhook_url = config.get('webhook_url')
        if not webhook_url:
            return
        
        # Determine color based on status
        color_map = {
            "passed": "good",
            "failed": "danger",
            "timeout": "warning",
            "cancelled": "warning"
        }
        color = color_map.get(data["status"], "warning")
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"Test Job {data['status'].upper()}: {data['job_name']}",
                "fields": [
                    {"title": "Job ID", "value": data["job_id"], "short": True},
                    {"title": "Execution ID", "value": data["execution_id"], "short": True},
                    {"title": "Duration", "value": f"{data['duration']:.2f}s", "short": True},
                    {"title": "Status", "value": data["status"].upper(), "short": True}
                ]
            }]
        }
        
        if data["error_message"]:
            payload["attachments"][0]["fields"].append({
                "title": "Error",
                "value": data["error_message"],
                "short": False
            })
        
        if data["metrics"]:
            metrics_text = []
            for key, value in data["metrics"].items():
                metrics_text.append(f"{key}: {value}")
            payload["attachments"][0]["fields"].append({
                "title": "Metrics",
                "value": "\n".join(metrics_text),
                "short": False
            })
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status != 200:
                    logger.error(f"Slack notification failed: {response.status}")
    
    async def _send_email_notification(self, data: Dict[str, Any], config: Dict[str, Any]):
        """Send email notification"""
        # Placeholder for email notification
        logger.info(f"Email notification for {data['job_name']}: {data['status']}")
    
    async def _send_webhook_notification(self, data: Dict[str, Any], config: Dict[str, Any]):
        """Send webhook notification"""
        webhook_url = config.get('url')
        if not webhook_url:
            return
        
        headers = config.get('headers', {})
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=data, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Webhook notification failed: {response.status}")
    
    async def run_all_jobs(self, job_type: str = None, tags: List[str] = None) -> List[TestExecution]:
        """Run all jobs (optionally filtered by type or tags)"""
        jobs_to_run = []
        
        for job in self.jobs.values():
            if not job.enabled:
                continue
            
            if job_type and job.test_type != job_type:
                continue
            
            if tags and not any(tag in job.tags for tag in tags):
                continue
            
            jobs_to_run.append(job)
        
        # Execute jobs concurrently
        tasks = []
        for job in jobs_to_run:
            task = asyncio.create_task(self.execute_job(job.id))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        executions = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Job execution failed: {result}")
            else:
                executions.append(result)
        
        return executions
    
    def get_job_status(self, job_id: str) -> Optional[TestExecution]:
        """Get current status of a job"""
        return self.running_jobs.get(job_id)
    
    def get_execution_history(self, job_id: str = None, limit: int = 50) -> List[TestExecution]:
        """Get execution history"""
        executions = list(self.executions.values())
        
        if job_id:
            executions = [exec for exec in executions if exec.job_id == job_id]
        
        # Sort by start time (newest first)
        executions.sort(key=lambda x: x.start_time, reverse=True)
        
        return executions[:limit]
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job"""
        if job_id in self.running_jobs:
            execution = self.running_jobs[job_id]
            execution.status = "cancelled"
            execution.end_time = datetime.now()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            
            del self.running_jobs[job_id]
            logger.info(f"Cancelled job {job_id}")
            return True
        
        return False
    
    def cleanup_executions(self, days: int = None):
        """Clean up old execution records and artifacts"""
        if days is None:
            days = self.config.artifact_retention_days
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Clean up execution records
        old_executions = [
            exec_id for exec_id, exec in self.executions.items()
            if exec.start_time < cutoff_date
        ]
        
        for exec_id in old_executions:
            del self.executions[exec_id]
        
        # Clean up artifact files
        for artifact_file in self.artifact_dir.glob("*"):
            try:
                file_time = datetime.fromtimestamp(artifact_file.stat().st_mtime)
                if file_time < cutoff_date:
                    artifact_file.unlink()
                    logger.debug(f"Cleaned up old artifact: {artifact_file}")
            except Exception as e:
                logger.error(f"Failed to clean up artifact {artifact_file}: {e}")
        
        logger.info(f"Cleaned up {len(old_executions)} old execution records")
    
    def generate_automation_report(self, output_path: str = "reports/automation_report.json"):
        """Generate automation report"""
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total_jobs": len(self.jobs),
            "enabled_jobs": len([j for j in self.jobs.values() if j.enabled]),
            "running_jobs": len(self.running_jobs),
            "total_executions": len(self.executions),
            "job_summary": {},
            "execution_trends": self._calculate_execution_trends(),
            "recommendations": self._generate_automation_recommendations()
        }
        
        # Job summary
        for job_id, job in self.jobs.items():
            job_executions = [
                exec for exec in self.executions.values()
                if exec.job_id == job_id
            ]
            
            if job_executions:
                latest = max(job_executions, key=lambda x: x.start_time)
                passed_count = len([e for e in job_executions if e.status == "passed"])
                total_count = len(job_executions)
                
                report_data["job_summary"][job_id] = {
                    "name": job.name,
                    "type": job.test_type,
                    "enabled": job.enabled,
                    "last_execution": latest.start_time.isoformat(),
                    "last_status": latest.status,
                    "total_executions": total_count,
                    "success_rate": (passed_count / total_count * 100) if total_count > 0 else 0,
                    "average_duration": sum(e.duration for e in job_executions) / total_count
                }
        
        # Save report
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"Automation report generated: {output_file}")
        return str(output_file)
    
    def _calculate_execution_trends(self) -> Dict[str, Any]:
        """Calculate execution trends"""
        # Get last 7 days of executions
        cutoff_date = datetime.now() - timedelta(days=7)
        recent_executions = [
            exec for exec in self.executions.values()
            if exec.start_time >= cutoff_date
        ]
        
        if not recent_executions:
            return {}
        
        # Group by day
        daily_stats = {}
        for exec in recent_executions:
            day = exec.start_time.date().isoformat()
            
            if day not in daily_stats:
                daily_stats[day] = {"total": 0, "passed": 0, "failed": 0}
            
            daily_stats[day]["total"] += 1
            if exec.status == "passed":
                daily_stats[day]["passed"] += 1
            elif exec.status == "failed":
                daily_stats[day]["failed"] += 1
        
        return daily_stats
    
    def _generate_automation_recommendations(self) -> List[str]:
        """Generate automation improvement recommendations"""
        recommendations = []
        
        # Analyze job success rates
        for job_id, job in self.jobs.items():
            job_executions = [
                exec for exec in self.executions.values()
                if exec.job_id == job_id
            ]
            
            if len(job_executions) >= 10:  # Only analyze jobs with sufficient history
                passed_count = len([e for e in job_executions if e.status == "passed"])
                success_rate = passed_count / len(job_executions)
                
                if success_rate < 0.8:
                    recommendations.append(
                        f"Improve reliability of job '{job.name}' (success rate: {success_rate:.1%})"
                    )
                
                # Check average duration
                avg_duration = sum(e.duration for e in job_executions) / len(job_executions)
                if avg_duration > job.timeout * 0.8:
                    recommendations.append(
                        f"Consider optimizing performance of job '{job.name}' (avg duration: {avg_duration:.1f}s)"
                    )
        
        # General recommendations
        if len(self.running_jobs) > self.config.max_concurrent_jobs * 0.8:
            recommendations.append("Consider increasing max_concurrent_jobs or optimizing job scheduling")
        
        if len(self.executions) > 1000:
            recommendations.append("Consider implementing execution cleanup policies")
        
        return recommendations
    
    def stop(self):
        """Stop the automation engine"""
        self.stop_event.set()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        self.executor.shutdown(wait=True)
        
        logger.info("Test automation engine stopped")


# Global automation engine instance
automation_engine = None


def initialize_automation(config: AutomationConfig) -> TestAutomationEngine:
    """Initialize global automation engine"""
    global automation_engine
    automation_engine = TestAutomationEngine(config)
    return automation_engine


def get_automation_engine() -> Optional[TestAutomationEngine]:
    """Get global automation engine instance"""
    return automation_engine
