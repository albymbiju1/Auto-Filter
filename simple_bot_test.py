"""
Absolute minimal test - does Pyrogram work at all?
"""

from pyrogram import Client, filters
import os

# Use your actual credentials
BOT_TOKEN = "7650202577:AAGTgOxw71PwUTmTZa86v5GBayflPzVqbzs"
API_ID = 1487366
API_HASH = "05b9114e84531190a3840995763f8ab8"

print("Creating bot...")
bot = Client(
    "test_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

print(f"Bot created: {bot}")
print(f"Dispatcher exists: {hasattr(bot, 'dispatcher')}")

@bot.on_message(filters.command("test"))
async def test_handler(client, message):
    print(f"Received command from {message.from_user.id}")
    await message.reply_text("✅ IT WORKS!")

print("Handler registered")
print(f"Dispatcher groups: {len(bot.dispatcher.groups) if hasattr(bot, 'dispatcher') else 'No dispatcher'}")

print("\nStarting bot...")
bot.run()
