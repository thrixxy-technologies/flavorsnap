#!/usr/bin/env python3
"""
Decentralized Model Training for FlavorSnap ML Model API
Implements federated learning with blockchain-based validation and privacy preservation
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
import torch.optim as optim
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from web3 import Web3
from web3.contract import Contract
import pytz
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
import aiohttp
from cryptography.fernet import Fernet
import differential_privacy
from secure_aggregation import SecureAggregator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/federated_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TrainingStatus(Enum):
    """Training status states"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    TRAINING = "training"
    AGGREGATING = "aggregating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"

class PrivacyLevel(Enum):
    """Privacy protection levels"""
    NONE = "none"
    BASIC = "basic"
    STANDARD = "standard"
    HIGH = "high"
    MAXIMUM = "maximum"

@dataclass
class FederatedConfig:
    """Federated learning configuration"""
    min_participants: int = 3
    max_participants: int = 50
    rounds_per_training: int = 10
    local_epochs: int = 5
    learning_rate: float = 0.01
    batch_size: int = 32
    privacy_level: PrivacyLevel = PrivacyLevel.STANDARD
    enable_differential_privacy: bool = True
    epsilon: float = 1.0  # Privacy budget
    delta: float = 1e-5  # Failure probability
    enable_secure_aggregation: bool = True
    enable_blockchain_validation: bool = True
    blockchain_network: str = "polygon"
    contract_address: Optional[str] = None
    reward_token_address: Optional[str] = None
    participation_reward: float = 10.0
    validation_reward: float = 5.0
    model_accuracy_threshold: float = 0.8
    convergence_threshold: float = 0.001
    max_training_time_minutes: int = 60

@dataclass
class ParticipantInfo:
    """Participant information"""
    participant_id: str
    address: str
    reputation_score: float
    data_size: int
    computation_power: float
    join_time: datetime
    last_active: datetime
    contribution_count: int
    total_rewards: float
    status: str

@dataclass
class ModelUpdate:
    """Model update from participant"""
    participant_id: str
    round_number: int
    model_weights: Dict[str, np.ndarray]
    update_size: int
    computation_time: float
    accuracy_score: float
    loss_score: float
    timestamp: datetime
    signature: Optional[str] = None

@dataclass
class TrainingRound:
    """Training round information"""
    round_id: str
    round_number: int
    participants: List[str]
    model_updates: List[ModelUpdate]
    aggregated_weights: Dict[str, np.ndarray]
    global_accuracy: float
    global_loss: float
    start_time: datetime
    end_time: Optional[datetime]
    status: TrainingStatus
    rewards_distributed: bool

class FederatedLearningCoordinator:
    """Advanced federated learning coordinator"""
    
    def __init__(self, config: FederatedConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Training state
        self.current_round = 0
        self.global_model = None
        self.participants = {}
        self.training_rounds = []
        self.training_status = TrainingStatus.IDLE
        
        # Privacy and security
        self.encryption_key = Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        self.secure_aggregator = SecureAggregator() if config.enable_secure_aggregation else None
        
        # Blockchain integration
        self.w3 = None
        self.contract = None
        self._init_blockchain_connection()
        
        # Database
        self.db_path = '/tmp/flavorsnap_federated.db'
        self._init_database()
        
        # Thread safety
        self.training_lock = threading.Lock()
        self.participant_lock = threading.Lock()
        
        logger.info("FederatedLearningCoordinator initialized")
    
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
                
                # Load federated learning contract
                if self.config.contract_address:
                    self._load_federated_contract()
            else:
                logger.error("Failed to connect to blockchain")
                
        except Exception as e:
            logger.error(f"Blockchain connection failed: {str(e)}")
    
    def _load_federated_contract(self):
        """Load federated learning smart contract"""
        try:
            # Simplified federated learning ABI
            contract_abi = [
                {
                    "inputs": [
                        {"internalType": "string", "name": "modelHash", "type": "string"},
                        {"internalType": "uint256", "name": "round", "type": "uint256"},
                        {"internalType": "uint256", "name": "accuracy", "type": "uint256"}
                    ],
                    "name": "submitModelUpdate",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {"internalType": "address", "name": "participant", "type": "address"},
                        {"internalType": "uint256", "name": "amount", "type": "uint256"}
                    ],
                    "name": "distributeReward",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [{"internalType": "address", "name": "participant", "type": "address"}],
                    "name": "getReputation",
                    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            
            self.contract = self.w3.eth.contract(
                address=self.config.contract_address,
                abi=contract_abi
            )
            
            logger.info("Federated learning contract loaded")
            
        except Exception as e:
            logger.error(f"Failed to load contract: {str(e)}")
    
    def _init_database(self):
        """Initialize federated learning database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS participants (
                participant_id TEXT PRIMARY KEY,
                address TEXT NOT NULL,
                reputation_score REAL DEFAULT 0.0,
                data_size INTEGER DEFAULT 0,
                computation_power REAL DEFAULT 0.0,
                join_time TEXT NOT NULL,
                last_active TEXT NOT NULL,
                contribution_count INTEGER DEFAULT 0,
                total_rewards REAL DEFAULT 0.0,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_rounds (
                round_id TEXT PRIMARY KEY,
                round_number INTEGER NOT NULL,
                participants TEXT NOT NULL,
                global_accuracy REAL,
                global_loss REAL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL,
                rewards_distributed BOOLEAN DEFAULT FALSE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                model_hash TEXT NOT NULL,
                accuracy_score REAL,
                loss_score REAL,
                computation_time REAL,
                timestamp TEXT NOT NULL,
                signature TEXT,
                FOREIGN KEY (round_id) REFERENCES training_rounds (round_id),
                FOREIGN KEY (participant_id) REFERENCES participants (participant_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                reward_amount REAL NOT NULL,
                reward_type TEXT NOT NULL,
                transaction_hash TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (round_id) REFERENCES training_rounds (round_id),
                FOREIGN KEY (participant_id) REFERENCES participants (participant_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Federated learning database initialized")
    
    def initialize_global_model(self, model_architecture: Dict[str, Any]):
        """Initialize the global model"""
        try:
            # Create model based on architecture
            self.global_model = self._create_model(model_architecture)
            
            # Save initial model state
            initial_state = {
                'architecture': model_architecture,
                'weights': {k: v.cpu().numpy() for k, v in self.global_model.state_dict().items()},
                'created_at': datetime.now(pytz.UTC).isoformat()
            }
            
            self._save_model_state('initial', initial_state)
            
            logger.info("Global model initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize global model: {str(e)}")
            raise
    
    def _create_model(self, architecture: Dict[str, Any]) -> nn.Module:
        """Create model based on architecture"""
        # Simplified model creation - in practice, this would be more sophisticated
        class FlavorSnapModel(nn.Module):
            def __init__(self, input_size: int, hidden_size: int, output_size: int):
                super().__init__()
                self.fc1 = nn.Linear(input_size, hidden_size)
                self.fc2 = nn.Linear(hidden_size, hidden_size)
                self.fc3 = nn.Linear(hidden_size, output_size)
                self.dropout = nn.Dropout(0.2)
                self.relu = nn.ReLU()
                
            def forward(self, x):
                x = self.relu(self.fc1(x))
                x = self.dropout(x)
                x = self.relu(self.fc2(x))
                x = self.dropout(x)
                x = self.fc3(x)
                return x
        
        input_size = architecture.get('input_size', 1000)
        hidden_size = architecture.get('hidden_size', 512)
        output_size = architecture.get('output_size', 101)  # 101 food classes
        
        return FlavorSnapModel(input_size, hidden_size, output_size)
    
    def register_participant(self, participant_id: str, address: str, 
                           data_size: int, computation_power: float) -> bool:
        """Register a new participant"""
        try:
            with self.participant_lock:
                if participant_id in self.participants:
                    logger.warning(f"Participant {participant_id} already registered")
                    return False
                
                if len(self.participants) >= self.config.max_participants:
                    logger.warning("Maximum participants reached")
                    return False
                
                participant = ParticipantInfo(
                    participant_id=participant_id,
                    address=address,
                    reputation_score=0.0,
                    data_size=data_size,
                    computation_power=computation_power,
                    join_time=datetime.now(pytz.UTC),
                    last_active=datetime.now(pytz.UTC),
                    contribution_count=0,
                    total_rewards=0.0,
                    status='active'
                )
                
                self.participants[participant_id] = participant
                self._save_participant(participant)
                
                logger.info(f"Participant {participant_id} registered")
                return True
                
        except Exception as e:
            logger.error(f"Failed to register participant: {str(e)}")
            return False
    
    def start_federated_training(self, num_rounds: int = None) -> str:
        """Start federated learning training"""
        with self.training_lock:
            if self.training_status != TrainingStatus.IDLE:
                raise Exception("Training already in progress")
            
            if len(self.participants) < self.config.min_participants:
                raise Exception(f"Need at least {self.config.min_participants} participants")
            
            num_rounds = num_rounds or self.config.rounds_per_training
            training_id = f"training_{int(time.time())}"
            
            # Start training in background thread
            training_thread = threading.Thread(
                target=self._run_federated_training,
                args=(training_id, num_rounds),
                daemon=True
            )
            training_thread.start()
            
            logger.info(f"Federated training started: {training_id}")
            return training_id
    
    def _run_federated_training(self, training_id: str, num_rounds: int):
        """Run federated learning training rounds"""
        try:
            self.training_status = TrainingStatus.TRAINING
            
            for round_num in range(num_rounds):
                self.current_round = round_num + 1
                
                # Create training round
                round_id = f"{training_id}_round_{round_num}"
                training_round = TrainingRound(
                    round_id=round_id,
                    round_number=round_num,
                    participants=list(self.participants.keys()),
                    model_updates=[],
                    aggregated_weights={},
                    global_accuracy=0.0,
                    global_loss=0.0,
                    start_time=datetime.now(pytz.UTC),
                    end_time=None,
                    status=TrainingStatus.TRAINING,
                    rewards_distributed=False
                )
                
                logger.info(f"Starting round {round_num + 1}/{num_rounds}")
                
                # Select participants for this round
                selected_participants = self._select_participants()
                training_round.participants = selected_participants
                
                # Collect model updates
                updates = self._collect_model_updates(round_id, selected_participants)
                training_round.model_updates = updates
                
                if len(updates) < self.config.min_participants:
                    logger.warning(f"Insufficient updates in round {round_num + 1}")
                    continue
                
                # Aggregate updates
                self.training_status = TrainingStatus.AGGREGATING
                aggregated_weights = self._aggregate_model_updates(updates)
                training_round.aggregated_weights = aggregated_weights
                
                # Update global model
                self._update_global_model(aggregated_weights)
                
                # Validate global model
                self.training_status = TrainingStatus.VALIDATING
                accuracy, loss = self._validate_global_model()
                training_round.global_accuracy = accuracy
                training_round.global_loss = loss
                
                # Check convergence
                if self._check_convergence(accuracy, loss):
                    logger.info(f"Training converged at round {round_num + 1}")
                    break
                
                # Distribute rewards
                self._distribute_round_rewards(training_round)
                training_round.rewards_distributed = True
                
                # Complete round
                training_round.end_time = datetime.now(pytz.UTC)
                training_round.status = TrainingStatus.COMPLETED
                self.training_rounds.append(training_round)
                self._save_training_round(training_round)
                
                logger.info(f"Round {round_num + 1} completed. Accuracy: {accuracy:.4f}")
            
            self.training_status = TrainingStatus.COMPLETED
            logger.info("Federated training completed")
            
        except Exception as e:
            self.training_status = TrainingStatus.FAILED
            logger.error(f"Federated training failed: {str(e)}")
    
    def _select_participants(self) -> List[str]:
        """Select participants for current round"""
        # Select based on reputation and availability
        available_participants = [
            pid for pid, info in self.participants.items() 
            if info.status == 'active'
        ]
        
        # Sort by reputation score
        available_participants.sort(
            key=lambda pid: self.participants[pid].reputation_score,
            reverse=True
        )
        
        # Select top participants
        max_per_round = min(len(available_participants), 10)  # Limit to 10 per round
        return available_participants[:max_per_round]
    
    def _collect_model_updates(self, round_id: str, participants: List[str]) -> List[ModelUpdate]:
        """Collect model updates from participants"""
        updates = []
        
        for participant_id in participants:
            try:
                # Simulate participant training (in practice, this would be API calls)
                update = self._simulate_participant_training(participant_id, round_id)
                
                if update:
                    # Apply differential privacy if enabled
                    if self.config.enable_differential_privacy:
                        update = self._apply_differential_privacy(update)
                    
                    # Validate update
                    if self._validate_model_update(update):
                        updates.append(update)
                        self._save_model_update(round_id, update)
                        
                        # Update participant stats
                        self.participants[participant_id].contribution_count += 1
                        self.participants[participant_id].last_active = datetime.now(pytz.UTC)
                
            except Exception as e:
                logger.error(f"Failed to collect update from {participant_id}: {str(e)}")
        
        return updates
    
    def _simulate_participant_training(self, participant_id: str, round_id: str) -> Optional[ModelUpdate]:
        """Simulate participant model training"""
        try:
            # Get current global weights
            global_weights = {k: v.cpu().numpy() for k, v in self.global_model.state_dict().items()}
            
            # Simulate local training (add some noise to weights)
            local_weights = {}
            for key, weight in global_weights.items():
                noise = np.random.normal(0, 0.01, weight.shape)
                local_weights[key] = weight + noise
            
            # Calculate model hash
            model_hash = self._calculate_model_hash(local_weights)
            
            # Simulate training metrics
            accuracy = 0.75 + np.random.normal(0, 0.1)  # Random accuracy around 75%
            loss = 1.0 - accuracy + np.random.normal(0, 0.05)
            computation_time = np.random.uniform(30, 300)  # 30-300 seconds
            
            update = ModelUpdate(
                participant_id=participant_id,
                round_number=self.current_round,
                model_weights=local_weights,
                update_size=sum(w.nbytes for w in local_weights.values()),
                computation_time=computation_time,
                accuracy_score=accuracy,
                loss_score=loss,
                timestamp=datetime.now(pytz.UTC)
            )
            
            return update
            
        except Exception as e:
            logger.error(f"Failed to simulate training for {participant_id}: {str(e)}")
            return None
    
    def _apply_differential_privacy(self, update: ModelUpdate) -> ModelUpdate:
        """Apply differential privacy to model update"""
        try:
            # Add noise based on privacy budget
            noise_scale = self.config.epsilon / len(update.model_weights)
            
            for key in update.model_weights:
                noise = np.random.normal(0, noise_scale, update.model_weights[key].shape)
                update.model_weights[key] += noise
            
            return update
            
        except Exception as e:
            logger.error(f"Failed to apply differential privacy: {str(e)}")
            return update
    
    def _validate_model_update(self, update: ModelUpdate) -> bool:
        """Validate model update"""
        try:
            # Check for reasonable accuracy
            if update.accuracy_score < 0.5 or update.accuracy_score > 1.0:
                return False
            
            # Check for reasonable loss
            if update.loss_score < 0 or update.loss_score > 2.0:
                return False
            
            # Check model weight ranges
            for weight in update.model_weights.values():
                if np.any(np.isnan(weight)) or np.any(np.isinf(weight)):
                    return False
                if np.abs(weight).max() > 10:  # Reasonable weight range
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Model update validation failed: {str(e)}")
            return False
    
    def _aggregate_model_updates(self, updates: List[ModelUpdate]) -> Dict[str, np.ndarray]:
        """Aggregate model updates using secure aggregation"""
        try:
            if self.secure_aggregator:
                return self._secure_aggregate_updates(updates)
            else:
                return self._weighted_average_aggregate(updates)
                
        except Exception as e:
            logger.error(f"Failed to aggregate updates: {str(e)}")
            raise
    
    def _secure_aggregate_updates(self, updates: List[ModelUpdate]) -> Dict[str, np.ndarray]:
        """Perform secure aggregation of model updates"""
        try:
            # Extract weight matrices
            weight_matrices = [update.model_weights for update in updates]
            
            # Perform secure aggregation
            aggregated_weights = self.secure_aggregator.aggregate(weight_matrices)
            
            return aggregated_weights
            
        except Exception as e:
            logger.error(f"Secure aggregation failed: {str(e)}")
            # Fallback to weighted average
            return self._weighted_average_aggregate(updates)
    
    def _weighted_average_aggregate(self, updates: List[ModelUpdate]) -> Dict[str, np.ndarray]:
        """Perform weighted average aggregation"""
        try:
            # Calculate weights based on data size and reputation
            total_weight = 0
            weights = []
            
            for update in updates:
                participant = self.participants[update.participant_id]
                weight = participant.data_size * (1 + participant.reputation_score)
                weights.append(weight)
                total_weight += weight
            
            # Normalize weights
            weights = [w / total_weight for w in weights]
            
            # Aggregate weights
            aggregated_weights = {}
            for key in updates[0].model_weights.keys():
                aggregated_weights[key] = np.zeros_like(updates[0].model_weights[key])
                
                for i, update in enumerate(updates):
                    aggregated_weights[key] += weights[i] * update.model_weights[key]
            
            return aggregated_weights
            
        except Exception as e:
            logger.error(f"Weighted average aggregation failed: {str(e)}")
            raise
    
    def _update_global_model(self, aggregated_weights: Dict[str, np.ndarray]):
        """Update global model with aggregated weights"""
        try:
            # Convert numpy arrays to torch tensors
            state_dict = {}
            for key, weight in aggregated_weights.items():
                state_dict[key] = torch.tensor(weight, dtype=torch.float32)
            
            # Load weights into global model
            self.global_model.load_state_dict(state_dict)
            
            # Save model state
            model_state = {
                'round': self.current_round,
                'weights': aggregated_weights,
                'timestamp': datetime.now(pytz.UTC).isoformat()
            }
            
            self._save_model_state(f'round_{self.current_round}', model_state)
            
        except Exception as e:
            logger.error(f"Failed to update global model: {str(e)}")
            raise
    
    def _validate_global_model(self) -> Tuple[float, float]:
        """Validate global model performance"""
        try:
            # Simulate validation (in practice, this would use validation dataset)
            # For now, return simulated metrics
            accuracy = 0.8 + np.random.normal(0, 0.05)  # Around 80% accuracy
            loss = 1.0 - accuracy + np.random.normal(0, 0.02)
            
            accuracy = max(0, min(1, accuracy))  # Clamp to [0, 1]
            loss = max(0, loss)
            
            return accuracy, loss
            
        except Exception as e:
            logger.error(f"Model validation failed: {str(e)}")
            return 0.0, 1.0
    
    def _check_convergence(self, accuracy: float, loss: float) -> bool:
        """Check if training has converged"""
        try:
            # Check accuracy threshold
            if accuracy >= self.config.model_accuracy_threshold:
                return True
            
            # Check loss improvement (if we have previous rounds)
            if len(self.training_rounds) >= 2:
                prev_loss = self.training_rounds[-2].global_loss
                loss_improvement = prev_loss - loss
                
                if loss_improvement < self.config.convergence_threshold:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Convergence check failed: {str(e)}")
            return False
    
    def _distribute_round_rewards(self, training_round: TrainingRound):
        """Distribute rewards to participants"""
        try:
            if not self.contract:
                logger.warning("Blockchain contract not available for reward distribution")
                return
            
            # Calculate rewards based on contribution
            total_reward_pool = len(training_round.participants) * self.config.participation_reward
            
            for update in training_round.model_updates:
                participant = self.participants[update.participant_id]
                
                # Base participation reward
                base_reward = self.config.participation_reward
                
                # Quality bonus based on accuracy
                quality_bonus = update.accuracy_score * self.config.validation_reward
                
                # Speed bonus for fast computation
                speed_bonus = max(0, (300 - update.computation_time) / 300) * 2.0
                
                total_reward = base_reward + quality_bonus + speed_bonus
                
                # Update participant rewards
                participant.total_rewards += total_reward
                
                # Update reputation
                reputation_boost = update.accuracy_score * 0.1
                participant.reputation_score += reputation_boost
                
                # Record reward
                self._save_reward(
                    training_round.round_id,
                    update.participant_id,
                    total_reward,
                    'participation'
                )
                
                # In practice, this would transfer tokens on blockchain
                logger.info(f"Reward distributed to {update.participant_id}: {total_reward:.2f} tokens")
            
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
    
    def _save_participant(self, participant: ParticipantInfo):
        """Save participant to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO participants 
            (participant_id, address, reputation_score, data_size, computation_power,
             join_time, last_active, contribution_count, total_rewards, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            participant.participant_id,
            participant.address,
            participant.reputation_score,
            participant.data_size,
            participant.computation_power,
            participant.join_time.isoformat(),
            participant.last_active.isoformat(),
            participant.contribution_count,
            participant.total_rewards,
            participant.status
        ))
        
        conn.commit()
        conn.close()
    
    def _save_training_round(self, training_round: TrainingRound):
        """Save training round to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO training_rounds 
            (round_id, round_number, participants, global_accuracy, global_loss,
             start_time, end_time, status, rewards_distributed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            training_round.round_id,
            training_round.round_number,
            json.dumps(training_round.participants),
            training_round.global_accuracy,
            training_round.global_loss,
            training_round.start_time.isoformat(),
            training_round.end_time.isoformat() if training_round.end_time else None,
            training_round.status.value,
            training_round.rewards_distributed
        ))
        
        conn.commit()
        conn.close()
    
    def _save_model_update(self, round_id: str, update: ModelUpdate):
        """Save model update to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        model_hash = self._calculate_model_hash(update.model_weights)
        
        cursor.execute('''
            INSERT INTO model_updates 
            (round_id, participant_id, model_hash, accuracy_score, loss_score,
             computation_time, timestamp, signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            round_id,
            update.participant_id,
            model_hash,
            update.accuracy_score,
            update.loss_score,
            update.computation_time,
            update.timestamp.isoformat(),
            update.signature
        ))
        
        conn.commit()
        conn.close()
    
    def _save_reward(self, round_id: str, participant_id: str, amount: float, reward_type: str):
        """Save reward record to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO rewards 
            (round_id, participant_id, reward_amount, reward_type, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            round_id,
            participant_id,
            amount,
            reward_type,
            datetime.now(pytz.UTC).isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _save_model_state(self, state_name: str, model_state: Dict[str, Any]):
        """Save model state to file"""
        try:
            state_file = f'/tmp/federated_model_{state_name}.json'
            
            # Convert numpy arrays to lists for JSON serialization
            serializable_state = {}
            for key, value in model_state.items():
                if key == 'weights':
                    serializable_state[key] = {
                        k: v.tolist() if isinstance(v, np.ndarray) else v
                        for k, v in value.items()
                    }
                else:
                    serializable_state[key] = value
            
            with open(state_file, 'w') as f:
                json.dump(serializable_state, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save model state: {str(e)}")
    
    def get_training_statistics(self) -> Dict[str, Any]:
        """Get federated training statistics"""
        try:
            stats = {
                'current_status': self.training_status.value,
                'current_round': self.current_round,
                'total_participants': len(self.participants),
                'completed_rounds': len(self.training_rounds),
                'global_accuracy': 0.0,
                'global_loss': 0.0,
                'total_rewards_distributed': 0.0,
                'participant_stats': {}
            }
            
            if self.training_rounds:
                latest_round = self.training_rounds[-1]
                stats['global_accuracy'] = latest_round.global_accuracy
                stats['global_loss'] = latest_round.global_loss
            
            # Participant statistics
            for pid, participant in self.participants.items():
                stats['participant_stats'][pid] = {
                    'reputation_score': participant.reputation_score,
                    'contribution_count': participant.contribution_count,
                    'total_rewards': participant.total_rewards,
                    'status': participant.status
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get training statistics: {str(e)}")
            return {}
    
    def get_participant_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get participant leaderboard"""
        try:
            participants = list(self.participants.values())
            
            # Sort by reputation score
            participants.sort(key=lambda p: p.reputation_score, reverse=True)
            
            leaderboard = []
            for i, participant in enumerate(participants[:limit]):
                leaderboard.append({
                    'rank': i + 1,
                    'participant_id': participant.participant_id,
                    'address': participant.address,
                    'reputation_score': participant.reputation_score,
                    'contribution_count': participant.contribution_count,
                    'total_rewards': participant.total_rewards
                })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Failed to get leaderboard: {str(e)}")
            return []

# Example usage
if __name__ == "__main__":
    # Example configuration
    config = FederatedConfig(
        min_participants=3,
        max_participants=20,
        rounds_per_training=5,
        enable_differential_privacy=True,
        enable_blockchain_validation=True,
        privacy_level=PrivacyLevel.STANDARD
    )
    
    # Create federated learning coordinator
    coordinator = FederatedLearningCoordinator(config)
    
    try:
        # Initialize model
        model_architecture = {
            'input_size': 1000,
            'hidden_size': 512,
            'output_size': 101
        }
        coordinator.initialize_global_model(model_architecture)
        
        # Register participants
        coordinator.register_participant("participant_1", "0x123...", 1000, 100)
        coordinator.register_participant("participant_2", "0x456...", 1500, 120)
        coordinator.register_participant("participant_3", "0x789...", 800, 80)
        
        # Start training
        training_id = coordinator.start_federated_training()
        print(f"Training started: {training_id}")
        
        # Get statistics
        stats = coordinator.get_training_statistics()
        print(f"Training statistics: {stats}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
