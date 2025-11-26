"""
Debug script to test handler registration
Run this locally to see if handlers are being registered
"""

import logging
logging.basicConfig(level=logging.INFO)

# Test 1: Check if bot instance exists
print("=" * 60)
print("TEST 1: Checking bot instance")
print("=" * 60)

try:
    from app.bot import bot
    print(f"✓ Bot instance created: {bot}")
    print(f"✓ Bot type: {type(bot)}")
    print(f"✓ Bot name: {bot.name}")
except Exception as e:
    print(f"✗ Failed to create bot: {e}")
    exit(1)

# Test 2: Check handler count BEFORE importing handlers
print("\n" + "=" * 60)
print("TEST 2: Handler count BEFORE import")
print("=" * 60)

handler_count_before = len(bot.dispatcher.groups)
print(f"Handler groups before: {handler_count_before}")
print(f"Dispatcher: {bot.dispatcher}")

# Test 3: Import handlers
print("\n" + "=" * 60)
print("TEST 3: Importing handlers")
print("=" * 60)

try:
    import handlers.test
    print("✓ handlers.test imported")
except Exception as e:
    print(f"✗ Failed to import handlers.test: {e}")
    import traceback
    traceback.print_exc()

try:
    import handlers.start
    print("✓ handlers.start imported")
except Exception as e:
    print(f"✗ Failed to import handlers.start: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Check handler count AFTER importing handlers
print("\n" + "=" * 60)
print("TEST 4: Handler count AFTER import")
print("=" * 60)

handler_count_after = len(bot.dispatcher.groups)
print(f"Handler groups after: {handler_count_after}")
print(f"Handlers added: {handler_count_after - handler_count_before}")

# Test 5: Inspect dispatcher groups
print("\n" + "=" * 60)
print("TEST 5: Dispatcher groups details")
print("=" * 60)

for group_id, handlers in bot.dispatcher.groups.items():
    print(f"\nGroup {group_id}: {len(handlers)} handlers")
    for handler in handlers:
        print(f"  - {handler}")

# Test 6: Try to manually register a handler
print("\n" + "=" * 60)
print("TEST 6: Manual handler registration")
print("=" * 60)

from pyrogram import filters
from pyrogram.types import Message

@bot.on_message(filters.command("manual") & filters.private)
async def manual_test(client, message: Message):
    await message.reply_text("Manual handler works!")

print("✓ Manual handler registered")

handler_count_manual = len(bot.dispatcher.groups)
print(f"Handler groups after manual: {handler_count_manual}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Bot instance: OK")
print(f"Handlers before import: {handler_count_before}")
print(f"Handlers after import: {handler_count_after}")
print(f"Handlers after manual: {handler_count_manual}")
print(f"Total handlers registered: {handler_count_manual}")

if handler_count_manual > 0:
    print("\n✓ Handlers ARE being registered!")
else:
    print("\n✗ NO handlers registered - something is wrong!")
