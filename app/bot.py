"""
Main bot client wrapper for CineAI AutoFilter Bot
Extends Pyrogram client with custom methods and helpers
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta

import pyrogram
from pyrogram import Client, types, enums, filters
from pyrogram.errors import (
    FloodWait,
    ChatAdminRequired,
    ChatWriteForbidden,
    UserBannedInChannel,
    ChannelPrivate
)

from app.config import config

logger = logging.getLogger(__name__)


class MovieBazarBot(Client):
    """Extended Pyrogram client with additional methods for Movie Bazar Bot"""

    def __init__(self):
        """Initialize the bot with configuration"""
        super().__init__(
            "cineai_bot",
            api_id=config.telegram.API_ID,
            api_hash=config.telegram.API_HASH,
            bot_token=config.telegram.BOT_TOKEN,
            in_memory=True,
            plugins=dict(root="handlers")
        )

        # Bot state
        self._rate_limits: Dict[int, Dict[str, datetime]] = {}
        self._force_subscribe_cache: Dict[int, List[int]] = {}

    async def start(self):
        """Start the bot and initialize connections"""
        logger.info("Starting CineAI AutoFilter Bot...")
        await super().start()

        # Get bot info
        me = await self.get_me()
        logger.info(f"Bot started successfully: @{me.username}")

        # Initialize rate limiting
        self._init_rate_limits()

        return me

    async def stop(self, *args, **kwargs):
        """Stop the bot gracefully"""
        logger.info("Stopping bot...")
        await super().stop(*args, **kwargs)
        logger.info("Bot stopped successfully")

    def _init_rate_limits(self):
        """Initialize rate limiting for users"""
        # Rate limit structure: {user_id: {last_action: timestamp}}
        self._rate_limits = {}

    def check_rate_limit(self, user_id: int, action: str = "general") -> bool:
        """Check if user exceeded rate limit"""
        if config.is_admin(user_id):
            return True  # Admins bypass rate limits

        current_time = datetime.now()
        user_limits = self._rate_limits.get(user_id, {})
        last_action = user_limits.get(action)

        if last_action:
            time_diff = (current_time - last_action).seconds
            if time_diff < config.bot_settings.RATE_LIMIT_PER_USER:
                logger.warning(f"Rate limit exceeded for user {user_id}, action: {action}")
                return False

        # Update last action time
        self._rate_limits[user_id] = user_limits
        self._rate_limits[user_id][action] = current_time
        return True

    async def send_message_with_retry(
        self,
        chat_id: Union[int, str],
        text: str,
        reply_markup: Optional["types.InlineKeyboardMarkup"] = None,
        **kwargs
    ) -> Optional["types.Message"]:
        """Send message with retry logic for network issues"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await self.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    **kwargs
                )
            except FloodWait as e:
                logger.warning(f"FloodWait encountered: {e.x} seconds")
                await asyncio.sleep(e.x + 1)
                continue
            except (ChatWriteForbidden, UserBannedInChannel) as e:
                logger.error(f"Cannot send to chat {chat_id}: {e}")
                return None
            except Exception as e:
                logger.error(f"Error sending message (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return None

    async def send_file_with_caption(
        self,
        chat_id: Union[int, str],
        file_id: str,
        caption: Optional[str] = None,
        reply_markup: Optional["types.InlineKeyboardMarkup"] = None,
        **kwargs
    ) -> Optional["types.Message"]:
        """Send file with automatic formatting and error handling"""
        try:
            # Send the file
            message = await self.send_cached_media(
                chat_id=chat_id,
                file_id=file_id,
                caption=caption,
                reply_markup=reply_markup,
                **kwargs
            )

            logger.info(f"File sent successfully to {chat_id}")
            return message

        except FloodWait as e:
            logger.warning(f"FloodWait when sending file: {e.x} seconds")
            await asyncio.sleep(e.x + 1)
            return await self.send_file_with_caption(chat_id, file_id, caption, reply_markup, **kwargs)

        except Exception as e:
            logger.error(f"Error sending file to {chat_id}: {e}")
            return None

    async def check_chat_membership(
        self,
        user_id: int,
        chat_id: Union[int, str]
    ) -> bool:
        """Check if user is member of a chat"""
        try:
            await self.get_chat_member(chat_id, user_id)
            return True
        except (UserBannedInChannel, ChatAdminRequired, ChannelPrivate):
            return False
        except Exception as e:
            logger.error(f"Error checking membership for user {user_id} in {chat_id}: {e}")
            return False

    async def delete_message_after_timeout(
        self,
        chat_id: Union[int, str],
        message_id: int,
        timeout_seconds: int = None
    ):
        """Delete message after specified timeout"""
        if timeout_seconds is None:
            timeout_seconds = config.bot_settings.FILE_DELETE_TTL

        try:
            await asyncio.sleep(timeout_seconds)
            await self.delete_messages(chat_id, [message_id])
            logger.info(f"Message {message_id} deleted from {chat_id} after {timeout_seconds}s")
        except Exception as e:
            logger.error(f"Error deleting message {message_id}: {e}")

    async def get_file_info(self, file_id: str) -> Optional[str]:
        """Get file information and return file path if accessible"""
        try:
            message = await self.get_messages(
                chat_id="me",  # Get from saved messages
                message_ids=file_id
            )

            if message and message.media:
                return message.file.file_id

        except Exception as e:
            logger.error(f"Error getting file info for {file_id}: {e}")

        return None

    async def create_force_subscribe_keyboard(
        self,
        user_id: int
    ) -> "types.InlineKeyboardMarkup":
        """Create Force Subscribe keyboard for required channels"""
        if not config.features.FORCE_SUBSCRIBE:
            return None

        buttons = []
        required_channels = config.force_subscribe.FORCE_SUBSCRIBE_CHANNELS

        for channel_id in required_channels:
            try:
                chat_info = await self.get_chat(channel_id)
                buttons.append([
                    types.InlineKeyboardButton(
                        text=f"👤 Join {chat_info.title}",
                        url=f"https://t.me/{chat_info.username}"
                    )
                ])
            except Exception as e:
                logger.error(f"Error getting chat info for {channel_id}: {e}")
                continue

        if buttons:
            buttons.append([
                types.InlineKeyboardButton(
                    text="🔄 Check Again",
                    callback_data="check_subscribe"
                )
            ])

        return types.InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

    async def search_files_paginated(
        self,
        query: str,
        user_id: int,
        offset: int = 0,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search files with pagination (delegate to database service)"""
        # This will be implemented in the database service
        from services.database_service import DatabaseService

        if not hasattr(self, 'db_service'):
            self.db_service = DatabaseService()

        return await self.db_service.search_files_with_pagination(
            query=query,
            user_id=user_id,
            offset=offset,
            limit=limit
        )

    async def handle_force_subscribe(
        self,
        user_id: int,
        callback_data: str = None
    ) -> bool:
        """Handle Force Subscribe flow"""
        if not config.features.FORCE_SUBSCRIBE:
            return True

        required_channels = config.force_subscribe.FORCE_SUBSCRIBE_CHANNELS
        if not required_channels:
            return True

        # Check membership for all required channels
        for channel_id in required_channels:
            if not await self.check_chat_membership(user_id, channel_id):
                # User not member, send Force Subscribe message
                keyboard = await self.create_force_subscribe_keyboard(user_id)
                await self.send_message_with_retry(
                    chat_id=user_id,
                    text=config.force_subscribe.CUSTOM_WELCOME_MESSAGE,
                    reply_markup=keyboard
                )
                return False

        # User is member of all required channels
        if callback_data == "check_subscribe":
            await self.send_message_with_retry(
                chat_id=user_id,
                text="✅ Thank you for joining! You can now use the bot."
            )

        return True

    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        # This will be implemented in the database service
        from services.database_service import DatabaseService

        if not hasattr(self, 'db_service'):
            self.db_service = DatabaseService()

        return await self.db_service.get_user_stats(user_id)

    async def update_user_stats(self, user_id: int, action: str):
        """Update user statistics"""
        from services.database_service import DatabaseService

        if not hasattr(self, 'db_service'):
            self.db_service = DatabaseService()

        await self.db_service.update_user_stats(user_id, action)

    async def generate_inline_results(
        self,
        query: str,
        user_id: int,
        offset: int = ""
    ) -> List["types.InlineQueryResult"]:
        """Generate inline search results"""
        # This will be implemented in the inline handler
        from handlers.inline import generate_inline_results
        return await generate_inline_results(self, query, user_id, offset)

    async def cleanup_old_messages(self):
        """Cleanup old messages based on TTL"""
        # This will be implemented as a background task
        logger.info("Starting message cleanup task...")
        # Implementation will be added in background tasks module

    async def get_bot_info(self) -> Dict[str, Any]:
        """Get comprehensive bot information"""
        me = await self.get_me()
        return {
            "bot_id": me.id,
            "username": me.username,
            "name": me.first_name,
            "is_premium": getattr(me, 'is_premium', False),
            "stats": {
                "total_users": 0,  # Will be populated from DB
                "total_files": 0,  # Will be populated from DB
                "total_searches": 0,  # Will be populated from DB
            }
        }


# Global bot instance
bot = MovieBazarBot()