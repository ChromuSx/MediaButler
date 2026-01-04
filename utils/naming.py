"""
Naming and file name parsing utilities
"""

import re
import os
from pathlib import Path
from typing import Optional, Tuple
from models.download import SeriesInfo, TMDBResult


class FileNameParser:
    """Media filename parser"""

    # Patterns to identify TV series with confidence scoring
    TV_PATTERNS = [
        # High confidence patterns (90-100)
        (r"[Ss](\d{1,2})[Ee](\d{1,3})", "standard", 100),  # S01E01
        (r"[Ss](\d{1,2})\s*[Ee](\d{1,3})", "spaced", 95),  # S01 E01
        (
            r"Season[\s\.](\d{1,2})[\s\.]Episode[\s\.](\d{1,3})",
            "verbose_sep",
            92,
        ),  # Season.2.Episode.5
        (
            r"Season\s*(\d{1,2})\s*Episode\s*(\d{1,3})",
            "verbose",
            90,
        ),  # Season 1 Episode 1
        # Medium confidence patterns (70-89)
        (r"^(\d{1,2})x(\d{1,3})", "x_format_leading", 92),  # 12x06 at start of filename
        (r"(\d{1,2})\s+x\s+(\d{1,3})", "x_format_spaced", 88),  # 12 x 5
        (r"(\d{1,2})x(\d{1,3})", "x_format", 85),  # 1x01
        (r"[\.\s\-_](\d{1,2})x(\d{1,3})", "x_format_sep", 80),  # .1x01
        (
            r"[Ss](\d{1,2})[Ee](\d{1,3})-[Ee](\d{1,3})",
            "multi_episode",
            75,
        ),  # S01E01-E03
        # New patterns
        (r"(\d{1,2})\.(\d{1,3})", "dot_format", 70),  # 1.01
        (r"[\[\(](\d{1,3})[\]\)]", "anime_bracket", 75),  # [01] per anime
        (r"(?:Episode|Ep)[\s\.]?(\d{1,3})", "episode_word", 65),  # Episode 1
        (r"[Pp]art[\s\.]?(\d{1,3})", "part_format", 60),  # Part 1
        # Low confidence patterns (50-69)
        (
            r"(?<![0-9xX])(\d)(\d{2})(?![0-9])",
            "concatenated",
            55,
        ),  # 101 (1x01), but not x265
        (r"[Ee][Pp][\.\s]?(\d{1,3})", "episode_only", 50),  # EP01
    ]

    # Quality tags to remove
    QUALITY_TAGS = [
        "1080p",
        "720p",
        "2160p",
        "4K",
        "BluRay",
        "WEBRip",
        "WEB-DL",
        "HDTV",
        "DVDRip",
        "BRRip",
        "x264",
        "x265",
        "HEVC",
        "HDR",
        "ITA",
        "ENG",
        "SUBITA",
        "DDP5.1",
        "AC3",
        "AAC",
        "AMZN",
        "NF",
        "DSNP",
        "DLMux",
        "BDMux",
        "HDR10",
        "DV",
        "Atmos",
        "MULTI",
        "DUAL",
        "SUB",
        "EXTENDED",
        "REMASTERED",
        "DIRECTORS.CUT",
    ]

    # Invalid characters for filenames
    INVALID_CHARS = '<>:"|?*'

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Clean filename from problematic characters

        Args:
            filename: Filename to clean

        Returns:
            Cleaned filename
        """
        # Remove null bytes
        filename = filename.replace("\x00", "")

        # Remove invalid characters
        for char in cls.INVALID_CHARS:
            filename = filename.replace(char, "")

        # Clean multiple dots
        filename = re.sub(r"\.+", ".", filename)

        # Clean multiple spaces
        filename = re.sub(r"\s+", " ", filename).strip()

        # Limit length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[: 200 - len(ext)] + ext

        return filename

    @classmethod
    def find_similar_folder(cls, target_name: str, search_path: Path, threshold: float = 0.7) -> Optional[str]:
        """
        Find existing folder with similar name using fuzzy matching

        Args:
            target_name: Name to search for
            search_path: Directory to search in
            threshold: Similarity threshold (0.0-1.0)

        Returns:
            Name of similar folder if found, None otherwise
        """
        if not search_path.exists():
            return None

        target_clean = cls._normalize_for_comparison(target_name)
        best_match = None
        best_score = 0.0

        try:
            for folder in search_path.iterdir():
                if not folder.is_dir():
                    continue

                folder_clean = cls._normalize_for_comparison(folder.name)
                score = cls._calculate_similarity(target_clean, folder_clean)

                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = folder.name
        except Exception:
            pass

        return best_match

    @classmethod
    def _normalize_for_comparison(cls, text: str) -> str:
        """
        Normalize text for comparison (lowercase, remove special chars, etc.)

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Convert to lowercase
        text = text.lower()

        # Remove year and brackets
        text = re.sub(r"\s*[\(\[]?\d{4}[\)\]]?", "", text)

        # Remove language tags
        text = re.sub(r"\s*\[(?:ita|eng|multi)\]", "", text, flags=re.IGNORECASE)

        # Remove special characters and separators
        text = re.sub(r"[._\-@]", " ", text)

        # Remove extra spaces
        text = re.sub(r"\s+", " ", text).strip()

        return text

    @classmethod
    def _calculate_similarity(cls, str1: str, str2: str) -> float:
        """
        Calculate similarity score between two strings
        Uses simple token-based matching

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score (0.0-1.0)
        """
        # Split into tokens
        tokens1 = set(str1.split())
        tokens2 = set(str2.split())

        if not tokens1 or not tokens2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        if union == 0:
            return 0.0

        # Also check if one is substring of the other (boost score)
        substring_bonus = 0.0
        if str1 in str2 or str2 in str1:
            substring_bonus = 0.3

        jaccard = intersection / union
        return min(1.0, jaccard + substring_bonus)

    @classmethod
    def extract_series_info(cls, filename: str) -> SeriesInfo:
        """
        Extract TV series information from filename with confidence scoring

        Args:
            filename: Filename

        Returns:
            SeriesInfo with extracted data
        """
        best_match = None
        best_confidence = 0

        # Remove extension first to avoid including it in series name
        filename_no_ext = os.path.splitext(filename)[0]

        # If file is an archive, remove .partX pattern to avoid false detection
        # (e.g., "movie.part2.rar" should not be detected as episode 2)
        import re

        if any(filename.lower().endswith(ext) for ext in [".rar", ".zip", ".7z"]):
            filename_no_ext = re.sub(r"\.part\d+", "", filename_no_ext, flags=re.IGNORECASE)

        # Detect years and dates in filename to avoid false TV series matches
        # Store positions to exclude them from pattern matching
        year_positions = []

        # Pattern 1: Years in brackets/parentheses like (2004) or [2004]
        year_pattern_brackets = r"[\(\[](\d{4})[\)\]]"
        for year_match in re.finditer(year_pattern_brackets, filename_no_ext):
            year_value = int(year_match.group(1))
            if 1900 <= year_value <= 2099:
                year_positions.append((year_match.start(), year_match.end()))

        # Pattern 2: Standalone years (not in brackets) like "2004"
        year_pattern_standalone = r"\b(19\d{2}|20\d{2})\b"
        for year_match in re.finditer(year_pattern_standalone, filename_no_ext):
            year_value = int(year_match.group(1))
            if 1900 <= year_value <= 2099:
                # Avoid overlapping with already detected bracketed years
                overlap = any(year_match.start() >= start and year_match.end() <= end for start, end in year_positions)
                if not overlap:
                    year_positions.append((year_match.start(), year_match.end()))

        # Pattern 3: Dates in DDMMYYYY format like "01112023"
        date_pattern = r"\b\d{8}\b"
        for date_match in re.finditer(date_pattern, filename_no_ext):
            date_str = date_match.group(0)
            # Verify it could be a valid date (basic check)
            # Day: 01-31, Month: 01-12, Year: 19xx or 20xx
            day = int(date_str[0:2])
            month = int(date_str[2:4])
            year = int(date_str[4:8])

            if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2099:
                year_positions.append((date_match.start(), date_match.end()))

        # Pattern 4: Timestamps or random numbers like "191858"
        timestamp_pattern = r"\b\d{6}\b"
        for ts_match in re.finditer(timestamp_pattern, filename_no_ext):
            ts_str = ts_match.group(0)
            # Could be HHMMSS format or similar
            hour = int(ts_str[0:2])
            minute = int(ts_str[2:4])
            second = int(ts_str[4:6])

            if 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59:
                # Avoid overlapping
                overlap = any(ts_match.start() >= start and ts_match.end() <= end for start, end in year_positions)
                if not overlap:
                    year_positions.append((ts_match.start(), ts_match.end()))

        # Try all patterns with scoring
        for pattern, pattern_type, confidence in cls.TV_PATTERNS:
            match = re.search(pattern, filename_no_ext, re.IGNORECASE)

            if match:
                # Skip if match overlaps with a detected year
                match_overlaps_year = False
                for year_start, year_end in year_positions:
                    # Check if match overlaps with year position
                    if not (match.end() <= year_start or match.start() >= year_end):
                        match_overlaps_year = True
                        break

                if match_overlaps_year:
                    continue  # Skip this match, it's part of a year

                season = None
                episode = None
                end_episode = None

                # Handle specific patterns
                if pattern_type == "episode_only" or pattern_type == "episode_word" or pattern_type == "part_format":
                    season = 1
                    episode = int(match.group(1))
                elif pattern_type == "anime_bracket":
                    season = 1
                    episode = int(match.group(1))
                elif pattern_type == "concatenated":
                    # 101 = S1E01
                    season = int(match.group(1))
                    episode = int(match.group(2))
                elif pattern_type == "multi_episode":
                    season = int(match.group(1))
                    episode = int(match.group(2))
                    end_episode = int(match.group(3)) if len(match.groups()) >= 3 else None
                else:
                    season = int(match.group(1))
                    episode = int(match.group(2))

                # Validation
                if not cls._validate_season_episode(season, episode):
                    continue

                # Calculate total confidence
                total_confidence = confidence

                # Bonus for context
                total_confidence += cls._calculate_context_bonus(filename_no_ext, match, pattern_type)

                if total_confidence > best_confidence:
                    best_confidence = total_confidence

                    # Special handling for pattern at start of filename
                    # (e.g., 12x06 American Horror Story)
                    if pattern_type == "x_format_leading" and match.start() == 0:
                        # Pattern is at start, series name comes AFTER the pattern
                        series_name_raw = filename_no_ext[match.end() :].strip()
                        # Remove common separators at the start
                        series_name_raw = re.sub(r"^[\.\-_\s@]+", "", series_name_raw)
                    else:
                        # Extract only the series name part (before SE pattern)
                        series_name_raw = filename_no_ext[: match.start()].strip()

                    # Remove common trailing separators (./-/_)
                    series_name_raw = re.sub(r"[\.\-_\s]+$", "", series_name_raw)

                    # If the name still seems to contain extra info (years, quality, etc),
                    # try to clean it further
                    series_name = cls._extract_clean_series_name(series_name_raw)

                    # Extract episode title if possible
                    episode_title = cls._extract_episode_title(filename_no_ext, match)

                    best_match = {
                        "series_name": series_name,
                        "season": season,
                        "episode": episode,
                        "end_episode": end_episode,
                        "episode_title": episode_title,
                        "confidence": total_confidence,
                    }

        # If nothing found, use filename without extension
        if not best_match:
            series_name = os.path.splitext(filename)[0]
            best_match = {
                "series_name": series_name,
                "season": None,
                "episode": None,
                "end_episode": None,
                "episode_title": None,
                "confidence": 0,
            }

        # Clean series name
        clean_name = cls.clean_media_name(best_match["series_name"])

        return SeriesInfo(
            series_name=cls.sanitize_filename(clean_name),
            season=best_match["season"],
            episode=best_match["episode"],
            episode_title=best_match["episode_title"],
            end_episode=best_match["end_episode"],
            confidence=best_match["confidence"],
        )

    @classmethod
    def extract_movie_info(cls, filename: str) -> Tuple[str, Optional[str]]:
        """
        Extract movie information from filename

        Args:
            filename: Filename

        Returns:
            (movie_name, year)
        """
        name = os.path.splitext(filename)[0]

        # Search for year
        year_match = re.search(r"[\(\[]?(\d{4})[\)\]]?", name)
        year = year_match.group(1) if year_match else None

        # Remove year and everything after
        if year:
            name = re.sub(r"[\(\[]?\d{4}[\)\]]?.*", "", name).strip()

        # Clean name
        name = cls.clean_media_name(name)

        return cls.sanitize_filename(name), year

    @classmethod
    def clean_media_name(cls, name: str) -> str:
        """
        Clean media name from technical tags

        Args:
            name: Name to clean

        Returns:
            Cleaned name
        """
        # Remove quality tags
        for tag in cls.QUALITY_TAGS:
            name = re.sub(rf"\b{tag}\b", "", name, flags=re.IGNORECASE)

        # Replace common separators
        name = re.sub(r"(?<!\s)\.(?!\s)", " ", name)  # Dots not surrounded by spaces
        name = name.replace("_", " ")

        # Remove empty parentheses
        name = re.sub(r"\(\s*\)", "", name)
        name = re.sub(r"\[\s*\]", "", name)

        # Clean trailing characters
        name = re.sub(r"[\-\.\s]+$", "", name).strip()

        # Multiple spaces
        name = re.sub(r"\s+", " ", name).strip()

        return name

    @classmethod
    def detect_italian_content(cls, filename: str) -> bool:
        """
        Detect if content is in Italian

        Args:
            filename: Filename

        Returns:
            True if probably Italian
        """
        italian_tags = ["ITA", "ITALIAN", "SUBITA", "iTALiAN", "DLMux"]
        return any(tag in filename.upper() for tag in italian_tags)

    @classmethod
    def create_folder_name(cls, title: str, year: Optional[str] = None, is_italian: bool = False) -> str:
        """
        Create folder name for media

        Args:
            title: Title
            year: Year (for movies)
            is_italian: If Italian content

        Returns:
            Folder name
        """
        folder_name = title

        if year:
            folder_name = f"{title} ({year})"

        if is_italian:
            folder_name += " [ITA]"

        return cls.sanitize_filename(folder_name)

    @classmethod
    def create_episode_filename(
        cls,
        series_name: str,
        season: int,
        episode: int,
        episode_title: Optional[str] = None,
        extension: str = ".mp4",
    ) -> str:
        """
        Create filename for episode

        Args:
            series_name: Series name
            season: Season number
            episode: Episode number
            episode_title: Episode title (optional)
            extension: File extension

        Returns:
            Episode filename
        """
        filename = f"{series_name} - S{season:02d}E{episode:02d}"

        if episode_title:
            # Clean episode title
            episode_title = cls.sanitize_filename(episode_title)
            filename += f" - {episode_title}"

        return filename + extension

    @classmethod
    def create_tmdb_filename(
        cls,
        tmdb_result: TMDBResult,
        original_filename: str,
        series_info: Optional[SeriesInfo] = None,
    ) -> Tuple[str, str]:
        """
        Create filename and folder based on TMDB data

        Args:
            tmdb_result: TMDB result
            original_filename: Original filename
            series_info: Series info (if TV show)

        Returns:
            (folder_name, filename)
        """
        extension = Path(original_filename).suffix
        is_italian = cls.detect_italian_content(original_filename)

        if tmdb_result.is_movie:
            # Movie
            folder_name = cls.create_folder_name(tmdb_result.title, tmdb_result.year, is_italian)
            filename = folder_name + extension

        else:
            # TV Series
            folder_name = cls.create_folder_name(tmdb_result.title, is_italian=is_italian)

            if series_info and series_info.season and series_info.episode:
                filename = cls.create_episode_filename(
                    tmdb_result.title,
                    series_info.season,
                    series_info.episode,
                    series_info.episode_title,
                    extension,
                )
            else:
                # Fallback to original name
                filename = cls.sanitize_filename(original_filename)

        return folder_name, filename

    @classmethod
    def _validate_season_episode(cls, season: int, episode: int) -> bool:
        """
        Validate season/episode numbers

        Args:
            season: Season number
            episode: Episode number

        Returns:
            True if valid
        """
        if season is None or episode is None:
            return False

        # Reasonableness checks
        if season < 1 or season > 50:  # Max 50 seasons
            return False

        if episode < 1 or episode > 999:  # Max 999 episodes
            return False

        # Check for episodes too high for low seasons (except anime)
        if season <= 5 and episode > 100 and episode < 999:
            return False

        return True

    @classmethod
    def _calculate_context_bonus(cls, filename: str, match, pattern_type: str) -> int:
        """
        Calculate confidence bonus based on context

        Args:
            filename: Full filename
            match: Regex match
            pattern_type: Pattern type

        Returns:
            Confidence bonus (0-20)
        """
        bonus = 0

        # Bonus if pattern is surrounded by separators
        start_char = filename[match.start() - 1] if match.start() > 0 else " "
        end_char = filename[match.end()] if match.end() < len(filename) else " "

        if start_char in [" ", ".", "-", "_", "[", "("]:
            bonus += 5
        if end_char in [" ", ".", "-", "_", "]", ")"]:
            bonus += 5

        # Bonus for presence of TV series keywords
        tv_keywords = ["series", "season", "episode", "ep", "stagione"]
        filename_lower = filename.lower()

        for keyword in tv_keywords:
            if keyword in filename_lower:
                bonus += 3
                break

        # Penalty for formats that could be years
        if pattern_type == "concatenated":
            # If it looks like a year (1900-2030), reduce confidence
            full_num = int(match.group(0)) if match.group(0).isdigit() else 0
            if 1900 <= full_num <= 2030:
                bonus -= 10

        return max(0, min(20, bonus))  # Limit between 0 and 20

    @classmethod
    def _extract_clean_series_name(cls, raw_name: str) -> str:
        """
        Extract clean series name by removing extra tags

        Args:
            raw_name: Raw series name

        Returns:
            Clean series name
        """
        # List of separators that might indicate start of extra metadata

        # Try to find a natural cutting point
        # First look for common patterns that indicate end of title
        end_patterns = [
            r"@\w+",  # Tags like @Serietvfilms, @username
            r"(?i)\b(?:" + "|".join(cls.QUALITY_TAGS) + r")\b",  # Quality tags
            r"\b\d{4}\b",  # Year
            r"\b(?:season|s)\d+\b",  # Season
            r"\b(?:complete|completa)\b",  # Complete series
            r"\b(?:multi|dual)\b",  # Multi audio
        ]

        clean_name = raw_name

        for pattern in end_patterns:
            match = re.search(pattern, clean_name)
            if match:
                # Cut at first match and clean
                clean_name = clean_name[: match.start()].strip()
                clean_name = re.sub(r"[\.\-_\s]+$", "", clean_name)
                break

        # If name is still empty or too short, use original
        if len(clean_name.strip()) < 3:
            clean_name = raw_name

        return clean_name

    @classmethod
    def _extract_episode_title(cls, filename: str, match) -> Optional[str]:
        """
        Extract episode title from filename

        Args:
            filename: Filename
            match: Regex match of SE pattern

        Returns:
            Episode title if found
        """
        # Search after SE pattern until quality tags or end
        after_match = filename[match.end() :].strip()

        # Patterns to find title (until quality tags or parentheses)
        title_patterns = [
            r"^[\s\-\.]*(.+?)[\[\(]",  # Until [ or (
            r"^[\s\-\.]*(.+?)\s+(?:" + "|".join(cls.QUALITY_TAGS) + r")",  # Until quality tag
            r"^[\s\-\.]*(.+?)\.(?:mkv|mp4|avi|mov|wmv|flv|webm|ts)$",  # Until extension
            r"^[\s\-\.]*(.+?)$",  # Rest of string
        ]

        for pattern in title_patterns:
            title_match = re.search(pattern, after_match, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                # Clean the title
                title = re.sub(r"[\-\.]+$", "", title).strip()
                if len(title) > 3:  # Minimum 3 characters to be valid
                    return cls.sanitize_filename(title)

        return None
