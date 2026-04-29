#!/usr/bin/env python3
"""
Advanced Feature Selection for FlavorSnap ML Model API
Implements various feature selection algorithms and techniques for optimal feature subset selection
"""

import os
import numpy as np
import pandas as pd
import json
import logging
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import pickle
from sklearn.feature_selection import (
    SelectKBest, SelectPercentile, RFE, RFECV,
    VarianceThreshold, SelectFromModel, mutual_info_classif,
    chi2, f_classif, f_regression
)
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import Lasso, LogisticRegression
from sklearn.svm import SVC, SVR
from sklearn.metrics import accuracy_score, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from scipy.stats import pearsonr, spearmanr
from scipy.cluster.hierarchy import linkage, fcluster
from itertools import combinations
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SelectionMethod(Enum):
    """Feature selection methods"""
    VARIANCE_THRESHOLD = "variance_threshold"
    CORRELATION_FILTER = "correlation_filter"
    MUTUAL_INFORMATION = "mutual_information"
    CHI_SQUARE = "chi_square"
    ANOVA_F = "anova_f"
    RECURSIVE_FEATURE_ELIMINATION = "recursive_feature_elimination"
    LASSO_SELECTION = "lasso_selection"
    RANDOM_FOREST_IMPORTANCE = "random_forest_importance"
    BORUTA = "boruta"
    GENETIC_ALGORITHM = "genetic_algorithm"
    SEQUENTIAL_FORWARD = "sequential_forward"
    SEQUENTIAL_BACKWARD = "sequential_backward"
    BIDIRECTIONAL = "bidirectional"
    CLUSTER_BASED = "cluster_based"

class SelectionStrategy(Enum):
    """Feature selection strategies"""
    FILTER = "filter"
    WRAPPER = "wrapper"
    EMBEDDED = "embedded"
    HYBRID = "hybrid"

@dataclass
class SelectionConfig:
    """Feature selection configuration"""
    # General settings
    task_type: str = "classification"  # "classification" or "regression"
    max_features: Optional[int] = None
    min_features: int = 5
    cv_folds: int = 5
    random_state: int = 42
    
    # Filter method settings
    variance_threshold: float = 0.01
    correlation_threshold: float = 0.95
    mutual_info_k: int = 50
    chi2_k: int = 50
    anova_f_k: int = 50
    
    # Wrapper method settings
    rfe_step: float = 0.1
    sequential_features: int = 50
    bidirectional_features: int = 50
    
    # Embedded method settings
    lasso_alpha: float = 0.01
    rf_n_estimators: int = 100
    rf_max_depth: Optional[int] = None
    
    # Advanced method settings
    boruta_max_iter: int = 100
    genetic_population_size: int = 50
    genetic_generations: int = 50
    genetic_mutation_rate: float = 0.1
    
    # Evaluation settings
    evaluation_metric: str = "accuracy"  # "accuracy", "f1", "roc_auc", "mse", "r2"
    scoring_strategy: str = "mean"  # "mean", "median", "max"

@dataclass
class SelectionResult:
    """Feature selection result"""
    method: SelectionMethod
    strategy: SelectionStrategy
    selected_features: List[str]
    feature_scores: Dict[str, float]
    feature_rankings: Dict[str, int]
    performance_score: float
    selection_time: datetime
    metadata: Dict[str, Any]
    cross_val_scores: List[float]

class FeatureSelector:
    """Advanced feature selection system"""
    
    def __init__(self, config: SelectionConfig = None):
        self.config = config or SelectionConfig()
        self.logger = logging.getLogger(__name__)
        
        # Selection history
        self.selection_history = []
        self.best_selection = None
        
        # Feature cache
        self.feature_cache = {}
        self.cache_file = "feature_selection_cache.pkl"
        
        # Initialize components
        self._load_cache()
        
        logger.info("FeatureSelector initialized")
    
    def _load_cache(self):
        """Load feature selection cache"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    self.feature_cache = pickle.load(f)
                logger.info(f"Loaded {len(self.feature_cache)} cached selections")
        except Exception as e:
            logger.error(f"Failed to load cache: {str(e)}")
            self.feature_cache = {}
    
    def _save_cache(self):
        """Save feature selection cache"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.feature_cache, f)
        except Exception as e:
            logger.error(f"Failed to save cache: {str(e)}")
    
    def select_features(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series],
                       feature_names: List[str] = None, methods: List[SelectionMethod] = None) -> Dict[SelectionMethod, SelectionResult]:
        """Perform feature selection using specified methods"""
        try:
            # Convert to DataFrame if needed
            if isinstance(X, np.ndarray):
                if feature_names is None:
                    feature_names = [f"feature_{i}" for i in range(X.shape[1])]
                X = pd.DataFrame(X, columns=feature_names)
            
            if isinstance(y, np.ndarray):
                y = pd.Series(y)
            
            # Default methods
            if methods is None:
                methods = [
                    SelectionMethod.VARIANCE_THRESHOLD,
                    SelectionMethod.CORRELATION_FILTER,
                    SelectionMethod.MUTUAL_INFORMATION,
                    SelectionMethod.RANDOM_FOREST_IMPORTANCE,
                    SelectionMethod.RECURSIVE_FEATURE_ELIMINATION
                ]
            
            # Check cache
            cache_key = self._generate_cache_key(X, y, methods)
            if cache_key in self.feature_cache:
                logger.info("Feature selection loaded from cache")
                return self.feature_cache[cache_key]
            
            results = {}
            
            for method in methods:
                try:
                    self.logger.info(f"Applying {method.value} selection")
                    result = self._apply_selection_method(X, y, method)
                    results[method] = result
                    self.selection_history.append(result)
                    
                except Exception as e:
                    self.logger.error(f"Failed to apply {method.value}: {str(e)}")
                    continue
            
            # Cache results
            self.feature_cache[cache_key] = results
            self._save_cache()
            
            # Find best selection
            self._update_best_selection(results)
            
            logger.info(f"Completed feature selection with {len(results)} methods")
            return results
            
        except Exception as e:
            logger.error(f"Feature selection failed: {str(e)}")
            raise
    
    def _apply_selection_method(self, X: pd.DataFrame, y: pd.Series, 
                               method: SelectionMethod) -> SelectionResult:
        """Apply specific feature selection method"""
        start_time = datetime.now()
        
        if method == SelectionMethod.VARIANCE_THRESHOLD:
            return self._variance_threshold_selection(X, y, start_time)
        elif method == SelectionMethod.CORRELATION_FILTER:
            return self._correlation_filter_selection(X, y, start_time)
        elif method == SelectionMethod.MUTUAL_INFORMATION:
            return self._mutual_information_selection(X, y, start_time)
        elif method == SelectionMethod.CHI_SQUARE:
            return self._chi_square_selection(X, y, start_time)
        elif method == SelectionMethod.ANOVA_F:
            return self._anova_f_selection(X, y, start_time)
        elif method == SelectionMethod.RECURSIVE_FEATURE_ELIMINATION:
            return self._recursive_feature_elimination_selection(X, y, start_time)
        elif method == SelectionMethod.LASSO_SELECTION:
            return self._lasso_selection(X, y, start_time)
        elif method == SelectionMethod.RANDOM_FOREST_IMPORTANCE:
            return self._random_forest_importance_selection(X, y, start_time)
        elif method == SelectionMethod.BORUTA:
            return self._boruta_selection(X, y, start_time)
        elif method == SelectionMethod.GENETIC_ALGORITHM:
            return self._genetic_algorithm_selection(X, y, start_time)
        elif method == SelectionMethod.SEQUENTIAL_FORWARD:
            return self._sequential_forward_selection(X, y, start_time)
        elif method == SelectionMethod.SEQUENTIAL_BACKWARD:
            return self._sequential_backward_selection(X, y, start_time)
        elif method == SelectionMethod.BIDIRECTIONAL:
            return self._bidirectional_selection(X, y, start_time)
        elif method == SelectionMethod.CLUSTER_BASED:
            return self._cluster_based_selection(X, y, start_time)
        else:
            raise ValueError(f"Unknown selection method: {method}")
    
    def _variance_threshold_selection(self, X: pd.DataFrame, y: pd.Series, 
                                    start_time: datetime) -> SelectionResult:
        """Variance threshold feature selection"""
        try:
            selector = VarianceThreshold(threshold=self.config.variance_threshold)
            X_selected = selector.fit_transform(X)
            
            # Get selected features
            selected_mask = selector.get_support()
            selected_features = X.columns[selected_mask].tolist()
            
            # Calculate scores (variance values)
            feature_scores = {}
            for i, feature in enumerate(X.columns):
                if selected_mask[i]:
                    feature_scores[feature] = np.var(X[feature])
                else:
                    feature_scores[feature] = np.var(X[feature])
            
            # Rank features by variance
            feature_rankings = self._rank_features_by_scores(feature_scores)
            
            # Evaluate performance
            performance_score, cv_scores = self._evaluate_selection(X_selected, y)
            
            metadata = {
                "threshold": self.config.variance_threshold,
                "original_features": len(X.columns),
                "selected_features": len(selected_features),
                "reduction_ratio": len(selected_features) / len(X.columns)
            }
            
            return SelectionResult(
                method=SelectionMethod.VARIANCE_THRESHOLD,
                strategy=SelectionStrategy.FILTER,
                selected_features=selected_features,
                feature_scores=feature_scores,
                feature_rankings=feature_rankings,
                performance_score=performance_score,
                selection_time=start_time,
                metadata=metadata,
                cross_val_scores=cv_scores
            )
            
        except Exception as e:
            logger.error(f"Variance threshold selection failed: {str(e)}")
            raise
    
    def _correlation_filter_selection(self, X: pd.DataFrame, y: pd.Series, 
                                    start_time: datetime) -> SelectionResult:
        """Correlation-based feature selection"""
        try:
            # Calculate correlation matrix
            corr_matrix = X.corr().abs()
            
            # Find highly correlated features
            upper_triangle = corr_matrix.where(
                np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
            )
            
            # Identify features to remove
            to_remove = set()
            for col in upper_triangle.columns:
                for row in upper_triangle.index:
                    if upper_triangle.loc[row, col] > self.config.correlation_threshold:
                        # Remove feature with lower correlation with target
                        target_corr_row = abs(X[row].corr(y))
                        target_corr_col = abs(X[col].corr(y))
                        
                        if target_corr_row < target_corr_col:
                            to_remove.add(row)
                        else:
                            to_remove.add(col)
            
            # Get selected features
            selected_features = [f for f in X.columns if f not in to_remove]
            
            # Calculate scores (correlation with target)
            feature_scores = {}
            for feature in X.columns:
                feature_scores[feature] = abs(X[feature].corr(y))
            
            # Rank features
            feature_rankings = self._rank_features_by_scores(feature_scores)
            
            # Evaluate performance
            X_selected = X[selected_features]
            performance_score, cv_scores = self._evaluate_selection(X_selected, y)
            
            metadata = {
                "correlation_threshold": self.config.correlation_threshold,
                "removed_features": list(to_remove),
                "original_features": len(X.columns),
                "selected_features": len(selected_features),
                "reduction_ratio": len(selected_features) / len(X.columns)
            }
            
            return SelectionResult(
                method=SelectionMethod.CORRELATION_FILTER,
                strategy=SelectionStrategy.FILTER,
                selected_features=selected_features,
                feature_scores=feature_scores,
                feature_rankings=feature_rankings,
                performance_score=performance_score,
                selection_time=start_time,
                metadata=metadata,
                cross_val_scores=cv_scores
            )
            
        except Exception as e:
            logger.error(f"Correlation filter selection failed: {str(e)}")
            raise
    
    def _mutual_information_selection(self, X: pd.DataFrame, y: pd.Series, 
                                    start_time: datetime) -> SelectionResult:
        """Mutual information feature selection"""
        try:
            # Handle negative values for mutual information
            X_positive = X.copy()
            for col in X_positive.columns:
                if (X_positive[col] < 0).any():
                    X_positive[col] = X_positive[col] - X_positive[col].min()
            
            # Calculate mutual information scores
            mi_scores = mutual_info_classif(X_positive, y, random_state=self.config.random_state)
            
            # Create feature scores dictionary
            feature_scores = dict(zip(X.columns, mi_scores))
            
            # Select top k features
            k = min(self.config.mutual_info_k, len(X.columns))
            selector = SelectKBest(mutual_info_classif, k=k)
            X_selected = selector.fit_transform(X_positive, y)
            
            selected_mask = selector.get_support()
            selected_features = X.columns[selected_mask].tolist()
            
            # Rank features
            feature_rankings = self._rank_features_by_scores(feature_scores)
            
            # Evaluate performance
            performance_score, cv_scores = self._evaluate_selection(X_selected, y)
            
            metadata = {
                "k": k,
                "original_features": len(X.columns),
                "selected_features": len(selected_features),
                "reduction_ratio": len(selected_features) / len(X.columns)
            }
            
            return SelectionResult(
                method=SelectionMethod.MUTUAL_INFORMATION,
                strategy=SelectionStrategy.FILTER,
                selected_features=selected_features,
                feature_scores=feature_scores,
                feature_rankings=feature_rankings,
                performance_score=performance_score,
                selection_time=start_time,
                metadata=metadata,
                cross_val_scores=cv_scores
            )
            
        except Exception as e:
            logger.error(f"Mutual information selection failed: {str(e)}")
            raise
    
    def _chi_square_selection(self, X: pd.DataFrame, y: pd.Series, 
                             start_time: datetime) -> SelectionResult:
        """Chi-square feature selection"""
        try:
            # Ensure non-negative values
            X_positive = np.abs(X)
            
            # Select top k features
            k = min(self.config.chi2_k, len(X.columns))
            selector = SelectKBest(chi2, k=k)
            X_selected = selector.fit_transform(X_positive, y)
            
            selected_mask = selector.get_support()
            selected_features = X.columns[selected_mask].tolist()
            
            # Get chi-square scores
            chi2_scores = selector.scores_
            feature_scores = dict(zip(X.columns, chi2_scores))
            
            # Rank features
            feature_rankings = self._rank_features_by_scores(feature_scores)
            
            # Evaluate performance
            performance_score, cv_scores = self._evaluate_selection(X_selected, y)
            
            metadata = {
                "k": k,
                "original_features": len(X.columns),
                "selected_features": len(selected_features),
                "reduction_ratio": len(selected_features) / len(X.columns)
            }
            
            return SelectionResult(
                method=SelectionMethod.CHI_SQUARE,
                strategy=SelectionStrategy.FILTER,
                selected_features=selected_features,
                feature_scores=feature_scores,
                feature_rankings=feature_rankings,
                performance_score=performance_score,
                selection_time=start_time,
                metadata=metadata,
                cross_val_scores=cv_scores
            )
            
        except Exception as e:
            logger.error(f"Chi-square selection failed: {str(e)}")
            raise
    
    def _anova_f_selection(self, X: pd.DataFrame, y: pd.Series, 
                          start_time: datetime) -> SelectionResult:
        """ANOVA F-test feature selection"""
        try:
            # Select top k features
            k = min(self.config.anova_f_k, len(X.columns))
            selector = SelectKBest(f_classif, k=k)
            X_selected = selector.fit_transform(X, y)
            
            selected_mask = selector.get_support()
            selected_features = X.columns[selected_mask].tolist()
            
            # Get F-scores
            f_scores = selector.scores_
            feature_scores = dict(zip(X.columns, f_scores))
            
            # Rank features
            feature_rankings = self._rank_features_by_scores(feature_scores)
            
            # Evaluate performance
            performance_score, cv_scores = self._evaluate_selection(X_selected, y)
            
            metadata = {
                "k": k,
                "original_features": len(X.columns),
                "selected_features": len(selected_features),
                "reduction_ratio": len(selected_features) / len(X.columns)
            }
            
            return SelectionResult(
                method=SelectionMethod.ANOVA_F,
                strategy=SelectionStrategy.FILTER,
                selected_features=selected_features,
                feature_scores=feature_scores,
                feature_rankings=feature_rankings,
                performance_score=performance_score,
                selection_time=start_time,
                metadata=metadata,
                cross_val_scores=cv_scores
            )
            
        except Exception as e:
            logger.error(f"ANOVA F selection failed: {str(e)}")
            raise
    
    def _recursive_feature_elimination_selection(self, X: pd.DataFrame, y: pd.Series, 
                                               start_time: datetime) -> SelectionResult:
        """Recursive Feature Elimination selection"""
        try:
            # Create estimator
            if self.config.task_type == "classification":
                estimator = RandomForestClassifier(
                    n_estimators=50,
                    random_state=self.config.random_state,
                    max_depth=5
                )
            else:
                estimator = RandomForestRegressor(
                    n_estimators=50,
                    random_state=self.config.random_state,
                    max_depth=5
                )
            
            # Determine number of features to select
            n_features = max(self.config.min_features, len(X.columns) // 2)
            
            # Apply RFE
            selector = RFE(estimator, n_features_to_select=n_features, step=self.config.rfe_step)
            X_selected = selector.fit_transform(X, y)
            
            selected_mask = selector.get_support()
            selected_features = X.columns[selected_mask].tolist()
            
            # Get feature rankings
            feature_rankings = dict(zip(X.columns, selector.ranking_))
            
            # Calculate feature scores (inverse of ranking)
            max_rank = max(selector.ranking_)
            feature_scores = {f: max_rank - r + 1 for f, r in feature_rankings.items()}
            
            # Evaluate performance
            performance_score, cv_scores = self._evaluate_selection(X_selected, y)
            
            metadata = {
                "n_features": n_features,
                "step": self.config.rfe_step,
                "original_features": len(X.columns),
                "selected_features": len(selected_features),
                "reduction_ratio": len(selected_features) / len(X.columns)
            }
            
            return SelectionResult(
                method=SelectionMethod.RECURSIVE_FEATURE_ELIMINATION,
                strategy=SelectionStrategy.WRAPPER,
                selected_features=selected_features,
                feature_scores=feature_scores,
                feature_rankings=feature_rankings,
                performance_score=performance_score,
                selection_time=start_time,
                metadata=metadata,
                cross_val_scores=cv_scores
            )
            
        except Exception as e:
            logger.error(f"RFE selection failed: {str(e)}")
            raise
    
    def _lasso_selection(self, X: pd.DataFrame, y: pd.Series, 
                         start_time: datetime) -> SelectionResult:
        """Lasso-based feature selection"""
        try:
            # Standardize features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Fit Lasso
            lasso = Lasso(alpha=self.config.lasso_alpha, random_state=self.config.random_state)
            lasso.fit(X_scaled, y)
            
            # Get non-zero coefficients
            coef_abs = np.abs(lasso.coef_)
            selected_mask = coef_abs > 1e-6
            selected_features = X.columns[selected_mask].tolist()
            
            # Feature scores are absolute coefficients
            feature_scores = dict(zip(X.columns, coef_abs))
            
            # Rank features
            feature_rankings = self._rank_features_by_scores(feature_scores)
            
            # Evaluate performance
            X_selected = X[selected_features]
            performance_score, cv_scores = self._evaluate_selection(X_selected, y)
            
            metadata = {
                "alpha": self.config.lasso_alpha,
                "non_zero_features": np.sum(selected_mask),
                "original_features": len(X.columns),
                "selected_features": len(selected_features),
                "reduction_ratio": len(selected_features) / len(X.columns)
            }
            
            return SelectionResult(
                method=SelectionMethod.LASSO_SELECTION,
                strategy=SelectionStrategy.EMBEDDED,
                selected_features=selected_features,
                feature_scores=feature_scores,
                feature_rankings=feature_rankings,
                performance_score=performance_score,
                selection_time=start_time,
                metadata=metadata,
                cross_val_scores=cv_scores
            )
            
        except Exception as e:
            logger.error(f"Lasso selection failed: {str(e)}")
            raise
    
    def _random_forest_importance_selection(self, X: pd.DataFrame, y: pd.Series, 
                                         start_time: datetime) -> SelectionResult:
        """Random Forest importance feature selection"""
        try:
            # Create and train Random Forest
            if self.config.task_type == "classification":
                rf = RandomForestClassifier(
                    n_estimators=self.config.rf_n_estimators,
                    max_depth=self.config.rf_max_depth,
                    random_state=self.config.random_state
                )
            else:
                rf = RandomForestRegressor(
                    n_estimators=self.config.rf_n_estimators,
                    max_depth=self.config.rf_max_depth,
                    random_state=self.config.random_state
                )
            
            rf.fit(X, y)
            
            # Get feature importances
            importances = rf.feature_importances_
            feature_scores = dict(zip(X.columns, importances))
            
            # Select top features based on importance
            n_features = max(self.config.min_features, len(X.columns) // 2)
            top_features = sorted(feature_scores.items(), key=lambda x: x[1], reverse=True)[:n_features]
            selected_features = [f[0] for f in top_features]
            
            # Rank features
            feature_rankings = self._rank_features_by_scores(feature_scores)
            
            # Evaluate performance
            X_selected = X[selected_features]
            performance_score, cv_scores = self._evaluate_selection(X_selected, y)
            
            metadata = {
                "n_estimators": self.config.rf_n_estimators,
                "max_depth": self.config.rf_max_depth,
                "n_features": n_features,
                "original_features": len(X.columns),
                "selected_features": len(selected_features),
                "reduction_ratio": len(selected_features) / len(X.columns)
            }
            
            return SelectionResult(
                method=SelectionMethod.RANDOM_FOREST_IMPORTANCE,
                strategy=SelectionStrategy.EMBEDDED,
                selected_features=selected_features,
                feature_scores=feature_scores,
                feature_rankings=feature_rankings,
                performance_score=performance_score,
                selection_time=start_time,
                metadata=metadata,
                cross_val_scores=cv_scores
            )
            
        except Exception as e:
            logger.error(f"Random Forest importance selection failed: {str(e)}")
            raise
    
    def _boruta_selection(self, X: pd.DataFrame, y: pd.Series, 
                         start_time: datetime) -> SelectionResult:
        """Boruta feature selection (simplified implementation)"""
        try:
            # Simplified Boruta implementation using Random Forest
            if self.config.task_type == "classification":
                rf = RandomForestClassifier(
                    n_estimators=50,
                    max_depth=5,
                    random_state=self.config.random_state
                )
            else:
                rf = RandomForestRegressor(
                    n_estimators=50,
                    max_depth=5,
                    random_state=self.config.random_state
                )
            
            # Get original importances
            rf.fit(X, y)
            original_importances = rf.feature_importances_
            
            # Create shadow features
            X_shadow = X.copy()
            for col in X_shadow.columns:
                X_shadow[col] = np.random.permutation(X_shadow[col].values)
            
            # Combine original and shadow features
            X_combined = pd.concat([X, X_shadow], axis=1)
            shadow_prefix = "shadow_"
            X_combined.columns = list(X.columns) + [shadow_prefix + col for col in X.columns]
            
            # Train on combined features
            rf.fit(X_combined, y)
            combined_importances = rf.feature_importances_
            
            # Separate importances
            shadow_importances = combined_importances[len(X.columns):]
            max_shadow_importance = np.max(shadow_importances)
            
            # Select features with importance > max shadow importance
            selected_mask = original_importances > max_shadow_importance
            selected_features = X.columns[selected_mask].tolist()
            
            # Feature scores
            feature_scores = dict(zip(X.columns, original_importances))
            
            # Rank features
            feature_rankings = self._rank_features_by_scores(feature_scores)
            
            # Evaluate performance
            X_selected = X[selected_features]
            performance_score, cv_scores = self._evaluate_selection(X_selected, y)
            
            metadata = {
                "max_shadow_importance": max_shadow_importance,
                "original_features": len(X.columns),
                "selected_features": len(selected_features),
                "reduction_ratio": len(selected_features) / len(X.columns)
            }
            
            return SelectionResult(
                method=SelectionMethod.BORUTA,
                strategy=SelectionStrategy.WRAPPER,
                selected_features=selected_features,
                feature_scores=feature_scores,
                feature_rankings=feature_rankings,
                performance_score=performance_score,
                selection_time=start_time,
                metadata=metadata,
                cross_val_scores=cv_scores
            )
            
        except Exception as e:
            logger.error(f"Boruta selection failed: {str(e)}")
            raise
    
    def _genetic_algorithm_selection(self, X: pd.DataFrame, y: pd.Series, 
                                    start_time: datetime) -> SelectionResult:
        """Genetic Algorithm feature selection"""
        try:
            from sklearn.ensemble import RandomForestClassifier
            
            # Genetic algorithm parameters
            population_size = self.config.genetic_population_size
            generations = self.config.genetic_generations
            mutation_rate = self.config.genetic_mutation_rate
            
            # Initialize population
            n_features = len(X.columns)
            population = []
            for _ in range(population_size):
                # Random subset of features
                n_select = np.random.randint(self.config.min_features, n_features + 1)
                individual = np.zeros(n_features, dtype=bool)
                selected_indices = np.random.choice(n_features, n_select, replace=False)
                individual[selected_indices] = True
                population.append(individual)
            
            best_individual = None
            best_score = -np.inf
            
            for generation in range(generations):
                # Evaluate fitness
                fitness_scores = []
                for individual in population:
                    selected_features = X.columns[individual].tolist()
                    if len(selected_features) == 0:
                        fitness_scores.append(-np.inf)
                        continue
                    
                    X_selected = X[selected_features]
                    score, _ = self._evaluate_selection(X_selected, y)
                    fitness_scores.append(score)
                
                # Update best
                max_idx = np.argmax(fitness_scores)
                if fitness_scores[max_idx] > best_score:
                    best_score = fitness_scores[max_idx]
                    best_individual = population[max_idx].copy()
                
                # Selection (tournament)
                new_population = []
                for _ in range(population_size):
                    # Tournament selection
                    tournament_size = 3
                    tournament_indices = np.random.choice(population_size, tournament_size, replace=False)
                    tournament_fitness = [fitness_scores[i] for i in tournament_indices]
                    winner_idx = tournament_indices[np.argmax(tournament_fitness)]
                    new_population.append(population[winner_idx].copy())
                
                # Crossover
                for i in range(0, population_size, 2):
                    if i + 1 < population_size:
                        # Uniform crossover
                        crossover_mask = np.random.random(n_features) < 0.5
                        temp = new_population[i].copy()
                        new_population[i][crossover_mask] = new_population[i + 1][crossover_mask]
                        new_population[i + 1][crossover_mask] = temp[crossover_mask]
                
                # Mutation
                for individual in new_population:
                    mutation_mask = np.random.random(n_features) < mutation_rate
                    individual[mutation_mask] = ~individual[mutation_mask]
                
                population = new_population
            
            # Get final selected features
            selected_features = X.columns[best_individual].tolist()
            
            # Calculate feature scores (frequency of selection in final population)
            feature_selection_counts = np.sum(population, axis=0)
            feature_scores = dict(zip(X.columns, feature_selection_counts))
            
            # Rank features
            feature_rankings = self._rank_features_by_scores(feature_scores)
            
            # Evaluate performance
            X_selected = X[selected_features]
            performance_score, cv_scores = self._evaluate_selection(X_selected, y)
            
            metadata = {
                "generations": generations,
                "population_size": population_size,
                "mutation_rate": mutation_rate,
                "original_features": len(X.columns),
                "selected_features": len(selected_features),
                "reduction_ratio": len(selected_features) / len(X.columns)
            }
            
            return SelectionResult(
                method=SelectionMethod.GENETIC_ALGORITHM,
                strategy=SelectionStrategy.WRAPPER,
                selected_features=selected_features,
                feature_scores=feature_scores,
                feature_rankings=feature_rankings,
                performance_score=performance_score,
                selection_time=start_time,
                metadata=metadata,
                cross_val_scores=cv_scores
            )
            
        except Exception as e:
            logger.error(f"Genetic algorithm selection failed: {str(e)}")
            raise
    
    def _sequential_forward_selection(self, X: pd.DataFrame, y: pd.Series, 
                                    start_time: datetime) -> SelectionResult:
        """Sequential Forward Selection"""
        try:
            n_features = len(X.columns)
            selected_features = []
            remaining_features = list(X.columns)
            
            best_score = -np.inf
            
            while len(selected_features) < min(self.config.sequential_features, n_features):
                best_feature = None
                best_current_score = -np.inf
                
                for feature in remaining_features:
                    current_features = selected_features + [feature]
                    X_current = X[current_features]
                    score, _ = self._evaluate_selection(X_current, y)
                    
                    if score > best_current_score:
                        best_current_score = score
                        best_feature = feature
                
                if best_feature is not None and best_current_score > best_score:
                    selected_features.append(best_feature)
                    remaining_features.remove(best_feature)
                    best_score = best_current_score
                else:
                    break
            
            # Calculate feature scores (individual contribution)
            feature_scores = {}
            for feature in X.columns:
                if feature in selected_features:
                    # Score when this feature is added
                    temp_features = [f for f in selected_features if f != feature]
                    if temp_features:
                        X_temp = X[temp_features]
                        score_without, _ = self._evaluate_selection(X_temp, y)
                        X_with = X[temp_features + [feature]]
                        score_with, _ = self._evaluate_selection(X_with, y)
                        feature_scores[feature] = score_with - score_without
                    else:
                        X_single = X[[feature]]
                        feature_scores[feature], _ = self._evaluate_selection(X_single, y)
                else:
                    feature_scores[feature] = 0
            
            # Rank features
            feature_rankings = self._rank_features_by_scores(feature_scores)
            
            # Evaluate performance
            X_selected = X[selected_features]
            performance_score, cv_scores = self._evaluate_selection(X_selected, y)
            
            metadata = {
                "max_features": self.config.sequential_features,
                "original_features": len(X.columns),
                "selected_features": len(selected_features),
                "reduction_ratio": len(selected_features) / len(X.columns)
            }
            
            return SelectionResult(
                method=SelectionMethod.SEQUENTIAL_FORWARD,
                strategy=SelectionStrategy.WRAPPER,
                selected_features=selected_features,
                feature_scores=feature_scores,
                feature_rankings=feature_rankings,
                performance_score=performance_score,
                selection_time=start_time,
                metadata=metadata,
                cross_val_scores=cv_scores
            )
            
        except Exception as e:
            logger.error(f"Sequential forward selection failed: {str(e)}")
            raise
    
    def _sequential_backward_selection(self, X: pd.DataFrame, y: pd.Series, 
                                     start_time: datetime) -> SelectionResult:
        """Sequential Backward Selection"""
        try:
            selected_features = list(X.columns)
            best_score, _ = self._evaluate_selection(X[selected_features], y)
            
            while len(selected_features) > self.config.min_features:
                worst_feature = None
                best_current_score = -np.inf
                
                for feature in selected_features:
                    current_features = [f for f in selected_features if f != feature]
                    X_current = X[current_features]
                    score, _ = self._evaluate_selection(X_current, y)
                    
                    if score > best_current_score:
                        best_current_score = score
                        worst_feature = feature
                
                if worst_feature is not None and best_current_score >= best_score:
                    selected_features.remove(worst_feature)
                    best_score = best_current_score
                else:
                    break
            
            # Calculate feature scores (importance for being kept)
            feature_scores = {}
            for feature in X.columns:
                if feature in selected_features:
                    # Score when this feature is removed
                    temp_features = [f for f in selected_features if f != feature]
                    if temp_features:
                        X_temp = X[temp_features]
                        score_without, _ = self._evaluate_selection(X_temp, y)
                        X_with = X[selected_features]
                        score_with, _ = self._evaluate_selection(X_with, y)
                        feature_scores[feature] = score_with - score_without
                    else:
                        feature_scores[feature] = 0
                else:
                    feature_scores[feature] = 0
            
            # Rank features
            feature_rankings = self._rank_features_by_scores(feature_scores)
            
            # Evaluate performance
            X_selected = X[selected_features]
            performance_score, cv_scores = self._evaluate_selection(X_selected, y)
            
            metadata = {
                "min_features": self.config.min_features,
                "original_features": len(X.columns),
                "selected_features": len(selected_features),
                "reduction_ratio": len(selected_features) / len(X.columns)
            }
            
            return SelectionResult(
                method=SelectionMethod.SEQUENTIAL_BACKWARD,
                strategy=SelectionStrategy.WRAPPER,
                selected_features=selected_features,
                feature_scores=feature_scores,
                feature_rankings=feature_rankings,
                performance_score=performance_score,
                selection_time=start_time,
                metadata=metadata,
                cross_val_scores=cv_scores
            )
            
        except Exception as e:
            logger.error(f"Sequential backward selection failed: {str(e)}")
            raise
    
    def _bidirectional_selection(self, X: pd.DataFrame, y: pd.Series, 
                                start_time: datetime) -> SelectionResult:
        """Bidirectional Selection (SFS + SBS)"""
        try:
            # Start with forward selection
            sfs_result = self._sequential_forward_selection(X, y, start_time)
            selected_features = sfs_result.selected_features.copy()
            
            # Apply backward elimination on forward selection result
            while len(selected_features) > self.config.min_features:
                worst_feature = None
                best_current_score = -np.inf
                
                for feature in selected_features:
                    current_features = [f for f in selected_features if f != feature]
                    X_current = X[current_features]
                    score, _ = self._evaluate_selection(X_current, y)
                    
                    if score > best_current_score:
                        best_current_score = score
                        worst_feature = feature
                
                if worst_feature is not None:
                    selected_features.remove(worst_feature)
                else:
                    break
            
            # Calculate feature scores
            feature_scores = {}
            for feature in X.columns:
                if feature in selected_features:
                    temp_features = [f for f in selected_features if f != feature]
                    if temp_features:
                        X_temp = X[temp_features]
                        score_without, _ = self._evaluate_selection(X_temp, y)
                        X_with = X[selected_features]
                        score_with, _ = self._evaluate_selection(X_with, y)
                        feature_scores[feature] = score_with - score_without
                    else:
                        X_single = X[[feature]]
                        feature_scores[feature], _ = self._evaluate_selection(X_single, y)
                else:
                    feature_scores[feature] = 0
            
            # Rank features
            feature_rankings = self._rank_features_by_scores(feature_scores)
            
            # Evaluate performance
            X_selected = X[selected_features]
            performance_score, cv_scores = self._evaluate_selection(X_selected, y)
            
            metadata = {
                "max_features": self.config.bidirectional_features,
                "min_features": self.config.min_features,
                "original_features": len(X.columns),
                "selected_features": len(selected_features),
                "reduction_ratio": len(selected_features) / len(X.columns)
            }
            
            return SelectionResult(
                method=SelectionMethod.BIDIRECTIONAL,
                strategy=SelectionStrategy.WRAPPER,
                selected_features=selected_features,
                feature_scores=feature_scores,
                feature_rankings=feature_rankings,
                performance_score=performance_score,
                selection_time=start_time,
                metadata=metadata,
                cross_val_scores=cv_scores
            )
            
        except Exception as e:
            logger.error(f"Bidirectional selection failed: {str(e)}")
            raise
    
    def _cluster_based_selection(self, X: pd.DataFrame, y: pd.Series, 
                                start_time: datetime) -> SelectionResult:
        """Cluster-based feature selection"""
        try:
            # Calculate correlation matrix
            corr_matrix = X.corr().abs()
            
            # Convert to distance matrix
            distance_matrix = 1 - corr_matrix
            
            # Hierarchical clustering
            linkage_matrix = linkage(squareform(distance_matrix.values), method='average')
            
            # Determine number of clusters
            n_clusters = max(self.config.min_features, len(X.columns) // 3)
            clusters = fcluster(linkage_matrix, n_clusters, criterion='maxclust')
            
            # Select representative feature from each cluster
            selected_features = []
            feature_scores = {}
            
            for cluster_id in range(1, n_clusters + 1):
                cluster_features = X.columns[clusters == cluster_id].tolist()
                
                if not cluster_features:
                    continue
                
                # Select feature with highest correlation to target
                best_feature = None
                best_correlation = -np.inf
                
                for feature in cluster_features:
                    correlation = abs(X[feature].corr(y))
                    if correlation > best_correlation:
                        best_correlation = correlation
                        best_feature = feature
                
                if best_feature:
                    selected_features.append(best_feature)
                    feature_scores[best_feature] = best_correlation
                    
                    # Give some score to other cluster members
                    for feature in cluster_features:
                        if feature != best_feature:
                            feature_scores[feature] = abs(X[feature].corr(y)) * 0.5
            
            # Rank features
            feature_rankings = self._rank_features_by_scores(feature_scores)
            
            # Evaluate performance
            X_selected = X[selected_features]
            performance_score, cv_scores = self._evaluate_selection(X_selected, y)
            
            metadata = {
                "n_clusters": n_clusters,
                "linkage_method": "average",
                "original_features": len(X.columns),
                "selected_features": len(selected_features),
                "reduction_ratio": len(selected_features) / len(X.columns)
            }
            
            return SelectionResult(
                method=SelectionMethod.CLUSTER_BASED,
                strategy=SelectionStrategy.FILTER,
                selected_features=selected_features,
                feature_scores=feature_scores,
                feature_rankings=feature_rankings,
                performance_score=performance_score,
                selection_time=start_time,
                metadata=metadata,
                cross_val_scores=cv_scores
            )
            
        except Exception as e:
            logger.error(f"Cluster-based selection failed: {str(e)}")
            raise
    
    def _evaluate_selection(self, X_selected: Union[np.ndarray, pd.DataFrame], 
                          y: pd.Series) -> Tuple[float, List[float]]:
        """Evaluate feature selection performance"""
        try:
            # Create estimator
            if self.config.task_type == "classification":
                estimator = RandomForestClassifier(
                    n_estimators=50,
                    random_state=self.config.random_state,
                    max_depth=5
                )
            else:
                estimator = RandomForestRegressor(
                    n_estimators=50,
                    random_state=self.config.random_state,
                    max_depth=5
                )
            
            # Cross-validation
            cv = StratifiedKFold(n_splits=self.config.cv_folds, shuffle=True, 
                                random_state=self.config.random_state) if self.config.task_type == "classification" else self.config.cv_folds
            
            if self.config.evaluation_metric == "accuracy":
                scores = cross_val_score(estimator, X_selected, y, cv=cv, scoring='accuracy')
            elif self.config.evaluation_metric == "f1":
                scores = cross_val_score(estimator, X_selected, y, cv=cv, scoring='f1_macro')
            elif self.config.evaluation_metric == "roc_auc":
                scores = cross_val_score(estimator, X_selected, y, cv=cv, scoring='roc_auc')
            elif self.config.evaluation_metric == "mse":
                scores = -cross_val_score(estimator, X_selected, y, cv=cv, scoring='neg_mean_squared_error')
            elif self.config.evaluation_metric == "r2":
                scores = cross_val_score(estimator, X_selected, y, cv=cv, scoring='r2')
            else:
                scores = cross_val_score(estimator, X_selected, y, cv=cv, scoring='accuracy')
            
            # Calculate final score
            if self.config.scoring_strategy == "mean":
                final_score = np.mean(scores)
            elif self.config.scoring_strategy == "median":
                final_score = np.median(scores)
            elif self.config.scoring_strategy == "max":
                final_score = np.max(scores)
            else:
                final_score = np.mean(scores)
            
            return final_score, scores.tolist()
            
        except Exception as e:
            logger.error(f"Evaluation failed: {str(e)}")
            return 0.0, []
    
    def _rank_features_by_scores(self, feature_scores: Dict[str, float]) -> Dict[str, int]:
        """Rank features by their scores"""
        sorted_features = sorted(feature_scores.items(), key=lambda x: x[1], reverse=True)
        rankings = {}
        for rank, (feature, score) in enumerate(sorted_features, 1):
            rankings[feature] = rank
        return rankings
    
    def _generate_cache_key(self, X: pd.DataFrame, y: pd.Series, 
                           methods: List[SelectionMethod]) -> str:
        """Generate cache key for feature selection"""
        try:
            # Create hash of data and methods
            data_hash = hashlib.md5(f"{X.shape}_{y.shape}_{X.columns.tolist()}_{methods}".encode()).hexdigest()
            return data_hash
        except:
            return str(hash((X.shape, y.shape, tuple(X.columns), tuple(methods))))
    
    def _update_best_selection(self, results: Dict[SelectionMethod, SelectionResult]):
        """Update best selection based on performance"""
        if not results:
            return
        
        best_result = max(results.values(), key=lambda x: x.performance_score)
        self.best_selection = best_result
    
    def get_best_features(self) -> Optional[SelectionResult]:
        """Get the best feature selection result"""
        return self.best_selection
    
    def compare_methods(self, results: Dict[SelectionMethod, SelectionResult]) -> pd.DataFrame:
        """Compare different feature selection methods"""
        comparison_data = []
        
        for method, result in results.items():
            comparison_data.append({
                "Method": method.value,
                "Strategy": result.strategy.value,
                "Selected_Features": len(result.selected_features),
                "Performance_Score": result.performance_score,
                "Reduction_Ratio": result.metadata.get("reduction_ratio", 0),
                "CV_Mean": np.mean(result.cross_val_scores) if result.cross_val_scores else 0,
                "CV_Std": np.std(result.cross_val_scores) if result.cross_val_scores else 0
            })
        
        return pd.DataFrame(comparison_data)
    
    def export_results(self, results: Dict[SelectionMethod, SelectionResult], 
                      output_path: str, format: str = "json"):
        """Export feature selection results"""
        try:
            if format.lower() == "json":
                export_data = {}
                for method, result in results.items():
                    export_data[method.value] = {
                        "strategy": result.strategy.value,
                        "selected_features": result.selected_features,
                        "feature_scores": result.feature_scores,
                        "feature_rankings": result.feature_rankings,
                        "performance_score": result.performance_score,
                        "selection_time": result.selection_time.isoformat(),
                        "metadata": result.metadata,
                        "cross_val_scores": result.cross_val_scores
                    }
                
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            
            elif format.lower() == "csv":
                # Create comparison DataFrame
                comparison_df = self.compare_methods(results)
                comparison_df.to_csv(output_path, index=False)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Feature selection results exported to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export results: {str(e)}")
            raise

# Utility functions
def create_default_selector(task_type: str = "classification") -> FeatureSelector:
    """Create feature selector with default configuration"""
    config = SelectionConfig(task_type=task_type)
    return FeatureSelector(config)

def create_custom_selector(**kwargs) -> FeatureSelector:
    """Create feature selector with custom configuration"""
    config = SelectionConfig(**kwargs)
    return FeatureSelector(config)

if __name__ == "__main__":
    # Example usage
    selector = create_default_selector()
    
    # Generate sample data
    from sklearn.datasets import make_classification
    X, y = make_classification(n_samples=100, n_features=20, n_informative=10, 
                              n_redundant=5, random_state=42)
    
    feature_names = [f"feature_{i}" for i in range(X.shape[1])]
    
    try:
        results = selector.select_features(X, y, feature_names)
        print(f"Applied {len(results)} feature selection methods")
        
        # Get best selection
        best_result = selector.get_best_features()
        if best_result:
            print(f"Best method: {best_result.method.value}")
            print(f"Selected {len(best_result.selected_features)} features")
            print(f"Performance score: {best_result.performance_score:.4f}")
        
        # Compare methods
        comparison = selector.compare_methods(results)
        print(comparison)
        
        # Export results
        selector.export_results(results, "feature_selection_results.json")
        
    except Exception as e:
        print(f"Error: {str(e)}")
