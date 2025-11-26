"""
File models for CineAI Bot
Supports both MongoDB and PostgreSQL backends
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator
from pydantic.types import conint

from models.base import BaseDocument, FileType, QualityType, LanguageType


class FileSource(str, Enum):
    """File source types"""
    CHANNEL = "channel"
    USER_UPLOAD = "user_upload"
    ADMIN_UPLOAD = "admin_upload"
    IMPORT = "import"


class FileStatus(str, Enum):
    """File status types"""
    ACTIVE = "active"
    PROCESSING = "processing"
    DELETED = "deleted"
    HIDDEN = "hidden"
    RESTRICTED = "restricted"


class FileDocument(BaseDocument):
    """File document model for MongoDB"""
    message_id: int = Field(..., description="Original message ID")
    chat_id: int = Field(..., description="Source chat ID")
    file_id: str = Field(..., description="Telegram file ID")
    file_type: FileType = Field(..., description="Type of file")
    file_name: Optional[str] = Field(None, description="Original file name")
    file_size: int = Field(0, description="File size in bytes")
    title: str = Field(..., description="Content title")
    alt_titles: List[str] = Field(default_factory=list, description="Alternative titles")
    description: Optional[str] = Field(None, description="File description")
    imdb_id: Optional[str] = Field(None, description="IMDB ID (e.g., tt1234567)")
    year: Optional[int] = Field(None, description="Release year")
    season: Optional[int] = Field(None, description="Season number (for series)")
    episode: Optional[int] = Field(None, description="Episode number (for series)")
    quality: Optional[QualityType] = Field(None, description="Video quality")
    language: Optional[LanguageType] = Field(None, description="Content language")
    duration: Optional[int] = Field(None, description="Duration in seconds")
    resolution: Optional[str] = Field(None, description="Video resolution (e.g., 1920x1080)")
    codec: Optional[str] = Field(None, description="Video codec")
    tags: List[str] = Field(default_factory=list, description="Search tags")
    genre: List[str] = Field(default_factory=list, description="Content genres")
    cast: List[str] = Field(default_factory=list, description="Cast members")
    director: Optional[str] = Field(None, description="Director name")
    rating: Optional[float] = Field(None, description="Content rating (0-10)")
    thumbnail_id: Optional[str] = Field(None, description="Thumbnail file ID")
    thumbnails: List[str] = Field(default_factory=list, description="Additional thumbnail IDs")
    source: FileSource = Field(FileSource.CHANNEL, description="File source")
    status: FileStatus = Field(FileStatus.ACTIVE, description="File status")
    uploaded_by: Optional[int] = Field(None, description="User who uploaded (if not from channel)")
    indexed_by: Optional[int] = Field(None, description="User who indexed the file")
    short_url: Optional[str] = Field(None, description="Shortened URL")
    stream_url: Optional[str] = Field(None, description="Stream URL")
    download_count: int = Field(0, description="Number of downloads")
    view_count: int = Field(0, description="Number of views")
    clones_count: int = Field(0, description="Number of clones")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    auto_delete: bool = Field(False, description="Auto-delete enabled")
    auto_delete_after: Optional[int] = Field(None, description="Auto-delete TTL in seconds")
    is_premium: bool = Field(False, description="Premium-only content")
    verification_required: bool = Field(False, description="Verification required")
    verification_token: Optional[str] = Field(None, description="Verification token")
    notes: Optional[str] = Field(None, description="Admin notes")

    @validator('message_id')
    def validate_message_id(cls, v):
        if v <= 0:
            raise ValueError('Message ID must be positive')
        return v

    @validator('chat_id')
    def validate_chat_id(cls, v):
        if v <= 0:
            raise ValueError('Chat ID must be positive')
        return v

    @validator('file_size')
    def validate_file_size(cls, v):
        if v < 0:
            raise ValueError('File size cannot be negative')
        return v

    @validator('year')
    def validate_year(cls, v):
        if v and (v < 1900 or v > datetime.utcnow().year + 5):
            raise ValueError('Invalid year')
        return v

    @validator('rating')
    def validate_rating(cls, v):
        if v is not None and (v < 0 or v > 10):
            raise ValueError('Rating must be between 0 and 10')
        return v

    @validator('season', 'episode')
    def validate_season_episode(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Season and episode must be positive')
        return v

    @validator('imdb_id')
    def validate_imdb_id(cls, v):
        if v and not v.startswith('tt'):
            raise ValueError('IMDB ID must start with tt')
        return v

    @property
    def is_series(self) -> bool:
        """Check if file is a series episode"""
        return self.season is not None and self.episode is not None

    @property
    def is_expired(self) -> bool:
        """Check if file has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def display_title(self) -> str:
        """Get formatted display title"""
        if self.is_series:
            return f"{self.title} S{self.season:02d}E{self.episode:02d}"
        return f"{self.title} ({self.year})" if self.year else self.title

    @property
    def search_text(self) -> str:
        """Get searchable text combining all relevant fields"""
        parts = [self.title]
        parts.extend(self.alt_titles)
        parts.extend(self.tags)
        parts.extend(self.genre)
        parts.extend(self.cast)

        if self.director:
            parts.append(self.director)

        if self.year:
            parts.append(str(self.year))

        return " ".join(parts).lower()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return self.dict(exclude_none=True)


class FileSQL(BaseModel):
    """File model for SQLAlchemy (PostgreSQL)"""
    __tablename__ = "files"

    # Primary fields
    id: Optional[int] = Field(None, primary_key=True)
    message_id: int = Field(...)
    chat_id: int = Field(...)
    file_id: str = Field(...)
    file_type: FileType = Field(...)
    file_name: Optional[str] = Field(None, max_length=500)
    file_size: int = Field(0)
    title: str = Field(..., max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    imdb_id: Optional[str] = Field(None, max_length=20)
    year: Optional[int] = Field(None)
    season: Optional[int] = Field(None)
    episode: Optional[int] = Field(None)
    quality: Optional[QualityType] = Field(None)
    language: Optional[LanguageType] = Field(None)
    duration: Optional[int] = Field(None)
    resolution: Optional[str] = Field(None, max_length=20)
    codec: Optional[str] = Field(None, max_length=50)
    source: FileSource = Field(FileSource.CHANNEL)
    status: FileStatus = Field(FileStatus.ACTIVE)
    uploaded_by: Optional[int] = Field(None, foreign_key="users.telegram_id")
    indexed_by: Optional[int] = Field(None, foreign_key="users.telegram_id")
    short_url: Optional[str] = Field(None, max_length=100)
    stream_url: Optional[str] = Field(None, max_length=500)
    download_count: int = Field(0)
    view_count: int = Field(0)
    clones_count: int = Field(0)
    last_accessed: Optional[datetime] = Field(None)
    expires_at: Optional[datetime] = Field(None)
    auto_delete: bool = Field(False)
    auto_delete_after: Optional[int] = Field(None)
    is_premium: bool = Field(False)
    verification_required: bool = Field(False)
    verification_token: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=1000)

    # JSON fields (stored as JSON in PostgreSQL)
    alt_titles: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    genre: List[str] = Field(default_factory=list)
    cast: List[str] = Field(default_factory=list)
    thumbnails: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Additional fields
    director: Optional[str] = Field(None, max_length=200)
    rating: Optional[float] = Field(None)
    thumbnail_id: Optional[str] = Field(None, max_length=255)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @property
    def is_series(self) -> bool:
        """Check if file is a series episode"""
        return self.season is not None and self.episode is not None

    @property
    def display_title(self) -> str:
        """Get formatted display title"""
        if self.is_series:
            return f"{self.title} S{self.season:02d}E{self.episode:02d}"
        return f"{self.title} ({self.year})" if self.year else self.title


class FileCreate(BaseModel):
    """Model for creating a new file"""
    message_id: int
    chat_id: int
    file_id: str
    file_type: FileType
    file_name: Optional[str] = None
    file_size: int = 0
    title: str
    description: Optional[str] = None
    imdb_id: Optional[str] = None
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    quality: Optional[QualityType] = None
    language: Optional[LanguageType] = None
    duration: Optional[int] = None
    resolution: Optional[str] = None
    codec: Optional[str] = None
    source: FileSource = FileSource.CHANNEL
    uploaded_by: Optional[int] = None
    indexed_by: Optional[int] = None
    thumbnail_id: Optional[str] = None
    director: Optional[str] = None
    rating: Optional[float] = None
    alt_titles: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    genre: List[str] = Field(default_factory=list)
    cast: List[str] = Field(default_factory=list)
    thumbnails: List[str] = Field(default_factory=list)


class FileUpdate(BaseModel):
    """Model for updating file data"""
    title: Optional[str] = None
    description: Optional[str] = None
    imdb_id: Optional[str] = None
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    quality: Optional[QualityType] = None
    language: Optional[LanguageType] = None
    duration: Optional[int] = None
    resolution: Optional[str] = None
    codec: Optional[str] = None
    status: Optional[FileStatus] = None
    thumbnail_id: Optional[str] = None
    director: Optional[str] = None
    rating: Optional[float] = None
    alt_titles: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    genre: Optional[List[str]] = None
    cast: Optional[List[str]] = None
    thumbnails: Optional[List[str]] = None
    short_url: Optional[str] = None
    stream_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    auto_delete: Optional[bool] = None
    auto_delete_after: Optional[int] = None
    is_premium: Optional[bool] = None
    verification_required: Optional[bool] = None
    verification_token: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class FileResponse(BaseModel):
    """Model for file response data"""
    id: Optional[int]
    message_id: int
    chat_id: int
    file_id: str
    file_type: FileType
    file_name: Optional[str]
    file_size: int
    title: str
    description: Optional[str]
    imdb_id: Optional[str]
    year: Optional[int]
    season: Optional[int]
    episode: Optional[int]
    quality: Optional[QualityType]
    language: Optional[LanguageType]
    duration: Optional[int]
    resolution: Optional[str]
    codec: Optional[str]
    source: FileSource
    status: FileStatus
    short_url: Optional[str]
    stream_url: Optional[str]
    download_count: int
    view_count: int
    clones_count: int
    last_accessed: Optional[datetime]
    is_premium: bool
    verification_required: bool
    created_at: datetime
    updated_at: datetime
    display_title: str
    is_series: bool

    class Config:
        from_attributes = True


class FileSearchFilters(BaseModel):
    """Filters for searching files"""
    file_type: Optional[FileType] = None
    quality: Optional[QualityType] = None
    language: Optional[LanguageType] = None
    source: Optional[FileSource] = None
    status: Optional[FileStatus] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    genre: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_premium: Optional[bool] = None
    verification_required: Optional[bool] = None
    chat_id: Optional[int] = None
    uploaded_by: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    file_size_min: Optional[int] = None
    file_size_max: Optional[int] = None
    rating_min: Optional[float] = None
    rating_max: Optional[float] = None


class FileStats(BaseModel):
    """File statistics model"""
    total_files: int = 0
    total_size: int = 0
    files_by_type: Dict[FileType, int] = Field(default_factory=dict)
    files_by_quality: Dict[QualityType, int] = Field(default_factory=dict)
    files_by_language: Dict[LanguageType, int] = Field(default_factory=dict)
    files_by_source: Dict[FileSource, int] = Field(default_factory=dict)
    total_downloads: int = 0
    total_views: int = 0
    average_file_size: float = 0
    most_recent_file: Optional[datetime] = None
    oldest_file: Optional[datetime] = None


class FileMetadata(BaseModel):
    """Additional file metadata"""
    extraction_method: Optional[str] = None
    processing_time: Optional[float] = None
    original_filename: Optional[str] = None
    hash_md5: Optional[str] = None
    hash_sha1: Optional[str] = None
    encoding_info: Optional[Dict[str, Any]] = None
    stream_info: Optional[Dict[str, Any]] = None