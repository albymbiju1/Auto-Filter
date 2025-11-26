"""
Simple test to verify bot is receiving messages
Run this locally to test
"""

from app.bot import bot
from pyrogram import filters

@bot.on_message(filters.command("test"))
async def test_handler(client, message):
    """Simple test handler"""
    await message.reply_text("✅ Bot is working! Commands are being received.")

@bot.on_message(filters.text & filters.private)
async def echo_handler(client, message):
    """Echo any text message"""
    await message.reply_text(f"I received: {message.text}")

if __name__ == "__main__":
    print("Starting test bot...")
    bot.run()
