"""
Database manager for MediaButler
Handles persistent storage of download history, statistics, and user preferences
"""

import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any

from core.config import get_config
from models.download import DownloadInfo, DownloadStatus


class DatabaseManager:
    """Manager for SQLite database operations"""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database manager"""
        self.config = get_config()
        self.logger = self.config.logger

        # Database path
        if db_path is None:
            db_path = Path("data/mediabutler.db")

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Connect to database and create tables"""
        self._connection = await aiosqlite.connect(str(self.db_path))
        self._connection.row_factory = aiosqlite.Row

        await self._create_tables()
        self.logger.info(f"✅ Database connected: {self.db_path}")

    async def close(self):
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            self.logger.info("Database connection closed")

    async def _create_tables(self):
        """Create database tables if they don't exist"""

        # Downloads history table
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,

                -- Media info
                media_type TEXT NOT NULL,
                is_movie BOOLEAN,
                movie_title TEXT,
                series_name TEXT,
                season INTEGER,
                episode INTEGER,

                -- TMDB info
                tmdb_id INTEGER,
                tmdb_title TEXT,
                tmdb_year TEXT,
                tmdb_confidence INTEGER DEFAULT 0,

                -- Paths
                dest_path TEXT,
                final_path TEXT,

                -- Status
                status TEXT NOT NULL,
                progress REAL DEFAULT 0.0,

                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,

                -- Metadata
                error_message TEXT,
                download_duration_seconds INTEGER,
                average_speed_mbps REAL
            )
        """
        )

        # User statistics table
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER PRIMARY KEY,
                total_downloads INTEGER DEFAULT 0,
                total_bytes INTEGER DEFAULT 0,
                successful_downloads INTEGER DEFAULT 0,
                failed_downloads INTEGER DEFAULT 0,
                cancelled_downloads INTEGER DEFAULT 0,
                first_download TIMESTAMP,
                last_download TIMESTAMP
            )
        """
        )

        # TMDB cache table
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tmdb_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                media_type TEXT NOT NULL,
                tmdb_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                original_title TEXT,
                year TEXT,
                poster_path TEXT,
                overview TEXT,
                vote_average REAL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(query, media_type, tmdb_id)
            )
        """
        )

        # User preferences table
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,

                -- Paths (override global defaults)
                movies_path TEXT,
                tv_path TEXT,

                -- Download settings
                max_concurrent_downloads INTEGER,
                auto_confirm_threshold INTEGER DEFAULT 70,

                -- TMDB settings
                tmdb_language TEXT,

                -- Subtitle settings
                subtitle_enabled BOOLEAN,
                subtitle_languages TEXT,
                subtitle_auto_download BOOLEAN DEFAULT 0,
                subtitle_format TEXT,

                -- Notification settings
                notify_download_complete BOOLEAN DEFAULT 1,
                notify_download_failed BOOLEAN DEFAULT 1,
                notify_low_space BOOLEAN DEFAULT 1,

                -- UI settings
                ui_language TEXT DEFAULT 'en',
                compact_messages BOOLEAN DEFAULT 0,

                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Authorized users table (for dynamic user management)
        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS authorized_users (
                user_id INTEGER PRIMARY KEY,
                telegram_username TEXT,
                is_admin BOOLEAN DEFAULT 0,
                is_banned BOOLEAN DEFAULT 0,
                added_by INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP,
                notes TEXT
            )
        """
        )

        # Create indexes for better performance
        await self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_downloads_user_id
            ON downloads(user_id)
        """
        )

        await self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_downloads_status
            ON downloads(status)
        """
        )

        await self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_downloads_created_at
            ON downloads(created_at)
        """
        )

        await self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tmdb_cache_query
            ON tmdb_cache(query, media_type)
        """
        )

        await self._connection.commit()
        self.logger.info("Database tables created/verified")

    # ==================== DOWNLOAD HISTORY ====================

    async def add_download(self, download_info: DownloadInfo) -> int:
        """
        Add a new download to history

        Args:
            download_info: Download information

        Returns:
            Database ID of inserted row
        """
        cursor = await self._connection.execute(
            """
            INSERT INTO downloads (
                message_id, user_id, filename, original_filename, size_bytes,
                media_type, is_movie, movie_title, series_name, season, episode,
                tmdb_id, tmdb_title, tmdb_year, tmdb_confidence,
                dest_path, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
            (
                download_info.message_id,
                download_info.user_id,
                download_info.filename,
                download_info.original_filename,
                download_info.size,
                download_info.media_type.value,
                download_info.is_movie,
                download_info.movie_folder,
                (
                    download_info.series_info.series_name
                    if download_info.series_info
                    else None
                ),
                download_info.series_info.season if download_info.series_info else None,
                (
                    download_info.series_info.episode
                    if download_info.series_info
                    else None
                ),
                download_info.selected_tmdb.id if download_info.selected_tmdb else None,
                (
                    download_info.selected_tmdb.title
                    if download_info.selected_tmdb
                    else None
                ),
                (
                    download_info.selected_tmdb.year
                    if download_info.selected_tmdb
                    else None
                ),
                download_info.tmdb_confidence,
                str(download_info.dest_path) if download_info.dest_path else None,
                download_info.status.value,
            ),
        )

        await self._connection.commit()
        return cursor.lastrowid

    async def update_download_status(
        self,
        message_id: int,
        status: DownloadStatus,
        progress: Optional[float] = None,
        error_message: Optional[str] = None,
    ):
        """Update download status"""

        updates = ["status = ?"]
        params = [status.value]

        if progress is not None:
            updates.append("progress = ?")
            params.append(progress)

        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)

        # Set timestamps based on status
        if status == DownloadStatus.DOWNLOADING:
            updates.append("started_at = CURRENT_TIMESTAMP")
        elif status in [
            DownloadStatus.COMPLETED,
            DownloadStatus.FAILED,
            DownloadStatus.CANCELLED,
        ]:
            updates.append("completed_at = CURRENT_TIMESTAMP")

        params.append(message_id)

        query = f"UPDATE downloads SET {', '.join(updates)} WHERE message_id = ?"
        await self._connection.execute(query, params)
        await self._connection.commit()

    async def complete_download(
        self,
        message_id: int,
        final_path: str,
        duration_seconds: int,
        average_speed_mbps: float,
    ):
        """Mark download as completed with final details"""
        await self._connection.execute(
            """
            UPDATE downloads
            SET status = ?,
                final_path = ?,
                completed_at = CURRENT_TIMESTAMP,
                download_duration_seconds = ?,
                average_speed_mbps = ?,
                progress = 100.0
            WHERE message_id = ?
        """,
            (
                DownloadStatus.COMPLETED.value,
                final_path,
                duration_seconds,
                average_speed_mbps,
                message_id,
            ),
        )

        await self._connection.commit()

    async def get_download_by_message_id(self, message_id: int) -> Optional[Dict]:
        """Get download by message ID"""
        cursor = await self._connection.execute(
            "SELECT * FROM downloads WHERE message_id = ?", (message_id,)
        )
        row = await cursor.fetchone()

        if row:
            return dict(row)
        return None

    async def get_user_downloads(
        self, user_id: int, limit: int = 50, status: Optional[DownloadStatus] = None
    ) -> List[Dict]:
        """Get downloads for a specific user"""

        query = "SELECT * FROM downloads WHERE user_id = ?"
        params = [user_id]

        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = await self._connection.execute(query, params)
        rows = await cursor.fetchall()

        return [dict(row) for row in rows]

    async def get_recent_downloads(self, limit: int = 20) -> List[Dict]:
        """Get recent downloads across all users"""
        cursor = await self._connection.execute(
            """
            SELECT * FROM downloads
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def check_duplicate_file(
        self, filename: str, user_id: Optional[int] = None
    ) -> Optional[Dict]:
        """Check if file was already downloaded"""

        if user_id:
            cursor = await self._connection.execute(
                """
                SELECT * FROM downloads
                WHERE (filename = ? OR original_filename = ?)
                AND user_id = ?
                AND status = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (filename, filename, user_id, DownloadStatus.COMPLETED.value),
            )
        else:
            cursor = await self._connection.execute(
                """
                SELECT * FROM downloads
                WHERE (filename = ? OR original_filename = ?)
                AND status = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (filename, filename, DownloadStatus.COMPLETED.value),
            )

        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None

    # ==================== USER STATISTICS ====================

    async def update_user_stats(self, user_id: int, download_info: DownloadInfo):
        """Update user statistics after download"""

        # Get or create user stats
        cursor = await self._connection.execute(
            "SELECT * FROM user_stats WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()

        if row is None:
            # Create new stats entry
            await self._connection.execute(
                """
                INSERT INTO user_stats (
                    user_id, total_downloads, total_bytes,
                    successful_downloads, first_download, last_download
                ) VALUES (?, 1, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
                (user_id, download_info.size),
            )
        else:
            # Update existing stats
            await self._connection.execute(
                """
                UPDATE user_stats
                SET total_downloads = total_downloads + 1,
                    total_bytes = total_bytes + ?,
                    successful_downloads = successful_downloads + 1,
                    last_download = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """,
                (download_info.size, user_id),
            )

        await self._connection.commit()

    async def increment_failed_downloads(self, user_id: int):
        """Increment failed download counter"""
        await self._connection.execute(
            """
            UPDATE user_stats
            SET failed_downloads = failed_downloads + 1
            WHERE user_id = ?
        """,
            (user_id,),
        )
        await self._connection.commit()

    async def increment_cancelled_downloads(self, user_id: int):
        """Increment cancelled download counter"""
        await self._connection.execute(
            """
            UPDATE user_stats
            SET cancelled_downloads = cancelled_downloads + 1
            WHERE user_id = ?
        """,
            (user_id,),
        )
        await self._connection.commit()

    async def get_user_stats(self, user_id: int) -> Optional[Dict]:
        """Get statistics for a specific user"""
        cursor = await self._connection.execute(
            "SELECT * FROM user_stats WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()

        if row:
            return dict(row)
        return None

    async def get_all_stats(self) -> Dict[str, Any]:
        """Get global statistics"""

        # Total downloads
        cursor = await self._connection.execute(
            "SELECT COUNT(*) as total FROM downloads"
        )
        total = (await cursor.fetchone())["total"]

        # By status
        cursor = await self._connection.execute(
            """
            SELECT status, COUNT(*) as count
            FROM downloads
            GROUP BY status
        """
        )
        status_counts = {row["status"]: row["count"] for row in await cursor.fetchall()}

        # Total size
        cursor = await self._connection.execute(
            "SELECT SUM(size_bytes) as total_bytes FROM downloads WHERE status = ?",
            (DownloadStatus.COMPLETED.value,),
        )
        total_bytes = (await cursor.fetchone())["total_bytes"] or 0

        # Total users (count from authorized_users table)
        cursor = await self._connection.execute(
            "SELECT COUNT(*) as total_users FROM authorized_users WHERE is_banned = 0"
        )
        total_users = (await cursor.fetchone())["total_users"]

        # Top users
        cursor = await self._connection.execute(
            """
            SELECT user_id, total_downloads, total_bytes
            FROM user_stats
            ORDER BY total_downloads DESC
            LIMIT 5
        """
        )
        top_users = [dict(row) for row in await cursor.fetchall()]

        # Recent downloads (last 24h)
        cursor = await self._connection.execute(
            """
            SELECT COUNT(*) as count
            FROM downloads
            WHERE created_at > datetime('now', '-1 day')
        """
        )
        recent_24h = (await cursor.fetchone())["count"]

        # Most downloaded series
        cursor = await self._connection.execute(
            """
            SELECT series_name, COUNT(*) as count
            FROM downloads
            WHERE series_name IS NOT NULL
            AND status = ?
            GROUP BY series_name
            ORDER BY count DESC
            LIMIT 10
        """,
            (DownloadStatus.COMPLETED.value,),
        )
        top_series = [dict(row) for row in await cursor.fetchall()]

        # Calculate successful and failed downloads
        successful_downloads = status_counts.get(DownloadStatus.COMPLETED.value, 0)
        failed_downloads = status_counts.get(DownloadStatus.FAILED.value, 0)
        total_size_gb = total_bytes / (1024**3) if total_bytes else 0.0

        # Calculate average file size (only from completed downloads)
        avg_file_size_gb = (
            total_size_gb / successful_downloads if successful_downloads > 0 else 0.0
        )

        result = {
            "total_downloads": total,
            "successful_downloads": successful_downloads,
            "failed_downloads": failed_downloads,
            "status_counts": status_counts,
            "total_bytes": total_bytes,
            "total_size_gb": total_size_gb,
            "avg_file_size_gb": avg_file_size_gb,
            "total_users": total_users,
            "top_users": top_users,
            "recent_24h": recent_24h,
            "top_series": top_series,
        }

        return result

    # ==================== TMDB CACHE ====================

    async def cache_tmdb_result(
        self, query: str, media_type: str, tmdb_data: Dict[str, Any]
    ):
        """Cache TMDB search result"""
        try:
            await self._connection.execute(
                """
                INSERT OR REPLACE INTO tmdb_cache (
                    query, media_type, tmdb_id, title, original_title,
                    year, poster_path, overview, vote_average, cached_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (
                    query.lower(),
                    media_type,
                    tmdb_data.get("id"),
                    tmdb_data.get("title") or tmdb_data.get("name"),
                    tmdb_data.get("original_title") or tmdb_data.get("original_name"),
                    tmdb_data.get("release_date", "")[:4]
                    or tmdb_data.get("first_air_date", "")[:4],
                    tmdb_data.get("poster_path"),
                    tmdb_data.get("overview"),
                    tmdb_data.get("vote_average", 0.0),
                ),
            )
            await self._connection.commit()
        except Exception as e:
            self.logger.error(f"Error caching TMDB result: {e}")

    async def get_cached_tmdb_results(
        self, query: str, media_type: str, max_age_days: int = 30
    ) -> List[Dict]:
        """Get cached TMDB results"""
        cursor = await self._connection.execute(
            """
            SELECT * FROM tmdb_cache
            WHERE query = ?
            AND media_type = ?
            AND cached_at > datetime('now', '-' || ? || ' days')
            ORDER BY vote_average DESC
        """,
            (query.lower(), media_type, max_age_days),
        )

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def clean_old_cache(self, days: int = 90):
        """Clean old TMDB cache entries"""
        await self._connection.execute(
            """
            DELETE FROM tmdb_cache
            WHERE cached_at < datetime('now', '-' || ? || ' days')
        """,
            (days,),
        )
        await self._connection.commit()
        self.logger.info(f"Cleaned TMDB cache older than {days} days")

    # ==================== USER PREFERENCES ====================

    async def get_user_preferences(self, user_id: int) -> Optional[Dict]:
        """Get user preferences for a specific user"""
        cursor = await self._connection.execute(
            "SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()

        if row:
            return dict(row)
        return None

    async def get_user_setting(
        self, user_id: int, setting_name: str, default: Any = None
    ) -> Any:
        """
        Get a specific user setting with fallback to default

        Args:
            user_id: User ID
            setting_name: Name of the setting (column name in user_preferences)
            default: Default value if not set

        Returns:
            Setting value or default
        """
        prefs = await self.get_user_preferences(user_id)

        if prefs and setting_name in prefs and prefs[setting_name] is not None:
            return prefs[setting_name]

        return default

    async def set_user_setting(self, user_id: int, setting_name: str, value: Any):
        """
        Set a specific user setting

        Args:
            user_id: User ID
            setting_name: Name of the setting
            value: Value to set
        """
        existing = await self.get_user_preferences(user_id)

        if existing is None:
            # Create new preferences with this setting
            await self._connection.execute(
                f"""
                INSERT INTO user_preferences (user_id, {setting_name})
                VALUES (?, ?)
            """,
                (user_id, value),
            )
        else:
            # Update existing
            await self._connection.execute(
                f"""
                UPDATE user_preferences
                SET {setting_name} = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """,
                (value, user_id),
            )

        await self._connection.commit()

    async def update_user_preferences(self, user_id: int, preferences: Dict[str, Any]):
        """
        Update multiple user preferences at once

        Args:
            user_id: User ID
            preferences: Dictionary of settings to update
        """
        if not preferences:
            return

        existing = await self.get_user_preferences(user_id)

        if existing is None:
            # Create new preferences entry
            columns = ["user_id"] + list(preferences.keys())
            placeholders = ", ".join(["?"] * len(columns))
            values = [user_id] + list(preferences.values())

            await self._connection.execute(
                f"""
                INSERT INTO user_preferences ({', '.join(columns)})
                VALUES ({placeholders})
            """,
                values,
            )
        else:
            # Update existing preferences
            updates = [f"{key} = ?" for key in preferences.keys()]
            updates.append("updated_at = CURRENT_TIMESTAMP")

            params = list(preferences.values()) + [user_id]

            query = (
                f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_id = ?"
            )
            await self._connection.execute(query, params)

        await self._connection.commit()

    async def reset_user_preferences(self, user_id: int):
        """Reset user preferences to defaults (delete custom settings)"""
        await self._connection.execute(
            "DELETE FROM user_preferences WHERE user_id = ?", (user_id,)
        )
        await self._connection.commit()

    async def get_all_user_preferences(self) -> List[Dict]:
        """Get preferences for all users"""
        cursor = await self._connection.execute("SELECT * FROM user_preferences")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # ==================== AUTHORIZED USERS ====================

    async def get_authorized_users(self) -> List[Dict]:
        """Get all authorized users"""
        cursor = await self._connection.execute(
            """
            SELECT * FROM authorized_users
            WHERE is_banned = 0
            ORDER BY is_admin DESC, added_at ASC
        """
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_authorized_user(self, user_id: int) -> Optional[Dict]:
        """Get authorized user by ID"""
        cursor = await self._connection.execute(
            "SELECT * FROM authorized_users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def add_authorized_user(
        self,
        user_id: int,
        telegram_username: Optional[str] = None,
        is_admin: bool = False,
        added_by: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Add a new authorized user

        Args:
            user_id: Telegram user ID
            telegram_username: Telegram username
            is_admin: Is admin user
            added_by: User ID who added this user
            notes: Optional notes

        Returns:
            True if added, False if already exists
        """
        try:
            await self._connection.execute(
                """
                INSERT INTO authorized_users (
                    user_id, telegram_username, is_admin, added_by, notes
                ) VALUES (?, ?, ?, ?, ?)
            """,
                (user_id, telegram_username, is_admin, added_by, notes),
            )
            await self._connection.commit()
            self.logger.info(f"Added authorized user: {user_id} ({telegram_username})")
            return True
        except Exception as e:
            self.logger.error(f"Error adding authorized user {user_id}: {e}")
            return False

    async def update_authorized_user(
        self,
        user_id: int,
        telegram_username: Optional[str] = None,
        is_admin: Optional[bool] = None,
        is_banned: Optional[bool] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Update authorized user information

        Args:
            user_id: Telegram user ID
            telegram_username: New username
            is_admin: New admin status
            is_banned: New banned status
            notes: New notes

        Returns:
            True if updated, False otherwise
        """
        updates = []
        params = []

        if telegram_username is not None:
            updates.append("telegram_username = ?")
            params.append(telegram_username)

        if is_admin is not None:
            updates.append("is_admin = ?")
            params.append(is_admin)

        if is_banned is not None:
            updates.append("is_banned = ?")
            params.append(is_banned)

        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)

        if not updates:
            return False

        params.append(user_id)
        query = f"UPDATE authorized_users SET {', '.join(updates)} WHERE user_id = ?"

        try:
            await self._connection.execute(query, params)
            await self._connection.commit()
            self.logger.info(f"Updated authorized user: {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating authorized user {user_id}: {e}")
            return False

    async def remove_authorized_user(self, user_id: int) -> bool:
        """
        Remove authorized user (soft delete by banning)

        Args:
            user_id: Telegram user ID

        Returns:
            True if removed, False otherwise
        """
        try:
            await self._connection.execute(
                "UPDATE authorized_users SET is_banned = 1 WHERE user_id = ?",
                (user_id,),
            )
            await self._connection.commit()
            self.logger.info(f"Removed authorized user: {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error removing authorized user {user_id}: {e}")
            return False

    async def update_user_last_seen(self, user_id: int):
        """Update last seen timestamp for user"""
        await self._connection.execute(
            """
            UPDATE authorized_users
            SET last_seen = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """,
            (user_id,),
        )
        await self._connection.commit()

    async def sync_authorized_users_from_config(self, user_ids: List[int]):
        """
        Sync authorized users from config (AUTHORIZED_USERS in .env)
        This ensures users in .env are added to database

        Args:
            user_ids: List of user IDs from config
        """
        for user_id in user_ids:
            # Check if user already exists
            existing = await self.get_authorized_user(user_id)
            if not existing:
                # Add user from config
                await self.add_authorized_user(
                    user_id=user_id,
                    telegram_username=None,
                    is_admin=(user_id == user_ids[0]),  # First user is admin
                    added_by=None,
                    notes="Added from .env configuration",
                )
                self.logger.info(f"Synced user {user_id} from .env to database")


# Singleton instance
_db_manager: Optional[DatabaseManager] = None


async def get_database() -> DatabaseManager:
    """Get database manager instance (singleton)"""
    global _db_manager

    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.connect()

    return _db_manager
