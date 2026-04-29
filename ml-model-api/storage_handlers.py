"""
Advanced File Storage with Cloud Integration, CDN, and Optimization
"""

import os
import hashlib
import mimetypes
import asyncio
import aiohttp
import boto3
import logging
from typing import Dict, List, Optional, Any, Union, BinaryIO
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import tempfile
from pathlib import Path
import shutil
from concurrent.futures import ThreadPoolExecutor
import backoff
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

class StorageProvider(Enum):
    """Storage providers"""
    AWS_S3 = "aws_s3"
    GOOGLE_CLOUD = "google_cloud"
    AZURE_BLOB = "azure_blob"
    LOCAL = "local"
    MULTI_REGION = "multi_region"

class StorageTier(Enum):
    """Storage tiers for cost optimization"""
    STANDARD = "standard"
    INFREQUENT_ACCESS = "infrequent_access"
    ARCHIVE = "archive"
    COLD = "cold"

@dataclass
class StorageConfig:
    """Storage configuration"""
    provider: StorageProvider
    bucket_name: str
    region: str
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    cdn_domain: Optional[str] = None
    backup_enabled: bool = True
    backup_regions: List[str] = None
    encryption_enabled: bool = True
    compression_enabled: bool = True
    default_tier: StorageTier = StorageTier.STANDARD
    lifecycle_rules: Dict[str, Any] = None

@dataclass
class FileMetadata:
    """File metadata"""
    filename: str
    content_type: str
    size_bytes: int
    hash_md5: str
    upload_time: datetime
    last_accessed: datetime
    access_count: int
    storage_tier: StorageTier
    etag: str
    metadata: Dict[str, Any]
    cdn_url: Optional[str] = None
    backup_urls: List[str] = None

@dataclass
class StorageStats:
    """Storage statistics"""
    total_files: int
    total_size_bytes: int
    total_size_gb: float
    storage_by_tier: Dict[str, int]
    upload_count: int
    download_count: int
    delete_count: int
    bandwidth_used_bytes: int
    cost_estimate: float
    cache_hit_rate: float

class StorageHandler:
    """Advanced storage handler with cloud integration and optimization"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.stats = StorageStats(0, 0, 0.0, {}, 0, 0, 0, 0, 0.0, 0.0)
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = timedelta(minutes=30)
        
        # Initialize storage client
        self._init_storage_client()
        
        # Initialize backup clients if enabled
        self.backup_clients = {}
        if config.backup_enabled and config.backup_regions:
            self._init_backup_clients()
    
    def _init_storage_client(self):
        """Initialize primary storage client"""
        try:
            if self.config.provider == StorageProvider.AWS_S3:
                self.client = boto3.client(
                    's3',
                    aws_access_key_id=self.config.access_key,
                    aws_secret_access_key=self.config.secret_key,
                    region_name=self.config.region,
                    endpoint_url=self.config.endpoint_url
                )
                self.resource = boto3.resource(
                    's3',
                    aws_access_key_id=self.config.access_key,
                    aws_secret_access_key=self.config.secret_key,
                    region_name=self.config.region,
                    endpoint_url=self.config.endpoint_url
                )
            elif self.config.provider == StorageProvider.LOCAL:
                self.client = None
                self.storage_path = Path(self.config.bucket_name)
                self.storage_path.mkdir(parents=True, exist_ok=True)
            else:
                raise ValueError(f"Unsupported storage provider: {self.config.provider}")
                
            self.logger.info(f"Initialized {self.config.provider} storage client")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize storage client: {e}")
            raise
    
    def _init_backup_clients(self):
        """Initialize backup storage clients"""
        for region in self.config.backup_regions:
            try:
                backup_client = boto3.client(
                    's3',
                    aws_access_key_id=self.config.access_key,
                    aws_secret_access_key=self.config.secret_key,
                    region_name=region
                )
                self.backup_clients[region] = backup_client
                self.logger.info(f"Initialized backup client for region: {region}")
            except Exception as e:
                self.logger.error(f"Failed to initialize backup client for {region}: {e}")
    
    @backoff.on_exception(backoff.expo, ClientError, max_tries=3)
    async def upload_file(self, file_data: Union[bytes, BinaryIO], filename: str, 
                          content_type: str = None, metadata: Dict[str, Any] = None,
                          storage_tier: StorageTier = None) -> FileMetadata:
        """
        Upload file to storage with optimization and backup
        
        Args:
            file_data: File data as bytes or file-like object
            filename: Original filename
            content_type: MIME type
            metadata: Additional metadata
            storage_tier: Storage tier for cost optimization
        
        Returns:
            FileMetadata with upload details
        """
        try:
            # Generate file hash
            if isinstance(file_data, bytes):
                file_hash = hashlib.md5(file_data).hexdigest()
                file_size = len(file_data)
            else:
                # For file-like objects, read and reset position
                current_pos = file_data.tell()
                file_data.seek(0)
                data = file_data.read()
                file_data.seek(current_pos)
                file_hash = hashlib.md5(data).hexdigest()
                file_size = len(data)
            
            # Detect content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(filename)
                if not content_type:
                    content_type = 'application/octet-stream'
            
            # Compress if enabled and applicable
            if self.config.compression_enabled and content_type.startswith('text/'):
                file_data = await self._compress_data(file_data if isinstance(file_data, bytes) else data)
                file_size = len(file_data)
            
            # Generate unique object key
            object_key = self._generate_object_key(filename, file_hash)
            
            # Upload to primary storage
            upload_result = await self._upload_to_storage(
                file_data, object_key, content_type, metadata, storage_tier
            )
            
            # Create backup if enabled
            backup_urls = []
            if self.config.backup_enabled:
                backup_urls = await self._create_backups(file_data, object_key, content_type)
            
            # Generate CDN URL
            cdn_url = None
            if self.config.cdn_domain:
                cdn_url = f"https://{self.config.cdn_domain}/{object_key}"
            
            # Create metadata
            file_metadata = FileMetadata(
                filename=filename,
                content_type=content_type,
                size_bytes=file_size,
                hash_md5=file_hash,
                upload_time=datetime.now(),
                last_accessed=datetime.now(),
                access_count=0,
                storage_tier=storage_tier or self.config.default_tier,
                etag=upload_result.get('etag', ''),
                metadata=metadata or {},
                cdn_url=cdn_url,
                backup_urls=backup_urls
            )
            
            # Update statistics
            self.stats.upload_count += 1
            self.stats.total_files += 1
            self.stats.total_size_bytes += file_size
            self.stats.total_size_gb = self.stats.total_size_bytes / (1024**3)
            
            # Cache metadata
            self._cache_metadata(object_key, file_metadata)
            
            self.logger.info(f"Successfully uploaded {filename} to {object_key}")
            return file_metadata
            
        except Exception as e:
            self.logger.error(f"Failed to upload {filename}: {e}")
            raise
    
    async def download_file(self, object_key: str, range_header: str = None) -> tuple[bytes, FileMetadata]:
        """
        Download file from storage with caching
        
        Args:
            object_key: Storage object key
            range_header: Range header for partial downloads
        
        Returns:
            Tuple of (file_data, metadata)
        """
        try:
            # Check cache first
            cached_metadata = self._get_cached_metadata(object_key)
            if cached_metadata:
                cached_metadata.last_accessed = datetime.now()
                cached_metadata.access_count += 1
                self.stats.download_count += 1
                self.stats.cache_hit_rate = (self.stats.cache_hit_rate + 1) / self.stats.download_count
            else:
                # Fetch metadata from storage
                cached_metadata = await self._get_file_metadata(object_key)
                if not cached_metadata:
                    raise FileNotFoundError(f"File not found: {object_key}")
                
                # Cache metadata
                self._cache_metadata(object_key, cached_metadata)
                self.stats.download_count += 1
            
            # Download file data
            file_data = await self._download_from_storage(object_key, range_header)
            
            # Update bandwidth usage
            self.stats.bandwidth_used_bytes += len(file_data)
            
            return file_data, cached_metadata
            
        except Exception as e:
            self.logger.error(f"Failed to download {object_key}: {e}")
            raise
    
    async def delete_file(self, object_key: str) -> bool:
        """Delete file from storage and backups"""
        try:
            # Delete from primary storage
            await self._delete_from_storage(object_key)
            
            # Delete from backups
            if self.config.backup_enabled:
                await self._delete_from_backups(object_key)
            
            # Remove from cache
            if object_key in self.cache:
                del self.cache[object_key]
            
            # Update statistics
            self.stats.delete_count += 1
            
            self.logger.info(f"Successfully deleted {object_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete {object_key}: {e}")
            return False
    
    async def list_files(self, prefix: str = "", limit: int = 1000) -> List[FileMetadata]:
        """List files in storage"""
        try:
            files = []
            
            if self.config.provider == StorageProvider.AWS_S3:
                paginator = self.client.get_paginator('list_objects_v2')
                pages = paginator.paginate(
                    Bucket=self.config.bucket_name,
                    Prefix=prefix,
                    PaginationConfig={'MaxItems': limit}
                )
                
                async for page in pages:
                    for obj in page.get('Contents', []):
                        metadata = await self._get_file_metadata(obj['Key'])
                        if metadata:
                            files.append(metadata)
            
            elif self.config.provider == StorageProvider.LOCAL:
                storage_path = self.storage_path / prefix
                for file_path in storage_path.rglob('*'):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(self.storage_path)
                        metadata = await self._get_file_metadata(str(relative_path))
                        if metadata:
                            files.append(metadata)
            
            return files[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            return []
    
    async def get_storage_stats(self) -> StorageStats:
        """Get comprehensive storage statistics"""
        try:
            # Update storage by tier
            if self.config.provider == StorageProvider.AWS_S3:
                # Get storage class distribution
                self.stats.storage_by_tier = await self._get_storage_by_tier()
            
            # Estimate cost (simplified calculation)
            self.stats.cost_estimate = self._estimate_storage_cost()
            
            return self.stats
            
        except Exception as e:
            self.logger.error(f"Failed to get storage stats: {e}")
            return self.stats
    
    def _generate_object_key(self, filename: str, file_hash: str) -> str:
        """Generate unique object key"""
        # Use hash-based naming for deduplication
        ext = os.path.splitext(filename)[1]
        date_prefix = datetime.now().strftime('%Y/%m/%d')
        return f"{date_prefix}/{file_hash[:2]}/{file_hash[2:]}{ext}"
    
    async def _upload_to_storage(self, file_data: Union[bytes, BinaryIO], object_key: str,
                                 content_type: str, metadata: Dict[str, Any],
                                 storage_tier: StorageTier) -> Dict[str, Any]:
        """Upload to primary storage"""
        if self.config.provider == StorageProvider.AWS_S3:
            # Map storage tier to S3 storage class
            storage_class = self._map_tier_to_storage_class(storage_tier)
            
            extra_args = {
                'ContentType': content_type,
                'Metadata': metadata or {},
                'ServerSideEncryption': 'AES256' if self.config.encryption_enabled else None
            }
            
            if storage_class != 'STANDARD':
                extra_args['StorageClass'] = storage_class
            
            upload_args = {
                'Bucket': self.config.bucket_name,
                'Key': object_key,
                'Body': file_data,
                **extra_args
            }
            
            # Remove None values
            upload_args = {k: v for k, v in upload_args.items() if v is not None}
            
            result = self.client.put_object(**upload_args)
            return {'etag': result.get('ETag', '').strip('"')}
        
        elif self.config.provider == StorageProvider.LOCAL:
            file_path = self.storage_path / object_key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if isinstance(file_data, bytes):
                with open(file_path, 'wb') as f:
                    f.write(file_data)
            else:
                with open(file_path, 'wb') as f:
                    shutil.copyfileobj(file_data, f)
            
            file_hash = hashlib.md5(file_data if isinstance(file_data, bytes) else file_data.read()).hexdigest()
            return {'etag': file_hash}
        
        return {}
    
    async def _download_from_storage(self, object_key: str, range_header: str = None) -> bytes:
        """Download from primary storage"""
        if self.config.provider == StorageProvider.AWS_S3:
            download_args = {
                'Bucket': self.config.bucket_name,
                'Key': object_key
            }
            
            if range_header:
                download_args['Range'] = range_header
            
            response = self.client.get_object(**download_args)
            return response['Body'].read()
        
        elif self.config.provider == StorageProvider.LOCAL:
            file_path = self.storage_path / object_key
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    return f.read()
            
        raise FileNotFoundError(f"File not found: {object_key}")
    
    async def _delete_from_storage(self, object_key: str):
        """Delete from primary storage"""
        if self.config.provider == StorageProvider.AWS_S3:
            self.client.delete_object(
                Bucket=self.config.bucket_name,
                Key=object_key
            )
        
        elif self.config.provider == StorageProvider.LOCAL:
            file_path = self.storage_path / object_key
            if file_path.exists():
                file_path.unlink()
    
    async def _create_backups(self, file_data: Union[bytes, BinaryIO], 
                             object_key: str, content_type: str) -> List[str]:
        """Create backups in different regions"""
        backup_urls = []
        
        for region, backup_client in self.backup_clients.items():
            try:
                backup_bucket = f"{self.config.bucket_name}-backup-{region}"
                
                # Create backup bucket if it doesn't exist
                try:
                    backup_client.head_bucket(Bucket=backup_bucket)
                except ClientError:
                    backup_client.create_bucket(
                        Bucket=backup_bucket,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )
                
                # Upload backup
                backup_client.put_object(
                    Bucket=backup_bucket,
                    Key=object_key,
                    Body=file_data,
                    ContentType=content_type,
                    ServerSideEncryption='AES256' if self.config.encryption_enabled else None
                )
                
                backup_urls.append(f"s3://{backup_bucket}/{object_key}")
                
            except Exception as e:
                self.logger.error(f"Failed to create backup in {region}: {e}")
        
        return backup_urls
    
    async def _delete_from_backups(self, object_key: str):
        """Delete from backup regions"""
        for region, backup_client in self.backup_clients.items():
            try:
                backup_bucket = f"{self.config.bucket_name}-backup-{region}"
                backup_client.delete_object(
                    Bucket=backup_bucket,
                    Key=object_key
                )
            except Exception as e:
                self.logger.error(f"Failed to delete backup from {region}: {e}")
    
    async def _get_file_metadata(self, object_key: str) -> Optional[FileMetadata]:
        """Get file metadata from storage"""
        try:
            if self.config.provider == StorageProvider.AWS_S3:
                response = self.client.head_object(
                    Bucket=self.config.bucket_name,
                    Key=object_key
                )
                
                # Extract metadata from response
                metadata = response.get('Metadata', {})
                filename = metadata.get('original-filename', object_key.split('/')[-1])
                
                return FileMetadata(
                    filename=filename,
                    content_type=response.get('ContentType', ''),
                    size_bytes=response.get('ContentLength', 0),
                    hash_md5=response.get('ETag', '').strip('"'),
                    upload_time=response.get('LastModified', datetime.now()),
                    last_accessed=datetime.now(),
                    access_count=0,
                    storage_tier=self._map_storage_class_to_tier(
                        response.get('StorageClass', 'STANDARD')
                    ),
                    etag=response.get('ETag', '').strip('"'),
                    metadata=metadata,
                    cdn_url=f"https://{self.config.cdn_domain}/{object_key}" if self.config.cdn_domain else None
                )
            
            elif self.config.provider == StorageProvider.LOCAL:
                file_path = self.storage_path / object_key
                if file_path.exists():
                    stat = file_path.stat()
                    return FileMetadata(
                        filename=file_path.name,
                        content_type=mimetypes.guess_type(str(file_path))[0] or '',
                        size_bytes=stat.st_size,
                        hash_md5='',  # Would need to calculate
                        upload_time=datetime.fromtimestamp(stat.st_ctime),
                        last_accessed=datetime.fromtimestamp(stat.st_atime),
                        access_count=0,
                        storage_tier=StorageTier.STANDARD,
                        etag='',
                        metadata={}
                    )
            
        except Exception as e:
            self.logger.error(f"Failed to get metadata for {object_key}: {e}")
        
        return None
    
    async def _compress_data(self, data: bytes) -> bytes:
        """Compress data for storage"""
        import gzip
        return gzip.compress(data)
    
    def _map_tier_to_storage_class(self, tier: StorageTier) -> str:
        """Map storage tier to S3 storage class"""
        mapping = {
            StorageTier.STANDARD: 'STANDARD',
            StorageTier.INFREQUENT_ACCESS: 'STANDARD_IA',
            StorageTier.ARCHIVE: 'GLACIER',
            StorageTier.COLD: 'DEEP_ARCHIVE'
        }
        return mapping.get(tier, 'STANDARD')
    
    def _map_storage_class_to_tier(self, storage_class: str) -> StorageTier:
        """Map S3 storage class to storage tier"""
        mapping = {
            'STANDARD': StorageTier.STANDARD,
            'STANDARD_IA': StorageTier.INFREQUENT_ACCESS,
            'GLACIER': StorageTier.ARCHIVE,
            'DEEP_ARCHIVE': StorageTier.COLD
        }
        return mapping.get(storage_class, StorageTier.STANDARD)
    
    async def _get_storage_by_tier(self) -> Dict[str, int]:
        """Get storage distribution by tier"""
        storage_by_tier = {}
        
        if self.config.provider == StorageProvider.AWS_S3:
            try:
                # Use CloudWatch metrics or S3 Inventory for accurate data
                # For now, return empty dict (would need CloudWatch integration)
                pass
            except Exception as e:
                self.logger.error(f"Failed to get storage by tier: {e}")
        
        return storage_by_tier
    
    def _estimate_storage_cost(self) -> float:
        """Estimate monthly storage cost"""
        # Simplified cost calculation (would need actual pricing)
        cost_per_gb = {
            StorageTier.STANDARD: 0.023,
            StorageTier.INFREQUENT_ACCESS: 0.0125,
            StorageTier.ARCHIVE: 0.004,
            StorageTier.COLD: 0.00099
        }
        
        total_cost = 0.0
        for tier, count in self.stats.storage_by_tier.items():
            if tier in cost_per_gb:
                # Estimate GB per tier (simplified)
                estimated_gb = count * 0.1  # Rough estimate
                total_cost += estimated_gb * cost_per_gb[tier]
        
        return total_cost
    
    def _cache_metadata(self, object_key: str, metadata: FileMetadata):
        """Cache file metadata"""
        self.cache[object_key] = {
            'metadata': metadata,
            'cached_at': datetime.now()
        }
    
    def _get_cached_metadata(self, object_key: str) -> Optional[FileMetadata]:
        """Get cached metadata if not expired"""
        if object_key in self.cache:
            cached_item = self.cache[object_key]
            if datetime.now() - cached_item['cached_at'] < self.cache_ttl:
                return cached_item['metadata']
            else:
                del self.cache[object_key]
        return None

# Utility functions
def create_storage_config_from_env() -> StorageConfig:
    """Create storage config from environment variables"""
    return StorageConfig(
        provider=StorageProvider(os.getenv('STORAGE_PROVIDER', 'aws_s3')),
        bucket_name=os.getenv('STORAGE_BUCKET', 'flavorsnap-storage'),
        region=os.getenv('STORAGE_REGION', 'us-east-1'),
        access_key=os.getenv('AWS_ACCESS_KEY_ID'),
        secret_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        endpoint_url=os.getenv('STORAGE_ENDPOINT_URL'),
        cdn_domain=os.getenv('CDN_DOMAIN'),
        backup_enabled=os.getenv('STORAGE_BACKUP_ENABLED', 'true').lower() == 'true',
        backup_regions=os.getenv('STORAGE_BACKUP_REGIONS', '').split(',') if os.getenv('STORAGE_BACKUP_REGIONS') else [],
        encryption_enabled=os.getenv('STORAGE_ENCRYPTION_ENABLED', 'true').lower() == 'true',
        compression_enabled=os.getenv('STORAGE_COMPRESSION_ENABLED', 'true').lower() == 'true'
    )

# Global storage handler instance
storage_handler = None

def get_storage_handler() -> StorageHandler:
    """Get global storage handler instance"""
    global storage_handler
    if not storage_handler:
        config = create_storage_config_from_env()
        storage_handler = StorageHandler(config)
    return storage_handler
