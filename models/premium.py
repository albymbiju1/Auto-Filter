"""
Premium models for CineAI Bot
Supports both MongoDB and PostgreSQL backends
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator

from models.base import BaseDocument


class PremiumPlan(str, Enum):
    """Premium plan types"""
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    VIP = "vip"
    LIFETIME = "lifetime"


class PremiumStatus(str, Enum):
    """Premium status types"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"
    PENDING = "pending"


class PaymentMethod(str, Enum):
    """Payment methods"""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    CRYPTO = "crypto"
    BANK_TRANSFER = "bank_transfer"
    REFERRAL = "referral"
    ADMIN_GRANT = "admin_grant"


class PremiumDocument(BaseDocument):
    """Premium document model for MongoDB"""
    user_id: int = Field(..., description="Telegram user ID")
    plan: PremiumPlan = Field(..., description="Premium plan")
    status: PremiumStatus = Field(PremiumStatus.ACTIVE, description="Premium status")
    starts_at: datetime = Field(..., description="Premium start date")
    expires_at: Optional[datetime] = Field(None, description="Premium expiration date")
    is_lifetime: bool = Field(False, description="Lifetime premium")
    payment_method: Optional[PaymentMethod] = Field(None, description="Payment method used")
    payment_id: Optional[str] = Field(None, description="Payment transaction ID")
    amount_paid: Optional[float] = Field(None, description="Amount paid")
    currency: str = Field("USD", description="Payment currency")
    auto_renew: bool = Field(False, description="Auto-renew subscription")
    cancelled_at: Optional[datetime] = Field(None, description="Cancellation date")
    cancel_reason: Optional[str] = Field(None, description="Cancellation reason")
    granted_by: Optional[int] = Field(None, description="Admin who granted premium")
    granted_reason: Optional[str] = Field(None, description="Reason for granting premium")
    features: List[str] = Field(default_factory=list, description="Enabled premium features")
    usage_limits: Dict[str, Any] = Field(default_factory=dict, description="Usage limits")
    current_usage: Dict[str, Any] = Field(default_factory=dict, description="Current usage")
    last_payment_at: Optional[datetime] = Field(None, description="Last payment date")
    next_billing_date: Optional[datetime] = Field(None, description="Next billing date")
    trial_used: bool = Field(False, description="Trial period used")
    trial_ends_at: Optional[datetime] = Field(None, description="Trial end date")
    subscription_id: Optional[str] = Field(None, description="Subscription ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    notes: Optional[str] = Field(None, description="Admin notes")

    @validator('user_id')
    def validate_user_id(cls, v):
        if v <= 0:
            raise ValueError('User ID must be positive')
        return v

    @validator('amount_paid')
    def validate_amount_paid(cls, v):
        if v is not None and v < 0:
            raise ValueError('Amount paid cannot be negative')
        return v

    @validator('starts_at')
    def validate_starts_at(cls, v):
        if v > datetime.utcnow():
            raise ValueError('Start date cannot be in the future')
        return v

    @validator('expires_at')
    def validate_expires_at(cls, v, values):
        if v and 'starts_at' in values and v <= values['starts_at']:
            raise ValueError('Expiration date must be after start date')
        return v

    @property
    def is_active(self) -> bool:
        """Check if premium is active"""
        if self.status != PremiumStatus.ACTIVE:
            return False

        if self.is_lifetime:
            return True

        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False

        return True

    @property
    def days_remaining(self) -> int:
        """Get days remaining in premium"""
        if self.is_lifetime:
            return -1  # Indicates lifetime

        if not self.expires_at:
            return 0

        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)

    @property
    def is_expired(self) -> bool:
        """Check if premium is expired"""
        if self.is_lifetime:
            return False
        return self.expires_at and datetime.utcnow() > self.expires_at

    @property
    def can_renew(self) -> bool:
        """Check if subscription can be renewed"""
        return (
            self.status in [PremiumStatus.ACTIVE, PremiumStatus.EXPIRED] and
            not self.is_lifetime and
            self.payment_method != PaymentMethod.ADMIN_GRANT
        )

    def has_feature(self, feature: str) -> bool:
        """Check if user has access to a specific feature"""
        return feature in self.features

    def check_usage_limit(self, feature: str, current_usage: int) -> bool:
        """Check if user is within usage limits"""
        limit = self.usage_limits.get(feature, float('inf'))
        return current_usage < limit

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return self.dict(exclude_none=True)


class PremiumSQL(BaseModel):
    """Premium model for SQLAlchemy (PostgreSQL)"""
    __tablename__ = "premium"

    # Primary fields
    id: Optional[int] = Field(None, primary_key=True)
    user_id: int = Field(..., unique=True)
    plan: PremiumPlan = Field(...)
    status: PremiumStatus = Field(PremiumStatus.ACTIVE)
    starts_at: datetime = Field(...)
    expires_at: Optional[datetime] = Field(None)
    is_lifetime: bool = Field(False)
    payment_method: Optional[PaymentMethod] = Field(None)
    payment_id: Optional[str] = Field(None, max_length=255)
    amount_paid: Optional[float] = Field(None)
    currency: str = Field("USD", max_length=3)
    auto_renew: bool = Field(False)
    cancelled_at: Optional[datetime] = Field(None)
    cancel_reason: Optional[str] = Field(None, max_length=500)
    granted_by: Optional[int] = Field(None, foreign_key="users.telegram_id")
    granted_reason: Optional[str] = Field(None, max_length=500)
    trial_used: bool = Field(False)
    trial_ends_at: Optional[datetime] = Field(None)
    subscription_id: Optional[str] = Field(None, max_length=255)
    last_payment_at: Optional[datetime] = Field(None)
    next_billing_date: Optional[datetime] = Field(None)
    notes: Optional[str] = Field(None, max_length=1000)

    # JSON fields (stored as JSON in PostgreSQL)
    features: List[str] = Field(default_factory=list)
    usage_limits: Dict[str, Any] = Field(default_factory=dict)
    current_usage: Dict[str, Any] = Field(default_factory=dict)
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
        """Check if premium is active"""
        if self.status != PremiumStatus.ACTIVE:
            return False

        if self.is_lifetime:
            return True

        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False

        return True

    @property
    def days_remaining(self) -> int:
        """Get days remaining in premium"""
        if self.is_lifetime:
            return -1  # Indicates lifetime

        if not self.expires_at:
            return 0

        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)


class PremiumCreate(BaseModel):
    """Model for creating a new premium subscription"""
    user_id: int
    plan: PremiumPlan
    starts_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_lifetime: bool = False
    payment_method: Optional[PaymentMethod] = None
    payment_id: Optional[str] = None
    amount_paid: Optional[float] = None
    currency: str = "USD"
    auto_renew: bool = False
    granted_by: Optional[int] = None
    granted_reason: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    usage_limits: Dict[str, Any] = Field(default_factory=dict)


class PremiumUpdate(BaseModel):
    """Model for updating premium data"""
    plan: Optional[PremiumPlan] = None
    status: Optional[PremiumStatus] = None
    expires_at: Optional[datetime] = None
    is_lifetime: Optional[bool] = None
    auto_renew: Optional[bool] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    features: Optional[List[str]] = None
    usage_limits: Optional[Dict[str, Any]] = None
    current_usage: Optional[Dict[str, Any]] = None
    last_payment_at: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None
    subscription_id: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PremiumResponse(BaseModel):
    """Model for premium response data"""
    id: Optional[int]
    user_id: int
    plan: PremiumPlan
    status: PremiumStatus
    starts_at: datetime
    expires_at: Optional[datetime]
    is_lifetime: bool
    payment_method: Optional[PaymentMethod]
    amount_paid: Optional[float]
    currency: str
    auto_renew: bool
    cancelled_at: Optional[datetime]
    cancel_reason: Optional[str]
    granted_by: Optional[int]
    granted_reason: Optional[str]
    features: List[str]
    usage_limits: Dict[str, Any]
    current_usage: Dict[str, Any]
    last_payment_at: Optional[datetime]
    next_billing_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    days_remaining: int
    is_expired: bool

    class Config:
        from_attributes = True


class PremiumPlanConfig(BaseModel):
    """Premium plan configuration"""
    plan: PremiumPlan
    name: str
    description: str
    price_monthly: Optional[float] = None
    price_yearly: Optional[float] = None
    price_lifetime: Optional[float] = None
    features: List[str]
    usage_limits: Dict[str, Any]
    trial_days: int = 0
    is_active: bool = True
    sort_order: int = 0


class PremiumTransaction(BaseModel):
    """Premium transaction model"""
    id: Optional[str] = None
    user_id: int
    premium_id: Optional[str] = None
    transaction_type: str  # payment, refund, grant, revoke
    amount: float
    currency: str = "USD"
    payment_method: PaymentMethod
    payment_id: Optional[str] = None
    status: str  # pending, completed, failed, refunded
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PremiumStats(BaseModel):
    """Premium statistics model"""
    total_premium_users: int = 0
    active_premium_users: int = 0
    expired_premium_users: int = 0
    lifetime_premium_users: int = 0
    total_revenue: float = 0.0
    revenue_this_month: float = 0.0
    revenue_this_year: float = 0.0
    premium_by_plan: Dict[PremiumPlan, int] = Field(default_factory=dict)
    premium_by_payment_method: Dict[PaymentMethod, int] = Field(default_factory=dict)
    churn_rate: float = 0.0
    average_subscription_length: float = 0.0
    trial_conversions: int = 0
    trial_conversion_rate: float = 0.0


class PremiumFeature(BaseModel):
    """Premium feature model"""
    name: str
    description: str
    required_plan: PremiumPlan
    is_enabled: bool = True
    usage_limit: Optional[int] = None
    reset_period: Optional[str] = None  # daily, weekly, monthly
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PremiumSearchFilters(BaseModel):
    """Filters for searching premium subscriptions"""
    user_id: Optional[int] = None
    plan: Optional[PremiumPlan] = None
    status: Optional[PremiumStatus] = None
    payment_method: Optional[PaymentMethod] = None
    is_lifetime: Optional[bool] = None
    auto_renew: Optional[bool] = None
    granted_by: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    expires_after: Optional[datetime] = None
    expires_before: Optional[datetime] = None
    has_feature: Optional[str] = None