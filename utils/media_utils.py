"""
Media utilities for CineAI Bot
Helper functions for file handling, formatting, and media processing
"""

import os
import re
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    if i == 0:
        return f"{int(size)}{size_names[i]}"
    else:
        return f"{size:.1f}{size_names[i]}"


def get_quality_emoji(quality) -> str:
    """Get emoji for video quality"""
    quality_emojis = {
        "SD": "📱",
        "HD": "📺",
        "FHD": "🖥️",
        "UHD": "🎬",
        "4K": "🎬",
        "HDR": "🌈"
    }
    return quality_emojis.get(str(quality).upper(), "🎬")


def get_language_emoji(language) -> str:
    """Get emoji for language"""
    language_emojis = {
        "EN": "🇬🇧",
        "HI": "🇮🇳",
        "TA": "🇱🇰",
        "TE": "🇮🇳",
        "ML": "🇮🇳",
        "KN": "🇮🇳",
        "BN": "🇧🇩",
        "MR": "🇮🇳",
        "GJ": "🇮🇳",
        "PB": "🇮🇳",
        "ENGLISH": "🇬🇧",
        "HINDI": "🇮🇳",
        "TAMIL": "🇱🇰",
        "TELUGU": "🇮🇳",
        "MALAYALAM": "🇮🇳",
        "KANNADA": "🇮🇳",
        "BENGALI": "🇧🇩",
        "MARATHI": "🇮🇳",
        "GUJARATI": "🇮🇳",
        "PUNJABI": "🇮🇳"
    }
    return language_emojis.get(str(language).upper(), "🌐")


def parse_duration(seconds: int) -> str:
    """Parse duration in seconds to human readable format"""
    if not seconds:
        return "Unknown"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {remaining_seconds}s"
    elif minutes > 0:
        return f"{minutes}m {remaining_seconds}s"
    else:
        return f"{remaining_seconds}s"


def extract_year_from_title(title: str) -> Optional[int]:
    """Extract year from movie title"""
    # Look for year patterns like (2019), [2019], or just 2019
    year_patterns = [
        r'\((\d{4})\)',  # (2019)
        r'\[(\d{4})\]',  # [2019]
        r'\b(\d{4})\b'   # 2019
    ]

    for pattern in year_patterns:
        match = re.search(pattern, title)
        if match:
            year = int(match.group(1))
            # Validate year is reasonable
            current_year = datetime.now().year
            if 1900 <= year <= current_year + 2:
                return year

    return None


def extract_season_episode(title: str) -> tuple[Optional[int], Optional[int]]:
    """Extract season and episode numbers from title"""
    # Common patterns for series episodes
    patterns = [
        r'S(\d{1,2})E(\d{1,2})',  # S01E01
        r'Season\s*(\d{1,2})\s*Episode\s*(\d{1,2})',  # Season 1 Episode 1
        r'(\d{1,2})x(\d{1,2})',  # 1x01
        r'Ep\s*(\d{1,2})',  # Ep 01 (season unknown)
        r'Episode\s*(\d{1,2})',  # Episode 1 (season unknown)
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                return int(match.group(1)), int(match.group(2))
            else:
                return None, int(match.group(1))

    return None, None


def detect_quality_from_title(title: str) -> Optional[str]:
    """Detect video quality from title"""
    quality_patterns = {
        "4K": [r'4K', r'2160p', r'UHD'],
        "FHD": [r'1080p', r'Full HD', r'FHD'],
        "HD": [r'720p', r'HD'],
        "SD": [r'480p', r'360p', r'SD'],
        "HDR": [r'HDR', r'High Dynamic Range']
    }

    # Check for higher qualities first (they're more specific)
    for quality in ["4K", "FHD", "HDR", "HD", "SD"]:
        for pattern in quality_patterns[quality]:
            if re.search(pattern, title, re.IGNORECASE):
                return quality

    return None


def detect_language_from_title(title: str) -> Optional[str]:
    """Detect language from title"""
    language_patterns = {
        "HI": [r'Hindi', r'\bHI\b', r'देसी'],
        "TA": [r'Tamil', r'\bTA\b', r'தமிழ்'],
        "TE": [r'Telugu', r'\bTE\b', r'తెలుగు'],
        "ML": [r'Malayalam', r'\bML\b', r'മലയാളം'],
        "KN": [r'Kannada', r'\bKN\b', r'ಕನ್ನಡ'],
        "BN": [r'Bengali', r'\bBN\b', r'বাংলা'],
        "MR": [r'Marathi', r'\bMR\b', r'मराठी'],
        "GJ": [r'Gujarati', r'\bGJ\b', r'ગુજરાતી'],
        "PB": [r'Punjabi', r'\bPB\b', r'ਪੰਜਾਬੀ'],
        "EN": [r'English', r'\bEN\b', r'Eng']
    }

    for lang_code, patterns in language_patterns.items():
        for pattern in patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return lang_code

    return None


def clean_title(title: str) -> str:
    """Clean movie title by removing common patterns"""
    if not title:
        return ""

    # Remove file extensions
    title = re.sub(r'\.(mp4|mkv|avi|mov|wmv|flv|webm|mpg|mpeg|m4v)$', '', title, flags=re.IGNORECASE)

    # Remove quality indicators
    title = re.sub(r'\b(1080p|720p|480p|360p|4K|HD|FHD|SD|HDR)\b', '', title, flags=re.IGNORECASE)

    # Remove language indicators
    title = re.sub(r'\b(Hindi|Tamil|Telugu|Malayalam|Kannada|Bengali|Marathi|Gujarati|Punjabi|English|HI|TA|TE|ML|KN|BN|MR|GJ|PB|EN)\b', '', title, flags=re.IGNORECASE)

    # Remove year in parentheses
    title = re.sub(r'\(\d{4}\)', '', title)

    # Remove brackets and special characters
    title = re.sub(r'[\[\](){}]', '', title)

    # Remove extra whitespace and dots
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'\.+', ' ', title)
    title = title.strip()

    # Capitalize words
    title = ' '.join(word.capitalize() for word in title.split())

    return title


def extract_imdb_id(text: str) -> Optional[str]:
    """Extract IMDB ID from text"""
    # Look for IMDB patterns like tt1234567
    imdb_pattern = r'(tt\d{7,8})'
    match = re.search(imdb_pattern, text, re.IGNORECASE)
    return match.group(1) if match else None


def create_file_caption(file_data: Dict[str, Any]) -> str:
    """Create formatted caption for file"""
    caption_parts = []

    # Title with emoji
    file_type = file_data.get('file_type', 'video')
    if file_type == 'video':
        title_emoji = "🎬"
    elif file_type == 'document':
        title_emoji = "📄"
    elif file_type == 'photo':
        title_emoji = "🖼️"
    else:
        title_emoji = "📁"

    title = file_data.get('title', 'Unknown')
    caption_parts.append(f"{title_emoji} **{title}**")

    # Year
    year = file_data.get('year')
    if year:
        caption_parts.append(f"📅 Year: {year}")

    # Quality
    quality = file_data.get('quality')
    if quality:
        quality_emoji = get_quality_emoji(quality)
        caption_parts.append(f"📺 Quality: {quality_emoji} {quality.upper()}")

    # Language
    language = file_data.get('language')
    if language:
        language_emoji = get_language_emoji(language)
        caption_parts.append(f"🌐 Language: {language_emoji} {language.upper()}")

    # File size
    file_size = file_data.get('file_size')
    if file_size:
        caption_parts.append(f"💾 Size: {format_file_size(file_size)}")

    # Duration for videos
    duration = file_data.get('duration')
    if duration and file_type == 'video':
        duration_str = parse_duration(duration)
        caption_parts.append(f"⏱️ Duration: {duration_str}")

    # Series info
    season = file_data.get('season')
    episode = file_data.get('episode')
    if season and episode:
        caption_parts.append(f"📺 Season: {season:02d}, Episode: {episode:02d}")

    # IMDB info
    imdb_id = file_data.get('imdb_id')
    rating = file_data.get('rating')
    if imdb_id:
        imdb_text = f"🎭 IMDB: [{imdb_id}](https://www.imdb.com/title/{imdb_id}/)"
        if rating:
            imdb_text += f" ⭐ {rating}/10"
        caption_parts.append(imdb_text)

    # Tags
    tags = file_data.get('tags', [])
    if tags:
        caption_parts.append(f"🏷️ Tags: {', '.join(tags)}")

    # Description
    description = file_data.get('description')
    if description:
        caption_parts.append(f"\n📝 {description}")

    # Footer
    caption_parts.append(f"\n\n_Requested via CineAI Bot_")

    return "\n".join(caption_parts)


def validate_file_name(file_name: str) -> bool:
    """Validate file name for security"""
    if not file_name:
        return False

    # Check for dangerous patterns
    dangerous_patterns = [
        r'\.\./',  # Directory traversal
        r'^/',     # Absolute path
        r'\x00',   # Null byte
        r'[<>:"|?*]',  # Invalid characters for filenames
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, file_name):
            return False

    # Check file extension
    allowed_extensions = {
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mpg', '.mpeg', '.m4v',  # Video
        '.pdf', '.doc', '.docx', '.txt', '.rtf',  # Documents
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp',  # Images
        '.mp3', '.wav', '.flac', '.aac', '.ogg',  # Audio
        '.zip', '.rar', '.7z', '.tar', '.gz'  # Archives
    }

    _, ext = os.path.splitext(file_name.lower())
    return ext in allowed_extensions


def generate_thumbnail_url(file_id: str, bot_token: str) -> str:
    """Generate thumbnail URL for file"""
    return f"https://api.telegram.org/file/bot{bot_token}/{file_id}"


def parse_telegram_file_id(file_id: str) -> Dict[str, Any]:
    """Parse Telegram file ID to extract information"""
    # Telegram file IDs are base64 encoded JSON
    try:
        import base64
        import json

        # Add padding if needed
        padding = '=' * (-len(file_id) % 4)
        decoded = base64.b64decode(file_id + padding)
        file_info = json.loads(decoded)

        return {
            'file_type': file_info.get('_', 'unknown'),
            'file_id': file_info.get('file_id', ''),
            'file_unique_id': file_info.get('file_unique_id', ''),
            'file_size': file_info.get('file_size', 0)
        }
    except Exception as e:
        logger.error(f"Error parsing file ID {file_id}: {e}")
        return {
            'file_type': 'unknown',
            'file_id': file_id,
            'file_unique_id': '',
            'file_size': 0
        }


def create_search_keywords(title: str, alt_titles: List[str] = None, tags: List[str] = None) -> List[str]:
    """Create searchable keywords from title and metadata"""
    keywords = []

    # Add main title words
    if title:
        # Split title into words and clean them
        words = re.findall(r'\b\w+\b', title.lower())
        keywords.extend(words)

    # Add alternative titles
    if alt_titles:
        for alt_title in alt_titles:
            words = re.findall(r'\b\w+\b', alt_title.lower())
            keywords.extend(words)

    # Add tags
    if tags:
        keywords.extend([tag.lower() for tag in tags])

    # Remove duplicates and common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}

    keywords = [kw for kw in keywords if kw not in stop_words and len(kw) > 1]
    keywords = list(set(keywords))  # Remove duplicates

    return keywords


def estimate_download_time(file_size_bytes: int, connection_speed_mbps: float = 10.0) -> str:
    """Estimate download time based on file size and connection speed"""
    if file_size_bytes <= 0 or connection_speed_mbps <= 0:
        return "Unknown"

    # Convert to megabits
    file_size_megabits = (file_size_bytes * 8) / (1024 * 1024)

    # Calculate time in seconds
    time_seconds = file_size_megabits / connection_speed_mbps

    # Format time
    if time_seconds < 60:
        return f"{int(time_seconds)}s"
    elif time_seconds < 3600:
        minutes = int(time_seconds // 60)
        seconds = int(time_seconds % 60)
        return f"{minutes}m {seconds}s"
    else:
        hours = int(time_seconds // 3600)
        minutes = int((time_seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def is_valid_imdb_id(imdb_id: str) -> bool:
    """Validate IMDB ID format"""
    if not imdb_id:
        return False

    # IMDB IDs start with 'tt' followed by 7-8 digits
    pattern = r'^tt\d{7,8}$'
    return bool(re.match(pattern, imdb_id))


def create_shareable_text(file_data: Dict[str, Any]) -> str:
    """Create shareable text for social media"""
    title = file_data.get('title', 'Unknown')
    year = file_data.get('year')
    quality = file_data.get('quality')
    rating = file_data.get('rating')

    share_text = f"🎬 {title}"
    if year:
        share_text += f" ({year})"
    if quality:
        share_text += f" [{quality.upper()}]"
    if rating:
        share_text += f" ⭐ {rating}/10"

    share_text += "\n\nAvailable on CineAI Bot! 🍿"

    return share_text