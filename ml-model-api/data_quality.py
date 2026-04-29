import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

class DataQualityChecker:
    """
    A class to perform data quality checks on datasets.
    Provides schema validation, missing value detection, and anomaly detection.
    """
    
    def __init__(self, schema: Dict[str, Any] = None):
        """
        Initialize with an optional expected schema.
        schema format: {'column_name': 'expected_dtype_string'}
        """
        self.schema = schema or {}
        
    def validate_schema(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate that the dataframe matches the expected schema.
        """
        errors = []
        if not self.schema:
            return True, errors
            
        for col, expected_type in self.schema.items():
            if col not in df.columns:
                errors.append(f"Missing required column: {col}")
                continue
                
            actual_type = str(df[col].dtype)
            # Basic type checking (can be expanded)
            if 'int' in expected_type and 'int' not in actual_type:
                errors.append(f"Type mismatch for {col}: expected {expected_type}, got {actual_type}")
            elif 'float' in expected_type and 'float' not in actual_type:
                errors.append(f"Type mismatch for {col}: expected {expected_type}, got {actual_type}")
            elif 'object' in expected_type and 'object' not in actual_type:
                errors.append(f"Type mismatch for {col}: expected {expected_type}, got {actual_type}")
                
        return len(errors) == 0, errors

    def check_completeness(self, df: pd.DataFrame, threshold: float = 0.05) -> Tuple[bool, Dict[str, float]]:
        """
        Check for missing values. Returns False if any column has missing values
        exceeding the threshold (0.0 to 1.0).
        """
        missing_ratios = df.isnull().mean().to_dict()
        failed_cols = {col: ratio for col, ratio in missing_ratios.items() if ratio > threshold}
        
        is_complete = len(failed_cols) == 0
        return is_complete, missing_ratios
        
    def detect_anomalies(self, df: pd.DataFrame, columns: List[str] = None, method: str = 'zscore', threshold: float = 3.0) -> Dict[str, int]:
        """
        Detect anomalies in numerical columns.
        Returns a dictionary mapping column names to the count of anomalous records.
        """
        anomalies_count = {}
        cols_to_check = columns if columns else df.select_dtypes(include=[np.number]).columns
        
        for col in cols_to_check:
            if col not in df.columns:
                continue
                
            if method == 'zscore':
                mean = df[col].mean()
                std = df[col].std()
                if pd.isna(std) or std == 0:
                    anomalies_count[col] = 0
                    continue
                    
                z_scores = np.abs((df[col] - mean) / std)
                anomalies = (z_scores > threshold).sum()
                anomalies_count[col] = int(anomalies)
            elif method == 'iqr':
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                anomalies = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
                anomalies_count[col] = int(anomalies)
                
        return anomalies_count

    def get_quality_score(self, df: pd.DataFrame) -> float:
        """
        Calculate an overall quality score between 0.0 and 1.0.
        """
        if df.empty:
            return 0.0
            
        score = 1.0
        
        # Schema penalty (if schema is provided and invalid)
        is_valid, _ = self.validate_schema(df)
        if self.schema and not is_valid:
            score -= 0.3
            
        # Completeness penalty
        _, missing_ratios = self.check_completeness(df)
        avg_missing = sum(missing_ratios.values()) / len(missing_ratios) if missing_ratios else 0
        score -= min(avg_missing * 0.5, 0.4) # Max 40% penalty for missing data
        
        # Anomaly penalty
        anomalies = self.detect_anomalies(df)
        total_rows = len(df)
        total_anomalies = sum(anomalies.values())
        anomaly_ratio = total_anomalies / (total_rows * len(anomalies) if anomalies else 1)
        score -= min(anomaly_ratio, 0.3) # Max 30% penalty for anomalies
        
        return max(0.0, score)
