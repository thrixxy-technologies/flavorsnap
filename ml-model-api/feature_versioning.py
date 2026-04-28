#!/usr/bin/env python3
"""
Feature Versioning System for FlavorSnap ML Model API
Comprehensive feature versioning, tracking, and management system
"""

import os
import json
import logging
import numpy as np
import pandas as pd
import sqlite3
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import pickle
import uuid
from pathlib import Path
import threading
from git import Repo, InvalidGitRepositoryError
import shutil

# Import our modules
from feature_extraction import ExtractedFeatures, FeatureType
from feature_selection import SelectionResult, SelectionMethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VersionStatus(Enum):
    """Feature version status"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    FAILED = "failed"

class VersionType(Enum):
    """Version creation types"""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    SCHEDULED = "scheduled"
    ROLLBACK = "rollback"

class StorageBackend(Enum):
    """Storage backend types"""
    LOCAL = "local"
    GIT = "git"
    S3 = "s3"
    DATABASE = "database"

@dataclass
class VersionConfig:
    """Feature versioning configuration"""
    # Version settings
    auto_versioning: bool = True
    max_versions: int = 50
    version_retention_days: int = 90
    
    # Storage settings
    storage_backend: StorageBackend = StorageBackend.LOCAL
    storage_path: str = "feature_versions"
    git_repo_path: str = "feature_versions_git"
    
    # Version naming
    version_prefix: str = "v"
    semantic_versioning: bool = True
    
    # Metadata settings
    capture_performance: bool = True
    capture_data_stats: bool = True
    capture_dependencies: bool = True
    
    # Validation settings
    validate_versions: bool = True
    compatibility_check: bool = True
    
    # Promotion settings
    auto_promote_threshold: float = 0.85
    require_testing: bool = True
    testing_threshold: float = 0.8
    
    # Backup settings
    enable_backup: bool = True
    backup_frequency: str = "daily"  # "daily", "weekly", "monthly"
    backup_retention_days: int = 30
    
    # Database
    database_path: str = "feature_versioning.db"

@dataclass
class FeatureVersion:
    """Feature version information"""
    version_id: str
    version_number: str
    status: VersionStatus
    version_type: VersionType
    created_at: datetime
    created_by: str
    parent_version_id: Optional[str]
    
    # Feature information
    feature_count: int
    feature_names: List[str]
    feature_hashes: Dict[str, str]
    feature_metadata: Dict[str, Any]
    
    # Performance information
    performance_metrics: Dict[str, float]
    validation_results: Dict[str, Any]
    
    # Storage information
    storage_path: str
    file_size: int
    checksum: str
    
    # Metadata
    description: str
    tags: List[str]
    dependencies: Dict[str, str]
    changelog: str
    
    # Testing information
    test_results: Dict[str, Any]
    is_tested: bool
    test_passed: bool

@dataclass
class VersionComparison:
    """Version comparison result"""
    version_1_id: str
    version_2_id: str
    comparison_type: str
    added_features: List[str]
    removed_features: List[str]
    modified_features: List[str]
    compatibility_score: float
    performance_diff: Dict[str, float]
    comparison_time: datetime
    metadata: Dict[str, Any]

class FeatureVersioningSystem:
    """Advanced feature versioning system"""
    
    def __init__(self, config: VersionConfig = None):
        self.config = config or VersionConfig()
        self.logger = logging.getLogger(__name__)
        
        # Version storage
        self.versions = {}
        self.active_version = None
        self.version_history = []
        
        # Storage setup
        self.storage_path = Path(self.config.storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Git repository setup
        self.git_repo = None
        if self.config.storage_backend == StorageBackend.GIT:
            self._setup_git_repository()
        
        # Database
        self.db_path = self.config.database_path
        self._init_database()
        
        # Thread safety
        self.version_lock = threading.Lock()
        
        logger.info("FeatureVersioningSystem initialized")
    
    def _setup_git_repository(self):
        """Setup Git repository for version control"""
        try:
            git_path = Path(self.config.git_repo_path)
            
            if git_path.exists():
                try:
                    self.git_repo = Repo(git_path)
                    logger.info("Existing Git repository loaded")
                except InvalidGitRepositoryError:
                    shutil.rmtree(git_path)
                    self.git_repo = Repo.init(git_path)
                    logger.info("New Git repository initialized")
            else:
                git_path.mkdir(parents=True, exist_ok=True)
                self.git_repo = Repo.init(git_path)
                logger.info("New Git repository created")
            
            # Configure Git user if not set
            with self.git_repo.config_writer() as config:
                if not config.has_section('user'):
                    config.set_value('user', 'name', 'Feature Versioning System')
                    config.set_value('user', 'email', 'versioning@flavorsnap.ai')
            
        except Exception as e:
            logger.error(f"Failed to setup Git repository: {str(e)}")
            raise
    
    def _init_database(self):
        """Initialize versioning database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Versions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS versions (
                    version_id TEXT PRIMARY KEY,
                    version_number TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    parent_version_id TEXT,
                    feature_count INTEGER NOT NULL,
                    feature_names TEXT NOT NULL,
                    feature_hashes TEXT NOT NULL,
                    feature_metadata TEXT,
                    performance_metrics TEXT,
                    validation_results TEXT,
                    storage_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    checksum TEXT NOT NULL,
                    description TEXT,
                    tags TEXT,
                    dependencies TEXT,
                    changelog TEXT,
                    test_results TEXT,
                    is_tested BOOLEAN DEFAULT FALSE,
                    test_passed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Version comparisons table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS version_comparisons (
                    comparison_id TEXT PRIMARY KEY,
                    version_1_id TEXT NOT NULL,
                    version_2_id TEXT NOT NULL,
                    comparison_type TEXT NOT NULL,
                    added_features TEXT NOT NULL,
                    removed_features TEXT NOT NULL,
                    modified_features TEXT NOT NULL,
                    compatibility_score REAL NOT NULL,
                    performance_diff TEXT NOT NULL,
                    comparison_time TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (version_1_id) REFERENCES versions (version_id),
                    FOREIGN KEY (version_2_id) REFERENCES versions (version_id)
                )
            ''')
            
            # Version lineage table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS version_lineage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_version_id TEXT NOT NULL,
                    child_version_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (parent_version_id) REFERENCES versions (version_id),
                    FOREIGN KEY (child_version_id) REFERENCES versions (version_id)
                )
            ''')
            
            # Version promotion history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS promotion_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_id TEXT NOT NULL,
                    from_status TEXT NOT NULL,
                    to_status TEXT NOT NULL,
                    promoted_by TEXT NOT NULL,
                    promotion_reason TEXT,
                    promoted_at TEXT NOT NULL,
                    FOREIGN KEY (version_id) REFERENCES versions (version_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Versioning database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def create_version(self, features: Dict[str, Any], feature_names: List[str],
                     version_type: VersionType = VersionType.MANUAL,
                     description: str = "", tags: List[str] = None,
                     created_by: str = "system", parent_version_id: str = None) -> FeatureVersion:
        """Create a new feature version"""
        try:
            with self.version_lock:
                # Generate version information
                version_id = str(uuid.uuid4())
                version_number = self._generate_version_number()
                created_at = datetime.now()
                
                # Calculate feature hashes
                feature_hashes = self._calculate_feature_hashes(features)
                
                # Calculate checksum
                checksum = self._calculate_version_checksum(features, feature_names)
                
                # Create version object
                version = FeatureVersion(
                    version_id=version_id,
                    version_number=version_number,
                    status=VersionStatus.DRAFT,
                    version_type=version_type,
                    created_at=created_at,
                    created_by=created_by,
                    parent_version_id=parent_version_id,
                    feature_count=len(feature_names),
                    feature_names=feature_names,
                    feature_hashes=feature_hashes,
                    feature_metadata=self._extract_feature_metadata(features),
                    performance_metrics={},
                    validation_results={},
                    storage_path="",
                    file_size=0,
                    checksum=checksum,
                    description=description,
                    tags=tags or [],
                    dependencies={},
                    changelog="",
                    test_results={},
                    is_tested=False,
                    test_passed=False
                )
                
                # Save version
                self._save_version(version, features)
                
                # Store in memory
                self.versions[version_id] = version
                self.version_history.append(version_id)
                
                # Add to lineage
                if parent_version_id:
                    self._add_to_lineage(parent_version_id, version_id, "child")
                
                logger.info(f"Created version {version_number} with {len(feature_names)} features")
                return version
                
        except Exception as e:
            logger.error(f"Failed to create version: {str(e)}")
            raise
    
    def _generate_version_number(self) -> str:
        """Generate version number"""
        try:
            if self.config.semantic_versioning:
                # Get latest version number
                latest_version = self._get_latest_version_number()
                
                if latest_version:
                    # Parse semantic version
                    parts = latest_version.split('.')
                    if len(parts) >= 3:
                        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                        patch += 1
                        return f"{major}.{minor}.{patch}"
                    else:
                        # Fallback to simple increment
                        return str(int(latest_version) + 1)
                
                return "1.0.0"
            else:
                # Simple incrementing version
                latest_version = self._get_latest_version_number()
                if latest_version and latest_version.isdigit():
                    return str(int(latest_version) + 1)
                else:
                    return "1"
                
        except Exception as e:
            logger.error(f"Failed to generate version number: {str(e)}")
            return "1"
    
    def _get_latest_version_number(self) -> Optional[str]:
        """Get the latest version number"""
        try:
            if not self.version_history:
                return None
            
            latest_version_id = self.version_history[-1]
            latest_version = self.versions.get(latest_version_id)
            
            return latest_version.version_number if latest_version else None
            
        except Exception as e:
            logger.error(f"Failed to get latest version number: {str(e)}")
            return None
    
    def _calculate_feature_hashes(self, features: Dict[str, Any]) -> Dict[str, str]:
        """Calculate hashes for features"""
        try:
            feature_hashes = {}
            
            for feature_name, feature_data in features.items():
                # Create hash from feature data
                feature_str = json.dumps(feature_data, sort_keys=True, default=str)
                feature_hash = hashlib.sha256(feature_str.encode()).hexdigest()
                feature_hashes[feature_name] = feature_hash
            
            return feature_hashes
            
        except Exception as e:
            logger.error(f"Failed to calculate feature hashes: {str(e)}")
            return {}
    
    def _calculate_version_checksum(self, features: Dict[str, Any], feature_names: List[str]) -> str:
        """Calculate overall version checksum"""
        try:
            # Create combined string of all feature data
            combined_data = {
                "features": features,
                "feature_names": sorted(feature_names),
                "timestamp": datetime.now().isoformat()
            }
            
            version_str = json.dumps(combined_data, sort_keys=True, default=str)
            checksum = hashlib.sha256(version_str.encode()).hexdigest()
            
            return checksum
            
        except Exception as e:
            logger.error(f"Failed to calculate version checksum: {str(e)}")
            return ""
    
    def _extract_feature_metadata(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from features"""
        try:
            metadata = {
                "total_features": len(features),
                "feature_types": {},
                "data_types": {},
                "creation_time": datetime.now().isoformat()
            }
            
            # Analyze feature types and data types
            for feature_name, feature_data in features.items():
                # Feature type analysis
                if isinstance(feature_data, dict):
                    feature_type = feature_data.get("type", "unknown")
                    metadata["feature_types"][feature_type] = metadata["feature_types"].get(feature_type, 0) + 1
                
                # Data type analysis
                data_type = type(feature_data).__name__
                metadata["data_types"][data_type] = metadata["data_types"].get(data_type, 0) + 1
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract feature metadata: {str(e)}")
            return {}
    
    def _save_version(self, version: FeatureVersion, features: Dict[str, Any]):
        """Save version to storage"""
        try:
            # Create version directory
            version_dir = self.storage_path / version.version_number
            version_dir.mkdir(exist_ok=True)
            
            # Save features
            features_file = version_dir / "features.pkl"
            with open(features_file, 'wb') as f:
                pickle.dump(features, f)
            
            # Save version metadata
            metadata_file = version_dir / "metadata.json"
            version_data = asdict(version)
            version_data["created_at"] = version.created_at.isoformat()
            with open(metadata_file, 'w') as f:
                json.dump(version_data, f, indent=2, default=str)
            
            # Update version storage info
            version.storage_path = str(version_dir)
            version.file_size = sum(f.stat().st_size for f in version_dir.rglob('*') if f.is_file())
            
            # Save to database
            self._save_version_to_db(version)
            
            # Git commit if enabled
            if self.config.storage_backend == StorageBackend.GIT and self.git_repo:
                self._git_commit_version(version, version_dir)
            
            logger.info(f"Version {version.version_number} saved to storage")
            
        except Exception as e:
            logger.error(f"Failed to save version: {str(e)}")
            raise
    
    def _save_version_to_db(self, version: FeatureVersion):
        """Save version to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO versions 
                (version_id, version_number, status, version_type, created_at, created_by,
                 parent_version_id, feature_count, feature_names, feature_hashes,
                 feature_metadata, performance_metrics, validation_results,
                 storage_path, file_size, checksum, description, tags, dependencies,
                 changelog, test_results, is_tested, test_passed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                version.version_id,
                version.version_number,
                version.status.value,
                version.version_type.value,
                version.created_at.isoformat(),
                version.created_by,
                version.parent_version_id,
                version.feature_count,
                json.dumps(version.feature_names),
                json.dumps(version.feature_hashes),
                json.dumps(version.feature_metadata),
                json.dumps(version.performance_metrics),
                json.dumps(version.validation_results),
                version.storage_path,
                version.file_size,
                version.checksum,
                version.description,
                json.dumps(version.tags),
                json.dumps(version.dependencies),
                version.changelog,
                json.dumps(version.test_results),
                version.is_tested,
                version.test_passed
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save version to database: {str(e)}")
    
    def _git_commit_version(self, version: FeatureVersion, version_dir: Path):
        """Commit version to Git repository"""
        try:
            if not self.git_repo:
                return
            
            # Copy version files to Git repository
            git_version_dir = Path(self.git_repo.working_dir) / version.version_number
            if git_version_dir.exists():
                shutil.rmtree(git_version_dir)
            shutil.copytree(version_dir, git_version_dir)
            
            # Stage and commit
            self.git_repo.index.add([str(git_version_dir)])
            
            commit_message = f"Add version {version.version_number}\n\n"
            commit_message += f"Features: {version.feature_count}\n"
            commit_message += f"Created by: {version.created_by}\n"
            if version.description:
                commit_message += f"Description: {version.description}\n"
            
            self.git_repo.index.commit(commit_message)
            
            # Create tag for this version
            tag_name = f"{self.config.version_prefix}{version.version_number}"
            self.git_repo.create_tag(tag_name, message=f"Version {version.version_number}")
            
            logger.info(f"Version {version.version_number} committed to Git")
            
        except Exception as e:
            logger.error(f"Failed to commit version to Git: {str(e)}")
    
    def _add_to_lineage(self, parent_id: str, child_id: str, relationship_type: str):
        """Add version relationship to lineage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO version_lineage 
                (parent_version_id, child_version_id, relationship_type, created_at)
                VALUES (?, ?, ?, ?)
            ''', (parent_id, child_id, relationship_type, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to add to lineage: {str(e)}")
    
    def load_version(self, version_id: str) -> Optional[FeatureVersion]:
        """Load version from storage"""
        try:
            # Check if already in memory
            if version_id in self.versions:
                return self.versions[version_id]
            
            # Load from database
            version = self._load_version_from_db(version_id)
            
            if version:
                self.versions[version_id] = version
                return version
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load version {version_id}: {str(e)}")
            return None
    
    def _load_version_from_db(self, version_id: str) -> Optional[FeatureVersion]:
        """Load version from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM versions WHERE version_id = ?
            ''', (version_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # Parse row data
            version = FeatureVersion(
                version_id=row[0],
                version_number=row[1],
                status=VersionStatus(row[2]),
                version_type=VersionType(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                created_by=row[5],
                parent_version_id=row[6],
                feature_count=row[7],
                feature_names=json.loads(row[8]),
                feature_hashes=json.loads(row[9]),
                feature_metadata=json.loads(row[10]),
                performance_metrics=json.loads(row[11]),
                validation_results=json.loads(row[12]),
                storage_path=row[13],
                file_size=row[14],
                checksum=row[15],
                description=row[16],
                tags=json.loads(row[17]),
                dependencies=json.loads(row[18]),
                changelog=row[19],
                test_results=json.loads(row[20]),
                is_tested=row[21],
                test_passed=row[22]
            )
            
            return version
            
        except Exception as e:
            logger.error(f"Failed to load version from database: {str(e)}")
            return None
    
    def load_version_features(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Load features for a specific version"""
        try:
            version = self.load_version(version_id)
            if not version:
                return None
            
            # Load features from storage
            features_file = Path(version.storage_path) / "features.pkl"
            if features_file.exists():
                with open(features_file, 'rb') as f:
                    return pickle.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load version features: {str(e)}")
            return None
    
    def promote_version(self, version_id: str, target_status: VersionStatus, 
                      promoted_by: str = "system", reason: str = "") -> bool:
        """Promote version to new status"""
        try:
            with self.version_lock:
                version = self.load_version(version_id)
                if not version:
                    raise ValueError(f"Version {version_id} not found")
                
                # Validate promotion
                if not self._validate_promotion(version, target_status):
                    return False
                
                old_status = version.status
                version.status = target_status
                
                # Update in database
                self._update_version_status(version_id, target_status)
                
                # Record promotion history
                self._record_promotion(version_id, old_status, target_status, promoted_by, reason)
                
                # Update active version if promoting to ACTIVE
                if target_status == VersionStatus.ACTIVE:
                    self.active_version = version_id
                
                logger.info(f"Version {version.version_number} promoted from {old_status.value} to {target_status.value}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to promote version: {str(e)}")
            return False
    
    def _validate_promotion(self, version: FeatureVersion, target_status: VersionStatus) -> bool:
        """Validate version promotion"""
        try:
            if not self.config.validate_versions:
                return True
            
            # Check if version is tested when required
            if self.config.require_testing and target_status == VersionStatus.ACTIVE:
                if not version.is_tested or not version.test_passed:
                    logger.warning(f"Version {version.version_number} not properly tested")
                    return False
            
            # Check performance threshold for active promotion
            if target_status == VersionStatus.ACTIVE:
                if version.performance_metrics:
                    accuracy = version.performance_metrics.get("accuracy", 0.0)
                    if accuracy < self.config.auto_promote_threshold:
                        logger.warning(f"Version {version.version_number} performance below threshold")
                        return False
            
            # Check compatibility if parent exists
            if version.parent_version_id and self.config.compatibility_check:
                compatibility = self._check_compatibility(version.parent_version_id, version.version_id)
                if compatibility < 0.8:  # 80% compatibility threshold
                    logger.warning(f"Version {version.version_number} compatibility check failed")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate promotion: {str(e)}")
            return False
    
    def _check_compatibility(self, version_1_id: str, version_2_id: str) -> float:
        """Check compatibility between versions"""
        try:
            version_1 = self.load_version(version_1_id)
            version_2 = self.load_version(version_2_id)
            
            if not version_1 or not version_2:
                return 0.0
            
            # Check feature overlap
            features_1 = set(version_1.feature_names)
            features_2 = set(version_2.feature_names)
            
            if not features_1:
                return 1.0  # First version is always compatible
            
            overlap = len(features_1.intersection(features_2))
            total = len(features_1.union(features_2))
            
            compatibility = overlap / total if total > 0 else 0.0
            
            return compatibility
            
        except Exception as e:
            logger.error(f"Failed to check compatibility: {str(e)}")
            return 0.0
    
    def _update_version_status(self, version_id: str, status: VersionStatus):
        """Update version status in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE versions SET status = ? WHERE version_id = ?
            ''', (status.value, version_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update version status: {str(e)}")
    
    def _record_promotion(self, version_id: str, from_status: VersionStatus, 
                         to_status: VersionStatus, promoted_by: str, reason: str):
        """Record promotion in history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO promotion_history 
                (version_id, from_status, to_status, promoted_by, promotion_reason, promoted_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (version_id, from_status.value, to_status.value, promoted_by, reason, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to record promotion: {str(e)}")
    
    def compare_versions(self, version_1_id: str, version_2_id: str) -> Optional[VersionComparison]:
        """Compare two versions"""
        try:
            version_1 = self.load_version(version_1_id)
            version_2 = self.load_version(version_2_id)
            
            if not version_1 or not version_2:
                return None
            
            # Calculate differences
            features_1 = set(version_1.feature_names)
            features_2 = set(version_2.feature_names)
            
            added_features = list(features_2 - features_1)
            removed_features = list(features_1 - features_2)
            modified_features = []  # Would need deeper analysis for actual modifications
            
            # Calculate compatibility score
            compatibility_score = self._check_compatibility(version_1_id, version_2_id)
            
            # Calculate performance differences
            performance_diff = {}
            for metric in set(version_1.performance_metrics.keys()).union(version_2.performance_metrics.keys()):
                val_1 = version_1.performance_metrics.get(metric, 0.0)
                val_2 = version_2.performance_metrics.get(metric, 0.0)
                performance_diff[metric] = val_2 - val_1
            
            # Create comparison object
            comparison = VersionComparison(
                version_1_id=version_1_id,
                version_2_id=version_2_id,
                comparison_type="feature_comparison",
                added_features=added_features,
                removed_features=removed_features,
                modified_features=modified_features,
                compatibility_score=compatibility_score,
                performance_diff=performance_diff,
                comparison_time=datetime.now(),
                metadata={
                    "version_1_number": version_1.version_number,
                    "version_2_number": version_2.version_number,
                    "feature_count_diff": version_2.feature_count - version_1.feature_count
                }
            )
            
            # Save comparison
            self._save_comparison(comparison)
            
            return comparison
            
        except Exception as e:
            logger.error(f"Failed to compare versions: {str(e)}")
            return None
    
    def _save_comparison(self, comparison: VersionComparison):
        """Save version comparison to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            comparison_id = str(uuid.uuid4())
            
            cursor.execute('''
                INSERT INTO version_comparisons 
                (comparison_id, version_1_id, version_2_id, comparison_type,
                 added_features, removed_features, modified_features,
                 compatibility_score, performance_diff, comparison_time, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                comparison_id,
                comparison.version_1_id,
                comparison.version_2_id,
                comparison.comparison_type,
                json.dumps(comparison.added_features),
                json.dumps(comparison.removed_features),
                json.dumps(comparison.modified_features),
                comparison.compatibility_score,
                json.dumps(comparison.performance_diff),
                comparison.comparison_time.isoformat(),
                json.dumps(comparison.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save comparison: {str(e)}")
    
    def rollback_to_version(self, version_id: str, rolled_back_by: str = "system") -> bool:
        """Rollback to a specific version"""
        try:
            version = self.load_version(version_id)
            if not version:
                raise ValueError(f"Version {version_id} not found")
            
            # Deprecate current active version
            if self.active_version:
                self.promote_version(self.active_version, VersionStatus.DEPRECATED, rolled_back_by, "Rollback")
            
            # Promote target version to active
            success = self.promote_version(version_id, VersionStatus.ACTIVE, rolled_back_by, "Rollback target")
            
            if success:
                logger.info(f"Successfully rolled back to version {version.version_number}")
                return True
            else:
                logger.error(f"Failed to rollback to version {version.version_number}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to rollback: {str(e)}")
            return False
    
    def list_versions(self, status: Optional[VersionStatus] = None, 
                     limit: int = 50) -> List[FeatureVersion]:
        """List versions with optional status filter"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if status:
                cursor.execute('''
                    SELECT version_id FROM versions 
                    WHERE status = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (status.value, limit))
            else:
                cursor.execute('''
                    SELECT version_id FROM versions 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            versions = []
            for row in rows:
                version = self.load_version(row[0])
                if version:
                    versions.append(version)
            
            return versions
            
        except Exception as e:
            logger.error(f"Failed to list versions: {str(e)}")
            return []
    
    def get_version_lineage(self, version_id: str) -> Dict[str, List[str]]:
        """Get version lineage (parents and children)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get parents
            cursor.execute('''
                SELECT parent_version_id FROM version_lineage 
                WHERE child_version_id = ?
            ''', (version_id,))
            parents = [row[0] for row in cursor.fetchall()]
            
            # Get children
            cursor.execute('''
                SELECT child_version_id FROM version_lineage 
                WHERE parent_version_id = ?
            ''', (version_id,))
            children = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                "parents": parents,
                "children": children
            }
            
        except Exception as e:
            logger.error(f"Failed to get version lineage: {str(e)}")
            return {"parents": [], "children": []}
    
    def cleanup_old_versions(self):
        """Clean up old versions based on retention policy"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.version_retention_days)
            
            # Get versions to cleanup
            versions_to_cleanup = []
            for version_id in self.version_history:
                version = self.load_version(version_id)
                if version and version.created_at < cutoff_date and version.status != VersionStatus.ACTIVE:
                    versions_to_cleanup.append(version_id)
            
            # Remove excess versions if over limit
            all_versions = self.list_versions()
            non_active_versions = [v for v in all_versions if v.status != VersionStatus.ACTIVE]
            
            if len(non_active_versions) > self.config.max_versions:
                # Sort by creation date and remove oldest
                non_active_versions.sort(key=lambda v: v.created_at)
                excess_count = len(non_active_versions) - self.config.max_versions
                
                for i in range(excess_count):
                    versions_to_cleanup.append(non_active_versions[i].version_id)
            
            # Cleanup versions
            for version_id in versions_to_cleanup:
                self._delete_version(version_id)
            
            logger.info(f"Cleaned up {len(versions_to_cleanup)} old versions")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old versions: {str(e)}")
    
    def _delete_version(self, version_id: str):
        """Delete a version"""
        try:
            version = self.load_version(version_id)
            if not version:
                return
            
            # Remove from storage
            if version.storage_path:
                storage_path = Path(version.storage_path)
                if storage_path.exists():
                    shutil.rmtree(storage_path)
            
            # Remove from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM versions WHERE version_id = ?", (version_id,))
            cursor.execute("DELETE FROM version_lineage WHERE parent_version_id = ? OR child_version_id = ?", 
                         (version_id, version_id))
            cursor.execute("DELETE FROM promotion_history WHERE version_id = ?", (version_id,))
            
            conn.commit()
            conn.close()
            
            # Remove from memory
            self.versions.pop(version_id, None)
            self.version_history.remove(version_id)
            
            logger.info(f"Deleted version {version.version_number}")
            
        except Exception as e:
            logger.error(f"Failed to delete version: {str(e)}")
    
    def export_versioning_data(self, output_path: str, format: str = "json"):
        """Export versioning data"""
        try:
            export_data = {
                "config": asdict(self.config),
                "active_version": self.active_version,
                "versions": {},
                "version_count": len(self.version_history)
            }
            
            # Export version information
            for version_id in self.version_history:
                version = self.load_version(version_id)
                if version:
                    version_data = asdict(version)
                    version_data["created_at"] = version.created_at.isoformat()
                    version_data["status"] = version.status.value
                    version_data["version_type"] = version.version_type.value
                    export_data["versions"][version_id] = version_data
            
            if format.lower() == "json":
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            
            elif format.lower() == "csv":
                # Export versions as CSV
                versions_data = []
                for version_data in export_data["versions"].values():
                    versions_data.append({
                        "version_id": version_data["version_id"],
                        "version_number": version_data["version_number"],
                        "status": version_data["status"],
                        "version_type": version_data["version_type"],
                        "created_at": version_data["created_at"],
                        "created_by": version_data["created_by"],
                        "feature_count": version_data["feature_count"],
                        "description": version_data["description"]
                    })
                
                df = pd.DataFrame(versions_data)
                df.to_csv(output_path, index=False)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Versioning data exported to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export versioning data: {str(e)}")
            raise

# Utility functions
def create_default_versioner() -> FeatureVersioningSystem:
    """Create versioning system with default configuration"""
    config = VersionConfig()
    return FeatureVersioningSystem(config)

def create_custom_versioner(**kwargs) -> FeatureVersioningSystem:
    """Create versioning system with custom configuration"""
    config = VersionConfig(**kwargs)
    return FeatureVersioningSystem(config)

if __name__ == "__main__":
    # Example usage
    versioner = create_default_versioner()
    
    try:
        # Create sample features
        sample_features = {
            "feature_1": {"type": "numerical", "value": 1.0},
            "feature_2": {"type": "categorical", "value": "A"},
            "feature_3": {"type": "text", "value": "sample text"}
        }
        feature_names = list(sample_features.keys())
        
        # Create version
        version = versioner.create_version(
            features=sample_features,
            feature_names=feature_names,
            description="Initial version",
            created_by="test_user"
        )
        
        print(f"Created version: {version.version_number}")
        
        # List versions
        versions = versioner.list_versions()
        print(f"Total versions: {len(versions)}")
        
        # Export data
        versioner.export_versioning_data("versioning_data.json")
        
    except Exception as e:
        print(f"Error: {str(e)}")
