"""
Disk space management and monitoring
"""

import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from core.config import get_config


@dataclass
class DiskUsage:
    """Disk usage information"""

    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float

    @property
    def available_for_download(self) -> float:
        """Available space for downloads (considering reserve)"""
        config = get_config()
        return max(0, self.free_gb - config.limits.min_free_space_gb)

    @property
    def status_emoji(self) -> str:
        """Space status emoji"""
        config = get_config()
        if self.free_gb > config.limits.warning_threshold_gb:
            return "🟢"
        elif self.free_gb > config.limits.min_free_space_gb:
            return "🟡"
        else:
            return "🔴"

    def can_download(self, size_gb: float) -> bool:
        """Check if there's space for a download"""
        config = get_config()
        return self.free_gb >= (size_gb + config.limits.min_free_space_gb)


class SpaceManager:
    """Disk space manager"""

    def __init__(self):
        self.config = get_config()
        self.logger = self.config.logger

    def get_disk_usage(self, path: Path) -> Optional[DiskUsage]:
        """
        Get disk usage information

        Args:
            path: Path to check

        Returns:
            DiskUsage or None if error
        """
        try:
            stat = shutil.disk_usage(str(path))
            return DiskUsage(
                total_gb=stat.total / (1024**3),
                used_gb=stat.used / (1024**3),
                free_gb=stat.free / (1024**3),
                percent_used=(stat.used / stat.total) * 100,
            )
        except Exception as e:
            self.logger.error(f"Error checking space for {path}: {e}")
            return None

    def get_free_space_gb(self, path: Path) -> float:
        """
        Get free space in GB

        Args:
            path: Path to check

        Returns:
            Free space in GB
        """
        usage = self.get_disk_usage(path)
        return usage.free_gb if usage else 0.0

    def check_space_available(self, path: Path, required_gb: float) -> Tuple[bool, float]:
        """
        Check if there's sufficient space

        Args:
            path: Download destination path
            required_gb: Required space in GB

        Returns:
            (available, free_space_gb)
        """
        usage = self.get_disk_usage(path)
        if not usage:
            return False, 0.0

        total_required = required_gb + self.config.limits.min_free_space_gb
        return usage.free_gb >= total_required, usage.free_gb

    def get_all_disk_usage(self) -> Dict[str, DiskUsage]:
        """
        Get disk usage for all paths

        Returns:
            Dictionary with usage for each path
        """
        usage = {}

        # Movies
        movies_usage = self.get_disk_usage(self.config.paths.movies)
        if movies_usage:
            usage["movies"] = movies_usage

        # TV Shows
        tv_usage = self.get_disk_usage(self.config.paths.tv)
        if tv_usage:
            usage["tv"] = tv_usage

        # If on the same disk, keep only one
        if "movies" in usage and "tv" in usage:
            if usage["movies"].total_gb == usage["tv"].total_gb:
                usage["media"] = usage["movies"]
                del usage["movies"]
                del usage["tv"]

        return usage

    def format_disk_status(self) -> str:
        """
        Format disk status for display

        Returns:
            Formatted string with disk status
        """
        usage = self.get_all_disk_usage()

        if not usage:
            return "❌ Unable to check disk space"

        status = "💾 **Disk Space Status**\n\n"

        for name, disk in usage.items():
            display_name = name.capitalize()
            status += f"{disk.status_emoji} **{display_name}:**\n"
            status += f"• Total: {disk.total_gb:.1f} GB\n"
            status += f"• Used: {disk.used_gb:.1f} GB ({disk.percent_used:.1f}%)\n"
            status += f"• Free: {disk.free_gb:.1f} GB\n"
            status += f"• Available for download: {disk.available_for_download:.1f} GB\n\n"

        status += f"⚙️ **Configured thresholds:**\n"
        status += f"• Minimum space: {self.config.limits.min_free_space_gb} GB\n"
        status += f"• Warning below: {self.config.limits.warning_threshold_gb} GB"

        return status

    def format_space_warning(self, path: Path, required_gb: float) -> str:
        """
        Format insufficient space warning

        Args:
            path: Destination path
            required_gb: Required space

        Returns:
            Formatted warning message
        """
        usage = self.get_disk_usage(path)
        if not usage:
            return "⚠️ Unable to check available space"

        total_required = required_gb + self.config.limits.min_free_space_gb
        missing = total_required - usage.free_gb

        return (
            f"⏸️ **Waiting for space**\n\n"
            f"❌ Insufficient space!\n"
            f"📊 Required: {required_gb:.1f} GB (+ {self.config.limits.min_free_space_gb} GB reserved)\n"
            f"💾 Available: {usage.free_gb:.1f} GB\n"
            f"🎯 Missing: {missing:.1f} GB\n\n"
            f"The download will start automatically when there's space."
        )

    def cleanup_empty_folders(self, folder_path: Path) -> bool:
        """
        Remove empty folders

        Args:
            folder_path: Folder path to check

        Returns:
            True if removed, False otherwise
        """
        try:
            if folder_path.exists() and not any(folder_path.iterdir()):
                folder_path.rmdir()
                self.logger.info(f"Empty folder removed: {folder_path}")
                return True
        except Exception as e:
            self.logger.warning(f"Unable to remove folder {folder_path}: {e}")

        return False

    def smart_cleanup(self, file_path: Path, is_movie: bool = True):
        """
        Smart cleanup after download cancellation

        Args:
            file_path: Cancelled file path
            is_movie: True if movie, False if TV series
        """
        try:
            # Remove partial file if exists
            if file_path.exists():
                file_path.unlink()
                self.logger.info(f"Partial file deleted: {file_path}")

            # Clean up empty folders
            if is_movie:
                # For movies, remove the movie folder if empty
                movie_folder = file_path.parent
                self.cleanup_empty_folders(movie_folder)
            else:
                # For TV series, remove season and series if empty
                season_folder = file_path.parent
                series_folder = season_folder.parent

                if self.cleanup_empty_folders(season_folder):
                    self.cleanup_empty_folders(series_folder)

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
