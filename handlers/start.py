"""
Start handler for CineAI Bot
Handles /start command and new user interactions
"""

import logging
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

from app.config import config

logger = logging.getLogger(__name__)


@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user_id = message.from_user.id

    try:
        # Check rate limiting
        if not client.check_rate_limit(user_id, "start"):
            return

        # Get or create user
        user = await client.db_service.get_user(user_id)
        if not user:
            # Create new user
            user_data = {
                "telegram_id": user_id,
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "is_bot": message.from_user.is_bot,
                "is_premium": getattr(message.from_user, 'is_premium', False),
                "language_code": message.from_user.language_code
            }
            user = await client.db_service.create_user(user_data)
            logger.info(f"New user created: {user_id}")

        # Handle Force Subscribe if enabled
        if config.features.FORCE_SUBSCRIBE:
            if not await client.handle_force_subscribe(user_id):
                return  # Force subscribe message sent, return early

        # Update user stats
        await client.db_service.update_user_stats(user_id, "start")

        # Parse start command arguments
        args = message.text.split()
        referral_code = None

        if len(args) > 1:
            # Check if it's a referral code
            potential_code = args[1]
            if len(potential_code) == 8 and potential_code.isalnum():
                referral_code = potential_code.upper()
                await handle_referral(client, user_id, referral_code)

        # Send welcome message
        await send_welcome_message(client, message, user, referral_code)

    except Exception as e:
        logger.error(f"Error in start command for user {user_id}: {e}")
        await message.reply_text(
            "❌ An error occurred. Please try again later.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Retry", callback_data="retry_start")]
            ])
        )


async def send_welcome_message(
    client: Client,
    message: Message,
    user,
    referral_code: Optional[str] = None
):
    """Send welcome message to user"""
    try:
        # Build welcome text
        welcome_text = config.force_subscribe.CUSTOM_START_MESSAGE

        if referral_code:
            welcome_text += "\n\n🎉 Welcome! You were referred by a friend!"

        # Add feature information
        features_text = "\n\n🎬 **Features:**\n"
        if config.features.AUTO_FILTER:
            features_text += "• Auto-filter from channels\n"
        if config.features.INLINE_SEARCH:
            features_text += "• Inline search\n"
        if config.features.PM_SEARCH:
            features_text += "• Private search\n"
        if config.features.STREAM:
            features_text += "• Streaming links\n"
        if config.features.PREMIUM:
            features_text += "• Premium features\n"

        welcome_text += features_text

        # Add help text
        bot_info = await client.get_me()
        welcome_text += f"\n\n💡 **How to use:**\n"
        welcome_text += f"• Type `/search <movie>` to search\n"
        welcome_text += f"• Use inline mode: `@{bot_info.username} movie`\n"
        welcome_text += f"• Type `/help` for more commands"

        # Build keyboard
        keyboard_buttons = []

        # Main buttons
        if config.features.INLINE_SEARCH:
            keyboard_buttons.append([
                InlineKeyboardButton("🔍 Search", switch_inline_query_current_chat=""),
                InlineKeyboardButton("📺 Browse", callback_data="browse_files")
            ])

        if config.features.PREMIUM:
            keyboard_buttons.append([
                InlineKeyboardButton("⭐ Premium", callback_data="premium_info")
            ])

        if config.features.REFERRAL:
            keyboard_buttons.append([
                InlineKeyboardButton("👥 Referral", callback_data="referral_info")
            ])

        # Help and tutorial
        help_row = [InlineKeyboardButton("❓ Help", callback_data="help")]
        if config.force_subscribe.CUSTOM_TUTORIAL_BUTTON:
            help_row.append(
                InlineKeyboardButton(
                    config.force_subscribe.CUSTOM_TUTORIAL_BUTTON,
                    callback_data="tutorial"
                )
            )
        keyboard_buttons.append(help_row)

        # Admin button for admins
        if config.is_admin(user.telegram_id):
            keyboard_buttons.append([
                InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")
            ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")
        raise


async def handle_referral(client: Client, user_id: int, referral_code: str):
    """Handle referral code usage"""
    try:
        if not config.features.REFERRAL:
            return

        # Get referral
        referral = await client.db_service.get_referral(referral_code)
        if not referral or not referral.is_active:
            return

        # Check if user already used referral
        user = await client.db_service.get_user(user_id)
        if user and user.referred_by:
            return  # Already used referral

        # Check if user is referring themselves
        if referral.owner_id == user_id:
            return

        # Check if already referred
        if user_id in referral.referred_users:
            return

        # Process referral
        await client.db_service.update_user(user_id, {"referred_by": referral.owner_id})

        # Update referral
        referral_data = {
            "referral_count": referral.referral_count + 1,
            "referred_users": referral.referred_users + [user_id],
            "last_used_at": datetime.utcnow(),
            "conversion_count": referral.conversion_count + 1
        }

        await client.db_service.update_referral(referral_code, referral_data)

        # Check if referrer earns premium
        if referral.auto_grant_premium and not referral.premium_granted:
            referrals_needed = 3
            if referral.referral_count >= referrals_needed:
                await grant_referral_premium(client, referral.owner_id)

        logger.info(f"Referral {referral_code} used by user {user_id}")

    except Exception as e:
        logger.error(f"Error handling referral: {e}")


async def grant_referral_premium(client: Client, referrer_id: int):
    """Grant premium to referrer"""
    try:
        premium_days = 7
        expires_at = datetime.utcnow() + timedelta(days=premium_days)

        # Check if user has existing premium
        existing_premium = await client.db_service.get_premium(referrer_id)
        if existing_premium and existing_premium.is_active:
            # Extend existing premium
            if existing_premium.expires_at:
                expires_at = existing_premium.expires_at + timedelta(days=premium_days)
            else:
                expires_at = None  # Lifetime premium

            await client.db_service.update_premium(
                referrer_id,
                {"expires_at": expires_at}
            )
        else:
            # Create new premium
            premium_data = {
                "user_id": referrer_id,
                "plan": "basic",
                "starts_at": datetime.utcnow(),
                "expires_at": expires_at,
                "payment_method": "referral",
                "granted_reason": "Referral reward - 3 referrals"
            }
            await client.db_service.create_premium(premium_data)

        # Update referral
        await client.db_service.update_referral(
            referral_code,
            {
                "premium_granted": True,
                "premium_granted_at": datetime.utcnow()
            }
        )

        # Notify user
        try:
            await client.send_message(
                referrer_id,
                f"🎉 **Congratulations!**\n\n"
                f"You've earned {premium_days} days of premium access "
                f"through referrals!\n\n"
                f"Thank you for sharing our bot! 🙏",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass  # User might have blocked the bot

        logger.info(f"Premium granted to user {referrer_id} via referrals")

    except Exception as e:
        logger.error(f"Error granting referral premium: {e}")


@Client.on_callback_query(filters.regex("^retry_start$"))
async def retry_start_callback(client: Client, callback_query):
    """Handle retry start callback"""
    user_id = callback_query.from_user.id

    try:
        await callback_query.answer("Retrying...")

        # Send new start message
        await start_command(client, callback_query.message)

    except Exception as e:
        logger.error(f"Error in retry start callback: {e}")
        await callback_query.answer("❌ Error occurred. Please try again.", show_alert=True)


@Client.on_callback_query(filters.regex("^browse_files$"))
async def browse_files_callback(client: Client, callback_query):
    """Handle browse files callback"""
    user_id = callback_query.from_user.id

    try:
        await callback_query.answer()

        # Get recent files
        result = await client.db_service.search_files_with_pagination(
            query="",  # Empty query for all files
            user_id=user_id,
            offset=0,
            limit=10
        )

        if not result["files"]:
            await callback_query.message.edit_text(
                "📂 No files available at the moment.\n"
                "Try searching for a specific movie!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Search", switch_inline_query_current_chat="")]
                ])
            )
            return

        # Send file list
        await send_file_list(client, callback_query.message, result, user_id)

    except Exception as e:
        logger.error(f"Error in browse files callback: {e}")
        await callback_query.answer("❌ Error occurred. Please try again.", show_alert=True)


async def send_file_list(client: Client, message, result, user_id):
    """Send list of files"""
    try:
        files_text = "📂 **Recent Files:**\n\n"

        keyboard_buttons = []

        for i, file in enumerate(result["files"][:10], 1):
            # File title with year
            title = file.display_title
            if file.year:
                title += f" ({file.year})"

            files_text += f"{i}. {title}\n"

            # Add quality and language if available
            details = []
            if file.quality:
                details.append(file.quality.value.upper())
            if file.language:
                details.append(file.language.value.upper())
            if file.file_size:
                size_mb = file.file_size / (1024 * 1024)
                details.append(f"{size_mb:.1f}MB")

            if details:
                files_text += f"   └ {', '.join(details)}\n"

            files_text += "\n"

            # Add send button
            keyboard_buttons.append([
                InlineKeyboardButton(
                    f"📥 {file.title[:20]}...",
                    callback_data=f"send_file_{file.file_id}"
                )
            ])

        # Add pagination if more files
        if result["has_next"]:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    "➡️ Next Page",
                    callback_data=f"browse_page_{result['offset'] + result['limit']}"
                )
            ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await message.edit_text(
            files_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Error sending file list: {e}")
        raise


@Client.on_callback_query(filters.regex("^browse_page_(\\d+)$"))
async def browse_page_callback(client: Client, callback_query):
    """Handle browse pagination"""
    user_id = callback_query.from_user.id
    offset = int(callback_query.matches[0].group(1))

    try:
        await callback_query.answer()

        # Get files for this page
        result = await client.db_service.search_files_with_pagination(
            query="",
            user_id=user_id,
            offset=offset,
            limit=10
        )

        if not result["files"]:
            await callback_query.answer("No more files available.")
            return

        await send_file_list(client, callback_query.message, result, user_id)

    except Exception as e:
        logger.error(f"Error in browse page callback: {e}")
        await callback_query.answer("❌ Error occurred. Please try again.", show_alert=True)