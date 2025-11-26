"""
User models for CineAI Bot
Supports both MongoDB and PostgreSQL backends
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator
from pydantic.types import conint

from models.base import BaseDocument, UserRole, UserStats


class UserStatus(str, Enum):
    """User status types"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    RESTRICTED = "restricted"


class UserDocument(BaseDocument):
    """User document model for MongoDB"""
    telegram_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    is_bot: bool = Field(False, description="Whether user is a bot")
    is_premium: bool = Field(False, description="Premium status")
    premium_expires: Optional[datetime] = Field(None, description="Premium expiration date")
    language_code: Optional[str] = Field(None, description="User's language code")
    role: UserRole = Field(UserRole.USER, description="User role")
    status: UserStatus = Field(UserStatus.ACTIVE, description="User status")
    referral_code: Optional[str] = Field(None, description="User's referral code")
    referred_by: Optional[int] = Field(None, description="ID of user who referred this user")
    referral_count: int = Field(0, description="Number of successful referrals")
    stats: UserStats = Field(default_factory=UserStats, description="User statistics")
    settings: Dict[str, Any] = Field(default_factory=dict, description="User-specific settings")
    last_seen: datetime = Field(default_factory=datetime.utcnow, description="Last activity timestamp")
    is_verified: bool = Field(False, description="Verification status")
    verification_token: Optional[str] = Field(None, description="Verification token")
    banned_until: Optional[datetime] = Field(None, description="Ban expiration date")
    ban_reason: Optional[str] = Field(None, description="Reason for ban")
    notes: Optional[str] = Field(None, description="Admin notes about user")

    @validator('telegram_id')
    def validate_telegram_id(cls, v):
        if v <= 0:
            raise ValueError('Telegram ID must be positive')
        return v

    @validator('username')
    def validate_username(cls, v):
        if v and not v.startswith('@'):
            v = '@' + v
        return v

    @validator('referral_code')
    def validate_referral_code(cls, v):
        if v and len(v) != 8:
            raise ValueError('Referral code must be 8 characters')
        return v

    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or str(self.telegram_id)

    @property
    def is_active(self) -> bool:
        """Check if user is active"""
        return self.status == UserStatus.ACTIVE

    @property
    def is_banned(self) -> bool:
        """Check if user is banned"""
        if self.status == UserStatus.BANNED:
            return True
        if self.banned_until and datetime.utcnow() < self.banned_until:
            return True
        return False

    @property
    def is_premium_active(self) -> bool:
        """Check if premium is active"""
        if not self.is_premium:
            return False
        if not self.premium_expires:
            return True
        return datetime.utcnow() < self.premium_expires

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return self.dict(exclude_none=True)

    @classmethod
    def from_telegram_user(cls, telegram_user, referral_code: Optional[str] = None, referred_by: Optional[int] = None):
        """Create user document from Telegram user object"""
        return cls(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            is_bot=telegram_user.is_bot,
            is_premium=getattr(telegram_user, 'is_premium', False),
            language_code=telegram_user.language_code,
            referral_code=referral_code,
            referred_by=referred_by
        )


class UserSQL(BaseModel):
    """User model for SQLAlchemy (PostgreSQL)"""
    __tablename__ = "users"

    # Primary fields
    telegram_id: int = Field(..., primary_key=True)
    username: Optional[str] = Field(None, max_length=255)
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    is_bot: bool = Field(False)
    is_premium: bool = Field(False)
    premium_expires: Optional[datetime] = Field(None)
    language_code: Optional[str] = Field(None, max_length=10)
    role: UserRole = Field(UserRole.USER)
    status: UserStatus = Field(UserStatus.ACTIVE)
    referral_code: Optional[str] = Field(None, max_length=8, unique=True)
    referred_by: Optional[int] = Field(None, foreign_key="users.telegram_id")
    referral_count: int = Field(0)

    # JSON fields (stored as JSON in PostgreSQL)
    stats: UserStats = Field(default_factory=UserStats)
    settings: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)

    # Verification and moderation
    is_verified: bool = Field(False)
    verification_token: Optional[str] = Field(None, max_length=255)
    banned_until: Optional[datetime] = Field(None)
    ban_reason: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or str(self.telegram_id)

    @property
    def is_active(self) -> bool:
        """Check if user is active"""
        return self.status == UserStatus.ACTIVE

    @property
    def is_banned(self) -> bool:
        """Check if user is banned"""
        if self.status == UserStatus.BANNED:
            return True
        if self.banned_until and datetime.utcnow() < self.banned_until:
            return True
        return False

    @property
    def is_premium_active(self) -> bool:
        """Check if premium is active"""
        if not self.is_premium:
            return False
        if not self.premium_expires:
            return True
        return datetime.utcnow() < self.premium_expires


class UserCreate(BaseModel):
    """Model for creating a new user"""
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_bot: bool = False
    is_premium: bool = False
    language_code: Optional[str] = None
    referral_code: Optional[str] = None
    referred_by: Optional[int] = None


class UserUpdate(BaseModel):
    """Model for updating user data"""
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_premium: Optional[bool] = None
    premium_expires: Optional[datetime] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    referral_code: Optional[str] = None
    referral_count: Optional[int] = None
    settings: Optional[Dict[str, Any]] = None
    is_verified: Optional[bool] = None
    verification_token: Optional[str] = None
    banned_until: Optional[datetime] = None
    ban_reason: Optional[str] = None
    notes: Optional[str] = None


class UserResponse(BaseModel):
    """Model for user response data"""
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_premium: bool
    premium_expires: Optional[datetime]
    role: UserRole
    status: UserStatus
    referral_code: Optional[str]
    referral_count: int
    stats: UserStats
    created_at: datetime
    last_seen: datetime
    is_verified: bool
    is_banned: bool
    is_premium_active: bool

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """User profile for display"""
    telegram_id: int
    full_name: str
    username: Optional[str]
    is_premium: bool
    premium_expires: Optional[datetime]
    role: UserRole
    status: UserStatus
    referral_code: Optional[str]
    referral_count: int
    stats: UserStats
    joined_at: datetime
    last_active: datetime

    class Config:
        from_attributes = True


class UserStatsUpdate(BaseModel):
    """Model for updating user statistics"""
    action_type: str  # 'search', 'download', 'upload', etc.
    metadata: Optional[Dict[str, Any]] = None


class UserBan(BaseModel):
    """Model for banning a user"""
    user_id: int
    reason: Optional[str] = None
    duration_days: Optional[int] = None  # None for permanent ban
    banned_by: int


class UserPremiumGrant(BaseModel):
    """Model for granting premium to a user"""
    user_id: int
    duration_days: int
    granted_by: int
    reason: Optional[str] = None


class UserVerification(BaseModel):
    """Model for user verification"""
    user_id: int
    token: str
    expires_at: datetime
    verified_by: Optional[int] = None


# Search filters for user queries
class UserSearchFilters(BaseModel):
    """Filters for searching users"""
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_premium: Optional[bool] = None
    is_verified: Optional[bool] = None
    referral_count_min: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    last_active_after: Optional[datetime] = None
    last_active_before: Optional[datetime] = None