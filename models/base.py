"""
Base models and database abstractions for CineAI Bot
Supports both MongoDB and SQLAlchemy (PostgreSQL) backends
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

# Type variables for generic models
T = TypeVar('T')


class DatabaseBackend(Enum):
    """Supported database backends"""
    MONGODB = "mongodb"
    POSTGRESQL = "postgresql"


class BaseDocument(BaseModel):
    """Base document model with common fields"""
    id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DatabaseService(ABC):
    """Abstract base class for database services"""

    @abstractmethod
    async def initialize(self):
        """Initialize database connection"""
        pass

    @abstractmethod
    async def close(self):
        """Close database connection"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check database health"""
        pass

    @abstractmethod
    async def create_indexes(self):
        """Create database indexes"""
        pass


class UserRepository(ABC, Generic[T]):
    """Abstract base class for user repositories"""

    @abstractmethod
    async def create_user(self, user_data: Dict[str, Any]) -> T:
        """Create a new user"""
        pass

    @abstractmethod
    async def get_user(self, user_id: int) -> Optional[T]:
        """Get user by ID"""
        pass

    @abstractmethod
    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> bool:
        """Update user data"""
        pass

    @abstractmethod
    async def delete_user(self, user_id: int) -> bool:
        """Delete user"""
        pass

    @abstractmethod
    async def get_all_users(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all users with pagination"""
        pass

    @abstractmethod
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        pass

    @abstractmethod
    async def update_user_stats(self, user_id: int, action: str):
        """Update user statistics"""
        pass


class FileRepository(ABC, Generic[T]):
    """Abstract base class for file repositories"""

    @abstractmethod
    async def create_file(self, file_data: Dict[str, Any]) -> T:
        """Create a new file record"""
        pass

    @abstractmethod
    async def get_file(self, file_id: str) -> Optional[T]:
        """Get file by ID"""
        pass

    @abstractmethod
    async def search_files(
        self,
        query: str,
        user_id: int,
        limit: int = 10,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """Search files with filters"""
        pass

    @abstractmethod
    async def get_recent_files(self, limit: int = 20, chat_id: Optional[int] = None) -> List[T]:
        """Get recent files"""
        pass

    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        """Delete file record"""
        pass

    @abstractmethod
    async def get_file_stats(self) -> Dict[str, Any]:
        """Get file statistics"""
        pass

    @abstractmethod
    async def cleanup_old_files(self, ttl_seconds: int) -> int:
        """Cleanup old files based on TTL"""
        pass


class ChannelRepository(ABC, Generic[T]):
    """Abstract base class for channel repositories"""

    @abstractmethod
    async def create_channel(self, channel_data: Dict[str, Any]) -> T:
        """Create a new channel record"""
        pass

    @abstractmethod
    async def get_channel(self, chat_id: int) -> Optional[T]:
        """Get channel by ID"""
        pass

    @abstractmethod
    async def update_channel(self, chat_id: int, update_data: Dict[str, Any]) -> bool:
        """Update channel data"""
        pass

    @abstractmethod
    async def get_all_channels(self) -> List[T]:
        """Get all channels"""
        pass

    @abstractmethod
    async def delete_channel(self, chat_id: int) -> bool:
        """Delete channel"""
        pass


class ReferralRepository(ABC, Generic[T]):
    """Abstract base class for referral repositories"""

    @abstractmethod
    async def create_referral(self, referral_data: Dict[str, Any]) -> T:
        """Create a new referral"""
        pass

    @abstractmethod
    async def get_referral(self, code: str) -> Optional[T]:
        """Get referral by code"""
        pass

    @abstractmethod
    async def get_user_referrals(self, user_id: int) -> List[T]:
        """Get user's referrals"""
        pass

    @abstractmethod
    async def update_referral(self, code: str, update_data: Dict[str, Any]) -> bool:
        """Update referral data"""
        pass


class SettingsRepository(ABC, Generic[T]):
    """Abstract base class for settings repositories"""

    @abstractmethod
    async def get_setting(self, key: str) -> Optional[T]:
        """Get setting by key"""
        pass

    @abstractmethod
    async def set_setting(self, key: str, value: Any) -> bool:
        """Set setting value"""
        pass

    @abstractmethod
    async def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings"""
        pass


class ShortUrlRepository(ABC, Generic[T]):
    """Abstract base class for short URL repositories"""

    @abstractmethod
    async def create_short_url(self, url_data: Dict[str, Any]) -> T:
        """Create a new short URL"""
        pass

    @abstractmethod
    async def get_short_url(self, slug: str) -> Optional[T]:
        """Get short URL by slug"""
        pass

    @abstractmethod
    async def get_user_short_urls(self, user_id: int) -> List[T]:
        """Get user's short URLs"""
        pass

    @abstractmethod
    async def cleanup_old_short_urls(self, days: int = 30) -> int:
        """Cleanup old short URLs"""
        pass


class DatabaseError(Exception):
    """Base exception for database operations"""
    pass


class ConnectionError(DatabaseError):
    """Database connection error"""
    pass


class ValidationError(DatabaseError):
    """Data validation error"""
    pass


class NotFoundError(DatabaseError):
    """Resource not found error"""
    pass


class DuplicateError(DatabaseError):
    """Duplicate resource error"""
    pass


# Common field types and validators
class QualityType(str, Enum):
    """File quality types"""
    HD = "HD"
    FHD = "FHD"
    SD = "SD"
    UHD = "4K"
    HDR = "HDR"


class LanguageType(str, Enum):
    """Content language types"""
    ENGLISH = "EN"
    HINDI = "HI"
    TAMIL = "TA"
    TELUGU = "TE"
    MALAYALAM = "ML"
    KANNADA = "KN"
    BENGALI = "BN"
    MARATHI = "MR"
    GUJARATI = "GJ"
    PUNJABI = "PB"


class FileType(str, Enum):
    """File types"""
    VIDEO = "video"
    DOCUMENT = "document"
    PHOTO = "photo"
    AUDIO = "audio"
    ANIMATION = "animation"


class UserRole(str, Enum):
    """User roles"""
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class SearchStats(BaseModel):
    """Search statistics model"""
    total_searches: int = 0
    successful_searches: int = 0
    failed_searches: int = 0
    last_search: Optional[datetime] = None
    popular_queries: List[str] = []


class DownloadStats(BaseModel):
    """Download statistics model"""
    total_downloads: int = 0
    files_downloaded: int = 0
    bytes_downloaded: int = 0
    last_download: Optional[datetime] = None


class UserStats(BaseModel):
    """Combined user statistics"""
    searches: SearchStats = Field(default_factory=SearchStats)
    downloads: DownloadStats = Field(default_factory=DownloadStats)
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)


class PaginationResult(GenericModel, Generic[T]):
    """Pagination result wrapper"""
    items: List[T]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


# Database connection configuration
class DatabaseConfig(BaseModel):
    """Database configuration model"""
    backend: DatabaseBackend
    connection_string: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False