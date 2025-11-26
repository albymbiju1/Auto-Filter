"""
Channel listener for CineAI Bot
Handles auto-indexing from linked channels
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.types import Message, Video, Document, Photo, Audio
from pyrogram.enums import ChatType, ParseMode

from app.config import config
from app.bot import bot
from utils.media_utils import (
    extract_year_from_title,
    extract_season_episode,
    detect_quality_from_title,
    detect_language_from_title,
    clean_title,
    extract_imdb_id,
    create_search_keywords
)
from services.imdb_service import IMDBService

logger = logging.getLogger(__name__)

# Initialize IMDB service
imdb_service = IMDBService() if config.features.IMDB_INTEGRATION else None


@bot.on_message(
    filters.group &
    ~filters.private &
    ~filters.bot &
    ~filters.command(['start', 'help', 'search'])
)
async def channel_message_handler(client: Client, message: Message):
    """Handle messages in linked channels for auto-indexing"""
    if not config.features.AUTO_FILTER:
        return

    try:
        chat_id = message.chat.id
        message_id = message.id

        # Check if this is a linked channel
        channel = await client.db_service.get_channel(chat_id)
        if not channel or not channel.can_index:
            return

        # Check if message already indexed
        existing_file = await client.db_service.get_file(str(message_id))
        if existing_file:
            return

        # Process the message
        await process_channel_message(client, message, channel)

        # Update channel stats
        await update_channel_stats(client, channel, message_id)

    except Exception as e:
        logger.error(f"Error processing channel message {message.id}: {e}")


async def process_channel_message(client: Client, message: Message, channel):
    """Process a channel message for indexing"""
    try:
        # Check if message contains media
        if not message.media:
            return

        # Extract file information based on media type
        file_data = await extract_file_data(message)
        if not file_data:
            return

        # Validate file data
        if not validate_file_for_indexing(file_data, channel):
            return

        # Enhance with additional metadata
        await enhance_file_metadata(file_data, message)

        # Save to database
        await save_indexed_file(client, file_data, channel, message)

        logger.info(f"Indexed file: {file_data['title']} from channel {channel.title}")

    except Exception as e:
        logger.error(f"Error processing channel message: {e}")


async def extract_file_data(message: Message) -> Optional[Dict[str, Any]]:
    """Extract file data from message"""
    file_data = None

    try:
        if message.video:
            file_data = await extract_video_data(message.video, message)
        elif message.document:
            file_data = await extract_document_data(message.document, message)
        elif message.photo:
            file_data = await extract_photo_data(message.photo, message)
        elif message.audio:
            file_data = await extract_audio_data(message.audio, message)

        # Add common message data
        if file_data:
            file_data.update({
                'message_id': message.id,
                'chat_id': message.chat.id,
                'caption': message.caption,
                'text': message.text or message.caption,
                'forward_from': message.forward_from,
                'forward_from_chat': message.forward_from_chat,
                'date': message.date,
                'media_group_id': message.media_group_id
            })

        return file_data

    except Exception as e:
        logger.error(f"Error extracting file data: {e}")
        return None


async def extract_video_data(video: Video, message: Message) -> Dict[str, Any]:
    """Extract data from video message"""
    return {
        'file_type': 'video',
        'file_id': video.file_id,
        'file_name': video.file_name,
        'file_size': video.file_size,
        'duration': video.duration,
        'width': video.width,
        'height': video.height,
        'mime_type': video.mime_type,
        'thumbnail_id': video.thumbs[0].file_id if video.thumbs else None,
        'resolution': f"{video.width}x{video.height}" if video.width and video.height else None
    }


async def extract_document_data(document: Document, message: Message) -> Dict[str, Any]:
    """Extract data from document message"""
    return {
        'file_type': 'document',
        'file_id': document.file_id,
        'file_name': document.file_name,
        'file_size': document.file_size,
        'mime_type': document.mime_type,
        'thumbnail_id': document.thumbs[0].file_id if document.thumbs else None
    }


async def extract_photo_data(photo, message: Message) -> Dict[str, Any]:
    """Extract data from photo message"""
    # Get the largest photo
    largest_photo = photo[-1] if photo else None
    if not largest_photo:
        return {}

    return {
        'file_type': 'photo',
        'file_id': largest_photo.file_id,
        'file_size': largest_photo.file_size,
        'width': largest_photo.width,
        'height': largest_photo.height,
        'resolution': f"{largest_photo.width}x{largest_photo.height}" if largest_photo.width and largest_photo.height else None
    }


async def extract_audio_data(audio, message: Message) -> Dict[str, Any]:
    """Extract data from audio message"""
    return {
        'file_type': 'audio',
        'file_id': audio.file_id,
        'file_name': audio.file_name,
        'file_size': audio.file_size,
        'duration': audio.duration,
        'mime_type': audio.mime_type,
        'thumbnail_id': audio.thumbs[0].file_id if audio.thumbs else None
    }


def validate_file_for_indexing(file_data: Dict[str, Any], channel) -> bool:
    """Validate if file should be indexed"""
    # Check file size limits
    if channel.min_file_size > 0 and file_data.get('file_size', 0) < channel.min_file_size:
        return False

    if channel.max_file_size > 0 and file_data.get('file_size', 0) > channel.max_file_size:
        return False

    # Check file type
    if file_data.get('file_type') not in channel.file_types_to_index:
        return False

    # Check file name
    file_name = file_data.get('file_name', '')
    if not file_name:
        return False

    # Check exclude keywords
    text = (file_data.get('text', '') + ' ' + file_data.get('file_name', '')).lower()
    for keyword in channel.exclude_keywords:
        if keyword.lower() in text:
            return False

    # Check include keywords (if specified)
    if channel.include_keywords:
        found_keyword = False
        for keyword in channel.include_keywords:
            if keyword.lower() in text:
                found_keyword = True
                break
        if not found_keyword:
            return False

    return True


async def enhance_file_metadata(file_data: Dict[str, Any], message: Message):
    """Enhance file metadata with additional information"""
    try:
        # Extract title from filename or caption
        title = extract_title_from_message(file_data, message)
        if not title:
            return

        file_data['title'] = title

        # Clean title
        file_data['clean_title'] = clean_title(title)

        # Extract year
        year = extract_year_from_title(title)
        if year:
            file_data['year'] = year

        # Extract season/episode for series
        season, episode = extract_season_episode(title)
        if season and episode:
            file_data['season'] = season
            file_data['episode'] = episode

        # Detect quality
        quality = detect_quality_from_title(title)
        if quality:
            file_data['quality'] = quality

        # Detect language
        language = detect_language_from_title(title)
        if language:
            file_data['language'] = language

        # Extract IMDB ID
        imdb_id = extract_imdb_id(message.text or message.caption or '')
        if imdb_id:
            file_data['imdb_id'] = imdb_id

        # Create search keywords
        keywords = create_search_keywords(title)
        if keywords:
            file_data['tags'] = keywords

        # Extract description from caption
        caption = message.caption or message.text or ''
        if caption and len(caption) > len(title):
            # Remove title from caption to get description
            description = caption.replace(title, '').strip()
            if description:
                file_data['description'] = description[:500]  # Limit description length

        # Get IMDB data if available
        if imdb_service and (file_data.get('imdb_id') or file_data.get('title')):
            await enrich_with_imdb_data(file_data)

    except Exception as e:
        logger.error(f"Error enhancing file metadata: {e}")


def extract_title_from_message(file_data: Dict[str, Any], message: Message) -> Optional[str]:
    """Extract title from message"""
    # Try different sources for title
    sources = []

    # File name
    file_name = file_data.get('file_name', '')
    if file_name:
        sources.append(file_name)

    # Caption
    caption = message.caption or ''
    if caption:
        sources.append(caption)

    # Text
    text = message.text or ''
    if text:
        sources.append(text)

    # Find the best title
    for source in sources:
        # Remove file extensions
        title = source.strip()
        title = title.rsplit('.', 1)[0] if '.' in title else title

        # Clean up common patterns
        title = clean_title(title)

        if title and len(title) > 3:  # Minimum title length
            return title

    return None


async def enrich_with_imdb_data(file_data: Dict[str, Any]):
    """Enrich file data with IMDB information"""
    try:
        if not imdb_service:
            return

        # Search IMDB
        imdb_data = await imdb_service.search_movie(
            title=file_data.get('title', ''),
            year=file_data.get('year')
        )

        if not imdb_data:
            return

        # Update file data with IMDB information
        if imdb_data.get('imdb_id'):
            file_data['imdb_id'] = imdb_data['imdb_id']

        if imdb_data.get('rating'):
            file_data['rating'] = imdb_data['rating']

        if imdb_data.get('year'):
            file_data['year'] = imdb_data['year']

        if imdb_data.get('genre'):
            file_data['genre'] = imdb_data['genre']

        if imdb_data.get('cast'):
            file_data['cast'] = imdb_data['cast'][:10]  # Limit to top 10 cast members

        if imdb_data.get('director'):
            file_data['director'] = imdb_data['director']

        if imdb_data.get('poster_url'):
            # Store poster URL for thumbnail
            file_data['poster_url'] = imdb_data['poster_url']

        logger.info(f"Enriched {file_data.get('title')} with IMDB data")

    except Exception as e:
        logger.error(f"Error enriching with IMDB data: {e}")


async def save_indexed_file(client: Client, file_data: Dict[str, Any], channel, message: Message):
    """Save indexed file to database"""
    try:
        # Prepare file record
        file_record = {
            'message_id': message.id,
            'chat_id': channel.chat_id,
            'file_id': file_data['file_id'],
            'file_type': file_data['file_type'],
            'file_name': file_data.get('file_name'),
            'file_size': file_data.get('file_size', 0),
            'title': file_data['title'],
            'description': file_data.get('description'),
            'imdb_id': file_data.get('imdb_id'),
            'year': file_data.get('year'),
            'season': file_data.get('season'),
            'episode': file_data.get('episode'),
            'quality': file_data.get('quality'),
            'language': file_data.get('language'),
            'duration': file_data.get('duration'),
            'resolution': file_data.get('resolution'),
            'codec': file_data.get('codec'),
            'tags': file_data.get('tags', []),
            'genre': file_data.get('genre', []),
            'cast': file_data.get('cast', []),
            'director': file_data.get('director'),
            'rating': file_data.get('rating'),
            'thumbnail_id': file_data.get('thumbnail_id'),
            'source': 'channel',
            'indexed_by': None,  # Auto-indexed
            'auto_delete': channel.auto_delete_files,
            'auto_delete_after': channel.auto_delete_after if channel.auto_delete_files else None,
            'is_premium': channel.is_premium_only,
            'verification_required': channel.verification_required,
            'metadata': {
                'channel_title': channel.title,
                'indexed_at': datetime.utcnow().isoformat(),
                'original_caption': message.caption,
                'original_text': message.text
            }
        }

        # Save to database
        await client.db_service.create_file(file_record)

        # Update channel last indexed message
        await client.db_service.update_channel(
            channel.chat_id,
            {
                'last_indexed_message_id': message.id,
                'last_indexed_at': datetime.utcnow(),
                'total_indexed_messages': channel.total_indexed_messages + 1,
                'total_files': channel.total_files + 1,
                'error_count': 0  # Reset error count on success
            }
        )

        # Cache file metadata if Redis is available
        if client.redis_service:
            await client.redis_service.cache_file_metadata(
                file_data['file_id'],
                file_record,
                ttl=7200  # 2 hours
            )

    except Exception as e:
        logger.error(f"Error saving indexed file: {e}")
        # Update channel error count
        await client.db_service.update_channel(
            channel.chat_id,
            {
                'error_count': channel.error_count + 1,
                'last_error': str(e)
            }
        )


async def update_channel_stats(client: Client, channel, message_id: int):
    """Update channel indexing statistics"""
    try:
        # Update last indexed message ID
        if message_id > channel.last_indexed_message_id:
            await client.db_service.update_channel(
                channel.chat_id,
                {'last_indexed_message_id': message_id}
            )

    except Exception as e:
        logger.error(f"Error updating channel stats: {e}")


async def cleanup_old_files_task():
    """Background task to clean up old files"""
    if not config.features.AUTO_FILTER:
        return

    while True:
        try:
            # Get all channels with auto-delete enabled
            channels = await client.db_service.get_all_channels()
            auto_delete_channels = [
                ch for ch in channels
                if ch.auto_delete and ch.auto_delete_after
            ]

            for channel in auto_delete_channels:
                # Calculate cutoff date
                cutoff_date = datetime.utcnow() - timedelta(seconds=channel.auto_delete_after)

                # Delete old files from this channel
                # This would need to be implemented in the database service
                deleted_count = await client.db_service.cleanup_channel_files(
                    channel.chat_id,
                    cutoff_date
                )

                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old files from channel {channel.title}")

            # Wait 24 hours before next cleanup
            await asyncio.sleep(86400)

        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(3600)  # Wait 1 hour on error


async def index_missing_messages_task():
    """Background task to index missing messages"""
    if not config.features.AUTO_FILTER:
        return

    while True:
        try:
            # Get all linked channels
            channels = await client.db_service.get_all_channels()
            linked_channels = [ch for ch in channels if ch.is_linked and ch.can_index]

            for channel in linked_channels:
                await index_channel_messages(client, channel)

            # Wait 1 hour before next check
            await asyncio.sleep(3600)

        except Exception as e:
            logger.error(f"Error in index missing messages task: {e}")
            await asyncio.sleep(1800)  # Wait 30 minutes on error


async def index_channel_messages(client: Client, channel):
    """Index missing messages from a channel"""
    try:
        # Get messages since last indexed
        start_id = channel.last_indexed_message_id + 1
        limit = min(channel.max_messages_per_batch, 200)  # Limit to 200 messages per batch

        # Fetch messages from Telegram
        messages = []
        async for message in client.get_chat_history(
            chat_id=channel.chat_id,
            offset_id=start_id,
            limit=limit
        ):
            messages.append(message)

        # Process messages in reverse order (oldest first)
        for message in reversed(messages):
            await process_channel_message(client, message, channel)

        logger.info(f"Indexed {len(messages)} messages from channel {channel.title}")

    except Exception as e:
        logger.error(f"Error indexing messages for channel {channel.title}: {e}")


# Start background tasks
async def start_background_tasks():
    """Start channel indexing background tasks"""
    if config.features.AUTO_FILTER:
        asyncio.create_task(cleanup_old_files_task())
        asyncio.create_task(index_missing_messages_task())
        logger.info("Channel indexing background tasks started")