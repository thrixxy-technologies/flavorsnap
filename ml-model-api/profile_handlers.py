"""
User Profile Management for FlavorSnap API
Implements comprehensive profile management with preferences, settings,
avatar management, and activity tracking
"""
import os
import uuid
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from PIL import Image
import io

from flask import request, jsonify

# Import user and security modules
from user_handlers import user_manager, User, UserRole, UserStatus
from security_config import InputValidator, SecurityConfig
from gdpr_compliance import GDPRCompliance


class NotificationPreference(Enum):
    """Notification preference types"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class PrivacyLevel(Enum):
    """Privacy level settings"""
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"


@dataclass
class UserProfile:
    """Extended user profile"""
    user_id: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    language: str = "en"
    timezone: str = "UTC"
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'display_name': self.display_name,
            'bio': self.bio,
            'avatar_url': self.avatar_url,
            'cover_image_url': self.cover_image_url,
            'location': self.location,
            'website': self.website,
            'social_links': self.social_links or {},
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'gender': self.gender,
            'language': self.language,
            'timezone': self.timezone,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


@dataclass
class UserPreferences:
    """User preferences and settings"""
    user_id: str
    notifications: Dict[str, bool] = None
    privacy: Dict[str, str] = None
    email_frequency: str = "daily"
    theme: str = "light"
    language: str = "en"
    timezone: str = "UTC"
    accessibility: Dict[str, Any] = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.notifications is None:
            self.notifications = {
                'email': True,
                'sms': False,
                'push': True,
                'in_app': True,
                'marketing': False
            }
        if self.privacy is None:
            self.privacy = {
                'profile_visibility': PrivacyLevel.PUBLIC.value,
                'email_visibility': PrivacyLevel.PRIVATE.value,
                'activity_visibility': PrivacyLevel.FRIENDS.value
            }
        if self.accessibility is None:
            self.accessibility = {
                'high_contrast': False,
                'large_text': False,
                'screen_reader': False
            }
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'notifications': self.notifications,
            'privacy': self.privacy,
            'email_frequency': self.email_frequency,
            'theme': self.theme,
            'language': self.language,
            'timezone': self.timezone,
            'accessibility': self.accessibility,
            'updated_at': self.updated_at.isoformat()
        }


@dataclass
class UserStatistics:
    """User statistics and metrics"""
    user_id: str
    total_predictions: int = 0
    total_uploads: int = 0
    total_api_calls: int = 0
    favorite_foods: List[str] = None
    most_active_day: Optional[str] = None
    most_active_hour: Optional[int] = None
    average_confidence: float = 0.0
    last_activity: Optional[datetime] = None
    
    def __post_init__(self):
        if self.favorite_foods is None:
            self.favorite_foods = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'total_predictions': self.total_predictions,
            'total_uploads': self.total_uploads,
            'total_api_calls': self.total_api_calls,
            'favorite_foods': self.favorite_foods,
            'most_active_day': self.most_active_day,
            'most_active_hour': self.most_active_hour,
            'average_confidence': self.average_confidence,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None
        }


class ProfileManager:
    """Comprehensive profile management system"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.profiles: Dict[str, UserProfile] = {}
        self.preferences: Dict[str, UserPreferences] = {}
        self.statistics: Dict[str, UserStatistics] = {}
        self.gdpr_compliance = GDPRCompliance()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize profile manager with Flask app"""
        self.app = app
        app.config.setdefault('AVATAR_UPLOAD_FOLDER', 'uploads/avatars')
        app.config.setdefault('COVER_UPLOAD_FOLDER', 'uploads/covers')
        
        # Create upload directories
        os.makedirs(app.config['AVATAR_UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['COVER_UPLOAD_FOLDER'], exist_ok=True)
    
    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile"""
        if user_id not in self.profiles:
            # Create default profile
            self.profiles[user_id] = UserProfile(user_id=user_id)
        
        return self.profiles[user_id]
    
    def update_profile(self, user_id: str, updates: Dict[str, Any]) -> Tuple[bool, Optional[UserProfile], Optional[str]]:
        """Update user profile"""
        user = user_manager.get_user(user_id)
        if not user:
            return False, None, "User not found"
        
        profile = self.get_profile(user_id)
        
        # Validate and apply updates
        if 'display_name' in updates:
            profile.display_name = InputValidator.sanitize_string(updates['display_name'], max_length=100)
        
        if 'bio' in updates:
            profile.bio = InputValidator.sanitize_string(updates['bio'], max_length=500)
        
        if 'location' in updates:
            profile.location = InputValidator.sanitize_string(updates['location'], max_length=100)
        
        if 'website' in updates:
            website = InputValidator.sanitize_url(updates['website'])
            if website:
                profile.website = website
        
        if 'social_links' in updates and isinstance(updates['social_links'], dict):
            sanitized_links = {}
            for platform, url in updates['social_links'].items():
                platform_clean = InputValidator.sanitize_string(platform, max_length=50)
                url_clean = InputValidator.sanitize_url(url)
                if platform_clean and url_clean:
                    sanitized_links[platform_clean] = url_clean
            profile.social_links = sanitized_links
        
        if 'date_of_birth' in updates:
            try:
                if isinstance(updates['date_of_birth'], str):
                    profile.date_of_birth = datetime.fromisoformat(updates['date_of_birth'])
                elif isinstance(updates['date_of_birth'], datetime):
                    profile.date_of_birth = updates['date_of_birth']
            except ValueError:
                pass
        
        if 'gender' in updates:
            profile.gender = InputValidator.sanitize_string(updates['gender'], max_length=20)
        
        if 'language' in updates:
            profile.language = InputValidator.sanitize_string(updates['language'], max_length=10)
        
        if 'timezone' in updates:
            profile.timezone = InputValidator.sanitize_string(updates['timezone'], max_length=50)
        
        profile.updated_at = datetime.now()
        
        # Log activity
        user_manager._log_activity(
            user_id=user_id,
            activity_type='profile_updated',
            activity_data={'fields': list(updates.keys())}
        )
        
        self.logger.info(f"Profile updated for user: {user_id}")
        return True, profile, None
    
    def upload_avatar(self, user_id: str, file) -> Tuple[bool, Optional[str], Optional[str]]:
        """Upload and process user avatar"""
        user = user_manager.get_user(user_id)
        if not user:
            return False, None, "User not found"
        
        # Validate file
        is_valid, error_msg = InputValidator.validate_file_upload(file)
        if not is_valid:
            return False, None, error_msg
        
        try:
            # Read and process image
            image_data = file.read()
            image = Image.open(io.BytesIO(image_data))
            
            # Resize to avatar size (256x256)
            avatar_size = (256, 256)
            image.thumbnail(avatar_size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Generate filename
            filename = f"{user_id}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join(self.app.config['AVATAR_UPLOAD_FOLDER'], filename)
            
            # Save image
            image.save(filepath, 'JPEG', quality=90, optimize=True)
            
            # Update profile
            profile = self.get_profile(user_id)
            avatar_url = f"/avatars/{filename}"
            profile.avatar_url = avatar_url
            profile.updated_at = datetime.now()
            
            # Log activity
            user_manager._log_activity(
                user_id=user_id,
                activity_type='avatar_uploaded',
                activity_data={'filename': filename}
            )
            
            self.logger.info(f"Avatar uploaded for user: {user_id}")
            return True, avatar_url, None
            
        except Exception as e:
            self.logger.error(f"Avatar upload error: {str(e)}")
            return False, None, "Failed to process avatar image"
    
    def upload_cover_image(self, user_id: str, file) -> Tuple[bool, Optional[str], Optional[str]]:
        """Upload and process cover image"""
        user = user_manager.get_user(user_id)
        if not user:
            return False, None, "User not found"
        
        # Validate file
        is_valid, error_msg = InputValidator.validate_file_upload(file)
        if not is_valid:
            return False, None, error_msg
        
        try:
            # Read and process image
            image_data = file.read()
            image = Image.open(io.BytesIO(image_data))
            
            # Resize to cover size (1200x400)
            cover_size = (1200, 400)
            
            # Calculate aspect ratio
            aspect = image.width / image.height
            target_aspect = cover_size[0] / cover_size[1]
            
            if aspect > target_aspect:
                # Image is wider, crop width
                new_width = int(image.height * target_aspect)
                left = (image.width - new_width) // 2
                image = image.crop((left, 0, left + new_width, image.height))
            else:
                # Image is taller, crop height
                new_height = int(image.width / target_aspect)
                top = (image.height - new_height) // 2
                image = image.crop((0, top, image.width, top + new_height))
            
            # Resize to target size
            image = image.resize(cover_size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Generate filename
            filename = f"{user_id}_{uuid.uuid4().hex[:8]}_cover.jpg"
            filepath = os.path.join(self.app.config['COVER_UPLOAD_FOLDER'], filename)
            
            # Save image
            image.save(filepath, 'JPEG', quality=90, optimize=True)
            
            # Update profile
            profile = self.get_profile(user_id)
            cover_url = f"/covers/{filename}"
            profile.cover_image_url = cover_url
            profile.updated_at = datetime.now()
            
            # Log activity
            user_manager._log_activity(
                user_id=user_id,
                activity_type='cover_uploaded',
                activity_data={'filename': filename}
            )
            
            self.logger.info(f"Cover image uploaded for user: {user_id}")
            return True, cover_url, None
            
        except Exception as e:
            self.logger.error(f"Cover upload error: {str(e)}")
            return False, None, "Failed to process cover image"
    
    def get_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences"""
        if user_id not in self.preferences:
            # Create default preferences
            self.preferences[user_id] = UserPreferences(user_id=user_id)
        
        return self.preferences[user_id]
    
    def update_preferences(self, user_id: str, updates: Dict[str, Any]) -> Tuple[bool, Optional[UserPreferences], Optional[str]]:
        """Update user preferences"""
        user = user_manager.get_user(user_id)
        if not user:
            return False, None, "User not found"
        
        preferences = self.get_preferences(user_id)
        
        # Update notifications
        if 'notifications' in updates and isinstance(updates['notifications'], dict):
            for key, value in updates['notifications'].items():
                if key in preferences.notifications and isinstance(value, bool):
                    preferences.notifications[key] = value
        
        # Update privacy settings
        if 'privacy' in updates and isinstance(updates['privacy'], dict):
            for key, value in updates['privacy'].items():
                if key in preferences.privacy and isinstance(value, str):
                    preferences.privacy[key] = value
        
        # Update other preferences
        if 'email_frequency' in updates:
            preferences.email_frequency = InputValidator.sanitize_string(updates['email_frequency'], max_length=20)
        
        if 'theme' in updates:
            preferences.theme = InputValidator.sanitize_string(updates['theme'], max_length=20)
        
        if 'language' in updates:
            preferences.language = InputValidator.sanitize_string(updates['language'], max_length=10)
        
        if 'timezone' in updates:
            preferences.timezone = InputValidator.sanitize_string(updates['timezone'], max_length=50)
        
        # Update accessibility settings
        if 'accessibility' in updates and isinstance(updates['accessibility'], dict):
            for key, value in updates['accessibility'].items():
                if key in preferences.accessibility and isinstance(value, bool):
                    preferences.accessibility[key] = value
        
        preferences.updated_at = datetime.now()
        
        # Log activity
        user_manager._log_activity(
            user_id=user_id,
            activity_type='preferences_updated',
            activity_data={'fields': list(updates.keys())}
        )
        
        self.logger.info(f"Preferences updated for user: {user_id}")
        return True, preferences, None
    
    def get_statistics(self, user_id: str) -> Optional[UserStatistics]:
        """Get user statistics"""
        if user_id not in self.statistics:
            # Create default statistics
            self.statistics[user_id] = UserStatistics(user_id=user_id)
        
        return self.statistics[user_id]
    
    def update_statistics(self, user_id: str, updates: Dict[str, Any]):
        """Update user statistics"""
        stats = self.get_statistics(user_id)
        
        if 'total_predictions' in updates:
            stats.total_predictions += updates['total_predictions']
        
        if 'total_uploads' in updates:
            stats.total_uploads += updates['total_uploads']
        
        if 'total_api_calls' in updates:
            stats.total_api_calls += updates['total_api_calls']
        
        if 'food_prediction' in updates:
            food = updates['food_prediction']
            if food not in stats.favorite_foods:
                stats.favorite_foods.append(food)
            # Keep only top 10
            if len(stats.favorite_foods) > 10:
                stats.favorite_foods = stats.favorite_foods[-10:]
        
        stats.last_activity = datetime.now()
    
    def get_complete_profile(self, user_id: str) -> Dict[str, Any]:
        """Get complete user profile with all information"""
        user = user_manager.get_user(user_id)
        if not user:
            return {}
        
        profile = self.get_profile(user_id)
        preferences = self.get_preferences(user_id)
        statistics = self.get_statistics(user_id)
        
        return {
            'user': user.to_dict(),
            'profile': profile.to_dict(),
            'preferences': preferences.to_dict(),
            'statistics': statistics.to_dict(),
            'permissions': user_manager.get_user_permissions(user_id)
        }
    
    def export_profile_data(self, user_id: str) -> Dict[str, Any]:
        """Export all profile data (GDPR compliance)"""
        complete_profile = self.get_complete_profile(user_id)
        
        # Get GDPR data export
        gdpr_export = self.gdpr_compliance.get_user_data_export(user_id)
        
        return {
            'profile_data': complete_profile,
            'gdpr_export': gdpr_export,
            'export_timestamp': datetime.now().isoformat()
        }
    
    def delete_profile_data(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """Delete all profile data (GDPR compliance)"""
        # Remove profile
        if user_id in self.profiles:
            del self.profiles[user_id]
        
        # Remove preferences
        if user_id in self.preferences:
            del self.preferences[user_id]
        
        # Remove statistics
        if user_id in self.statistics:
            del self.statistics[user_id]
        
        # Request GDPR data deletion
        self.gdpr_compliance.request_data_deletion(user_id, reason="User profile deletion")
        
        self.logger.info(f"Profile data deleted for user: {user_id}")
        return True, None


# Initialize global profile manager
profile_manager = ProfileManager()
