"""
Referral models for CineAI Bot
Supports both MongoDB and PostgreSQL backends
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator

from models.base import BaseDocument


class ReferralStatus(str, Enum):
    """Referral status types"""
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    DISABLED = "disabled"


class ReferralRewardType(str, Enum):
    """Referral reward types"""
    PREMIUM_DAYS = "premium_days"
    DOWNLOAD_CREDITS = "download_credits"
    CUSTOM_FEATURE = "custom_feature"


class ReferralDocument(BaseDocument):
    """Referral document model for MongoDB"""
    code: str = Field(..., description="Unique referral code")
    owner_id: int = Field(..., description="Telegram ID of referral owner")
    referral_count: int = Field(0, description="Number of successful referrals")
    max_uses: Optional[int] = Field(None, description="Maximum uses (None = unlimited)")
    status: ReferralStatus = Field(ReferralStatus.ACTIVE, description="Referral status")
    reward_type: ReferralRewardType = Field(ReferralRewardType.PREMIUM_DAYS, description="Reward type")
    reward_value: int = Field(7, description="Reward value (e.g., days of premium)")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    referred_users: List[int] = Field(default_factory=list, description="List of referred user IDs")
    click_count: int = Field(0, description="Number of times referral link was clicked")
    conversion_count: int = Field(0, description="Number of successful conversions")
    custom_message: Optional[str] = Field(None, description="Custom referral message")
    auto_grant_premium: bool = Field(True, description="Auto-grant premium to referrer")
    premium_granted: bool = Field(False, description="Premium granted to referrer")
    premium_granted_at: Optional[datetime] = Field(None, description="When premium was granted")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_by: Optional[int] = Field(None, description="Admin who created referral")
    notes: Optional[str] = Field(None, description="Admin notes")

    @validator('code')
    def validate_code(cls, v):
        if not v or len(v) < 4:
            raise ValueError('Referral code must be at least 4 characters')
        return v.upper()

    @validator('owner_id')
    def validate_owner_id(cls, v):
        if v <= 0:
            raise ValueError('Owner ID must be positive')
        return v

    @validator('referral_count', 'max_uses', 'reward_value', 'click_count', 'conversion_count')
    def validate_counts(cls, v):
        if v is not None and v < 0:
            raise ValueError('Counts cannot be negative')
        return v

    @validator('referred_users')
    def validate_referred_users(cls, v):
        if v and len(v) != len(set(v)):
            raise ValueError('Duplicate user IDs in referred users')
        return v

    @property
    def is_active(self) -> bool:
        """Check if referral is active"""
        if self.status != ReferralStatus.ACTIVE:
            return False

        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False

        if self.max_uses and self.referral_count >= self.max_uses:
            return False

        return True

    @property
    def can_be_used(self) -> bool:
        """Check if referral can be used"""
        return self.is_active

    @property
    def conversion_rate(self) -> float:
        """Calculate conversion rate"""
        if self.click_count == 0:
            return 0.0
        return (self.conversion_count / self.click_count) * 100

    @property
    def remaining_uses(self) -> Optional[int]:
        """Get remaining uses"""
        if self.max_uses is None:
            return None
        return max(0, self.max_uses - self.referral_count)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return self.dict(exclude_none=True)


class ReferralSQL(BaseModel):
    """Referral model for SQLAlchemy (PostgreSQL)"""
    __tablename__ = "referrals"

    # Primary fields
    id: Optional[int] = Field(None, primary_key=True)
    code: str = Field(..., max_length=20, unique=True)
    owner_id: int = Field(...)
    referral_count: int = Field(0)
    max_uses: Optional[int] = Field(None)
    status: ReferralStatus = Field(ReferralStatus.ACTIVE)
    reward_type: ReferralRewardType = Field(ReferralRewardType.PREMIUM_DAYS)
    reward_value: int = Field(7)
    expires_at: Optional[datetime] = Field(None)
    last_used_at: Optional[datetime] = Field(None)
    click_count: int = Field(0)
    conversion_count: int = Field(0)
    custom_message: Optional[str] = Field(None, max_length=500)
    auto_grant_premium: bool = Field(True)
    premium_granted: bool = Field(False)
    premium_granted_at: Optional[datetime] = Field(None)
    created_by: Optional[int] = Field(None, foreign_key="users.telegram_id")
    notes: Optional[str] = Field(None, max_length=1000)

    # JSON fields (stored as JSON in PostgreSQL)
    referred_users: List[int] = Field(default_factory=list)
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
        """Check if referral is active"""
        if self.status != ReferralStatus.ACTIVE:
            return False

        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False

        if self.max_uses and self.referral_count >= self.max_uses:
            return False

        return True

    @property
    def conversion_rate(self) -> float:
        """Calculate conversion rate"""
        if self.click_count == 0:
            return 0.0
        return (self.conversion_count / self.click_count) * 100


class ReferralCreate(BaseModel):
    """Model for creating a new referral"""
    code: str
    owner_id: int
    max_uses: Optional[int] = None
    reward_type: ReferralRewardType = ReferralRewardType.PREMIUM_DAYS
    reward_value: int = 7
    expires_at: Optional[datetime] = None
    custom_message: Optional[str] = None
    auto_grant_premium: bool = True
    created_by: Optional[int] = None


class ReferralUpdate(BaseModel):
    """Model for updating referral data"""
    max_uses: Optional[int] = None
    status: Optional[ReferralStatus] = None
    reward_type: Optional[ReferralRewardType] = None
    reward_value: Optional[int] = None
    expires_at: Optional[datetime] = None
    custom_message: Optional[str] = None
    auto_grant_premium: Optional[bool] = None
    premium_granted: Optional[bool] = None
    premium_granted_at: Optional[datetime] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ReferralResponse(BaseModel):
    """Model for referral response data"""
    id: Optional[int]
    code: str
    owner_id: int
    referral_count: int
    max_uses: Optional[int]
    status: ReferralStatus
    reward_type: ReferralRewardType
    reward_value: int
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    click_count: int
    conversion_count: int
    custom_message: Optional[str]
    auto_grant_premium: bool
    premium_granted: bool
    premium_granted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    conversion_rate: float
    remaining_uses: Optional[int]

    class Config:
        from_attributes = True


class ReferralUse(BaseModel):
    """Model for recording referral usage"""
    referral_code: str
    user_id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    granted_reward: bool = False
    reward_type: Optional[ReferralRewardType] = None
    reward_value: Optional[int] = None


class ReferralClick(BaseModel):
    """Model for recording referral clicks"""
    referral_code: str
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    referrer: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    converted: bool = False


class ReferralStats(BaseModel):
    """Referral statistics model"""
    total_referrals: int = 0
    active_referrals: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    average_conversion_rate: float = 0.0
    top_referrers: List[Dict[str, Any]] = Field(default_factory=list)
    referral_by_status: Dict[ReferralStatus, int] = Field(default_factory=dict)
    referral_by_reward_type: Dict[ReferralRewardType, int] = Field(default_factory=dict)
    total_premium_granted: int = 0
    clicks_today: int = 0
    conversions_today: int = 0
    clicks_this_week: int = 0
    conversions_this_week: int = 0


class UserReferralInfo(BaseModel):
    """User referral information"""
    user_id: int
    referral_code: Optional[str] = None
    referral_count: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    premium_granted: bool = False
    premium_granted_at: Optional[datetime] = None
    referred_by: Optional[int] = None
    referral_used_at: Optional[datetime] = None
    pending_rewards: int = 0


class ReferralReward(BaseModel):
    """Referral reward model"""
    referral_code: str
    referrer_id: int
    referred_user_id: int
    reward_type: ReferralRewardType
    reward_value: int
    granted_at: datetime
    expires_at: Optional[datetime] = None
    is_used: bool = False
    used_at: Optional[datetime] = None
    notes: Optional[str] = None


class ReferralSearchFilters(BaseModel):
    """Filters for searching referrals"""
    owner_id: Optional[int] = None
    status: Optional[ReferralStatus] = None
    reward_type: Optional[ReferralRewardType] = None
    is_active: Optional[bool] = None
    created_by: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    expires_after: Optional[datetime] = None
    expires_before: Optional[datetime] = None
    min_referral_count: Optional[int] = None
    max_referral_count: Optional[int] = None
    has_referrer: Optional[bool] = None