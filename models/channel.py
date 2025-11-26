"""
Channel models for CineAI Bot
Supports both MongoDB and PostgreSQL backends
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator

from models.base import BaseDocument


class ChannelType(str, Enum):
    """Channel types"""
    PUBLIC = "public"
    PRIVATE = "private"
    SUPERGROUP = "supergroup"
    GROUP = "group"


class ChannelStatus(str, Enum):
    """Channel status types"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    RESTRICTED = "restricted"
    ARCHIVED = "archived"


class IndexMode(str, Enum):
    """Indexing modes"""
    AUTO = "auto"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    DISABLED = "disabled"


class ChannelDocument(BaseDocument):
    """Channel document model for MongoDB"""
    chat_id: int = Field(..., description="Telegram chat ID")
    title: str = Field(..., description="Channel title")
    username: Optional[str] = Field(None, description="Channel username")
    description: Optional[str] = Field(None, description="Channel description")
    channel_type: ChannelType = Field(..., description="Type of channel")
    status: ChannelStatus = Field(ChannelStatus.ACTIVE, description="Channel status")
    is_linked: bool = Field(True, description="Is linked for auto-indexing")
    index_mode: IndexMode = Field(IndexMode.AUTO, description="Indexing mode")
    last_indexed_message_id: int = Field(0, description="Last indexed message ID")
    total_indexed_messages: int = Field(0, description="Total indexed messages")
    total_files: int = Field(0, description="Total files indexed")
    last_indexed_at: Optional[datetime] = Field(None, description="Last indexing timestamp")
    indexing_interval: int = Field(30, description="Indexing interval in seconds")
    max_messages_per_batch: int = Field(100, description="Max messages to process per batch")
    file_types_to_index: List[str] = Field(
        default_factory=lambda: ["video", "document", "photo"],
        description="File types to index"
    )
    min_file_size: int = Field(0, description="Minimum file size to index (bytes)")
    max_file_size: int = Field(0, description="Maximum file size to index (0 = unlimited)")
    exclude_keywords: List[str] = Field(default_factory=list, description="Keywords to exclude")
    include_keywords: List[str] = Field(default_factory=list, description="Keywords to include")
    auto_delete_files: bool = Field(False, description="Auto-delete indexed files")
    auto_delete_after: int = Field(86400, description="Auto-delete TTL in seconds")
    is_premium_only: bool = Field(False, description="Premium-only channel")
    verification_required: bool = Field(False, description="Verification required for access")
    custom_welcome: Optional[str] = Field(None, description="Custom welcome message")
    added_by: Optional[int] = Field(None, description="Admin who added this channel")
    member_count: Optional[int] = Field(None, description="Channel member count")
    invite_link: Optional[str] = Field(None, description="Channel invite link")
    last_checked: Optional[datetime] = Field(None, description="Last channel check timestamp")
    indexing_enabled: bool = Field(True, description="Is indexing enabled")
    error_count: int = Field(0, description="Consecutive indexing errors")
    last_error: Optional[str] = Field(None, description="Last indexing error")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    notes: Optional[str] = Field(None, description="Admin notes")

    @validator('chat_id')
    def validate_chat_id(cls, v):
        if v <= 0:
            raise ValueError('Chat ID must be positive')
        return v

    @validator('title')
    def validate_title(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Title cannot be empty')
        return v.strip()

    @validator('username')
    def validate_username(cls, v):
        if v and not v.startswith('@'):
            v = '@' + v
        return v

    @validator('last_indexed_message_id', 'total_indexed_messages', 'total_files')
    def validate_counts(cls, v):
        if v < 0:
            raise ValueError('Counts cannot be negative')
        return v

    @validator('indexing_interval', 'max_messages_per_batch', 'min_file_size', 'max_file_size', 'auto_delete_after')
    def validate_positive_integers(cls, v):
        if v < 0:
            raise ValueError('Value must be non-negative')
        return v

    @property
    def is_active(self) -> bool:
        """Check if channel is active"""
        return self.status == ChannelStatus.ACTIVE

    @property
    def can_index(self) -> bool:
        """Check if channel can be indexed"""
        return (
            self.is_active and
            self.is_linked and
            self.indexing_enabled and
            self.index_mode != IndexMode.DISABLED
        )

    @property
    def display_name(self) -> str:
        """Get display name"""
        return self.username or self.title

    @property
    def needs_indexing(self) -> bool:
        """Check if channel needs indexing"""
        if not self.can_index:
            return False

        if self.last_indexed_at is None:
            return True

        time_diff = (datetime.utcnow() - self.last_indexed_at).seconds
        return time_diff >= self.indexing_interval

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return self.dict(exclude_none=True)


class ChannelSQL(BaseModel):
    """Channel model for SQLAlchemy (PostgreSQL)"""
    __tablename__ = "channels"

    # Primary fields
    id: Optional[int] = Field(None, primary_key=True)
    chat_id: int = Field(..., unique=True)
    title: str = Field(...)
    username: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    channel_type: ChannelType = Field(...)
    status: ChannelStatus = Field(ChannelStatus.ACTIVE)
    is_linked: bool = Field(True)
    index_mode: IndexMode = Field(IndexMode.AUTO)
    last_indexed_message_id: int = Field(0)
    total_indexed_messages: int = Field(0)
    total_files: int = Field(0)
    last_indexed_at: Optional[datetime] = Field(None)
    indexing_interval: int = Field(30)
    max_messages_per_batch: int = Field(100)
    min_file_size: int = Field(0)
    max_file_size: int = Field(0)
    auto_delete_files: bool = Field(False)
    auto_delete_after: int = Field(86400)
    is_premium_only: bool = Field(False)
    verification_required: bool = Field(False)
    custom_welcome: Optional[str] = Field(None, max_length=1000)
    added_by: Optional[int] = Field(None, foreign_key="users.telegram_id")
    member_count: Optional[int] = Field(None)
    invite_link: Optional[str] = Field(None, max_length=500)
    last_checked: Optional[datetime] = Field(None)
    indexing_enabled: bool = Field(True)
    error_count: int = Field(0)
    last_error: Optional[str] = Field(None, max_length=1000)
    notes: Optional[str] = Field(None, max_length=1000)

    # JSON fields (stored as JSON in PostgreSQL)
    file_types_to_index: List[str] = Field(
        default_factory=lambda: ["video", "document", "photo"]
    )
    exclude_keywords: List[str] = Field(default_factory=list)
    include_keywords: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @property
    def is_active(self) -> bool:
        """Check if channel is active"""
        return self.status == ChannelStatus.ACTIVE

    @property
    def can_index(self) -> bool:
        """Check if channel can be indexed"""
        return (
            self.is_active and
            self.is_linked and
            self.indexing_enabled and
            self.index_mode != IndexMode.DISABLED
        )

    @property
    def display_name(self) -> str:
        """Get display name"""
        return self.username or self.title


class ChannelCreate(BaseModel):
    """Model for creating a new channel"""
    chat_id: int
    title: str
    username: Optional[str] = None
    description: Optional[str] = None
    channel_type: ChannelType
    is_linked: bool = True
    index_mode: IndexMode = IndexMode.AUTO
    indexing_interval: int = 30
    max_messages_per_batch: int = 100
    file_types_to_index: List[str] = Field(default_factory=lambda: ["video", "document", "photo"])
    min_file_size: int = 0
    max_file_size: int = 0
    exclude_keywords: List[str] = Field(default_factory=list)
    include_keywords: List[str] = Field(default_factory=list)
    auto_delete_files: bool = False
    auto_delete_after: int = 86400
    is_premium_only: bool = False
    verification_required: bool = False
    custom_welcome: Optional[str] = None
    added_by: Optional[int] = None


class ChannelUpdate(BaseModel):
    """Model for updating channel data"""
    title: Optional[str] = None
    username: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ChannelStatus] = None
    is_linked: Optional[bool] = None
    index_mode: Optional[IndexMode] = None
    last_indexed_message_id: Optional[int] = None
    indexing_interval: Optional[int] = None
    max_messages_per_batch: Optional[int] = None
    file_types_to_index: Optional[List[str]] = None
    min_file_size: Optional[int] = None
    max_file_size: Optional[int] = None
    exclude_keywords: Optional[List[str]] = None
    include_keywords: Optional[List[str]] = None
    auto_delete_files: Optional[bool] = None
    auto_delete_after: Optional[int] = None
    is_premium_only: Optional[bool] = None
    verification_required: Optional[bool] = None
    custom_welcome: Optional[str] = None
    member_count: Optional[int] = None
    invite_link: Optional[str] = None
    indexing_enabled: Optional[bool] = None
    error_count: Optional[int] = None
    last_error: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChannelResponse(BaseModel):
    """Model for channel response data"""
    id: Optional[int]
    chat_id: int
    title: str
    username: Optional[str]
    description: Optional[str]
    channel_type: ChannelType
    status: ChannelStatus
    is_linked: bool
    index_mode: IndexMode
    last_indexed_message_id: int
    total_indexed_messages: int
    total_files: int
    last_indexed_at: Optional[datetime]
    indexing_interval: int
    max_messages_per_batch: int
    file_types_to_index: List[str]
    min_file_size: int
    max_file_size: int
    auto_delete_files: bool
    auto_delete_after: int
    is_premium_only: bool
    verification_required: bool
    custom_welcome: Optional[str]
    added_by: Optional[int]
    member_count: Optional[int]
    invite_link: Optional[str]
    last_checked: Optional[datetime]
    indexing_enabled: bool
    error_count: int
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime
    display_name: str
    can_index: bool

    class Config:
        from_attributes = True


class ChannelSearchFilters(BaseModel):
    """Filters for searching channels"""
    channel_type: Optional[ChannelType] = None
    status: Optional[ChannelStatus] = None
    is_linked: Optional[bool] = None
    index_mode: Optional[IndexMode] = None
    indexing_enabled: Optional[bool] = None
    is_premium_only: Optional[bool] = None
    verification_required: Optional[bool] = None
    added_by: Optional[int] = None
    member_count_min: Optional[int] = None
    member_count_max: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    last_indexed_after: Optional[datetime] = None
    last_indexed_before: Optional[datetime] = None


class ChannelStats(BaseModel):
    """Channel statistics model"""
    total_channels: int = 0
    active_channels: int = 0
    linked_channels: int = 0
    total_files: int = 0
    total_indexed_messages: int = 0
    channels_by_type: Dict[ChannelType, int] = Field(default_factory=dict)
    channels_by_status: Dict[ChannelStatus, int] = Field(default_factory=dict)
    channels_by_index_mode: Dict[IndexMode, int] = Field(default_factory=dict)
    average_files_per_channel: float = 0
    most_active_channel: Optional[str] = None
    least_active_channel: Optional[str] = None


class IndexingProgress(BaseModel):
    """Indexing progress model"""
    channel_id: int
    channel_title: str
    total_messages: int
    indexed_messages: int
    remaining_messages: int
    progress_percentage: float
    start_time: datetime
    estimated_completion: Optional[datetime] = None
    current_message_id: int
    files_found: int
    errors: List[str] = Field(default_factory=list)