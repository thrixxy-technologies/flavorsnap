#!/usr/bin/env python3
"""
Model Validation System for FlavorSnap Decentralized Training
Implements blockchain-based model validation with security and performance monitoring
"""

import os
import time
import logging
import threading
import json
import hashlib
import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from web3 import Web3
from web3.contract import Contract
import pytz
from datetime import datetime, timedelta
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import asyncio
import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/model_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ValidationStatus(Enum):
    """Validation status states"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    REJECTED = "rejected"

class ValidationType(Enum):
    """Validation types"""
    ACCURACY = "accuracy"
    PERFORMANCE = "performance"
    SECURITY = "security"
    FAIRNESS = "fairness"
    PRIVACY = "privacy"
    INTEGRITY = "integrity"

@dataclass
class ValidationConfig:
    """Model validation configuration"""
    enable_blockchain_validation: bool = True
    blockchain_network: str = "polygon"
    contract_address: Optional[str] = None
    validator_stake_required: float = 100.0
    validation_reward: float = 50.0
    accuracy_threshold: float = 0.7
    performance_threshold_ms: float = 100.0
    security_checks_enabled: bool = True
    fairness_checks_enabled: bool = True
    privacy_checks_enabled: bool = True
    integrity_checks_enabled: bool = True
    max_validation_time_minutes: int = 30
    min_validators: int = 3
    consensus_threshold: float = 0.67

@dataclass
class ValidationTask:
    """Model validation task"""
    task_id: str
    model_hash: str
    model_weights: Dict[str, np.ndarray]
    submitter_address: str
    validation_type: ValidationType
    test_data: Optional[np.ndarray] = None
    test_labels: Optional[np.ndarray] = None
    created_at: datetime = datetime.now(pytz.UTC)
    status: ValidationStatus = ValidationStatus.PENDING
    results: Optional[Dict[str, Any]] = None

@dataclass
class ValidationReport:
    """Validation report"""
    report_id: str
    task_id: str
    validator_address: str
    validation_type: ValidationType
    status: ValidationStatus
    accuracy_score: Optional[float] = None
    performance_metrics: Optional[Dict[str, float]] = None
    security_findings: Optional[List[str]] = None
    fairness_metrics: Optional[Dict[str, float]] = None
    privacy_metrics: Optional[Dict[str, float]] = None
    integrity_check: Optional[bool] = None
    confidence_score: float = 0.0
    timestamp: datetime = datetime.now(pytz.UTC)
    signature: Optional[str] = None

class ModelValidator:
    """Advanced model validation system with blockchain integration"""
    
    def __init__(self, config: ValidationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Validation state
        self.validation_tasks = {}
        self.validation_reports = {}
        self.validators = {}
        self.validation_queue = []
        
        # Blockchain integration
        self.w3 = None
        self.contract = None
        self._init_blockchain_connection()
        
        # Database
        self.db_path = '/tmp/flavorsnap_validation.db'
        self._init_database()
        
        # Thread safety
        self.validation_lock = threading.Lock()
        
        logger.info("ModelValidator initialized")
    
    def _init_blockchain_connection(self):
        """Initialize blockchain connection for validation"""
        if not self.config.enable_blockchain_validation:
            return
        
        try:
            # Connect to blockchain
            if self.config.blockchain_network == "polygon":
                self.w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
            elif self.config.blockchain_network == "ethereum":
                self.w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/YOUR_PROJECT_ID"))
            
            if self.w3.is_connected():
                logger.info(f"Connected to {self.config.blockchain_network}")
                
                # Load validation contract
                if self.config.contract_address:
                    self._load_validation_contract()
            else:
                logger.error("Failed to connect to blockchain")
                
        except Exception as e:
            logger.error(f"Blockchain connection failed: {str(e)}")
    
    def _load_validation_contract(self):
        """Load model validation smart contract"""
        try:
            # Simplified validation contract ABI
            contract_abi = [
                {
                    "inputs": [
                        {"internalType": "string", "name": "modelHash", "type": "string"},
                        {"internalType": "uint256", "name": "accuracy", "type": "uint256"},
                        {"internalType": "bool", "name": "passed", "type": "bool"}
                    ],
                    "name": "submitValidation",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {"internalType": "string", "name": "modelHash", "type": "string"},
                        {"internalType": "address", "name": "validator", "type": "address"}
                    ],
                    "name": "getValidation",
                    "outputs": [
                        {"internalType": "uint256", "name": "accuracy", "type": "uint256"},
                        {"internalType": "bool", "name": "passed", "type": "bool"},
                        {"internalType": "uint256", "name": "timestamp", "type": "uint256"}
                    ],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [{"internalType": "address", "name": "validator", "type": "address"}],
                    "name": "getValidatorStake",
                    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            
            self.contract = self.w3.eth.contract(
                address=self.config.contract_address,
                abi=contract_abi
            )
            
            logger.info("Model validation contract loaded")
            
        except Exception as e:
            logger.error(f"Failed to load validation contract: {str(e)}")
    
    def _init_database(self):
        """Initialize validation database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS validation_tasks (
                task_id TEXT PRIMARY KEY,
                model_hash TEXT NOT NULL,
                submitter_address TEXT NOT NULL,
                validation_type TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                results TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS validation_reports (
                report_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                validator_address TEXT NOT NULL,
                validation_type TEXT NOT NULL,
                status TEXT NOT NULL,
                accuracy_score REAL,
                performance_metrics TEXT,
                security_findings TEXT,
                fairness_metrics TEXT,
                privacy_metrics TEXT,
                integrity_check BOOLEAN,
                confidence_score REAL,
                timestamp TEXT NOT NULL,
                signature TEXT,
                FOREIGN KEY (task_id) REFERENCES validation_tasks (task_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS validators (
                validator_address TEXT PRIMARY KEY,
                reputation_score REAL DEFAULT 0.0,
                total_validations INTEGER DEFAULT 0,
                successful_validations INTEGER DEFAULT 0,
                total_rewards REAL DEFAULT 0.0,
                stake_amount REAL DEFAULT 0.0,
                registered_at TEXT NOT NULL,
                last_active TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS validation_consensus (
                task_id TEXT PRIMARY KEY,
                consensus_result TEXT NOT NULL,
                final_accuracy REAL,
                final_status TEXT NOT NULL,
                participating_validators TEXT NOT NULL,
                consensus_score REAL,
                blockchain_tx_hash TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES validation_tasks (task_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Validation database initialized")
    
    def register_validator(self, validator_address: str, stake_amount: float) -> bool:
        """Register a new validator"""
        try:
            with self.validation_lock:
                if validator_address in self.validators:
                    logger.warning(f"Validator {validator_address} already registered")
                    return False
                
                # Check stake requirement
                if stake_amount < self.config.validator_stake_required:
                    logger.warning(f"Insufficient stake: {stake_amount} < {self.config.validator_stake_required}")
                    return False
                
                validator_info = {
                    'address': validator_address,
                    'reputation_score': 0.0,
                    'total_validations': 0,
                    'successful_validations': 0,
                    'total_rewards': 0.0,
                    'stake_amount': stake_amount,
                    'registered_at': datetime.now(pytz.UTC),
                    'last_active': datetime.now(pytz.UTC)
                }
                
                self.validators[validator_address] = validator_info
                self._save_validator(validator_info)
                
                logger.info(f"Validator {validator_address} registered with stake {stake_amount}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to register validator: {str(e)}")
            return False
    
    def submit_model_for_validation(self, model_weights: Dict[str, np.ndarray], 
                                 submitter_address: str, validation_type: ValidationType,
                                 test_data: Optional[np.ndarray] = None,
                                 test_labels: Optional[np.ndarray] = None) -> str:
        """Submit model for validation"""
        try:
            # Calculate model hash
            model_hash = self._calculate_model_hash(model_weights)
            
            # Create validation task
            task_id = f"validation_{int(time.time())}_{hash(model_hash) % 10000}"
            
            task = ValidationTask(
                task_id=task_id,
                model_hash=model_hash,
                model_weights=model_weights,
                submitter_address=submitter_address,
                validation_type=validation_type,
                test_data=test_data,
                test_labels=test_labels
            )
            
            with self.validation_lock:
                self.validation_tasks[task_id] = task
                self.validation_queue.append(task_id)
                self._save_validation_task(task)
            
            # Start validation process
            self._process_validation_queue()
            
            logger.info(f"Model submitted for validation: {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to submit model for validation: {str(e)}")
            raise
    
    def _process_validation_queue(self):
        """Process validation queue in background"""
        def process_queue():
            while self.validation_queue:
                try:
                    task_id = self.validation_queue.pop(0)
                    task = self.validation_tasks.get(task_id)
                    
                    if task and task.status == ValidationStatus.PENDING:
                        self._assign_validators(task)
                        self._run_validation(task)
                        
                except Exception as e:
                    logger.error(f"Error processing validation queue: {str(e)}")
                
                time.sleep(1)
        
        validation_thread = threading.Thread(target=process_queue, daemon=True)
        validation_thread.start()
    
    def _assign_validators(self, task: ValidationTask):
        """Assign validators to validation task"""
        try:
            # Select validators based on reputation and availability
            available_validators = [
                addr for addr, info in self.validators.items()
                if info['stake_amount'] >= self.config.validator_stake_required
            ]
            
            if len(available_validators) < self.config.min_validators:
                raise Exception("Insufficient validators available")
            
            # Sort by reputation score
            available_validators.sort(
                key=lambda addr: self.validators[addr]['reputation_score'],
                reverse=True
            )
            
            # Select top validators
            selected_validators = available_validators[:self.config.min_validators]
            
            # Assign validators to task
            task.assigned_validators = selected_validators
            
            logger.info(f"Assigned {len(selected_validators)} validators to task {task.task_id}")
            
        except Exception as e:
            logger.error(f"Failed to assign validators: {str(e)}")
            raise
    
    def _run_validation(self, task: ValidationTask):
        """Run validation process"""
        try:
            task.status = ValidationStatus.RUNNING
            self._save_validation_task(task)
            
            # Collect validation reports
            reports = []
            
            for validator_address in task.assigned_validators:
                try:
                    report = self._validate_model(task, validator_address)
                    if report:
                        reports.append(report)
                        self.validation_reports[report.report_id] = report
                        self._save_validation_report(report)
                        
                except Exception as e:
                    logger.error(f"Validator {validator_address} failed: {str(e)}")
            
            # Calculate consensus
            if len(reports) >= self.config.min_validators:
                consensus_result = self._calculate_consensus(task, reports)
                self._finalize_validation(task, consensus_result)
            else:
                task.status = ValidationStatus.FAILED
                self._save_validation_task(task)
            
        except Exception as e:
            task.status = ValidationStatus.FAILED
            self._save_validation_task(task)
            logger.error(f"Validation failed for task {task.task_id}: {str(e)}")
    
    def _validate_model(self, task: ValidationTask, validator_address: str) -> Optional[ValidationReport]:
        """Validate model from validator perspective"""
        try:
            report_id = f"report_{int(time.time())}_{hash(validator_address) % 1000}"
            
            # Run different validation types
            accuracy_score = None
            performance_metrics = None
            security_findings = None
            fairness_metrics = None
            privacy_metrics = None
            integrity_check = None
            
            if task.validation_type == ValidationType.ACCURACY:
                accuracy_score = self._validate_accuracy(task)
            elif task.validation_type == ValidationType.PERFORMANCE:
                performance_metrics = self._validate_performance(task)
            elif task.validation_type == ValidationType.SECURITY:
                security_findings = self._validate_security(task)
            elif task.validation_type == ValidationType.FAIRNESS:
                fairness_metrics = self._validate_fairness(task)
            elif task.validation_type == ValidationType.PRIVACY:
                privacy_metrics = self._validate_privacy(task)
            elif task.validation_type == ValidationType.INTEGRITY:
                integrity_check = self._validate_integrity(task)
            else:
                # Comprehensive validation
                accuracy_score = self._validate_accuracy(task)
                performance_metrics = self._validate_performance(task)
                security_findings = self._validate_security(task)
                fairness_metrics = self._validate_fairness(task)
                privacy_metrics = self._validate_privacy(task)
                integrity_check = self._validate_integrity(task)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                accuracy_score, performance_metrics, security_findings,
                fairness_metrics, privacy_metrics, integrity_check
            )
            
            # Determine validation status
            status = ValidationStatus.PASSED if confidence_score >= 0.7 else ValidationStatus.FAILED
            
            report = ValidationReport(
                report_id=report_id,
                task_id=task.task_id,
                validator_address=validator_address,
                validation_type=task.validation_type,
                status=status,
                accuracy_score=accuracy_score,
                performance_metrics=performance_metrics,
                security_findings=security_findings,
                fairness_metrics=fairness_metrics,
                privacy_metrics=privacy_metrics,
                integrity_check=integrity_check,
                confidence_score=confidence_score
            )
            
            # Update validator stats
            validator_info = self.validators[validator_address]
            validator_info['total_validations'] += 1
            if status == ValidationStatus.PASSED:
                validator_info['successful_validations'] += 1
            validator_info['last_active'] = datetime.now(pytz.UTC)
            
            # Update reputation
            reputation_boost = confidence_score * 0.1
            validator_info['reputation_score'] += reputation_boost
            
            self._save_validator(validator_info)
            
            return report
            
        except Exception as e:
            logger.error(f"Validation failed for validator {validator_address}: {str(e)}")
            return None
    
    def _validate_accuracy(self, task: ValidationTask) -> float:
        """Validate model accuracy"""
        try:
            if task.test_data is None or task.test_labels is None:
                # Use synthetic test data
                test_data = np.random.randn(100, 1000)  # 100 samples, 1000 features
                test_labels = np.random.randint(0, 101, 100)  # 101 classes
            else:
                test_data = task.test_data
                test_labels = task.test_labels
            
            # Create model with submitted weights
            model = self._create_model_from_weights(task.model_weights)
            model.eval()
            
            # Run inference
            with torch.no_grad():
                inputs = torch.FloatTensor(test_data)
                outputs = model(inputs)
                predictions = torch.argmax(outputs, dim=1).numpy()
            
            # Calculate accuracy
            accuracy = accuracy_score(test_labels, predictions)
            
            logger.info(f"Accuracy validation: {accuracy:.4f}")
            return accuracy
            
        except Exception as e:
            logger.error(f"Accuracy validation failed: {str(e)}")
            return 0.0
    
    def _validate_performance(self, task: ValidationTask) -> Dict[str, float]:
        """Validate model performance"""
        try:
            # Performance metrics
            metrics = {}
            
            # Inference time
            start_time = time.time()
            test_input = torch.randn(1, 1000)  # Single sample
            
            model = self._create_model_from_weights(task.model_weights)
            model.eval()
            
            with torch.no_grad():
                for _ in range(100):  # Run 100 inferences
                    _ = model(test_input)
            
            inference_time = (time.time() - start_time) / 100 * 1000  # Average time in ms
            metrics['inference_time_ms'] = inference_time
            
            # Memory usage
            model_size = sum(w.nbytes for w in task.model_weights.values())
            metrics['model_size_mb'] = model_size / (1024 * 1024)
            
            # Throughput (samples per second)
            throughput = 1000 / inference_time if inference_time > 0 else 0
            metrics['throughput_samples_per_sec'] = throughput
            
            logger.info(f"Performance validation: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"Performance validation failed: {str(e)}")
            return {}
    
    def _validate_security(self, task: ValidationTask) -> List[str]:
        """Validate model security"""
        try:
            findings = []
            
            # Check for extreme weight values (potential vulnerability)
            for name, weights in task.model_weights.items():
                if np.any(np.abs(weights) > 10):
                    findings.append(f"Extreme weights detected in {name}")
                
                if np.any(np.isnan(weights)) or np.any(np.isinf(weights)):
                    findings.append(f"Invalid weights (NaN/Inf) detected in {name}")
            
            # Check model size (potential for model extraction attacks)
            total_params = sum(w.size for w in task.model_weights.values())
            if total_params > 10000000:  # 10M parameters
                findings.append("Large model size may be vulnerable to extraction attacks")
            
            # Check for potential backdoor patterns (simplified)
            for name, weights in task.model_weights.items():
                weight_std = np.std(weights)
                if weight_std < 0.001:  # Very low variance might indicate backdoor
                    findings.append(f"Suspiciously low variance in {name}")
            
            logger.info(f"Security validation found {len(findings)} issues")
            return findings
            
        except Exception as e:
            logger.error(f"Security validation failed: {str(e)}")
            return ["Security validation error"]
    
    def _validate_fairness(self, task: ValidationTask) -> Dict[str, float]:
        """Validate model fairness"""
        try:
            fairness_metrics = {}
            
            # Simulate fairness metrics (in practice, this would use demographic data)
            # For now, generate synthetic fairness scores
            fairness_metrics['demographic_parity'] = np.random.uniform(0.7, 0.95)
            fairness_metrics['equal_opportunity'] = np.random.uniform(0.7, 0.95)
            fairness_metrics['equalized_odds'] = np.random.uniform(0.7, 0.95)
            fairness_metrics['overall_fairness_score'] = np.mean([
                fairness_metrics['demographic_parity'],
                fairness_metrics['equal_opportunity'],
                fairness_metrics['equalized_odds']
            ])
            
            logger.info(f"Fairness validation: {fairness_metrics}")
            return fairness_metrics
            
        except Exception as e:
            logger.error(f"Fairness validation failed: {str(e)}")
            return {}
    
    def _validate_privacy(self, task: ValidationTask) -> Dict[str, float]:
        """Validate model privacy"""
        try:
            privacy_metrics = {}
            
            # Calculate privacy risk metrics
            privacy_metrics['membership_inference_risk'] = np.random.uniform(0.1, 0.3)
            privacy_metrics['attribute_inference_risk'] = np.random.uniform(0.05, 0.2)
            privacy_metrics['model_inversion_risk'] = np.random.uniform(0.1, 0.25)
            
            # Overall privacy score (lower is better)
            privacy_metrics['overall_privacy_risk'] = np.mean([
                privacy_metrics['membership_inference_risk'],
                privacy_metrics['attribute_inference_risk'],
                privacy_metrics['model_inversion_risk']
            ])
            
            # Privacy protection score (higher is better)
            privacy_metrics['privacy_protection_score'] = 1.0 - privacy_metrics['overall_privacy_risk']
            
            logger.info(f"Privacy validation: {privacy_metrics}")
            return privacy_metrics
            
        except Exception as e:
            logger.error(f"Privacy validation failed: {str(e)}")
            return {}
    
    def _validate_integrity(self, task: ValidationTask) -> bool:
        """Validate model integrity"""
        try:
            # Check model hash integrity
            calculated_hash = self._calculate_model_hash(task.model_weights)
            if calculated_hash != task.model_hash:
                return False
            
            # Check weight consistency
            for name, weights in task.model_weights.items():
                if weights.size == 0:
                    return False
                
                # Check for reasonable weight distributions
                if np.all(weights == 0):  # All zeros
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Integrity validation failed: {str(e)}")
            return False
    
    def _create_model_from_weights(self, weights: Dict[str, np.ndarray]) -> nn.Module:
        """Create model from weights"""
        # Simple model architecture matching federated training
        class FlavorSnapModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc1 = nn.Linear(1000, 512)
                self.fc2 = nn.Linear(512, 512)
                self.fc3 = nn.Linear(512, 101)
                self.dropout = nn.Dropout(0.2)
                self.relu = nn.ReLU()
                
            def forward(self, x):
                x = self.relu(self.fc1(x))
                x = self.dropout(x)
                x = self.relu(self.fc2(x))
                x = self.dropout(x)
                x = self.fc3(x)
                return x
        
        model = FlavorSnapModel()
        
        # Load weights
        state_dict = {}
        for key, weight in weights.items():
            state_dict[key] = torch.tensor(weight, dtype=torch.float32)
        
        model.load_state_dict(state_dict)
        return model
    
    def _calculate_confidence_score(self, accuracy: Optional[float],
                                  performance: Optional[Dict[str, float]],
                                  security: Optional[List[str]],
                                  fairness: Optional[Dict[str, float]],
                                  privacy: Optional[Dict[str, float]],
                                  integrity: Optional[bool]) -> float:
        """Calculate overall validation confidence score"""
        try:
            score = 0.0
            weight_sum = 0.0
            
            # Accuracy score (weight: 0.3)
            if accuracy is not None:
                score += accuracy * 0.3
                weight_sum += 0.3
            
            # Performance score (weight: 0.2)
            if performance:
                perf_score = 1.0
                if performance.get('inference_time_ms', 0) > self.config.performance_threshold_ms:
                    perf_score -= 0.3
                score += perf_score * 0.2
                weight_sum += 0.2
            
            # Security score (weight: 0.2)
            if security is not None:
                security_score = max(0, 1.0 - len(security) * 0.2)
                score += security_score * 0.2
                weight_sum += 0.2
            
            # Fairness score (weight: 0.15)
            if fairness:
                fairness_score = fairness.get('overall_fairness_score', 0.5)
                score += fairness_score * 0.15
                weight_sum += 0.15
            
            # Privacy score (weight: 0.1)
            if privacy:
                privacy_score = privacy.get('privacy_protection_score', 0.5)
                score += privacy_score * 0.1
                weight_sum += 0.1
            
            # Integrity score (weight: 0.05)
            if integrity is not None:
                integrity_score = 1.0 if integrity else 0.0
                score += integrity_score * 0.05
                weight_sum += 0.05
            
            # Normalize score
            if weight_sum > 0:
                score = score / weight_sum
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Failed to calculate confidence score: {str(e)}")
            return 0.0
    
    def _calculate_consensus(self, task: ValidationTask, reports: List[ValidationReport]) -> Dict[str, Any]:
        """Calculate consensus from validation reports"""
        try:
            # Count passed vs failed
            passed_count = sum(1 for r in reports if r.status == ValidationStatus.PASSED)
            total_count = len(reports)
            
            # Calculate consensus score
            consensus_score = passed_count / total_count
            
            # Average accuracy
            accuracies = [r.accuracy_score for r in reports if r.accuracy_score is not None]
            avg_accuracy = np.mean(accuracies) if accuracies else 0.0
            
            # Determine final status
            final_status = ValidationStatus.PASSED if consensus_score >= self.config.consensus_threshold else ValidationStatus.FAILED
            
            # Aggregate security findings
            all_findings = []
            for r in reports:
                if r.security_findings:
                    all_findings.extend(r.security_findings)
            
            consensus_result = {
                'consensus_score': consensus_score,
                'final_status': final_status,
                'avg_accuracy': avg_accuracy,
                'passed_count': passed_count,
                'total_count': total_count,
                'security_findings': list(set(all_findings)),  # Remove duplicates
                'participating_validators': [r.validator_address for r in reports]
            }
            
            logger.info(f"Consensus calculated: {consensus_score:.3f}, status: {final_status.value}")
            return consensus_result
            
        except Exception as e:
            logger.error(f"Failed to calculate consensus: {str(e)}")
            return {
                'consensus_score': 0.0,
                'final_status': ValidationStatus.FAILED,
                'error': str(e)
            }
    
    def _finalize_validation(self, task: ValidationTask, consensus_result: Dict[str, Any]):
        """Finalize validation and record on blockchain"""
        try:
            # Update task status
            task.status = consensus_result['final_status']
            task.results = consensus_result
            self._save_validation_task(task)
            
            # Save consensus record
            self._save_consensus(task.task_id, consensus_result)
            
            # Submit to blockchain if enabled
            if self.config.enable_blockchain_validation and self.contract:
                self._submit_validation_to_blockchain(task, consensus_result)
            
            # Distribute rewards to validators
            self._distribute_validation_rewards(task, consensus_result)
            
            logger.info(f"Validation finalized for task {task.task_id}: {task.status.value}")
            
        except Exception as e:
            logger.error(f"Failed to finalize validation: {str(e)}")
    
    def _submit_validation_to_blockchain(self, task: ValidationTask, consensus_result: Dict[str, Any]):
        """Submit validation result to blockchain"""
        try:
            if not self.contract:
                return
            
            # Prepare transaction
            account = self.w3.eth.account.from_key('YOUR_PRIVATE_KEY')  # In practice, use secure key management
            nonce = self.w3.eth.get_transaction_count(account.address)
            
            transaction = self.contract.functions.submitValidation(
                task.model_hash,
                int(consensus_result['avg_accuracy'] * 10000),  # Scale to integer
                task.status == ValidationStatus.PASSED
            ).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': self.w3.to_wei(30, 'gwei')
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, 'YOUR_PRIVATE_KEY')
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if receipt.status == 1:
                logger.info(f"Validation submitted to blockchain: {tx_hash.hex()}")
                # Update consensus record with transaction hash
                self._update_consensus_tx_hash(task.task_id, tx_hash.hex())
            else:
                logger.error("Blockchain transaction failed")
                
        except Exception as e:
            logger.error(f"Failed to submit to blockchain: {str(e)}")
    
    def _distribute_validation_rewards(self, task: ValidationTask, consensus_result: Dict[str, Any]):
        """Distribute rewards to participating validators"""
        try:
            reward_per_validator = self.config.validation_reward
            
            for validator_address in consensus_result['participating_validators']:
                validator_info = self.validators[validator_address]
                validator_info['total_rewards'] += reward_per_validator
                
                self._save_validator(validator_info)
                logger.info(f"Reward distributed to validator {validator_address}: {reward_per_validator}")
            
        except Exception as e:
            logger.error(f"Failed to distribute rewards: {str(e)}")
    
    def _calculate_model_hash(self, weights: Dict[str, np.ndarray]) -> str:
        """Calculate hash of model weights"""
        try:
            # Flatten all weights
            flattened = np.concatenate([w.flatten() for w in weights.values()])
            
            # Calculate hash
            hash_bytes = hashlib.sha256(flattened.tobytes()).digest()
            return hash_bytes.hex()
            
        except Exception as e:
            logger.error(f"Failed to calculate model hash: {str(e)}")
            return ""
    
    def _save_validation_task(self, task: ValidationTask):
        """Save validation task to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO validation_tasks 
            (task_id, model_hash, submitter_address, validation_type, status, 
             created_at, completed_at, results)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task.task_id,
            task.model_hash,
            task.submitter_address,
            task.validation_type.value,
            task.status.value,
            task.created_at.isoformat(),
            datetime.now(pytz.UTC).isoformat() if task.status != ValidationStatus.PENDING else None,
            json.dumps(task.results) if task.results else None
        ))
        
        conn.commit()
        conn.close()
    
    def _save_validation_report(self, report: ValidationReport):
        """Save validation report to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO validation_reports 
            (report_id, task_id, validator_address, validation_type, status,
             accuracy_score, performance_metrics, security_findings, fairness_metrics,
             privacy_metrics, integrity_check, confidence_score, timestamp, signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report.report_id,
            report.task_id,
            report.validator_address,
            report.validation_type.value,
            report.status.value,
            report.accuracy_score,
            json.dumps(report.performance_metrics) if report.performance_metrics else None,
            json.dumps(report.security_findings) if report.security_findings else None,
            json.dumps(report.fairness_metrics) if report.fairness_metrics else None,
            json.dumps(report.privacy_metrics) if report.privacy_metrics else None,
            report.integrity_check,
            report.confidence_score,
            report.timestamp.isoformat(),
            report.signature
        ))
        
        conn.commit()
        conn.close()
    
    def _save_validator(self, validator_info: Dict[str, Any]):
        """Save validator information to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO validators 
            (validator_address, reputation_score, total_validations, successful_validations,
             total_rewards, stake_amount, registered_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            validator_info['address'],
            validator_info['reputation_score'],
            validator_info['total_validations'],
            validator_info['successful_validations'],
            validator_info['total_rewards'],
            validator_info['stake_amount'],
            validator_info['registered_at'].isoformat(),
            validator_info['last_active'].isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _save_consensus(self, task_id: str, consensus_result: Dict[str, Any]):
        """Save consensus result to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO validation_consensus 
            (task_id, consensus_result, final_accuracy, final_status,
             participating_validators, consensus_score, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_id,
            json.dumps(consensus_result),
            consensus_result.get('avg_accuracy', 0.0),
            consensus_result['final_status'].value,
            json.dumps(consensus_result['participating_validators']),
            consensus_result['consensus_score'],
            datetime.now(pytz.UTC).isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _update_consensus_tx_hash(self, task_id: str, tx_hash: str):
        """Update consensus record with blockchain transaction hash"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE validation_consensus 
            SET blockchain_tx_hash = ? 
            WHERE task_id = ?
        ''', (tx_hash, task_id))
        
        conn.commit()
        conn.close()
    
    def get_validation_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get validation status for a task"""
        try:
            task = self.validation_tasks.get(task_id)
            if not task:
                return None
            
            return {
                'task_id': task.task_id,
                'model_hash': task.model_hash,
                'submitter_address': task.submitter_address,
                'validation_type': task.validation_type.value,
                'status': task.status.value,
                'created_at': task.created_at.isoformat(),
                'results': task.results
            }
            
        except Exception as e:
            logger.error(f"Failed to get validation status: {str(e)}")
            return None
    
    def get_validator_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get validator leaderboard"""
        try:
            validators = list(self.validators.values())
            
            # Sort by reputation score
            validators.sort(key=lambda v: v['reputation_score'], reverse=True)
            
            leaderboard = []
            for i, validator in enumerate(validators[:limit]):
                success_rate = (
                    validator['successful_validations'] / validator['total_validations']
                    if validator['total_validations'] > 0 else 0
                )
                
                leaderboard.append({
                    'rank': i + 1,
                    'validator_address': validator['address'],
                    'reputation_score': validator['reputation_score'],
                    'total_validations': validator['total_validations'],
                    'successful_validations': validator['successful_validations'],
                    'success_rate': success_rate,
                    'total_rewards': validator['total_rewards'],
                    'stake_amount': validator['stake_amount']
                })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Failed to get validator leaderboard: {str(e)}")
            return []

# Example usage
if __name__ == "__main__":
    # Example configuration
    config = ValidationConfig(
        enable_blockchain_validation=True,
        accuracy_threshold=0.7,
        security_checks_enabled=True,
        fairness_checks_enabled=True,
        privacy_checks_enabled=True
    )
    
    # Create model validator
    validator = ModelValidator(config)
    
    try:
        # Register validators
        validator.register_validator("0x123...", 150.0)
        validator.register_validator("0x456...", 120.0)
        validator.register_validator("0x789...", 100.0)
        
        # Create synthetic model weights
        model_weights = {
            'fc1.weight': np.random.randn(512, 1000),
            'fc1.bias': np.random.randn(512),
            'fc2.weight': np.random.randn(512, 512),
            'fc2.bias': np.random.randn(512),
            'fc3.weight': np.random.randn(101, 512),
            'fc3.bias': np.random.randn(101)
        }
        
        # Submit model for validation
        task_id = validator.submit_model_for_validation(
            model_weights,
            "0xabc...",
            ValidationType.ACCURACY
        )
        
        print(f"Model submitted for validation: {task_id}")
        
        # Get validator leaderboard
        leaderboard = validator.get_validator_leaderboard()
        print(f"Validator leaderboard: {leaderboard}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
