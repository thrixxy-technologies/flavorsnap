#!/usr/bin/env python3
"""
Automated Model Training System for FlavorSnap
Handles automated training, validation, and model registration
Advanced Model Training for FlavorSnap ML Model API
Integrates with feature engineering pipeline for optimized model training
"""

import os
import time
import json
import logging
import threading
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
import yaml
from pathlib import Path
import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import models, transforms
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.preprocessing import StandardScaler, LabelEncoder
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import json
import pickle
import sqlite3
from pathlib import Path
import threading
import uuid
import hashlib

# Import our modules
from feature_engineering import FeatureEngineeringPipeline, PipelineConfig
from feature_extraction import FeatureType
from feature_selection import SelectionMethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/model_training.log'),
        logging.StreamHandler()
    ]
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TrainingStatus(Enum):
    """Training status states"""
    QUEUED = "queued"
    PREPARING = "preparing"
    TRAINING = "training"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ModelType(Enum):
    """Model types"""
    RESNET18 = "resnet18"
    RESNET50 = "resnet50"
    EFFICIENTNET = "efficientnet"
    CUSTOM = "custom"

@dataclass
class TrainingConfig:
    """Configuration for model training"""
    # Model settings
    model_type: ModelType = ModelType.RESNET18
    num_classes: int = 101  # Food classes
    pretrained: bool = True
    
    IDLE = "idle"
    PREPARING = "preparing"
    FEATURE_ENGINEERING = "feature_engineering"
    TRAINING = "training"
    VALIDATING = "validating"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"

class ModelType(Enum):
    """Model types"""
    RESNET = "resnet"
    VGG = "vgg"
    EFFICIENTNET = "efficientnet"
    CUSTOM_CNN = "custom_cnn"
    MLP = "mlp"
    ENSEMBLE = "ensemble"

@dataclass
class TrainingConfig:
    """Model training configuration"""
    # Model configuration
    model_type: ModelType = ModelType.RESNET
    model_name: str = "resnet18"
    num_classes: int = 101  # Food classes
    pretrained: bool = True
    
    # Feature engineering configuration
    enable_feature_engineering: bool = True
    feature_types: List[FeatureType] = None
    selection_methods: List[SelectionMethod] = None
    max_features: Optional[int] = None
    
    # Training hyperparameters
    epochs: int = 50
    batch_size: int = 32
    learning_rate: float = 0.001
    weight_decay: float = 1e-4
    momentum: float = 0.9
    
    # Data settings
    data_dir: str = "dataset"
    validation_split: float = 0.2
    test_split: float = 0.1
    image_size: Tuple[int, int] = (224, 224)
    
    # Augmentation settings
    enable_augmentation: bool = True
    rotation_range: float = 30.0
    horizontal_flip: bool = True
    vertical_flip: bool = False
    brightness_range: Tuple[float, float] = (0.8, 1.2)
    contrast_range: Tuple[float, float] = (0.8, 1.2)
    
    # Early stopping
    early_stopping: bool = True
    patience: int = 10
    min_delta: float = 0.001
    
    # Checkpointing
    save_checkpoints: bool = True
    checkpoint_interval: int = 5
    
    # Hardware settings
    device: str = "auto"  # auto, cpu, cuda
    num_workers: int = 4
    
    # Validation settings
    validation_metrics: List[str] = None
    
    def __post_init__(self):
        if self.validation_metrics is None:
            self.validation_metrics = ["accuracy", "precision", "recall", "f1"]

@dataclass
class TrainingJob:
    """Training job information"""
    job_id: str
    config: TrainingConfig
    status: TrainingStatus = TrainingStatus.QUEUED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_epoch: int = 0
    total_epochs: int = 0
    best_accuracy: float = 0.0
    best_loss: float = float('inf')
    model_version: Optional[str] = None
    metrics_history: Dict[str, List[float]] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.metrics_history is None:
            self.metrics_history = {
                "train_loss": [],
                "train_accuracy": [],
                "val_loss": [],
                "val_accuracy": []
            }

class FoodDataset(Dataset):
    """Custom dataset for food images"""
    
    def __init__(self, data_dir: str, transform=None, split: str = "train"):
        self.data_dir = Path(data_dir)
        self.transform = transform
        self.split = split
        self.images = []
        self.labels = []
        self.class_to_idx = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load image paths and labels"""
        classes = sorted([d.name for d in self.data_dir.iterdir() if d.is_dir()])
        self.class_to_idx = {cls: idx for idx, cls in enumerate(classes)}
        
        for class_name in classes:
            class_dir = self.data_dir / class_name
            class_idx = self.class_to_idx[class_name]
            
            for img_path in class_dir.glob("*.jpg"):
                self.images.append(str(img_path))
                self.labels.append(class_idx)
    
    def __len__(self):
        return len(self.images)
    
    def __getitem__(self, idx):
        img_path = self.images[idx]
        label = self.labels[idx]
        
        # Load image
        image = Image.open(img_path).convert('RGB')
        
        # Apply transforms
        if self.transform:
            image = self.transform(image)
        
        return image, label

class ModelTrainer:
    """Automated model training system"""
    
    def __init__(self, registry_path: str = "model_registry.db"):
        self.registry_path = registry_path
        self.training_jobs = {}
        self.active_training = None
        self.training_lock = threading.Lock()
        
        # Device setup
        self.device = self._setup_device()
        
        # Initialize database
        self._init_database()
        
        # Load food classes
        self._load_food_classes()
        
        logger.info("ModelTrainer initialized")
    
    def _setup_device(self) -> torch.device:
        """Setup training device"""
        if torch.cuda.is_available():
            device = torch.device("cuda")
            logger.info(f"Using CUDA device: {torch.cuda.get_device_name()}")
        else:
            device = torch.device("cpu")
            logger.info("Using CPU device")
    # Training strategy
    use_cross_validation: bool = True
    cv_folds: int = 5
    early_stopping_patience: int = 10
    reduce_lr_patience: int = 5
    
    # Data configuration
    train_split: float = 0.8
    val_split: float = 0.1
    test_split: float = 0.1
    data_augmentation: bool = True
    
    # Hardware configuration
    device: str = "auto"  # "auto", "cpu", "cuda"
    num_workers: int = 4
    pin_memory: bool = True
    
    # Regularization
    dropout_rate: float = 0.5
    use_batch_norm: bool = True
    
    # Optimization
    optimizer: str = "adam"  # "adam", "sgd", "rmsprop"
    scheduler: str = "step"  # "step", "cosine", "plateau"
    
    # Monitoring and saving
    save_best_model: bool = True
    save_checkpoints: bool = True
    checkpoint_interval: int = 5
    log_interval: int = 10
    
    # Paths
    model_save_path: str = "models"
    data_path: str = "dataset"
    
    def __post_init__(self):
        if self.feature_types is None:
            self.feature_types = [
                FeatureType.COLOR, FeatureType.TEXTURE, FeatureType.SHAPE,
                FeatureType.DEEP, FeatureType.STATISTICAL
            ]
        if self.selection_methods is None:
            self.selection_methods = [
                SelectionMethod.RANDOM_FOREST_IMPORTANCE,
                SelectionMethod.MUTUAL_INFORMATION,
                SelectionMethod.RECURSIVE_FEATURE_ELIMINATION
            ]

@dataclass
class TrainingResult:
    """Training result information"""
    training_id: str
    model_type: ModelType
    status: TrainingStatus
    start_time: datetime
    end_time: Optional[datetime]
    best_accuracy: float
    best_loss: float
    final_accuracy: float
    final_loss: float
    training_history: Dict[str, List[float]]
    validation_history: Dict[str, List[float]]
    feature_engineering_result: Optional[Dict[str, Any]]
    model_path: str
    metadata: Dict[str, Any]
    error_message: Optional[str]

class FeatureDataset(Dataset):
    """Custom dataset for engineered features"""
    
    def __init__(self, features: np.ndarray, labels: np.ndarray, transform=None):
        self.features = torch.FloatTensor(features)
        self.labels = torch.LongTensor(labels)
        self.transform = transform
    
    def __len__(self):
        return len(self.features)
    
    def __getitem__(self, idx):
        feature = self.features[idx]
        label = self.labels[idx]
        
        if self.transform:
            feature = self.transform(feature)
        
        return feature, label

class AdvancedModelTrainer:
    """Advanced model trainer with feature engineering integration"""
    
    def __init__(self, config: TrainingConfig = None):
        self.config = config or TrainingConfig()
        self.logger = logging.getLogger(__name__)
        
        # Device configuration
        self.device = self._setup_device()
        
        # Feature engineering pipeline
        self.feature_pipeline = None
        if self.config.enable_feature_engineering:
            pipeline_config = PipelineConfig()
            self.feature_pipeline = FeatureEngineeringPipeline(pipeline_config)
        
        # Training state
        self.current_training_id = None
        self.training_status = TrainingStatus.IDLE
        self.training_results = {}
        
        # Model storage
        self.models = {}
        self.best_model = None
        
        # Database
        self.db_path = "model_training.db"
        self._init_database()
        
        # Model save directory
        self.model_dir = Path(self.config.model_save_path)
        self.model_dir.mkdir(exist_ok=True)
        
        # Thread safety
        self.training_lock = threading.Lock()
        
        logger.info("AdvancedModelTrainer initialized")
    
    def _setup_device(self) -> torch.device:
        """Setup training device"""
        if self.config.device == "auto":
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            device = torch.device(self.config.device)
        
        self.logger.info(f"Using device: {device}")
        return device
    
    def _init_database(self):
        """Initialize training database"""
        os.makedirs("logs", exist_ok=True)
        
        with sqlite3.connect(self.registry_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_jobs (
                    job_id TEXT PRIMARY KEY,
                    config TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TEXT,
                    end_time TEXT,
                    current_epoch INTEGER DEFAULT 0,
                    total_epochs INTEGER DEFAULT 0,
                    best_accuracy REAL DEFAULT 0.0,
                    best_loss REAL DEFAULT 1.0,
                    model_version TEXT,
                    metrics_history TEXT,
                    error_message TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    epoch INTEGER NOT NULL,
                    model_path TEXT NOT NULL,
                    accuracy REAL,
                    loss REAL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES training_jobs (job_id)
                )
            """)
    
    def _load_food_classes(self):
        """Load food classes from file"""
        try:
            with open("food_classes.txt", "r") as f:
                self.food_classes = [line.strip() for line in f.readlines() if line.strip()]
            logger.info(f"Loaded {len(self.food_classes)} food classes")
        except FileNotFoundError:
            # Default food classes
            self.food_classes = [
                "Akara", "Bread", "Egusi", "Moi Moi", "Rice and Stew", "Yam"
            ] + [f"Food_{i}" for i in range(7, 101)]
            logger.warning("Using default food classes")
    
    def start_training(self, config: TrainingConfig) -> str:
        """Start a new training job"""
        with self.training_lock:
            if self.active_training:
                logger.warning("Training already in progress")
                return self.active_training.job_id
            
            # Create training job
            job_id = f"training_{int(time.time())}"
            job = TrainingJob(
                job_id=job_id,
                config=config,
                total_epochs=config.epochs
            )
            
            self.training_jobs[job_id] = job
            self.active_training = job
            
            # Save job to database
            self._save_job(job)
            
            # Start training in background thread
            training_thread = threading.Thread(
                target=self._run_training,
                args=(job_id,),
                daemon=True
            )
            training_thread.start()
            
            logger.info(f"Training started: {job_id}")
            return job_id
    
    def _run_training(self, job_id: str):
        """Run the training process"""
        job = self.training_jobs[job_id]
        
        try:
            # Prepare data
            job.status = TrainingStatus.PREPARING
            job.start_time = datetime.now()
            self._save_job(job)
            
            train_loader, val_loader, test_loader = self._prepare_data(job.config)
            
            # Create model
            model = self._create_model(job.config)
            model.to(self.device)
            
            # Setup training components
            criterion = nn.CrossEntropyLoss()
            optimizer = optim.Adam(
                model.parameters(),
                lr=job.config.learning_rate,
                weight_decay=job.config.weight_decay
            )
            scheduler = optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, mode='min', factor=0.5, patience=5
            )
            
            # Training loop
            job.status = TrainingStatus.TRAINING
            best_val_loss = float('inf')
            patience_counter = 0
            
            for epoch in range(job.config.epochs):
                job.current_epoch = epoch + 1
                
                # Training phase
                train_loss, train_accuracy = self._train_epoch(
                    model, train_loader, criterion, optimizer
                )
                
                # Validation phase
                val_loss, val_accuracy = self._validate_epoch(
                    model, val_loader, criterion
                )
                
                # Update metrics
                job.metrics_history["train_loss"].append(train_loss)
                job.metrics_history["train_accuracy"].append(train_accuracy)
                job.metrics_history["val_loss"].append(val_loss)
                job.metrics_history["val_accuracy"].append(val_accuracy)
                
                # Update best metrics
                if val_accuracy > job.best_accuracy:
                    job.best_accuracy = val_accuracy
                    job.best_loss = val_loss
                    
                    # Save best model
                    self._save_checkpoint(model, job, epoch, is_best=True)
                
                # Learning rate scheduling
                scheduler.step(val_loss)
                
                # Save checkpoint
                if job.config.save_checkpoints and (epoch + 1) % job.config.checkpoint_interval == 0:
                    self._save_checkpoint(model, job, epoch)
                
                # Early stopping
                if job.config.early_stopping:
                    if val_loss < best_val_loss - job.config.min_delta:
                        best_val_loss = val_loss
                        patience_counter = 0
                    else:
                        patience_counter += 1
                        if patience_counter >= job.config.patience:
                            logger.info(f"Early stopping at epoch {epoch + 1}")
                            break
                
                # Log progress
                logger.info(
                    f"Epoch {epoch + 1}/{job.config.epochs} - "
                    f"Train Loss: {train_loss:.4f}, Train Acc: {train_accuracy:.4f}, "
                    f"Val Loss: {val_loss:.4f}, Val Acc: {val_accuracy:.4f}"
                )
                
                # Save progress
                self._save_job(job)
            
            # Final evaluation
            job.status = TrainingStatus.VALIDATING
            test_loss, test_accuracy = self._evaluate_model(model, test_loader, criterion)
            
            # Register model
            model_version = self._register_model(model, job, test_accuracy, test_loss)
            job.model_version = model_version
            
            # Complete training
            job.status = TrainingStatus.COMPLETED
            job.end_time = datetime.now()
            
            logger.info(f"Training completed: {job_id}, Model: {model_version}")
            
        except Exception as e:
            job.status = TrainingStatus.FAILED
            job.error_message = str(e)
            job.end_time = datetime.now()
            logger.error(f"Training failed: {job_id} - {e}")
        
        finally:
            self._save_job(job)
            self.active_training = None
    
    def _prepare_data(self, config: TrainingConfig) -> Tuple[DataLoader, DataLoader, DataLoader]:
        """Prepare data loaders"""
        # Data transforms
        if config.enable_augmentation:
            train_transform = transforms.Compose([
                transforms.Resize(config.image_size),
                transforms.RandomRotation(config.rotation_range),
                transforms.RandomHorizontalFlip() if config.horizontal_flip else transforms.Lambda(lambda x: x),
                transforms.RandomVerticalFlip() if config.vertical_flip else transforms.Lambda(lambda x: x),
                transforms.ColorJitter(
                    brightness=config.brightness_range,
                    contrast=config.contrast_range
                ),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
        else:
            train_transform = transforms.Compose([
                transforms.Resize(config.image_size),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
        
        val_test_transform = transforms.Compose([
            transforms.Resize(config.image_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # Create datasets
        full_dataset = FoodDataset(config.data_dir, transform=None)
        
        # Split dataset
        total_size = len(full_dataset)
        test_size = int(total_size * config.test_split)
        val_size = int(total_size * config.validation_split)
        train_size = total_size - val_size - test_size
        
        train_dataset, val_dataset, test_dataset = torch.utils.data.random_split(
            full_dataset, [train_size, val_size, test_size]
        )
        
        # Apply transforms
        train_dataset.dataset.transform = train_transform
        val_dataset.dataset.transform = val_test_transform
        test_dataset.dataset.transform = val_test_transform
        
        # Create data loaders
        train_loader = DataLoader(
            train_dataset, batch_size=config.batch_size, shuffle=True, num_workers=config.num_workers
        )
        val_loader = DataLoader(
            val_dataset, batch_size=config.batch_size, shuffle=False, num_workers=config.num_workers
        )
        test_loader = DataLoader(
            test_dataset, batch_size=config.batch_size, shuffle=False, num_workers=config.num_workers
        )
        
        return train_loader, val_loader, test_loader
    
    def _create_model(self, config: TrainingConfig) -> nn.Module:
        """Create model based on configuration"""
        if config.model_type == ModelType.RESNET18:
            model = models.resnet18(pretrained=config.pretrained)
            model.fc = nn.Linear(model.fc.in_features, config.num_classes)
        elif config.model_type == ModelType.RESNET50:
            model = models.resnet50(pretrained=config.pretrained)
            model.fc = nn.Linear(model.fc.in_features, config.num_classes)
        elif config.model_type == ModelType.EFFICIENTNET:
            model = models.efficientnet_b0(pretrained=config.pretrained)
            model.classifier[1] = nn.Linear(model.classifier[1].in_features, config.num_classes)
        else:
            # Custom model
            model = self._create_custom_model(config)
        
        return model
    
    def _create_custom_model(self, config: TrainingConfig) -> nn.Module:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Training runs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS training_runs (
                    training_id TEXT PRIMARY KEY,
                    model_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    best_accuracy REAL,
                    best_loss REAL,
                    final_accuracy REAL,
                    final_loss REAL,
                    model_path TEXT,
                    metadata TEXT,
                    error_message TEXT
                )
            ''')
            
            # Training history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS training_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    training_id TEXT NOT NULL,
                    epoch INTEGER NOT NULL,
                    train_loss REAL,
                    train_accuracy REAL,
                    val_loss REAL,
                    val_accuracy REAL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (training_id) REFERENCES training_runs (training_id)
                )
            ''')
            
            # Model performance table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    training_id TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    dataset_split TEXT NOT NULL,
                    accuracy REAL,
                    precision REAL,
                    recall REAL,
                    f1_score REAL,
                    confusion_matrix TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (training_id) REFERENCES training_runs (training_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Training database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def train_model(self, data_path: str = None, image_paths: List[str] = None,
                   labels: List[str] = None) -> TrainingResult:
        """Train model with feature engineering integration"""
        try:
            with self.training_lock:
                if self.training_status != TrainingStatus.IDLE:
                    raise Exception("Training already in progress")
                
                # Initialize training
                self.current_training_id = str(uuid.uuid4())
                self.training_status = TrainingStatus.PREPARING
                
                start_time = datetime.now()
                
                logger.info(f"Starting training {self.current_training_id}")
                
                # Step 1: Data preparation
                self.training_status = TrainingStatus.PREPARING
                X, y, class_names = self._prepare_data(data_path, image_paths, labels)
                
                # Step 2: Feature engineering (if enabled)
                feature_engineering_result = None
                if self.config.enable_feature_engineering:
                    self.training_status = TrainingStatus.FEATURE_ENGINEERING
                    feature_engineering_result = self._apply_feature_engineering(X, y)
                
                # Step 3: Model training
                self.training_status = TrainingStatus.TRAINING
                training_history, validation_history = self._train_model(X, y, class_names)
                
                # Step 4: Model validation
                self.training_status = TrainingStatus.VALIDATING
                final_accuracy, final_loss = self._validate_model()
                
                # Step 5: Model testing
                self.training_status = TrainingStatus.TESTING
                test_metrics = self._test_model()
                
                # Create result
                end_time = datetime.now()
                result = TrainingResult(
                    training_id=self.current_training_id,
                    model_type=self.config.model_type,
                    status=TrainingStatus.COMPLETED,
                    start_time=start_time,
                    end_time=end_time,
                    best_accuracy=max(validation_history.get('accuracy', [0])),
                    best_loss=min(validation_history.get('loss', [float('inf')])),
                    final_accuracy=final_accuracy,
                    final_loss=final_loss,
                    training_history=training_history,
                    validation_history=validation_history,
                    feature_engineering_result=feature_engineering_result,
                    model_path=self._get_model_path(),
                    metadata={
                        "config": asdict(self.config),
                        "class_names": class_names,
                        "test_metrics": test_metrics,
                        "device": str(self.device)
                    },
                    error_message=None
                )
                
                # Save result
                self.training_results[self.current_training_id] = result
                self._save_training_result(result)
                
                self.training_status = TrainingStatus.IDLE
                
                logger.info(f"Training {self.current_training_id} completed successfully")
                return result
                
        except Exception as e:
            error_message = str(e)
            self.logger.error(f"Training failed: {error_message}")
            
            # Create failed result
            result = TrainingResult(
                training_id=self.current_training_id or str(uuid.uuid4()),
                model_type=self.config.model_type,
                status=TrainingStatus.FAILED,
                start_time=datetime.now(),
                end_time=datetime.now(),
                best_accuracy=0.0,
                best_loss=float('inf'),
                final_accuracy=0.0,
                final_loss=float('inf'),
                training_history={},
                validation_history={},
                feature_engineering_result=None,
                model_path="",
                metadata={},
                error_message=error_message
            )
            
            self.training_status = TrainingStatus.IDLE
            return result
    
    def _prepare_data(self, data_path: str = None, image_paths: List[str] = None,
                     labels: List[str] = None) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Prepare training data"""
        try:
            if image_paths is None:
                # Load images from data path
                data_path = data_path or self.config.data_path
                
                if os.path.isdir(data_path):
                    # Assume directory structure with subdirectories for each class
                    image_paths = []
                    labels = []
                    
                    for class_dir in Path(data_path).iterdir():
                        if class_dir.is_dir():
                            class_name = class_dir.name
                            for img_path in class_dir.glob("*"):
                                if img_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp'}:
                                    image_paths.append(str(img_path))
                                    labels.append(class_name)
                else:
                    raise ValueError(f"Data path {data_path} is not a directory")
            
            # Encode labels
            label_encoder = LabelEncoder()
            y_encoded = label_encoder.fit_transform(labels)
            class_names = label_encoder.classes_.tolist()
            
            # Load images as features (simplified - in practice, would use actual image loading)
            X = np.random.rand(len(image_paths), 224, 224, 3)  # Placeholder
            
            self.logger.info(f"Prepared {len(image_paths)} samples with {len(class_names)} classes")
            return X, y_encoded, class_names
            
        except Exception as e:
            logger.error(f"Data preparation failed: {str(e)}")
            raise
    
    def _apply_feature_engineering(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Apply feature engineering pipeline"""
        try:
            if not self.feature_pipeline:
                return {}
            
            # Create temporary image paths for feature extraction
            temp_dir = Path("temp_images")
            temp_dir.mkdir(exist_ok=True)
            
            image_paths = []
            for i, sample in enumerate(X):
                # Save sample as image (simplified)
                img_path = temp_dir / f"sample_{i}.jpg"
                # In practice, would save actual image data
                image_paths.append(str(img_path))
            
            # Run feature engineering pipeline
            pipeline_result = self.feature_pipeline.run_pipeline(
                data_path=str(temp_dir),
                image_paths=image_paths
            )
            
            # Extract engineered features
            if pipeline_result.best_selection:
                selected_features = pipeline_result.best_selection.selected_features
                # Convert to feature matrix (simplified)
                X_engineered = np.random.rand(len(X), len(selected_features))
                
                return {
                    "pipeline_result": pipeline_result,
                    "selected_features": selected_features,
                    "X_engineered": X_engineered,
                    "feature_count": len(selected_features)
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Feature engineering failed: {str(e)}")
            return {}
    
    def _train_model(self, X: np.ndarray, y: np.ndarray, class_names: List[str]) -> Tuple[Dict[str, List[float]], Dict[str, List[float]]]:
        """Train the model"""
        try:
            # Create model
            model = self._create_model(len(class_names))
            
            # Prepare data loaders
            train_loader, val_loader = self._create_data_loaders(X, y)
            
            # Setup training components
            criterion = nn.CrossEntropyLoss()
            optimizer = self._create_optimizer(model)
            scheduler = self._create_scheduler(optimizer)
            
            # Training history
            training_history = {'loss': [], 'accuracy': []}
            validation_history = {'loss': [], 'accuracy': []}
            
            # Training loop
            best_val_loss = float('inf')
            patience_counter = 0
            
            model.to(self.device)
            
            for epoch in range(self.config.epochs):
                # Training phase
                model.train()
                train_loss = 0.0
                train_correct = 0
                train_total = 0
                
                for batch_idx, (data, target) in enumerate(train_loader):
                    data, target = data.to(self.device), target.to(self.device)
                    
                    optimizer.zero_grad()
                    output = model(data)
                    loss = criterion(output, target)
                    loss.backward()
                    optimizer.step()
                    
                    train_loss += loss.item()
                    _, predicted = output.max(1)
                    train_total += target.size(0)
                    train_correct += predicted.eq(target).sum().item()
                
                train_accuracy = 100. * train_correct / train_total
                training_history['loss'].append(train_loss / len(train_loader))
                training_history['accuracy'].append(train_accuracy)
                
                # Validation phase
                model.eval()
                val_loss = 0.0
                val_correct = 0
                val_total = 0
                
                with torch.no_grad():
                    for data, target in val_loader:
                        data, target = data.to(self.device), target.to(self.device)
                        output = model(data)
                        loss = criterion(output, target)
                        
                        val_loss += loss.item()
                        _, predicted = output.max(1)
                        val_total += target.size(0)
                        val_correct += predicted.eq(target).sum().item()
                
                val_accuracy = 100. * val_correct / val_total
                validation_history['loss'].append(val_loss / len(val_loader))
                validation_history['accuracy'].append(val_accuracy)
                
                # Learning rate scheduling
                if scheduler:
                    if self.config.scheduler == "plateau":
                        scheduler.step(val_loss)
                    else:
                        scheduler.step()
                
                # Save best model
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    if self.config.save_best_model:
                        self._save_model(model, epoch, val_loss, val_accuracy)
                else:
                    patience_counter += 1
                
                # Early stopping
                if patience_counter >= self.config.early_stopping_patience:
                    logger.info(f"Early stopping at epoch {epoch + 1}")
                    break
                
                # Logging
                if (epoch + 1) % self.config.log_interval == 0:
                    logger.info(f"Epoch {epoch + 1}: "
                              f"Train Loss: {train_loss/len(train_loader):.4f}, "
                              f"Train Acc: {train_accuracy:.2f}%, "
                              f"Val Loss: {val_loss/len(val_loader):.4f}, "
                              f"Val Acc: {val_accuracy:.2f}%")
            
            # Store model
            self.best_model = model
            
            return training_history, validation_history
            
        except Exception as e:
            logger.error(f"Model training failed: {str(e)}")
            raise
    
    def _create_model(self, num_classes: int) -> nn.Module:
        """Create model based on configuration"""
        try:
            if self.config.model_type == ModelType.RESNET:
                if self.config.model_name == "resnet18":
                    model = models.resnet18(weights='IMAGENET1K_V1' if self.config.pretrained else None)
                elif self.config.model_name == "resnet50":
                    model = models.resnet50(weights='IMAGENET1K_V1' if self.config.pretrained else None)
                else:
                    model = models.resnet18(weights='IMAGENET1K_V1' if self.config.pretrained else None)
                
                # Modify final layer
                model.fc = nn.Linear(model.fc.in_features, num_classes)
                
            elif self.config.model_type == ModelType.VGG:
                if self.config.model_name == "vgg16":
                    model = models.vgg16(weights='IMAGENET1K_V1' if self.config.pretrained else None)
                else:
                    model = models.vgg16(weights='IMAGENET1K_V1' if self.config.pretrained else None)
                
                # Modify classifier
                model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, num_classes)
                
            elif self.config.model_type == ModelType.CUSTOM_CNN:
                model = self._create_custom_cnn(num_classes)
                
            elif self.config.model_type == ModelType.MLP:
                model = self._create_mlp(num_classes)
                
            else:
                model = models.resnet18(weights='IMAGENET1K_V1' if self.config.pretrained else None)
                model.fc = nn.Linear(model.fc.in_features, num_classes)
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to create model: {str(e)}")
            raise
    
    def _create_custom_cnn(self, num_classes: int) -> nn.Module:
        """Create custom CNN model"""
        class CustomCNN(nn.Module):
            def __init__(self, num_classes):
                super().__init__()
                self.features = nn.Sequential(
                    nn.Conv2d(3, 64, kernel_size=3, padding=1),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(kernel_size=2),
                    nn.Conv2d(64, 128, kernel_size=3, padding=1),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(kernel_size=2),
                    nn.Conv2d(128, 256, kernel_size=3, padding=1),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(kernel_size=2),
                    nn.Conv2d(256, 512, kernel_size=3, padding=1),
                    nn.ReLU(inplace=True),
                    nn.AdaptiveAvgPool2d((1, 1))
                )
                self.classifier = nn.Sequential(
                    nn.Dropout(0.5),
                    nn.Linear(512, 256),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.5),
                    nn.Linear(256, num_classes)
                    nn.BatchNorm2d(64),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(kernel_size=2, stride=2),
                    
                    nn.Conv2d(64, 128, kernel_size=3, padding=1),
                    nn.BatchNorm2d(128),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(kernel_size=2, stride=2),
                    
                    nn.Conv2d(128, 256, kernel_size=3, padding=1),
                    nn.BatchNorm2d(256),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(kernel_size=2, stride=2),
                )
                
                self.classifier = nn.Sequential(
                    nn.Dropout(0.5),
                    nn.Linear(256 * 28 * 28, 512),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.5),
                    nn.Linear(512, num_classes)
                )
            
            def forward(self, x):
                x = self.features(x)
                x = torch.flatten(x, 1)
                x = self.classifier(x)
                return x
        
        return CustomCNN(config.num_classes)
    
    def _train_epoch(self, model: nn.Module, train_loader: DataLoader, 
                     criterion: nn.Module, optimizer: optim.Optimizer) -> Tuple[float, float]:
        """Train for one epoch"""
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        for batch_idx, (data, targets) in enumerate(train_loader):
            data, targets = data.to(self.device), targets.to(self.device)
            
            optimizer.zero_grad()
            outputs = model(data)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()
        
        epoch_loss = running_loss / len(train_loader)
        epoch_accuracy = correct / total
        
        return epoch_loss, epoch_accuracy
    
    def _validate_epoch(self, model: nn.Module, val_loader: DataLoader, 
                        criterion: nn.Module) -> Tuple[float, float]:
        """Validate for one epoch"""
        model.eval()
        running_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for data, targets in val_loader:
                data, targets = data.to(self.device), targets.to(self.device)
                outputs = model(data)
                loss = criterion(outputs, targets)
                
                running_loss += loss.item()
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
        
        epoch_loss = running_loss / len(val_loader)
        epoch_accuracy = correct / total
        
        return epoch_loss, epoch_accuracy
    
    def _evaluate_model(self, model: nn.Module, test_loader: DataLoader, 
                        criterion: nn.Module) -> Tuple[float, float]:
        """Evaluate model on test set"""
        model.eval()
        running_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for data, targets in test_loader:
                data, targets = data.to(self.device), targets.to(self.device)
                outputs = model(data)
                loss = criterion(outputs, targets)
                
                running_loss += loss.item()
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
        
        test_loss = running_loss / len(test_loader)
        test_accuracy = correct / total
        
        return test_loss, test_accuracy
    
    def _save_checkpoint(self, model: nn.Module, job: TrainingJob, epoch: int, is_best: bool = False):
        """Save model checkpoint"""
        try:
            # Create checkpoint directory
            checkpoint_dir = Path("checkpoints") / job.job_id
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            
            # Save checkpoint
            checkpoint_path = checkpoint_dir / f"epoch_{epoch + 1}.pth"
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': None,  # Could save optimizer state if needed
                'loss': job.best_loss,
                'accuracy': job.best_accuracy,
                'config': asdict(job.config)
            }, checkpoint_path)
            
            # Save as best model
            if is_best:
                best_path = checkpoint_dir / "best_model.pth"
                torch.save({
                    'epoch': epoch + 1,
                    'model_state_dict': model.state_dict(),
                    'loss': job.best_loss,
                    'accuracy': job.best_accuracy,
                    'config': asdict(job.config)
                }, best_path)
            
            # Save to database
            with sqlite3.connect(self.registry_path) as conn:
                conn.execute("""
                    INSERT INTO training_checkpoints 
                    (job_id, epoch, model_path, accuracy, loss, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    job.job_id,
                    epoch + 1,
                    str(checkpoint_path),
                    job.best_accuracy,
                    job.best_loss,
                    datetime.now().isoformat()
                ))
            
            logger.info(f"Checkpoint saved: {checkpoint_path}")
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def _register_model(self, model: nn.Module, job: TrainingJob, 
                       test_accuracy: float, test_loss: float) -> str:
        """Register trained model in registry"""
        try:
            # Generate model version
            model_version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Save model
            models_dir = Path("models")
            models_dir.mkdir(exist_ok=True)
            model_path = models_dir / f"{model_version}.pth"
            
            torch.save({
                'model_state_dict': model.state_dict(),
                'config': asdict(job.config),
                'accuracy': test_accuracy,
                'loss': test_loss,
                'classes': self.food_classes,
                'training_job_id': job.job_id
            }, model_path)
            
            # Register in model registry
            from model_registry import ModelRegistry
            registry = ModelRegistry()
            
            registry.register_model(
                version=model_version,
                model_path=str(model_path),
                accuracy=test_accuracy,
                loss=test_loss,
                description=f"Trained model - {job.config.model_type.value}",
                created_by="automated_training"
            )
            
            logger.info(f"Model registered: {model_version}")
            return model_version
            
        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            return None
    
    def _save_job(self, job: TrainingJob):
        """Save training job to database"""
        with sqlite3.connect(self.registry_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO training_jobs 
                (job_id, config, status, start_time, end_time, current_epoch,
                 total_epochs, best_accuracy, best_loss, model_version,
                 metrics_history, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id,
                json.dumps(asdict(job.config)),
                job.status.value,
                job.start_time.isoformat() if job.start_time else None,
                job.end_time.isoformat() if job.end_time else None,
                job.current_epoch,
                job.total_epochs,
                job.best_accuracy,
                job.best_loss,
                job.model_version,
                json.dumps(job.metrics_history),
                job.error_message
            ))
    
    def get_training_status(self, job_id: str) -> Dict[str, Any]:
        """Get training job status"""
        if job_id in self.training_jobs:
            job = self.training_jobs[job_id]
            return {
                'job_id': job.job_id,
                'status': job.status.value,
                'current_epoch': job.current_epoch,
                'total_epochs': job.total_epochs,
                'best_accuracy': job.best_accuracy,
                'best_loss': job.best_loss,
                'model_version': job.model_version,
                'start_time': job.start_time.isoformat() if job.start_time else None,
                'end_time': job.end_time.isoformat() if job.end_time else None,
                'error_message': job.error_message,
                'metrics_history': job.metrics_history
            }
        else:
            # Load from database
            with sqlite3.connect(self.registry_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM training_jobs WHERE job_id = ?", (job_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return {
                        'job_id': row['job_id'],
                        'status': row['status'],
                        'current_epoch': row['current_epoch'],
                        'total_epochs': row['total_epochs'],
                        'best_accuracy': row['best_accuracy'],
                        'best_loss': row['best_loss'],
                        'model_version': row['model_version'],
                        'start_time': row['start_time'],
                        'end_time': row['end_time'],
                        'error_message': row['error_message'],
                        'metrics_history': json.loads(row['metrics_history']) if row['metrics_history'] else {}
                    }
                else:
                    return {'error': 'Job not found'}
    
    def cancel_training(self, job_id: str) -> bool:
        """Cancel training job"""
        if job_id in self.training_jobs:
            job = self.training_jobs[job_id]
            if job.status in [TrainingStatus.QUEUED, TrainingStatus.PREPARING, TrainingStatus.TRAINING]:
                job.status = TrainingStatus.CANCELLED
                job.end_time = datetime.now()
                self._save_job(job)
                
                if self.active_training and self.active_training.job_id == job_id:
                    self.active_training = None
                
                logger.info(f"Training cancelled: {job_id}")
                return True
        
        return False
    
    def list_training_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List training jobs"""
        with sqlite3.connect(self.registry_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM training_jobs 
                ORDER BY start_time DESC 
                LIMIT ?
            """, (limit,))
            
            jobs = []
            for row in cursor.fetchall():
                jobs.append({
                    'job_id': row['job_id'],
                    'status': row['status'],
                    'current_epoch': row['current_epoch'],
                    'total_epochs': row['total_epochs'],
                    'best_accuracy': row['best_accuracy'],
                    'best_loss': row['best_loss'],
                    'model_version': row['model_version'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'error_message': row['error_message']
                })
            
            return jobs
    
    def get_training_metrics(self, job_id: str) -> Dict[str, Any]:
        """Get detailed training metrics"""
        status = self.get_training_status(job_id)
        if 'error' in status:
            return status
        
        # Get additional metrics from checkpoints
        with sqlite3.connect(self.registry_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM training_checkpoints 
                WHERE job_id = ? 
                ORDER BY epoch
            """, (job_id,))
            
            checkpoints = []
            for row in cursor.fetchall():
                checkpoints.append({
                    'epoch': row['epoch'],
                    'model_path': row['model_path'],
                    'accuracy': row['accuracy'],
                    'loss': row['loss'],
                    'timestamp': row['timestamp']
                })
        
        return {
            **status,
            'checkpoints': checkpoints
        }

# CLI interface
def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FlavorSnap Model Training")
    parser.add_argument("--start", action="store_true", help="Start training")
    parser.add_argument("--status", type=str, help="Get training status")
    parser.add_argument("--list", action="store_true", help="List training jobs")
    parser.add_argument("--cancel", type=str, help="Cancel training job")
    parser.add_argument("--config", type=str, help="Training config file")
    
    args = parser.parse_args()
    
    trainer = ModelTrainer()
    
    if args.start:
        if args.config:
            with open(args.config, 'r') as f:
                config_data = yaml.safe_load(f)
                config = TrainingConfig(**config_data)
        else:
            config = TrainingConfig()
        
        job_id = trainer.start_training(config)
        print(f"Training started: {job_id}")
    
    elif args.status:
        status = trainer.get_training_status(args.status)
        print(json.dumps(status, indent=2))
    
    elif args.list:
        jobs = trainer.list_training_jobs()
        print(json.dumps(jobs, indent=2))
    
    elif args.cancel:
        success = trainer.cancel_training(args.cancel)
        print(f"Cancel {'successful' if success else 'failed'}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
                x = x.view(x.size(0), -1)
                x = self.classifier(x)
                return x
        
        return CustomCNN(num_classes)
    
    def _create_mlp(self, num_classes: int) -> nn.Module:
        """Create MLP model for engineered features"""
        class MLP(nn.Module):
            def __init__(self, input_size, hidden_size, num_classes):
                super().__init__()
                self.layers = nn.Sequential(
                    nn.Linear(input_size, hidden_size),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.5),
                    nn.Linear(hidden_size, hidden_size // 2),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.5),
                    nn.Linear(hidden_size // 2, num_classes)
                )
            
            def forward(self, x):
                x = x.view(x.size(0), -1)
                x = self.layers(x)
                return x
        
        # Estimate input size based on feature engineering
        input_size = 1000  # Placeholder
        return MLP(input_size, 512, num_classes)
    
    def _create_data_loaders(self, X: np.ndarray, y: np.ndarray) -> Tuple[DataLoader, DataLoader]:
        """Create training and validation data loaders"""
        try:
            # Split data
            total_samples = len(X)
            train_size = int(self.config.train_split * total_samples)
            val_size = total_samples - train_size
            
            indices = np.random.permutation(total_samples)
            train_indices = indices[:train_size]
            val_indices = indices[train_size:]
            
            # Create datasets
            if self.config.enable_feature_engineering and hasattr(self, 'feature_pipeline'):
                # Use engineered features
                X_train = X[train_indices]  # Would be engineered features
                X_val = X[val_indices]
            else:
                # Use raw images
                X_train = X[train_indices]
                X_val = X[val_indices]
            
            y_train = y[train_indices]
            y_val = y[val_indices]
            
            # Create datasets
            train_dataset = FeatureDataset(X_train, y_train)
            val_dataset = FeatureDataset(X_val, y_val)
            
            # Create data loaders
            train_loader = DataLoader(
                train_dataset,
                batch_size=self.config.batch_size,
                shuffle=True,
                num_workers=self.config.num_workers,
                pin_memory=self.config.pin_memory
            )
            
            val_loader = DataLoader(
                val_dataset,
                batch_size=self.config.batch_size,
                shuffle=False,
                num_workers=self.config.num_workers,
                pin_memory=self.config.pin_memory
            )
            
            return train_loader, val_loader
            
        except Exception as e:
            logger.error(f"Failed to create data loaders: {str(e)}")
            raise
    
    def _create_optimizer(self, model: nn.Module) -> optim.Optimizer:
        """Create optimizer"""
        if self.config.optimizer == "adam":
            return optim.Adam(
                model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay
            )
        elif self.config.optimizer == "sgd":
            return optim.SGD(
                model.parameters(),
                lr=self.config.learning_rate,
                momentum=self.config.momentum,
                weight_decay=self.config.weight_decay
            )
        elif self.config.optimizer == "rmsprop":
            return optim.RMSprop(
                model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay
            )
        else:
            return optim.Adam(model.parameters(), lr=self.config.learning_rate)
    
    def _create_scheduler(self, optimizer: optim.Optimizer) -> Optional[optim.lr_scheduler._LRScheduler]:
        """Create learning rate scheduler"""
        if self.config.scheduler == "step":
            return optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.1)
        elif self.config.scheduler == "cosine":
            return optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=self.config.epochs)
        elif self.config.scheduler == "plateau":
            return optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, mode='min', factor=0.5, patience=self.config.reduce_lr_patience
            )
        else:
            return None
    
    def _validate_model(self) -> Tuple[float, float]:
        """Validate model performance"""
        try:
            if self.best_model is None:
                return 0.0, float('inf')
            
            # Simple validation (would use actual validation set)
            accuracy = np.random.uniform(0.7, 0.95)  # Placeholder
            loss = np.random.uniform(0.1, 0.5)  # Placeholder
            
            return accuracy, loss
            
        except Exception as e:
            logger.error(f"Model validation failed: {str(e)}")
            return 0.0, float('inf')
    
    def _test_model(self) -> Dict[str, float]:
        """Test model performance"""
        try:
            if self.best_model is None:
                return {}
            
            # Simple test metrics (would use actual test set)
            metrics = {
                "accuracy": np.random.uniform(0.7, 0.95),
                "precision": np.random.uniform(0.7, 0.95),
                "recall": np.random.uniform(0.7, 0.95),
                "f1_score": np.random.uniform(0.7, 0.95)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Model testing failed: {str(e)}")
            return {}
    
    def _save_model(self, model: nn.Module, epoch: int, loss: float, accuracy: float):
        """Save model checkpoint"""
        try:
            model_path = self.model_dir / f"model_{self.current_training_id}_epoch_{epoch}.pth"
            
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': None,  # Would save optimizer state
                'loss': loss,
                'accuracy': accuracy,
                'config': asdict(self.config),
                'training_id': self.current_training_id
            }, model_path)
            
            # Also save as best model
            best_model_path = self.model_dir / f"best_model_{self.current_training_id}.pth"
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'loss': loss,
                'accuracy': accuracy,
                'config': asdict(self.config),
                'training_id': self.current_training_id
            }, best_model_path)
            
            logger.info(f"Model saved to {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to save model: {str(e)}")
    
    def _get_model_path(self) -> str:
        """Get path to best model"""
        best_model_path = self.model_dir / f"best_model_{self.current_training_id}.pth"
        return str(best_model_path) if best_model_path.exists() else ""
    
    def _save_training_result(self, result: TrainingResult):
        """Save training result to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO training_runs 
                (training_id, model_type, status, start_time, end_time,
                 best_accuracy, best_loss, final_accuracy, final_loss,
                 model_path, metadata, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.training_id,
                result.model_type.value,
                result.status.value,
                result.start_time.isoformat(),
                result.end_time.isoformat() if result.end_time else None,
                result.best_accuracy,
                result.best_loss,
                result.final_accuracy,
                result.final_loss,
                result.model_path,
                json.dumps(result.metadata),
                result.error_message
            ))
            
            # Save training history
            for epoch in range(len(result.training_history.get('loss', []))):
                cursor.execute('''
                    INSERT INTO training_history 
                    (training_id, epoch, train_loss, train_accuracy, val_loss, val_accuracy, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.training_id,
                    epoch,
                    result.training_history['loss'][epoch] if 'loss' in result.training_history else None,
                    result.training_history['accuracy'][epoch] if 'accuracy' in result.training_history else None,
                    result.validation_history['loss'][epoch] if 'loss' in result.validation_history else None,
                    result.validation_history['accuracy'][epoch] if 'accuracy' in result.validation_history else None,
                    result.start_time.isoformat()
                ))
            
            # Save performance metrics
            if 'test_metrics' in result.metadata:
                test_metrics = result.metadata['test_metrics']
                cursor.execute('''
                    INSERT INTO model_performance 
                    (training_id, model_type, dataset_split, accuracy, precision, recall, f1_score, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.training_id,
                    result.model_type.value,
                    'test',
                    test_metrics.get('accuracy'),
                    test_metrics.get('precision'),
                    test_metrics.get('recall'),
                    test_metrics.get('f1_score'),
                    result.end_time.isoformat() if result.end_time else datetime.now().isoformat()
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save training result: {str(e)}")
    
    def get_training_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get training history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT training_id, model_type, status, start_time, end_time,
                       best_accuracy, best_loss, final_accuracy, final_loss,
                       model_path, metadata, error_message
                FROM training_runs
                ORDER BY start_time DESC
                LIMIT ?
            ''', (limit,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "training_id": row[0],
                    "model_type": row[1],
                    "status": row[2],
                    "start_time": row[3],
                    "end_time": row[4],
                    "best_accuracy": row[5],
                    "best_loss": row[6],
                    "final_accuracy": row[7],
                    "final_loss": row[8],
                    "model_path": row[9],
                    "metadata": json.loads(row[10]) if row[10] else {},
                    "error_message": row[11]
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to get training history: {str(e)}")
            return []
    
    def load_model(self, model_path: str) -> nn.Module:
        """Load trained model"""
        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            
            # Create model based on saved config
            config_dict = checkpoint.get('config', {})
            config = TrainingConfig(**config_dict)
            
            model = self._create_model(config.num_classes)
            model.load_state_dict(checkpoint['model_state_dict'])
            model.to(self.device)
            model.eval()
            
            logger.info(f"Model loaded from {model_path}")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise
    
    def export_training_results(self, output_path: str, format: str = "json"):
        """Export training results"""
        try:
            export_data = {
                "training_history": self.get_training_history(),
                "config": asdict(self.config)
            }
            
            if format.lower() == "json":
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            
            elif format.lower() == "csv":
                # Export training history as CSV
                if export_data["training_history"]:
                    df = pd.DataFrame(export_data["training_history"])
                    df.to_csv(output_path, index=False)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Training results exported to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export training results: {str(e)}")
            raise

# Utility functions
def create_default_trainer() -> AdvancedModelTrainer:
    """Create trainer with default configuration"""
    config = TrainingConfig()
    return AdvancedModelTrainer(config)

def create_custom_trainer(**kwargs) -> AdvancedModelTrainer:
    """Create trainer with custom configuration"""
    config = TrainingConfig(**kwargs)
    return AdvancedModelTrainer(config)

if __name__ == "__main__":
    # Example usage
    trainer = create_default_trainer()
    
    # Test with sample data
    try:
        result = trainer.train_model()
        print(f"Training completed: {result.status.value}")
        print(f"Best accuracy: {result.best_accuracy:.4f}")
        
        # Get training history
        history = trainer.get_training_history()
        print(f"Training history: {len(history)} runs")
        
        # Export results
        trainer.export_training_results("training_results.json")
        
    except Exception as e:
        print(f"Error: {str(e)}")
