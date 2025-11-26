"""
Database service for CineAI Bot
Supports both MongoDB and PostgreSQL backends with unified interface
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, update, delete, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload

from app.config import config
from models.base import DatabaseService, DatabaseBackend, PaginationResult
from models.user import UserDocument, UserSQL, UserCreate, UserUpdate, UserSearchFilters, UserRole, UserStatus
from models.file import FileDocument, FileSQL, FileCreate, FileUpdate, FileSearchFilters, FileType, FileStatus, FileSource
from models.channel import ChannelDocument, ChannelSQL, ChannelCreate, ChannelUpdate, ChannelSearchFilters, ChannelType, ChannelStatus, IndexMode
from models.referral import ReferralDocument, ReferralSQL, ReferralCreate, ReferralUpdate, ReferralSearchFilters, ReferralStatus, ReferralRewardType
from models.premium import PremiumDocument, PremiumSQL, PremiumCreate, PremiumUpdate, PremiumSearchFilters, PremiumPlan, PremiumStatus, PaymentMethod

logger = logging.getLogger(__name__)


class MongoDatabaseService(DatabaseService):
    """MongoDB implementation of database service"""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

    async def initialize(self):
        """Initialize MongoDB connection"""
        try:
            self.client = AsyncIOMotorClient(
                config.database.MONGO_URI,
                maxPoolSize=20,
                minPoolSize=5,
                serverSelectionTimeoutMS=30000
            )
            self.db = self.client.get_default_database()

            # Test connection
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully")

            # Create indexes
            await self.create_indexes()

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

    async def health_check(self) -> bool:
        """Check MongoDB health"""
        try:
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False

    async def create_indexes(self):
        """Create MongoDB indexes"""
        try:
            # User indexes
            await self.db.users.create_index("telegram_id", unique=True)
            await self.db.users.create_index("username")
            await self.db.users.create_index("referral_code", unique=True, sparse=True)
            await self.db.users.create_index("referred_by")
            await self.db.users.create_index("status")
            await self.db.users.create_index("created_at")

            # File indexes
            await self.db.files.create_index([("chat_id", 1), ("message_id", 1)], unique=True)
            await self.db.files.create_index("file_id")
            await self.db.files.create_index("title")
            await self.db.files.create_index("imdb_id", sparse=True)
            await self.db.files.create_index([("title", "text"), ("alt_titles", "text"), ("tags", "text")])
            await self.db.files.create_index("year")
            await self.db.files.create_index("quality")
            await self.db.files.create_index("language")
            await self.db.files.create_index("status")
            await self.db.files.create_index("created_at")
            await self.db.files.create_index("expires_at", sparse=True)

            # Channel indexes
            await self.db.channels.create_index("chat_id", unique=True)
            await self.db.channels.create_index("username", sparse=True)
            await self.db.channels.create_index("status")
            await self.db.channels.create_index("is_linked")
            await self.db.channels.create_index("last_indexed_at")
            await self.db.channels.create_index("created_at")

            # Referral indexes
            await self.db.referrals.create_index("code", unique=True)
            await self.db.referrals.create_index("owner_id")
            await self.db.referrals.create_index("status")
            await self.db.referrals.create_index("expires_at", sparse=True)
            await self.db.referrals.create_index("created_at")

            # Premium indexes
            await self.db.premium.create_index("user_id", unique=True)
            await self.db.premium.create_index("status")
            await self.db.premium.create_index("expires_at", sparse=True)
            await self.db.premium.create_index("created_at")

            logger.info("MongoDB indexes created successfully")

        except Exception as e:
            logger.error(f"Failed to create MongoDB indexes: {e}")
            raise

    # User operations
    async def create_user(self, user_data: Dict[str, Any]) -> UserDocument:
        """Create a new user"""
        user = UserDocument(**user_data)
        result = await self.db.users.insert_one(user.to_dict())
        user.id = str(result.inserted_id)
        return user

    async def get_user(self, user_id: int) -> Optional[UserDocument]:
        """Get user by ID"""
        data = await self.db.users.find_one({"telegram_id": user_id})
        return UserDocument(**data) if data else None

    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> bool:
        """Update user data"""
        update_data["updated_at"] = datetime.utcnow()
        result = await self.db.users.update_one(
            {"telegram_id": user_id},
            {"$set": update_data}
        )
        return result.modified_count > 0

    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        user = await self.get_user(user_id)
        if not user:
            return {}

        return {
            "searches": user.stats.searches.total_searches,
            "downloads": user.stats.downloads.total_downloads,
            "files_shared": user.stats.downloads.files_downloaded,
            "last_active": user.last_seen.isoformat(),
            "joined_at": user.created_at.isoformat()
        }

    async def update_user_stats(self, user_id: int, action: str):
        """Update user statistics"""
        update_field = f"stats.{action}s.total_{action}s"
        await self.db.users.update_one(
            {"telegram_id": user_id},
            {
                "$inc": {update_field: 1},
                "$set": {
                    "stats.last_active": datetime.utcnow(),
                    "last_seen": datetime.utcnow()
                }
            }
        )

    # File operations
    async def create_file(self, file_data: Dict[str, Any]) -> FileDocument:
        """Create a new file record"""
        file = FileDocument(**file_data)
        result = await self.db.files.insert_one(file.to_dict())
        file.id = str(result.inserted_id)
        return file

    async def get_file(self, file_id: str) -> Optional[FileDocument]:
        """Get file by ID"""
        data = await self.db.files.find_one({"file_id": file_id})
        return FileDocument(**data) if data else None

    async def search_files_with_pagination(
        self,
        query: str,
        user_id: int,
        offset: int = 0,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search files with pagination"""
        search_filter = {
            "status": FileStatus.ACTIVE
        }

        if query:
            search_filter["$text"] = {"$search": query}

        # Get total count
        total = await self.db.files.count_documents(search_filter)

        # Get files with pagination
        cursor = self.db.files.find(search_filter).skip(offset).limit(limit)
        files = [FileDocument(**doc) async for doc in cursor]

        return {
            "files": files,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_next": offset + limit < total
        }

    async def cleanup_old_files(self, ttl_seconds: int) -> int:
        """Cleanup old files based on TTL"""
        cutoff_date = datetime.utcnow() - timedelta(seconds=ttl_seconds)
        result = await self.db.files.delete_many({
            "expires_at": {"$lt": cutoff_date}
        })
        return result.deleted_count

    # Channel operations
    async def create_channel(self, channel_data: Dict[str, Any]) -> ChannelDocument:
        """Create a new channel record"""
        channel = ChannelDocument(**channel_data)
        result = await self.db.channels.insert_one(channel.to_dict())
        channel.id = str(result.inserted_id)
        return channel

    async def get_channel(self, chat_id: int) -> Optional[ChannelDocument]:
        """Get channel by ID"""
        data = await self.db.channels.find_one({"chat_id": chat_id})
        return ChannelDocument(**data) if data else None

    async def get_all_channels(self) -> List[ChannelDocument]:
        """Get all channels"""
        cursor = self.db.channels.find({"status": ChannelStatus.ACTIVE})
        return [ChannelDocument(**doc) async for doc in cursor]

    async def auto_index_channels(self):
        """Auto-index channels"""
        channels = await self.db.channels.find({
            "status": ChannelStatus.ACTIVE,
            "is_linked": True,
            "indexing_enabled": True,
            "index_mode": {"$ne": IndexMode.DISABLED}
        }).to_list(None)

        for channel_data in channels:
            channel = ChannelDocument(**channel_data)
            if channel.needs_indexing:
                # Trigger indexing for this channel
                await self._index_channel(channel)

    async def _index_channel(self, channel: ChannelDocument):
        """Index a specific channel"""
        # This will be implemented in the channel listener
        pass

    # Referral operations
    async def create_referral(self, referral_data: Dict[str, Any]) -> ReferralDocument:
        """Create a new referral"""
        referral = ReferralDocument(**referral_data)
        result = await self.db.referrals.insert_one(referral.to_dict())
        referral.id = str(result.inserted_id)
        return referral

    async def get_referral(self, code: str) -> Optional[ReferralDocument]:
        """Get referral by code"""
        data = await self.db.referrals.find_one({"code": code})
        return ReferralDocument(**data) if data else None

    # Premium operations
    async def create_premium(self, premium_data: Dict[str, Any]) -> PremiumDocument:
        """Create a new premium subscription"""
        premium = PremiumDocument(**premium_data)
        result = await self.db.premium.insert_one(premium.to_dict())
        premium.id = str(result.inserted_id)
        return premium

    async def get_premium(self, user_id: int) -> Optional[PremiumDocument]:
        """Get premium subscription by user ID"""
        data = await self.db.premium.find_one({"user_id": user_id})
        return PremiumDocument(**data) if data else None

    async def cleanup_expired_premium(self):
        """Cleanup expired premium subscriptions"""
        await self.db.premium.update_many(
            {"expires_at": {"$lt": datetime.utcnow()}, "status": PremiumStatus.ACTIVE},
            {"$set": {"status": PremiumStatus.EXPIRED}}
        )

    # General operations
    async def get_bot_stats(self) -> Dict[str, Any]:
        """Get bot statistics"""
        stats = {}

        # User stats
        stats["total_users"] = await self.db.users.count_documents({})
        stats["active_users"] = await self.db.users.count_documents({
            "last_seen": {"$gte": datetime.utcnow() - timedelta(days=7)}
        })

        # File stats
        stats["total_files"] = await self.db.files.count_documents({})
        stats["active_files"] = await self.db.files.count_documents({"status": FileStatus.ACTIVE})

        # Channel stats
        stats["total_channels"] = await self.db.channels.count_documents({})
        stats["active_channels"] = await self.db.channels.count_documents({"status": ChannelStatus.ACTIVE})

        # Premium stats
        stats["premium_users"] = await self.db.premium.count_documents({"status": PremiumStatus.ACTIVE})

        return stats


class DatabaseService:
    """Unified database service using MongoDB backend"""

    def __init__(self):
        self.backend = MongoDatabaseService()
        logger.info("Using MONGODB as primary database")

    async def initialize(self):
        """Initialize database service"""
        await self.backend.initialize()

    async def close(self):
        """Close database service"""
        await self.backend.close()

    async def health_check(self) -> bool:
        """Check database health"""
        return await self.backend.health_check()

    # Delegate all operations to the backend
    async def create_user(self, user_data: Dict[str, Any]):
        return await self.backend.create_user(user_data)

    async def get_user(self, user_id: int):
        return await self.backend.get_user(user_id)

    async def update_user(self, user_id: int, update_data: Dict[str, Any]):
        return await self.backend.update_user(user_id, update_data)

    async def get_user_stats(self, user_id: int):
        return await self.backend.get_user_stats(user_id)

    async def update_user_stats(self, user_id: int, action: str):
        return await self.backend.update_user_stats(user_id, action)

    async def create_file(self, file_data: Dict[str, Any]):
        return await self.backend.create_file(file_data)

    async def get_file(self, file_id: str):
        return await self.backend.get_file(file_id)

    async def search_files_with_pagination(self, query: str, user_id: int, offset: int = 0, limit: int = 10):
        return await self.backend.search_files_with_pagination(query, user_id, offset, limit)

    async def cleanup_old_files(self, ttl_seconds: int):
        return await self.backend.cleanup_old_files(ttl_seconds)

    async def create_channel(self, channel_data: Dict[str, Any]):
        return await self.backend.create_channel(channel_data)

    async def get_channel(self, chat_id: int):
        return await self.backend.get_channel(chat_id)

    async def get_all_channels(self):
        return await self.backend.get_all_channels()

    async def auto_index_channels(self):
        return await self.backend.auto_index_channels()

    async def create_referral(self, referral_data: Dict[str, Any]):
        return await self.backend.create_referral(referral_data)

    async def get_referral(self, code: str):
        return await self.backend.get_referral(code)

    async def create_premium(self, premium_data: Dict[str, Any]):
        return await self.backend.create_premium(premium_data)

    async def get_premium(self, user_id: int):
        return await self.backend.get_premium(user_id)

    async def cleanup_expired_premium(self):
        return await self.backend.cleanup_expired_premium()

    async def get_bot_stats(self):
        return await self.backend.get_bot_stats()

    async def cleanup_old_short_urls(self, days: int = 30):
        """Cleanup old short URLs"""
        # Implementation would depend on backend
        return 0