#!/usr/bin/env python3
"""
NFT Handlers for FlavorSnap ML Model API
Implements NFT minting, metadata management, marketplace integration, and IPFS integration
"""

import os
import json
import time
import logging
import hashlib
import requests
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pytz
from datetime import datetime, timedelta
import sqlite3
from web3 import Web3
from web3.contract import Contract
from web3.middleware import geth_poa_middleware
import ipfshttpclient
from PIL import Image
import io
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/nft_handlers.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NFTStatus(Enum):
    """NFT status states"""
    PENDING = "pending"
    MINTING = "minting"
    MINTED = "minted"
    LISTED = "listed"
    SOLD = "sold"
    ERROR = "error"

class NFTType(Enum):
    """NFT types"""
    FOOD_ITEM = "food_item"
    RECIPE = "recipe"
    ACHIEVEMENT = "achievement"
    CONTRIBUTOR_BADGE = "contributor_badge"

@dataclass
class NFTMetadata:
    """NFT metadata structure"""
    name: str
    description: str
    image: str  # IPFS hash or URL
    external_url: Optional[str] = None
    attributes: Optional[List[Dict[str, Any]]] = None
    background_color: Optional[str] = None
    animation_url: Optional[str] = None
    youtube_url: Optional[str] = None
    food_type: Optional[str] = None
    ingredients: Optional[List[str]] = None
    nutrition_info: Optional[Dict[str, Any]] = None
    recipe_steps: Optional[List[str]] = None
    contributor: Optional[str] = None
    creation_date: Optional[str] = None
    rarity: Optional[str] = None
    flavor_profile: Optional[List[str]] = None

@dataclass
class NFTConfig:
    """NFT system configuration"""
    blockchain_network: str = "polygon"  # polygon, ethereum, bsc
    rpc_url: str = "https://polygon-rpc.com"
    contract_address: Optional[str] = None
    private_key: Optional[str] = None
    ipfs_node_url: str = "/ip4/127.0.0.1/tcp/5001"
    ipfs_gateway_url: str = "https://ipfs.io/ipfs/"
    marketplace_api_url: str = "https://api.opensea.io/api/v1"
    royalty_percentage: float = 2.5
    gas_limit: int = 300000
    gas_price_gwei: float = 30.0
    enable_metadata_validation: bool = True
    enable_image_optimization: bool = True
    max_image_size_mb: int = 10

@dataclass
class NFTRecord:
    """NFT record in database"""
    token_id: Optional[int]
    nft_type: NFTType
    status: NFTStatus
    metadata_hash: str
    image_hash: str
    owner_address: Optional[str]
    transaction_hash: Optional[str]
    block_number: Optional[int]
    minted_at: Optional[datetime]
    listed_price: Optional[float]
    created_at: datetime
    updated_at: datetime

class NFTHandler:
    """Advanced NFT handler for FlavorSnap"""
    
    def __init__(self, config: NFTConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize blockchain connection
        self.w3 = None
        self.contract = None
        self._init_blockchain_connection()
        
        # Initialize IPFS client
        self.ipfs_client = None
        self._init_ipfs_connection()
        
        # Initialize database
        self.db_path = '/tmp/flavorsnap_nft.db'
        self._init_database()
        
        logger.info(f"NFTHandler initialized for network: {config.blockchain_network}")
    
    def _init_blockchain_connection(self):
        """Initialize blockchain connection"""
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
            
            # Add POA middleware for Polygon
            if self.config.blockchain_network == "polygon":
                self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Check connection
            if self.w3.is_connected():
                logger.info(f"Connected to {self.config.blockchain_network}")
                
                # Load contract if address provided
                if self.config.contract_address:
                    self._load_contract()
            else:
                logger.error("Failed to connect to blockchain")
                
        except Exception as e:
            logger.error(f"Blockchain connection failed: {str(e)}")
    
    def _load_contract(self):
        """Load NFT smart contract"""
        try:
            # Standard ERC-721 ABI (simplified)
            contract_abi = [
                {
                    "inputs": [{"internalType": "string", "name": "name_", "type": "string"},
                              {"internalType": "string", "name": "symbol_", "type": "string"}],
                    "stateMutability": "nonpayable", "type": "constructor"
                },
                {
                    "anonymous": False,
                    "inputs": [
                        {"indexed": True, "internalType": "address", "name": "owner", "type": "address"},
                        {"indexed": True, "internalType": "address", "name": "approved", "type": "address"},
                        {"indexed": True, "internalType": "uint256", "name": "tokenId", "type": "uint256"}
                    ],
                    "name": "Approval", "type": "event"
                },
                {
                    "anonymous": False,
                    "inputs": [
                        {"indexed": True, "internalType": "address", "name": "from", "type": "address"},
                        {"indexed": True, "internalType": "address", "name": "to", "type": "address"},
                        {"indexed": True, "internalType": "uint256", "name": "tokenId", "type": "uint256"}
                    ],
                    "name": "Transfer", "type": "event"
                },
                {
                    "inputs": [
                        {"internalType": "address", "name": "to", "type": "address"},
                        {"internalType": "uint256", "name": "tokenId", "type": "uint256"}
                    ],
                    "name": "mint", "outputs": [], "stateMutability": "nonpayable", "type": "function"
                },
                {
                    "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
                    "name": "tokenURI", "outputs": [{"internalType": "string", "name": "", "type": "string"}],
                    "stateMutability": "view", "type": "function"
                },
                {
                    "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
                    "name": "ownerOf", "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                    "stateMutability": "view", "type": "function"
                }
            ]
            
            self.contract = self.w3.eth.contract(
                address=self.config.contract_address,
                abi=contract_abi
            )
            
            logger.info(f"NFT contract loaded: {self.config.contract_address}")
            
        except Exception as e:
            logger.error(f"Failed to load contract: {str(e)}")
    
    def _init_ipfs_connection(self):
        """Initialize IPFS connection"""
        try:
            self.ipfs_client = ipfshttpclient.connect(self.config.ipfs_node_url)
            
            # Test connection
            self.ipfs_client.id()
            logger.info("Connected to IPFS node")
            
        except Exception as e:
            logger.error(f"IPFS connection failed: {str(e)}")
    
    def _init_database(self):
        """Initialize NFT database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nft_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_id INTEGER,
                nft_type TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata_hash TEXT NOT NULL,
                image_hash TEXT NOT NULL,
                owner_address TEXT,
                transaction_hash TEXT,
                block_number INTEGER,
                minted_at TEXT,
                listed_price REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nft_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nft_id INTEGER NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (nft_id) REFERENCES nft_records (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS royalty_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nft_id INTEGER NOT NULL,
                recipient_address TEXT NOT NULL,
                percentage REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (nft_id) REFERENCES nft_records (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("NFT database initialized")
    
    def upload_image_to_ipfs(self, image_data: bytes, filename: str = None) -> str:
        """Upload image to IPFS"""
        try:
            # Optimize image if enabled
            if self.config.enable_image_optimization:
                image_data = self._optimize_image(image_data)
            
            # Upload to IPFS
            result = self.ipfs_client.add_bytes(image_data)
            ipfs_hash = result['Hash']
            
            logger.info(f"Image uploaded to IPFS: {ipfs_hash}")
            return ipfs_hash
            
        except Exception as e:
            logger.error(f"Failed to upload image to IPFS: {str(e)}")
            raise
    
    def _optimize_image(self, image_data: bytes) -> bytes:
        """Optimize image for NFT"""
        try:
            # Open image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Resize if too large
            max_size = (1024, 1024)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save optimized image
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85, optimize=True)
            buffer.seek(0)
            
            optimized_data = buffer.getvalue()
            
            logger.info(f"Image optimized: {len(image_data)} -> {len(optimized_data)} bytes")
            return optimized_data
            
        except Exception as e:
            logger.warning(f"Image optimization failed: {str(e)}")
            return image_data
    
    def upload_metadata_to_ipfs(self, metadata: NFTMetadata) -> str:
        """Upload metadata to IPFS"""
        try:
            # Validate metadata
            if self.config.enable_metadata_validation:
                self._validate_metadata(metadata)
            
            # Convert to JSON
            metadata_json = json.dumps(asdict(metadata), indent=2)
            
            # Upload to IPFS
            result = self.ipfs_client.add_str(metadata_json)
            ipfs_hash = result['Hash']
            
            logger.info(f"Metadata uploaded to IPFS: {ipfs_hash}")
            return ipfs_hash
            
        except Exception as e:
            logger.error(f"Failed to upload metadata to IPFS: {str(e)}")
            raise
    
    def _validate_metadata(self, metadata: NFTMetadata):
        """Validate NFT metadata"""
        if not metadata.name or len(metadata.name) > 100:
            raise ValueError("Invalid name: must be 1-100 characters")
        
        if not metadata.description or len(metadata.description) > 1000:
            raise ValueError("Invalid description: must be 1-1000 characters")
        
        if not metadata.image:
            raise ValueError("Image hash is required")
        
        # Validate image hash format
        if not (metadata.image.startswith('Qm') and len(metadata.image) == 46):
            raise ValueError("Invalid IPFS image hash format")
    
    def mint_food_item_nft(self, metadata: NFTMetadata, image_data: bytes,
                          owner_address: str) -> Dict[str, Any]:
        """Mint food item NFT"""
        try:
            logger.info(f"Minting food item NFT: {metadata.name}")
            
            # Upload image to IPFS
            image_hash = self.upload_image_to_ipfs(image_data)
            metadata.image = f"{self.config.ipfs_gateway_url}{image_hash}"
            
            # Upload metadata to IPFS
            metadata_hash = self.upload_metadata_to_ipfs(metadata)
            
            # Create NFT record
            nft_record = NFTRecord(
                token_id=None,
                nft_type=NFTType.FOOD_ITEM,
                status=NFTStatus.PENDING,
                metadata_hash=metadata_hash,
                image_hash=image_hash,
                owner_address=owner_address,
                transaction_hash=None,
                block_number=None,
                minted_at=None,
                listed_price=None,
                created_at=datetime.now(pytz.UTC),
                updated_at=datetime.now(pytz.UTC)
            )
            
            # Save to database
            nft_id = self._save_nft_record(nft_record)
            
            # Mint on blockchain
            if self.contract and self.config.private_key:
                token_id = self._mint_on_blockchain(metadata_hash, owner_address)
                
                # Update record with token ID
                nft_record.token_id = token_id
                nft_record.status = NFTStatus.MINTED
                nft_record.minted_at = datetime.now(pytz.UTC)
                self._update_nft_record(nft_id, nft_record)
            
            # Set up royalties
            self._setup_royalties(nft_id, owner_address)
            
            logger.info(f"Food item NFT minted successfully: {metadata.name}")
            
            return {
                'nft_id': nft_id,
                'token_id': nft_record.token_id,
                'metadata_hash': metadata_hash,
                'image_hash': image_hash,
                'status': nft_record.status.value,
                'owner_address': owner_address,
                'ipfs_url': f"{self.config.ipfs_gateway_url}{metadata_hash}"
            }
            
        except Exception as e:
            logger.error(f"Failed to mint food item NFT: {str(e)}")
            raise
    
    def mint_recipe_nft(self, metadata: NFTMetadata, image_data: bytes,
                       owner_address: str) -> Dict[str, Any]:
        """Mint recipe NFT"""
        try:
            logger.info(f"Minting recipe NFT: {metadata.name}")
            
            # Validate recipe metadata
            if not metadata.ingredients or not metadata.recipe_steps:
                raise ValueError("Recipe NFT requires ingredients and recipe steps")
            
            # Upload image to IPFS
            image_hash = self.upload_image_to_ipfs(image_data)
            metadata.image = f"{self.config.ipfs_gateway_url}{image_hash}"
            
            # Upload metadata to IPFS
            metadata_hash = self.upload_metadata_to_ipfs(metadata)
            
            # Create NFT record
            nft_record = NFTRecord(
                token_id=None,
                nft_type=NFTType.RECIPE,
                status=NFTStatus.PENDING,
                metadata_hash=metadata_hash,
                image_hash=image_hash,
                owner_address=owner_address,
                transaction_hash=None,
                block_number=None,
                minted_at=None,
                listed_price=None,
                created_at=datetime.now(pytz.UTC),
                updated_at=datetime.now(pytz.UTC)
            )
            
            # Save to database
            nft_id = self._save_nft_record(nft_record)
            
            # Mint on blockchain
            if self.contract and self.config.private_key:
                token_id = self._mint_on_blockchain(metadata_hash, owner_address)
                
                # Update record
                nft_record.token_id = token_id
                nft_record.status = NFTStatus.MINTED
                nft_record.minted_at = datetime.now(pytz.UTC)
                self._update_nft_record(nft_id, nft_record)
            
            # Set up royalties
            self._setup_royalties(nft_id, owner_address)
            
            logger.info(f"Recipe NFT minted successfully: {metadata.name}")
            
            return {
                'nft_id': nft_id,
                'token_id': nft_record.token_id,
                'metadata_hash': metadata_hash,
                'image_hash': image_hash,
                'status': nft_record.status.value,
                'owner_address': owner_address,
                'ipfs_url': f"{self.config.ipfs_gateway_url}{metadata_hash}"
            }
            
        except Exception as e:
            logger.error(f"Failed to mint recipe NFT: {str(e)}")
            raise
    
    def mint_achievement_nft(self, metadata: NFTMetadata, image_data: bytes,
                          owner_address: str, achievement_type: str) -> Dict[str, Any]:
        """Mint achievement NFT"""
        try:
            logger.info(f"Minting achievement NFT: {metadata.name}")
            
            # Add achievement type to metadata
            if not metadata.attributes:
                metadata.attributes = []
            metadata.attributes.append({
                "trait_type": "Achievement Type",
                "value": achievement_type
            })
            
            # Upload image to IPFS
            image_hash = self.upload_image_to_ipfs(image_data)
            metadata.image = f"{self.config.ipfs_gateway_url}{image_hash}"
            
            # Upload metadata to IPFS
            metadata_hash = self.upload_metadata_to_ipfs(metadata)
            
            # Create NFT record
            nft_record = NFTRecord(
                token_id=None,
                nft_type=NFTType.ACHIEVEMENT,
                status=NFTStatus.PENDING,
                metadata_hash=metadata_hash,
                image_hash=image_hash,
                owner_address=owner_address,
                transaction_hash=None,
                block_number=None,
                minted_at=None,
                listed_price=None,
                created_at=datetime.now(pytz.UTC),
                updated_at=datetime.now(pytz.UTC)
            )
            
            # Save to database
            nft_id = self._save_nft_record(nft_record)
            
            # Mint on blockchain
            if self.contract and self.config.private_key:
                token_id = self._mint_on_blockchain(metadata_hash, owner_address)
                
                # Update record
                nft_record.token_id = token_id
                nft_record.status = NFTStatus.MINTED
                nft_record.minted_at = datetime.now(pytz.UTC)
                self._update_nft_record(nft_id, nft_record)
            
            logger.info(f"Achievement NFT minted successfully: {metadata.name}")
            
            return {
                'nft_id': nft_id,
                'token_id': nft_record.token_id,
                'metadata_hash': metadata_hash,
                'image_hash': image_hash,
                'status': nft_record.status.value,
                'owner_address': owner_address,
                'ipfs_url': f"{self.config.ipfs_gateway_url}{metadata_hash}"
            }
            
        except Exception as e:
            logger.error(f"Failed to mint achievement NFT: {str(e)}")
            raise
    
    def _mint_on_blockchain(self, metadata_hash: str, owner_address: str) -> int:
        """Mint NFT on blockchain"""
        try:
            if not self.contract or not self.config.private_key:
                raise ValueError("Contract or private key not configured")
            
            # Get nonce
            account = self.w3.eth.account.from_key(self.config.private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)
            
            # Build transaction
            transaction = self.contract.functions.mint(
                owner_address,
                int(hashlib.sha256(metadata_hash.encode()).hexdigest(), 16)
            ).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': self.config.gas_limit,
                'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
            })
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.config.private_key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if tx_receipt.status == 1:
                # Get token ID from Transfer event
                transfer_event = self.contract.events.Transfer().process_receipt(tx_receipt)[0]
                token_id = transfer_event.args.tokenId
                
                logger.info(f"NFT minted on blockchain: token_id={token_id}, tx_hash={tx_hash.hex()}")
                return token_id
            else:
                raise Exception("Transaction failed")
                
        except Exception as e:
            logger.error(f"Blockchain minting failed: {str(e)}")
            raise
    
    def _save_nft_record(self, nft_record: NFTRecord) -> int:
        """Save NFT record to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO nft_records 
            (token_id, nft_type, status, metadata_hash, image_hash, owner_address,
             transaction_hash, block_number, minted_at, listed_price, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            nft_record.token_id,
            nft_record.nft_type.value,
            nft_record.status.value,
            nft_record.metadata_hash,
            nft_record.image_hash,
            nft_record.owner_address,
            nft_record.transaction_hash,
            nft_record.block_number,
            nft_record.minted_at.isoformat() if nft_record.minted_at else None,
            nft_record.listed_price,
            nft_record.created_at.isoformat(),
            nft_record.updated_at.isoformat()
        ))
        
        nft_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return nft_id
    
    def _update_nft_record(self, nft_id: int, nft_record: NFTRecord):
        """Update NFT record in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE nft_records SET
            token_id = ?, status = ?, owner_address = ?, transaction_hash = ?,
            block_number = ?, minted_at = ?, listed_price = ?, updated_at = ?
            WHERE id = ?
        ''', (
            nft_record.token_id,
            nft_record.status.value,
            nft_record.owner_address,
            nft_record.transaction_hash,
            nft_record.block_number,
            nft_record.minted_at.isoformat() if nft_record.minted_at else None,
            nft_record.listed_price,
            datetime.now(pytz.UTC).isoformat(),
            nft_id
        ))
        
        conn.commit()
        conn.close()
    
    def _setup_royalties(self, nft_id: int, creator_address: str):
        """Set up royalty distribution"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO royalty_records 
                (nft_id, recipient_address, percentage, created_at)
                VALUES (?, ?, ?, ?)
            ''', (
                nft_id,
                creator_address,
                self.config.royalty_percentage,
                datetime.now(pytz.UTC).isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Royalties set up for NFT {nft_id}: {self.config.royalty_percentage}% to {creator_address}")
            
        except Exception as e:
            logger.error(f"Failed to set up royalties: {str(e)}")
    
    def list_nft_on_marketplace(self, nft_id: int, price: float, marketplace: str = "opensea") -> Dict[str, Any]:
        """List NFT on marketplace"""
        try:
            # Get NFT record
            nft_record = self._get_nft_record(nft_id)
            if not nft_record:
                raise ValueError(f"NFT {nft_id} not found")
            
            if nft_record.status != NFTStatus.MINTED:
                raise ValueError("NFT must be minted before listing")
            
            # List on marketplace (simplified implementation)
            listing_data = {
                'token_id': nft_record.token_id,
                'contract_address': self.config.contract_address,
                'price': price,
                'currency': 'ETH',
                'marketplace': marketplace
            }
            
            # In a real implementation, this would call the marketplace API
            # For now, we'll simulate the listing
            listing_id = f"list_{int(time.time())}_{nft_id}"
            
            # Update NFT record
            nft_record.status = NFTStatus.LISTED
            nft_record.listed_price = price
            nft_record.updated_at = datetime.now(pytz.UTC)
            self._update_nft_record(nft_id, nft_record)
            
            logger.info(f"NFT {nft_id} listed on {marketplace} for {price} ETH")
            
            return {
                'listing_id': listing_id,
                'nft_id': nft_id,
                'token_id': nft_record.token_id,
                'price': price,
                'marketplace': marketplace,
                'status': 'listed'
            }
            
        except Exception as e:
            logger.error(f"Failed to list NFT on marketplace: {str(e)}")
            raise
    
    def get_nft_metadata(self, nft_id: int) -> Optional[Dict[str, Any]]:
        """Get NFT metadata"""
        try:
            nft_record = self._get_nft_record(nft_id)
            if not nft_record:
                return None
            
            # Get metadata from IPFS
            metadata_url = f"{self.config.ipfs_gateway_url}{nft_record.metadata_hash}"
            response = requests.get(metadata_url, timeout=10)
            
            if response.status_code == 200:
                metadata = response.json()
                return {
                    'nft_record': asdict(nft_record),
                    'metadata': metadata
                }
            else:
                logger.error(f"Failed to fetch metadata from IPFS: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get NFT metadata: {str(e)}")
            return None
    
    def _get_nft_record(self, nft_id: int) -> Optional[NFTRecord]:
        """Get NFT record from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM nft_records WHERE id = ?', (nft_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return NFTRecord(
                token_id=row[1],
                nft_type=NFTType(row[2]),
                status=NFTStatus(row[3]),
                metadata_hash=row[4],
                image_hash=row[5],
                owner_address=row[6],
                transaction_hash=row[7],
                block_number=row[8],
                minted_at=datetime.fromisoformat(row[9]) if row[9] else None,
                listed_price=row[10],
                created_at=datetime.fromisoformat(row[11]),
                updated_at=datetime.fromisoformat(row[12])
            )
        
        return None
    
    def get_nfts_by_owner(self, owner_address: str) -> List[Dict[str, Any]]:
        """Get all NFTs owned by an address"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM nft_records 
                WHERE owner_address = ? AND status = ?
                ORDER BY created_at DESC
            ''', (owner_address, NFTStatus.MINTED.value))
            
            rows = cursor.fetchall()
            conn.close()
            
            nfts = []
            for row in rows:
                nft_record = NFTRecord(
                    token_id=row[1],
                    nft_type=NFTType(row[2]),
                    status=NFTStatus(row[3]),
                    metadata_hash=row[4],
                    image_hash=row[5],
                    owner_address=row[6],
                    transaction_hash=row[7],
                    block_number=row[8],
                    minted_at=datetime.fromisoformat(row[9]) if row[9] else None,
                    listed_price=row[10],
                    created_at=datetime.fromisoformat(row[11]),
                    updated_at=datetime.fromisoformat(row[12])
                )
                
                # Get metadata
                metadata_url = f"{self.config.ipfs_gateway_url}{nft_record.metadata_hash}"
                try:
                    response = requests.get(metadata_url, timeout=5)
                    if response.status_code == 200:
                        metadata = response.json()
                    else:
                        metadata = {}
                except:
                    metadata = {}
                
                nfts.append({
                    'nft_record': asdict(nft_record),
                    'metadata': metadata
                })
            
            return nfts
            
        except Exception as e:
            logger.error(f"Failed to get NFTs by owner: {str(e)}")
            return []
    
    def get_nfts_by_type(self, nft_type: NFTType) -> List[Dict[str, Any]]:
        """Get all NFTs of a specific type"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM nft_records 
                WHERE nft_type = ? AND status = ?
                ORDER BY created_at DESC
            ''', (nft_type.value, NFTStatus.MINTED.value))
            
            rows = cursor.fetchall()
            conn.close()
            
            nfts = []
            for row in rows:
                nft_record = NFTRecord(
                    token_id=row[1],
                    nft_type=NFTType(row[2]),
                    status=NFTStatus(row[3]),
                    metadata_hash=row[4],
                    image_hash=row[5],
                    owner_address=row[6],
                    transaction_hash=row[7],
                    block_number=row[8],
                    minted_at=datetime.fromisoformat(row[9]) if row[9] else None,
                    listed_price=row[10],
                    created_at=datetime.fromisoformat(row[11]),
                    updated_at=datetime.fromisoformat(row[12])
                )
                
                nfts.append(asdict(nft_record))
            
            return nfts
            
        except Exception as e:
            logger.error(f"Failed to get NFTs by type: {str(e)}")
            return []
    
    def transfer_nft(self, nft_id: int, from_address: str, to_address: str) -> Dict[str, Any]:
        """Transfer NFT to new owner"""
        try:
            nft_record = self._get_nft_record(nft_id)
            if not nft_record:
                raise ValueError(f"NFT {nft_id} not found")
            
            if nft_record.owner_address != from_address:
                raise ValueError("Not the owner of this NFT")
            
            # Transfer on blockchain
            if self.contract and self.config.private_key:
                self._transfer_on_blockchain(nft_record.token_id, from_address, to_address)
            
            # Update record
            nft_record.owner_address = to_address
            nft_record.updated_at = datetime.now(pytz.UTC)
            self._update_nft_record(nft_id, nft_record)
            
            logger.info(f"NFT {nft_id} transferred from {from_address} to {to_address}")
            
            return {
                'nft_id': nft_id,
                'token_id': nft_record.token_id,
                'from_address': from_address,
                'to_address': to_address,
                'status': 'transferred'
            }
            
        except Exception as e:
            logger.error(f"Failed to transfer NFT: {str(e)}")
            raise
    
    def _transfer_on_blockchain(self, token_id: int, from_address: str, to_address: str):
        """Transfer NFT on blockchain"""
        try:
            if not self.contract or not self.config.private_key:
                raise ValueError("Contract or private key not configured")
            
            # Get nonce
            account = self.w3.eth.account.from_key(self.config.private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)
            
            # Build transaction
            transaction = self.contract.functions.transferFrom(
                from_address,
                to_address,
                token_id
            ).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': self.config.gas_limit,
                'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
            })
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.config.private_key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            if tx_receipt.status == 1:
                logger.info(f"NFT transferred on blockchain: token_id={token_id}, tx_hash={tx_hash.hex()}")
            else:
                raise Exception("Transfer transaction failed")
                
        except Exception as e:
            logger.error(f"Blockchain transfer failed: {str(e)}")
            raise
    
    def get_nft_statistics(self) -> Dict[str, Any]:
        """Get NFT statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total NFTs by type
            cursor.execute('''
                SELECT nft_type, COUNT(*) as count
                FROM nft_records
                WHERE status = ?
                GROUP BY nft_type
            ''', (NFTStatus.MINTED.value,))
            
            type_stats = dict(cursor.fetchall())
            
            # Total NFTs by status
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM nft_records
                GROUP BY status
            ''')
            
            status_stats = dict(cursor.fetchall())
            
            # Total listed NFTs
            cursor.execute('''
                SELECT COUNT(*) FROM nft_records
                WHERE status = ? AND listed_price IS NOT NULL
            ''', (NFTStatus.LISTED.value,))
            
            listed_count = cursor.fetchone()[0]
            
            # Total value of listed NFTs
            cursor.execute('''
                SELECT SUM(listed_price) FROM nft_records
                WHERE status = ? AND listed_price IS NOT NULL
            ''', (NFTStatus.LISTED.value,))
            
            total_value = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_by_type': type_stats,
                'total_by_status': status_stats,
                'listed_count': listed_count,
                'total_listed_value_eth': total_value,
                'royalty_percentage': self.config.royalty_percentage,
                'blockchain_network': self.config.blockchain_network
            }
            
        except Exception as e:
            logger.error(f"Failed to get NFT statistics: {str(e)}")
            return {}

# Example usage
if __name__ == "__main__":
    # Example configuration
    config = NFTConfig(
        blockchain_network="polygon",
        rpc_url="https://polygon-rpc.com",
        ipfs_node_url="/ip4/127.0.0.1/tcp/5001",
        royalty_percentage=2.5
    )
    
    # Create NFT handler
    handler = NFTHandler(config)
    
    try:
        # Example metadata
        metadata = NFTMetadata(
            name="Delicious Pizza",
            description="A classic Italian pizza with fresh ingredients",
            food_type="pizza",
            ingredients=["flour", "tomato", "cheese", "basil"],
            flavor_profile=["savory", "herbal", "creamy"],
            rarity="common"
        )
        
        # Example image (in real usage, this would be actual image data)
        image_data = b"fake_image_data_for_testing"
        
        # Mint NFT
        result = handler.mint_food_item_nft(
            metadata, 
            image_data, 
            "0x1234567890123456789012345678901234567890"
        )
        
        print(f"NFT minted: {result}")
        
        # Get statistics
        stats = handler.get_nft_statistics()
        print(f"NFT statistics: {stats}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
