"""
Working example of how Pyrogram handlers should be structured
Based on official Pyrogram documentation
"""

from pyrogram import Client, filters
from pyrogram.types import Message

# Bot instance
app = Client(
    "my_bot",
    api_id=1487366,
    api_hash="05b9114e84531190a3840995763f8ab8",
    bot_token="7650202577:AAGTgOxw71PwUTmTZa86v5GBayflPzVqbzs",
    in_memory=True
)

# Handlers registered DIRECTLY on the app instance
@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply_text("✅ Start command works!")

@app.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    await message.reply_text("✅ Help command works!")

@app.on_message(filters.command("test") & filters.private)
async def test_command(client: Client, message: Message):
    await message.reply_text("✅ Test command works!")

# This is the correct pattern for Pyrogram
if __name__ == "__main__":
    print("Starting bot with handlers...")
    print(f"Registered handler groups: {len(app.dispatcher.groups)}")
    app.run()
