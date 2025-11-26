"""
Commands handler for CineAI Bot
Handles all bot commands like /search, /help, /stats, etc.
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

from app.config import config
from app.bot import bot
from services.spellcheck_service import SpellCheckService

logger = logging.getLogger(__name__)

# Initialize services
spell_check = SpellCheckService() if config.features.SPELL_CHECK else None


@bot.on_message(filters.command("search") & filters.private)
async def search_command(client: Client, message: Message):
    """Handle /search command"""
    user_id = message.from_user.id

    try:
        # Check if PM search is enabled
        if not config.features.PM_SEARCH:
            await message.reply_text(
                "❌ Private search is disabled.\n"
                "Please use inline search instead.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🔍 Try Inline Search",
                        switch_inline_query_current_chat=""
                    )]
                ])
            )
            return

        # Check rate limiting
        if not client.check_rate_limit(user_id, "search"):
            await message.reply_text(
                "⏱️ Please wait before searching again.",
                show_alert=True
            )
            return

        # Get search query
        query = message.text.split("/search", 1)[1].strip()
        if not query:
            bot_info = await client.get_me()
            await message.reply_text(
                "🔍 **Search Usage:**\n\n"
                "`/search <movie name>`\n\n"
                "Examples:\n"
                "• `/search Avengers`\n"
                "• `/search Avengers 2019`\n"
                "• `/search Game of Thrones S01E01`\n\n"
                "You can also use inline search:\n"
                f"@{bot_info.username} <movie name>",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🔍 Try Inline Search",
                        switch_inline_query_current_chat=""
                    )]
                ])
            )
            return

        # Spell check if enabled
        if spell_check:
            corrected_query = await spell_check.correct_query(query)
            if corrected_query != query:
                await message.reply_text(
                    f"💡 Did you mean: **{corrected_query}**?\n\n"
                    f"Searching for: `{corrected_query}`",
                    parse_mode=ParseMode.MARKDOWN
                )
                query = corrected_query

        # Perform search
        await perform_search(client, message, query, user_id)

        # Update user stats
        await client.db_service.update_user_stats(user_id, "search")

    except Exception as e:
        logger.error(f"Error in search command for user {user_id}: {e}")
        await message.reply_text(
            "❌ An error occurred while searching. Please try again later."
        )


async def perform_search(client: Client, message: Message, query: str, user_id: int):
    """Perform file search and send results"""
    try:
        # Search files
        result = await client.db_service.search_files_with_pagination(
            query=query,
            user_id=user_id,
            offset=0,
            limit=10
        )

        if not result["files"]:
            await message.reply_text(
                f"🔍 **No Results Found**\n\n"
                f"No files found for: `{query}`\n\n"
                f"💡 **Tips:**\n"
                f"• Check spelling\n"
                f"• Try different keywords\n"
                f"• Use movie titles only\n"
                f"• Include year for better results\n\n"
                f"Try inline search for more results:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🔍 Try Inline Search",
                        switch_inline_query_current_chat=query
                    )]
                ])
            )
            return

        # Send results
        await send_search_results(client, message, result, query, user_id)

    except Exception as e:
        logger.error(f"Error performing search: {e}")
        raise


async def send_search_results(client: Client, message: Message, result, query: str, user_id: int):
    """Send search results to user"""
    try:
        files_text = f"🔍 **Search Results for:** `{query}`\n\n"
        files_text += f"Found {result['total']} files\n\n"

        keyboard_buttons = []

        for i, file in enumerate(result["files"][:10], 1):
            # File title with quality emoji
            title = file.display_title
            quality_emoji = get_quality_emoji(file.quality)
            files_text += f"{i}. {quality_emoji} {title}\n"

            # Add details
            details = []
            if file.year:
                details.append(str(file.year))
            if file.quality:
                details.append(file.quality.value.upper())
            if file.language:
                details.append(file.language.value.upper())
            if file.file_size:
                size_mb = file.file_size / (1024 * 1024)
                details.append(f"{size_mb:.1f}MB")

            if details:
                files_text += f"   └ {', '.join(details)}\n"

            # Add premium/verification indicators
            if file.is_premium:
                files_text += f"   └ 🔒 Premium\n"
            elif file.verification_required:
                files_text += f"   └ 🔐 Verification Required\n"

            files_text += "\n"

            # Add action button
            button_text = f"📥 {file.title[:20]}..."
            if file.is_premium:
                button_text = f"🔒 {file.title[:18]}..."
            elif file.verification_required:
                button_text = f"🔐 {file.title[:18]}..."

            keyboard_buttons.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"send_file_{file.file_id}"
                )
            ])

        # Add pagination if more results
        if result["has_next"]:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    "➡️ More Results",
                    callback_data=f"search_page_{query}_{result['offset'] + result['limit']}"
                )
            ])

        # Add search again button
        keyboard_buttons.append([
            InlineKeyboardButton(
                "🔍 New Search",
                callback_data="new_search"
            )
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await message.reply_text(
            files_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Error sending search results: {e}")
        raise


@bot.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    """Handle /help command"""
    user_id = message.from_user.id

    try:
        help_text = await build_help_text(client)

        # Build keyboard based on available features
        keyboard_buttons = []

        # Search buttons
        search_row = []
        if config.features.INLINE_SEARCH:
            search_row.append(InlineKeyboardButton(
                "🔍 Inline Search",
                switch_inline_query_current_chat=""
            ))
        if config.features.PM_SEARCH:
            search_row.append(InlineKeyboardButton(
                "📝 PM Search",
                callback_data="pm_search"
            ))
        if search_row:
            keyboard_buttons.append(search_row)

        # Feature buttons
        feature_row = []
        if config.features.PREMIUM:
            feature_row.append(InlineKeyboardButton(
                "⭐ Premium",
                callback_data="premium_info"
            ))
        if config.features.REFERRAL:
            feature_row.append(InlineKeyboardButton(
                "👥 Referral",
                callback_data="referral_info"
            ))
        if feature_row:
            keyboard_buttons.append(feature_row)

        # Utility buttons
        utility_row = []
        utility_row.append(InlineKeyboardButton(
            "📊 My Stats",
            callback_data="my_stats"
        ))
        if config.features.STREAM:
            utility_row.append(InlineKeyboardButton(
                "🎬 Streaming",
                callback_data="streaming_info"
            ))
        if utility_row:
            keyboard_buttons.append(utility_row)

        # Admin button
        if config.is_admin(user_id):
            keyboard_buttons.append([
                InlineKeyboardButton(
                    "⚙️ Admin Panel",
                    callback_data="admin_panel"
                )
            ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None

        await message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Error in help command for user {user_id}: {e}")
        await message.reply_text("❌ Error loading help. Please try again later.")


async def build_help_text(client: Client) -> str:
    """Build help text based on enabled features"""
    help_text = "🎬 **CineAI Bot Help**\n\n"

    help_text += "📖 **Available Commands:**\n\n"

    # Basic commands
    help_text += "• `/start` - Start the bot\n"
    help_text += "• `/help` - Show this help message\n"

    # Search commands
    if config.features.PM_SEARCH:
        help_text += "• `/search <query>` - Search in private chat\n"

    if config.features.INLINE_SEARCH:
        bot_info = await client.get_me()
        help_text += f"• Inline: `@{bot_info.username} <query>` - Search inline\n"

    # Feature commands
    if config.features.PREMIUM:
        help_text += "• `/premium` - Premium information\n"

    if config.features.REFERRAL:
        help_text += "• `/referral` - Referral system\n"

    if config.features.STREAM:
        help_text += "• `/stream` - Streaming information\n"

    # User commands
    help_text += "• `/stats` - Your statistics\n"
    help_text += "• `/profile` - Your profile\n"

    # Admin commands
    if config.is_admin(message.from_user.id if 'message' in locals() else 0):
        help_text += "\n🔧 **Admin Commands:**\n"
        help_text += "• `/admin` - Admin panel\n"
        help_text += "• `/broadcast <message>` - Broadcast message\n"
        help_text += "• `/stats` - Bot statistics\n"
        help_text += "• `/users` - User statistics\n"
        help_text += "• `/channels` - Channel management\n"

    # Features section
    help_text += "\n✨ **Features:**\n\n"

    if config.features.AUTO_FILTER:
        help_text += "🤖 **Auto Filter:** Automatically indexes files from linked channels\n"

    if config.features.INLINE_SEARCH:
        help_text += "🔍 **Inline Search:** Search directly in any chat\n"

    if config.features.PM_SEARCH:
        help_text += "📝 **PM Search:** Search in private chat with bot\n"

    if config.features.STREAM:
        help_text += "🎬 **Streaming:** Watch files online without downloading\n"

    if config.features.PREMIUM:
        help_text += "⭐ **Premium:** Get access to exclusive features\n"

    if config.features.REFERRAL:
        help_text += "👥 **Referral:** Earn premium by inviting friends\n"

    if config.features.FORCE_SUBSCRIBE:
        help_text += "🔒 **Force Subscribe:** Must join channels to use bot\n"

    if config.features.CLONE:
        help_text += "📋 **Clone:** Save files to your personal collection\n"

    if config.features.SPELL_CHECK:
        help_text += "✨ **Spell Check:** Automatic typo correction\n"

    if config.features.IMDB_INTEGRATION:
        help_text += "🎭 **IMDB:** Movie information and ratings\n"

    # Tips
    help_text += "\n💡 **Search Tips:**\n\n"
    help_text += "• Use exact movie titles for best results\n"
    help_text += "• Include year for better accuracy (e.g., `Avengers 2019`)\n"
    help_text += "• For series: `Show Name S01E01`\n"
    help_text += "• Add quality: `Movie Name HD`\n"
    help_text += "• Add language: `Movie Name Hindi`\n"

    # Support
    help_text += "\n🆘 **Need Help?**\n\n"
    help_text += "If you need assistance, contact our support team.\n"

    return help_text


@bot.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    """Handle /stats command"""
    user_id = message.from_user.id

    try:
        # Get user statistics
        user_stats = await client.db_service.get_user_stats(user_id)
        user = await client.db_service.get_user(user_id)

        if not user:
            await message.reply_text("❌ User not found. Please start the bot first.")
            return

        # Build stats message
        stats_text = f"📊 **Your Statistics**\n\n"
        stats_text += f"👤 **User Info:**\n"
        stats_text += f"• ID: `{user_id}`\n"
        stats_text += f"• Name: {user.full_name}\n"
        stats_text += f"• Username: @{user.username}\n" if user.username else "• Username: None\n"
        stats_text += f"• Joined: {user.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        stats_text += f"• Last Active: {user.last_seen.strftime('%Y-%m-%d %H:%M')}\n"

        if user.is_premium_active:
            stats_text += f"• Status: ⭐ Premium User\n"
            if user.premium_expires:
                days_left = (user.premium_expires - datetime.utcnow()).days
                stats_text += f"• Premium Expires: {days_left} days\n"
        else:
            stats_text += f"• Status: Regular User\n"

        stats_text += f"\n📈 **Activity:**\n"
        stats_text += f"• Total Searches: {user_stats.get('searches', 0)}\n"
        stats_text += f"• Total Downloads: {user_stats.get('downloads', 0)}\n"
        stats_text += f"• Files Shared: {user_stats.get('files_shared', 0)}\n"

        if user.referral_count > 0:
            stats_text += f"• Referrals: {user.referral_count}\n"

        # Build keyboard
        keyboard_buttons = []
        keyboard_buttons.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats")
        ])

        if config.features.REFERRAL:
            keyboard_buttons.append([
                InlineKeyboardButton("👥 My Referrals", callback_data="my_referrals")
            ])

        if config.features.PREMIUM and not user.is_premium_active:
            keyboard_buttons.append([
                InlineKeyboardButton("⭐ Get Premium", callback_data="premium_info")
            ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await message.reply_text(
            stats_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error in stats command for user {user_id}: {e}")
        await message.reply_text("❌ Error loading statistics. Please try again later.")


@bot.on_message(filters.command("profile") & filters.private)
async def profile_command(client: Client, message: Message):
    """Handle /profile command"""
    user_id = message.from_user.id

    try:
        user = await client.db_service.get_user(user_id)
        if not user:
            await message.reply_text("❌ User not found. Please start the bot first.")
            return

        # Build profile message
        profile_text = f"👤 **Your Profile**\n\n"
        profile_text += f"📛 **Name:** {user.full_name}\n"
        profile_text += f"🆔 **ID:** `{user_id}`\n"

        if user.username:
            profile_text += f"🔗 **Username:** @{user.username}\n"

        profile_text += f"📅 **Joined:** {user.created_at.strftime('%B %d, %Y')}\n"
        profile_text += f"🕐 **Last Seen:** {user.last_seen.strftime('%B %d, %Y at %I:%M %p')}\n"

        # Premium status
        if user.is_premium_active:
            profile_text += f"\n⭐ **Premium Status:** Active\n"
            if user.premium_expires:
                days_left = (user.premium_expires - datetime.utcnow()).days
                profile_text += f"📆 **Expires:** {days_left} days\n"
            else:
                profile_text += f"📆 **Expires:** Lifetime\n"
        else:
            profile_text += f"\n⭐ **Premium Status:** Inactive\n"

        # Referral info
        if config.features.REFERRAL:
            if user.referral_code:
                bot_info = await client.get_me()
                profile_text += f"\n👥 **Referral Code:** `{user.referral_code}`\n"
                profile_text += f"🔗 **Referral Link:** https://t.me/{bot_info.username}?start={user.referral_code}\n"
                profile_text += f"📊 **Referrals:** {user.referral_count}\n"

        # Verification status
        if user.is_verified:
            profile_text += f"\n✅ **Verification:** Verified\n"
        else:
            profile_text += f"\n❌ **Verification:** Not Verified\n"

        # Build keyboard
        keyboard_buttons = []
        keyboard_buttons.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_profile")
        ])

        if config.features.REFERRAL and user.referral_code:
            keyboard_buttons.append([
                InlineKeyboardButton("📋 Copy Code", callback_data="copy_referral_code")
            ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await message.reply_text(
            profile_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error in profile command for user {user_id}: {e}")
        await message.reply_text("❌ Error loading profile. Please try again later.")


def get_quality_emoji(quality) -> str:
    """Get emoji for quality"""
    quality_emojis = {
        "HD": "📺",
        "FHD": "📺",
        "SD": "📱",
        "UHD": "🖥️",
        "HDR": "🌈"
    }
    return quality_emojis.get(quality, "🎬")


# Callback handlers
@bot.on_callback_query(filters.regex("^search_page_(.+?)_(\\d+)$"))
async def search_page_callback(client: Client, callback_query):
    """Handle search pagination"""
    user_id = callback_query.from_user.id
    query = callback_query.matches[0].group(1)
    offset = int(callback_query.matches[0].group(2))

    try:
        await callback_query.answer("Loading more results...")

        # Search files for this page
        result = await client.db_service.search_files_with_pagination(
            query=query,
            user_id=user_id,
            offset=offset,
            limit=10
        )

        if not result["files"]:
            await callback_query.answer("No more results available.")
            return

        # Update message with new results
        await send_search_results(client, callback_query.message, result, query, user_id)

    except Exception as e:
        logger.error(f"Error in search page callback: {e}")
        await callback_query.answer("❌ Error occurred. Please try again.", show_alert=True)


@bot.on_callback_query(filters.regex("^new_search$"))
async def new_search_callback(client: Client, callback_query):
    """Handle new search callback"""
    try:
        await callback_query.answer()

        await callback_query.message.edit_text(
            "🔍 **New Search**\n\n"
            "Type `/search <movie name>` to search again\n\n"
            "Or use inline search:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔍 Search Inline",
                    switch_inline_query_current_chat=""
                )]
            ])
        )

    except Exception as e:
        logger.error(f"Error in new search callback: {e}")
        await callback_query.answer("❌ Error occurred. Please try again.", show_alert=True)