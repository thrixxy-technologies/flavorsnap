#!/usr/bin/env python3
"""
Feature Importance Analysis for FlavorSnap ML Model API
Comprehensive feature importance analysis with multiple methods and visualization
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import json
import pickle
import sqlite3
from pathlib import Path
import hashlib

# ML libraries
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.inspection import permutation_importance
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score, mean_squared_error
import shap
import eli5
from eli5.sklearn import PermutationImportance

# Import our modules
from feature_extraction import ExtractedFeatures, FeatureType
from feature_selection import SelectionResult, SelectionMethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ImportanceMethod(Enum):
    """Feature importance calculation methods"""
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    LOGISTIC_REGRESSION = "logistic_regression"
    PERMUTATION = "permutation"
    SHAP = "shap"
    ELI5 = "eli5"
    CORRELATION = "correlation"
    MUTUAL_INFORMATION = "mutual_information"
    VARIANCE = "variance"
    CUSTOM = "custom"

class AnalysisType(Enum):
    """Analysis types"""
    GLOBAL = "global"
    LOCAL = "local"
    TEMPORAL = "temporal"
    COMPARATIVE = "comparative"

@dataclass
class ImportanceConfig:
    """Feature importance analysis configuration"""
    # Analysis methods
    methods: List[ImportanceMethod] = None
    analysis_types: List[AnalysisType] = None
    
    # Model configuration
    task_type: str = "classification"  # "classification" or "regression"
    cv_folds: int = 5
    random_state: int = 42
    
    # SHAP configuration
    shap_background_samples: int = 100
    shap_explanation_samples: int = 50
    
    # Visualization configuration
    plot_top_features: int = 20
    plot_style: str = "seaborn"
    figure_size: Tuple[int, int] = (12, 8)
    save_plots: bool = True
    plot_format: str = "png"
    plot_dpi: int = 300
    
    # Output configuration
    output_directory: str = "feature_importance_analysis"
    database_path: str = "feature_importance.db"
    
    # Thresholds
    importance_threshold: float = 0.01
    correlation_threshold: float = 0.1
    
    def __post_init__(self):
        if self.methods is None:
            self.methods = [
                ImportanceMethod.RANDOM_FOREST,
                ImportanceMethod.GRADIENT_BOOSTING,
                ImportanceMethod.PERMUTATION,
                ImportanceMethod.SHAP
            ]
        if self.analysis_types is None:
            self.analysis_types = [AnalysisType.GLOBAL, AnalysisType.COMPARATIVE]

@dataclass
class ImportanceResult:
    """Feature importance result"""
    method: ImportanceMethod
    analysis_type: AnalysisType
    feature_names: List[str]
    importance_scores: np.ndarray
    feature_rankings: Dict[str, int]
    confidence_intervals: Optional[Dict[str, Tuple[float, float]]]
    metadata: Dict[str, Any]
    analysis_time: datetime
    plot_paths: Dict[str, str]

@dataclass
class ComparativeAnalysis:
    """Comparative analysis result"""
    comparison_id: str
    methods_compared: List[ImportanceMethod]
    agreement_scores: Dict[str, float]
    consensus_ranking: Dict[str, int]
    disagreement_features: List[str]
    metadata: Dict[str, Any]
    analysis_time: datetime

class FeatureImportanceAnalyzer:
    """Advanced feature importance analyzer"""
    
    def __init__(self, config: ImportanceConfig = None):
        self.config = config or ImportanceConfig()
        self.logger = logging.getLogger(__name__)
        
        # Analysis results
        self.importance_results = {}
        self.comparative_analyses = {}
        
        # Database
        self.db_path = self.config.database_path
        self._init_database()
        
        # Output directory
        self.output_dir = Path(self.config.output_directory)
        self.output_dir.mkdir(exist_ok=True)
        
        # Plotting setup
        if self.config.plot_style == "seaborn":
            sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = self.config.figure_size
        
        logger.info("FeatureImportanceAnalyzer initialized")
    
    def _init_database(self):
        """Initialize importance analysis database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Importance results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS importance_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    method TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    feature_names TEXT NOT NULL,
                    importance_scores TEXT NOT NULL,
                    feature_rankings TEXT NOT NULL,
                    confidence_intervals TEXT,
                    metadata TEXT,
                    analysis_time TEXT NOT NULL,
                    plot_paths TEXT
                )
            ''')
            
            # Comparative analyses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS comparative_analyses (
                    comparison_id TEXT PRIMARY KEY,
                    methods_compared TEXT NOT NULL,
                    agreement_scores TEXT NOT NULL,
                    consensus_ranking TEXT NOT NULL,
                    disagreement_features TEXT NOT NULL,
                    metadata TEXT,
                    analysis_time TEXT NOT NULL
                )
            ''')
            
            # Feature tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feature_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feature_name TEXT NOT NULL,
                    analysis_date TEXT NOT NULL,
                    importance_score REAL,
                    ranking INTEGER,
                    method TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Importance analysis database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def analyze_importance(self, X: Union[np.ndarray, pd.DataFrame], 
                          y: Union[np.ndarray, pd.Series],
                          feature_names: List[str] = None,
                          sample_data: Union[np.ndarray, pd.DataFrame] = None) -> Dict[ImportanceMethod, ImportanceResult]:
        """Perform comprehensive feature importance analysis"""
        try:
            # Prepare data
            X_df, feature_names = self._prepare_data(X, feature_names)
            
            results = {}
            
            for method in self.config.methods:
                try:
                    self.logger.info(f"Computing importance using {method.value}")
                    
                    if method == ImportanceMethod.RANDOM_FOREST:
                        result = self._random_forest_importance(X_df, y, feature_names)
                    elif method == ImportanceMethod.GRADIENT_BOOSTING:
                        result = self._gradient_boosting_importance(X_df, y, feature_names)
                    elif method == ImportanceMethod.LOGISTIC_REGRESSION:
                        result = self._logistic_regression_importance(X_df, y, feature_names)
                    elif method == ImportanceMethod.PERMUTATION:
                        result = self._permutation_importance(X_df, y, feature_names)
                    elif method == ImportanceMethod.SHAP:
                        result = self._shap_importance(X_df, y, feature_names, sample_data)
                    elif method == ImportanceMethod.ELI5:
                        result = self._eli5_importance(X_df, y, feature_names)
                    elif method == ImportanceMethod.CORRELATION:
                        result = self._correlation_importance(X_df, y, feature_names)
                    elif method == ImportanceMethod.MUTUAL_INFORMATION:
                        result = self._mutual_information_importance(X_df, y, feature_names)
                    elif method == ImportanceMethod.VARIANCE:
                        result = self._variance_importance(X_df, feature_names)
                    else:
                        self.logger.warning(f"Unknown method: {method.value}")
                        continue
                    
                    results[method] = result
                    self._save_importance_result(result)
                    
                    # Generate plots
                    if self.config.save_plots:
                        self._generate_importance_plots(result)
                    
                except Exception as e:
                    self.logger.error(f"Failed to compute importance with {method.value}: {str(e)}")
                    continue
            
            # Store results
            self.importance_results.update(results)
            
            # Perform comparative analysis
            if len(results) > 1:
                self._perform_comparative_analysis(results)
            
            self.logger.info(f"Completed importance analysis with {len(results)} methods")
            return results
            
        except Exception as e:
            logger.error(f"Importance analysis failed: {str(e)}")
            raise
    
    def _prepare_data(self, X: Union[np.ndarray, pd.DataFrame], 
                    feature_names: List[str] = None) -> Tuple[pd.DataFrame, List[str]]:
        """Prepare data for analysis"""
        try:
            # Convert to DataFrame
            if isinstance(X, np.ndarray):
                if feature_names is None:
                    feature_names = [f"feature_{i}" for i in range(X.shape[1])]
                X_df = pd.DataFrame(X, columns=feature_names)
            else:
                X_df = X.copy()
                if feature_names is None:
                    feature_names = X_df.columns.tolist()
            
            return X_df, feature_names
            
        except Exception as e:
            logger.error(f"Failed to prepare data: {str(e)}")
            raise
    
    def _random_forest_importance(self, X: pd.DataFrame, y: pd.Series, 
                                 feature_names: List[str]) -> ImportanceResult:
        """Random Forest feature importance"""
        try:
            # Create and train model
            if self.config.task_type == "classification":
                rf = RandomForestClassifier(
                    n_estimators=100,
                    random_state=self.config.random_state,
                    n_jobs=-1
                )
            else:
                rf = RandomForestRegressor(
                    n_estimators=100,
                    random_state=self.config.random_state,
                    n_jobs=-1
                )
            
            rf.fit(X, y)
            
            # Get importance scores
            importance_scores = rf.feature_importances_
            
            # Calculate rankings
            feature_rankings = self._calculate_rankings(feature_names, importance_scores)
            
            # Calculate confidence intervals using cross-validation
            confidence_intervals = self._calculate_confidence_intervals(
                X, y, rf, feature_names, importance_scores
            )
            
            result = ImportanceResult(
                method=ImportanceMethod.RANDOM_FOREST,
                analysis_type=AnalysisType.GLOBAL,
                feature_names=feature_names,
                importance_scores=importance_scores,
                feature_rankings=feature_rankings,
                confidence_intervals=confidence_intervals,
                metadata={
                    "model_type": "RandomForest",
                    "n_estimators": 100,
                    "task_type": self.config.task_type,
                    "oob_score": getattr(rf, 'oob_score_', None)
                },
                analysis_time=datetime.now(),
                plot_paths={}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Random Forest importance failed: {str(e)}")
            raise
    
    def _gradient_boosting_importance(self, X: pd.DataFrame, y: pd.Series, 
                                    feature_names: List[str]) -> ImportanceResult:
        """Gradient Boosting feature importance"""
        try:
            # Create and train model
            if self.config.task_type == "classification":
                gb = GradientBoostingClassifier(
                    n_estimators=100,
                    random_state=self.config.random_state
                )
            else:
                from sklearn.ensemble import GradientBoostingRegressor
                gb = GradientBoostingRegressor(
                    n_estimators=100,
                    random_state=self.config.random_state
                )
            
            gb.fit(X, y)
            
            # Get importance scores
            importance_scores = gb.feature_importances_
            
            # Calculate rankings
            feature_rankings = self._calculate_rankings(feature_names, importance_scores)
            
            # Calculate confidence intervals
            confidence_intervals = self._calculate_confidence_intervals(
                X, y, gb, feature_names, importance_scores
            )
            
            result = ImportanceResult(
                method=ImportanceMethod.GRADIENT_BOOSTING,
                analysis_type=AnalysisType.GLOBAL,
                feature_names=feature_names,
                importance_scores=importance_scores,
                feature_rankings=feature_rankings,
                confidence_intervals=confidence_intervals,
                metadata={
                    "model_type": "GradientBoosting",
                    "n_estimators": 100,
                    "task_type": self.config.task_type
                },
                analysis_time=datetime.now(),
                plot_paths={}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Gradient Boosting importance failed: {str(e)}")
            raise
    
    def _logistic_regression_importance(self, X: pd.DataFrame, y: pd.Series, 
                                       feature_names: List[str]) -> ImportanceResult:
        """Logistic Regression feature importance"""
        try:
            # Create and train model
            if self.config.task_type == "classification":
                lr = LogisticRegression(
                    random_state=self.config.random_state,
                    max_iter=1000
                )
            else:
                lr = LinearRegression()
            
            lr.fit(X, y)
            
            # Get importance scores (absolute coefficients)
            if hasattr(lr, 'coef_'):
                if lr.coef_.ndim == 2:
                    importance_scores = np.mean(np.abs(lr.coef_), axis=0)
                else:
                    importance_scores = np.abs(lr.coef_)
            else:
                importance_scores = np.zeros(len(feature_names))
            
            # Calculate rankings
            feature_rankings = self._calculate_rankings(feature_names, importance_scores)
            
            # Calculate confidence intervals
            confidence_intervals = self._calculate_confidence_intervals(
                X, y, lr, feature_names, importance_scores
            )
            
            result = ImportanceResult(
                method=ImportanceMethod.LOGISTIC_REGRESSION,
                analysis_type=AnalysisType.GLOBAL,
                feature_names=feature_names,
                importance_scores=importance_scores,
                feature_rankings=feature_rankings,
                confidence_intervals=confidence_intervals,
                metadata={
                    "model_type": "LogisticRegression" if self.config.task_type == "classification" else "LinearRegression",
                    "task_type": self.config.task_type
                },
                analysis_time=datetime.now(),
                plot_paths={}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Logistic Regression importance failed: {str(e)}")
            raise
    
    def _permutation_importance(self, X: pd.DataFrame, y: pd.Series, 
                               feature_names: List[str]) -> ImportanceResult:
        """Permutation importance"""
        try:
            # Create base model
            if self.config.task_type == "classification":
                base_model = RandomForestClassifier(
                    n_estimators=50,
                    random_state=self.config.random_state
                )
            else:
                base_model = RandomForestRegressor(
                    n_estimators=50,
                    random_state=self.config.random_state
                )
            
            # Calculate permutation importance
            perm_importance = permutation_importance(
                base_model, X, y,
                n_repeats=10,
                random_state=self.config.random_state,
                scoring='accuracy' if self.config.task_type == "classification" else 'neg_mean_squared_error'
            )
            
            importance_scores = perm_importance.importances_mean
            
            # Calculate rankings
            feature_rankings = self._calculate_rankings(feature_names, importance_scores)
            
            # Calculate confidence intervals
            confidence_intervals = {}
            for i, feature in enumerate(feature_names):
                lower = np.percentile(perm_importance.importances[i], 2.5)
                upper = np.percentile(perm_importance.importances[i], 97.5)
                confidence_intervals[feature] = (lower, upper)
            
            result = ImportanceResult(
                method=ImportanceMethod.PERMUTATION,
                analysis_type=AnalysisType.GLOBAL,
                feature_names=feature_names,
                importance_scores=importance_scores,
                feature_rankings=feature_rankings,
                confidence_intervals=confidence_intervals,
                metadata={
                    "method": "PermutationImportance",
                    "n_repeats": 10,
                    "task_type": self.config.task_type
                },
                analysis_time=datetime.now(),
                plot_paths={}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Permutation importance failed: {str(e)}")
            raise
    
    def _shap_importance(self, X: pd.DataFrame, y: pd.Series, 
                        feature_names: List[str],
                        sample_data: Union[np.ndarray, pd.DataFrame] = None) -> ImportanceResult:
        """SHAP feature importance"""
        try:
            # Create and train model
            if self.config.task_type == "classification":
                model = RandomForestClassifier(
                    n_estimators=50,
                    random_state=self.config.random_state
                )
            else:
                model = RandomForestRegressor(
                    n_estimators=50,
                    random_state=self.config.random_state
                )
            
            model.fit(X, y)
            
            # Prepare background data
            if sample_data is not None:
                background_data = sample_data[:self.config.shap_background_samples]
            else:
                background_data = X.sample(min(self.config.shap_background_samples, len(X)), random_state=self.config.random_state)
            
            # Create SHAP explainer
            explainer = shap.TreeExplainer(model, background_data)
            
            # Calculate SHAP values
            sample_indices = np.random.choice(len(X), min(self.config.shap_explanation_samples, len(X)), replace=False)
            shap_values = explainer.shap_values(X.iloc[sample_indices])
            
            # Handle multi-class case
            if isinstance(shap_values, list):
                # Average across classes
                shap_values = np.mean([np.abs(values).mean(axis=0) for values in shap_values], axis=0)
            else:
                shap_values = np.abs(shap_values).mean(axis=0)
            
            importance_scores = shap_values
            
            # Calculate rankings
            feature_rankings = self._calculate_rankings(feature_names, importance_scores)
            
            # No confidence intervals for SHAP (would require more complex bootstrapping)
            confidence_intervals = None
            
            result = ImportanceResult(
                method=ImportanceMethod.SHAP,
                analysis_type=AnalysisType.GLOBAL,
                feature_names=feature_names,
                importance_scores=importance_scores,
                feature_rankings=feature_rankings,
                confidence_intervals=confidence_intervals,
                metadata={
                    "method": "SHAP",
                    "background_samples": len(background_data),
                    "explanation_samples": len(sample_indices),
                    "task_type": self.config.task_type
                },
                analysis_time=datetime.now(),
                plot_paths={}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"SHAP importance failed: {str(e)}")
            raise
    
    def _eli5_importance(self, X: pd.DataFrame, y: pd.Series, 
                        feature_names: List[str]) -> ImportanceResult:
        """ELI5 permutation importance"""
        try:
            # Create base model
            if self.config.task_type == "classification":
                model = RandomForestClassifier(
                    n_estimators=50,
                    random_state=self.config.random_state
                )
            else:
                model = RandomForestRegressor(
                    n_estimators=50,
                    random_state=self.config.random_state
                )
            
            model.fit(X, y)
            
            # Calculate ELI5 permutation importance
            perm = PermutationImportance(
                model,
                random_state=self.config.random_state,
                scoring='accuracy' if self.config.task_type == "classification" else 'neg_mean_squared_error'
            )
            perm.fit(X, y)
            
            # Get importance scores
            importance_scores = perm.feature_importances_
            
            # Calculate rankings
            feature_rankings = self._calculate_rankings(feature_names, importance_scores)
            
            # Calculate confidence intervals
            confidence_intervals = {}
            for i, feature in enumerate(feature_names):
                lower = perm.feature_importances_[i] - 2 * perm.feature_importances_std_[i]
                upper = perm.feature_importances_[i] + 2 * perm.feature_importances_std_[i]
                confidence_intervals[feature] = (lower, upper)
            
            result = ImportanceResult(
                method=ImportanceMethod.ELI5,
                analysis_type=AnalysisType.GLOBAL,
                feature_names=feature_names,
                importance_scores=importance_scores,
                feature_rankings=feature_rankings,
                confidence_intervals=confidence_intervals,
                metadata={
                    "method": "ELI5",
                    "task_type": self.config.task_type
                },
                analysis_time=datetime.now(),
                plot_paths={}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"ELI5 importance failed: {str(e)}")
            raise
    
    def _correlation_importance(self, X: pd.DataFrame, y: pd.Series, 
                               feature_names: List[str]) -> ImportanceResult:
        """Correlation-based feature importance"""
        try:
            # Calculate correlation with target
            importance_scores = []
            
            for feature in feature_names:
                if self.config.task_type == "classification":
                    # For classification, use point-biserial correlation
                    correlation = abs(np.corrcoef(X[feature], y)[0, 1])
                else:
                    # For regression, use Pearson correlation
                    correlation = abs(np.corrcoef(X[feature], y)[0, 1])
                
                importance_scores.append(abs(correlation))
            
            importance_scores = np.array(importance_scores)
            
            # Calculate rankings
            feature_rankings = self._calculate_rankings(feature_names, importance_scores)
            
            # No confidence intervals for correlation
            confidence_intervals = None
            
            result = ImportanceResult(
                method=ImportanceMethod.CORRELATION,
                analysis_type=AnalysisType.GLOBAL,
                feature_names=feature_names,
                importance_scores=importance_scores,
                feature_rankings=feature_rankings,
                confidence_intervals=confidence_intervals,
                metadata={
                    "method": "Correlation",
                    "task_type": self.config.task_type
                },
                analysis_time=datetime.now(),
                plot_paths={}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Correlation importance failed: {str(e)}")
            raise
    
    def _mutual_information_importance(self, X: pd.DataFrame, y: pd.Series, 
                                     feature_names: List[str]) -> ImportanceResult:
        """Mutual information feature importance"""
        try:
            from sklearn.feature_selection import mutual_info_classif, mutual_info_regression
            
            # Calculate mutual information
            if self.config.task_type == "classification":
                mi_scores = mutual_info_classif(X, y, random_state=self.config.random_state)
            else:
                mi_scores = mutual_info_regression(X, y, random_state=self.config.random_state)
            
            importance_scores = mi_scores
            
            # Calculate rankings
            feature_rankings = self._calculate_rankings(feature_names, importance_scores)
            
            # No confidence intervals for mutual information
            confidence_intervals = None
            
            result = ImportanceResult(
                method=ImportanceMethod.MUTUAL_INFORMATION,
                analysis_type=AnalysisType.GLOBAL,
                feature_names=feature_names,
                importance_scores=importance_scores,
                feature_rankings=feature_rankings,
                confidence_intervals=confidence_intervals,
                metadata={
                    "method": "MutualInformation",
                    "task_type": self.config.task_type
                },
                analysis_time=datetime.now(),
                plot_paths={}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Mutual information importance failed: {str(e)}")
            raise
    
    def _variance_importance(self, X: pd.DataFrame, feature_names: List[str]) -> ImportanceResult:
        """Variance-based feature importance"""
        try:
            # Calculate variance for each feature
            importance_scores = X.var().values
            
            # Calculate rankings
            feature_rankings = self._calculate_rankings(feature_names, importance_scores)
            
            # No confidence intervals for variance
            confidence_intervals = None
            
            result = ImportanceResult(
                method=ImportanceMethod.VARIANCE,
                analysis_type=AnalysisType.GLOBAL,
                feature_names=feature_names,
                importance_scores=importance_scores,
                feature_rankings=feature_rankings,
                confidence_intervals=confidence_intervals,
                metadata={
                    "method": "Variance"
                },
                analysis_time=datetime.now(),
                plot_paths={}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Variance importance failed: {str(e)}")
            raise
    
    def _calculate_rankings(self, feature_names: List[str], importance_scores: np.ndarray) -> Dict[str, int]:
        """Calculate feature rankings from importance scores"""
        try:
            # Sort features by importance (descending)
            sorted_indices = np.argsort(importance_scores)[::-1]
            
            # Create ranking dictionary
            rankings = {}
            for rank, idx in enumerate(sorted_indices, 1):
                rankings[feature_names[idx]] = rank
            
            return rankings
            
        except Exception as e:
            logger.error(f"Failed to calculate rankings: {str(e)}")
            return {}
    
    def _calculate_confidence_intervals(self, X: pd.DataFrame, y: pd.Series, 
                                      model, feature_names: List[str], 
                                      importance_scores: np.ndarray) -> Dict[str, Tuple[float, float]]:
        """Calculate confidence intervals for importance scores"""
        try:
            confidence_intervals = {}
            
            # Use cross-validation to estimate variability
            cv_scores = []
            
            for _ in range(self.config.cv_folds):
                # Sample with replacement
                indices = np.random.choice(len(X), len(X), replace=True)
                X_boot = X.iloc[indices]
                y_boot = y.iloc[indices]
                
                # Train model on bootstrap sample
                model.fit(X_boot, y_boot)
                
                # Get importance scores
                if hasattr(model, 'feature_importances_'):
                    boot_scores = model.feature_importances_
                elif hasattr(model, 'coef_'):
                    if model.coef_.ndim == 2:
                        boot_scores = np.mean(np.abs(model.coef_), axis=0)
                    else:
                        boot_scores = np.abs(model.coef_)
                else:
                    continue
                
                cv_scores.append(boot_scores)
            
            if cv_scores:
                cv_scores = np.array(cv_scores)
                
                # Calculate confidence intervals
                for i, feature in enumerate(feature_names):
                    scores = cv_scores[:, i]
                    lower = np.percentile(scores, 2.5)
                    upper = np.percentile(scores, 97.5)
                    confidence_intervals[feature] = (lower, upper)
            
            return confidence_intervals
            
        except Exception as e:
            logger.error(f"Failed to calculate confidence intervals: {str(e)}")
            return {}
    
    def _generate_importance_plots(self, result: ImportanceResult):
        """Generate importance plots"""
        try:
            # Create plot directory
            plot_dir = self.output_dir / "plots"
            plot_dir.mkdir(exist_ok=True)
            
            # Sort features by importance
            sorted_indices = np.argsort(result.importance_scores)[::-1]
            top_n = min(self.config.plot_top_features, len(result.feature_names))
            
            # Plot 1: Bar plot of top features
            plt.figure(figsize=self.config.figure_size)
            top_features = [result.feature_names[i] for i in sorted_indices[:top_n]]
            top_scores = [result.importance_scores[i] for i in sorted_indices[:top_n]]
            
            plt.barh(range(len(top_features)), top_scores)
            plt.yticks(range(len(top_features)), top_features)
            plt.xlabel('Importance Score')
            plt.title(f'Top {top_n} Features - {result.method.value}')
            plt.gca().invert_yaxis()
            
            plot_path = plot_dir / f"importance_{result.method.value}.{self.config.plot_format}"
            plt.savefig(plot_path, dpi=self.config.plot_dpi, bbox_inches='tight')
            plt.close()
            
            result.plot_paths['bar_plot'] = str(plot_path)
            
            # Plot 2: With confidence intervals if available
            if result.confidence_intervals:
                plt.figure(figsize=self.config.figure_size)
                
                means = top_scores
                errors = []
                for feature in top_features:
                    if feature in result.confidence_intervals:
                        lower, upper = result.confidence_intervals[feature]
                        errors.append([means[top_features.index(feature)] - lower, upper - means[top_features.index(feature)]])
                    else:
                        errors.append([0, 0])
                
                errors = np.array(errors).T
                
                plt.barh(range(len(top_features)), means, xerr=errors, alpha=0.7, capsize=5)
                plt.yticks(range(len(top_features)), top_features)
                plt.xlabel('Importance Score')
                plt.title(f'Top {top_n} Features with CI - {result.method.value}')
                plt.gca().invert_yaxis()
                
                ci_plot_path = plot_dir / f"importance_ci_{result.method.value}.{self.config.plot_format}"
                plt.savefig(ci_plot_path, dpi=self.config.plot_dpi, bbox_inches='tight')
                plt.close()
                
                result.plot_paths['ci_plot'] = str(ci_plot_path)
            
            self.logger.info(f"Generated plots for {result.method.value}")
            
        except Exception as e:
            logger.error(f"Failed to generate plots for {result.method.value}: {str(e)}")
    
    def _perform_comparative_analysis(self, results: Dict[ImportanceMethod, ImportanceResult]):
        """Perform comparative analysis of different methods"""
        try:
            comparison_id = str(hashlib.md5(
                f"{list(results.keys())}_{datetime.now()}".encode()
            ).hexdigest())
            
            methods_compared = list(results.keys())
            
            # Calculate agreement scores
            agreement_scores = self._calculate_agreement_scores(results)
            
            # Calculate consensus ranking
            consensus_ranking = self._calculate_consensus_ranking(results)
            
            # Find disagreement features
            disagreement_features = self._find_disagreement_features(results)
            
            comparative_result = ComparativeAnalysis(
                comparison_id=comparison_id,
                methods_compared=methods_compared,
                agreement_scores=agreement_scores,
                consensus_ranking=consensus_ranking,
                disagreement_features=disagreement_features,
                metadata={
                    "n_methods": len(methods_compared),
                    "analysis_type": "global_comparison"
                },
                analysis_time=datetime.now()
            )
            
            self.comparative_analyses[comparison_id] = comparative_result
            self._save_comparative_analysis(comparative_result)
            
            # Generate comparative plots
            self._generate_comparative_plots(results, comparative_result)
            
            self.logger.info(f"Completed comparative analysis: {comparison_id}")
            
        except Exception as e:
            logger.error(f"Comparative analysis failed: {str(e)}")
    
    def _calculate_agreement_scores(self, results: Dict[ImportanceMethod, ImportanceResult]) -> Dict[str, float]:
        """Calculate agreement scores between methods"""
        try:
            agreement_scores = {}
            feature_names = list(results.values())[0].feature_names
            
            for feature in feature_names:
                rankings = []
                for result in results.values():
                    rankings.append(result.feature_rankings.get(feature, len(feature_names)))
                
                # Calculate Spearman correlation of rankings
                if len(rankings) > 1:
                    from scipy.stats import spearmanr
                    correlations = []
                    for i in range(len(rankings)):
                        for j in range(i + 1, len(rankings)):
                            corr, _ = spearmanr([rankings[i]], [rankings[j]])
                            correlations.append(abs(corr))
                    
                    agreement_scores[feature] = np.mean(correlations) if correlations else 0.0
                else:
                    agreement_scores[feature] = 1.0
            
            return agreement_scores
            
        except Exception as e:
            logger.error(f"Failed to calculate agreement scores: {str(e)}")
            return {}
    
    def _calculate_consensus_ranking(self, results: Dict[ImportanceMethod, ImportanceResult]) -> Dict[str, int]:
        """Calculate consensus ranking across methods"""
        try:
            feature_names = list(results.values())[0].feature_names
            consensus_scores = {}
            
            for feature in feature_names:
                scores = []
                for result in results.values():
                    if feature in result.feature_rankings:
                        # Use inverse ranking (higher importance = lower rank number)
                        score = 1.0 / result.feature_rankings[feature]
                        scores.append(score)
                
                consensus_scores[feature] = np.mean(scores) if scores else 0.0
            
            # Convert scores to rankings
            sorted_features = sorted(consensus_scores.items(), key=lambda x: x[1], reverse=True)
            consensus_ranking = {feature: rank + 1 for rank, (feature, score) in enumerate(sorted_features)}
            
            return consensus_ranking
            
        except Exception as e:
            logger.error(f"Failed to calculate consensus ranking: {str(e)}")
            return {}
    
    def _find_disagreement_features(self, results: Dict[ImportanceMethod, ImportanceResult]) -> List[str]:
        """Find features with high disagreement between methods"""
        try:
            disagreement_features = []
            feature_names = list(results.values())[0].feature_names
            
            for feature in feature_names:
                rankings = []
                for result in results.values():
                    rankings.append(result.feature_rankings.get(feature, len(feature_names)))
                
                # Calculate standard deviation of rankings
                ranking_std = np.std(rankings)
                
                # High disagreement if std is high
                if ranking_std > len(rankings) / 4:  # Threshold for high disagreement
                    disagreement_features.append(feature)
            
            return disagreement_features
            
        except Exception as e:
            logger.error(f"Failed to find disagreement features: {str(e)}")
            return []
    
    def _generate_comparative_plots(self, results: Dict[ImportanceMethod, ImportanceResult], 
                                   comparative_result: ComparativeAnalysis):
        """Generate comparative analysis plots"""
        try:
            plot_dir = self.output_dir / "plots"
            plot_dir.mkdir(exist_ok=True)
            
            # Plot 1: Heatmap of rankings across methods
            feature_names = list(results.values())[0].feature_names
            top_features = sorted(
                comparative_result.consensus_ranking.items(), 
                key=lambda x: x[1]
            )[:self.config.plot_top_features]
            
            ranking_matrix = []
            method_names = []
            
            for method, result in results.items():
                rankings = []
                for feature, _ in top_features:
                    rankings.append(result.feature_rankings.get(feature, len(feature_names)))
                ranking_matrix.append(rankings)
                method_names.append(method.value)
            
            plt.figure(figsize=self.config.figure_size)
            sns.heatmap(ranking_matrix, 
                       xticklabels=[f[0] for f in top_features],
                       yticklabels=method_names,
                       annot=True, 
                       cmap='RdYlBu_r',
                       cbar_kws={'label': 'Ranking'})
            plt.title('Feature Rankings Across Methods')
            plt.xlabel('Features')
            plt.ylabel('Methods')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            heatmap_path = plot_dir / f"ranking_heatmap.{self.config.plot_format}"
            plt.savefig(heatmap_path, dpi=self.config.plot_dpi, bbox_inches='tight')
            plt.close()
            
            # Plot 2: Agreement scores
            agreement_scores = comparative_result.agreement_scores
            if agreement_scores:
                plt.figure(figsize=self.config.figure_size)
                
                features = list(agreement_scores.keys())
                scores = list(agreement_scores.values())
                
                # Sort by agreement score
                sorted_indices = np.argsort(scores)[::-1]
                top_agreement_features = [features[i] for i in sorted_indices[:self.config.plot_top_features]]
                top_agreement_scores = [scores[i] for i in sorted_indices[:self.config.plot_top_features]]
                
                plt.barh(range(len(top_agreement_features)), top_agreement_scores)
                plt.yticks(range(len(top_agreement_features)), top_agreement_features)
                plt.xlabel('Agreement Score')
                plt.title('Feature Agreement Across Methods')
                plt.gca().invert_yaxis()
                
                agreement_plot_path = plot_dir / f"agreement_scores.{self.config.plot_format}"
                plt.savefig(agreement_plot_path, dpi=self.config.plot_dpi, bbox_inches='tight')
                plt.close()
            
            self.logger.info("Generated comparative analysis plots")
            
        except Exception as e:
            logger.error(f"Failed to generate comparative plots: {str(e)}")
    
    def _save_importance_result(self, result: ImportanceResult):
        """Save importance result to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO importance_results 
                (method, analysis_type, feature_names, importance_scores, 
                 feature_rankings, confidence_intervals, metadata, analysis_time, plot_paths)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.method.value,
                result.analysis_type.value,
                json.dumps(result.feature_names),
                json.dumps(result.importance_scores.tolist()),
                json.dumps(result.feature_rankings),
                json.dumps(result.confidence_intervals) if result.confidence_intervals else None,
                json.dumps(result.metadata),
                result.analysis_time.isoformat(),
                json.dumps(result.plot_paths)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save importance result: {str(e)}")
    
    def _save_comparative_analysis(self, comparative_result: ComparativeAnalysis):
        """Save comparative analysis to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO comparative_analyses 
                (comparison_id, methods_compared, agreement_scores, 
                 consensus_ranking, disagreement_features, metadata, analysis_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                comparative_result.comparison_id,
                json.dumps([m.value for m in comparative_result.methods_compared]),
                json.dumps(comparative_result.agreement_scores),
                json.dumps(comparative_result.consensus_ranking),
                json.dumps(comparative_result.disagreement_features),
                json.dumps(comparative_result.metadata),
                comparative_result.analysis_time.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save comparative analysis: {str(e)}")
    
    def get_importance_summary(self) -> Dict[str, Any]:
        """Get summary of importance analyses"""
        try:
            summary = {
                "total_analyses": len(self.importance_results),
                "methods_used": list(self.importance_results.keys()),
                "comparative_analyses": len(self.comparative_analyses),
                "feature_count": len(list(self.importance_results.values())[0].feature_names) if self.importance_results else 0,
                "analysis_types": list(set(r.analysis_type for r in self.importance_results.values())),
                "latest_analysis": max([r.analysis_time for r in self.importance_results.values()]).isoformat() if self.importance_results else None
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get importance summary: {str(e)}")
            return {}
    
    def export_results(self, output_path: str, format: str = "json"):
        """Export importance analysis results"""
        try:
            export_data = {
                "importance_results": {},
                "comparative_analyses": {},
                "summary": self.get_importance_summary(),
                "config": asdict(self.config)
            }
            
            # Convert importance results to serializable format
            for method, result in self.importance_results.items():
                export_data["importance_results"][method.value] = {
                    "method": result.method.value,
                    "analysis_type": result.analysis_type.value,
                    "feature_names": result.feature_names,
                    "importance_scores": result.importance_scores.tolist(),
                    "feature_rankings": result.feature_rankings,
                    "confidence_intervals": result.confidence_intervals,
                    "metadata": result.metadata,
                    "analysis_time": result.analysis_time.isoformat(),
                    "plot_paths": result.plot_paths
                }
            
            # Convert comparative analyses to serializable format
            for comp_id, comp_result in self.comparative_analyses.items():
                export_data["comparative_analyses"][comp_id] = {
                    "comparison_id": comp_result.comparison_id,
                    "methods_compared": [m.value for m in comp_result.methods_compared],
                    "agreement_scores": comp_result.agreement_scores,
                    "consensus_ranking": comp_result.consensus_ranking,
                    "disagreement_features": comp_result.disagreement_features,
                    "metadata": comp_result.metadata,
                    "analysis_time": comp_result.analysis_time.isoformat()
                }
            
            if format.lower() == "json":
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            
            elif format.lower() == "csv":
                # Export importance results as CSV
                if export_data["importance_results"]:
                    # Create summary DataFrame
                    summary_data = []
                    for method, result in export_data["importance_results"].items():
                        for i, feature in enumerate(result["feature_names"]):
                            summary_data.append({
                                "method": method,
                                "feature": feature,
                                "importance_score": result["importance_scores"][i],
                                "ranking": result["feature_rankings"][feature],
                                "analysis_time": result["analysis_time"]
                            })
                    
                    df = pd.DataFrame(summary_data)
                    df.to_csv(output_path, index=False)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Importance analysis results exported to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export results: {str(e)}")
            raise

# Utility functions
def create_default_analyzer(task_type: str = "classification") -> FeatureImportanceAnalyzer:
    """Create analyzer with default configuration"""
    config = ImportanceConfig(task_type=task_type)
    return FeatureImportanceAnalyzer(config)

def create_custom_analyzer(**kwargs) -> FeatureImportanceAnalyzer:
    """Create analyzer with custom configuration"""
    config = ImportanceConfig(**kwargs)
    return FeatureImportanceAnalyzer(config)

if __name__ == "__main__":
    # Example usage
    analyzer = create_default_analyzer()
    
    # Generate sample data
    from sklearn.datasets import make_classification
    X, y = make_classification(n_samples=100, n_features=20, n_informative=10, 
                              n_redundant=5, random_state=42)
    
    feature_names = [f"feature_{i}" for i in range(X.shape[1])]
    
    try:
        results = analyzer.analyze_importance(X, y, feature_names)
        print(f"Completed importance analysis with {len(results)} methods")
        
        # Get summary
        summary = analyzer.get_importance_summary()
        print(f"Summary: {summary}")
        
        # Export results
        analyzer.export_results("importance_results.json")
        
    except Exception as e:
        print(f"Error: {str(e)}")
