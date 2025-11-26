"""
Configuration module for CineAI AutoFilter Bot
Handles environment variables, feature toggles, and runtime settings
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class FeatureToggles(BaseModel):
    """Feature toggle configuration"""
    PM_SEARCH: bool = True
    AUTO_FILTER: bool = True
    INLINE_SEARCH: bool = True
    FORCE_SUBSCRIBE: bool = False
    PREMIUM: bool = False
    REFERRAL: bool = False
    STREAM: bool = False
    RENAME: bool = False
    CLONE: bool = False
    SPELL_CHECK: bool = True
    IMDB_INTEGRATION: bool = True
    URL_SHORTENER: bool = False
    MULTI_DB: bool = False


class DatabaseConfig(BaseModel):
    """Database configuration"""
    MONGO_URI: str
    PRIMARY_DB: str = "mongo"  # mongo only
    REDIS_URL: Optional[str] = None


class TelegramConfig(BaseModel):
    """Telegram bot configuration"""
    BOT_TOKEN: str
    API_ID: int
    API_HASH: str
    ADMIN_USER_IDS: List[int] = []
    SUPER_ADMIN_ID: Optional[int] = None

    @field_validator("API_ID", mode="before")
    @classmethod
    def parse_api_id(cls, v):
        if isinstance(v, str):
            return int(v)
        return v

    @field_validator("ADMIN_USER_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v


class ExternalAPIConfig(BaseModel):
    """External API configuration"""
    IMDB_API_KEY: Optional[str] = None
    SHORTENER_API_KEY: Optional[str] = None


class PaymentConfig(BaseModel):
    """Payment system configuration"""
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None


class BotSettings(BaseModel):
    """General bot settings"""
    LOG_LEVEL: str = "INFO"
    FILE_DELETE_TTL: int = 86400  # 24 hours
    MAX_FILE_SIZE_MB: int = 2000
    BROADCAST_CHUNK_SIZE: int = 50
    RATE_LIMIT_PER_USER: int = 30
    CACHE_TTL: int = 3600
    DEVELOPMENT: bool = False


class ForceSubscribeConfig(BaseModel):
    """Force subscribe configuration"""
    FORCE_SUBSCRIBE_CHANNELS: List[int] = []
    AUTO_APPROVE_JOINS: bool = True
    CUSTOM_WELCOME_MESSAGE: str = "Welcome to CineAI Bot! 🎬"
    CUSTOM_START_MESSAGE: str = "Hello! I'm your personal movie assistant. 🍿"
    CUSTOM_TUTORIAL_BUTTON: str = "How to use me?"

    @field_validator("FORCE_SUBSCRIBE_CHANNELS", mode="before")
    @classmethod
    def parse_force_subscribe_channels(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v




class Config(BaseSettings):
    """Main configuration class"""

    # Telegram Configuration
    BOT_TOKEN: str
    API_ID: int
    API_HASH: str
    ADMIN_USER_IDS: str = ""
    SUPER_ADMIN_ID: Optional[int] = None

    # Database Configuration
    MONGO_URI: str
    PRIMARY_DB: str = "mongo"
    REDIS_URL: Optional[str] = None

    # Feature Toggles
    FEATURE_TOGGLES: str = "{}"

    # External API Configuration
    IMDB_API_KEY: Optional[str] = None
    SHORTENER_API_KEY: Optional[str] = None

    # Payment Configuration
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None

    # Bot Settings
    LOG_LEVEL: str = "INFO"
    FILE_DELETE_TTL: int = 86400
    MAX_FILE_SIZE_MB: int = 2000
    BROADCAST_CHUNK_SIZE: int = 50
    RATE_LIMIT_PER_USER: int = 30
    CACHE_TTL: int = 3600
    DEVELOPMENT: bool = False

    # Force Subscribe Settings
    FORCE_SUBSCRIBE_CHANNELS: str = ""
    AUTO_APPROVE_JOINS: str = "true"
    CUSTOM_WELCOME_MESSAGE: str = "Welcome to CineAI Bot! 🎬"
    CUSTOM_START_MESSAGE: str = "Hello! I'm your personal movie assistant. 🍿"
    CUSTOM_TUTORIAL_BUTTON: str = "How to use me?"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"  # Changed from "forbid" to "ignore" for cloud deployments
    }

    @field_validator("API_ID", mode="before")
    @classmethod
    def parse_api_id(cls, v):
        if isinstance(v, str):
            return int(v)
        return v

    @field_validator("SUPER_ADMIN_ID", mode="before")
    @classmethod
    def parse_super_admin_id(cls, v):
        if isinstance(v, str) and v.strip():
            return int(v)
        return None

    @field_validator("FILE_DELETE_TTL", "MAX_FILE_SIZE_MB", "BROADCAST_CHUNK_SIZE", "RATE_LIMIT_PER_USER", "CACHE_TTL", mode="before")
    @classmethod
    def parse_int_fields(cls, v):
        if isinstance(v, str):
            return int(v)
        return v

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment variables"""
        return cls()

    @property
    def telegram(self) -> TelegramConfig:
        admin_ids = []
        if self.ADMIN_USER_IDS:
            admin_ids = [int(x.strip()) for x in self.ADMIN_USER_IDS.split(",") if x.strip()]

        return TelegramConfig(
            BOT_TOKEN=self.BOT_TOKEN,
            API_ID=self.API_ID,
            API_HASH=self.API_HASH,
            ADMIN_USER_IDS=admin_ids,
            SUPER_ADMIN_ID=self.SUPER_ADMIN_ID
        )

    @property
    def database(self) -> DatabaseConfig:
        return DatabaseConfig(
            MONGO_URI=self.MONGO_URI,
            PRIMARY_DB=self.PRIMARY_DB,
            REDIS_URL=self.REDIS_URL
        )

    @property
    def features(self) -> FeatureToggles:
        try:
            features_data = json.loads(self.FEATURE_TOGGLES)
            return FeatureToggles(**features_data)
        except json.JSONDecodeError:
            logging.error("Invalid JSON in FEATURE_TOGGLES, using defaults")
            return FeatureToggles()

    @property
    def external_apis(self) -> ExternalAPIConfig:
        return ExternalAPIConfig(
            IMDB_API_KEY=self.IMDB_API_KEY,
            SHORTENER_API_KEY=self.SHORTENER_API_KEY
        )

    @property
    def payment(self) -> PaymentConfig:
        return PaymentConfig(
            PAYPAL_CLIENT_ID=self.PAYPAL_CLIENT_ID,
            PAYPAL_CLIENT_SECRET=self.PAYPAL_CLIENT_SECRET
        )

    @property
    def bot_settings(self) -> BotSettings:
        return BotSettings(
            LOG_LEVEL=self.LOG_LEVEL,
            FILE_DELETE_TTL=self.FILE_DELETE_TTL,
            MAX_FILE_SIZE_MB=self.MAX_FILE_SIZE_MB,
            BROADCAST_CHUNK_SIZE=self.BROADCAST_CHUNK_SIZE,
            RATE_LIMIT_PER_USER=self.RATE_LIMIT_PER_USER,
            CACHE_TTL=self.CACHE_TTL,
            DEVELOPMENT=self.DEVELOPMENT
        )

    @property
    def force_subscribe(self) -> ForceSubscribeConfig:
        channels = []
        if self.FORCE_SUBSCRIBE_CHANNELS:
            channels = [int(x.strip()) for x in self.FORCE_SUBSCRIBE_CHANNELS.split(",") if x.strip()]

        return ForceSubscribeConfig(
            FORCE_SUBSCRIBE_CHANNELS=channels,
            AUTO_APPROVE_JOINS=self.AUTO_APPROVE_JOINS.lower() == "true",
            CUSTOM_WELCOME_MESSAGE=self.CUSTOM_WELCOME_MESSAGE,
            CUSTOM_START_MESSAGE=self.CUSTOM_START_MESSAGE,
            CUSTOM_TUTORIAL_BUTTON=self.CUSTOM_TUTORIAL_BUTTON
        )

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.telegram.ADMIN_USER_IDS

    def is_super_admin(self, user_id: int) -> bool:
        """Check if user is super admin"""
        return user_id == self.telegram.SUPER_ADMIN_ID

    def get_feature_status(self, feature_name: str) -> bool:
        """Get status of a specific feature"""
        return getattr(self.features, feature_name.upper(), False)

    def toggle_feature(self, feature_name: str, status: bool) -> bool:
        """Toggle a feature (runtime change)"""
        if hasattr(self.features, feature_name.upper()):
            setattr(self.features, feature_name.upper(), status)
            return True
        return False


# Global config instance
config = Config.load()

# Setup logging based on config
logging.basicConfig(
    level=getattr(logging, config.bot_settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

