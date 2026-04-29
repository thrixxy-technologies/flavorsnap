"""
PWA (Progressive Web App) offline functionality manager.

This module provides offline storage, caching, and synchronization capabilities
for the FlavorSnap PWA application.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

logger = logging.getLogger(__name__)


class OfflineManager:
    """Manages offline storage and synchronization for PWA functionality."""
    
    def __init__(self, storage_path: str = "offline_data.db"):
        """
        Initialize the offline manager.
        
        Args:
            storage_path: Path to the SQLite database for offline storage
        """
        self.storage_path = storage_path
        self.conn = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the SQLite database for offline storage."""
        try:
            self.conn = sqlite3.connect(self.storage_path)
            self.conn.execute("PRAGMA foreign_keys = ON")
            
            # Create tables for offline storage
            self._create_tables()
            logger.info("Offline storage initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize offline storage: {e}")
            raise
    
    def _create_tables(self):
        """Create necessary tables for offline storage."""
        cursor = self.conn.cursor()
        
        # Cache table for API responses and static content
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                etag TEXT,
                size_bytes INTEGER
            )
        """)
        
        # Offline queue for actions to sync when online
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                retry_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        # User preferences and settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Offline analytics data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                synced BOOLEAN DEFAULT FALSE
            )
        """)
        
        self.conn.commit()
    
    def cache_content(self, key: str, content: str, content_type: str, 
                     expires_in_hours: int = 24, etag: str = None) -> bool:
        """
        Cache content for offline access.
        
        Args:
            key: Unique cache key
            content: Content to cache
            content_type: MIME type of content
            expires_in_hours: Hours until cache expires
            etag: ETag for cache validation
            
        Returns:
            True if caching successful, False otherwise
        """
        try:
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
            size_bytes = len(content.encode('utf-8'))
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO cache 
                (key, content, content_type, expires_at, etag, size_bytes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (key, content, content_type, expires_at, etag, size_bytes))
            
            self.conn.commit()
            logger.debug(f"Cached content: {key} ({size_bytes} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache content {key}: {e}")
            return False
    
    def get_cached_content(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached content.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Dictionary with cached content metadata or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT content, content_type, timestamp, expires_at, etag, size_bytes
                FROM cache WHERE key = ? AND expires_at > datetime('now')
            """, (key,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'content': result[0],
                    'content_type': result[1],
                    'cached_at': result[2],
                    'expires_at': result[3],
                    'etag': result[4],
                    'size_bytes': result[5]
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve cached content {key}: {e}")
            return None
    
    def add_to_sync_queue(self, action_type: str, data: Dict[str, Any]) -> bool:
        """
        Add an action to the synchronization queue.
        
        Args:
            action_type: Type of action (e.g., 'upload', 'analysis', 'preference')
            data: Action data as JSON-serializable dictionary
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            data_json = json.dumps(data)
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO sync_queue (action_type, data)
                VALUES (?, ?)
            """, (action_type, data_json))
            
            self.conn.commit()
            logger.debug(f"Added to sync queue: {action_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add to sync queue: {e}")
            return False
    
    def get_sync_queue(self, status: str = 'pending') -> List[Dict[str, Any]]:
        """
        Get items from the synchronization queue.
        
        Args:
            status: Filter by status ('pending', 'synced', 'failed')
            
        Returns:
            List of sync queue items
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, action_type, data, timestamp, retry_count, status
                FROM sync_queue WHERE status = ?
                ORDER BY timestamp ASC
            """, (status,))
            
            items = []
            for row in cursor.fetchall():
                items.append({
                    'id': row[0],
                    'action_type': row[1],
                    'data': json.loads(row[2]),
                    'timestamp': row[3],
                    'retry_count': row[4],
                    'status': row[5]
                })
            
            return items
            
        except Exception as e:
            logger.error(f"Failed to get sync queue: {e}")
            return []
    
    def mark_synced(self, item_id: int, status: str = 'synced') -> bool:
        """
        Mark a sync queue item as synced or failed.
        
        Args:
            item_id: ID of the sync queue item
            status: New status ('synced', 'failed')
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE sync_queue 
                SET status = ?, timestamp = datetime('now')
                WHERE id = ?
            """, (status, item_id))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark sync item {item_id}: {e}")
            return False
    
    def store_preference(self, key: str, value: str) -> bool:
        """
        Store a user preference.
        
        Args:
            key: Preference key
            value: Preference value
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO preferences (key, value)
                VALUES (?, ?)
            """, (key, value))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to store preference {key}: {e}")
            return False
    
    def get_preference(self, key: str) -> Optional[str]:
        """
        Retrieve a user preference.
        
        Args:
            key: Preference key
            
        Returns:
            Preference value or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Failed to get preference {key}: {e}")
            return None
    
    def log_analytics_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        Log an analytics event for offline storage.
        
        Args:
            event_type: Type of analytics event
            data: Event data
            
        Returns:
            True if logged successfully, False otherwise
        """
        try:
            data_json = json.dumps(data)
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO analytics (event_type, data)
                VALUES (?, ?)
            """, (event_type, data_json))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log analytics event: {e}")
            return False
    
    def get_unsynced_analytics(self) -> List[Dict[str, Any]]:
        """
        Get unsynced analytics events.
        
        Returns:
            List of unsynced analytics events
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, event_type, data, timestamp
                FROM analytics WHERE synced = FALSE
                ORDER BY timestamp ASC
            """)
            
            events = []
            for row in cursor.fetchall():
                events.append({
                    'id': row[0],
                    'event_type': row[1],
                    'data': json.loads(row[2]),
                    'timestamp': row[3]
                })
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get unsynced analytics: {e}")
            return []
    
    def mark_analytics_synced(self, event_ids: List[int]) -> bool:
        """
        Mark analytics events as synced.
        
        Args:
            event_ids: List of event IDs to mark as synced
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            if not event_ids:
                return True
                
            placeholders = ','.join(['?' for _ in event_ids])
            cursor = self.conn.cursor()
            cursor.execute(f"""
                UPDATE analytics SET synced = TRUE
                WHERE id IN ({placeholders})
            """, event_ids)
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark analytics as synced: {e}")
            return False
    
    def cleanup_expired_cache(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of entries removed
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                DELETE FROM cache WHERE expires_at <= datetime('now')
            """)
            
            deleted_count = cursor.rowcount
            self.conn.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired cache entries")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired cache: {e}")
            return 0
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            cursor = self.conn.cursor()
            
            # Cache stats
            cursor.execute("SELECT COUNT(*), SUM(size_bytes) FROM cache")
            cache_count, cache_size = cursor.fetchone()
            
            # Sync queue stats
            cursor.execute("SELECT COUNT(*) FROM sync_queue WHERE status = 'pending'")
            pending_sync = cursor.fetchone()[0]
            
            # Analytics stats
            cursor.execute("SELECT COUNT(*) FROM analytics WHERE synced = FALSE")
            unsynced_analytics = cursor.fetchone()[0]
            
            return {
                'cache_entries': cache_count or 0,
                'cache_size_bytes': cache_size or 0,
                'pending_sync_items': pending_sync,
                'unsynced_analytics': unsynced_analytics,
                'storage_path': self.storage_path
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {}
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class PWAManager:
    """High-level PWA functionality manager."""
    
    def __init__(self, storage_path: str = "offline_data.db"):
        """
        Initialize PWA manager.
        
        Args:
            storage_path: Path to offline storage database
        """
        self.offline_manager = OfflineManager(storage_path)
        self.is_online = True
    
    def set_online_status(self, is_online: bool):
        """
        Set the online status of the application.
        
        Args:
            is_online: True if online, False if offline
        """
        self.is_online = is_online
        if is_online:
            self._sync_when_online()
    
    def _sync_when_online(self):
        """Attempt to sync pending items when coming back online."""
        try:
            # Get pending sync items
            pending_items = self.offline_manager.get_sync_queue('pending')
            
            for item in pending_items:
                success = self._process_sync_item(item)
                if success:
                    self.offline_manager.mark_synced(item['id'], 'synced')
                else:
                    self.offline_manager.mark_synced(item['id'], 'failed')
            
            # Sync analytics
            unsynced_events = self.offline_manager.get_unsynced_analytics()
            if unsynced_events:
                event_ids = [event['id'] for event in unsynced_events]
                self.offline_manager.mark_analytics_synced(event_ids)
            
            logger.info(f"Synced {len(pending_items)} items and {len(unsynced_events)} analytics events")
            
        except Exception as e:
            logger.error(f"Failed to sync when online: {e}")
    
    def _process_sync_item(self, item: Dict[str, Any]) -> bool:
        """
        Process a single sync queue item.
        
        Args:
            item: Sync queue item
            
        Returns:
            True if processed successfully, False otherwise
        """
        # This would integrate with the actual API endpoints
        # For now, we'll simulate successful processing
        action_type = item['action_type']
        
        if action_type == 'upload':
            return self._sync_upload(item['data'])
        elif action_type == 'analysis':
            return self._sync_analysis(item['data'])
        elif action_type == 'preference':
            return self._sync_preference(item['data'])
        else:
            logger.warning(f"Unknown sync action type: {action_type}")
            return False
    
    def _sync_upload(self, data: Dict[str, Any]) -> bool:
        """Sync an upload action."""
        # Integration with upload API would go here
        logger.info(f"Syncing upload: {data.get('filename', 'unknown')}")
        return True
    
    def _sync_analysis(self, data: Dict[str, Any]) -> bool:
        """Sync an analysis action."""
        # Integration with analysis API would go here
        logger.info(f"Syncing analysis: {data.get('image_id', 'unknown')}")
        return True
    
    def _sync_preference(self, data: Dict[str, Any]) -> bool:
        """Sync a preference action."""
        # Integration with preferences API would go here
        logger.info(f"Syncing preference: {data.get('key', 'unknown')}")
        return True
    
    def cache_api_response(self, endpoint: str, response_data: Any, 
                          expires_in_hours: int = 1) -> bool:
        """
        Cache an API response for offline access.
        
        Args:
            endpoint: API endpoint identifier
            response_data: Response data to cache
            expires_in_hours: Hours until cache expires
            
        Returns:
            True if cached successfully, False otherwise
        """
        key = f"api_{endpoint}"
        content = json.dumps(response_data)
        return self.offline_manager.cache_content(
            key, content, 'application/json', expires_in_hours
        )
    
    def get_cached_api_response(self, endpoint: str) -> Optional[Any]:
        """
        Get a cached API response.
        
        Args:
            endpoint: API endpoint identifier
            
        Returns:
            Cached response data or None if not found
        """
        key = f"api_{endpoint}"
        cached = self.offline_manager.get_cached_content(key)
        
        if cached:
            try:
                return json.loads(cached['content'])
            except json.JSONDecodeError:
                logger.error(f"Failed to decode cached API response for {endpoint}")
                return None
        
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current PWA status.
        
        Returns:
            Dictionary with PWA status information
        """
        stats = self.offline_manager.get_storage_stats()
        
        return {
            'is_online': self.is_online,
            'storage_stats': stats,
            'last_cleanup': datetime.now().isoformat()
        }
    
    def close(self):
        """Close the PWA manager."""
        self.offline_manager.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
