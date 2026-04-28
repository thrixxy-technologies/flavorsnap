"""
A/B Testing Framework for FlavorSnap Recommendation System

This module provides comprehensive A/B testing capabilities for
testing different recommendation algorithms, configurations, and strategies.
"""

import logging
import uuid
import hashlib
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json
import numpy as np
from enum import Enum
import statistics
from scipy import stats
from db_config import get_connection

logger = logging.getLogger(__name__)

class TestStatus(Enum):
    """A/B test status"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class MetricType(Enum):
    """Metric types for A/B testing"""
    CLICK_THROUGH_RATE = "ctr"
    CONVERSION_RATE = "conversion_rate"
    ENGAGEMENT_TIME = "engagement_time"
    USER_SATISFACTION = "user_satisfaction"
    RECOMMENDATION_ACCURACY = "accuracy"
    DIVERSITY_SCORE = "diversity"
    NOVELTY_SCORE = "novelty"
    REVENUE_PER_USER = "revenue_per_user"

@dataclass
class TestVariant:
    """A/B test variant configuration"""
    variant_id: str
    name: str
    description: str
    configuration: Dict[str, Any]
    traffic_allocation: float  # 0.0 to 1.0
    is_control: bool = False

@dataclass
class ABTest:
    """A/B test configuration"""
    test_id: str
    name: str
    description: str
    hypothesis: str
    start_time: datetime
    end_time: datetime
    status: TestStatus
    variants: List[TestVariant]
    target_metrics: List[MetricType]
    sample_size: int
    confidence_level: float = 0.95
    minimum_detectable_effect: float = 0.05
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class TestEvent:
    """A/B test event data"""
    test_id: str
    variant_id: str
    user_id: str
    session_id: str
    event_type: str  # 'impression', 'click', 'conversion', 'engagement'
    timestamp: datetime
    metrics: Dict[str, float]
    metadata: Dict[str, Any]

@dataclass
class TestResult:
    """A/B test statistical results"""
    test_id: str
    variant_id: str
    metric_name: str
    control_value: float
    variant_value: float
    absolute_difference: float
    relative_difference: float
    p_value: float
    confidence_interval: Tuple[float, float]
    statistical_significance: bool
    sample_size: int
    power: float

@dataclass
class ABTestConfig:
    """Configuration for A/B testing system"""
    # Test settings
    max_concurrent_tests: int = 10
    default_test_duration_days: int = 14
    minimum_sample_size: int = 1000
    default_confidence_level: float = 0.95
    
    # Traffic allocation
    enable_uniform_allocation: bool = True
    allow_user_reassignment: bool = False
    assignment_cache_duration_hours: int = 24
    
    # Statistical settings
    multiple_testing_correction: str = "bonferroni"  # bonferroni, holm, none
    early_stopping_enabled: bool = True
    early_stopping_looks: int = 5
    
    # Performance settings
    enable_async_processing: bool = True
    batch_size: int = 1000
    cache_size: int = 10000

class ABTestingFramework:
    """Main A/B testing framework for recommendations"""
    
    def __init__(self, config: ABTestConfig = None, db_connection=None):
        self.config = config or ABTestConfig()
        self.db_connection = db_connection or get_connection()
        
        # Test management
        self.active_tests: Dict[str, ABTest] = {}
        self.user_assignments: Dict[str, Dict[str, str]] = {}  # user_id -> test_id -> variant_id
        self.assignment_cache: Dict[str, Tuple[str, datetime]] = {}  # user_hash -> (variant_id, expiry)
        
        # Event processing
        self.event_queue = []
        self.metric_aggregators: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        
        # Statistical analysis
        self.statistical_calculators = {
            MetricType.CLICK_THROUGH_RATE: self._calculate_proportion_metrics,
            MetricType.CONVERSION_RATE: self._calculate_proportion_metrics,
            MetricType.ENGAGEMENT_TIME: self._calculate_continuous_metrics,
            MetricType.USER_SATISFACTION: self._calculate_continuous_metrics,
            MetricType.RECOMMENDATION_ACCURACY: self._calculate_continuous_metrics,
            MetricType.DIVERSITY_SCORE: self._calculate_continuous_metrics,
            MetricType.NOVELTY_SCORE: self._calculate_continuous_metrics,
            MetricType.REVENUE_PER_USER: self._calculate_continuous_metrics
        }
        
        self._init_database()
        self._load_active_tests()
    
    def _init_database(self):
        """Initialize A/B testing database tables"""
        if not self.db_connection:
            logger.warning("No database connection available for A/B testing")
            return
            
        try:
            cursor = self.db_connection.cursor()
            
            # A/B tests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ab_tests (
                    test_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    hypothesis TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    status TEXT,
                    variants TEXT,
                    target_metrics TEXT,
                    sample_size INTEGER,
                    confidence_level REAL,
                    minimum_detectable_effect REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Test assignments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT,
                    user_id TEXT,
                    variant_id TEXT,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    context TEXT,
                    UNIQUE(test_id, user_id)
                )
            """)
            
            # Test events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT,
                    variant_id TEXT,
                    user_id TEXT,
                    session_id TEXT,
                    event_type TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metrics TEXT,
                    metadata TEXT
                )
            """)
            
            # Test results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_id TEXT,
                    variant_id TEXT,
                    metric_name TEXT,
                    control_value REAL,
                    variant_value REAL,
                    absolute_difference REAL,
                    relative_difference REAL,
                    p_value REAL,
                    confidence_interval_lower REAL,
                    confidence_interval_upper REAL,
                    statistical_significance BOOLEAN,
                    sample_size INTEGER,
                    power REAL,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.db_connection.commit()
            logger.info("A/B testing database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize A/B testing database: {e}")
    
    def _load_active_tests(self):
        """Load active tests from database"""
        try:
            if not self.db_connection:
                return
                
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                SELECT test_id, name, description, hypothesis, start_time, end_time,
                       status, variants, target_metrics, sample_size, confidence_level,
                       minimum_detectable_effect, created_at, updated_at
                FROM ab_tests 
                WHERE status IN ('running', 'paused')
            """)
            
            rows = cursor.fetchall()
            
            for row in rows:
                variants_data = json.loads(row[7]) if row[7] else []
                variants = []
                for variant_data in variants_data:
                    variant = TestVariant(
                        variant_id=variant_data['variant_id'],
                        name=variant_data['name'],
                        description=variant_data['description'],
                        configuration=variant_data['configuration'],
                        traffic_allocation=variant_data['traffic_allocation'],
                        is_control=variant_data.get('is_control', False)
                    )
                    variants.append(variant)
                
                target_metrics = [MetricType(metric) for metric in json.loads(row[8]) if row[8]]
                
                test = ABTest(
                    test_id=row[0],
                    name=row[1],
                    description=row[2],
                    hypothesis=row[3],
                    start_time=datetime.fromisoformat(row[4]) if row[4] else None,
                    end_time=datetime.fromisoformat(row[5]) if row[5] else None,
                    status=TestStatus(row[6]),
                    variants=variants,
                    target_metrics=target_metrics,
                    sample_size=row[9],
                    confidence_level=row[10],
                    minimum_detectable_effect=row[11],
                    created_at=datetime.fromisoformat(row[12]) if row[12] else None,
                    updated_at=datetime.fromisoformat(row[13]) if row[13] else None
                )
                
                self.active_tests[row[0]] = test
            
            logger.info(f"Loaded {len(self.active_tests)} active tests")
            
        except Exception as e:
            logger.error(f"Failed to load active tests: {e}")
    
    def create_test(self, name: str, description: str, hypothesis: str,
                   variants: List[TestVariant], target_metrics: List[MetricType],
                   duration_days: int = None, sample_size: int = None) -> str:
        """Create a new A/B test"""
        try:
            test_id = str(uuid.uuid4())
            
            # Validate variants
            total_allocation = sum(variant.traffic_allocation for variant in variants)
            if abs(total_allocation - 1.0) > 0.001:
                raise ValueError(f"Variant traffic allocations must sum to 1.0, got {total_allocation}")
            
            # Set defaults
            duration_days = duration_days or self.config.default_test_duration_days
            sample_size = sample_size or self.config.minimum_sample_size
            
            # Create test
            test = ABTest(
                test_id=test_id,
                name=name,
                description=description,
                hypothesis=hypothesis,
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(days=duration_days),
                status=TestStatus.DRAFT,
                variants=variants,
                target_metrics=target_metrics,
                sample_size=sample_size,
                confidence_level=self.config.default_confidence_level,
                minimum_detectable_effect=self.config.minimum_detectable_effect,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Save to database
            if self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute("""
                    INSERT INTO ab_tests 
                    (test_id, name, description, hypothesis, start_time, end_time,
                     status, variants, target_metrics, sample_size, confidence_level,
                     minimum_detectable_effect, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    test.test_id, test.name, test.description, test.hypothesis,
                    test.start_time.isoformat(), test.end_time.isoformat(),
                    test.status.value, json.dumps([asdict(variant) for variant in variants]),
                    json.dumps([metric.value for metric in target_metrics]),
                    test.sample_size, test.confidence_level, test.minimum_detectable_effect,
                    test.created_at.isoformat(), test.updated_at.isoformat()
                ))
                self.db_connection.commit()
            
            logger.info(f"Created A/B test: {test_id} - {name}")
            return test_id
            
        except Exception as e:
            logger.error(f"Failed to create A/B test: {e}")
            raise
    
    def start_test(self, test_id: str) -> bool:
        """Start an A/B test"""
        try:
            if test_id not in self.active_tests:
                # Load test from database
                test = self._load_test_from_db(test_id)
                if not test:
                    logger.error(f"Test {test_id} not found")
                    return False
                self.active_tests[test_id] = test
            
            test = self.active_tests[test_id]
            
            if test.status != TestStatus.DRAFT:
                logger.warning(f"Test {test_id} is not in draft status")
                return False
            
            # Update test status
            test.status = TestStatus.RUNNING
            test.start_time = datetime.now()
            test.updated_at = datetime.now()
            
            # Save to database
            if self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute("""
                    UPDATE ab_tests 
                    SET status = ?, start_time = ?, updated_at = ?
                    WHERE test_id = ?
                """, (test.status.value, test.start_time.isoformat(), test.updated_at.isoformat(), test_id))
                self.db_connection.commit()
            
            logger.info(f"Started A/B test: {test_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start A/B test {test_id}: {e}")
            return False
    
    def assign_user_to_variant(self, test_id: str, user_id: str, 
                              context: Dict[str, Any] = None) -> Optional[str]:
        """Assign a user to a test variant"""
        try:
            if test_id not in self.active_tests:
                return None
            
            test = self.active_tests[test_id]
            
            if test.status != TestStatus.RUNNING:
                return None
            
            # Check if user is already assigned
            if user_id in self.user_assignments and test_id in self.user_assignments[user_id]:
                return self.user_assignments[user_id][test_id]
            
            # Check assignment cache
            user_hash = self._hash_user_id(user_id)
            cache_key = f"{test_id}:{user_hash}"
            
            if cache_key in self.assignment_cache:
                variant_id, expiry = self.assignment_cache[cache_key]
                if datetime.now() < expiry:
                    self.user_assignments[user_id][test_id] = variant_id
                    return variant_id
                else:
                    del self.assignment_cache[cache_key]
            
            # Assign to variant based on traffic allocation
            variant_id = self._assign_variant(test, user_hash)
            
            if variant_id:
                # Store assignment
                if user_id not in self.user_assignments:
                    self.user_assignments[user_id] = {}
                self.user_assignments[user_id][test_id] = variant_id
                
                # Cache assignment
                expiry = datetime.now() + timedelta(hours=self.config.assignment_cache_duration_hours)
                self.assignment_cache[cache_key] = (variant_id, expiry)
                
                # Save to database
                if self.db_connection:
                    cursor = self.db_connection.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO test_assignments 
                        (test_id, user_id, variant_id, context)
                        VALUES (?, ?, ?, ?)
                    """, (test_id, user_id, variant_id, json.dumps(context) if context else None))
                    self.db_connection.commit()
            
            return variant_id
            
        except Exception as e:
            logger.error(f"Failed to assign user {user_id} to test {test_id}: {e}")
            return None
    
    def _assign_variant(self, test: ABTest, user_hash: str) -> Optional[str]:
        """Assign user to variant using deterministic hashing"""
        try:
            # Use user hash to determine assignment
            hash_value = int(hashlib.md5(f"{test.test_id}:{user_hash}".encode()).hexdigest(), 16)
            hash_float = hash_value / (2**128 - 1)  # Normalize to 0-1
            
            # Find variant based on traffic allocation
            cumulative = 0.0
            for variant in test.variants:
                cumulative += variant.traffic_allocation
                if hash_float <= cumulative:
                    return variant.variant_id
            
            # Fallback to first variant
            return test.variants[0].variant_id if test.variants else None
            
        except Exception as e:
            logger.error(f"Failed to assign variant: {e}")
            return None
    
    def _hash_user_id(self, user_id: str) -> str:
        """Hash user ID for consistent assignment"""
        return hashlib.md5(user_id.encode()).hexdigest()[:16]
    
    def record_event(self, test_id: str, user_id: str, session_id: str,
                    event_type: str, metrics: Dict[str, float],
                    metadata: Dict[str, Any] = None) -> bool:
        """Record a test event"""
        try:
            # Get user's variant assignment
            variant_id = self.user_assignments.get(user_id, {}).get(test_id)
            if not variant_id:
                return False
            
            # Create event
            event = TestEvent(
                test_id=test_id,
                variant_id=variant_id,
                user_id=user_id,
                session_id=session_id,
                event_type=event_type,
                timestamp=datetime.now(),
                metrics=metrics,
                metadata=metadata or {}
            )
            
            # Store event
            self.event_queue.append(event)
            
            # Update metric aggregators
            for metric_name, value in metrics.items():
                self.metric_aggregators[f"{test_id}:{variant_id}"][metric_name].append(value)
            
            # Save to database
            if self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute("""
                    INSERT INTO test_events 
                    (test_id, variant_id, user_id, session_id, event_type, metrics, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    test_id, variant_id, user_id, session_id, event_type,
                    json.dumps(metrics), json.dumps(metadata) if metadata else None
                ))
                self.db_connection.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record test event: {e}")
            return False
    
    def get_variant_configuration(self, test_id: str, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific variant"""
        try:
            if test_id not in self.active_tests:
                return None
            
            test = self.active_tests[test_id]
            for variant in test.variants:
                if variant.variant_id == variant_id:
                    return variant.configuration
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get variant configuration: {e}")
            return None
    
    def analyze_test(self, test_id: str) -> Dict[str, List[TestResult]]:
        """Analyze test results and generate statistical results"""
        try:
            if test_id not in self.active_tests:
                return {}
            
            test = self.active_tests[test_id]
            
            # Get control variant
            control_variant = None
            for variant in test.variants:
                if variant.is_control:
                    control_variant = variant
                    break
            
            if not control_variant:
                logger.warning(f"No control variant found for test {test_id}")
                return {}
            
            results = {}
            
            for metric in test.target_metrics:
                metric_results = []
                
                for variant in test.variants:
                    if variant.is_control:
                        continue
                    
                    # Calculate statistical test
                    result = self._calculate_statistical_test(
                        test_id, control_variant.variant_id, variant.variant_id, metric
                    )
                    
                    if result:
                        metric_results.append(result)
                
                results[metric.value] = metric_results
            
            # Apply multiple testing correction
            if self.config.multiple_testing_correction != "none":
                results = self._apply_multiple_testing_correction(results)
            
            # Save results to database
            self._save_test_results(test_id, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to analyze test {test_id}: {e}")
            return {}
    
    def _calculate_statistical_test(self, test_id: str, control_variant_id: str,
                                 variant_variant_id: str, metric: MetricType) -> Optional[TestResult]:
        """Calculate statistical test between control and variant"""
        try:
            # Get metric data
            control_data = self.metric_aggregators[f"{test_id}:{control_variant_id}"].get(metric.value, [])
            variant_data = self.metric_aggregators[f"{test_id}:{variant_variant_id}"].get(metric.value, [])
            
            if len(control_data) < 30 or len(variant_data) < 30:
                logger.warning(f"Insufficient sample size for metric {metric.value}")
                return None
            
            # Calculate statistics using appropriate method
            calculator = self.statistical_calculators.get(metric)
            if not calculator:
                logger.warning(f"No calculator for metric {metric.value}")
                return None
            
            return calculator(control_data, variant_data, test_id, variant_variant_id, metric)
            
        except Exception as e:
            logger.error(f"Failed to calculate statistical test: {e}")
            return None
    
    def _calculate_proportion_metrics(self, control_data: List[float], variant_data: List[float],
                                    test_id: str, variant_id: str, metric: MetricType) -> TestResult:
        """Calculate statistical test for proportion metrics"""
        try:
            # Calculate proportions
            control_successes = sum(1 for x in control_data if x > 0)
            control_total = len(control_data)
            control_rate = control_successes / control_total
            
            variant_successes = sum(1 for x in variant_data if x > 0)
            variant_total = len(variant_data)
            variant_rate = variant_successes / variant_total
            
            # Calculate difference
            abs_diff = variant_rate - control_rate
            rel_diff = abs_diff / control_rate if control_rate > 0 else 0
            
            # Perform two-proportion z-test
            pooled_rate = (control_successes + variant_successes) / (control_total + variant_total)
            se = np.sqrt(pooled_rate * (1 - pooled_rate) * (1/control_total + 1/variant_total))
            z_score = abs_diff / se if se > 0 else 0
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
            
            # Calculate confidence interval
            margin = stats.norm.ppf(0.975) * se
            ci_lower = abs_diff - margin
            ci_upper = abs_diff + margin
            
            # Calculate power
            power = self._calculate_power(abs_diff, se, 0.05)
            
            return TestResult(
                test_id=test_id,
                variant_id=variant_id,
                metric_name=metric.value,
                control_value=control_rate,
                variant_value=variant_rate,
                absolute_difference=abs_diff,
                relative_difference=rel_diff,
                p_value=p_value,
                confidence_interval=(ci_lower, ci_upper),
                statistical_significance=p_value < 0.05,
                sample_size=variant_total,
                power=power
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate proportion metrics: {e}")
            raise
    
    def _calculate_continuous_metrics(self, control_data: List[float], variant_data: List[float],
                                  test_id: str, variant_id: str, metric: MetricType) -> TestResult:
        """Calculate statistical test for continuous metrics"""
        try:
            # Calculate means
            control_mean = np.mean(control_data)
            variant_mean = np.mean(variant_data)
            
            # Calculate difference
            abs_diff = variant_mean - control_mean
            rel_diff = abs_diff / control_mean if control_mean > 0 else 0
            
            # Perform two-sample t-test
            t_stat, p_value = stats.ttest_ind(variant_data, control_data)
            
            # Calculate confidence interval
            se = np.sqrt(np.var(variant_data, ddof=1)/len(variant_data) + np.var(control_data, ddof=1)/len(control_data))
            margin = stats.t.ppf(0.975, len(variant_data) + len(control_data) - 2) * se
            ci_lower = abs_diff - margin
            ci_upper = abs_diff + margin
            
            # Calculate power
            power = self._calculate_power(abs_diff, se, 0.05)
            
            return TestResult(
                test_id=test_id,
                variant_id=variant_id,
                metric_name=metric.value,
                control_value=control_mean,
                variant_value=variant_mean,
                absolute_difference=abs_diff,
                relative_difference=rel_diff,
                p_value=p_value,
                confidence_interval=(ci_lower, ci_upper),
                statistical_significance=p_value < 0.05,
                sample_size=len(variant_data),
                power=power
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate continuous metrics: {e}")
            raise
    
    def _calculate_power(self, effect_size: float, standard_error: float, alpha: float) -> float:
        """Calculate statistical power"""
        try:
            # Simplified power calculation
            z_alpha = stats.norm.ppf(1 - alpha/2)
            z_beta = effect_size / standard_error - z_alpha
            power = stats.norm.cdf(z_beta)
            return max(0, min(1, power))
            
        except Exception as e:
            logger.error(f"Failed to calculate power: {e}")
            return 0.0
    
    def _apply_multiple_testing_correction(self, results: Dict[str, List[TestResult]]) -> Dict[str, List[TestResult]]:
        """Apply multiple testing correction"""
        try:
            if self.config.multiple_testing_correction == "bonferroni":
                return self._apply_bonferroni_correction(results)
            elif self.config.multiple_testing_correction == "holm":
                return self._apply_holm_correction(results)
            else:
                return results
                
        except Exception as e:
            logger.error(f"Failed to apply multiple testing correction: {e}")
            return results
    
    def _apply_bonferroni_correction(self, results: Dict[str, List[TestResult]]) -> Dict[str, List[TestResult]]:
        """Apply Bonferroni correction"""
        try:
            # Count total number of tests
            total_tests = sum(len(metric_results) for metric_results in results.values())
            
            # Apply correction
            corrected_results = {}
            for metric_name, metric_results in results.items():
                corrected_metric_results = []
                for result in metric_results:
                    corrected_result = TestResult(
                        test_id=result.test_id,
                        variant_id=result.variant_id,
                        metric_name=result.metric_name,
                        control_value=result.control_value,
                        variant_value=result.variant_value,
                        absolute_difference=result.absolute_difference,
                        relative_difference=result.relative_difference,
                        p_value=min(1.0, result.p_value * total_tests),
                        confidence_interval=result.confidence_interval,
                        statistical_significance=result.p_value * total_tests < 0.05,
                        sample_size=result.sample_size,
                        power=result.power
                    )
                    corrected_metric_results.append(corrected_result)
                corrected_results[metric_name] = corrected_metric_results
            
            return corrected_results
            
        except Exception as e:
            logger.error(f"Failed to apply Bonferroni correction: {e}")
            return results
    
    def _apply_holm_correction(self, results: Dict[str, List[TestResult]]) -> Dict[str, List[TestResult]]:
        """Apply Holm-Bonferroni correction"""
        try:
            # Collect all p-values
            all_results = []
            for metric_results in results.values():
                all_results.extend(metric_results)
            
            # Sort by p-value
            all_results.sort(key=lambda x: x.p_value)
            
            # Apply Holm correction
            corrected_results = {}
            for i, result in enumerate(all_results):
                corrected_p_value = min(1.0, result.p_value * (len(all_results) - i))
                
                corrected_result = TestResult(
                    test_id=result.test_id,
                    variant_id=result.variant_id,
                    metric_name=result.metric_name,
                    control_value=result.control_value,
                    variant_value=result.variant_value,
                    absolute_difference=result.absolute_difference,
                    relative_difference=result.relative_difference,
                    p_value=corrected_p_value,
                    confidence_interval=result.confidence_interval,
                    statistical_significance=corrected_p_value < 0.05,
                    sample_size=result.sample_size,
                    power=result.power
                )
                
                if result.metric_name not in corrected_results:
                    corrected_results[result.metric_name] = []
                corrected_results[result.metric_name].append(corrected_result)
            
            return corrected_results
            
        except Exception as e:
            logger.error(f"Failed to apply Holm correction: {e}")
            return results
    
    def _save_test_results(self, test_id: str, results: Dict[str, List[TestResult]]):
        """Save test results to database"""
        try:
            if not self.db_connection:
                return
                
            cursor = self.db_connection.cursor()
            
            # Clear existing results
            cursor.execute("DELETE FROM test_results WHERE test_id = ?", (test_id,))
            
            # Insert new results
            for metric_name, metric_results in results.items():
                for result in metric_results:
                    cursor.execute("""
                        INSERT INTO test_results 
                        (test_id, variant_id, metric_name, control_value, variant_value,
                         absolute_difference, relative_difference, p_value,
                         confidence_interval_lower, confidence_interval_upper,
                         statistical_significance, sample_size, power)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        result.test_id, result.variant_id, result.metric_name,
                        result.control_value, result.variant_value,
                        result.absolute_difference, result.relative_difference,
                        result.p_value, result.confidence_interval[0], result.confidence_interval[1],
                        result.statistical_significance, result.sample_size, result.power
                    ))
            
            self.db_connection.commit()
            logger.info(f"Saved test results for {test_id}")
            
        except Exception as e:
            logger.error(f"Failed to save test results: {e}")
    
    def get_test_summary(self, test_id: str) -> Dict[str, Any]:
        """Get comprehensive test summary"""
        try:
            if test_id not in self.active_tests:
                return {}
            
            test = self.active_tests[test_id]
            
            # Get sample sizes
            sample_sizes = {}
            for variant in test.variants:
                variant_key = f"{test_id}:{variant.variant_id}"
                total_events = sum(len(values) for values in self.metric_aggregators[variant_key].values())
                sample_sizes[variant.variant_id] = total_events
            
            # Get latest results
            results = self.analyze_test(test_id)
            
            # Calculate test duration
            duration = (datetime.now() - test.start_time).days if test.start_time else 0
            
            return {
                'test_id': test_id,
                'name': test.name,
                'status': test.status.value,
                'hypothesis': test.hypothesis,
                'start_time': test.start_time.isoformat() if test.start_time else None,
                'end_time': test.end_time.isoformat() if test.end_time else None,
                'duration_days': duration,
                'sample_sizes': sample_sizes,
                'target_metrics': [metric.value for metric in test.target_metrics],
                'variants': [
                    {
                        'variant_id': variant.variant_id,
                        'name': variant.name,
                        'is_control': variant.is_control,
                        'traffic_allocation': variant.traffic_allocation
                    }
                    for variant in test.variants
                ],
                'results': results,
                'is_statistically_significant': any(
                    any(result.statistical_significance for result in metric_results)
                    for metric_results in results.values()
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to get test summary: {e}")
            return {}
    
    def stop_test(self, test_id: str) -> bool:
        """Stop an A/B test"""
        try:
            if test_id not in self.active_tests:
                return False
            
            test = self.active_tests[test_id]
            
            if test.status not in [TestStatus.RUNNING, TestStatus.PAUSED]:
                logger.warning(f"Test {test_id} is not running")
                return False
            
            # Update test status
            test.status = TestStatus.COMPLETED
            test.updated_at = datetime.now()
            
            # Save to database
            if self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute("""
                    UPDATE ab_tests 
                    SET status = ?, updated_at = ?
                    WHERE test_id = ?
                """, (test.status.value, test.updated_at.isoformat(), test_id))
                self.db_connection.commit()
            
            logger.info(f"Stopped A/B test: {test_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop A/B test {test_id}: {e}")
            return False
    
    def _load_test_from_db(self, test_id: str) -> Optional[ABTest]:
        """Load test from database"""
        try:
            if not self.db_connection:
                return None
                
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                SELECT test_id, name, description, hypothesis, start_time, end_time,
                       status, variants, target_metrics, sample_size, confidence_level,
                       minimum_detectable_effect, created_at, updated_at
                FROM ab_tests WHERE test_id = ?
            """, (test_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            variants_data = json.loads(row[7]) if row[7] else []
            variants = []
            for variant_data in variants_data:
                variant = TestVariant(
                    variant_id=variant_data['variant_id'],
                    name=variant_data['name'],
                    description=variant_data['description'],
                    configuration=variant_data['configuration'],
                    traffic_allocation=variant_data['traffic_allocation'],
                    is_control=variant_data.get('is_control', False)
                )
                variants.append(variant)
            
            target_metrics = [MetricType(metric) for metric in json.loads(row[8]) if row[8]]
            
            return ABTest(
                test_id=row[0],
                name=row[1],
                description=row[2],
                hypothesis=row[3],
                start_time=datetime.fromisoformat(row[4]) if row[4] else None,
                end_time=datetime.fromisoformat(row[5]) if row[5] else None,
                status=TestStatus(row[6]),
                variants=variants,
                target_metrics=target_metrics,
                sample_size=row[9],
                confidence_level=row[10],
                minimum_detectable_effect=row[11],
                created_at=datetime.fromisoformat(row[12]) if row[12] else None,
                updated_at=datetime.fromisoformat(row[13]) if row[13] else None
            )
            
        except Exception as e:
            logger.error(f"Failed to load test from database: {e}")
            return None
    
    def get_all_tests(self) -> List[Dict[str, Any]]:
        """Get all tests with summaries"""
        try:
            if not self.db_connection:
                return []
                
            cursor = self.db_connection.cursor()
            
            cursor.execute("""
                SELECT test_id, name, status, start_time, end_time, created_at
                FROM ab_tests 
                ORDER BY created_at DESC
            """)
            
            tests = []
            for row in cursor.fetchall():
                test_summary = {
                    'test_id': row[0],
                    'name': row[1],
                    'status': row[2],
                    'start_time': row[3],
                    'end_time': row[4],
                    'created_at': row[5]
                }
                tests.append(test_summary)
            
            return tests
            
        except Exception as e:
            logger.error(f"Failed to get all tests: {e}")
            return []

# Utility functions for creating common test variants
def create_recommendation_algorithm_test(algorithm_configs: Dict[str, Dict[str, Any]]) -> List[TestVariant]:
    """Create test variants for recommendation algorithm comparison"""
    variants = []
    allocation = 1.0 / len(algorithm_configs)
    
    for name, config in algorithm_configs.items():
        variant = TestVariant(
            variant_id=str(uuid.uuid4()),
            name=name,
            description=f"Recommendation algorithm: {name}",
            configuration=config,
            traffic_allocation=allocation,
            is_control=(name == "control")
        )
        variants.append(variant)
    
    return variants

def create_weight_configuration_test(weight_configs: Dict[str, Dict[str, float]]) -> List[TestVariant]:
    """Create test variants for weight configuration testing"""
    variants = []
    allocation = 1.0 / len(weight_configs)
    
    for name, weights in weight_configs.items():
        variant = TestVariant(
            variant_id=str(uuid.uuid4()),
            name=name,
            description=f"Weight configuration: {name}",
            configuration={'weights': weights},
            traffic_allocation=allocation,
            is_control=(name == "default")
        )
        variants.append(variant)
    
    return variants

def create_diversity_test(diversity_levels: List[float]) -> List[TestVariant]:
    """Create test variants for diversity level testing"""
    variants = []
    allocation = 1.0 / len(diversity_levels)
    
    for level in diversity_levels:
        variant = TestVariant(
            variant_id=str(uuid.uuid4()),
            name=f"diversity_{level}",
            description=f"Diversity level: {level}",
            configuration={'diversity_threshold': level},
            traffic_allocation=allocation,
            is_control=(level == 0.3)  # Default diversity level
        )
        variants.append(variant)
    
    return variants
