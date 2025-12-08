"""
User-specific configuration with fallback to global defaults
"""
from pathlib import Path
from typing import Optional, List, Any
from core.config import get_config
from core.database import DatabaseManager
from utils.helpers import ValidationHelpers


class UserConfig:
    """
    User-specific configuration manager
    Provides user settings with fallback to global config
    """

    def __init__(self, user_id: int, database: DatabaseManager):
        """
        Initialize user configuration

        Args:
            user_id: Telegram user ID
            database: Database manager instance
        """
        self.user_id = user_id
        self.database = database
        self.global_config = get_config()

    async def get_movies_path(self) -> Path:
        """Get movies path for this user"""
        custom_path = await self.database.get_user_setting(
            self.user_id,
            'movies_path'
        )
        if custom_path:
            return Path(custom_path)
        return self.global_config.paths.movies

    async def get_tv_path(self) -> Path:
        """Get TV shows path for this user"""
        custom_path = await self.database.get_user_setting(
            self.user_id,
            'tv_path'
        )
        if custom_path:
            return Path(custom_path)
        return self.global_config.paths.tv

    async def get_max_concurrent_downloads(self) -> int:
        """Get max concurrent downloads for this user"""
        user_limit = await self.database.get_user_setting(
            self.user_id,
            'max_concurrent_downloads'
        )
        if user_limit is not None:
            return int(user_limit)
        return self.global_config.limits.max_concurrent_downloads

    async def get_auto_confirm_threshold(self) -> int:
        """
        Get auto-confirm threshold for TMDB matches
        If TMDB confidence >= threshold, skip user confirmation
        """
        threshold = await self.database.get_user_setting(
            self.user_id,
            'auto_confirm_threshold',
            default=70
        )
        return int(threshold) if threshold is not None else 70

    async def get_tmdb_language(self) -> str:
        """Get TMDB language preference"""
        lang = await self.database.get_user_setting(
            self.user_id,
            'tmdb_language'
        )
        if lang:
            return str(lang)
        return self.global_config.tmdb.language

    async def get_subtitle_enabled(self) -> bool:
        """Get subtitle system enabled status"""
        enabled = await self.database.get_user_setting(
            self.user_id,
            'subtitle_enabled'
        )
        if enabled is not None:
            return bool(enabled)
        return self.global_config.subtitles.enabled

    async def get_subtitle_languages(self) -> List[str]:
        """Get preferred subtitle languages"""
        langs = await self.database.get_user_setting(
            self.user_id,
            'subtitle_languages'
        )
        if langs:
            return [lang.strip() for lang in str(langs).split(',') if lang.strip()]
        return self.global_config.subtitles.languages

    async def get_subtitle_auto_download(self) -> bool:
        """Get auto-download subtitles preference"""
        auto_dl = await self.database.get_user_setting(
            self.user_id,
            'subtitle_auto_download'
        )
        if auto_dl is not None:
            return bool(auto_dl)
        return self.global_config.subtitles.auto_download

    async def get_subtitle_format(self) -> str:
        """Get preferred subtitle format"""
        fmt = await self.database.get_user_setting(
            self.user_id,
            'subtitle_format'
        )
        if fmt:
            return str(fmt)
        return self.global_config.subtitles.preferred_format

    async def get_notify_download_complete(self) -> bool:
        """Get notification preference for completed downloads"""
        notify = await self.database.get_user_setting(
            self.user_id,
            'notify_download_complete',
            default=True
        )
        return bool(notify) if notify is not None else True

    async def get_notify_download_failed(self) -> bool:
        """Get notification preference for failed downloads"""
        notify = await self.database.get_user_setting(
            self.user_id,
            'notify_download_failed',
            default=True
        )
        return bool(notify) if notify is not None else True

    async def get_notify_low_space(self) -> bool:
        """Get notification preference for low space warnings"""
        notify = await self.database.get_user_setting(
            self.user_id,
            'notify_low_space',
            default=True
        )
        return bool(notify) if notify is not None else True

    async def get_ui_language(self) -> str:
        """Get UI language preference"""
        lang = await self.database.get_user_setting(
            self.user_id,
            'ui_language',
            default='en'
        )
        return str(lang) if lang else 'en'

    async def get_compact_messages(self) -> bool:
        """Get compact messages preference (concise vs detailed)"""
        compact = await self.database.get_user_setting(
            self.user_id,
            'compact_messages',
            default=False
        )
        return bool(compact) if compact is not None else False

    async def set_movies_path(self, path: str):
        """
        Set custom movies path with security validation

        Args:
            path: Custom path for movies

        Raises:
            ValueError: If path is outside allowed directories
        """
        # Get allowed base paths (movies and tv paths from global config)
        allowed_bases = [
            self.global_config.paths.movies.parent,  # Allow within movies parent
            self.global_config.paths.movies,         # Allow movies path itself
        ]

        # Validate path
        is_valid, error_msg = ValidationHelpers.validate_user_path(path, allowed_bases)
        if not is_valid:
            raise ValueError(f"Invalid movies path: {error_msg}")

        await self.database.set_user_setting(self.user_id, 'movies_path', path)

    async def set_tv_path(self, path: str):
        """
        Set custom TV shows path with security validation

        Args:
            path: Custom path for TV shows

        Raises:
            ValueError: If path is outside allowed directories
        """
        # Get allowed base paths
        allowed_bases = [
            self.global_config.paths.tv.parent,  # Allow within tv parent
            self.global_config.paths.tv,         # Allow tv path itself
        ]

        # Validate path
        is_valid, error_msg = ValidationHelpers.validate_user_path(path, allowed_bases)
        if not is_valid:
            raise ValueError(f"Invalid TV path: {error_msg}")

        await self.database.set_user_setting(self.user_id, 'tv_path', path)

    async def set_max_concurrent_downloads(self, limit: int):
        """Set max concurrent downloads limit"""
        await self.database.set_user_setting(self.user_id, 'max_concurrent_downloads', limit)

    async def set_auto_confirm_threshold(self, threshold: int):
        """Set auto-confirm threshold (0-100)"""
        if 0 <= threshold <= 100:
            await self.database.set_user_setting(self.user_id, 'auto_confirm_threshold', threshold)

    async def set_tmdb_language(self, language: str):
        """Set TMDB language (e.g., 'it-IT', 'en-US')"""
        await self.database.set_user_setting(self.user_id, 'tmdb_language', language)

    async def set_subtitle_enabled(self, enabled: bool):
        """Enable/disable subtitle system"""
        await self.database.set_user_setting(self.user_id, 'subtitle_enabled', enabled)

    async def set_subtitle_languages(self, languages: List[str]):
        """Set preferred subtitle languages"""
        langs_str = ','.join(languages)
        await self.database.set_user_setting(self.user_id, 'subtitle_languages', langs_str)

    async def set_subtitle_auto_download(self, enabled: bool):
        """Enable/disable auto-download subtitles"""
        await self.database.set_user_setting(self.user_id, 'subtitle_auto_download', enabled)

    async def set_subtitle_format(self, format: str):
        """Set preferred subtitle format"""
        await self.database.set_user_setting(self.user_id, 'subtitle_format', format)

    async def set_notify_download_complete(self, enabled: bool):
        """Enable/disable download complete notifications"""
        await self.database.set_user_setting(self.user_id, 'notify_download_complete', enabled)

    async def set_notify_download_failed(self, enabled: bool):
        """Enable/disable download failed notifications"""
        await self.database.set_user_setting(self.user_id, 'notify_download_failed', enabled)

    async def set_notify_low_space(self, enabled: bool):
        """Enable/disable low space notifications"""
        await self.database.set_user_setting(self.user_id, 'notify_low_space', enabled)

    async def set_ui_language(self, language: str):
        """Set UI language ('en', 'it', 'es')"""
        await self.database.set_user_setting(self.user_id, 'ui_language', language)

    async def set_compact_messages(self, enabled: bool):
        """Enable/disable compact messages"""
        await self.database.set_user_setting(self.user_id, 'compact_messages', enabled)

    async def reset_to_defaults(self):
        """Reset all user preferences to global defaults"""
        await self.database.reset_user_preferences(self.user_id)

    async def get_all_settings(self) -> dict:
        """Get all current settings (including defaults)"""
        return {
            'movies_path': str(await self.get_movies_path()),
            'tv_path': str(await self.get_tv_path()),
            'max_concurrent_downloads': await self.get_max_concurrent_downloads(),
            'auto_confirm_threshold': await self.get_auto_confirm_threshold(),
            'tmdb_language': await self.get_tmdb_language(),
            'subtitle_enabled': await self.get_subtitle_enabled(),
            'subtitle_languages': await self.get_subtitle_languages(),
            'subtitle_auto_download': await self.get_subtitle_auto_download(),
            'subtitle_format': await self.get_subtitle_format(),
            'notify_download_complete': await self.get_notify_download_complete(),
            'notify_download_failed': await self.get_notify_download_failed(),
            'notify_low_space': await self.get_notify_low_space(),
            'ui_language': await self.get_ui_language(),
            'compact_messages': await self.get_compact_messages()
        }


async def get_user_config(user_id: int, database: DatabaseManager) -> UserConfig:
    """
    Get user configuration instance

    Args:
        user_id: Telegram user ID
        database: Database manager instance

    Returns:
        UserConfig instance for this user
    """
    return UserConfig(user_id, database)
