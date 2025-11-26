"""
Spell check service for CineAI Bot
Provides typo correction and fuzzy matching for search queries
"""

import logging
from typing import Optional, List, Dict, Tuple
import re

try:
    from fuzzywuzzy import fuzz, process
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False
    logging.warning("fuzzywuzzy not available, spell check will be limited")

logger = logging.getLogger(__name__)


class SpellCheckService:
    """Spell check and typo correction service"""

    def __init__(self):
        self.movie_titles = set()
        self.common_words = set()
        self.quality_terms = set()
        self.language_terms = set()
        self._initialize_dictionaries()

    def _initialize_dictionaries(self):
        """Initialize common dictionaries for spell checking"""
        # Common movie words
        self.common_words.update([
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'movie', 'movies', 'film', 'films', 'cinema', 'picture', 'pictures',
            'avengers', 'marvel', 'dc', 'comics', 'superhero', 'action', 'adventure',
            'drama', 'comedy', 'thriller', 'horror', 'romance', 'sci-fi', 'fantasy',
            'animation', 'animated', 'cartoon', 'anime', 'series', 'season', 'episode',
            'part', 'chapter', 'volume', 'edition', 'version', 'director', 'actor',
            'actress', 'cast', 'crew', 'story', 'plot', 'script', 'screenplay'
        ])

        # Quality terms
        self.quality_terms.update([
            'hd', 'fhd', 'uhd', '4k', 'sd', 'hdr', 'high', 'definition', 'full',
            'standard', 'ultra', 'premium', 'blue', 'ray', 'bluray', 'dvd', 'cam',
            'ts', 'tc', 'web', 'dl', 'webdl', 'webrip', 'hdrip', 'brrip', 'dvdrip'
        ])

        # Language terms
        self.language_terms.update([
            'english', 'hindi', 'tamil', 'telugu', 'malayalam', 'kannada', 'bengali',
            'marathi', 'gujarati', 'punjabi', 'urdu', 'chinese', 'japanese', 'korean',
            'french', 'german', 'spanish', 'italian', 'russian', 'arabic', 'portuguese',
            'dubbed', 'subtitled', 'subs', 'subtitles', 'multi', 'audio'
        ])

    async def load_movie_titles(self, titles: List[str]):
        """Load movie titles for better spell checking"""
        self.movie_titles.update([title.lower() for title in titles])
        logger.info(f"Loaded {len(titles)} movie titles for spell checking")

    async def correct_query(self, query: str) -> str:
        """Correct spelling in search query"""
        if not query or not FUZZYWUZZY_AVAILABLE:
            return query

        try:
            # Split query into words
            words = query.split()
            corrected_words = []

            for word in words:
                corrected_word = await self.correct_word(word)
                corrected_words.append(corrected_word)

            corrected_query = " ".join(corrected_words)

            # Return corrected query if it's different
            if corrected_query.lower() != query.lower():
                logger.info(f"Spell correction: '{query}' -> '{corrected_query}'")
                return corrected_query

            return query

        except Exception as e:
            logger.error(f"Error in spell correction for '{query}': {e}")
            return query

    async def correct_word(self, word: str) -> str:
        """Correct a single word"""
        if not word or len(word) < 2:
            return word

        word_lower = word.lower()

        # Remove special characters for matching
        clean_word = re.sub(r'[^\w]', '', word_lower)

        # Check if word is already correct
        if (clean_word in self.common_words or
            clean_word in self.quality_terms or
            clean_word in self.language_terms or
            any(clean_word in title.split() for title in self.movie_titles)):
            return word

        # Try to find best match
        best_match = await self.find_best_match(clean_word)
        if best_match and best_match[1] >= 80:  # 80% similarity threshold
            # Preserve original case if possible
            if word.isupper():
                return best_match[0].upper()
            elif word[0].isupper():
                return best_match[0].capitalize()
            else:
                return best_match[0]

        return word

    async def find_best_match(self, word: str) -> Optional[Tuple[str, int]]:
        """Find best matching word using fuzzy matching"""
        candidates = []

        # Add common words
        candidates.extend(self.common_words)

        # Add quality terms
        candidates.extend(self.quality_terms)

        # Add language terms
        candidates.extend(self.language_terms)

        # Add movie title words
        for title in self.movie_titles:
            candidates.extend(title.split())

        # Remove duplicates
        candidates = list(set(candidates))

        # Find best match
        if FUZZYWUZZY_AVAILABLE:
            result = process.extractOne(word, candidates, scorer=fuzz.ratio)
            return result if result and result[1] >= 80 else None

        return None

    async def suggest_alternatives(self, query: str, max_suggestions: int = 5) -> List[str]:
        """Suggest alternative queries"""
        if not query or not FUZZYWUZZY_AVAILABLE:
            return []

        try:
            suggestions = []

            # Try with different combinations
            words = query.split()

            # Suggest corrections for individual words
            for i, word in enumerate(words):
                corrected_word = await self.correct_word(word)
                if corrected_word.lower() != word.lower():
                    # Create suggestion with this word corrected
                    suggestion_words = words.copy()
                    suggestion_words[i] = corrected_word
                    suggestion = " ".join(suggestion_words)
                    if suggestion not in suggestions:
                        suggestions.append(suggestion)

            # Try fuzzy matching against movie titles
            if self.movie_titles:
                title_matches = process.extract(
                    query.lower(),
                    list(self.movie_titles),
                    limit=max_suggestions,
                    scorer=fuzz.ratio
                )

                for match, score in title_matches:
                    if score >= 70 and match not in suggestions:
                        suggestions.append(match)

            return suggestions[:max_suggestions]

        except Exception as e:
            logger.error(f"Error generating suggestions for '{query}': {e}")
            return []

    async def is_common_typo(self, word: str) -> bool:
        """Check if word is a common typo"""
        common_typos = {
            'avenger': 'avengers',
            'spiderman': 'spider-man',
            'superman': 'super-man',
            'batman': 'bat-man',
            'ironman': 'iron-man',
            'hulk': 'hulk',
            'thor': 'thor',
            'captian': 'captain',
            'america': 'america',
            'marval': 'marvel',
            'dceu': 'dc',
            'mcu': 'marvel',
            'cinima': 'cinema',
            'movei': 'movie',
            'flim': 'film',
            'acton': 'action',
            'advanture': 'adventure',
            'darama': 'drama',
            'comdy': 'comedy',
            'thriler': 'thriller',
            'horor': 'horror',
            'romance': 'romance',
            'scifi': 'sci-fi',
            'animtion': 'animation',
            'cartoon': 'cartoon',
            'anmie': 'anime',
            'seris': 'series',
            'seas': 'season',
            'episod': 'episode',
            'part': 'part',
            'chaptr': 'chapter',
            'volum': 'volume',
            'editon': 'edition',
            'versin': 'version',
            'directr': 'director',
            'actr': 'actor',
            'actrss': 'actress',
            'cast': 'cast',
            'crew': 'crew',
            'story': 'story',
            'plot': 'plot',
            'scrit': 'script',
            'screenply': 'screenplay'
        }

        return word.lower() in common_typos

    async def get_quality_variations(self, quality: str) -> List[str]:
        """Get variations of quality terms"""
        quality_variations = {
            'hd': ['hd', 'high definition', 'high def', '720p'],
            'fhd': ['fhd', 'full hd', 'full definition', '1080p'],
            'uhd': ['uhd', 'ultra hd', 'ultra definition', '4k', '2160p'],
            '4k': ['4k', 'uhd', 'ultra hd', 'ultra definition', '2160p'],
            'sd': ['sd', 'standard definition', 'standard def', '480p', '360p'],
            'hdr': ['hdr', 'high dynamic range', 'hd high dynamic range']
        }

        variations = quality_variations.get(quality.lower(), [])
        return variations

    async def get_language_variations(self, language: str) -> List[str]:
        """Get variations of language terms"""
        language_variations = {
            'english': ['english', 'eng', 'en'],
            'hindi': ['hindi', 'hin', 'hi'],
            'tamil': ['tamil', 'tam', 'ta'],
            'telugu': ['telugu', 'tel', 'te'],
            'malayalam': ['malayalam', 'mal', 'ml'],
            'kannada': ['kannada', 'kan', 'kn'],
            'bengali': ['bengali', 'ben', 'bn'],
            'marathi': ['marathi', 'mar', 'mr'],
            'gujarati': ['gujarati', 'guj', 'gj'],
            'punjabi': ['punjabi', 'pun', 'pb'],
            'urdu': ['urdu', 'urd'],
            'chinese': ['chinese', 'chi', 'zh'],
            'japanese': ['japanese', 'jap', 'ja'],
            'korean': ['korean', 'kor', 'ko'],
            'french': ['french', 'fre', 'fr'],
            'german': ['german', 'ger', 'de'],
            'spanish': ['spanish', 'spa', 'es'],
            'italian': ['italian', 'ita', 'it'],
            'russian': ['russian', 'rus', 'ru'],
            'arabic': ['arabic', 'ara', 'ar'],
            'portuguese': ['portuguese', 'por', 'pt']
        }

        variations = language_variations.get(language.lower(), [])
        return variations

    async def normalize_query(self, query: str) -> str:
        """Normalize query by removing special characters and standardizing format"""
        if not query:
            return query

        # Convert to lowercase
        normalized = query.lower()

        # Remove special characters except spaces and hyphens
        normalized = re.sub(r'[^\w\s\-]', ' ', normalized)

        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized)

        # Remove leading/trailing spaces
        normalized = normalized.strip()

        return normalized

    async def extract_search_terms(self, query: str) -> Dict[str, List[str]]:
        """Extract different types of search terms from query"""
        if not query:
            return {
                'title': [],
                'quality': [],
                'language': [],
                'year': [],
                'series': []
            }

        normalized = await self.normalize_query(query)
        words = normalized.split()

        terms = {
            'title': [],
            'quality': [],
            'language': [],
            'year': [],
            'series': []
        }

        for word in words:
            # Check for year
            if re.match(r'^\d{4}$', word):
                terms['year'].append(word)
                continue

            # Check for quality
            if word in self.quality_terms:
                terms['quality'].append(word)
                continue

            # Check for language
            if word in self.language_terms:
                terms['language'].append(word)
                continue

            # Check for series indicators
            if word in ['season', 'episode', 'ep', 's', 'e']:
                terms['series'].append(word)
                continue

            # Otherwise, treat as title term
            terms['title'].append(word)

        return terms

    async def get_spell_correction_stats(self) -> Dict[str, int]:
        """Get spell correction statistics"""
        # This would track correction statistics over time
        # For now, return placeholder stats
        return {
            'total_corrections': 0,
            'accuracy_improvements': 0,
            'common_typos_fixed': 0,
            'user_satisfaction': 0
        }


# Global spell check service instance
spell_check_service = None


async def get_spell_check_service() -> SpellCheckService:
    """Get or create spell check service instance"""
    global spell_check_service
    if spell_check_service is None:
        spell_check_service = SpellCheckService()
    return spell_check_service


async def correct_query(query: str) -> str:
    """Convenience function to correct a query"""
    service = await get_spell_check_service()
    return await service.correct_query(query)


async def suggest_alternatives(query: str, max_suggestions: int = 5) -> List[str]:
    """Convenience function to get suggestions"""
    service = await get_spell_check_service()
    return await service.suggest_alternatives(query, max_suggestions)