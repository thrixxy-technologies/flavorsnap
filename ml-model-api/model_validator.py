"""
Automated Model Validation and Testing Pipeline for FlavorSnap
Provides comprehensive model validation before deployment
"""

import os
import json
import sqlite3
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import logging
import time
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
import io
import hashlib

from model_registry import ModelRegistry, ModelMetadata


@dataclass
class FileValidationResult:
    """Results of file validation"""
    filename: str
    is_valid: bool
    file_size: int
    detected_mime_type: Optional[str] = None
    image_dimensions: Optional[Tuple[int, int]] = None
    file_hash: Optional[str] = None
    validation_errors: List[str] = None
    security_flags: List[str] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
        if self.security_flags is None:
            self.security_flags = []


@dataclass
class ValidationConfig:
    """Configuration for model validation"""
    min_accuracy_threshold: float = 0.80
    max_inference_time_threshold: float = 2.0  # seconds
    min_confidence_threshold: float = 0.60
    test_dataset_path: str = "dataset/test"
    validation_dataset_path: str = "dataset/val"
    num_test_samples: int = 100
    enable_visual_validation: bool = True
    check_model_integrity: bool = True
    check_performance_regression: bool = True
    baseline_comparison_version: Optional[str] = None


@dataclass
class ValidationResult:
    """Results of model validation"""
    model_version: str
    validation_timestamp: str
    passed: bool
    overall_score: float
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    avg_inference_time: Optional[float] = None
    avg_confidence: Optional[float] = None
    model_integrity_passed: bool = True
    performance_regression_detected: bool = False
    error_messages: List[str] = None
    detailed_metrics: Dict[str, Any] = None
    confusion_matrix_path: Optional[str] = None
    
    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []
        if self.detailed_metrics is None:
            self.detailed_metrics = {}


class ModelValidator:
    """Automated model validation and testing"""
    
    # File validation constants
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ALLOWED_MIME_TYPES = {
        'image/jpeg', 'image/png', 'image/gif', 'image/webp'
    }
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    MIN_IMAGE_DIMENSION = 32
    MAX_IMAGE_DIMENSION = 8192
    MALICIOUS_SIGNATURES = {
        b'\x4D\x5A': 'PE executable',
        b'\x7FELF': 'ELF executable',
        b'\xCA\xFE\xBA\xBE': 'Java class',
        b'\xD0\xCF\x11\xE0': 'Microsoft Office',
        b'PK\x03\x04': 'ZIP archive'
    }
    
    def __init__(self, 
                 model_registry: ModelRegistry,
                 validation_config: ValidationConfig = None,
                 registry_path: str = "model_registry.db"):
        self.model_registry = model_registry
        self.config = validation_config or ValidationConfig()
        self.registry_path = registry_path
        self.class_names = ['Akara', 'Bread', 'Egusi', 'Moi Moi', 'Rice and Stew', 'Yam']
        
        # Setup directories
        self.validation_results_dir = Path("validation_results")
        self.validation_results_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Initialize validation tracking
        self._init_validation_tracking()
        
        # Setup transforms
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
        ])
    
    def _setup_logging(self):
        """Setup logging for validation events"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('validation.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('ModelValidator')
    
    def _init_validation_tracking(self):
        """Initialize validation tracking database"""
        with sqlite3.connect(self.registry_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS validation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version TEXT NOT NULL,
                    validation_timestamp TEXT NOT NULL,
                    passed BOOLEAN NOT NULL,
                    overall_score REAL NOT NULL,
                    accuracy REAL,
                    precision REAL,
                    recall REAL,
                    f1_score REAL,
                    avg_inference_time REAL,
                    avg_confidence REAL,
                    model_integrity_passed BOOLEAN,
                    performance_regression_detected BOOLEAN,
                    error_messages TEXT,
                    detailed_metrics TEXT,
                    confusion_matrix_path TEXT,
                    FOREIGN KEY (model_version) REFERENCES models(version)
                )
            """)
    
    def load_model(self, model_path: str) -> nn.Module:
        """Load a model for validation"""
        try:
            # Create ResNet18 model
            model = models.resnet18(weights='IMAGENET1K_V1')
            model.fc = nn.Linear(model.fc.in_features, len(self.class_names))
            
            # Load state dict
            state_dict = torch.load(model_path, map_location='cpu')
            model.load_state_dict(state_dict)
            model.eval()
            
            return model
            
        except Exception as e:
            self.logger.error(f"Failed to load model from {model_path}: {e}")
            raise
    
    def check_model_integrity(self, model_path: str) -> Tuple[bool, List[str]]:
        """Check model file integrity and structure"""
        errors = []
        
        try:
            # Check if file exists
            if not os.path.exists(model_path):
                errors.append(f"Model file not found: {model_path}")
                return False, errors
            
            # Check file size
            file_size = os.path.getsize(model_path)
            if file_size < 1000:  # Less than 1KB is suspicious
                errors.append(f"Model file too small: {file_size} bytes")
            
            # Try to load model
            model = self.load_model(model_path)
            
            # Check model architecture
            if not hasattr(model, 'fc'):
                errors.append("Model missing fully connected layer")
            
            if model.fc.out_features != len(self.class_names):
                errors.append(f"Model output features ({model.fc.out_features}) "
                            f"don't match expected ({len(self.class_names)})")
            
            # Test forward pass with dummy input
            dummy_input = torch.randn(1, 3, 224, 224)
            with torch.no_grad():
                output = model(dummy_input)
            
            if output.shape != (1, len(self.class_names)):
                errors.append(f"Model output shape {output.shape} "
                            f"doesn't match expected (1, {len(self.class_names)})")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Model integrity check failed: {str(e)}")
            return False, errors
    
    def load_test_dataset(self, dataset_path: str) -> Tuple[List[Tuple[str, str]], int]:
        """Load test dataset with images and labels"""
        if not os.path.exists(dataset_path):
            self.logger.warning(f"Test dataset not found: {dataset_path}")
            return [], 0
        
        test_data = []
        dataset_size = 0
        
        for class_name in self.class_names:
            class_dir = os.path.join(dataset_path, class_name)
            if os.path.exists(class_dir):
                for image_file in os.listdir(class_dir):
                    if image_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        image_path = os.path.join(class_dir, image_file)
                        test_data.append((image_path, class_name))
                        dataset_size += 1
        
        # Limit to configured number of samples
        if dataset_size > self.config.num_test_samples:
            test_data = test_data[:self.config.num_test_samples]
            dataset_size = len(test_data)
        
        self.logger.info(f"Loaded {dataset_size} test samples")
        return test_data, dataset_size
    
    def run_inference_test(self, model: nn.Module, test_data: List[Tuple[str, str]]) -> Dict[str, Any]:
        """Run inference on test dataset and collect metrics"""
        
        if not test_data:
            return {
                'predictions': [],
                'ground_truths': [],
                'confidences': [],
                'inference_times': [],
                'error_count': 0
            }
        
        predictions = []
        ground_truths = []
        confidences = []
        inference_times = []
        error_count = 0
        
        model.eval()
        
        with torch.no_grad():
            for image_path, true_label in test_data:
                try:
                    # Load and preprocess image
                    start_time = time.time()
                    
                    image = Image.open(image_path).convert('RGB')
                    input_tensor = self.transform(image).unsqueeze(0)
                    
                    # Run inference
                    output = model(input_tensor)
                    probabilities = torch.softmax(output, dim=1)
                    confidence, predicted_class = torch.max(probabilities, 1)
                    
                    inference_time = time.time() - start_time
                    
                    # Convert class index to label
                    predicted_label = self.class_names[predicted_class.item()]
                    
                    predictions.append(predicted_label)
                    ground_truths.append(true_label)
                    confidences.append(confidence.item())
                    inference_times.append(inference_time)
                    
                except Exception as e:
                    self.logger.error(f"Error processing {image_path}: {e}")
                    error_count += 1
        
        return {
            'predictions': predictions,
            'ground_truths': ground_truths,
            'confidences': confidences,
            'inference_times': inference_times,
            'error_count': error_count
        }
    
    def calculate_metrics(self, inference_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance metrics from inference results"""
        
        predictions = inference_results['predictions']
        ground_truths = inference_results['ground_truths']
        confidences = inference_results['confidences']
        inference_times = inference_results['inference_times']
        error_count = inference_results['error_count']
        
        if not predictions:
            return {
                'accuracy': 0.0,
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'avg_confidence': 0.0,
                'avg_inference_time': 0.0,
                'error_rate': 1.0
            }
        
        # Calculate basic metrics
        accuracy = accuracy_score(ground_truths, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            ground_truths, predictions, average='weighted', zero_division=0
        )
        avg_confidence = np.mean(confidences)
        avg_inference_time = np.mean(inference_times)
        
        # Calculate error rate
        total_samples = len(predictions) + error_count
        error_rate = error_count / total_samples if total_samples > 0 else 1.0
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'avg_confidence': avg_confidence,
            'avg_inference_time': avg_inference_time,
            'error_rate': error_rate,
            'total_predictions': len(predictions),
            'error_count': error_count
        }
    
    def generate_confusion_matrix(self, 
                                 ground_truths: List[str], 
                                 predictions: List[str],
                                 model_version: str) -> str:
        """Generate and save confusion matrix plot"""
        
        if not ground_truths or not predictions:
            return None
        
        try:
            # Calculate confusion matrix
            cm = confusion_matrix(ground_truths, predictions, labels=self.class_names)
            
            # Create plot
            plt.figure(figsize=(10, 8))
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                       xticklabels=self.class_names,
                       yticklabels=self.class_names)
            plt.title(f'Confusion Matrix - Model {model_version}')
            plt.xlabel('Predicted')
            plt.ylabel('Actual')
            plt.tight_layout()
            
            # Save plot
            confusion_matrix_path = self.validation_results_dir / f"confusion_matrix_{model_version}.png"
            plt.savefig(confusion_matrix_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            return str(confusion_matrix_path)
            
        except Exception as e:
            self.logger.error(f"Failed to generate confusion matrix: {e}")
            return None
    
    def check_performance_regression(self, 
                                   current_metrics: Dict[str, Any],
                                   baseline_version: str) -> Tuple[bool, List[str]]:
        """Check for performance regression compared to baseline"""
        
        if not baseline_version:
            return False, []
        
        # Get baseline validation results
        with sqlite3.connect(self.registry_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM validation_results 
                WHERE model_version = ?
                ORDER BY validation_timestamp DESC
                LIMIT 1
            """, (baseline_version,))
            
            baseline_row = cursor.fetchone()
        
        if not baseline_row:
            return False, ["Baseline validation results not found"]
        
        regression_detected = False
        regression_messages = []
        
        # Check accuracy regression
        current_accuracy = current_metrics.get('accuracy', 0)
        baseline_accuracy = baseline_row['accuracy'] or 0
        accuracy_drop = baseline_accuracy - current_accuracy
        
        if accuracy_drop > 0.05:  # 5% drop threshold
            regression_detected = True
            regression_messages.append(
                f"Accuracy regression detected: {accuracy_drop:.2%} drop "
                f"(baseline: {baseline_accuracy:.2%}, current: {current_accuracy:.2%})"
            )
        
        # Check inference time regression
        current_time = current_metrics.get('avg_inference_time', 0)
        baseline_time = baseline_row['avg_inference_time'] or 0
        time_increase = current_time - baseline_time
        
        if time_increase > 0.5:  # 0.5 second increase threshold
            regression_detected = True
            regression_messages.append(
                f"Inference time regression: +{time_increase:.3f}s "
                f"(baseline: {baseline_time:.3f}s, current: {current_time:.3f}s)"
            )
        
        return regression_detected, regression_messages
    
    def validate_model(self, model_version: str) -> ValidationResult:
        """Perform comprehensive model validation"""
        
        self.logger.info(f"Starting validation for model {model_version}")
        
        # Get model metadata
        model_metadata = self.model_registry.get_model(model_version)
        if not model_metadata:
            return ValidationResult(
                model_version=model_version,
                validation_timestamp=datetime.now().isoformat(),
                passed=False,
                overall_score=0.0,
                error_messages=["Model not found in registry"]
            )
        
        # Initialize result
        result = ValidationResult(
            model_version=model_version,
            validation_timestamp=datetime.now().isoformat(),
            passed=True,
            overall_score=0.0
        )
        
        # 1. Model Integrity Check
        if self.config.check_model_integrity:
            integrity_passed, integrity_errors = self.check_model_integrity(model_metadata.model_path)
            result.model_integrity_passed = integrity_passed
            result.error_messages.extend(integrity_errors)
            
            if not integrity_passed:
                result.passed = False
                self.logger.error(f"Model integrity check failed for {model_version}")
        
        # 2. Load model for testing
        try:
            model = self.load_model(model_metadata.model_path)
        except Exception as e:
            result.passed = False
            result.error_messages.append(f"Failed to load model: {str(e)}")
            return result
        
        # 3. Load test dataset
        test_data, dataset_size = self.load_test_dataset(self.config.test_dataset_path)
        
        if dataset_size == 0:
            result.passed = False
            result.error_messages.append("No test data available")
            return result
        
        # 4. Run inference test
        inference_results = self.run_inference_test(model, test_data)
        metrics = self.calculate_metrics(inference_results)
        
        # Update result with metrics
        result.accuracy = metrics['accuracy']
        result.precision = metrics['precision']
        result.recall = metrics['recall']
        result.f1_score = metrics['f1_score']
        result.avg_confidence = metrics['avg_confidence']
        result.avg_inference_time = metrics['avg_inference_time']
        result.detailed_metrics = metrics
        
        # 5. Generate confusion matrix
        if self.config.enable_visual_validation:
            result.confusion_matrix_path = self.generate_confusion_matrix(
                inference_results['ground_truths'],
                inference_results['predictions'],
                model_version
            )
        
        # 6. Check thresholds
        threshold_failures = []
        
        if result.accuracy < self.config.min_accuracy_threshold:
            threshold_failures.append(
                f"Accuracy {result.accuracy:.2%} below threshold {self.config.min_accuracy_threshold:.2%}"
            )
        
        if result.avg_inference_time > self.config.max_inference_time_threshold:
            threshold_failures.append(
                f"Inference time {result.avg_inference_time:.3f}s above threshold "
                f"{self.config.max_inference_time_threshold:.3f}s"
            )
        
        if result.avg_confidence < self.config.min_confidence_threshold:
            threshold_failures.append(
                f"Average confidence {result.avg_confidence:.3f} below threshold "
                f"{self.config.min_confidence_threshold:.3f}"
            )
        
        result.error_messages.extend(threshold_failures)
        
        # 7. Check performance regression
        if self.config.check_performance_regression and self.config.baseline_comparison_version:
            regression_detected, regression_messages = self.check_performance_regression(
                metrics, self.config.baseline_comparison_version
            )
            result.performance_regression_detected = regression_detected
            result.error_messages.extend(regression_messages)
        
        # 8. Calculate overall score
        score_components = [
            result.accuracy or 0,
            result.precision or 0,
            result.recall or 0,
            result.f1_score or 0,
            1.0 - (result.avg_inference_time / self.config.max_inference_time_threshold) if result.avg_inference_time else 0,
            result.avg_confidence or 0
        ]
        
        result.overall_score = np.mean(score_components)
        
        # 9. Determine final pass/fail
        if threshold_failures or not result.model_integrity_passed:
            result.passed = False
        
        # 10. Save validation result
        self._save_validation_result(result)
        
        self.logger.info(f"Validation completed for {model_version}: "
                        f"{'PASSED' if result.passed else 'FAILED'} "
                        f"(Score: {result.overall_score:.3f})")
        
        return result
    
    def _save_validation_result(self, result: ValidationResult):
        """Save validation result to database"""
        with sqlite3.connect(self.registry_path) as conn:
            conn.execute("""
                INSERT INTO validation_results 
                (model_version, validation_timestamp, passed, overall_score,
                 accuracy, precision, recall, f1_score, avg_inference_time,
                 avg_confidence, model_integrity_passed, performance_regression_detected,
                 error_messages, detailed_metrics, confusion_matrix_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.model_version,
                result.validation_timestamp,
                result.passed,
                result.overall_score,
                result.accuracy,
                result.precision,
                result.recall,
                result.f1_score,
                result.avg_inference_time,
                result.avg_confidence,
                result.model_integrity_passed,
                result.performance_regression_detected,
                json.dumps(result.error_messages),
                json.dumps(result.detailed_metrics),
                result.confusion_matrix_path
            ))
    
    def get_validation_history(self, model_version: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get validation history"""
        with sqlite3.connect(self.registry_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM validation_results"
            params = []
            
            if model_version:
                query += " WHERE model_version = ?"
                params.append(model_version)
            
            query += " ORDER BY validation_timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'model_version': row['model_version'],
                    'validation_timestamp': row['validation_timestamp'],
                    'passed': bool(row['passed']),
                    'overall_score': row['overall_score'],
                    'accuracy': row['accuracy'],
                    'precision': row['precision'],
                    'recall': row['recall'],
                    'f1_score': row['f1_score'],
                    'avg_inference_time': row['avg_inference_time'],
                    'avg_confidence': row['avg_confidence'],
                    'model_integrity_passed': bool(row['model_integrity_passed']),
                    'performance_regression_detected': bool(row['performance_regression_detected']),
                    'error_messages': json.loads(row['error_messages']) if row['error_messages'] else [],
                    'detailed_metrics': json.loads(row['detailed_metrics']) if row['detailed_metrics'] else {},
                    'confusion_matrix_path': row['confusion_matrix_path']
                })
            
            return history
    
    def validate_uploaded_file(self, file, filename: str = None) -> FileValidationResult:
        """Comprehensive file validation for uploaded files"""
        if filename is None:
            filename = getattr(file, 'filename', 'unknown_file')
        
        result = FileValidationResult(
            filename=filename,
            is_valid=False,
            file_size=0
        )
        
        try:
            # Get file size
            if hasattr(file, 'seek'):
                file.seek(0, 2)  # Seek to end
                result.file_size = file.tell()
                file.seek(0)  # Reset to beginning
            
            # Read file content
            if hasattr(file, 'read'):
                file_content = file.read()
                file.seek(0)  # Reset for further processing
            else:
                file_content = file
            
            # Calculate file hash
            result.file_hash = hashlib.sha256(file_content).hexdigest()
            
            # Check file size
            if result.file_size > self.MAX_FILE_SIZE:
                result.validation_errors.append(
                    f"File too large: {result.file_size} bytes (max: {self.MAX_FILE_SIZE} bytes)"
                )
                return result
            
            if result.file_size == 0:
                result.validation_errors.append("File is empty")
                return result
            
            # Check file extension
            if '.' in filename:
                ext = filename.rsplit('.', 1)[1].lower()
                if ext not in self.ALLOWED_EXTENSIONS:
                    result.validation_errors.append(
                        f"Invalid file extension: {ext} (allowed: {', '.join(self.ALLOWED_EXTENSIONS)})"
                    )
                    return result
            
            # Detect MIME type
            try:
                if MAGIC_AVAILABLE:
                    result.detected_mime_type = magic.from_buffer(file_content, mime=True)
                else:
                    # Fallback: use PIL to detect image format
                    try:
                        image = Image.open(io.BytesIO(file_content))
                        format_to_mime = {
                            'JPEG': 'image/jpeg',
                            'PNG': 'image/png',
                            'GIF': 'image/gif',
                            'WEBP': 'image/webp'
                        }
                        result.detected_mime_type = format_to_mime.get(image.format, 'application/octet-stream')
                    except:
                        result.detected_mime_type = 'application/octet-stream'
                
                if result.detected_mime_type not in self.ALLOWED_MIME_TYPES:
                    result.validation_errors.append(
                        f"Unsupported MIME type: {result.detected_mime_type}"
                    )
                    return result
            except Exception as e:
                result.validation_errors.append(f"MIME type detection failed: {str(e)}")
                return result
            
            # Check for malicious signatures
            for signature, description in self.MALICIOUS_SIGNATURES.items():
                if file_content.startswith(signature):
                    result.security_flags.append(f"Malicious signature detected: {description}")
                    result.validation_errors.append(f"Security threat: {description}")
                    return result
            
            # Check for script content
            try:
                text_content = file_content.decode('utf-8', errors='ignore').lower()
                script_patterns = [
                    '<script', 'javascript:', 'vbscript:',
                    'onload=', 'onerror=', 'onclick=',
                    'eval(', 'document.', 'window.',
                    'php://', 'data://', 'file://'
                ]
                
                for pattern in script_patterns:
                    if pattern in text_content:
                        result.security_flags.append(f"Script content detected: {pattern}")
                        result.validation_errors.append(f"Security threat: {pattern}")
                        return result
            except UnicodeDecodeError:
                # Binary file, continue with image validation
                pass
            
            # Validate image content
            try:
                image = Image.open(io.BytesIO(file_content))
                
                # Verify image format
                if image.format not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                    result.validation_errors.append(
                        f"Unsupported image format: {image.format}"
                    )
                    return result
                
                # Get image dimensions
                result.image_dimensions = image.size
                width, height = image.size
                
                # Check dimensions
                if width < self.MIN_IMAGE_DIMENSION or height < self.MIN_IMAGE_DIMENSION:
                    result.validation_errors.append(
                        f"Image too small: {width}x{height} (min: {self.MIN_IMAGE_DIMENSION}x{self.MIN_IMAGE_DIMENSION})"
                    )
                    return result
                
                if width > self.MAX_IMAGE_DIMENSION or height > self.MAX_IMAGE_DIMENSION:
                    result.validation_errors.append(
                        f"Image too large: {width}x{height} (max: {self.MAX_IMAGE_DIMENSION}x{self.MAX_IMAGE_DIMENSION})"
                    )
                    return result
                
                # Verify image can be loaded
                image.verify()
                
                # Check aspect ratio
                aspect_ratio = max(width, height) / min(width, height)
                if aspect_ratio > 20:
                    result.validation_errors.append(
                        f"Extreme aspect ratio: {aspect_ratio:.2f}"
                    )
                    return result
                
                result.is_valid = True
                
            except Exception as e:
                result.validation_errors.append(f"Image validation failed: {str(e)}")
                return result
            
        except Exception as e:
            result.validation_errors.append(f"Validation error: {str(e)}")
        
        return result
    
    def batch_validate_files(self, file_list: List[Tuple[Any, str]]) -> List[FileValidationResult]:
        """Validate multiple files in batch"""
        results = []
        for file_data, filename in file_list:
            result = self.validate_uploaded_file(file_data, filename)
            results.append(result)
        return results
    
    def get_validation_summary(self, results: List[FileValidationResult]) -> Dict[str, Any]:
        """Get summary statistics for batch validation"""
        total_files = len(results)
        valid_files = sum(1 for r in results if r.is_valid)
        invalid_files = total_files - valid_files
        
        security_issues = sum(len(r.security_flags) for r in results)
        total_size = sum(r.file_size for r in results)
        
        mime_types = {}
        for result in results:
            if result.detected_mime_type:
                mime_types[result.detected_mime_type] = mime_types.get(result.detected_mime_type, 0) + 1
        
        return {
            'total_files': total_files,
            'valid_files': valid_files,
            'invalid_files': invalid_files,
            'success_rate': valid_files / total_files if total_files > 0 else 0,
            'security_issues': security_issues,
            'total_size_bytes': total_size,
            'mime_type_distribution': mime_types,
            'validation_timestamp': datetime.now().isoformat()
        }
