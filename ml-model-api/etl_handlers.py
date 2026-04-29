import pandas as pd
import sqlite3
import logging
from typing import Dict, Any, List, Optional, Callable
from data_quality import DataQualityChecker

logger = logging.getLogger(__name__)

class Extractors:
    @staticmethod
    def from_sqlite(db_path: str, query: str, chunksize: int = 1000) -> pd.DataFrame:
        """Extract data from a SQLite database in chunks."""
        try:
            conn = sqlite3.connect(db_path)
            # Yield chunks if used in a loop, or just return first chunk for simplicity in this template
            for chunk in pd.read_sql_query(query, conn, chunksize=chunksize):
                yield chunk
        except Exception as e:
            logger.error(f"Error extracting from SQLite: {e}")
            raise
        finally:
            conn.close()

    @staticmethod
    def from_csv(file_path: str, chunksize: int = 1000) -> pd.DataFrame:
        """Extract data from a CSV file in chunks."""
        try:
            for chunk in pd.read_csv(file_path, chunksize=chunksize):
                yield chunk
        except Exception as e:
            logger.error(f"Error extracting from CSV: {e}")
            raise

class Transformers:
    @staticmethod
    def clean_missing_values(df: pd.DataFrame, strategy: str = 'drop') -> pd.DataFrame:
        """Clean missing values."""
        if strategy == 'drop':
            return df.dropna()
        elif strategy == 'fill_zero':
            return df.fillna(0)
        return df

    @staticmethod
    def normalize_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """Normalize specified columns using min-max scaling."""
        df_out = df.copy()
        for col in columns:
            if col in df_out.columns:
                min_val = df_out[col].min()
                max_val = df_out[col].max()
                if max_val > min_val:
                    df_out[col] = (df_out[col] - min_val) / (max_val - min_val)
                else:
                    df_out[col] = 0.0
        return df_out
        
    @staticmethod
    def apply_custom(df: pd.DataFrame, func: Callable) -> pd.DataFrame:
        """Apply a custom transformation function."""
        return func(df)

class Loaders:
    @staticmethod
    def to_sqlite(df: pd.DataFrame, db_path: str, table_name: str, if_exists: str = 'append'):
        """Load data into a SQLite database."""
        try:
            conn = sqlite3.connect(db_path)
            df.to_sql(table_name, conn, if_exists=if_exists, index=False)
        except Exception as e:
            logger.error(f"Error loading to SQLite: {e}")
            raise
        finally:
            conn.close()

    @staticmethod
    def to_csv(df: pd.DataFrame, file_path: str, mode: str = 'a', header: bool = False):
        """Load data into a CSV file."""
        try:
            df.to_csv(file_path, mode=mode, header=header, index=False)
        except Exception as e:
            logger.error(f"Error loading to CSV: {e}")
            raise

class ETLJob:
    """Represents a single ETL process."""
    def __init__(self, name: str, extractor, transformer, loader, quality_checker: Optional[DataQualityChecker] = None):
        self.name = name
        self.extractor = extractor
        self.transformer = transformer
        self.loader = loader
        self.quality_checker = quality_checker

    def run(self) -> Dict[str, Any]:
        """Execute the ETL job."""
        logger.info(f"Starting ETL Job: {self.name}")
        records_processed = 0
        total_quality_score = 0.0
        chunks = 0
        
        try:
            for chunk in self.extractor():
                # Data Quality Check (pre-transformation)
                if self.quality_checker:
                    score = self.quality_checker.get_quality_score(chunk)
                    total_quality_score += score
                    is_valid, errors = self.quality_checker.validate_schema(chunk)
                    if not is_valid:
                        logger.warning(f"Schema validation failed in {self.name}: {errors}")
                
                # Transform
                transformed_chunk = self.transformer(chunk)
                
                # Load
                self.loader(transformed_chunk)
                
                records_processed += len(transformed_chunk)
                chunks += 1
                
            avg_quality_score = total_quality_score / chunks if chunks > 0 else 1.0
            logger.info(f"Completed ETL Job: {self.name}. Records processed: {records_processed}")
            
            return {
                "status": "success",
                "records_processed": records_processed,
                "quality_score": avg_quality_score
            }
        except Exception as e:
            logger.error(f"ETL Job {self.name} failed: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
