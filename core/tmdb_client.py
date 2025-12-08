"""
TMDB API integration client
"""

import aiohttp
import asyncio
from typing import Optional, List, Dict, Any
from core.config import get_config
from core.constants import (
    TMDB_RATE_LIMIT_CALLS,
    TMDB_RATE_LIMIT_PERIOD,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_DELAY,
    API_REQUEST_TIMEOUT,
)
from models.download import TMDBResult, SeriesInfo
from utils.helpers import RetryHelpers, AsyncHelpers, RateLimiter


class TMDBClient:
    """Client for The Movie Database API"""

    def __init__(self):
        self.config = get_config()
        self.api_key = self.config.tmdb.api_key
        self.base_url = self.config.tmdb.base_url
        self.language = self.config.tmdb.language
        self.logger = self.config.logger

        # Rate limiter: TMDB allows 40 requests every 10 seconds
        self.rate_limiter = RateLimiter(
            max_calls=TMDB_RATE_LIMIT_CALLS, period=TMDB_RATE_LIMIT_PERIOD
        )

        if not self.api_key:
            self.logger.warning("TMDB API key not configured")

    @RetryHelpers.async_retry(
        max_attempts=DEFAULT_RETRY_ATTEMPTS,
        delay=DEFAULT_RETRY_DELAY,
        exceptions=(aiohttp.ClientError, asyncio.TimeoutError),
    )
    async def search(
        self, query: str, media_type: Optional[str] = None, year: Optional[str] = None
    ) -> Optional[List[TMDBResult]]:
        """
        Search for movies and TV series with automatic retry

        Args:
            query: Search query
            media_type: Media type ('movie', 'tv', None for multi)
            year: Year to filter results (uses 'y:YYYY' filter)

        Returns:
            List of results or None
        """
        if not self.api_key:
            return None

        # Apply rate limiting
        await self.rate_limiter.acquire()

        try:
            # Clean query and extract year if not provided
            cleaned_query, extracted_year = self._clean_query(query)

            # Use extracted year if not explicitly provided
            if not year:
                year = extracted_year

            # Endpoint
            if media_type:
                endpoint = f"/search/{media_type}"
            else:
                endpoint = "/search/multi"

            # Base parameters
            params = {
                "api_key": self.api_key,
                "query": cleaned_query,
                "language": self.language,
                "include_adult": "false",
            }

            # Add year filter if available
            # Note: year filter works differently for movies vs TV
            if year:
                if media_type == "movie":
                    params["primary_release_year"] = year
                elif media_type == "tv":
                    params["first_air_date_year"] = year
                # For 'multi' search, year filter is not directly supported

            # Request with timeout
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}{endpoint}"

                # Use helper for timeout
                response = await AsyncHelpers.run_with_timeout(
                    session.get(url, params=params),
                    timeout=API_REQUEST_TIMEOUT,
                    default=None,
                )

                if response and response.status == 200:
                    data = await response.json()
                    return self._parse_results(data.get("results", []))
                else:
                    self.logger.warning(
                        f"TMDB API error: {response.status if response else 'timeout'}"
                    )
                    return None

        except Exception as e:
            self.logger.error(f"TMDB search error: {e}")
            return None

    @RetryHelpers.async_retry(max_attempts=2, delay=DEFAULT_RETRY_DELAY)
    async def get_episode_details(
        self, tv_id: int, season: int, episode: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get episode details with retry

        Args:
            tv_id: TMDB series ID
            season: Season number
            episode: Episode number

        Returns:
            Episode details or None
        """
        if not self.api_key:
            return None

        # Rate limiting
        await self.rate_limiter.acquire()

        try:
            params = {"api_key": self.api_key, "language": self.language}

            url = f"{self.base_url}/tv/{tv_id}/season/{season}/episode/{episode}"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params, timeout=API_REQUEST_TIMEOUT
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.warning(
                            f"TMDB episode API error: {response.status}"
                        )
                        return None

        except Exception as e:
            self.logger.error(f"TMDB episode details error: {e}")
            return None

    def _clean_query(self, query: str) -> tuple[str, Optional[str]]:
        """
        Clean search query and extract year

        Args:
            query: Raw query

        Returns:
            (cleaned_query, extracted_year)
        """
        import re

        # Extract year before removing it (search in parentheses or brackets)
        year = None
        year_match = re.search(r"[\(\[](\d{4})[\)\]]", query)
        if year_match:
            year_value = int(year_match.group(1))
            # Validate it's a reasonable year (1900-2099)
            if 1900 <= year_value <= 2099:
                year = year_match.group(1)

        # If not found in parentheses, search for year at the end
        if not year:
            year_match = re.search(r"\b(\d{4})$", query)
            if year_match:
                year_value = int(year_match.group(1))
                if 1900 <= year_value <= 2099:
                    year = year_match.group(1)

        # Remove episode info
        query = re.sub(r"[Ss]\d+[Ee]\d+.*", "", query).strip()

        # Remove quality tags in square/round brackets: [HD], [4K], etc.
        query = re.sub(r"\[.*?\]", "", query).strip()
        query = re.sub(r"\(.*?p\)", "", query).strip()

        # Remove year in parentheses
        query = re.sub(r"\(\d{4}\)", "", query).strip()

        # Remove year at the end
        query = re.sub(r"\d{4}$", "", query).strip()

        # Remove common video quality information
        quality_patterns = [
            r"WEBDL",
            r"WEB-DL",
            r"WEBRip",
            r"WEB-Rip",
            r"BluRay",
            r"BRRip",
            r"BDRip",
            r"DVDRip",
            r"HDTV",
            r"HDRip",
            r"CAM",
            r"TS",
            r"TC",
            r"\d{3,4}p",
            r"1080p",
            r"720p",
            r"2160p",
            r"4K",
            r"x264",
            r"x265",
            r"h264",
            r"h265",
            r"HEVC",
            r"AAC",
            r"AC3",
            r"DTS",
            r"DD5\.1",
            r"ITA",
            r"ENG",
            r"SUB",
            r"Multi",
        ]
        for pattern in quality_patterns:
            query = re.sub(pattern, "", query, flags=re.IGNORECASE).strip()

        # Replace separators
        query = re.sub(r"[\._]", " ", query)

        # Remove multiple spaces
        query = re.sub(r"\s+", " ", query).strip()

        return query, year

    def _parse_results(self, results: List[Dict]) -> List[TMDBResult]:
        """
        Convert API results to TMDBResult

        Args:
            results: Raw results from API

        Returns:
            List of TMDBResult
        """
        parsed = []

        for result in results:
            # Determine media type
            media_type = result.get("media_type", "movie")

            # Extract base data
            if media_type == "tv" or "first_air_date" in result:
                title = result.get("name", "Unknown")
                original_title = result.get("original_name", title)
                year = result.get("first_air_date", "")[:4]
                media_type = "tv"
            else:
                title = result.get("title", "Unknown")
                original_title = result.get("original_title", title)
                year = result.get("release_date", "")[:4]
                media_type = "movie"

            tmdb_result = TMDBResult(
                id=result.get("id", 0),
                title=title,
                original_title=original_title,
                media_type=media_type,
                year=year,
                poster_path=result.get("poster_path"),
                backdrop_path=result.get("backdrop_path"),
                overview=result.get("overview", ""),
                vote_average=result.get("vote_average", 0.0),
            )

            parsed.append(tmdb_result)

        return parsed

    def calculate_confidence(
        self, result: TMDBResult, search_query: str, original_filename: str = ""
    ) -> int:
        """
        Calculate match confidence

        Args:
            result: TMDB result
            search_query: Search query
            original_filename: Original filename

        Returns:
            Confidence percentage (0-100)
        """
        confidence = 0

        # Compare titles
        result_title = result.title.lower()
        search_title = search_query.lower()

        if result_title == search_title:
            confidence = 95
        elif search_title in result_title or result_title in search_title:
            confidence = 80
        else:
            # Calculate base similarity
            confidence = 60

        # Boost for year if present
        if original_filename and result.year:
            import re

            year_match = re.search(r"(\d{4})", original_filename)
            if year_match and year_match.group(1) == result.year:
                confidence = min(100, confidence + 15)

        return confidence

    def format_result(
        self, result: TMDBResult, series_info: Optional[SeriesInfo] = None
    ) -> tuple[str, Optional[str]]:
        """
        Format result for display

        Args:
            result: TMDB result
            series_info: Series info if TV show

        Returns:
            (formatted_text, poster_url)
        """
        # Emoji and type
        if result.is_tv_show:
            emoji = "📺"
            media_type_str = "TV Series"
        else:
            emoji = "🎬"
            media_type_str = "Movie"

        # Rating
        rating_str = (
            f"⭐ {result.vote_average:.1f}/10" if result.vote_average > 0 else ""
        )

        # Overview (truncate if too long)
        overview = result.overview
        if len(overview) > 300:
            overview = overview[:297] + "..."

        # Build text
        text = f"{emoji} **{media_type_str}**\n\n"
        text += f"**{result.title}**"
        if result.year:
            text += f" ({result.year})"
        text += "\n"

        # Episode info if present
        if series_info and series_info.season and series_info.episode:
            text += f"📅 Season {series_info.season}, Episode {series_info.episode}\n"

        if rating_str:
            text += f"{rating_str}\n"

        if overview:
            text += f"\n📝 {overview}\n"

        return text, result.poster_url

    async def search_with_confidence(
        self, filename: str, media_hint: Optional[str] = None
    ) -> tuple[Optional[TMDBResult], int]:
        """
        Search and calculate confidence automatically

        Args:
            filename: Filename
            media_hint: Media type hint

        Returns:
            (best_result, confidence)
        """
        # Import parser
        from utils.naming import FileNameParser

        # Extract info from filename
        year = None
        if media_hint == "tv":
            series_info = FileNameParser.extract_series_info(filename)
            search_query = series_info.series_name
        else:
            movie_name, year = FileNameParser.extract_movie_info(filename)
            search_query = movie_name

        # Search with year if available
        results = await self.search(search_query, media_hint, year)

        if not results:
            return None, 0

        # Get first result and calculate confidence
        first_result = results[0]
        confidence = self.calculate_confidence(first_result, search_query, filename)

        first_result.confidence = confidence

        return first_result, confidence
