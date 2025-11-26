"""
Inline search handler for CineAI Bot
Handles inline queries and search results
"""

import logging
from typing import List, Optional, Dict, Any
from urllib.parse import quote

from pyrogram import Client, filters
from pyrogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InlineQueryResultVideo,
    InlineQueryResultDocument,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputTextMessageContent,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument
)
from pyrogram.enums import ParseMode

from app.config import config
from services.spellcheck_service import SpellCheckService
from utils.media_utils import format_file_size, get_quality_emoji

logger = logging.getLogger(__name__)

# Initialize spell check service
spell_check = SpellCheckService() if config.features.SPELL_CHECK else None


@Client.on_inline_query()
async def inline_query_handler(client: Client, inline_query: InlineQuery):
    """Handle inline search queries"""
    user_id = inline_query.from_user.id
    query = inline_query.query.strip()

    try:
        # Check if inline search is enabled
        if not config.features.INLINE_SEARCH:
            await inline_query.answer(
                [],
                cache_time=300,
                is_personal=True
            )
            return

        # Check rate limiting
        if not client.check_rate_limit(user_id, "inline_search"):
            await inline_query.answer(
                [],
                cache_time=5,
                is_personal=True
            )
            return

        # Handle empty query
        if not query:
            await send_inline_help(inline_query)
            return

        # Spell check if enabled
        if spell_check:
            corrected_query = await spell_check.correct_query(query)
            if corrected_query != query:
                # Include spell correction suggestion
                await send_spell_correction_suggestion(inline_query, query, corrected_query)

        # Search files
        results = await search_inline_files(client, query, user_id)

        # Send results
        await inline_query.answer(
            results,
            cache_time=60,
            is_personal=True,
            next_offset=str(len(results)) if len(results) >= 10 else ""
        )

        # Update user stats
        await client.db_service.update_user_stats(user_id, "search")

    except Exception as e:
        logger.error(f"Error in inline query handler: {e}")
        await inline_query.answer(
            [],
            cache_time=5,
            is_personal=True
        )


async def send_inline_help(inline_query: InlineQuery):
    """Send help message for empty inline query"""
    help_text = (
        "🔍 **How to search:**\n\n"
        "• Movie name: `Avengers`\n"
        "• Movie with year: `Avengers 2019`\n"
        "• Series: `Game of Thrones S01E01`\n"
        "• Quality: `Avengers HD`\n"
        "• Language: `Avengers Hindi`\n\n"
        "Type a movie name to start searching!"
    )

    result = InlineQueryResultArticle(
        title="🔍 Search Help",
        description="How to use inline search",
        input_message_content=InputTextMessageContent(
            message_text=help_text,
            parse_mode=ParseMode.MARKDOWN
        ),
        thumbnail_url="https://img.icons8.com/color/96/search.png",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📖 Full Help",
                callback_data="help"
            )]
        ])
    )

    await inline_query.answer([result], cache_time=300, is_personal=True)


async def send_spell_correction_suggestion(
    inline_query: InlineQuery,
    original_query: str,
    corrected_query: str
):
    """Send spell correction suggestion"""
    correction_text = (
        f"Did you mean: **{corrected_query}**?\n\n"
        f"Original: {original_query}\n"
        f"Corrected: {corrected_query}"
    )

    result = InlineQueryResultArticle(
        title="✨ Spell Correction",
        description=f"Showing results for: {corrected_query}",
        input_message_content=InputTextMessageContent(
            message_text=correction_text,
            parse_mode=ParseMode.MARKDOWN
        ),
        thumbnail_url="https://img.icons8.com/color/96/spell-check.png"
    )

    await inline_query.answer([result], cache_time=60, is_personal=True)


async def search_inline_files(
    client: Client,
    query: str,
    user_id: int,
    offset: int = 0,
    limit: int = 10
) -> List:
    """Search files for inline results"""
    try:
        # Search in database
        result = await client.db_service.search_files_with_pagination(
            query=query,
            user_id=user_id,
            offset=offset,
            limit=limit
        )

        inline_results = []

        for file in result["files"]:
            inline_result = await create_inline_result(client, file, user_id)
            if inline_result:
                inline_results.append(inline_result)

        return inline_results

    except Exception as e:
        logger.error(f"Error searching inline files: {e}")
        return []


async def create_inline_result(client: Client, file, user_id: int):
    """Create inline result for a file"""
    try:
        # Check if user can access this file
        if file.is_premium:
            user_premium = await client.db_service.get_premium(user_id)
            if not user_premium or not user_premium.is_active:
                return create_premium_only_result(file)

        if file.verification_required:
            # Check if user is verified
            user = await client.db_service.get_user(user_id)
            if not user or not user.is_verified:
                return create_verification_required_result(file)

        # Create result based on file type
        if file.file_type == "video":
            return await create_video_inline_result(client, file)
        elif file.file_type == "document":
            return await create_document_inline_result(client, file)
        elif file.file_type == "photo":
            return await create_photo_inline_result(client, file)
        else:
            return create_generic_inline_result(file)

    except Exception as e:
        logger.error(f"Error creating inline result for file {file.file_id}: {e}")
        return None


async def create_video_inline_result(client: Client, file):
    """Create inline result for video file"""
    title = file.display_title
    description_parts = []

    # Add quality
    if file.quality:
        description_parts.append(f"Quality: {file.quality.value.upper()}")

    # Add language
    if file.language:
        description_parts.append(f"Language: {file.language.value.upper()}")

    # Add file size
    if file.file_size:
        description_parts.append(f"Size: {format_file_size(file.file_size)}")

    # Add duration
    if file.duration:
        hours = file.duration // 3600
        minutes = (file.duration % 3600) // 60
        if hours > 0:
            description_parts.append(f"Duration: {hours}h {minutes}m")
        else:
            description_parts.append(f"Duration: {minutes}m")

    description = " | ".join(description_parts)

    # Create keyboard
    keyboard = create_file_keyboard(file)

    # Use thumbnail if available
    thumbnail_url = None
    if file.thumbnail_id:
        try:
            # Get thumbnail URL (this would need implementation)
            thumbnail_url = f"https://api.telegram.org/file/bot{config.telegram.BOT_TOKEN}/{file.thumbnail_id}"
        except Exception:
            pass

    # Add IMDB info if available
    if file.imdb_id:
        description += f" | IMDB: {file.imdb_id}"
        if file.rating:
            description += f" ⭐ {file.rating}/10"

    result = InlineQueryResultVideo(
        id=file.file_id,
        title=title,
        description=description,
        video_file_id=file.file_id,
        caption=create_file_caption(file),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
        thumbnail_url=thumbnail_url
    )

    return result


async def create_document_inline_result(client: Client, file):
    """Create inline result for document file"""
    title = file.display_title
    description_parts = []

    # Add file type
    description_parts.append("Document")

    # Add file size
    if file.file_size:
        description_parts.append(f"Size: {format_file_size(file.file_size)}")

    description = " | ".join(description_parts)

    result = InlineQueryResultDocument(
        id=file.file_id,
        title=title,
        description=description,
        document_file_id=file.file_id,
        caption=create_file_caption(file),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_file_keyboard(file)
    )

    return result


async def create_photo_inline_result(client: Client, file):
    """Create inline result for photo file"""
    title = file.display_title

    result = InlineQueryResultPhoto(
        id=file.file_id,
        title=title,
        photo_file_id=file.file_id,
        caption=create_file_caption(file),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_file_keyboard(file)
    )

    return result


def create_generic_inline_result(file):
    """Create generic inline result"""
    title = file.display_title
    description = f"Type: {file.file_type.value}"

    if file.file_size:
        description += f" | Size: {format_file_size(file.file_size)}"

    result = InlineQueryResultArticle(
        id=file.file_id,
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=create_file_caption(file),
            parse_mode=ParseMode.MARKDOWN
        ),
        reply_markup=create_file_keyboard(file)
    )

    return result


def create_premium_only_result(file):
    """Create premium-only inline result"""
    title = f"🔒 {file.display_title}"
    description = "Premium content - Upgrade to access"

    result = InlineQueryResultArticle(
        id=f"premium_{file.file_id}",
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=(
                f"🔒 **Premium Content**\n\n"
                f"**{file.display_title}**\n\n"
                f"This content is only available to premium users.\n\n"
                f"Upgrade to premium to access exclusive content!"
            ),
            parse_mode=ParseMode.MARKDOWN
        ),
        thumbnail_url="https://img.icons8.com/color/96/crown.png",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "⭐ Get Premium",
                callback_data="premium_info"
            )]
        ])
    )

    return result


def create_verification_required_result(file):
    """Create verification required inline result"""
    title = f"🔐 {file.display_title}"
    description = "Verification required - Complete verification to access"

    result = InlineQueryResultArticle(
        id=f"verify_{file.file_id}",
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=(
                f"🔐 **Verification Required**\n\n"
                f"**{file.display_title}**\n\n"
                f"This content requires verification to access.\n\n"
                f"Complete verification to continue!"
            ),
            parse_mode=ParseMode.MARKDOWN
        ),
        thumbnail_url="https://img.icons8.com/color/96/verified.png",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "✅ Verify Now",
                callback_data="start_verification"
            )]
        ])
    )

    return result


def create_file_keyboard(file):
    """Create inline keyboard for file"""
    buttons = []

    # Main action buttons
    main_row = []
    main_row.append(InlineKeyboardButton(
        "📥 Download",
        callback_data=f"send_file_{file.file_id}"
    ))

    if config.features.STREAM and file.stream_url:
        main_row.append(InlineKeyboardButton(
            "🎬 Stream",
            url=file.stream_url
        ))

    if main_row:
        buttons.append(main_row)

    # Additional action buttons
    action_row = []
    if config.features.CLONE:
        action_row.append(InlineKeyboardButton(
            "📋 Clone",
            callback_data=f"clone_file_{file.file_id}"
        ))

    if config.features.URL_SHORTENER and file.short_url:
        action_row.append(InlineKeyboardButton(
            "🔗 Share",
            url=file.short_url
        ))

    if action_row:
        buttons.append(action_row)

    # Info row
    info_row = []
    if file.imdb_id:
        info_row.append(InlineKeyboardButton(
            "🎬 IMDB",
            url=f"https://www.imdb.com/title/{file.imdb_id}"
        ))

    if info_row:
        buttons.append(info_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None


def create_file_caption(file):
    """Create caption for file"""
    caption_parts = []

    # Title with emoji
    title_emoji = "🎬" if file.file_type == "video" else "📄"
    caption_parts.append(f"{title_emoji} **{file.display_title}**")

    # Year
    if file.year:
        caption_parts.append(f"📅 Year: {file.year}")

    # Quality
    if file.quality:
        caption_parts.append(f"📺 Quality: {file.quality.value.upper()}")

    # Language
    if file.language:
        caption_parts.append(f"🌐 Language: {file.language.value.upper()}")

    # File size
    if file.file_size:
        caption_parts.append(f"💾 Size: {format_file_size(file.file_size)}")

    # Duration for videos
    if file.duration and file.file_type == "video":
        hours = file.duration // 3600
        minutes = (file.duration % 3600) // 60
        if hours > 0:
            caption_parts.append(f"⏱️ Duration: {hours}h {minutes}m")
        else:
            caption_parts.append(f"⏱️ Duration: {minutes}m")

    # IMDB info
    if file.imdb_id:
        imdb_text = f"🎭 IMDB: [{file.imdb_id}](https://www.imdb.com/title/{file.imdb_id})"
        if file.rating:
            imdb_text += f" ⭐ {file.rating}/10"
        caption_parts.append(imdb_text)

    # Tags
    if file.tags:
        caption_parts.append(f"🏷️ Tags: {', '.join(file.tags)}")

    # Description
    if file.description:
        caption_parts.append(f"\n📝 {file.description}")

    # Footer
    caption_parts.append(f"\n\n_Requested via @{bot.me.username}_")

    return "\n".join(caption_parts)


async def generate_inline_results(
    client: Client,
    query: str,
    user_id: int,
    offset: str = ""
) -> List:
    """Generate inline search results (callable from bot.py)"""
    try:
        offset_int = int(offset) if offset else 0
        return await search_inline_files(client, query, user_id, offset_int)
    except ValueError:
        return await search_inline_files(client, query, user_id, 0)