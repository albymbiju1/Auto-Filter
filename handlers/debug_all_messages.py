"""
Debug handler to log ALL incoming messages
This will help us see if the bot is receiving messages at all
"""

from pyrogram import Client, filters
from pyrogram.types import Message
import logging

from app.bot import bot

logger = logging.getLogger(__name__)

@bot.on_message(filters.private)
async def debug_all_messages(client: Client, message: Message):
    """Log every private message received"""
    logger.info(f"=" * 60)
    logger.info(f"MESSAGE RECEIVED!")
    logger.info(f"From: {message.from_user.id} (@{message.from_user.username})")
    logger.info(f"Text: {message.text}")
    logger.info(f"Chat: {message.chat.id}")
    logger.info(f"Message ID: {message.id}")
    logger.info(f"=" * 60)

    # Echo back to confirm
    await message.reply_text(
        f"🔍 DEBUG: Received your message!\n\n"
        f"Text: {message.text}\n"
        f"From: {message.from_user.id}\n"
        f"This proves the bot CAN receive messages!"
    )

logger.info("Debug all messages handler loaded")
