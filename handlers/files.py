"""
Handlers for files received via Telegram
"""
import os
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.tl.types import DocumentAttributeFilename
from core.auth import AuthManager
from core.downloader import DownloadManager, get_user_config_for_download
from core.tmdb_client import TMDBClient
from core.space_manager import SpaceManager
from core.database import DatabaseManager
from models.download import DownloadInfo, MediaType
from utils.naming import FileNameParser
from utils.helpers import ValidationHelpers, FileHelpers


class FileHandlers:
    """Received file management"""
    
    def __init__(
        self,
        client: TelegramClient,
        auth_manager: AuthManager,
        download_manager: DownloadManager,
        tmdb_client: TMDBClient,
        space_manager: SpaceManager,
        database_manager: DatabaseManager = None
    ):
        self.client = client
        self.auth = auth_manager
        self.downloads = download_manager
        self.tmdb = tmdb_client
        self.space = space_manager
        self.database = database_manager
        self.config = download_manager.config
        self.logger = self.config.logger
    
    def register(self):
        """Register file handlers"""
        self.client.on(events.NewMessage(func=lambda e: e.file))(self.file_handler)
        self.client.on(events.NewMessage(func=lambda e: e.text and not e.text.startswith('/')))(self.text_handler)
        self.logger.info("File handlers registered")
    
    async def file_handler(self, event: events.NewMessage.Event):
        """Main handler for received files"""
        if not await self.auth.check_authorized(event):
            return
        
        self.logger.info(
            f"File received from user {event.sender_id}, "
            f"size: {event.file.size / (1024*1024):.1f} MB"
        )
        
        # Validate file size
        size_valid, error_msg = ValidationHelpers.validate_file_size(
            event.file.size,
            min_size=1024 * 100,  # 100 KB minimo
            max_size=int(self.config.limits.max_file_size_gb * (1024**3))
        )
        
        if not size_valid:
            await event.reply(f"⚠️ {error_msg}")
            return
        
        # Extract filename
        filename = self._extract_filename(event)
        
        # Verify it's a video file
        if not FileHelpers.is_video_file(filename):
            await event.reply(
                f"⚠️ **Unsupported file**\n\n"
                f"The file `{filename}` doesn't appear to be a video.\n"
                f"Supported formats: {', '.join(FileHelpers.get_video_extensions())}"
            )
            return
        
        # Create DownloadInfo
        download_info = DownloadInfo(
            message_id=event.message.id,
            user_id=event.sender_id,
            filename=filename,
            original_filename=filename,
            size=event.file.size,
            message=event.message
        )
        
        # Extract info from name
        movie_name, year = FileNameParser.extract_movie_info(filename)
        series_info = FileNameParser.extract_series_info(filename)

        # Set movie_folder only if NOT a recognized TV series
        if series_info.season is None:
            download_info.movie_folder = FileNameParser.create_folder_name(movie_name, year)

        download_info.series_info = series_info

        # Check for duplicates
        if self.database:
            duplicate = await self.database.check_duplicate_file(
                filename,
                event.sender_id
            )

            if duplicate:
                await self._show_duplicate_warning(event, download_info, duplicate)
                return

        # Add to manager
        if not self.downloads.add_download(download_info):
            await event.reply("⚠️ Download already processing for this file")
            return

        # Process with TMDB if available
        if self.tmdb:
            await self._process_with_tmdb(event, download_info)
        else:
            await self._process_without_tmdb(event, download_info)
    
    def _extract_filename(self, event) -> str:
        """Extract filename from message"""
        filename = "unknown"
        
        # Try from file
        if hasattr(event.file, 'name') and event.file.name:
            filename = event.file.name
        # Try from document attributes
        elif event.document:
            for attr in event.document.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    filename = attr.file_name
                    break
        
        # If still unknown, generate name
        if not filename or filename == "unknown":
            filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        
        # Check if there's text in the message (for forwarded files)
        message_text = event.message.message if event.message.message else ""
        if message_text and (filename.startswith("video_") or filename == "unknown"):
            detected_name = message_text.strip()
            if not any(detected_name.endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov']):
                ext = os.path.splitext(filename)[1] or '.mp4'
                detected_name += ext
            self.logger.info(f"Name detected from text: {detected_name}")
            return detected_name
        
        return filename
    
    async def _process_with_tmdb(self, event, download_info: DownloadInfo):
        """Process file with TMDB search"""
        initial_msg = await event.reply("🔍 **Searching TMDB database...**")
        download_info.progress_msg = initial_msg

        # Get user auto-confirm threshold
        user_config = await get_user_config_for_download(download_info.user_id)
        auto_confirm_threshold = 70  # Default

        if user_config:
            auto_confirm_threshold = await user_config.get_auto_confirm_threshold()

        # Determine search type
        if download_info.series_info.season:
            search_query = download_info.series_info.series_name
            media_hint = 'tv'
        else:
            search_query = download_info.movie_folder
            media_hint = None

        # Search on TMDB
        tmdb_result, confidence = await self.tmdb.search_with_confidence(
            search_query,
            media_hint
        )

        if tmdb_result:
            download_info.tmdb_results = [tmdb_result]
            download_info.selected_tmdb = tmdb_result
            download_info.tmdb_confidence = confidence

        # Prepare space warning
        space_warning = self._get_space_warning(download_info)

        # Check if auto-confirm is enabled and confidence is high enough
        if tmdb_result and confidence >= auto_confirm_threshold:
            # Auto-confirm download
            download_info.event = initial_msg
            await self._auto_confirm_download(
                initial_msg,
                download_info,
                tmdb_result,
                confidence,
                space_warning
            )
        # Mostra risultati per conferma manuale
        elif tmdb_result and confidence >= 60:
            await self._show_high_confidence_match(
                initial_msg,
                download_info,
                tmdb_result,
                confidence,
                space_warning
            )
        elif tmdb_result and confidence >= 40:
            await self._show_medium_confidence_match(
                initial_msg,
                download_info,
                space_warning
            )
        else:
            await self._show_manual_selection(
                initial_msg,
                download_info,
                space_warning
            )
    
    async def _auto_confirm_download(
        self,
        msg,
        download_info,
        tmdb_result,
        confidence,
        space_warning
    ):
        """Auto-confirm download when confidence >= threshold"""
        # Update message to show auto-confirmation
        text, poster_url = self.tmdb.format_result(
            tmdb_result,
            download_info.series_info
        )

        info_text = f"📁 **File:** `{download_info.filename}`\n"
        info_text += f"📏 **Size:** {download_info.size_mb:.1f} MB ({download_info.size_gb:.1f} GB)\n\n"
        info_text += f"⚡ **Auto-confirmed** (confidence {confidence}%)\n\n"
        info_text += text

        if poster_url:
            info_text = f"[​]({poster_url})" + info_text

        await msg.edit(info_text + space_warning, link_preview=True)

        # Auto-detect type from TMDB and proceed with download
        if download_info.selected_tmdb.is_tv_show:
            # TV Show - need to determine season
            download_info.media_type = MediaType.TV_SHOW
            download_info.is_movie = False
            download_info.dest_path = self.config.paths.tv
            download_info.emoji = "📺"

            # If season is detected from filename, proceed
            if download_info.series_info and download_info.series_info.season:
                download_info.selected_season = download_info.series_info.season

                # Check space and proceed
                size_gb = download_info.size_gb
                space_ok, free_gb = self.space.check_space_available(
                    download_info.dest_path,
                    size_gb
                )

                if not space_ok:
                    position = self.downloads.queue_for_space(download_info)
                    await msg.edit(
                        f"{download_info.emoji} **{download_info.media_type}**\n"
                        f"📅 Season {download_info.selected_season}\n\n"
                        + self.space.format_space_warning(download_info.dest_path, size_gb)
                        + f"\nPosition in space queue: #{position}"
                    )
                    return

                # Queue download
                position = await self.downloads.queue_download(download_info)

                await msg.edit(
                    f"{download_info.emoji} **{download_info.media_type}**\n"
                    f"📅 Season {download_info.selected_season}\n\n"
                    f"📥 **Preparing download...**\n"
                    f"✅ Available space: {free_gb:.1f} GB\n"
                    f"📊 Position in queue: #{position}"
                )
        else:
            # Movie - proceed directly
            download_info.media_type = MediaType.MOVIE
            download_info.is_movie = True
            download_info.dest_path = self.config.paths.movies
            download_info.emoji = "🎬"

            # Check space
            size_gb = download_info.size_gb
            space_ok, free_gb = self.space.check_space_available(
                download_info.dest_path,
                size_gb
            )

            if not space_ok:
                position = self.downloads.queue_for_space(download_info)

                await msg.edit(
                    f"🎬 **Movie** selected\n\n"
                    + self.space.format_space_warning(download_info.dest_path, size_gb)
                    + f"\nPosition in space queue: #{position}"
                )
                return

            # Queue download
            position = await self.downloads.queue_download(download_info)

            active_downloads = len(self.downloads.get_active_downloads())

            await msg.edit(
                f"🎬 **Movie** selected\n\n"
                f"📥 **Preparing download...**\n"
                f"✅ Available space: {free_gb:.1f} GB\n"
                f"📊 Position in queue: #{position}"
            )

    async def _process_without_tmdb(self, event, download_info: DownloadInfo):
        """Process file without TMDB"""
        # Basic info
        info_text = self._format_file_info(download_info)

        # Space warning
        space_warning = self._get_space_warning(download_info)

        # If season/episode was detected, it's definitely a TV series
        if download_info.series_info.season:
            buttons = [
                [
                    Button.inline("✅ Confirm TV Series", f"tv_{download_info.message_id}"),
                    Button.inline("🎬 It's a Movie", f"movie_{download_info.message_id}")
                ],
                [Button.inline("❌ Cancel", f"cancel_{download_info.message_id}")]
            ]
            question = "**Confirm it's a TV series?**"
        else:
            # No TV series pattern detected, ask for type
            buttons = [
                [
                    Button.inline("🎬 Movie", f"movie_{download_info.message_id}"),
                    Button.inline("📺 TV Series", f"tv_{download_info.message_id}")
                ],
                [Button.inline("❌ Cancel", f"cancel_{download_info.message_id}")]
            ]
            question = "**Is it a movie or TV series?**"

        msg = await event.reply(
            f"📁 **File received:**\n"
            f"`{download_info.filename}`\n"
            f"📏 Size: **{download_info.size_mb:.1f} MB** ({download_info.size_gb:.1f} GB)"
            f"{info_text}\n"
            f"{space_warning}\n\n"
            f"{question}",
            buttons=buttons
        )

        download_info.progress_msg = msg
    
    async def _show_high_confidence_match(
        self,
        msg,
        download_info,
        tmdb_result,
        confidence,
        space_warning
    ):
        """Show high confidence TMDB match"""
        text, poster_url = self.tmdb.format_result(
            tmdb_result,
            download_info.series_info
        )
        
        info_text = f"📁 **File:** `{download_info.filename}`\n"
        info_text += f"📏 **Size:** {download_info.size_mb:.1f} MB ({download_info.size_gb:.1f} GB)\n\n"
        info_text += f"✅ **TMDB Match** (confidence {confidence}%)\n\n"
        info_text += text

        # Add poster if available
        if poster_url:
            info_text = f"[​]({poster_url})" + info_text  # Hidden link for preview

        buttons = [
            [
                Button.inline("✅ Confirm", f"confirm_{download_info.message_id}"),
                Button.inline("🔄 Search Again", f"search_{download_info.message_id}")
            ],
            [
                Button.inline("🎬 Movie", f"movie_{download_info.message_id}"),
                Button.inline("📺 TV Series", f"tv_{download_info.message_id}")
            ],
            [Button.inline("❌ Cancel", f"cancel_{download_info.message_id}")]
        ]
        
        await msg.edit(info_text + space_warning, buttons=buttons, link_preview=True)
    
    async def _show_medium_confidence_match(
        self,
        msg,
        download_info,
        space_warning
    ):
        """Show medium confidence TMDB match"""
        # Search for other results
        results = await self.tmdb.search(download_info.movie_folder)
        if results:
            download_info.tmdb_results = results[:3]

        info_text = f"📁 **File:** `{download_info.filename}`\n"
        info_text += f"📏 **Size:** {download_info.size_mb:.1f} MB ({download_info.size_gb:.1f} GB)\n\n"
        info_text += f"🔍 **Possible matches:**\n\n"

        # Show first 3 results
        for idx, result in enumerate(download_info.tmdb_results, 1):
            emoji = "📺" if result.is_tv_show else "🎬"
            info_text += f"{idx}. {emoji} **{result.title}**"
            if result.year:
                info_text += f" ({result.year})"
            info_text += "\n"

        info_text += "\n**Select the correct one or choose type:**"

        buttons = []
        # Buttons for each result
        for idx, result in enumerate(download_info.tmdb_results, 1):
            title = result.title[:17] + "..." if len(result.title) > 20 else result.title
            buttons.append([
                Button.inline(f"{idx}. {title}", f"tmdb_{idx}_{download_info.message_id}")
            ])

        buttons.append([
            Button.inline("🎬 Movie", f"movie_{download_info.message_id}"),
            Button.inline("📺 TV Series", f"tv_{download_info.message_id}")
        ])
        buttons.append([Button.inline("❌ Cancel", f"cancel_{download_info.message_id}")])
        
        await msg.edit(info_text + space_warning, buttons=buttons)
    
    async def _show_manual_selection(
        self,
        msg,
        download_info,
        space_warning
    ):
        """Show manual selection"""
        info_text = self._format_file_info(download_info)

        if self.tmdb:
            info_text += "\n\n⚠️ No TMDB match found - using info from filename"

        # If season/episode was detected, it's definitely a TV series
        if download_info.series_info.season:
            buttons = [
                [
                    Button.inline("✅ Confirm TV Series", f"tv_{download_info.message_id}"),
                    Button.inline("🎬 It's a Movie", f"movie_{download_info.message_id}")
                ],
                [Button.inline("❌ Cancel", f"cancel_{download_info.message_id}")]
            ]
            question = "**Confirm it's a TV series?**"
        else:
            # No TV series pattern detected, ask for type
            buttons = [
                [
                    Button.inline("🎬 Movie", f"movie_{download_info.message_id}"),
                    Button.inline("📺 TV Series", f"tv_{download_info.message_id}")
                ],
                [Button.inline("❌ Cancel", f"cancel_{download_info.message_id}")]
            ]
            question = "**Is it a movie or TV series?**"

        await msg.edit(
            f"📁 **File received:**\n"
            f"`{download_info.filename}`\n"
            f"📏 Size: **{download_info.size_mb:.1f} MB** ({download_info.size_gb:.1f} GB)"
            f"{info_text}\n"
            f"{space_warning}\n\n"
            f"{question}",
            buttons=buttons
        )
    
    def _format_file_info(self, download_info: DownloadInfo) -> str:
        """Format extracted file info"""
        info_text = ""

        if download_info.series_info.season:
            info_text = f"\n\n📺 **Detected:** {download_info.series_info.series_name}\n"
            info_text += f"📅 Season {download_info.series_info.season}"
            if download_info.series_info.episode:
                info_text += f", Episode {download_info.series_info.episode}"
        else:
            info_text = f"\n\n🎬 **Possible title:** {download_info.movie_folder}"
            if any(x in download_info.filename.lower() for x in ['ep', 'episode', 'x0', 'x1', 'x2']):
                info_text += f"\n⚠️ Looks like a TV series but can't identify the season"

        return info_text
    
    def _get_space_warning(self, download_info: DownloadInfo) -> str:
        """Generate space warning if necessary"""
        size_gb = download_info.size_gb

        movies_ok, movies_free = self.space.check_space_available(
            self.config.paths.movies,
            size_gb
        )
        tv_ok, tv_free = self.space.check_space_available(
            self.config.paths.tv,
            size_gb
        )

        if not movies_ok and not tv_ok:
            return (
                f"\n\n🟡 **Space warning:**\n"
                f"File requires {size_gb:.1f} GB + {self.config.limits.min_free_space_gb} GB reserved\n"
                f"Free space: Movies {movies_free:.1f} GB, TV Series {tv_free:.1f} GB\n"
                f"File may be queued for space."
            )

        return ""

    async def text_handler(self, event: events.NewMessage.Event):
        """Handler for text messages (manual season/rename input)"""
        if not await self.auth.check_authorized(event):
            return

        # Check for download waiting for rename
        rename_download = None
        for download_info in self.downloads.active_downloads.values():
            if (download_info.user_id == event.sender_id and
                hasattr(download_info, 'rename_requested') and
                download_info.rename_requested):
                rename_download = download_info
                break

        if rename_download:
            await self._handle_rename_input(event, rename_download)
            return

        # Check for download waiting for season
        waiting_download = None
        for download_info in self.downloads.active_downloads.values():
            if (download_info.user_id == event.sender_id and
                hasattr(download_info, 'waiting_for_season') and
                download_info.waiting_for_season):
                waiting_download = download_info
                break

        if not waiting_download:
            return  # No download waiting

        # Try to parse season number
        try:
            season_text = event.text.strip()
            season_num = int(season_text)

            if season_num < 1 or season_num > 50:
                await event.reply("❌ Invalid season number. Enter a number between 1 and 50.")
                return

            # Reset waiting flag
            waiting_download.waiting_for_season = False
            waiting_download.selected_season = season_num

            # Check space and proceed with download
            size_gb = waiting_download.size_gb
            space_ok, free_gb = self.space.check_space_available(
                waiting_download.dest_path,
                size_gb
            )

            if not space_ok:
                # Queue for space
                position = self.downloads.queue_for_space(waiting_download)
                await event.reply(
                    f"📺 **TV Series** - Season {season_num}\n\n"
                    + self.space.format_space_warning(waiting_download.dest_path, size_gb)
                    + f"\nSpace queue position: #{position}"
                )
                return

            # Queue download
            position = await self.downloads.queue_download(waiting_download)

            await event.reply(
                f"📺 **TV Series** - Season {season_num}\n\n"
                f"📥 **Preparing download...**\n"
                f"✅ Available space: {free_gb:.1f} GB\n"
                f"📊 Queue position: #{position}"
            )

        except ValueError:
            await event.reply("❌ Enter only the season number (e.g., 12)")
        except Exception as e:
            self.logger.error(f"Manual season handling error: {e}")
            await event.reply("❌ Error during selection. Please try again.")
            waiting_download.waiting_for_season = False

    async def _show_duplicate_warning(
        self,
        event,
        download_info: DownloadInfo,
        duplicate: dict
    ):
        """Show duplicate file warning with options"""
        # Format duplicate info
        downloaded_date = duplicate['created_at'][:16] if duplicate['created_at'] else 'Unknown'
        size_gb = duplicate['size_bytes'] / (1024**3) if duplicate['size_bytes'] else 0
        status = duplicate['status']

        # Build warning message
        text = (
            f"⚠️ **Duplicate File Detected!**\n\n"
            f"📁 **File:** `{download_info.filename}`\n"
            f"📏 **Size:** {download_info.size_gb:.2f} GB\n\n"
            f"🔍 **Previously downloaded:**\n"
            f"• Date: {downloaded_date}\n"
            f"• Size: {size_gb:.2f} GB\n"
            f"• Status: {status}\n"
        )

        if duplicate.get('final_path'):
            text += f"• Location: `{duplicate['final_path']}`\n"

        if duplicate.get('movie_title'):
            text += f"• Title: {duplicate['movie_title']}\n"
        elif duplicate.get('series_name'):
            text += f"• Series: {duplicate['series_name']}"
            if duplicate.get('season') and duplicate.get('episode'):
                text += f" S{duplicate['season']:02d}E{duplicate['episode']:02d}"
            text += "\n"

        text += (
            f"\n**What would you like to do?**"
        )

        # Create buttons
        buttons = [
            [
                Button.inline("⏭️ Skip (Don't Download)", f"dup_skip_{download_info.message_id}"),
            ],
            [
                Button.inline("📥 Download Again", f"dup_download_{download_info.message_id}"),
            ],
            [
                Button.inline("✏️ Rename & Download", f"dup_rename_{download_info.message_id}")
            ],
            [
                Button.inline("❌ Cancel", f"dup_cancel_{download_info.message_id}")
            ]
        ]

        await event.reply(text, buttons=buttons)

    async def _handle_rename_input(self, event: events.NewMessage.Event, download_info: DownloadInfo):
        """Handle rename filename input from user"""
        new_filename = event.text.strip()

        # Validate filename
        if not new_filename:
            await event.reply("❌ Filename cannot be empty. Please try again.")
            return

        # Check if filename has extension
        if '.' not in new_filename:
            await event.reply("❌ Filename must include an extension (e.g., .mkv, .mp4). Please try again.")
            return

        # Update filename
        old_filename = download_info.filename
        download_info.filename = new_filename
        download_info.rename_requested = False

        await event.reply(
            f"✅ **Filename renamed**\n\n"
            f"📁 From: `{old_filename}`\n"
            f"📁 To: `{new_filename}`\n\n"
            f"⏳ Processing download..."
        )

        # Proceed with download - determine media type
        if download_info.selected_tmdb:
            if download_info.selected_tmdb.is_tv_show:
                # Need to handle TV selection
                download_info.media_type = MediaType.TV_SHOW
                download_info.is_movie = False
                download_info.dest_path = self.config.paths.tv
                download_info.emoji = "📺"

                # Check if season info exists
                if not download_info.series_info or not download_info.series_info.season:
                    # Need season selection - create a temporary event for callback handler
                    from handlers.callbacks import CallbackHandlers

                    # Get callback handler instance
                    callback_handler = None
                    for handler in self.client.list_event_handlers():
                        if isinstance(handler[0].__self__, CallbackHandlers):
                            callback_handler = handler[0].__self__
                            break

                    if callback_handler:
                        await callback_handler._process_tv_selection(event, download_info)
                    else:
                        self.logger.error("Could not find CallbackHandlers instance")
                        await event.reply("❌ Error processing TV series. Please try again.")
                else:
                    # Has season info, proceed
                    download_info.selected_season = download_info.series_info.season
                    await self._queue_for_download(event, download_info)
            else:
                # Movie
                download_info.media_type = MediaType.MOVIE
                download_info.is_movie = True
                download_info.dest_path = self.config.paths.movies
                download_info.emoji = "🎬"
                await self._queue_for_download(event, download_info)
        elif download_info.is_movie is not None:
            if download_info.is_movie:
                download_info.media_type = MediaType.MOVIE
                download_info.dest_path = self.config.paths.movies
                download_info.emoji = "🎬"
                await self._queue_for_download(event, download_info)
            else:
                download_info.media_type = MediaType.TV_SHOW
                download_info.dest_path = self.config.paths.tv
                download_info.emoji = "📺"
                # Need season info
                if not download_info.series_info or not download_info.series_info.season:
                    from handlers.callbacks import CallbackHandlers

                    callback_handler = None
                    for handler in self.client.list_event_handlers():
                        if isinstance(handler[0].__self__, CallbackHandlers):
                            callback_handler = handler[0].__self__
                            break

                    if callback_handler:
                        await callback_handler._process_tv_selection(event, download_info)
                else:
                    download_info.selected_season = download_info.series_info.season
                    await self._queue_for_download(event, download_info)
        else:
            # Show type selection
            buttons = [
                [
                    Button.inline("🎬 Movie", f"movie_{download_info.message_id}"),
                    Button.inline("📺 TV Series", f"tv_{download_info.message_id}")
                ],
                [Button.inline("❌ Cancel", f"cancel_{download_info.message_id}")]
            ]

            await event.reply(
                f"📁 **File:** `{download_info.filename}`\n"
                f"📏 **Size:** {download_info.size_gb:.1f} GB\n\n"
                f"**Select media type:**",
                buttons=buttons
            )

    async def _queue_for_download(self, event, download_info: DownloadInfo):
        """Queue download after all info is ready"""
        # Check space
        size_gb = download_info.size_gb
        space_ok, free_gb = self.space.check_space_available(
            download_info.dest_path,
            size_gb
        )

        if not space_ok:
            position = self.downloads.queue_for_space(download_info)
            await event.reply(
                f"{download_info.emoji} **{download_info.media_type}**\n\n"
                + self.space.format_space_warning(download_info.dest_path, size_gb)
                + f"\nPosition in space queue: #{position}"
            )
            return

        # Queue download
        position = await self.downloads.queue_download(download_info)

        await event.reply(
            f"{download_info.emoji} **{download_info.media_type}**\n\n"
            f"📥 **Preparing download...**\n"
            f"✅ Available space: {free_gb:.1f} GB\n"
            f"📊 Queue position: #{position}"
        )