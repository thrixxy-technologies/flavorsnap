#!/usr/bin/env python3
"""
Advanced Feature Engineering Pipeline for FlavorSnap ML Model API
Orchestrates automated feature extraction, selection, monitoring, and versioning
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import pickle
import sqlite3
from pathlib import Path
import threading
import time
import uuid

# Import our modules
from feature_extraction import (
    AutomatedFeatureExtractor, FeatureConfig, ExtractedFeatures, FeatureType
)
from feature_selection import (
    FeatureSelector, SelectionConfig, SelectionResult, SelectionMethod, SelectionStrategy
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PipelineStatus(Enum):
    """Pipeline execution status"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    EXTRACTING = "extracting"
    SELECTING = "selecting"
    VALIDATING = "validating"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"

class FeatureVersion(Enum):
    """Feature version status"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"

@dataclass
class PipelineConfig:
    """Feature engineering pipeline configuration"""
    # Feature extraction settings
    extraction_config: FeatureConfig = None
    
    # Feature selection settings
    selection_config: SelectionConfig = None
    
    # Pipeline settings
    enable_monitoring: bool = True
    enable_versioning: bool = True
    enable_documentation: bool = True
    enable_performance_tracking: bool = True
    
    # Processing settings
    batch_size: int = 32
    max_concurrent_jobs: int = 4
    timeout_seconds: int = 3600
    
    # Storage settings
    cache_directory: str = "feature_cache"
    database_path: str = "feature_engineering.db"
    
    # Monitoring settings
    monitoring_interval: int = 300  # seconds
    performance_window: int = 7  # days
    
    # Versioning settings
    max_versions: int = 10
    auto_promote_threshold: float = 0.85
    
    def __post_init__(self):
        if self.extraction_config is None:
            self.extraction_config = FeatureConfig()
        if self.selection_config is None:
            self.selection_config = SelectionConfig()

@dataclass
class PipelineResult:
    """Pipeline execution result"""
    pipeline_id: str
    status: PipelineStatus
    start_time: datetime
    end_time: Optional[datetime]
    input_data_path: str
    extracted_features: Dict[str, ExtractedFeatures]
    selection_results: Dict[SelectionMethod, SelectionResult]
    best_selection: Optional[SelectionResult]
    performance_metrics: Dict[str, float]
    metadata: Dict[str, Any]
    error_message: Optional[str]

@dataclass
class FeatureVersionInfo:
    """Feature version information"""
    version_id: str
    pipeline_id: str
    version_number: int
    status: FeatureVersion
    created_at: datetime
    feature_count: int
    performance_score: float
    feature_hashes: Dict[str, str]
    metadata: Dict[str, Any]

@dataclass
class FeatureMetrics:
    """Feature performance metrics"""
    feature_name: str
    pipeline_id: str
    timestamp: datetime
    accuracy: Optional[float]
    precision: Optional[float]
    recall: Optional[float]
    f1_score: Optional[float]
    mse: Optional[float]
    r2_score: Optional[float]
    training_time: float
    inference_time: float
    memory_usage: float

class FeatureEngineeringPipeline:
    """Advanced feature engineering pipeline"""
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.feature_extractor = AutomatedFeatureExtractor(self.config.extraction_config)
        self.feature_selector = FeatureSelector(self.config.selection_config)
        
        # Pipeline state
        self.current_pipeline_id = None
        self.pipeline_status = PipelineStatus.IDLE
        self.pipeline_results = {}
        
        # Feature versions
        self.feature_versions = {}
        self.active_version = None
        
        # Performance tracking
        self.performance_history = []
        self.feature_metrics = []
        
        # Database
        self.db_path = self.config.database_path
        self._init_database()
        
        # Cache directories
        self.cache_dir = Path(self.config.cache_directory)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Thread safety
        self.pipeline_lock = threading.Lock()
        self.monitoring_thread = None
        self.monitoring_active = False
        
        logger.info("FeatureEngineeringPipeline initialized")
    
    def _init_database(self):
        """Initialize pipeline database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Pipeline runs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    pipeline_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    input_data_path TEXT NOT NULL,
                    extracted_features_count INTEGER,
                    selection_methods_count INTEGER,
                    best_method TEXT,
                    performance_score REAL,
                    metadata TEXT,
                    error_message TEXT
                )
            ''')
            
            # Feature versions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feature_versions (
                    version_id TEXT PRIMARY KEY,
                    pipeline_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    feature_count INTEGER NOT NULL,
                    performance_score REAL,
                    feature_hashes TEXT,
                    metadata TEXT,
                    FOREIGN KEY (pipeline_id) REFERENCES pipeline_runs (pipeline_id)
                )
            ''')
            
            # Feature metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feature_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feature_name TEXT NOT NULL,
                    pipeline_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    accuracy REAL,
                    precision REAL,
                    recall REAL,
                    f1_score REAL,
                    mse REAL,
                    r2_score REAL,
                    training_time REAL,
                    inference_time REAL,
                    memory_usage REAL,
                    FOREIGN KEY (pipeline_id) REFERENCES pipeline_runs (pipeline_id)
                )
            ''')
            
            # Feature documentation table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feature_documentation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feature_name TEXT NOT NULL,
                    feature_type TEXT NOT NULL,
                    description TEXT,
                    extraction_method TEXT,
                    selection_method TEXT,
                    importance_score REAL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Pipeline database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def run_pipeline(self, data_path: str, image_paths: List[str] = None,
                    feature_types: List[FeatureType] = None,
                    selection_methods: List[SelectionMethod] = None) -> PipelineResult:
        """Run the complete feature engineering pipeline"""
        try:
            with self.pipeline_lock:
                if self.pipeline_status != PipelineStatus.IDLE:
                    raise Exception("Pipeline already running")
                
                # Initialize pipeline
                self.current_pipeline_id = str(uuid.uuid4())
                self.pipeline_status = PipelineStatus.INITIALIZING
                
                start_time = datetime.now()
                
                logger.info(f"Starting pipeline {self.current_pipeline_id}")
                
                # Step 1: Feature Extraction
                self.pipeline_status = PipelineStatus.EXTRACTING
                extracted_features = self._extract_features(data_path, image_paths, feature_types)
                
                # Step 2: Feature Selection
                self.pipeline_status = PipelineStatus.SELECTING
                selection_results = self._select_features(extracted_features, selection_methods)
                
                # Step 3: Validation
                self.pipeline_status = PipelineStatus.VALIDATING
                best_selection = self._validate_selection(selection_results)
                
                # Step 4: Performance Metrics
                performance_metrics = self._calculate_performance_metrics(
                    extracted_features, selection_results, best_selection
                )
                
                # Step 5: Versioning
                if self.config.enable_versioning:
                    self._create_feature_version(extracted_features, best_selection)
                
                # Step 6: Documentation
                if self.config.enable_documentation:
                    self._generate_documentation(extracted_features, selection_results)
                
                # Step 7: Monitoring
                if self.config.enable_monitoring:
                    self._start_monitoring()
                
                # Create result
                end_time = datetime.now()
                result = PipelineResult(
                    pipeline_id=self.current_pipeline_id,
                    status=PipelineStatus.COMPLETED,
                    start_time=start_time,
                    end_time=end_time,
                    input_data_path=data_path,
                    extracted_features=extracted_features,
                    selection_results=selection_results,
                    best_selection=best_selection,
                    performance_metrics=performance_metrics,
                    metadata={
                        "config": asdict(self.config),
                        "feature_types": [ft.value for ft in feature_types] if feature_types else None,
                        "selection_methods": [sm.value for sm in selection_methods] if selection_methods else None
                    },
                    error_message=None
                )
                
                # Save result
                self.pipeline_results[self.current_pipeline_id] = result
                self._save_pipeline_result(result)
                
                self.pipeline_status = PipelineStatus.IDLE
                
                logger.info(f"Pipeline {self.current_pipeline_id} completed successfully")
                return result
                
        except Exception as e:
            error_message = str(e)
            self.logger.error(f"Pipeline failed: {error_message}")
            
            # Create failed result
            result = PipelineResult(
                pipeline_id=self.current_pipeline_id or str(uuid.uuid4()),
                status=PipelineStatus.FAILED,
                start_time=datetime.now(),
                end_time=datetime.now(),
                input_data_path=data_path,
                extracted_features={},
                selection_results={},
                best_selection=None,
                performance_metrics={},
                metadata={},
                error_message=error_message
            )
            
            self.pipeline_status = PipelineStatus.IDLE
            return result
    
    def _extract_features(self, data_path: str, image_paths: List[str] = None,
                         feature_types: List[FeatureType] = None) -> Dict[str, ExtractedFeatures]:
        """Extract features from images"""
        try:
            if image_paths is None:
                # Get all images from data path
                image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
                image_paths = []
                
                if os.path.isdir(data_path):
                    for ext in image_extensions:
                        image_paths.extend(Path(data_path).glob(f"**/*{ext}"))
                        image_paths.extend(Path(data_path).glob(f"**/*{ext.upper()}"))
                    image_paths = [str(p) for p in image_paths]
                elif os.path.isfile(data_path):
                    image_paths = [data_path]
                else:
                    raise ValueError(f"Invalid data path: {data_path}")
            
            extracted_features = {}
            
            for i, image_path in enumerate(image_paths):
                try:
                    self.logger.info(f"Extracting features from {image_path} ({i+1}/{len(image_paths)})")
                    
                    # Extract all features
                    all_features = self.feature_extractor.extract_all_features(image_path)
                    
                    # Filter by feature types if specified
                    if feature_types:
                        filtered_features = {
                            ft: features for ft, features in all_features.items()
                            if ft in feature_types
                        }
                    else:
                        filtered_features = all_features
                    
                    # Store features by image path
                    extracted_features[image_path] = filtered_features
                    
                except Exception as e:
                    self.logger.error(f"Failed to extract features from {image_path}: {str(e)}")
                    continue
            
            self.logger.info(f"Extracted features from {len(extracted_features)} images")
            return extracted_features
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {str(e)}")
            raise
    
    def _select_features(self, extracted_features: Dict[str, ExtractedFeatures],
                        selection_methods: List[SelectionMethod] = None) -> Dict[SelectionMethod, SelectionResult]:
        """Perform feature selection"""
        try:
            # Prepare data for selection
            X, y, feature_names = self._prepare_selection_data(extracted_features)
            
            if X is None or len(X) == 0:
                raise ValueError("No features available for selection")
            
            # Apply feature selection
            selection_results = self.feature_selector.select_features(
                X, y, feature_names, selection_methods
            )
            
            self.logger.info(f"Applied {len(selection_results)} feature selection methods")
            return selection_results
            
        except Exception as e:
            logger.error(f"Feature selection failed: {str(e)}")
            raise
    
    def _prepare_selection_data(self, extracted_features: Dict[str, ExtractedFeatures]) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], List[str]]:
        """Prepare data for feature selection"""
        try:
            # Collect all features
            all_feature_data = []
            feature_names = []
            labels = []
            
            # For this example, we'll use a simple approach
            # In practice, you would have actual labels for your data
            for image_path, features_dict in extracted_features.items():
                # Flatten all features
                feature_vector = []
                
                for feature_type, extracted_feature in features_dict.items():
                    for feature_name, feature_value in extracted_feature.features.items():
                        if isinstance(feature_value, (int, float)):
                            feature_vector.append(feature_value)
                            feature_names.append(f"{feature_type.value}_{feature_name}")
                        elif isinstance(feature_value, list):
                            for i, val in enumerate(feature_value):
                                if isinstance(val, (int, float)):
                                    feature_vector.append(val)
                                    feature_names.append(f"{feature_type.value}_{feature_name}_{i}")
                
                if feature_vector:
                    all_feature_data.append(feature_vector)
                    # Generate dummy labels (in practice, you'd use real labels)
                    labels.append(hash(image_path) % 10)  # 10 classes
            
            if not all_feature_data:
                return None, None, []
            
            X = np.array(all_feature_data)
            y = np.array(labels)
            
            # Remove duplicate feature names
            unique_features = []
            feature_indices = {}
            for i, name in enumerate(feature_names):
                if name not in feature_indices:
                    feature_indices[name] = len(unique_features)
                    unique_features.append(name)
            
            # Reconstruct X with unique features
            X_unique = np.zeros((X.shape[0], len(unique_features)))
            for i, name in enumerate(feature_names):
                if name in feature_indices:
                    X_unique[:, feature_indices[name]] += X[:, i]
            
            return X_unique, y, unique_features
            
        except Exception as e:
            logger.error(f"Failed to prepare selection data: {str(e)}")
            return None, None, []
    
    def _validate_selection(self, selection_results: Dict[SelectionMethod, SelectionResult]) -> Optional[SelectionResult]:
        """Validate and select best feature selection result"""
        try:
            if not selection_results:
                return None
            
            # Get best selection from feature selector
            best_selection = self.feature_selector.get_best_features()
            
            if best_selection is None:
                # Fallback: select by performance score
                best_selection = max(selection_results.values(), key=lambda x: x.performance_score)
            
            # Validate minimum requirements
            if len(best_selection.selected_features) < self.config.selection_config.min_features:
                logger.warning(f"Best selection has fewer than minimum features: {len(best_selection.selected_features)}")
            
            return best_selection
            
        except Exception as e:
            logger.error(f"Selection validation failed: {str(e)}")
            return None
    
    def _calculate_performance_metrics(self, extracted_features: Dict[str, ExtractedFeatures],
                                     selection_results: Dict[SelectionMethod, SelectionResult],
                                     best_selection: Optional[SelectionResult]) -> Dict[str, float]:
        """Calculate comprehensive performance metrics"""
        try:
            metrics = {}
            
            # Extraction metrics
            metrics["total_images"] = len(extracted_features)
            metrics["total_feature_types"] = len(set(
                ft for features in extracted_features.values() 
                for ft in features.keys()
            ))
            metrics["total_features_extracted"] = sum(
                len(features.features) for features_dict in extracted_features.values()
                for features in features_dict.values()
            )
            
            # Selection metrics
            metrics["selection_methods_applied"] = len(selection_results)
            metrics["average_selected_features"] = np.mean([
                len(result.selected_features) for result in selection_results.values()
            ]) if selection_results else 0
            
            if best_selection:
                metrics["best_method"] = best_selection.method.value
                metrics["best_performance_score"] = best_selection.performance_score
                metrics["best_selected_features"] = len(best_selection.selected_features)
                metrics["feature_reduction_ratio"] = len(best_selection.selected_features) / metrics["total_features_extracted"]
            
            # Time metrics
            if best_selection:
                extraction_time = max(
                    features.extraction_time for features_dict in extracted_features.values()
                    for features in features_dict.values()
                )
                selection_time = best_selection.selection_time
                metrics["extraction_time_seconds"] = (extraction_time - min(
                    features.extraction_time for features_dict in extracted_features.values()
                    for features in features_dict.values()
                )).total_seconds()
                metrics["selection_time_seconds"] = 0  # Would need actual timing
                metrics["total_pipeline_time"] = metrics["extraction_time_seconds"] + metrics["selection_time_seconds"]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate performance metrics: {str(e)}")
            return {}
    
    def _create_feature_version(self, extracted_features: Dict[str, ExtractedFeatures],
                               best_selection: Optional[SelectionResult]):
        """Create a new feature version"""
        try:
            if not best_selection:
                return
            
            # Generate version info
            version_id = str(uuid.uuid4())
            version_number = len(self.feature_versions) + 1
            
            # Calculate feature hashes
            feature_hashes = {}
            for feature_name in best_selection.selected_features:
                feature_data = str(best_selection.feature_scores.get(feature_name, 0))
                feature_hashes[feature_name] = hashlib.md5(feature_data.encode()).hexdigest()
            
            # Create version info
            version_info = FeatureVersionInfo(
                version_id=version_id,
                pipeline_id=self.current_pipeline_id,
                version_number=version_number,
                status=FeatureVersion.DRAFT,
                created_at=datetime.now(),
                feature_count=len(best_selection.selected_features),
                performance_score=best_selection.performance_score,
                feature_hashes=feature_hashes,
                metadata={
                    "method": best_selection.method.value,
                    "strategy": best_selection.strategy.value,
                    "config": asdict(self.config)
                }
            )
            
            # Store version
            self.feature_versions[version_id] = version_info
            
            # Auto-promote if threshold met
            if best_selection.performance_score >= self.config.auto_promote_threshold:
                version_info.status = FeatureVersion.ACTIVE
                self.active_version = version_id
            
            # Save to database
            self._save_feature_version(version_info)
            
            logger.info(f"Created feature version {version_number} with {len(best_selection.selected_features)} features")
            
        except Exception as e:
            logger.error(f"Failed to create feature version: {str(e)}")
    
    def _generate_documentation(self, extracted_features: Dict[str, ExtractedFeatures],
                              selection_results: Dict[SelectionMethod, SelectionResult]):
        """Generate feature documentation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Document extracted features
            for image_path, features_dict in extracted_features.items():
                for feature_type, extracted_feature in features_dict.items():
                    for feature_name, feature_value in extracted_feature.features.items():
                        full_feature_name = f"{feature_type.value}_{feature_name}"
                        
                        # Check if already documented
                        cursor.execute('''
                            SELECT id FROM feature_documentation WHERE feature_name = ?
                        ''', (full_feature_name,))
                        
                        if not cursor.fetchone():
                            # Insert new documentation
                            cursor.execute('''
                                INSERT INTO feature_documentation 
                                (feature_name, feature_type, description, extraction_method, 
                                 importance_score, created_at, updated_at, metadata)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                full_feature_name,
                                feature_type.value,
                                f"Feature extracted using {feature_type.value} method",
                                feature_type.value,
                                None,  # Importance score to be calculated later
                                datetime.now().isoformat(),
                                datetime.now().isoformat(),
                                json.dumps({
                                    "sample_value": str(feature_value),
                                    "value_type": type(feature_value).__name__
                                })
                            ))
            
            # Document selected features
            for method, result in selection_results.items():
                for feature_name in result.selected_features:
                    importance = result.feature_scores.get(feature_name, 0)
                    
                    cursor.execute('''
                        UPDATE feature_documentation 
                        SET selection_method = ?, importance_score = ?, updated_at = ?
                        WHERE feature_name = ?
                    ''', (method.value, importance, datetime.now().isoformat(), feature_name))
            
            conn.commit()
            conn.close()
            logger.info("Feature documentation generated")
            
        except Exception as e:
            logger.error(f"Failed to generate documentation: {str(e)}")
    
    def _start_monitoring(self):
        """Start feature monitoring thread"""
        try:
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                return
            
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitor_features, daemon=True)
            self.monitoring_thread.start()
            logger.info("Feature monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {str(e)}")
    
    def _monitor_features(self):
        """Monitor feature performance and drift"""
        try:
            while self.monitoring_active:
                try:
                    # Collect current metrics
                    current_metrics = self._collect_current_metrics()
                    
                    # Store metrics
                    for metric in current_metrics:
                        self.feature_metrics.append(metric)
                        self._save_feature_metric(metric)
                    
                    # Check for performance drift
                    self._check_performance_drift()
                    
                    # Sleep until next monitoring cycle
                    time.sleep(self.config.monitoring_interval)
                    
                except Exception as e:
                    logger.error(f"Monitoring cycle failed: {str(e)}")
                    time.sleep(self.config.monitoring_interval)
                    
        except Exception as e:
            logger.error(f"Feature monitoring failed: {str(e)}")
    
    def _collect_current_metrics(self) -> List[FeatureMetrics]:
        """Collect current feature metrics"""
        metrics = []
        
        try:
            # Get active version
            if self.active_version and self.active_version in self.feature_versions:
                version_info = self.feature_versions[self.active_version]
                
                # Collect metrics for each selected feature
                for feature_name in version_info.feature_hashes.keys():
                    metric = FeatureMetrics(
                        feature_name=feature_name,
                        pipeline_id=self.current_pipeline_id,
                        timestamp=datetime.now(),
                        accuracy=None,  # Would be calculated from actual model performance
                        precision=None,
                        recall=None,
                        f1_score=None,
                        mse=None,
                        r2_score=None,
                        training_time=0.0,
                        inference_time=0.0,
                        memory_usage=0.0
                    )
                    metrics.append(metric)
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {str(e)}")
        
        return metrics
    
    def _check_performance_drift(self):
        """Check for performance drift in features"""
        try:
            if len(self.feature_metrics) < 10:
                return
            
            # Get recent metrics
            recent_metrics = [m for m in self.feature_metrics 
                            if m.timestamp > datetime.now() - timedelta(days=self.config.performance_window)]
            
            if not recent_metrics:
                return
            
            # Group by feature
            feature_metrics = {}
            for metric in recent_metrics:
                if metric.feature_name not in feature_metrics:
                    feature_metrics[metric.feature_name] = []
                feature_metrics[metric.feature_name].append(metric)
            
            # Check for drift (simplified)
            for feature_name, metrics_list in feature_metrics.items():
                if len(metrics_list) < 5:
                    continue
                
                # Calculate performance trend
                accuracies = [m.accuracy for m in metrics_list if m.accuracy is not None]
                if len(accuracies) >= 3:
                    recent_avg = np.mean(accuracies[-3:])
                    older_avg = np.mean(accuracies[:-3]) if len(accuracies) > 3 else recent_avg
                    
                    # Check for significant drop
                    if older_avg > 0 and (recent_avg / older_avg) < 0.9:
                        logger.warning(f"Performance drift detected for feature {feature_name}: "
                                     f"recent avg {recent_avg:.3f} vs older avg {older_avg:.3f}")
            
        except Exception as e:
            logger.error(f"Failed to check performance drift: {str(e)}")
    
    def _save_pipeline_result(self, result: PipelineResult):
        """Save pipeline result to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO pipeline_runs 
                (pipeline_id, status, start_time, end_time, input_data_path,
                 extracted_features_count, selection_methods_count, best_method,
                 performance_score, metadata, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.pipeline_id,
                result.status.value,
                result.start_time.isoformat(),
                result.end_time.isoformat() if result.end_time else None,
                result.input_data_path,
                len(result.extracted_features),
                len(result.selection_results),
                result.best_selection.method.value if result.best_selection else None,
                result.best_selection.performance_score if result.best_selection else None,
                json.dumps(result.metadata),
                result.error_message
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save pipeline result: {str(e)}")
    
    def _save_feature_version(self, version_info: FeatureVersionInfo):
        """Save feature version to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO feature_versions 
                (version_id, pipeline_id, version_number, status, created_at,
                 feature_count, performance_score, feature_hashes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                version_info.version_id,
                version_info.pipeline_id,
                version_info.version_number,
                version_info.status.value,
                version_info.created_at.isoformat(),
                version_info.feature_count,
                version_info.performance_score,
                json.dumps(version_info.feature_hashes),
                json.dumps(version_info.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save feature version: {str(e)}")
    
    def _save_feature_metric(self, metric: FeatureMetrics):
        """Save feature metric to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO feature_metrics 
                (feature_name, pipeline_id, timestamp, accuracy, precision, recall,
                 f1_score, mse, r2_score, training_time, inference_time, memory_usage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.feature_name,
                metric.pipeline_id,
                metric.timestamp.isoformat(),
                metric.accuracy,
                metric.precision,
                metric.recall,
                metric.f1_score,
                metric.mse,
                metric.r2_score,
                metric.training_time,
                metric.inference_time,
                metric.memory_usage
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save feature metric: {str(e)}")
    
    def get_pipeline_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pipeline execution history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT pipeline_id, status, start_time, end_time, input_data_path,
                       extracted_features_count, selection_methods_count, best_method,
                       performance_score, metadata, error_message
                FROM pipeline_runs
                ORDER BY start_time DESC
                LIMIT ?
            ''', (limit,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "pipeline_id": row[0],
                    "status": row[1],
                    "start_time": row[2],
                    "end_time": row[3],
                    "input_data_path": row[4],
                    "extracted_features_count": row[5],
                    "selection_methods_count": row[6],
                    "best_method": row[7],
                    "performance_score": row[8],
                    "metadata": json.loads(row[9]) if row[9] else {},
                    "error_message": row[10]
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to get pipeline history: {str(e)}")
            return []
    
    def get_feature_versions(self) -> List[Dict[str, Any]]:
        """Get all feature versions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT version_id, pipeline_id, version_number, status, created_at,
                       feature_count, performance_score, feature_hashes, metadata
                FROM feature_versions
                ORDER BY version_number DESC
            ''')
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "version_id": row[0],
                    "pipeline_id": row[1],
                    "version_number": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "feature_count": row[5],
                    "performance_score": row[6],
                    "feature_hashes": json.loads(row[7]) if row[7] else {},
                    "metadata": json.loads(row[8]) if row[8] else {}
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to get feature versions: {str(e)}")
            return []
    
    def get_feature_documentation(self, feature_name: str = None) -> List[Dict[str, Any]]:
        """Get feature documentation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if feature_name:
                cursor.execute('''
                    SELECT feature_name, feature_type, description, extraction_method,
                           selection_method, importance_score, created_at, updated_at, metadata
                    FROM feature_documentation
                    WHERE feature_name = ?
                    ORDER BY importance_score DESC
                ''', (feature_name,))
            else:
                cursor.execute('''
                    SELECT feature_name, feature_type, description, extraction_method,
                           selection_method, importance_score, created_at, updated_at, metadata
                    FROM feature_documentation
                    ORDER BY importance_score DESC
                ''')
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "feature_name": row[0],
                    "feature_type": row[1],
                    "description": row[2],
                    "extraction_method": row[3],
                    "selection_method": row[4],
                    "importance_score": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "metadata": json.loads(row[8]) if row[8] else {}
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to get feature documentation: {str(e)}")
            return []
    
    def export_pipeline_results(self, output_path: str, format: str = "json"):
        """Export pipeline results"""
        try:
            export_data = {
                "pipeline_history": self.get_pipeline_history(),
                "feature_versions": self.get_feature_versions(),
                "feature_documentation": self.get_feature_documentation(),
                "config": asdict(self.config)
            }
            
            if format.lower() == "json":
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            
            elif format.lower() == "csv":
                # Export as multiple CSV files
                base_path = Path(output_path).with_suffix('')
                
                # Pipeline history
                if export_data["pipeline_history"]:
                    pd.DataFrame(export_data["pipeline_history"]).to_csv(
                        f"{base_path}_pipeline_history.csv", index=False
                    )
                
                # Feature versions
                if export_data["feature_versions"]:
                    pd.DataFrame(export_data["feature_versions"]).to_csv(
                        f"{base_path}_feature_versions.csv", index=False
                    )
                
                # Feature documentation
                if export_data["feature_documentation"]:
                    pd.DataFrame(export_data["feature_documentation"]).to_csv(
                        f"{base_path}_feature_documentation.csv", index=False
                    )
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Pipeline results exported to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export pipeline results: {str(e)}")
            raise
    
    def stop_monitoring(self):
        """Stop feature monitoring"""
        try:
            self.monitoring_active = False
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
            logger.info("Feature monitoring stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {str(e)}")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.stop_monitoring()

# Utility functions
def create_default_pipeline() -> FeatureEngineeringPipeline:
    """Create pipeline with default configuration"""
    config = PipelineConfig()
    return FeatureEngineeringPipeline(config)

def create_custom_pipeline(**kwargs) -> FeatureEngineeringPipeline:
    """Create pipeline with custom configuration"""
    config = PipelineConfig(**kwargs)
    return FeatureEngineeringPipeline(config)

if __name__ == "__main__":
    # Example usage
    pipeline = create_default_pipeline()
    
    # Test with sample data
    data_path = "test-food.jpg"
    if os.path.exists(data_path):
        try:
            result = pipeline.run_pipeline(data_path)
            print(f"Pipeline completed: {result.status.value}")
            print(f"Best selection: {result.best_selection.method.value if result.best_selection else 'None'}")
            
            # Get history
            history = pipeline.get_pipeline_history()
            print(f"Pipeline history: {len(history)} runs")
            
            # Export results
            pipeline.export_pipeline_results("pipeline_results.json")
            
        except Exception as e:
            print(f"Error: {str(e)}")
    else:
        print(f"Test image {data_path} not found")
