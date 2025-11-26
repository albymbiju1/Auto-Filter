"""
Simple test handler to verify plugin loading
"""

from pyrogram import Client, filters
from pyrogram.types import Message
import logging

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("test") & filters.private)
async def test_handler(client: Client, message: Message):
    """Test command to verify handlers are working"""
    logger.info(f"Test command received from {message.from_user.id}")
    await message.reply_text("✅ Handler is working! Commands are being received.")

logger.info("Test handler module loaded")
