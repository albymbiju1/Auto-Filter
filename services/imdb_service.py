"""
IMDB service for CineAI Bot
Fetches movie information and metadata from IMDB
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx
from pydantic import BaseModel

from app.config import config

logger = logging.getLogger(__name__)


class IMDBMovie(BaseModel):
    """IMDB movie data model"""
    imdb_id: str
    title: str
    year: Optional[int] = None
    rating: Optional[float] = None
    genre: List[str] = []
    director: Optional[str] = None
    cast: List[str] = []
    plot: Optional[str] = None
    poster_url: Optional[str] = None
    runtime: Optional[int] = None  # in minutes
    language: List[str] = []
    country: List[str] = []
    awards: Optional[str] = None
    box_office: Optional[str] = None
    metascore: Optional[int] = None


class IMDBService:
    """IMDB API service for fetching movie information"""

    def __init__(self):
        self.api_key = config.external_apis.IMDB_API_KEY
        self.base_url = "https://imdb-api.com/en/API"
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 3600  # 1 hour cache

    async def search_movie(
        self,
        title: str,
        year: Optional[int] = None,
        max_results: int = 5
    ) -> Optional[IMDBMovie]:
        """Search for a movie and return the best match"""
        if not self.api_key:
            logger.warning("IMDB API key not configured")
            return None

        try:
            # Check cache first
            cache_key = f"{title.lower()}_{year or ''}"
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result

            # Search for movie
            search_results = await self._search_imdb(title, max_results)
            if not search_results:
                return None

            # Find best match
            best_match = self._find_best_match(search_results, title, year)
            if not best_match:
                return None

            # Get detailed movie information
            movie_data = await self._get_movie_details(best_match['id'])
            if not movie_data:
                return None

            # Cache the result
            self._cache_result(cache_key, movie_data)

            return movie_data

        except Exception as e:
            logger.error(f"Error searching IMDB for '{title}': {e}")
            return None

    async def get_movie_by_id(self, imdb_id: str) -> Optional[IMDBMovie]:
        """Get movie information by IMDB ID"""
        if not self.api_key:
            return None

        try:
            # Check cache first
            cached_result = self._get_from_cache(f"id_{imdb_id}")
            if cached_result:
                return cached_result

            movie_data = await self._get_movie_details(imdb_id)
            if movie_data:
                self._cache_result(f"id_{imdb_id}", movie_data)

            return movie_data

        except Exception as e:
            logger.error(f"Error getting IMDB movie {imdb_id}: {e}")
            return None

    async def get_movie_poster(self, imdb_id: str, size: str = "original") -> Optional[str]:
        """Get movie poster URL"""
        try:
            movie_data = await self.get_movie_by_id(imdb_id)
            if movie_data and movie_data.poster_url:
                return movie_data.poster_url
            return None

        except Exception as e:
            logger.error(f"Error getting poster for {imdb_id}: {e}")
            return None

    async def get_top_rated_movies(self, limit: int = 10) -> List[IMDBMovie]:
        """Get top rated movies"""
        if not self.api_key:
            return []

        try:
            url = f"{self.base_url}/Top250Movies/{self.api_key}"
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()
                if data.get('errorMessage'):
                    logger.error(f"IMDB API error: {data['errorMessage']}")
                    return []

                movies = []
                for item in data.get('items', [])[:limit]:
                    movie_data = await self._parse_movie_data(item)
                    if movie_data:
                        movies.append(movie_data)

                return movies

        except Exception as e:
            logger.error(f"Error getting top rated movies: {e}")
            return []

    async def get_popular_movies(self, limit: int = 10) -> List[IMDBMovie]:
        """Get popular movies"""
        if not self.api_key:
            return []

        try:
            url = f"{self.base_url}/MostPopularMovies/{self.api_key}"
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()
                if data.get('errorMessage'):
                    logger.error(f"IMDB API error: {data['errorMessage']}")
                    return []

                movies = []
                for item in data.get('items', [])[:limit]:
                    movie_data = await self._parse_movie_data(item)
                    if movie_data:
                        movies.append(movie_data)

                return movies

        except Exception as e:
            logger.error(f"Error getting popular movies: {e}")
            return []

    async def _search_imdb(self, title: str, max_results: int) -> List[Dict[str, Any]]:
        """Search IMDB API"""
        try:
            url = f"{self.base_url}/SearchMovie/{self.api_key}/{title}"
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()
                if data.get('errorMessage'):
                    logger.error(f"IMDB API error: {data['errorMessage']}")
                    return []

                return data.get('results', [])[:max_results]

        except Exception as e:
            logger.error(f"Error searching IMDB API: {e}")
            return []

    async def _get_movie_details(self, imdb_id: str) -> Optional[IMDBMovie]:
        """Get detailed movie information"""
        try:
            url = f"{self.base_url}/Title/{self.api_key}/{imdb_id}"
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()
                if data.get('errorMessage'):
                    logger.error(f"IMDB API error: {data['errorMessage']}")
                    return None

                return await self._parse_movie_data(data)

        except Exception as e:
            logger.error(f"Error getting movie details: {e}")
            return None

    async def _parse_movie_data(self, data: Dict[str, Any]) -> Optional[IMDBMovie]:
        """Parse IMDB API response into IMDBMovie model"""
        try:
            return IMDBMovie(
                imdb_id=data.get('id', ''),
                title=data.get('title', ''),
                year=data.get('year'),
                rating=data.get('imDbRating'),
                genre=data.get('genreList', []),
                director=data.get('directors'),
                cast=data.get('stars', []),
                plot=data.get('plot'),
                poster_url=data.get('image'),
                runtime=self._parse_runtime(data.get('runtimeStr')),
                language=data.get('languageList', []),
                country=data.get('countries'),
                awards=data.get('awards'),
                box_office=data.get('boxOffice'),
                metascore=data.get('metacriticRating')
            )

        except Exception as e:
            logger.error(f"Error parsing movie data: {e}")
            return None

    def _parse_runtime(self, runtime_str: Optional[str]) -> Optional[int]:
        """Parse runtime string to minutes"""
        if not runtime_str:
            return None

        try:
            # Handle formats like "2h 30m" or "150 min"
            if 'h' in runtime_str:
                hours = int(runtime_str.split('h')[0].strip())
                minutes = 0
                if 'm' in runtime_str:
                    minutes_part = runtime_str.split('h')[1].strip()
                    minutes = int(minutes_part.split('m')[0].strip())
                return hours * 60 + minutes
            elif 'min' in runtime_str:
                return int(runtime_str.split('min')[0].strip())
            elif runtime_str.isdigit():
                return int(runtime_str)

        except (ValueError, AttributeError):
            pass

        return None

    def _find_best_match(
        self,
        results: List[Dict[str, Any]],
        title: str,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Find the best matching result from search results"""
        if not results:
            return None

        # Filter by year if provided
        if year:
            year_filtered = [
                result for result in results
                if result.get('year') == year
            ]
            if year_filtered:
                results = year_filtered

        # Simple matching - in a real implementation, you'd use fuzzy matching
        title_lower = title.lower()
        best_match = None
        best_score = 0

        for result in results:
            result_title = result.get('title', '').lower()

            # Exact match gets highest score
            if result_title == title_lower:
                return result

            # Calculate simple similarity score
            score = self._calculate_similarity(title_lower, result_title)
            if score > best_score:
                best_score = score
                best_match = result

        # Return best match if score is reasonable
        if best_score > 0.6:  # 60% similarity threshold
            return best_match

        return results[0] if results else None

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate simple similarity between two strings"""
        # This is a very basic similarity calculation
        # In production, you'd use more sophisticated algorithms
        str1_words = set(str1.split())
        str2_words = set(str2.split())

        intersection = str1_words.intersection(str2_words)
        union = str1_words.union(str2_words)

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _get_from_cache(self, key: str) -> Optional[IMDBMovie]:
        """Get result from cache"""
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            if datetime.utcnow().timestamp() - timestamp < self.cache_ttl:
                return cached_data
            else:
                # Remove expired cache entry
                del self.cache[key]
        return None

    def _cache_result(self, key: str, result: IMDBMovie):
        """Cache a result"""
        self.cache[key] = (result, datetime.utcnow().timestamp())

        # Limit cache size
        if len(self.cache) > 1000:
            # Remove oldest entries
            oldest_keys = sorted(
                self.cache.keys(),
                key=lambda k: self.cache[k][1]
            )[:100]
            for old_key in oldest_keys:
                del self.cache[old_key]

    async def get_movie_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """Get movie suggestions based on query"""
        try:
            search_results = await self._search_imdb(query, limit)
            return [
                result.get('title', '')
                for result in search_results
                if result.get('title')
            ]

        except Exception as e:
            logger.error(f"Error getting movie suggestions: {e}")
            return []

    async def get_movie_trailer_url(self, imdb_id: str) -> Optional[str]:
        """Get movie trailer URL"""
        try:
            url = f"{self.base_url}/Trailer/{self.api_key}/{imdb_id}"
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()
                if data.get('errorMessage'):
                    logger.error(f"IMDB API error: {data['errorMessage']}")
                    return None

                # Return the first available trailer
                trailers = data.get('trailers', [])
                if trailers:
                    return trailers[0].get('videoUrl')

                return None

        except Exception as e:
            logger.error(f"Error getting movie trailer: {e}")
            return None

    async def get_similar_movies(self, imdb_id: str, limit: int = 5) -> List[IMDBMovie]:
        """Get similar movies"""
        try:
            url = f"{self.base_url}/Title/{self.api_key}/{imdb_id},Similar"
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()
                if data.get('errorMessage'):
                    logger.error(f"IMDB API error: {data['errorMessage']}")
                    return []

                movies = []
                for item in data.get('similar', [])[:limit]:
                    movie_data = await self._parse_movie_data(item)
                    if movie_data:
                        movies.append(movie_data)

                return movies

        except Exception as e:
            logger.error(f"Error getting similar movies: {e}")
            return []

    def clear_cache(self):
        """Clear the cache"""
        self.cache.clear()
        logger.info("IMDB service cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cache_size': len(self.cache),
            'cache_ttl': self.cache_ttl,
            'oldest_entry': min((ts for _, ts in self.cache.values()), default=0),
            'newest_entry': max((ts for _, ts in self.cache.values()), default=0)
        }


# Global IMDB service instance
imdb_service = None


async def get_imdb_service() -> IMDBService:
    """Get or create IMDB service instance"""
    global imdb_service
    if imdb_service is None:
        imdb_service = IMDBService()
    return imdb_service


async def search_movie(title: str, year: Optional[int] = None) -> Optional[IMDBMovie]:
    """Convenience function to search for a movie"""
    service = await get_imdb_service()
    return await service.search_movie(title, year)


async def get_movie_by_id(imdb_id: str) -> Optional[IMDBMovie]:
    """Convenience function to get movie by ID"""
    service = await get_imdb_service()
    return await service.get_movie_by_id(imdb_id)