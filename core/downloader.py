"""
Download and queue management
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, Optional, Set, List
from telethon import TelegramClient
from core.config import get_config
from core.space_manager import SpaceManager
from core.tmdb_client import TMDBClient
from core.subtitle_manager import SubtitleManager
from core.extractor import ArchiveExtractor
from core.user_config import UserConfig
from models.download import DownloadInfo, DownloadStatus, QueueItem
from utils.helpers import RetryHelpers, FileHelpers
from utils.naming import FileNameParser


# Database import - will be set by main.py
_database_manager = None


def set_database_manager(db_manager):
    """Set database manager instance"""
    global _database_manager
    _database_manager = db_manager


async def get_user_config_for_download(user_id: int) -> UserConfig:
    """Get user configuration for download operations"""
    if _database_manager:
        return UserConfig(user_id, _database_manager)
    return None


class DownloadManager:
    """Download and queue manager"""

    def __init__(
        self,
        client: TelegramClient,
        space_manager: SpaceManager,
        tmdb_client: Optional[TMDBClient] = None,
    ):
        self.client = client
        self.space_manager = space_manager
        self.tmdb_client = tmdb_client
        self.subtitle_manager = SubtitleManager()
        self.extractor = ArchiveExtractor()
        self.config = get_config()
        self.logger = self.config.logger

        # Data structures for download management
        self.active_downloads: Dict[int, DownloadInfo] = {}
        self.download_tasks: Dict[int, asyncio.Task] = {}
        self.download_queue = asyncio.Queue()
        self.space_waiting_queue: list[QueueItem] = []
        self.cancelled_downloads: Set[int] = set()

        # Workers
        self.workers = []
        self.space_monitor_task = None

    async def start_workers(self):
        """Start workers to process downloads"""
        # Create download workers
        for i in range(self.config.limits.max_concurrent_downloads):
            worker = asyncio.create_task(self._download_worker())
            self.workers.append(worker)

        # Start space monitor
        self.space_monitor_task = asyncio.create_task(self._space_monitor_worker())

        self.logger.info(f"Started {len(self.workers)} download workers")

    async def stop(self):
        """Stop all workers"""
        # Cancel all active downloads
        for msg_id in list(self.active_downloads.keys()):
            self.cancelled_downloads.add(msg_id)

        # Cancel tasks
        for task in self.download_tasks.values():
            task.cancel()

        # Stop workers
        for worker in self.workers:
            worker.cancel()

        if self.space_monitor_task:
            self.space_monitor_task.cancel()

        # Wait for shutdown
        await asyncio.gather(*self.workers, return_exceptions=True)

        self.logger.info("Download manager stopped")

    def add_download(self, download_info: DownloadInfo) -> bool:
        """
        Add a download

        Args:
            download_info: Download info

        Returns:
            True if added, False if already present
        """
        if download_info.message_id in self.active_downloads:
            return False

        self.active_downloads[download_info.message_id] = download_info
        return True

    async def queue_download(self, download_info: DownloadInfo) -> int:
        """
        Queue a download

        Args:
            download_info: Download info

        Returns:
            Queue position
        """
        queue_item = QueueItem(download_info=download_info)
        await self.download_queue.put(queue_item)

        download_info.status = DownloadStatus.QUEUED
        return self.download_queue.qsize()

    def queue_for_space(self, download_info: DownloadInfo) -> int:
        """
        Queue for space

        Args:
            download_info: Download info

        Returns:
            Space queue position
        """
        queue_item = QueueItem(download_info=download_info)
        self.space_waiting_queue.append(queue_item)

        download_info.status = DownloadStatus.WAITING_SPACE
        return len(self.space_waiting_queue)

    def _cleanup_download_folders(self, download_info: DownloadInfo):
        """
        Cleanup empty folders created for a download

        Args:
            download_info: Download info with created_folders list
        """
        if not hasattr(download_info, "created_folders") or not download_info.created_folders:
            return

        # Iterate in reverse order (deepest folders first)
        for folder_path in reversed(download_info.created_folders):
            try:
                # Only remove if folder exists and is empty
                if folder_path.exists() and folder_path.is_dir():
                    # Check if folder is empty
                    if not any(folder_path.iterdir()):
                        folder_path.rmdir()
                        self.logger.info(f"Removed empty folder: {folder_path}")
                    else:
                        self.logger.debug(f"Folder not empty, keeping: {folder_path}")
            except Exception as e:
                self.logger.warning(f"Could not remove folder {folder_path}: {e}")

    def cancel_download(self, message_id: int) -> bool:
        """
        Cancel a download and cleanup created folders

        Args:
            message_id: Message ID

        Returns:
            True if cancelled
        """
        self.cancelled_downloads.add(message_id)

        # Get download info for cleanup
        download_info = self.active_downloads.get(message_id)

        if message_id in self.download_tasks:
            self.download_tasks[message_id].cancel()

            # Cleanup folders if download was cancelled
            if download_info:
                self._cleanup_download_folders(download_info)

            return True

        if message_id in self.active_downloads:
            self.active_downloads[message_id].status = DownloadStatus.CANCELLED

            # Cleanup folders
            self._cleanup_download_folders(download_info)

            return True

        return False

    def cancel_all_downloads(self) -> int:
        """
        Cancel all downloads

        Returns:
            Number of cancelled downloads
        """
        cancelled = 0

        # Cancel active ones
        for msg_id in list(self.active_downloads.keys()):
            if self.cancel_download(msg_id):
                cancelled += 1

        # Empty queues
        while not self.download_queue.empty():
            try:
                queue_item = self.download_queue.get_nowait()
                self.cancelled_downloads.add(queue_item.download_info.message_id)
                cancelled += 1
            except:
                break

        # Empty space queue
        for item in self.space_waiting_queue:
            self.cancelled_downloads.add(item.download_info.message_id)
            cancelled += 1
        self.space_waiting_queue.clear()

        return cancelled

    def get_active_downloads(self) -> list[DownloadInfo]:
        """Get active downloads"""
        return [
            info for msg_id, info in self.active_downloads.items() if msg_id in self.download_tasks
        ]

    def get_queued_count(self) -> int:
        """Get number of queued files"""
        return self.download_queue.qsize()

    def get_space_waiting_count(self) -> int:
        """Get number of files waiting for space"""
        return len(self.space_waiting_queue)

    def get_download_info(self, message_id: int) -> Optional[DownloadInfo]:
        """Get download info"""
        return self.active_downloads.get(message_id)

    def is_downloading(self, message_id: int) -> bool:
        """Check if downloading"""
        return message_id in self.download_tasks

    async def _download_worker(self):
        """Worker that processes download queue"""
        while True:
            try:
                # Wait for free slot
                while len(self.download_tasks) >= self.config.limits.max_concurrent_downloads:
                    await asyncio.sleep(1)

                # Get from queue
                queue_item = await self.download_queue.get()
                download_info = queue_item.download_info
                msg_id = download_info.message_id

                # Check if cancelled
                if msg_id in self.cancelled_downloads:
                    self.logger.info(f"Download cancelled from queue: {download_info.filename}")
                    self.cancelled_downloads.discard(msg_id)
                    continue

                # Check space
                size_gb = download_info.size_gb
                space_ok, free_gb = self.space_manager.check_space_available(
                    download_info.dest_path, size_gb
                )

                if not space_ok:
                    # Put back in space queue
                    self.queue_for_space(download_info)
                    self.logger.warning(
                        f"Insufficient space for {download_info.filename}, " f"queued for space"
                    )

                    # Notify user if possible
                    if download_info.event:
                        try:
                            await download_info.event.edit(
                                self.space_manager.format_space_warning(
                                    download_info.dest_path, size_gb
                                )
                            )
                        except:
                            pass
                    continue

                # Start download
                task = asyncio.create_task(self._download_file(download_info))
                self.download_tasks[msg_id] = task

                # Wait for completion
                await task

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Errore in download worker: {e}", exc_info=True)

    async def _space_monitor_worker(self):
        """Worker that monitors space and processes waiting queue"""
        while True:
            try:
                await asyncio.sleep(self.config.limits.space_check_interval)

                if not self.space_waiting_queue:
                    continue

                processed = []

                for queue_item in self.space_waiting_queue:
                    download_info = queue_item.download_info
                    msg_id = download_info.message_id

                    # Check if cancelled
                    if msg_id in self.cancelled_downloads:
                        processed.append(queue_item)
                        continue

                    # Check space
                    size_gb = download_info.size_gb
                    space_ok, free_gb = self.space_manager.check_space_available(
                        download_info.dest_path, size_gb
                    )

                    # If there's space and free slot, move to download queue
                    if (
                        space_ok
                        and len(self.download_tasks) < self.config.limits.max_concurrent_downloads
                    ):
                        await self.download_queue.put(queue_item)
                        processed.append(queue_item)

                        self.logger.info(
                            f"Space available for {download_info.filename}, "
                            f"moved to download queue"
                        )

                        # Notify user
                        if download_info.event:
                            try:
                                await download_info.event.edit(
                                    f"{download_info.emoji} **{download_info.media_type}**\n\n"
                                    f"✅ **Space available!**\n"
                                    f"📥 Moved to download queue...\n"
                                    f"💾 Free space: {free_gb:.1f} GB"
                                )
                            except:
                                pass

                # Remove processed
                for item in processed:
                    self.space_waiting_queue.remove(item)

            except Exception as e:
                self.logger.error(f"Errore in space monitor: {e}", exc_info=True)

    async def _download_file(self, download_info: DownloadInfo):
        """Execute file download with retry and safe handling"""
        msg_id = download_info.message_id

        try:
            # Check cancellation
            if msg_id in self.cancelled_downloads:
                self.logger.info(f"Download already cancelled: {download_info.filename}")
                return

            # Update status
            download_info.status = DownloadStatus.DOWNLOADING
            download_info.start_time = time.time()

            # Add to database
            if _database_manager:
                try:
                    await _database_manager.add_download(download_info)
                    await _database_manager.update_download_status(
                        download_info.message_id, DownloadStatus.DOWNLOADING
                    )
                except Exception as e:
                    self.logger.error(f"Error adding download to database: {e}")

            # Prepare paths
            filepath = self._prepare_file_path(download_info)
            download_info.final_path = filepath

            # Check if file already exists (avoid duplicates)
            if filepath.exists():
                # Use async hash calculation to avoid blocking event loop
                existing_hash = await FileHelpers.get_file_hash_async(filepath)
                self.logger.warning(f"File already exists: {filepath} (hash: {existing_hash})")

                # Notifica utente
                if download_info.event:
                    await download_info.event.edit(
                        f"⚠️ **File already exists**\n\n"
                        f"The file `{filepath.name}` already exists in the destination.\n"
                        f"Download cancelled to avoid duplicates."
                    )
                return

            self.logger.info(f"Download started: {download_info.filename} -> {filepath}")

            # Info for display
            path_info = self._get_path_info(download_info, filepath)

            # Notify start
            if download_info.event:
                await download_info.event.edit(
                    f"{download_info.emoji} **{download_info.media_type}**\n\n"
                    f"📥 **Downloading...**\n"
                    f"`{filepath.name}`\n\n"
                    f"{path_info}"
                    f"Initializing..."
                )

            # Progress callback
            last_update = time.time()

            async def progress_callback(current, total):
                nonlocal last_update

                # Check cancellation
                if msg_id in self.cancelled_downloads:
                    raise asyncio.CancelledError("Download cancelled by user")

                now = time.time()
                if now - last_update < 2:  # Update every 2 seconds
                    return

                last_update = now
                await self._update_progress(download_info, current, total, path_info)

            # Download to temp first, then move (safer)
            temp_path = self.config.paths.temp / f"{msg_id}_{filepath.name}"
            temp_path.parent.mkdir(parents=True, exist_ok=True)

            # Download with automatic retry
            @RetryHelpers.async_retry(max_attempts=3, delay=2, exceptions=(Exception,))
            async def download_with_retry():
                return await self.client.download_media(
                    download_info.message,
                    temp_path,
                    progress_callback=progress_callback,
                )

            await download_with_retry()

            # Check final cancellation
            if msg_id in self.cancelled_downloads:
                if temp_path.exists():
                    temp_path.unlink()
                raise asyncio.CancelledError("Download cancelled")

            # Move file to final position (atomic)
            if not FileHelpers.safe_move(temp_path, filepath):
                raise Exception("Unable to move file to final destination")

            # Check if file is an archive and extract if needed
            if self.config.extraction.enabled and self.extractor.is_archive(filepath):
                self.logger.info(f"Archive detected: {filepath.name}")

                # Notify user about extraction
                if download_info.event:
                    try:
                        await download_info.event.edit(
                            f"{download_info.emoji} **{download_info.media_type}**\n\n"
                            f"📦 **Extracting archive...**\n"
                            f"`{filepath.name}`\n\n"
                            f"{path_info}"
                            f"Please wait..."
                        )
                    except:
                        pass

                # Extract archive
                success, video_files = await self.extractor.extract_archive(
                    archive_path=filepath,
                    extract_to=filepath.parent,
                    delete_archive=self.config.extraction.delete_after_extract,
                )

                if success and video_files:
                    # Use the first extracted video file as the main file
                    original_archive_path = filepath
                    filepath = video_files[0]

                    # Check if original archive was multi-part and rename accordingly
                    if self.extractor.is_multipart_archive(original_archive_path):
                        part_num = self.extractor.get_multipart_number(original_archive_path)
                        if part_num is not None:
                            # Add part number to filename
                            stem = filepath.stem
                            suffix = filepath.suffix
                            new_name = f"{stem} - Part {part_num}{suffix}"
                            new_filepath = filepath.parent / new_name

                            # Rename the extracted file
                            try:
                                filepath.rename(new_filepath)
                                filepath = new_filepath
                                self.logger.info(f"Renamed to include part number: {filepath.name}")
                            except Exception as e:
                                self.logger.warning(
                                    f"Could not rename file to add part number: {e}"
                                )

                    download_info.final_path = filepath
                    self.logger.info(f"Archive extracted successfully: {filepath.name}")

                    # If multiple video files were extracted, log them
                    if len(video_files) > 1:
                        self.logger.info(
                            f"Multiple video files extracted ({len(video_files)}): "
                            f"{', '.join([f.name for f in video_files])}"
                        )
                elif not success:
                    self.logger.warning(
                        f"Archive extraction failed or no video files found: {filepath.name}"
                    )
                    # Continue with the archive file itself if extraction failed

            # Completed
            download_info.status = DownloadStatus.COMPLETED
            download_info.end_time = time.time()

            # Calculate hash for future deduplication
            file_hash = await FileHelpers.get_file_hash_async(filepath, timeout=30)
            self.logger.info(f"File completed: {filepath} (hash: {file_hash})")

            # Save to database
            if _database_manager:
                try:
                    duration = (
                        int(download_info.end_time - download_info.start_time)
                        if download_info.start_time
                        else 0
                    )
                    await _database_manager.complete_download(
                        download_info.message_id,
                        str(filepath),
                        duration,
                        download_info.speed_mbps,
                    )
                    await _database_manager.update_user_stats(download_info.user_id, download_info)
                except Exception as e:
                    self.logger.error(f"Error saving to database: {e}")

            # Download subtitles if configured
            await self._handle_subtitles_download(download_info, filepath)

            # Notify completion
            await self._notify_completion(download_info, filepath)

        except asyncio.CancelledError:
            self.logger.info(f"Download cancelled: {download_info.filename}")
            download_info.status = DownloadStatus.CANCELLED

            # Save cancellation to database
            if _database_manager:
                try:
                    await _database_manager.update_download_status(
                        download_info.message_id, DownloadStatus.CANCELLED
                    )
                    await _database_manager.increment_cancelled_downloads(download_info.user_id)
                except Exception as e:
                    self.logger.error(f"Error saving cancellation to database: {e}")

            # Cleanup temporary file
            if "temp_path" in locals() and temp_path.exists():
                temp_path.unlink()

            # Cleanup final file and folders
            if download_info.final_path and download_info.final_path.exists():
                self.space_manager.smart_cleanup(download_info.final_path, download_info.is_movie)

            # Notify cancellation
            if download_info.event:
                try:
                    await download_info.event.edit(
                        f"❌ **Download cancelled**\n\n" f"File: `{download_info.filename}`"
                    )
                except:
                    pass

        except Exception as e:
            self.logger.error(f"Download error: {e}", exc_info=True)
            download_info.status = DownloadStatus.FAILED
            download_info.error_message = str(e)

            # Save failure to database
            if _database_manager:
                try:
                    await _database_manager.update_download_status(
                        download_info.message_id,
                        DownloadStatus.FAILED,
                        error_message=str(e),
                    )
                    await _database_manager.increment_failed_downloads(download_info.user_id)
                except Exception as db_err:
                    self.logger.error(f"Error saving failure to database: {db_err}")

            # Cleanup temporary file if exists
            if "temp_path" in locals() and temp_path.exists():
                temp_path.unlink()

            # Notify error (respecting user preferences)
            user_config = await get_user_config_for_download(download_info.user_id)
            notify_failed = True  # Default
            compact_messages = False

            if user_config:
                notify_failed = await user_config.get_notify_download_failed()
                compact_messages = await user_config.get_compact_messages()

            if notify_failed and download_info.event:
                try:
                    if compact_messages:
                        await download_info.event.edit(f"❌ **Failed**\n`{download_info.filename}`")
                    else:
                        await download_info.event.edit(
                            f"❌ **Download error**\n\n"
                            f"File: `{download_info.filename}`\n"
                            f"Error: `{str(e)}`"
                        )
                except:
                    pass

        finally:
            # Remove from structures
            if msg_id in self.download_tasks:
                del self.download_tasks[msg_id]
            if msg_id in self.active_downloads:
                del self.active_downloads[msg_id]
            self.cancelled_downloads.discard(msg_id)

    def _prepare_file_path(self, download_info: DownloadInfo) -> Path:
        """Prepare final file path"""
        # Determine filename and folder
        if download_info.selected_tmdb and download_info.tmdb_confidence >= 60:
            # Use TMDB naming
            folder_name, filename = FileNameParser.create_tmdb_filename(
                download_info.selected_tmdb,
                download_info.original_filename,
                download_info.series_info,
            )
        else:
            # Use base naming
            folder_name = download_info.movie_folder or download_info.display_name
            filename = download_info.filename

        # Create folder structure
        if download_info.is_movie:
            # Check for existing similar folder
            similar_folder = FileNameParser.find_similar_folder(
                folder_name, download_info.dest_path, threshold=0.75
            )

            if similar_folder:
                self.logger.info(f"Found similar folder: '{similar_folder}' for '{folder_name}'")
                folder_name = similar_folder

            folder_path = download_info.dest_path / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)

            if folder_path not in download_info.created_folders:
                download_info.created_folders.append(folder_path)

            filepath = folder_path / filename
        else:
            # Serie TV - check for existing similar series folder
            similar_series = FileNameParser.find_similar_folder(
                folder_name, download_info.dest_path, threshold=0.75
            )

            if similar_series:
                self.logger.info(
                    f"Found similar series folder: '{similar_series}' for '{folder_name}'"
                )
                folder_name = similar_series

            series_folder = download_info.dest_path / folder_name
            season_folder = series_folder / f"Season {download_info.selected_season:02d}"
            season_folder.mkdir(parents=True, exist_ok=True)

            if not series_folder.exists() and series_folder not in download_info.created_folders:
                download_info.created_folders.append(series_folder)
            if not season_folder.exists() and season_folder not in download_info.created_folders:
                download_info.created_folders.append(season_folder)

            filepath = season_folder / filename

        return filepath

    def _get_path_info(self, download_info: DownloadInfo, filepath: Path) -> str:
        """Generate path info for display"""
        if download_info.is_movie:
            return f"📁 Folder: `{filepath.parent.name}/`\n"
        else:
            season_folder = filepath.parent
            series_folder = season_folder.parent
            return f"📁 Series: `{series_folder.name}/`\n" f"📅 Season: `{season_folder.name}/`\n"

    async def _update_progress(
        self, download_info: DownloadInfo, current: int, total: int, path_info: str
    ):
        """Update download progress"""
        progress = (current / total) * 100
        download_info.progress = progress

        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)

        # Calculate speed and ETA
        elapsed = time.time() - download_info.start_time
        speed = (current / (1024 * 1024)) / elapsed if elapsed > 0 else 0
        download_info.speed_mbps = speed

        if speed > 0:
            eta = (total - current) / (speed * 1024 * 1024)
            download_info.eta_seconds = int(eta)

            if eta < 60:
                eta_str = f"{int(eta)}s"
            else:
                eta_str = f"{int(eta/60)}m {int(eta%60)}s"
        else:
            eta_str = "calculating..."

        # Progress bar
        filled = int(progress / 5)
        bar = "█" * filled + "░" * (20 - filled)

        # Space status
        free_gb = self.space_manager.get_free_space_gb(download_info.dest_path)
        space_emoji = (
            "🟢"
            if free_gb > self.config.limits.warning_threshold_gb
            else "🟡" if free_gb > self.config.limits.min_free_space_gb else "🔴"
        )

        # Update message
        if download_info.event:
            try:
                await download_info.event.edit(
                    f"{download_info.emoji} **{download_info.media_type}**\n\n"
                    f"📥 **Downloading...**\n"
                    f"`{download_info.final_path.name}`\n\n"
                    f"{path_info}"
                    f"`[{bar}]`\n"
                    f"**{progress:.1f}%** - {current_mb:.1f}/{total_mb:.1f} MB\n"
                    f"⚡ Speed: **{speed:.1f} MB/s**\n"
                    f"⏱ Time remaining: **{eta_str}**\n"
                    f"{space_emoji} Free space: **{free_gb:.1f} GB**"
                )
            except:
                pass

    async def _notify_completion(self, download_info: DownloadInfo, filepath: Path):
        """Notify download completion"""
        # Check user notification preferences
        user_config = await get_user_config_for_download(download_info.user_id)

        if user_config:
            notify_complete = await user_config.get_notify_download_complete()
            compact_messages = await user_config.get_compact_messages()
        else:
            notify_complete = True  # Default to enabled
            compact_messages = False

        if not notify_complete:
            self.logger.info(f"Download completed (notification disabled): {filepath}")
            return

        final_free_gb = self.space_manager.get_free_space_gb(download_info.dest_path)

        # Relative path for display
        if download_info.is_movie:
            display_path = f"{filepath.parent.name}/{filepath.name}"
        else:
            season_folder = filepath.parent
            series_folder = season_folder.parent
            display_path = f"{series_folder.name}/{season_folder.name}/{filepath.name}"

        if download_info.event:
            try:
                if compact_messages:
                    # Compact notification
                    await download_info.event.edit(
                        f"✅ **Completed**\n"
                        f"`{filepath.name}`\n"
                        f"💾 {final_free_gb:.1f} GB free"
                    )
                else:
                    # Detailed notification
                    await download_info.event.edit(
                        f"✅ **Download completed!**\n\n"
                        f"{download_info.emoji} Type: **{download_info.media_type}**\n"
                        f"📁 File: `{filepath.name}`\n"
                        f"📂 Path: `{display_path}`\n"
                        f"💾 Remaining space: **{final_free_gb:.1f} GB**\n\n"
                        f"🎬 Available on your media server!"
                    )
            except:
                pass

        self.logger.info(f"Download completed: {filepath}")

    async def _handle_subtitles_download(self, download_info: DownloadInfo, filepath: Path):
        """Handle subtitle download after video completion"""
        # Get user-specific configuration
        user_config = await get_user_config_for_download(download_info.user_id)

        if user_config:
            subtitle_enabled = await user_config.get_subtitle_enabled()
            auto_download = await user_config.get_subtitle_auto_download()
            languages = await user_config.get_subtitle_languages()
        else:
            # Fallback to global config
            subtitle_enabled = self.config.subtitles.enabled
            auto_download = self.config.subtitles.auto_download
            languages = self.config.subtitles.languages

        if not subtitle_enabled:
            return

        if not auto_download:
            self.logger.debug("Automatic subtitle download disabled")
            return

        try:
            self.logger.info(f"🎬 Starting subtitle download for: {filepath.name}")

            # Extract information for subtitle search
            season = None
            episode = None
            imdb_id = getattr(download_info, "imdb_id", None)

            # If it's a TV series, extract season/episode
            if (
                not download_info.is_movie
                and hasattr(download_info, "season")
                and hasattr(download_info, "episode")
            ):
                season = download_info.season
                episode = download_info.episode

            # Download subtitles
            subtitle_files = await self.subtitle_manager.download_subtitles_for_video(
                video_path=filepath,
                imdb_id=imdb_id,
                season=season,
                episode=episode,
                languages=languages,  # Use user-specific languages
                force=False,
            )

            if subtitle_files:
                self.logger.info(
                    f"✅ Downloaded {len(subtitle_files)} subtitles for {filepath.name}"
                )

                # Update notification to include subtitle info
                if download_info.event:
                    try:
                        langs = ", ".join(
                            [f.stem.split(".")[-2] for f in subtitle_files if "." in f.stem]
                        )
                        current_text = download_info.event.text or ""
                        if "🎬 Available on your media server!" in current_text:
                            updated_text = current_text.replace(
                                "🎬 Available on your media server!",
                                f"🎬 Available on your media server!\n📝 Subtitles: {langs}",
                            )
                            await download_info.event.edit(updated_text)
                    except Exception as e:
                        self.logger.debug(f"Error updating subtitle notification: {e}")
            else:
                self.logger.info(f"❌ No subtitles found for {filepath.name}")

        except Exception as e:
            self.logger.error(f"❌ Subtitle download error for {filepath.name}: {e}")

    async def download_subtitles_manually(
        self,
        video_path: Path,
        languages: Optional[List[str]] = None,
        force: bool = True,
    ) -> List[Path]:
        """
        Manual subtitle download for an existing video

        Args:
            video_path: Video file path
            languages: Languages to download (default: from config)
            force: Force download even if already existing

        Returns:
            List of downloaded subtitle files
        """
        if not self.config.subtitles.enabled:
            self.logger.warning("Subtitle system disabled")
            return []

        return await self.subtitle_manager.download_subtitles_for_video(
            video_path=video_path,
            languages=languages or self.config.subtitles.languages,
            force=force,
        )
