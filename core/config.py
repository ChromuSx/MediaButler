"""
Centralized configuration for MediaButler
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

# Load environment variables
try:
    from dotenv import load_dotenv

    env_path = Path(".env")
    if env_path.exists():
        load_dotenv()
        print("OK .env file loaded successfully")
except ImportError:
    print("WARNING python-dotenv not installed")


@dataclass
class TelegramConfig:
    """Telegram configuration"""

    api_id: int
    api_hash: str
    bot_token: str
    session_path: str


@dataclass
class TMDBConfig:
    """TMDB configuration"""

    api_key: Optional[str]
    base_url: str = "https://api.themoviedb.org/3"
    image_base: str = "https://image.tmdb.org/t/p/"
    language: str = "it-IT"

    @property
    def is_enabled(self) -> bool:
        return bool(self.api_key)


@dataclass
class PathsConfig:
    """Paths configuration"""

    movies: Path
    tv: Path
    temp: Path

    def create_directories(self):
        """Create directories if they don't exist"""
        for path in [self.movies, self.tv, self.temp]:
            path.mkdir(parents=True, exist_ok=True)


@dataclass
class LimitsConfig:
    """Limits and thresholds configuration"""

    max_concurrent_downloads: int = 3
    min_free_space_gb: float = 5.0
    warning_threshold_gb: float = 10.0
    space_check_interval: int = 30
    max_file_size_gb: float = 10.0


@dataclass
class AuthConfig:
    """Authorization configuration"""

    authorized_users: List[int]
    admin_mode: bool

    @property
    def first_admin(self) -> Optional[int]:
        return self.authorized_users[0] if self.authorized_users else None


@dataclass
class SubtitleConfig:
    """Subtitles configuration"""

    enabled: bool = False
    auto_download: bool = False
    languages: List[str] = None
    opensubtitles_user_agent: str = "MediaButler v1.0"
    opensubtitles_username: Optional[str] = None
    opensubtitles_password: Optional[str] = None
    preferred_format: str = "srt"

    def __post_init__(self):
        if self.languages is None:
            self.languages = ["it", "en"]

    @property
    def is_opensubtitles_configured(self) -> bool:
        return bool(self.opensubtitles_username and self.opensubtitles_password)


@dataclass
class DatabaseConfig:
    """Database configuration"""

    path: Path
    enabled: bool = True


@dataclass
class ExtractionConfig:
    """Archive extraction configuration"""

    enabled: bool = True
    delete_after_extract: bool = True
    supported_formats: List[str] = None

    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = [".zip", ".rar", ".7z"]


class Config:
    """Main MediaButler configuration"""

    def __init__(self):
        self.telegram = self._load_telegram_config()
        self.tmdb = self._load_tmdb_config()
        self.paths = self._load_paths_config()
        self.limits = self._load_limits_config()
        self.auth = self._load_auth_config()
        self.subtitles = self._load_subtitle_config()
        self.database = self._load_database_config()
        self.extraction = self._load_extraction_config()
        self.logger = self._setup_logging()

        # Validation
        self._validate_config()

        # Create necessary directories
        self.paths.create_directories()

        # Create directory for session
        Path(os.path.dirname(self.telegram.session_path)).mkdir(
            parents=True, exist_ok=True
        )

        # Create directory for database
        self.database.path.parent.mkdir(parents=True, exist_ok=True)

    def _load_telegram_config(self) -> TelegramConfig:
        """Load Telegram configuration"""
        api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
        api_hash = os.getenv("TELEGRAM_API_HASH", "")
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

        if sys.platform == "win32":
            session_path = os.getenv("SESSION_PATH", "./session/bot_session")
        else:
            session_path = os.getenv("SESSION_PATH", "/app/session/bot_session")

        return TelegramConfig(
            api_id=api_id,
            api_hash=api_hash,
            bot_token=bot_token,
            session_path=session_path,
        )

    def _load_tmdb_config(self) -> TMDBConfig:
        """Load TMDB configuration"""
        return TMDBConfig(
            api_key=os.getenv("TMDB_API_KEY", "") or None,
            language=os.getenv("TMDB_LANGUAGE", "it-IT"),
        )

    def _load_paths_config(self) -> PathsConfig:
        """Load paths configuration"""
        return PathsConfig(
            movies=Path(os.getenv("MOVIES_PATH", "/media/movies")),
            tv=Path(os.getenv("TV_PATH", "/media/tv")),
            temp=Path(os.getenv("TEMP_PATH", "/media/temp")),
        )

    def _load_limits_config(self) -> LimitsConfig:
        """Load limits configuration"""
        return LimitsConfig(
            max_concurrent_downloads=int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3")),
            min_free_space_gb=float(os.getenv("MIN_FREE_SPACE_GB", "5")),
            warning_threshold_gb=float(os.getenv("WARNING_THRESHOLD_GB", "10")),
            space_check_interval=int(os.getenv("SPACE_CHECK_INTERVAL", "30")),
        )

    def _load_auth_config(self) -> AuthConfig:
        """Load authorization configuration"""
        users_str = os.getenv("AUTHORIZED_USERS", "")
        authorized_users = [
            int(uid.strip()) for uid in users_str.split(",") if uid.strip()
        ]

        return AuthConfig(
            authorized_users=authorized_users, admin_mode=len(authorized_users) == 0
        )

    def _load_subtitle_config(self) -> SubtitleConfig:
        """Load subtitles configuration"""
        languages_str = os.getenv("SUBTITLE_LANGUAGES", "it,en")
        languages = [lang.strip() for lang in languages_str.split(",") if lang.strip()]

        return SubtitleConfig(
            enabled=os.getenv("SUBTITLE_ENABLED", "false").lower() == "true",
            auto_download=os.getenv("SUBTITLE_AUTO_DOWNLOAD", "false").lower()
            == "true",
            languages=languages,
            opensubtitles_user_agent=os.getenv(
                "OPENSUBTITLES_USER_AGENT", "MediaButler v1.0"
            ),
            opensubtitles_username=os.getenv("OPENSUBTITLES_USERNAME") or None,
            opensubtitles_password=os.getenv("OPENSUBTITLES_PASSWORD") or None,
            preferred_format=os.getenv("SUBTITLE_FORMAT", "srt"),
        )

    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration"""
        db_path = os.getenv("DATABASE_PATH", "data/mediabutler.db")
        enabled = os.getenv("DATABASE_ENABLED", "true").lower() == "true"

        return DatabaseConfig(path=Path(db_path), enabled=enabled)

    def _load_extraction_config(self) -> ExtractionConfig:
        """Load extraction configuration"""
        enabled = os.getenv("EXTRACTION_ENABLED", "true").lower() == "true"
        delete_after = os.getenv("EXTRACTION_DELETE_AFTER", "true").lower() == "true"

        return ExtractionConfig(enabled=enabled, delete_after_extract=delete_after)

    def _setup_logging(self) -> logging.Logger:
        """Configure logging"""
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )
        return logging.getLogger("MediaButler")

    def _validate_config(self):
        """Validate configuration"""
        if not all(
            [self.telegram.api_id, self.telegram.api_hash, self.telegram.bot_token]
        ):
            self.logger.error("Missing Telegram credentials!")
            self.logger.error(
                "Configure: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN"
            )
            sys.exit(1)

    def log_config(self):
        """Log current configuration"""
        self.logger.info("=== MEDIABUTLER CONFIGURATION ===")
        self.logger.info(f"Movies path: {self.paths.movies}")
        self.logger.info(f"TV path: {self.paths.tv}")
        self.logger.info(f"Authorized users: {len(self.auth.authorized_users)}")
        self.logger.info(f"Admin mode: {self.auth.admin_mode}")
        self.logger.info(f"TMDB enabled: {self.tmdb.is_enabled}")
        self.logger.info(f"Subtitles enabled: {self.subtitles.enabled}")
        self.logger.info(f"Subtitle auto-download: {self.subtitles.auto_download}")
        self.logger.info(f"Database enabled: {self.database.enabled}")
        self.logger.info(f"Database path: {self.database.path}")
        self.logger.info(f"Archive extraction enabled: {self.extraction.enabled}")
        self.logger.info(
            f"Delete archives after extraction: {self.extraction.delete_after_extract}"
        )
        self.logger.info(
            f"Max concurrent downloads: {self.limits.max_concurrent_downloads}"
        )
        self.logger.info(f"Min free space: {self.limits.min_free_space_gb} GB")


# Singleton for global configuration
_config: Optional[Config] = None


def get_config() -> Config:
    """Get configuration instance (singleton)"""
    global _config
    if _config is None:
        _config = Config()
    return _config
