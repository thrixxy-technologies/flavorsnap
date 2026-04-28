"""
IPFS Integration for FlavorSnap Decentralized Storage
Implements IPFS file storage, content addressing, and verification
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
import aiohttp
import aiofiles
import ipfshttpclient
from web3 import Web3
from web3.contract import Contract
import cryptography.hazmat.primitives.hashes as hashes
import cryptography.hazmat.primitives.asymmetric as rsa
import cryptography.hazmat.primitives.serialization as serialization
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


@dataclass
class IPFSFile:
    """IPFS file metadata"""
    cid: str
    name: str
    size: int
    content_hash: str
    timestamp: datetime
    owner: str
    permissions: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    replicas: List[str] = field(default_factory=list)
    verification_status: str = "pending"  # pending, verified, failed
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    cost_estimate: float = 0.0


@dataclass
class StorageMetrics:
    """Storage performance metrics"""
    upload_speed_mbps: float
    download_speed_mbps: float
    latency_ms: float
    success_rate: float
    total_operations: int
    failed_operations: int
    average_file_size: float
    storage_efficiency: float


class IPFSManager:
    """Advanced IPFS storage manager"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ipfs_client = None
        self.web3 = None
        self.storage_contract = None
        
        # Performance tracking
        self.metrics = StorageMetrics(
            upload_speed_mbps=0.0,
            download_speed_mbps=0.0,
            latency_ms=0.0,
            success_rate=0.0,
            total_operations=0,
            failed_operations=0,
            average_file_size=0.0,
            storage_efficiency=0.0
        )
        
        # File registry
        self.file_registry = {}
        self.access_logs = []
        
        # Initialize connections
        self._initialize_ipfs()
        self._initialize_blockchain()
        
        # Background tasks
        self.replication_task = None
        self.cleanup_task = None
        self.stop_event = asyncio.Event()
        
        # Start background tasks
        asyncio.create_task(self._start_background_tasks())
    
    def _initialize_ipfs(self):
        """Initialize IPFS client"""
        try:
            ipfs_config = self.config.get('ipfs', {})
            host = ipfs_config.get('host', 'localhost')
            port = ipfs_config.get('port', 5001)
            
            self.ipfs_client = ipfshttpclient.connect(f'/ip4/{host}/tcp/{port}')
            
            # Test connection
            self.ipfs_client.id()
            logger.info("Connected to IPFS node")
            
        except Exception as e:
            logger.error(f"Failed to connect to IPFS: {e}")
            raise
    
    def _initialize_blockchain(self):
        """Initialize blockchain connection for storage contracts"""
        try:
            blockchain_config = self.config.get('blockchain', {})
            
            if blockchain_config.get('enabled', False):
                # Connect to Ethereum node
                web3_url = blockchain_config.get('web3_url', 'http://localhost:8545')
                self.web3 = Web3(Web3.HTTPProvider(web3_url))
                
                if self.web3.is_connected():
                    # Load storage contract
                    contract_address = blockchain_config.get('storage_contract_address')
                    contract_abi = self._load_storage_contract_abi()
                    
                    if contract_address and contract_abi:
                        self.storage_contract = self.web3.eth.contract(
                            address=contract_address,
                            abi=contract_abi
                        )
                        logger.info("Connected to blockchain storage contract")
                
        except Exception as e:
            logger.warning(f"Failed to initialize blockchain connection: {e}")
    
    def _load_storage_contract_abi(self) -> Optional[List[Dict]]:
        """Load storage contract ABI"""
        # Simplified ABI for storage contract
        return [
            {
                "inputs": [{"name": "cid", "type": "string"}, {"name": "hash", "type": "string"}],
                "name": "registerFile",
                "outputs": [],
                "type": "function"
            },
            {
                "inputs": [{"name": "cid", "type": "string"}],
                "name": "verifyFile",
                "outputs": [{"name": "valid", "type": "bool"}],
                "type": "function"
            },
            {
                "inputs": [{"name": "cid", "type": "string"}],
                "name": "getFileMetadata",
                "outputs": [{"name": "metadata", "type": "string"}],
                "type": "function"
            }
        ]
    
    async def upload_file(self, file_path: Union[str, Path], 
                         owner: str = None, metadata: Dict[str, Any] = None,
                         replicate: bool = True) -> IPFSFile:
        """Upload file to IPFS with verification and replication"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        start_time = time.time()
        
        try:
            # Calculate file hash
            content_hash = await self._calculate_file_hash(file_path)
            
            # Upload to IPFS
            cid = await self._upload_to_ipfs(file_path)
            
            # Create file metadata
            ipfs_file = IPFSFile(
                cid=cid,
                name=file_path.name,
                size=file_path.stat().st_size,
                content_hash=content_hash,
                timestamp=datetime.now(),
                owner=owner or "anonymous",
                metadata=metadata or {},
                cost_estimate=await self._estimate_storage_cost(file_path.stat().st_size)
            )
            
            # Verify upload
            if await self._verify_ipfs_file(cid, content_hash):
                ipfs_file.verification_status = "verified"
                
                # Replicate to other nodes if requested
                if replicate:
                    await self._replicate_file(cid)
                
                # Register on blockchain if available
                if self.storage_contract:
                    await self._register_on_blockchain(ipfs_file)
                
                # Update metrics
                upload_time = time.time() - start_time
                self._update_upload_metrics(file_path.stat().st_size, upload_time, True)
                
                # Add to registry
                self.file_registry[cid] = ipfs_file
                
                logger.info(f"Successfully uploaded {file_path.name} to IPFS with CID: {cid}")
                return ipfs_file
            else:
                ipfs_file.verification_status = "failed"
                self._update_upload_metrics(file_path.stat().st_size, upload_time, False)
                raise ValueError("File verification failed")
                
        except Exception as e:
            self._update_upload_metrics(file_path.stat().st_size if file_path.exists() else 0, time.time() - start_time, False)
            logger.error(f"Failed to upload file {file_path}: {e}")
            raise
    
    async def download_file(self, cid: str, output_path: Union[str, Path] = None,
                           verify: bool = True) -> bytes:
        """Download file from IPFS with verification"""
        start_time = time.time()
        
        try:
            # Get file metadata
            file_metadata = self.file_registry.get(cid)
            if not file_metadata:
                # Try to fetch from blockchain
                file_metadata = await self._get_file_metadata_from_blockchain(cid)
            
            # Download from IPFS
            file_content = await self._download_from_ipfs(cid)
            
            # Verify content if requested and metadata available
            if verify and file_metadata:
                downloaded_hash = hashlib.sha256(file_content).hexdigest()
                if downloaded_hash != file_metadata.content_hash:
                    raise ValueError("Content verification failed - hash mismatch")
            
            # Save to file if output path provided
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                async with aiofiles.open(output_path, 'wb') as f:
                    await f.write(file_content)
            
            # Update access metrics
            if file_metadata:
                file_metadata.access_count += 1
                file_metadata.last_accessed = datetime.now()
            
            # Update download metrics
            download_time = time.time() - start_time
            file_size = len(file_content)
            self._update_download_metrics(file_size, download_time, True)
            
            logger.info(f"Successfully downloaded file with CID: {cid}")
            return file_content
            
        except Exception as e:
            self._update_download_metrics(0, time.time() - start_time, False)
            logger.error(f"Failed to download file with CID {cid}: {e}")
            raise
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    async def _upload_to_ipfs(self, file_path: Path) -> str:
        """Upload file to IPFS"""
        loop = asyncio.get_event_loop()
        
        def sync_upload():
            with open(file_path, 'rb') as f:
                result = self.ipfs_client.add(f)
                return result['Hash']
        
        return await loop.run_in_executor(None, sync_upload)
    
    async def _download_from_ipfs(self, cid: str) -> bytes:
        """Download file from IPFS"""
        loop = asyncio.get_event_loop()
        
        def sync_download():
            return self.ipfs_client.cat(cid)
        
        return await loop.run_in_executor(None, sync_download)
    
    async def _verify_ipfs_file(self, cid: str, expected_hash: str) -> bool:
        """Verify IPFS file content"""
        try:
            # Download a small portion for verification
            content = await self._download_from_ipfs(cid)
            actual_hash = hashlib.sha256(content).hexdigest()
            return actual_hash == expected_hash
        except Exception as e:
            logger.error(f"Verification failed for CID {cid}: {e}")
            return False
    
    async def _replicate_file(self, cid: str, target_replicas: int = 3) -> List[str]:
        """Replicate file to multiple IPFS nodes"""
        replicas = []
        
        try:
            # Get current replication info
            repo_stat = self.ipfs_client.repo.stat()
            
            # Pin the file to ensure it's kept locally
            self.ipfs_client.pin.add(cid)
            
            # Find and connect to other peers for replication
            peers = self.ipfs_client.swarm.peers()['Peers']
            
            for peer in peers[:target_replicas - 1]:
                try:
                    # Connect to peer
                    self.ipfs_client.swarm.connect(peer['Addr'])
                    
                    # Request file from peer (this would trigger replication)
                    self.ipfs_client.cat(cid, timeout=30)
                    
                    replicas.append(peer['Addr'])
                    
                except Exception as e:
                    logger.warning(f"Failed to replicate to peer {peer['Addr']}: {e}")
            
            logger.info(f"Replicated file {cid} to {len(replicas)} peers")
            return replicas
            
        except Exception as e:
            logger.error(f"Replication failed for CID {cid}: {e}")
            return replicas
    
    async def _register_on_blockchain(self, ipfs_file: IPFSFile):
        """Register file on blockchain for verification"""
        try:
            if not self.storage_contract or not self.web3:
                return
            
            # Prepare transaction
            transaction = self.storage_contract.functions.registerFile(
                ipfs_file.cid,
                ipfs_file.content_hash
            ).build_transaction({
                'from': self.web3.eth.accounts[0] if self.web3.eth.accounts else self.web3.eth.default_account,
                'gas': 200000
            })
            
            # Sign and send transaction (simplified - in production would use proper signing)
            tx_hash = self.web3.eth.send_transaction(transaction)
            
            # Wait for confirmation
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            logger.info(f"Registered file {ipfs_file.cid} on blockchain: {tx_hash.hex()}")
            
        except Exception as e:
            logger.error(f"Failed to register file on blockchain: {e}")
    
    async def _get_file_metadata_from_blockchain(self, cid: str) -> Optional[IPFSFile]:
        """Get file metadata from blockchain"""
        try:
            if not self.storage_contract or not self.web3:
                return None
            
            # Call contract
            metadata_json = self.storage_contract.functions.getFileMetadata(cid).call()
            
            if metadata_json:
                metadata = json.loads(metadata_json)
                return IPFSFile(**metadata)
            
        except Exception as e:
            logger.error(f"Failed to get metadata from blockchain: {e}")
        
        return None
    
    async def verify_file_integrity(self, cid: str) -> bool:
        """Verify file integrity using blockchain records"""
        try:
            if self.storage_contract:
                # Verify on blockchain
                is_valid = self.storage_contract.functions.verifyFile(cid).call()
                return is_valid
            else:
                # Local verification
                file_metadata = self.file_registry.get(cid)
                if file_metadata:
                    return await self._verify_ipfs_file(cid, file_metadata.content_hash)
                return False
                
        except Exception as e:
            logger.error(f"Failed to verify file integrity for {cid}: {e}")
            return False
    
    async def _estimate_storage_cost(self, file_size: int) -> float:
        """Estimate storage cost based on file size and duration"""
        # Simplified cost calculation (in USD)
        cost_per_mb_per_month = 0.01  # $0.01 per MB per month
        cost_per_gb_transfer = 0.05   # $0.05 per GB transfer
        
        size_mb = file_size / (1024 * 1024)
        storage_cost = size_mb * cost_per_mb_per_month
        transfer_cost = size_mb / 1024 * cost_per_gb_transfer
        
        return storage_cost + transfer_cost
    
    def _update_upload_metrics(self, file_size: int, duration: float, success: bool):
        """Update upload performance metrics"""
        self.metrics.total_operations += 1
        if not success:
            self.metrics.failed_operations += 1
        
        if success and duration > 0:
            # Calculate speed in Mbps
            speed_mbps = (file_size * 8) / (duration * 1024 * 1024)
            
            # Update rolling average
            alpha = 0.1  # Smoothing factor
            self.metrics.upload_speed_mbps = (
                alpha * speed_mbps + 
                (1 - alpha) * self.metrics.upload_speed_mbps
            )
        
        # Update average file size
        if self.metrics.total_operations > 0:
            self.metrics.average_file_size = (
                (self.metrics.average_file_size * (self.metrics.total_operations - 1) + file_size) /
                self.metrics.total_operations
            )
        
        # Update success rate
        self.metrics.success_rate = (
            (self.metrics.total_operations - self.metrics.failed_operations) /
            self.metrics.total_operations
        )
    
    def _update_download_metrics(self, file_size: int, duration: float, success: bool):
        """Update download performance metrics"""
        self.metrics.total_operations += 1
        if not success:
            self.metrics.failed_operations += 1
        
        if success and duration > 0:
            # Calculate speed in Mbps
            speed_mbps = (file_size * 8) / (duration * 1024 * 1024)
            
            # Update rolling average
            alpha = 0.1  # Smoothing factor
            self.metrics.download_speed_mbps = (
                alpha * speed_mbps + 
                (1 - alpha) * self.metrics.download_speed_mbps
            )
            
            # Update latency (inverse of speed for small files)
            if file_size < 1024 * 1024:  # Files smaller than 1MB
                latency_ms = duration * 1000
                self.metrics.latency_ms = (
                    alpha * latency_ms + 
                    (1 - alpha) * self.metrics.latency_ms
                )
        
        # Update success rate
        self.metrics.success_rate = (
            (self.metrics.total_operations - self.metrics.failed_operations) /
            self.metrics.total_operations
        )
    
    async def _start_background_tasks(self):
        """Start background maintenance tasks"""
        self.replication_task = asyncio.create_task(self._replication_maintenance())
        self.cleanup_task = asyncio.create_task(self._cleanup_maintenance())
    
    async def _replication_maintenance(self):
        """Background task to maintain file replication"""
        while not self.stop_event.is_set():
            try:
                # Check replication levels for all files
                for cid, ipfs_file in self.file_registry.items():
                    if len(ipfs_file.replicas) < 3:  # Target replication level
                        await self._replicate_file(cid)
                
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error(f"Error in replication maintenance: {e}")
                await asyncio.sleep(300)  # Retry after 5 minutes
    
    async def _cleanup_maintenance(self):
        """Background task to cleanup old files and optimize storage"""
        while not self.stop_event.is_set():
            try:
                # Remove old unpinned files
                cutoff_time = datetime.now() - timedelta(days=30)
                
                for cid, ipfs_file in list(self.file_registry.items()):
                    if (ipfs_file.last_accessed and 
                        ipfs_file.last_accessed < cutoff_time and 
                        ipfs_file.access_count == 0):
                        
                        # Unpin and remove from registry
                        try:
                            self.ipfs_client.pin.rm(cid)
                            del self.file_registry[cid]
                            logger.info(f"Cleaned up old file: {cid}")
                        except Exception as e:
                            logger.warning(f"Failed to cleanup file {cid}: {e}")
                
                await asyncio.sleep(86400)  # Check daily
                
            except Exception as e:
                logger.error(f"Error in cleanup maintenance: {e}")
                await asyncio.sleep(3600)  # Retry after 1 hour
    
    async def get_storage_metrics(self) -> StorageMetrics:
        """Get current storage performance metrics"""
        return self.metrics
    
    async def get_file_info(self, cid: str) -> Optional[IPFSFile]:
        """Get file information"""
        return self.file_registry.get(cid)
    
    async def list_files(self, owner: str = None, limit: int = 100) -> List[IPFSFile]:
        """List files with optional owner filter"""
        files = list(self.file_registry.values())
        
        if owner:
            files = [f for f in files if f.owner == owner]
        
        # Sort by timestamp (newest first)
        files.sort(key=lambda f: f.timestamp, reverse=True)
        
        return files[:limit]
    
    async def delete_file(self, cid: str) -> bool:
        """Delete file from IPFS (unpin)"""
        try:
            # Unpin from IPFS
            self.ipfs_client.pin.rm(cid)
            
            # Remove from registry
            if cid in self.file_registry:
                del self.file_registry[cid]
            
            logger.info(f"Deleted file with CID: {cid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file {cid}: {e}")
            return False
    
    async def optimize_storage(self) -> Dict[str, Any]:
        """Optimize storage performance and cost"""
        optimization_results = {
            'files_optimized': 0,
            'space_saved': 0,
            'cost_reduction': 0.0,
            'recommendations': []
        }
        
        try:
            # Analyze storage patterns
            total_files = len(self.file_registry)
            total_size = sum(f.size for f in self.file_registry.values())
            
            # Identify rarely accessed files
            rarely_accessed = [
                f for f in self.file_registry.values()
                if f.access_count == 0 and 
                (datetime.now() - f.timestamp).days > 30
            ]
            
            if rarely_accessed:
                optimization_results['recommendations'].append(
                    f"Consider archiving {len(rarely_accessed)} rarely accessed files"
                )
                optimization_results['files_optimized'] = len(rarely_accessed)
                optimization_results['space_saved'] = sum(f.size for f in rarely_accessed)
            
            # Check replication efficiency
            over_replicated = [
                f for f in self.file_registry.values()
                if len(f.replicas) > 3
            ]
            
            if over_replicated:
                optimization_results['recommendations'].append(
                    f"Reduce replication for {len(over_replicated)} over-replicated files"
                )
            
            # Calculate cost optimization potential
            if total_size > 0:
                current_cost = sum(f.cost_estimate for f in self.file_registry.values())
                potential_savings = optimization_results['space_saved'] / total_size * current_cost
                optimization_results['cost_reduction'] = potential_savings
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"Storage optimization failed: {e}")
            return optimization_results
    
    def stop(self):
        """Stop background tasks"""
        self.stop_event.set()
        
        if self.replication_task:
            self.replication_task.cancel()
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        logger.info("IPFS manager stopped")


class ContentAddressedStorage:
    """Content-addressed storage with verification"""
    
    def __init__(self, ipfs_manager: IPFSManager):
        self.ipfs_manager = ipfs_manager
        self.content_registry = {}
    
    async def store_content(self, content: bytes, content_type: str = "application/octet-stream",
                           owner: str = None, metadata: Dict[str, Any] = None) -> str:
        """Store content with content addressing"""
        # Calculate content hash
        content_hash = hashlib.sha256(content).hexdigest()
        
        # Check if content already exists
        if content_hash in self.content_registry:
            existing_cid = self.content_registry[content_hash]
            logger.info(f"Content already exists with CID: {existing_cid}")
            return existing_cid
        
        # Create temporary file
        temp_file = Path(f"/tmp/temp_content_{content_hash[:16]}")
        try:
            async with aiofiles.open(temp_file, 'wb') as f:
                await f.write(content)
            
            # Upload to IPFS
            ipfs_file = await self.ipfs_manager.upload_file(
                temp_file,
                owner=owner,
                metadata={
                    **(metadata or {}),
                    'content_type': content_type,
                    'content_hash': content_hash
                }
            )
            
            # Register content
            self.content_registry[content_hash] = ipfs_file.cid
            
            return ipfs_file.cid
            
        finally:
            # Clean up temporary file
            if temp_file.exists():
                temp_file.unlink()
    
    async def retrieve_content(self, cid: str) -> bytes:
        """Retrieve content by CID"""
        return await self.ipfs_manager.download_file(cid)
    
    async def verify_content(self, cid: str, expected_hash: str = None) -> bool:
        """Verify content integrity"""
        try:
            content = await self.retrieve_content(cid)
            actual_hash = hashlib.sha256(content).hexdigest()
            
            if expected_hash:
                return actual_hash == expected_hash
            
            # Check against registry
            for content_hash, registered_cid in self.content_registry.items():
                if registered_cid == cid:
                    return actual_hash == content_hash
            
            return False
            
        except Exception as e:
            logger.error(f"Content verification failed for {cid}: {e}")
            return False


# Global IPFS manager instance
ipfs_manager = None


def initialize_ipfs(config: Dict[str, Any]) -> IPFSManager:
    """Initialize global IPFS manager"""
    global ipfs_manager
    ipfs_manager = IPFSManager(config)
    return ipfs_manager


def get_ipfs_manager() -> Optional[IPFSManager]:
    """Get global IPFS manager instance"""
    return ipfs_manager
