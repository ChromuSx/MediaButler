"""
Data models for MediaButler
"""

from dataclasses import dataclass, field
from typing import Optional, Any, List
from pathlib import Path
from enum import Enum


class MediaType(Enum):
    """Media type"""

    MOVIE = "movie"
    TV_SHOW = "tv"
    UNKNOWN = "unknown"


class DownloadStatus(Enum):
    """Download status"""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_SPACE = "waiting_space"
    QUEUED = "queued"


@dataclass
class SeriesInfo:
    """TV series information"""

    series_name: str
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_title: Optional[str] = None
    end_episode: Optional[int] = None  # For multi-episodes (S01E01-E03)
    confidence: int = 0  # Recognition confidence (0-120)

    @property
    def season_folder(self) -> str:
        """Season folder name"""
        if self.season:
            return f"Season {self.season:02d}"
        return "Season 01"

    @property
    def episode_code(self) -> str:
        """Episode code (e.g.: S01E01 or S01E01-E03)"""
        if self.season and self.episode:
            code = f"S{self.season:02d}E{self.episode:02d}"
            if self.end_episode and self.end_episode != self.episode:
                code += f"-E{self.end_episode:02d}"
            return code
        return ""

    @property
    def is_multi_episode(self) -> bool:
        """True if it's a multi-episode"""
        return self.end_episode is not None and self.end_episode > self.episode

    @property
    def is_high_confidence(self) -> bool:
        """True if recognition has high confidence (>=70)"""
        return self.confidence >= 70


@dataclass
class TMDBResult:
    """TMDB search result"""

    id: int
    title: str
    original_title: str
    media_type: str
    year: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    overview: Optional[str] = None
    vote_average: float = 0.0
    confidence: int = 0

    @property
    def is_movie(self) -> bool:
        return self.media_type == "movie"

    @property
    def is_tv_show(self) -> bool:
        return self.media_type == "tv"

    @property
    def poster_url(self) -> Optional[str]:
        if self.poster_path:
            return f"https://image.tmdb.org/t/p/w200{self.poster_path}"
        return None


@dataclass
class DownloadInfo:
    """Complete download information"""

    # Identifiers
    message_id: int
    user_id: int

    # File info
    filename: str
    original_filename: str
    size: int

    # Media info
    media_type: MediaType = MediaType.UNKNOWN
    is_movie: Optional[bool] = None
    movie_folder: Optional[str] = None
    series_info: Optional[SeriesInfo] = None
    selected_season: Optional[int] = None

    # TMDB
    tmdb_results: List[TMDBResult] = field(default_factory=list)
    selected_tmdb: Optional[TMDBResult] = None
    tmdb_confidence: int = 0

    # Paths
    dest_path: Optional[Path] = None
    final_path: Optional[Path] = None

    # Status
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    speed_mbps: float = 0.0
    eta_seconds: Optional[int] = None

    # Telegram messages
    message: Any = None  # Telethon message object
    progress_msg: Any = None  # Progress message object
    event: Any = None  # Callback event

    # Metadata
    created_folders: List[Path] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    waiting_for_season: bool = False  # True when waiting for manual season input

    @property
    def size_gb(self) -> float:
        """Size in GB"""
        return self.size / (1024 * 1024 * 1024)

    @property
    def size_mb(self) -> float:
        """Size in MB"""
        return self.size / (1024 * 1024)

    @property
    def display_name(self) -> str:
        """Name to display to user"""
        if self.selected_tmdb:
            return self.selected_tmdb.title
        elif self.series_info and self.series_info.series_name:
            return self.series_info.series_name
        elif self.movie_folder:
            return self.movie_folder
        return self.filename

    @property
    def folder_structure(self) -> str:
        """Folder structure for display"""
        if self.is_movie:
            return f"{self.movie_folder}/"
        elif self.series_info:
            return f"{self.series_info.series_name}/{self.series_info.season_folder}/"
        return ""

    def get_final_filename(self) -> str:
        """Calculate the final filename"""
        if self.selected_tmdb and self.tmdb_confidence >= 60:
            extension = Path(self.original_filename).suffix

            if self.is_movie:
                title = self.selected_tmdb.title
                year = self.selected_tmdb.year
                return f"{title} ({year}){extension}" if year else f"{title}{extension}"
            else:
                # TV Series
                if self.series_info and self.series_info.episode_code:
                    filename = f"{self.selected_tmdb.title} - {self.series_info.episode_code}"
                    if self.series_info.episode_title:
                        filename += f" - {self.series_info.episode_title}"
                    return f"{filename}{extension}"

        return self.filename


@dataclass
class QueueItem:
    """Download queue item"""

    download_info: DownloadInfo
    priority: int = 0  # Priority (0 = normal, higher = more priority)
    retry_count: int = 0
    max_retries: int = 3

    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries
