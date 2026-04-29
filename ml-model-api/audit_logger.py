"""
Advanced Audit Logger for FlavorSnap API
Implements comprehensive audit logging with structured logging, monitoring, and compliance
"""
import os
import json
import time
import hashlib
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import uuid
import gzip
import boto3
from elasticsearch import Elasticsearch
from flask import request, current_app, g


class AuditEventType(Enum):
    """Audit event types"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_CONFIG = "system_config"
    SECURITY_EVENT = "security_event"
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    USER_ACTION = "user_action"
    ADMIN_ACTION = "admin_action"
    ERROR_EVENT = "error_event"
    COMPLIANCE_CHECK = "compliance_check"


class AuditSeverity(Enum):
    """Audit event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event data structure"""
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: str
    user_agent: str
    endpoint: str
    method: str
    status_code: Optional[int]
    request_id: Optional[str]
    client_id: Optional[str]
    resource: Optional[str]
    action: Optional[str]
    details: Dict[str, Any]
    compliance_tags: List[str]
    retention_days: int = 365
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        return data
    
    def to_json(self) -> str:
        """Convert audit event to JSON"""
        return json.dumps(self.to_dict())


class AuditConfig:
    """Audit configuration settings"""
    
    # Logging configuration
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Retention policies
    RETENTION_PERIODS = {
        AuditSeverity.LOW: 90,      # 90 days
        AuditSeverity.MEDIUM: 365,  # 1 year
        AuditSeverity.HIGH: 1825,  # 5 years
        AuditSeverity.CRITICAL: 3650  # 10 years
    }
    
    # Compliance requirements
    COMPLIANCE_FRAMEWORKS = {
        'GDPR': ['data_access', 'data_modification', 'user_action', 'authentication'],
        'SOX': ['admin_action', 'system_config', 'data_modification'],
        'HIPAA': ['data_access', 'data_modification', 'authentication'],
        'PCI_DSS': ['data_access', 'authentication', 'security_event']
    }
    
    # Storage configuration
    STORAGE_BACKENDS = ['file', 'elasticsearch', 's3']
    DEFAULT_STORAGE_BACKEND = 'file'
    
    # Buffer configuration
    BUFFER_SIZE = 1000
    FLUSH_INTERVAL = 60  # seconds
    
    # Elasticsearch configuration
    ELASTICSEARCH_INDEX_PREFIX = 'audit_logs'
    ELASTICSEARCH_MAPPING = {
        'mappings': {
            'properties': {
                'timestamp': {'type': 'date'},
                'event_type': {'type': 'keyword'},
                'severity': {'type': 'keyword'},
                'user_id': {'type': 'keyword'},
                'session_id': {'type': 'keyword'},
                'ip_address': {'type': 'ip'},
                'endpoint': {'type': 'keyword'},
                'method': {'type': 'keyword'},
                'status_code': {'type': 'integer'},
                'request_id': {'type': 'keyword'},
                'client_id': {'type': 'keyword'},
                'resource': {'type': 'keyword'},
                'action': {'type': 'keyword'},
                'compliance_tags': {'type': 'keyword'},
                'details': {'type': 'object', 'dynamic': True}
            }
        }
    }


class AuditStorageBackend:
    """Abstract base class for audit storage backends"""
    
    def store_event(self, event: AuditEvent) -> bool:
        """Store audit event"""
        raise NotImplementedError
    
    def query_events(self, query: Dict[str, Any]) -> List[AuditEvent]:
        """Query audit events"""
        raise NotImplementedError
    
    def cleanup_old_events(self, cutoff_date: datetime) -> int:
        """Clean up old events"""
        raise NotImplementedError


class FileAuditStorage(AuditStorageBackend):
    """File-based audit storage"""
    
    def __init__(self, log_dir: str = 'logs/audit'):
        self.log_dir = log_dir
        self.logger = logging.getLogger(__name__)
        os.makedirs(log_dir, exist_ok=True)
    
    def store_event(self, event: AuditEvent) -> bool:
        """Store audit event to file"""
        try:
            # Create daily log file
            date_str = event.timestamp.strftime('%Y-%m-%d')
            log_file = os.path.join(self.log_dir, f'audit_{date_str}.log')
            
            # Write event to file
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(event.to_json() + '\n')
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to store audit event to file: {str(e)}")
            return False
    
    def query_events(self, query: Dict[str, Any]) -> List[AuditEvent]:
        """Query audit events from files"""
        events = []
        
        # Determine date range
        start_date = query.get('start_date')
        end_date = query.get('end_date')
        
        if not start_date:
            start_date = datetime.now() - timedelta(days=1)
        if not end_date:
            end_date = datetime.now()
        
        # Scan log files in date range
        current_date = start_date.date()
        while current_date <= end_date.date():
            date_str = current_date.strftime('%Y-%m-%d')
            log_file = os.path.join(self.log_dir, f'audit_{date_str}.log')
            
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                event_data = json.loads(line.strip())
                                event = self._dict_to_event(event_data)
                                
                                # Apply filters
                                if self._matches_query(event, query):
                                    events.append(event)
                            except json.JSONDecodeError:
                                continue
                except Exception as e:
                    self.logger.error(f"Failed to read audit log file {log_file}: {str(e)}")
            
            current_date += timedelta(days=1)
        
        return events
    
    def cleanup_old_events(self, cutoff_date: datetime) -> int:
        """Clean up old audit log files"""
        removed_count = 0
        
        try:
            for filename in os.listdir(self.log_dir):
                if filename.startswith('audit_') and filename.endswith('.log'):
                    file_path = os.path.join(self.log_dir, filename)
                    
                    # Extract date from filename
                    date_str = filename[6:-4]  # Remove 'audit_' prefix and '.log' suffix
                    try:
                        file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        if file_date < cutoff_date.date():
                            os.remove(file_path)
                            removed_count += 1
                            self.logger.info(f"Removed old audit log: {filename}")
                    except ValueError:
                        continue
        except Exception as e:
            self.logger.error(f"Failed to cleanup old audit logs: {str(e)}")
        
        return removed_count
    
    def _dict_to_event(self, data: Dict[str, Any]) -> AuditEvent:
        """Convert dictionary to AuditEvent"""
        return AuditEvent(
            event_id=data['event_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            event_type=AuditEventType(data['event_type']),
            severity=AuditSeverity(data['severity']),
            user_id=data.get('user_id'),
            session_id=data.get('session_id'),
            ip_address=data['ip_address'],
            user_agent=data['user_agent'],
            endpoint=data['endpoint'],
            method=data['method'],
            status_code=data.get('status_code'),
            request_id=data.get('request_id'),
            client_id=data.get('client_id'),
            resource=data.get('resource'),
            action=data.get('action'),
            details=data.get('details', {}),
            compliance_tags=data.get('compliance_tags', []),
            retention_days=data.get('retention_days', 365)
        )
    
    def _matches_query(self, event: AuditEvent, query: Dict[str, Any]) -> bool:
        """Check if event matches query filters"""
        # Filter by event type
        if 'event_type' in query:
            if isinstance(query['event_type'], list):
                if event.event_type not in [AuditEventType(t) for t in query['event_type']]:
                    return False
            elif event.event_type != AuditEventType(query['event_type']):
                return False
        
        # Filter by severity
        if 'severity' in query:
            if isinstance(query['severity'], list):
                if event.severity not in [AuditSeverity(s) for s in query['severity']]:
                    return False
            elif event.severity != AuditSeverity(query['severity']):
                return False
        
        # Filter by user_id
        if 'user_id' in query and event.user_id != query['user_id']:
            return False
        
        # Filter by IP address
        if 'ip_address' in query and event.ip_address != query['ip_address']:
            return False
        
        # Filter by endpoint
        if 'endpoint' in query and query['endpoint'] not in event.endpoint:
            return False
        
        return True


class ElasticsearchAuditStorage(AuditStorageBackend):
    """Elasticsearch-based audit storage"""
    
    def __init__(self, hosts: List[str] = None, index_prefix: str = None):
        self.hosts = hosts or ['localhost:9200']
        self.index_prefix = index_prefix or AuditConfig.ELASTICSEARCH_INDEX_PREFIX
        self.logger = logging.getLogger(__name__)
        
        try:
            self.es = Elasticsearch(self.hosts)
            self._create_index_template()
            self.logger.info("Elasticsearch audit storage initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Elasticsearch: {str(e)}")
            self.es = None
    
    def _create_index_template(self):
        """Create index template for audit logs"""
        try:
            self.es.indices.put_template(
                name='audit_logs_template',
                body=AuditConfig.ELASTICSEARCH_MAPPING
            )
        except Exception as e:
            self.logger.error(f"Failed to create index template: {str(e)}")
    
    def store_event(self, event: AuditEvent) -> bool:
        """Store audit event to Elasticsearch"""
        if not self.es:
            return False
        
        try:
            # Use daily index
            index_name = f"{self.index_prefix}_{event.timestamp.strftime('%Y.%m.%d')}"
            
            # Store event
            self.es.index(
                index=index_name,
                id=event.event_id,
                body=event.to_dict()
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to store audit event to Elasticsearch: {str(e)}")
            return False
    
    def query_events(self, query: Dict[str, Any]) -> List[AuditEvent]:
        """Query audit events from Elasticsearch"""
        if not self.es:
            return []
        
        try:
            # Build Elasticsearch query
            es_query = self._build_es_query(query)
            
            # Determine index pattern
            start_date = query.get('start_date', datetime.now() - timedelta(days=1))
            end_date = query.get('end_date', datetime.now())
            
            index_pattern = f"{self.index_prefix}_*"
            
            # Execute search
            response = self.es.search(
                index=index_pattern,
                body=es_query,
                size=query.get('limit', 100)
            )
            
            # Convert hits to AuditEvent objects
            events = []
            for hit in response['hits']['hits']:
                event_data = hit['_source']
                event = self._dict_to_event(event_data)
                events.append(event)
            
            return events
        except Exception as e:
            self.logger.error(f"Failed to query audit events from Elasticsearch: {str(e)}")
            return []
    
    def cleanup_old_events(self, cutoff_date: datetime) -> int:
        """Clean up old events from Elasticsearch"""
        if not self.es:
            return 0
        
        removed_count = 0
        
        try:
            # Find indices older than cutoff date
            indices = self.es.cat.indices(index=f"{self.index_prefix}_*", format='json')
            
            for index_info in indices:
                index_name = index_info['index']
                
                # Extract date from index name
                date_str = index_name.split('_')[-1]
                try:
                    index_date = datetime.strptime(date_str, '%Y.%m.%d')
                    
                    if index_date < cutoff_date:
                        self.es.indices.delete(index=index_name)
                        removed_count += 1
                        self.logger.info(f"Removed old Elasticsearch index: {index_name}")
                except ValueError:
                    continue
        except Exception as e:
            self.logger.error(f"Failed to cleanup old Elasticsearch indices: {str(e)}")
        
        return removed_count
    
    def _build_es_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Build Elasticsearch query from audit query"""
        es_query = {
            'query': {
                'bool': {
                    'must': []
                }
            }
        }
        
        # Date range
        if 'start_date' in query or 'end_date' in query:
            date_range = {}
            if 'start_date' in query:
                date_range['gte'] = query['start_date'].isoformat()
            if 'end_date' in query:
                date_range['lte'] = query['end_date'].isoformat()
            
            es_query['query']['bool']['must'].append({
                'range': {
                    'timestamp': date_range
                }
            })
        
        # Event type filter
        if 'event_type' in query:
            if isinstance(query['event_type'], list):
                es_query['query']['bool']['must'].append({
                    'terms': {'event_type': query['event_type']}
                })
            else:
                es_query['query']['bool']['must'].append({
                    'term': {'event_type': query['event_type']}
                })
        
        # Severity filter
        if 'severity' in query:
            if isinstance(query['severity'], list):
                es_query['query']['bool']['must'].append({
                    'terms': {'severity': query['severity']}
                })
            else:
                es_query['query']['bool']['must'].append({
                    'term': {'severity': query['severity']}
                })
        
        # User ID filter
        if 'user_id' in query:
            es_query['query']['bool']['must'].append({
                'term': {'user_id': query['user_id']}
            })
        
        # IP address filter
        if 'ip_address' in query:
            es_query['query']['bool']['must'].append({
                'term': {'ip_address': query['ip_address']}
            })
        
        # Endpoint filter
        if 'endpoint' in query:
            es_query['query']['bool']['must'].append({
                'wildcard': {'endpoint': f"*{query['endpoint']}*"}
            })
        
        return es_query
    
    def _dict_to_event(self, data: Dict[str, Any]) -> AuditEvent:
        """Convert dictionary to AuditEvent"""
        return AuditEvent(
            event_id=data['event_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            event_type=AuditEventType(data['event_type']),
            severity=AuditSeverity(data['severity']),
            user_id=data.get('user_id'),
            session_id=data.get('session_id'),
            ip_address=data['ip_address'],
            user_agent=data['user_agent'],
            endpoint=data['endpoint'],
            method=data['method'],
            status_code=data.get('status_code'),
            request_id=data.get('request_id'),
            client_id=data.get('client_id'),
            resource=data.get('resource'),
            action=data.get('action'),
            details=data.get('details', {}),
            compliance_tags=data.get('compliance_tags', []),
            retention_days=data.get('retention_days', 365)
        )


class S3AuditStorage(AuditStorageBackend):
    """S3-based audit storage for long-term archival"""
    
    def __init__(self, bucket_name: str, aws_access_key: str = None, 
                 aws_secret_key: str = None, region: str = 'us-east-1'):
        self.bucket_name = bucket_name
        self.logger = logging.getLogger(__name__)
        
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key or os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=aws_secret_key or os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=region
            )
            self.logger.info("S3 audit storage initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {str(e)}")
            self.s3_client = None
    
    def store_event(self, event: AuditEvent) -> bool:
        """Store audit event to S3 (batched daily)"""
        if not self.s3_client:
            return False
        
        try:
            # Create daily batch file
            date_str = event.timestamp.strftime('%Y-%m-%d')
            key = f"audit_logs/{date_str}.jsonl.gz"
            
            # Get existing content or create new
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                existing_content = gzip.decompress(response['Body'].read()).decode('utf-8')
            except self.s3_client.exceptions.NoSuchKey:
                existing_content = ''
            
            # Append new event
            existing_content += event.to_json() + '\n'
            
            # Compress and upload
            compressed_content = gzip.compress(existing_content.encode('utf-8'))
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=compressed_content,
                ContentEncoding='gzip',
                ContentType='application/json'
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to store audit event to S3: {str(e)}")
            return False
    
    def query_events(self, query: Dict[str, Any]) -> List[AuditEvent]:
        """Query audit events from S3"""
        # This would be more complex for S3 - would need to list objects,
        # download relevant files, and parse them
        # For now, return empty list
        return []
    
    def cleanup_old_events(self, cutoff_date: datetime) -> int:
        """Clean up old audit logs from S3"""
        if not self.s3_client:
            return 0
        
        removed_count = 0
        
        try:
            # List objects in audit_logs prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix='audit_logs/')
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        
                        # Extract date from key
                        try:
                            date_str = key.split('/')[-1].replace('.jsonl.gz', '')
                            file_date = datetime.strptime(date_str, '%Y-%m-%d')
                            
                            if file_date < cutoff_date.date():
                                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                                removed_count += 1
                                self.logger.info(f"Removed old S3 audit log: {key}")
                        except ValueError:
                            continue
        except Exception as e:
            self.logger.error(f"Failed to cleanup old S3 audit logs: {str(e)}")
        
        return removed_count


class AuditLogger:
    """Main audit logger class"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.storage_backends: List[AuditStorageBackend] = []
        self.event_buffer: deque = deque(maxlen=AuditConfig.BUFFER_SIZE)
        self.buffer_lock = threading.Lock()
        self.flush_timer = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize audit logger with Flask app"""
        self.app = app
        
        # Configure logging
        logging.basicConfig(
            level=AuditConfig.LOG_LEVEL,
            format=AuditConfig.LOG_FORMAT
        )
        
        # Initialize storage backends
        self._initialize_storage_backends(app)
        
        # Start background flush timer
        self._start_flush_timer()
        
        # Register request hooks
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_appcontext(self._teardown_request)
        
        self.logger.info("Audit logger initialized")
    
    def _initialize_storage_backends(self, app):
        """Initialize storage backends based on configuration"""
        storage_config = app.config.get('AUDIT_STORAGE', {})
        
        # Default to file storage
        if not storage_config:
            self.storage_backends.append(FileAuditStorage())
            return
        
        # Initialize configured backends
        for backend_config in storage_config:
            backend_type = backend_config.get('type')
            
            if backend_type == 'file':
                log_dir = backend_config.get('log_dir', 'logs/audit')
                self.storage_backends.append(FileAuditStorage(log_dir))
            
            elif backend_type == 'elasticsearch':
                hosts = backend_config.get('hosts', ['localhost:9200'])
                index_prefix = backend_config.get('index_prefix')
                self.storage_backends.append(ElasticsearchAuditStorage(hosts, index_prefix))
            
            elif backend_type == 's3':
                bucket_name = backend_config.get('bucket_name')
                aws_access_key = backend_config.get('aws_access_key')
                aws_secret_key = backend_config.get('aws_secret_key')
                region = backend_config.get('region', 'us-east-1')
                self.storage_backends.append(S3AuditStorage(bucket_name, aws_access_key, aws_secret_key, region))
    
    def _start_flush_timer(self):
        """Start background timer for flushing events"""
        if self.flush_timer:
            self.flush_timer.cancel()
        
        self.flush_timer = threading.Timer(AuditConfig.FLUSH_INTERVAL, self._flush_events)
        self.flush_timer.daemon = True
        self.flush_timer.start()
    
    def _before_request(self):
        """Log request start"""
        # Generate request ID
        request_id = str(uuid.uuid4())
        g.request_id = request_id
        g.request_start_time = time.time()
        
        # Extract request information
        user_id = getattr(g, 'user_id', None)
        session_id = getattr(g, 'session_id', None)
        client_id = request.headers.get('X-Client-ID')
        
        # Create audit event
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            event_type=AuditEventType.API_REQUEST,
            severity=AuditSeverity.LOW,
            user_id=user_id,
            session_id=session_id,
            ip_address=self._get_client_ip(),
            user_agent=request.headers.get('User-Agent', ''),
            endpoint=request.endpoint or 'unknown',
            method=request.method,
            status_code=None,
            request_id=request_id,
            client_id=client_id,
            resource=request.path,
            action='request_start',
            details={
                'query_params': dict(request.args),
                'content_length': request.content_length or 0,
                'content_type': request.content_type
            },
            compliance_tags=self._get_compliance_tags(AuditEventType.API_REQUEST)
        )
        
        self.log_event(event)
    
    def _after_request(self, response):
        """Log request completion"""
        if not hasattr(g, 'request_id'):
            return response
        
        # Calculate request duration
        start_time = getattr(g, 'request_start_time', time.time())
        duration = time.time() - start_time
        
        # Extract request information
        user_id = getattr(g, 'user_id', None)
        session_id = getattr(g, 'session_id', None)
        client_id = request.headers.get('X-Client-ID')
        
        # Determine severity based on status code
        if response.status_code >= 500:
            severity = AuditSeverity.HIGH
        elif response.status_code >= 400:
            severity = AuditSeverity.MEDIUM
        else:
            severity = AuditSeverity.LOW
        
        # Create audit event
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            event_type=AuditEventType.API_RESPONSE,
            severity=severity,
            user_id=user_id,
            session_id=session_id,
            ip_address=self._get_client_ip(),
            user_agent=request.headers.get('User-Agent', ''),
            endpoint=request.endpoint or 'unknown',
            method=request.method,
            status_code=response.status_code,
            request_id=g.request_id,
            client_id=client_id,
            resource=request.path,
            action='request_complete',
            details={
                'duration_ms': round(duration * 1000, 2),
                'response_size': len(response.get_data()) if hasattr(response, 'get_data') else 0
            },
            compliance_tags=self._get_compliance_tags(AuditEventType.API_RESPONSE)
        )
        
        self.log_event(event)
        return response
    
    def _teardown_request(self, exception):
        """Log request teardown and any exceptions"""
        if exception and hasattr(g, 'request_id'):
            # Extract request information
            user_id = getattr(g, 'user_id', None)
            session_id = getattr(g, 'session_id', None)
            client_id = request.headers.get('X-Client-ID')
            
            # Create error audit event
            event = AuditEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                event_type=AuditEventType.ERROR_EVENT,
                severity=AuditSeverity.HIGH,
                user_id=user_id,
                session_id=session_id,
                ip_address=self._get_client_ip(),
                user_agent=request.headers.get('User-Agent', ''),
                endpoint=request.endpoint or 'unknown',
                method=request.method,
                status_code=500,
                request_id=g.request_id,
                client_id=client_id,
                resource=request.path,
                action='request_error',
                details={
                    'error_type': type(exception).__name__,
                    'error_message': str(exception),
                    'traceback': getattr(exception, '__traceback__', None)
                },
                compliance_tags=self._get_compliance_tags(AuditEventType.ERROR_EVENT)
            )
            
            self.log_event(event)
    
    def log_event(self, event: AuditEvent):
        """Log audit event"""
        with self.buffer_lock:
            self.event_buffer.append(event)
    
    def log_authentication_event(self, success: bool, user_id: str = None, 
                               auth_method: str = 'password', failure_reason: str = None):
        """Log authentication event"""
        severity = AuditSeverity.LOW if success else AuditSeverity.MEDIUM
        
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            event_type=AuditEventType.AUTHENTICATION,
            severity=severity,
            user_id=user_id,
            session_id=getattr(g, 'session_id', None),
            ip_address=self._get_client_ip(),
            user_agent=request.headers.get('User-Agent', ''),
            endpoint='/auth/login',
            method='POST',
            status_code=200 if success else 401,
            request_id=getattr(g, 'request_id', None),
            client_id=request.headers.get('X-Client-ID'),
            resource='authentication',
            action='login_attempt',
            details={
                'auth_method': auth_method,
                'success': success,
                'failure_reason': failure_reason
            },
            compliance_tags=self._get_compliance_tags(AuditEventType.AUTHENTICATION)
        )
        
        self.log_event(event)
    
    def log_authorization_event(self, user_id: str, resource: str, action: str, 
                              allowed: bool, reason: str = None):
        """Log authorization event"""
        severity = AuditSeverity.LOW if allowed else AuditSeverity.MEDIUM
        
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            event_type=AuditEventType.AUTHORIZATION,
            severity=severity,
            user_id=user_id,
            session_id=getattr(g, 'session_id', None),
            ip_address=self._get_client_ip(),
            user_agent=request.headers.get('User-Agent', ''),
            endpoint=request.endpoint or 'unknown',
            method=request.method,
            status_code=200 if allowed else 403,
            request_id=getattr(g, 'request_id', None),
            client_id=request.headers.get('X-Client-ID'),
            resource=resource,
            action=action,
            details={
                'allowed': allowed,
                'reason': reason
            },
            compliance_tags=self._get_compliance_tags(AuditEventType.AUTHORIZATION)
        )
        
        self.log_event(event)
    
    def log_data_access(self, user_id: str, resource: str, action: str, 
                       record_count: int = None, data_type: str = None):
        """Log data access event"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            event_type=AuditEventType.DATA_ACCESS,
            severity=AuditSeverity.MEDIUM,
            user_id=user_id,
            session_id=getattr(g, 'session_id', None),
            ip_address=self._get_client_ip(),
            user_agent=request.headers.get('User-Agent', ''),
            endpoint=request.endpoint or 'unknown',
            method=request.method,
            status_code=200,
            request_id=getattr(g, 'request_id', None),
            client_id=request.headers.get('X-Client-ID'),
            resource=resource,
            action=action,
            details={
                'record_count': record_count,
                'data_type': data_type
            },
            compliance_tags=self._get_compliance_tags(AuditEventType.DATA_ACCESS)
        )
        
        self.log_event(event)
    
    def log_data_modification(self, user_id: str, resource: str, action: str, 
                            changes: Dict[str, Any] = None):
        """Log data modification event"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            event_type=AuditEventType.DATA_MODIFICATION,
            severity=AuditSeverity.HIGH,
            user_id=user_id,
            session_id=getattr(g, 'session_id', None),
            ip_address=self._get_client_ip(),
            user_agent=request.headers.get('User-Agent', ''),
            endpoint=request.endpoint or 'unknown',
            method=request.method,
            status_code=200,
            request_id=getattr(g, 'request_id', None),
            client_id=request.headers.get('X-Client-ID'),
            resource=resource,
            action=action,
            details={
                'changes': changes or {}
            },
            compliance_tags=self._get_compliance_tags(AuditEventType.DATA_MODIFICATION)
        )
        
        self.log_event(event)
    
    def log_security_event(self, threat_type: str, threat_score: int, 
                         ip_address: str, details: Dict[str, Any] = None):
        """Log security event"""
        # Determine severity based on threat score
        if threat_score >= 80:
            severity = AuditSeverity.CRITICAL
        elif threat_score >= 50:
            severity = AuditSeverity.HIGH
        elif threat_score >= 20:
            severity = AuditSeverity.MEDIUM
        else:
            severity = AuditSeverity.LOW
        
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            event_type=AuditEventType.SECURITY_EVENT,
            severity=severity,
            user_id=None,
            session_id=None,
            ip_address=ip_address,
            user_agent=request.headers.get('User-Agent', ''),
            endpoint=request.endpoint or 'unknown',
            method=request.method,
            status_code=403,
            request_id=getattr(g, 'request_id', None),
            client_id=request.headers.get('X-Client-ID'),
            resource='security',
            action=threat_type,
            details=details or {},
            compliance_tags=self._get_compliance_tags(AuditEventType.SECURITY_EVENT)
        )
        
        self.log_event(event)
    
    def _get_client_ip(self) -> str:
        """Get client IP address"""
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        return request.remote_addr or 'unknown'
    
    def _get_compliance_tags(self, event_type: AuditEventType) -> List[str]:
        """Get compliance tags for event type"""
        tags = []
        
        for framework, event_types in AuditConfig.COMPLIANCE_FRAMEWORKS.items():
            if event_type.value in event_types:
                tags.append(framework)
        
        return tags
    
    def _flush_events(self):
        """Flush buffered events to storage backends"""
        with self.buffer_lock:
            if not self.event_buffer:
                return
            
            events_to_flush = list(self.event_buffer)
            self.event_buffer.clear()
        
        # Store events in all backends
        for backend in self.storage_backends:
            for event in events_to_flush:
                backend.store_event(event)
        
        self.logger.info(f"Flushed {len(events_to_flush)} audit events")
        
        # Restart timer
        self._start_flush_timer()
    
    def query_events(self, query: Dict[str, Any]) -> List[AuditEvent]:
        """Query audit events"""
        all_events = []
        
        # Query all backends
        for backend in self.storage_backends:
            try:
                events = backend.query_events(query)
                all_events.extend(events)
            except Exception as e:
                self.logger.error(f"Failed to query backend {type(backend).__name__}: {str(e)}")
        
        # Remove duplicates and sort
        unique_events = {event.event_id: event for event in all_events}.values()
        sorted_events = sorted(unique_events, key=lambda x: x.timestamp, reverse=True)
        
        return sorted_events[:query.get('limit', 100)]
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get audit statistics"""
        # Query events from last 24 hours
        query = {
            'start_date': datetime.now() - timedelta(hours=24),
            'end_date': datetime.now(),
            'limit': 10000
        }
        
        events = self.query_events(query)
        
        # Calculate statistics
        stats = {
            'total_events': len(events),
            'events_by_type': defaultdict(int),
            'events_by_severity': defaultdict(int),
            'top_users': defaultdict(int),
            'top_ips': defaultdict(int),
            'hourly_distribution': defaultdict(int)
        }
        
        for event in events:
            stats['events_by_type'][event.event_type.value] += 1
            stats['events_by_severity'][event.severity.value] += 1
            
            if event.user_id:
                stats['top_users'][event.user_id] += 1
            
            stats['top_ips'][event.ip_address] += 1
            
            hour = event.timestamp.hour
            stats['hourly_distribution'][hour] += 1
        
        # Convert defaultdicts to regular dicts and sort
        stats['events_by_type'] = dict(sorted(stats['events_by_type'].items(), key=lambda x: x[1], reverse=True))
        stats['events_by_severity'] = dict(sorted(stats['events_by_severity'].items(), key=lambda x: x[1], reverse=True))
        stats['top_users'] = dict(sorted(stats['top_users'].items(), key=lambda x: x[1], reverse=True)[:10])
        stats['top_ips'] = dict(sorted(stats['top_ips'].items(), key=lambda x: x[1], reverse=True)[:10])
        stats['hourly_distribution'] = dict(stats['hourly_distribution'])
        
        return stats
    
    def cleanup_old_events(self):
        """Clean up old events based on retention policies"""
        total_removed = 0
        
        for backend in self.storage_backends:
            try:
                # Determine cutoff date for each severity level
                cutoff_dates = {}
                for severity, days in AuditConfig.RETENTION_PERIODS.items():
                    cutoff_dates[severity] = datetime.now() - timedelta(days=days)
                
                # Use the longest retention period (critical events)
                cutoff_date = cutoff_dates[AuditSeverity.CRITICAL]
                
                removed = backend.cleanup_old_events(cutoff_date)
                total_removed += removed
                
                self.logger.info(f"Cleaned up {removed} old events from {type(backend).__name__}")
            except Exception as e:
                self.logger.error(f"Failed to cleanup backend {type(backend).__name__}: {str(e)}")
        
        return total_removed
    
    def export_audit_report(self, start_date: datetime, end_date: datetime, 
                           format: str = 'json') -> str:
        """Export audit report for date range"""
        query = {
            'start_date': start_date,
            'end_date': end_date,
            'limit': 50000
        }
        
        events = self.query_events(query)
        
        if format == 'json':
            report_data = {
                'metadata': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'total_events': len(events),
                    'generated_at': datetime.now().isoformat()
                },
                'events': [event.to_dict() for event in events]
            }
            
            return json.dumps(report_data, indent=2)
        
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            header = ['event_id', 'timestamp', 'event_type', 'severity', 'user_id', 
                     'ip_address', 'endpoint', 'method', 'status_code', 'resource', 'action']
            writer.writerow(header)
            
            # Write events
            for event in events:
                row = [
                    event.event_id,
                    event.timestamp.isoformat(),
                    event.event_type.value,
                    event.severity.value,
                    event.user_id or '',
                    event.ip_address,
                    event.endpoint,
                    event.method,
                    event.status_code or '',
                    event.resource or '',
                    event.action or ''
                ]
                writer.writerow(row)
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Initialize global audit logger
audit_logger = AuditLogger()
