"""
Modelli dati per MediaButler
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path
from enum import Enum


class MediaType(Enum):
    """Tipo di media"""
    MOVIE = "movie"
    TV_SHOW = "tv"
    UNKNOWN = "unknown"


class DownloadStatus(Enum):
    """Stato del download"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_SPACE = "waiting_space"
    QUEUED = "queued"


@dataclass
class SeriesInfo:
    """Informazioni serie TV"""
    series_name: str
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_title: Optional[str] = None
    end_episode: Optional[int] = None  # Per multi-episodi (S01E01-E03)
    confidence: int = 0  # Confidence del riconoscimento (0-120)

    @property
    def season_folder(self) -> str:
        """Nome cartella stagione"""
        if self.season:
            return f"Season {self.season:02d}"
        return "Season 01"

    @property
    def episode_code(self) -> str:
        """Codice episodio (es: S01E01 o S01E01-E03)"""
        if self.season and self.episode:
            code = f"S{self.season:02d}E{self.episode:02d}"
            if self.end_episode and self.end_episode != self.episode:
                code += f"-E{self.end_episode:02d}"
            return code
        return ""

    @property
    def is_multi_episode(self) -> bool:
        """True se è un multi-episodio"""
        return self.end_episode is not None and self.end_episode > self.episode

    @property
    def is_high_confidence(self) -> bool:
        """True se il riconoscimento ha alta confidenza (>=70)"""
        return self.confidence >= 70


@dataclass
class TMDBResult:
    """Risultato ricerca TMDB"""
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
        return self.media_type == 'movie'
    
    @property
    def is_tv_show(self) -> bool:
        return self.media_type == 'tv'
    
    @property
    def poster_url(self) -> Optional[str]:
        if self.poster_path:
            return f"https://image.tmdb.org/t/p/w200{self.poster_path}"
        return None


@dataclass
class DownloadInfo:
    """Informazioni complete download"""
    # Identificativi
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
    
    # Percorsi
    dest_path: Optional[Path] = None
    final_path: Optional[Path] = None
    
    # Stato
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    speed_mbps: float = 0.0
    eta_seconds: Optional[int] = None
    
    # Messaggi Telegram
    message: Any = None  # Telethon message object
    progress_msg: Any = None  # Progress message object
    event: Any = None  # Callback event
    
    # Metadata
    created_folders: List[Path] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    waiting_for_season: bool = False  # True quando attende input manuale stagione
    
    @property
    def size_gb(self) -> float:
        """Dimensione in GB"""
        return self.size / (1024 * 1024 * 1024)
    
    @property
    def size_mb(self) -> float:
        """Dimensione in MB"""
        return self.size / (1024 * 1024)
    
    @property
    def display_name(self) -> str:
        """Nome da mostrare all'utente"""
        if self.selected_tmdb:
            return self.selected_tmdb.title
        elif self.series_info and self.series_info.series_name:
            return self.series_info.series_name
        elif self.movie_folder:
            return self.movie_folder
        return self.filename
    
    @property
    def folder_structure(self) -> str:
        """Struttura cartelle per display"""
        if self.is_movie:
            return f"{self.movie_folder}/"
        elif self.series_info:
            return f"{self.series_info.series_name}/{self.series_info.season_folder}/"
        return ""
    
    def get_final_filename(self) -> str:
        """Calcola il nome file finale"""
        if self.selected_tmdb and self.tmdb_confidence >= 60:
            extension = Path(self.original_filename).suffix
            
            if self.is_movie:
                title = self.selected_tmdb.title
                year = self.selected_tmdb.year
                return f"{title} ({year}){extension}" if year else f"{title}{extension}"
            else:
                # Serie TV
                if self.series_info and self.series_info.episode_code:
                    filename = f"{self.selected_tmdb.title} - {self.series_info.episode_code}"
                    if self.series_info.episode_title:
                        filename += f" - {self.series_info.episode_title}"
                    return f"{filename}{extension}"
        
        return self.filename


@dataclass
class QueueItem:
    """Elemento in coda download"""
    download_info: DownloadInfo
    priority: int = 0  # Priorità (0 = normale, higher = più priorità)
    retry_count: int = 0
    max_retries: int = 3
    
    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries