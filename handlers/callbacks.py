"""
Telegram callback (buttons) handlers
"""
from telethon import TelegramClient, events, Button
from core.auth import AuthManager
from core.downloader import DownloadManager
from core.space_manager import SpaceManager
from models.download import MediaType
from utils.naming import FileNameParser


class CallbackHandlers:
    """Button callback management"""
    
    def __init__(
        self,
        client: TelegramClient,
        auth_manager: AuthManager,
        download_manager: DownloadManager,
        space_manager: SpaceManager
    ):
        self.client = client
        self.auth = auth_manager
        self.downloads = download_manager
        self.space = space_manager
        self.config = download_manager.config
        self.logger = self.config.logger
    
    def register(self):
        """Register callback handlers"""
        self.client.on(events.CallbackQuery)(self.callback_handler)
        self.logger.info("Callback handlers registered")
    
    async def callback_handler(self, event: events.CallbackQuery.Event):
        """Main callback handler"""
        if not await self.auth.check_callback_authorized(event):
            return
        
        data = event.data.decode('utf-8')
        
        # Route appropriate callback
        if data.startswith('tmdb_'):
            await self._handle_tmdb_selection(event, data)
        elif data.startswith('confirm_'):
            await self._handle_confirm(event, data)
        elif data.startswith('search_'):
            await self._handle_search_again(event, data)
        elif data.startswith('season_'):
            await self._handle_season_selection(event, data)
        elif data.startswith('manual_season_'):
            await self._handle_manual_season(event, data)
        elif data.startswith('cancel_'):
            await self._handle_cancel(event, data)
        elif data.startswith('movie_'):
            await self._handle_movie_selection(event, data)
        elif data.startswith('tv_'):
            await self._handle_tv_selection(event, data)
        else:
            await event.answer("⚠️ Azione non riconosciuta")
    
    async def _handle_tmdb_selection(self, event, data: str):
        """Handles TMDB result selection"""
        parts = data.split('_')
        result_idx = int(parts[1]) - 1
        msg_id = int(parts[2])
        
        download_info = self.downloads.get_download_info(msg_id)
        if not download_info:
            await event.answer("❌ Download expired or already completed")
            return
        
        # Check ownership
        if not self.auth.can_manage_download(event.sender_id, download_info.user_id):
            await event.answer("❌ You can only manage your own downloads", alert=True)
            return
        
        # Seleziona risultato TMDB
        if download_info.tmdb_results and result_idx < len(download_info.tmdb_results):
            download_info.selected_tmdb = download_info.tmdb_results[result_idx]
            download_info.tmdb_confidence = 100  # Confermato dall'utente
            
            # Determina tipo
            if download_info.selected_tmdb.is_tv_show:
                await self._process_tv_selection(event, download_info)
            else:
                await self._process_movie_selection(event, download_info)
    
    async def _handle_confirm(self, event, data: str):
        """Handles TMDB match confirmation"""
        msg_id = int(data.split('_')[1])
        
        download_info = self.downloads.get_download_info(msg_id)
        if not download_info:
            await event.answer("❌ Download expired or already completed")
            return
        
        # Auto-detect type from TMDB
        if download_info.selected_tmdb:
            if download_info.selected_tmdb.is_tv_show:
                await self._process_tv_selection(event, download_info)
            else:
                await self._process_movie_selection(event, download_info)
    
    async def _handle_search_again(self, event, data: str):
        """Handles new search"""
        msg_id = int(data.split('_')[1])
        
        download_info = self.downloads.get_download_info(msg_id)
        if not download_info:
            await event.answer("❌ Download expired or already completed")
            return
        
        # Reset TMDB
        download_info.selected_tmdb = None
        download_info.tmdb_confidence = 0
        
        # Show manual selection
        buttons = [
            [
                Button.inline("🎬 Film", f"movie_{msg_id}"),
                Button.inline("📺 Serie TV", f"tv_{msg_id}")
            ],
            [Button.inline("❌ Cancella", f"cancel_{msg_id}")]
        ]
        
        await event.edit(
            f"📁 **File:** `{download_info.filename}`\n"
            f"📏 **Dimensione:** {download_info.size_gb:.1f} GB\n\n"
            f"**Seleziona tipo media:**",
            buttons=buttons
        )
    
    async def _handle_season_selection(self, event, data: str):
        """Handles season selection"""
        parts = data.split('_')
        season_num = int(parts[1])
        msg_id = int(parts[2])
        
        download_info = self.downloads.get_download_info(msg_id)
        if not download_info:
            await event.answer("❌ Download expired or already completed")
            return
        
        download_info.selected_season = season_num
        
        # Check space
        size_gb = download_info.size_gb
        space_ok, free_gb = self.space.check_space_available(
            download_info.dest_path,
            size_gb
        )
        
        if not space_ok:
            # Put in space queue
            position = self.downloads.queue_for_space(download_info)
            
            await event.edit(
                f"{download_info.emoji} **{download_info.media_type}**\n"
                f"📅 Stagione {season_num}\n\n"
                + self.space.format_space_warning(download_info.dest_path, size_gb)
                + f"\nPosition in space queue: #{position}"
            )
            return
        
        # Put in download queue
        position = await self.downloads.queue_download(download_info)
        
        await event.edit(
            f"{download_info.emoji} **{download_info.media_type}**\n"
            f"📅 Stagione {season_num}\n\n"
            f"📥 **Preparazione download...**\n"
            f"✅ Spazio disponibile: {free_gb:.1f} GB\n"
            f"📊 Position in queue: #{position}"
        )

    async def _handle_manual_season(self, event, data: str):
        """Handles manual season number input"""
        msg_id = int(data.split('_')[2])

        download_info = self.downloads.get_download_info(msg_id)
        if not download_info:
            await event.answer("❌ Download expired or already completed")
            return

        # Series name
        series_name = download_info.series_info.series_name if download_info.series_info else "Serie"
        if download_info.selected_tmdb:
            series_name = download_info.selected_tmdb.title

        # Save message ID in download_info for future reference
        download_info.waiting_for_season = True

        await event.edit(
            f"📺 **Serie TV selezionata**\n\n"
            f"📁 Serie: `{series_name}`\n"
            f"📄 File: `{download_info.filename}`\n\n"
            f"**Scrivi il numero della stagione** (es: `12`)\n"
            f"_Risponderò con un messaggio qui sotto_",
            buttons=[[Button.inline("❌ Cancella", f"cancel_{download_info.message_id}")]]
        )

    async def _handle_cancel(self, event, data: str):
        """Handles cancellation"""
        msg_id = int(data.split('_')[1])
        
        download_info = self.downloads.get_download_info(msg_id)
        if not download_info:
            await event.answer("❌ Download già completato o cancellato")
            return
        
        # Check ownership
        if not self.auth.can_manage_download(event.sender_id, download_info.user_id):
            await event.answer("❌ Puoi cancellare solo i tuoi download", alert=True)
            return
        
        # Cancel
        self.downloads.cancel_download(msg_id)
        
        await event.edit("❌ Download cancellato")
    
    async def _handle_movie_selection(self, event, data: str):
        """Handles movie selection"""
        msg_id = int(data.split('_')[1])
        
        download_info = self.downloads.get_download_info(msg_id)
        if not download_info:
            await event.answer("❌ Download expired or already completed")
            return
        
        await self._process_movie_selection(event, download_info)
    
    async def _handle_tv_selection(self, event, data: str):
        """Handles TV series selection"""
        msg_id = int(data.split('_')[1])
        
        download_info = self.downloads.get_download_info(msg_id)
        if not download_info:
            await event.answer("❌ Download expired or already completed")
            return
        
        await self._process_tv_selection(event, download_info)
    
    async def _process_movie_selection(self, event, download_info):
        """Processes movie selection"""
        download_info.media_type = MediaType.MOVIE
        download_info.is_movie = True
        download_info.dest_path = self.config.paths.movies
        download_info.emoji = "🎬"
        download_info.event = event
        
        # Check space
        size_gb = download_info.size_gb
        space_ok, free_gb = self.space.check_space_available(
            download_info.dest_path,
            size_gb
        )
        
        if not space_ok:
            position = self.downloads.queue_for_space(download_info)
            
            await event.edit(
                f"🎬 **Film** selezionato\n\n"
                + self.space.format_space_warning(download_info.dest_path, size_gb)
                + f"\nPosition in space queue: #{position}"
            )
            return
        
        # Metti in coda
        position = await self.downloads.queue_download(download_info)
        
        # Notifica
        active_downloads = len(self.downloads.get_active_downloads())
        
        if active_downloads >= self.config.limits.max_concurrent_downloads:
            await event.edit(
                f"🎬 **Film** selezionato\n\n"
                f"⏳ **In coda** - Posizione: #{position}\n"
                f"Download attivi: {active_downloads}/{self.config.limits.max_concurrent_downloads}\n\n"
                f"✅ Spazio disponibile: {free_gb:.1f} GB\n"
                f"Il download partirà automaticamente."
            )
        else:
            await event.edit(
                f"🎬 **Film** selezionato\n\n"
                f"📥 **Preparazione download...**\n"
                f"✅ Spazio disponibile: {free_gb:.1f} GB"
            )
    
    async def _process_tv_selection(self, event, download_info):
        """Processa selezione serie TV"""
        download_info.media_type = MediaType.TV_SHOW
        download_info.is_movie = False
        download_info.dest_path = self.config.paths.tv
        download_info.emoji = "📺"
        download_info.event = event
        
        # Se non ha info stagione, chiedi
        if not download_info.series_info or not download_info.series_info.season:
            # Bottoni stagione
            season_buttons = []
            for i in range(1, 6):
                if len(season_buttons) < 1:
                    season_buttons.append([])
                season_buttons[0].append(
                    Button.inline(f"S{i}", f"season_{i}_{download_info.message_id}")
                )
            
            for i in range(6, 11):
                if len(season_buttons) < 2:
                    season_buttons.append([])
                season_buttons[1].append(
                    Button.inline(f"S{i}", f"season_{i}_{download_info.message_id}")
                )
            
            season_buttons.append([
                Button.inline("✏️ Inserisci numero", f"manual_season_{download_info.message_id}")
            ])
            season_buttons.append([
                Button.inline("❌ Cancella", f"cancel_{download_info.message_id}")
            ])
            
            # Series name
            series_name = download_info.series_info.series_name if download_info.series_info else "Serie"
            if download_info.selected_tmdb:
                series_name = download_info.selected_tmdb.title
            
            await event.edit(
                f"📺 **Serie TV selezionata**\n\n"
                f"📁 Serie: `{series_name}`\n"
                f"📄 File: `{download_info.filename}`\n\n"
                f"**Quale stagione?**\n"
                f"_Usa ✏️ Inserisci numero per stagioni oltre la 10_",
                buttons=season_buttons
            )
            return
        
        # Ha già info stagione
        download_info.selected_season = download_info.series_info.season
        
        # Check space
        size_gb = download_info.size_gb
        space_ok, free_gb = self.space.check_space_available(
            download_info.dest_path,
            size_gb
        )
        
        if not space_ok:
            position = self.downloads.queue_for_space(download_info)
            
            await event.edit(
                f"📺 **Serie TV** selezionata\n\n"
                + self.space.format_space_warning(download_info.dest_path, size_gb)
                + f"\nPosition in space queue: #{position}"
            )
            return
        
        # Metti in coda
        position = await self.downloads.queue_download(download_info)
        
        # Notifica
        await event.edit(
            f"📺 **Serie TV** selezionata\n"
            f"📅 Stagione {download_info.selected_season}\n\n"
            f"📥 **Preparazione download...**\n"
            f"✅ Spazio disponibile: {free_gb:.1f} GB\n"
            f"📊 Position in queue: #{position}"
        )