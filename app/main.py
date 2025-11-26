"""
Main entry point for CineAI AutoFilter Bot
Initializes and starts the bot with all components
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from app.config import config
from app.bot import bot as movie_bazar_bot
from services.database_service import DatabaseService
from services.redis_service import RedisService
from utils.logger import setup_logging
from pyrogram.enums import ParseMode

# Setup logging
logger = setup_logging()
logger.info("Starting Movie Bazar Bot...")


class BotManager:
    """Manages bot lifecycle and services"""

    def __init__(self):
        self.db_service: Optional[DatabaseService] = None
        self.redis_service: Optional[RedisService] = None
        self._shutdown_event = asyncio.Event()

    async def initialize(self):
        """Initialize all services"""
        logger.info("Initializing services...")

        try:
            # Initialize database service
            self.db_service = DatabaseService()
            await self.db_service.initialize()
            logger.info("Database service initialized")

            # Initialize Redis service if configured
            if config.database.REDIS_URL:
                self.redis_service = RedisService(config.database.REDIS_URL)
                await self.redis_service.initialize()
                logger.info("Redis service initialized")
            else:
                logger.info("Redis not configured, skipping cache service")

            # Store services in bot instance for easy access
            movie_bazar_bot.db_service = self.db_service
            movie_bazar_bot.redis_service = self.redis_service

            # Initialize background tasks
            await self._initialize_background_tasks()

            logger.info("All services initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise

    async def _initialize_background_tasks(self):
        """Initialize background tasks"""
        # Start health check server for Koyeb
        from health_server import start_health_server
        asyncio.create_task(start_health_server(8000))

        # Start cleanup tasks
        asyncio.create_task(self._cleanup_task())
        asyncio.create_task(self._stats_update_task())

        if config.features.AUTO_FILTER:
            asyncio.create_task(self._auto_index_task())

        logger.info("Background tasks started")

    async def start(self):
        """Start the bot"""
        try:
            # Initialize services first
            await self.initialize()

            # Start the bot
            me = await movie_bazar_bot.start()

            logger.info(f"Bot started successfully: @{me.username}")
            logger.info(f"Admin users: {config.telegram.ADMIN_USER_IDS}")
            logger.info(f"Features enabled: {config.features.model_dump()}")

            # Send startup message to super admin
            if config.telegram.SUPER_ADMIN_ID:
                await self._send_startup_message(config.telegram.SUPER_ADMIN_ID, me)

            # Wait for shutdown signal
            await self._wait_for_shutdown()

        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise

    async def stop(self):
        """Stop the bot and cleanup"""
        logger.info("Shutting down bot...")

        try:
            # Stop the bot
            await movie_bazar_bot.stop()

            # Cleanup services
            if self.db_service:
                await self.db_service.close()

            if self.redis_service:
                await self.redis_service.close()

            logger.info("Bot shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def _wait_for_shutdown(self):
        """Wait for shutdown signals"""
        def signal_handler():
            self._shutdown_event.set()

        # Register signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda s, f: signal_handler())

        # Wait for shutdown
        await self._shutdown_event.wait()

    async def _send_startup_message(self, admin_id: int, bot_info):
        """Send startup message to admin"""
        try:
            startup_text = f"""
🚀 **Movie Bazar Bot Started Successfully**

🤖 **Bot Info:**
- Username: @{bot_info.username}
- ID: {bot_info.id}
- Premium: {'✅' if getattr(bot_info, 'is_premium', False) else '❌'}

⚙️ **Features Status:**
- Auto Filter: {'✅' if config.features.AUTO_FILTER else '❌'}
- PM Search: {'✅' if config.features.PM_SEARCH else '❌'}
- Inline Search: {'✅' if config.features.INLINE_SEARCH else '❌'}
- Force Subscribe: {'✅' if config.features.FORCE_SUBSCRIBE else '❌'}
- Premium: {'✅' if config.features.PREMIUM else '❌'}
- Referral: {'✅' if config.features.REFERRAL else '❌'}
- Stream: {'✅' if config.features.STREAM else '❌'}
- Clone: {'✅' if config.features.CLONE else '❌'}

📊 **Database:**
- Primary: {config.database.PRIMARY_DB.upper()}
- Multi-DB: {'✅' if config.features.MULTI_DB else '❌'}

🔗 **External APIs:**
- IMDB: {'✅' if config.features.IMDB_INTEGRATION else '❌'}
- URL Shortener: {'✅' if config.features.URL_SHORTENER else '❌'}

Bot is ready to serve users! 🎬
            """

            await movie_bazar_bot.send_message(
                chat_id=admin_id,
                text=startup_text,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            logger.error(f"Failed to send startup message: {e}")

    async def _cleanup_task(self):
        """Background cleanup task"""
        while not self._shutdown_event.is_set():
            try:
                # Cleanup old files based on TTL
                if config.bot_settings.FILE_DELETE_TTL > 0:
                    await self.db_service.cleanup_old_files(config.bot_settings.FILE_DELETE_TTL)

                # Cleanup expired premium memberships
                if config.features.PREMIUM:
                    await self.db_service.cleanup_expired_premium()

                # Cleanup old short URLs if feature is enabled
                if config.features.URL_SHORTENER:
                    await self.db_service.cleanup_old_short_urls()

                # Wait 1 hour before next cleanup
                await asyncio.sleep(3600)

            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _stats_update_task(self):
        """Background stats update task"""
        while not self._shutdown_event.is_set():
            try:
                # Update bot statistics
                stats = await self.db_service.get_bot_stats()

                # Cache stats in Redis if available
                if self.redis_service:
                    await self.redis_service.cache_bot_stats(stats)

                # Wait 5 minutes before next update
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Error in stats update task: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def _auto_index_task(self):
        """Auto-index background task"""
        while not self._shutdown_event.is_set():
            try:
                # Check for new messages in linked channels
                await self.db_service.auto_index_channels()

                # Wait 30 seconds before next check
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in auto-index task: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error


async def main():
    """Main entry point"""
    bot_manager = BotManager()

    try:
        await bot_manager.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await bot_manager.stop()


if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())