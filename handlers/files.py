"""
Handler per file ricevuti via Telegram
"""
import os
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.tl.types import DocumentAttributeFilename
from core.auth import AuthManager
from core.downloader import DownloadManager
from core.tmdb_client import TMDBClient
from core.space_manager import SpaceManager
from models.download import DownloadInfo, MediaType
from utils.naming import FileNameParser
from utils.helpers import ValidationHelpers, FileHelpers


class FileHandlers:
    """Gestione file ricevuti"""
    
    def __init__(
        self,
        client: TelegramClient,
        auth_manager: AuthManager,
        download_manager: DownloadManager,
        tmdb_client: TMDBClient,
        space_manager: SpaceManager
    ):
        self.client = client
        self.auth = auth_manager
        self.downloads = download_manager
        self.tmdb = tmdb_client
        self.space = space_manager
        self.config = download_manager.config
        self.logger = self.config.logger
    
    def register(self):
        """Registra handler file"""
        self.client.on(events.NewMessage(func=lambda e: e.file))(self.file_handler)
        self.client.on(events.NewMessage(func=lambda e: e.text and not e.text.startswith('/')))(self.text_handler)
        self.logger.info("Handler file registrati")
    
    async def file_handler(self, event: events.NewMessage.Event):
        """Handler principale per file ricevuti"""
        if not await self.auth.check_authorized(event):
            return
        
        self.logger.info(
            f"File ricevuto da utente {event.sender_id}, "
            f"dimensione: {event.file.size / (1024*1024):.1f} MB"
        )
        
        # Valida dimensione file
        size_valid, error_msg = ValidationHelpers.validate_file_size(
            event.file.size,
            min_size=1024 * 100,  # 100 KB minimo
            max_size=int(self.config.limits.max_file_size_gb * (1024**3))
        )
        
        if not size_valid:
            await event.reply(f"⚠️ {error_msg}")
            return
        
        # Estrai nome file
        filename = self._extract_filename(event)
        
        # Verifica che sia un file video
        if not FileHelpers.is_video_file(filename):
            await event.reply(
                f"⚠️ **File non supportato**\n\n"
                f"Il file `{filename}` non sembra essere un video.\n"
                f"Formati supportati: {', '.join(FileHelpers.get_video_extensions())}"
            )
            return
        
        # Crea DownloadInfo
        download_info = DownloadInfo(
            message_id=event.message.id,
            user_id=event.sender_id,
            filename=filename,
            original_filename=filename,
            size=event.file.size,
            message=event.message
        )
        
        # Estrai info dal nome
        movie_name, year = FileNameParser.extract_movie_info(filename)
        series_info = FileNameParser.extract_series_info(filename)

        # Imposta movie_folder solo se NON è una serie TV riconosciuta
        if series_info.season is None:
            download_info.movie_folder = FileNameParser.create_folder_name(movie_name, year)

        download_info.series_info = series_info
        
        # Aggiungi al manager
        if not self.downloads.add_download(download_info):
            await event.reply("⚠️ Download già in elaborazione per questo file")
            return
        
        # Processa con TMDB se disponibile
        if self.tmdb:
            await self._process_with_tmdb(event, download_info)
        else:
            await self._process_without_tmdb(event, download_info)
    
    def _extract_filename(self, event) -> str:
        """Estrai nome file dal messaggio"""
        filename = "unknown"
        
        # Prova dal file
        if hasattr(event.file, 'name') and event.file.name:
            filename = event.file.name
        # Prova dagli attributi documento
        elif event.document:
            for attr in event.document.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    filename = attr.file_name
                    break
        
        # Se ancora unknown, genera nome
        if not filename or filename == "unknown":
            filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        
        # Controlla se c'è testo nel messaggio (per file inoltrati)
        message_text = event.message.message if event.message.message else ""
        if message_text and (filename.startswith("video_") or filename == "unknown"):
            detected_name = message_text.strip()
            if not any(detected_name.endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov']):
                ext = os.path.splitext(filename)[1] or '.mp4'
                detected_name += ext
            self.logger.info(f"Nome rilevato dal testo: {detected_name}")
            return detected_name
        
        return filename
    
    async def _process_with_tmdb(self, event, download_info: DownloadInfo):
        """Processa file con ricerca TMDB"""
        initial_msg = await event.reply("🔍 **Ricerca nel database TMDB...**")
        download_info.progress_msg = initial_msg
        
        # Determina tipo ricerca
        if download_info.series_info.season:
            search_query = download_info.series_info.series_name
            media_hint = 'tv'
        else:
            search_query = download_info.movie_folder
            media_hint = None
        
        # Cerca su TMDB
        tmdb_result, confidence = await self.tmdb.search_with_confidence(
            search_query,
            media_hint
        )
        
        if tmdb_result:
            download_info.tmdb_results = [tmdb_result]
            download_info.selected_tmdb = tmdb_result
            download_info.tmdb_confidence = confidence
        
        # Prepara avviso spazio
        space_warning = self._get_space_warning(download_info)
        
        # Mostra risultati
        if tmdb_result and confidence >= 80:
            await self._show_high_confidence_match(
                initial_msg, 
                download_info, 
                tmdb_result, 
                confidence, 
                space_warning
            )
        elif tmdb_result and confidence >= 60:
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
    
    async def _process_without_tmdb(self, event, download_info: DownloadInfo):
        """Processa file senza TMDB"""
        # Info base
        info_text = self._format_file_info(download_info)

        # Avviso spazio
        space_warning = self._get_space_warning(download_info)

        # Se è stata rilevata stagione/episodio, è sicuramente una serie TV
        if download_info.series_info.season:
            buttons = [
                [
                    Button.inline("✅ Conferma Serie TV", f"tv_{download_info.message_id}"),
                    Button.inline("🎬 È un Film", f"movie_{download_info.message_id}")
                ],
                [Button.inline("❌ Cancella", f"cancel_{download_info.message_id}")]
            ]
            question = "**Confermi che è una serie TV?**"
        else:
            # Non è stato rilevato pattern serie TV, chiedi tipo
            buttons = [
                [
                    Button.inline("🎬 Film", f"movie_{download_info.message_id}"),
                    Button.inline("📺 Serie TV", f"tv_{download_info.message_id}")
                ],
                [Button.inline("❌ Cancella", f"cancel_{download_info.message_id}")]
            ]
            question = "**È un film o una serie TV?**"

        msg = await event.reply(
            f"📁 **File ricevuto:**\n"
            f"`{download_info.filename}`\n"
            f"📏 Dimensione: **{download_info.size_mb:.1f} MB** ({download_info.size_gb:.1f} GB)"
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
        """Mostra match TMDB ad alta confidenza"""
        text, poster_url = self.tmdb.format_result(
            tmdb_result,
            download_info.series_info
        )
        
        info_text = f"📁 **File:** `{download_info.filename}`\n"
        info_text += f"📏 **Dimensione:** {download_info.size_mb:.1f} MB ({download_info.size_gb:.1f} GB)\n\n"
        info_text += f"✅ **Match TMDB** (confidenza {confidence}%)\n\n"
        info_text += text
        
        # Aggiungi poster se disponibile
        if poster_url:
            info_text = f"[​]({poster_url})" + info_text  # Link nascosto per preview
        
        buttons = [
            [
                Button.inline("✅ Conferma", f"confirm_{download_info.message_id}"),
                Button.inline("🔄 Cerca ancora", f"search_{download_info.message_id}")
            ],
            [
                Button.inline("🎬 Film", f"movie_{download_info.message_id}"),
                Button.inline("📺 Serie TV", f"tv_{download_info.message_id}")
            ],
            [Button.inline("❌ Cancella", f"cancel_{download_info.message_id}")]
        ]
        
        await msg.edit(info_text + space_warning, buttons=buttons, link_preview=True)
    
    async def _show_medium_confidence_match(
        self,
        msg,
        download_info,
        space_warning
    ):
        """Mostra match TMDB a media confidenza"""
        # Cerca altri risultati
        results = await self.tmdb.search(download_info.movie_folder)
        if results:
            download_info.tmdb_results = results[:3]
        
        info_text = f"📁 **File:** `{download_info.filename}`\n"
        info_text += f"📏 **Dimensione:** {download_info.size_mb:.1f} MB ({download_info.size_gb:.1f} GB)\n\n"
        info_text += f"🔍 **Possibili corrispondenze:**\n\n"
        
        # Mostra primi 3 risultati
        for idx, result in enumerate(download_info.tmdb_results, 1):
            emoji = "📺" if result.is_tv_show else "🎬"
            info_text += f"{idx}. {emoji} **{result.title}**"
            if result.year:
                info_text += f" ({result.year})"
            info_text += "\n"
        
        info_text += "\n**Seleziona quello corretto o scegli il tipo:**"
        
        buttons = []
        # Bottoni per ogni risultato
        for idx, result in enumerate(download_info.tmdb_results, 1):
            title = result.title[:17] + "..." if len(result.title) > 20 else result.title
            buttons.append([
                Button.inline(f"{idx}. {title}", f"tmdb_{idx}_{download_info.message_id}")
            ])
        
        buttons.append([
            Button.inline("🎬 Film", f"movie_{download_info.message_id}"),
            Button.inline("📺 Serie TV", f"tv_{download_info.message_id}")
        ])
        buttons.append([Button.inline("❌ Cancella", f"cancel_{download_info.message_id}")])
        
        await msg.edit(info_text + space_warning, buttons=buttons)
    
    async def _show_manual_selection(
        self,
        msg,
        download_info,
        space_warning
    ):
        """Mostra selezione manuale"""
        info_text = self._format_file_info(download_info)

        if self.tmdb:
            info_text += "\n\n⚠️ Nessuna corrispondenza TMDB trovata - uso info dal nome file"

        # Se è stata rilevata stagione/episodio, è sicuramente una serie TV
        if download_info.series_info.season:
            buttons = [
                [
                    Button.inline("✅ Conferma Serie TV", f"tv_{download_info.message_id}"),
                    Button.inline("🎬 È un Film", f"movie_{download_info.message_id}")
                ],
                [Button.inline("❌ Cancella", f"cancel_{download_info.message_id}")]
            ]
            question = "**Confermi che è una serie TV?**"
        else:
            # Non è stato rilevato pattern serie TV, chiedi tipo
            buttons = [
                [
                    Button.inline("🎬 Film", f"movie_{download_info.message_id}"),
                    Button.inline("📺 Serie TV", f"tv_{download_info.message_id}")
                ],
                [Button.inline("❌ Cancella", f"cancel_{download_info.message_id}")]
            ]
            question = "**È un film o una serie TV?**"

        await msg.edit(
            f"📁 **File ricevuto:**\n"
            f"`{download_info.filename}`\n"
            f"📏 Dimensione: **{download_info.size_mb:.1f} MB** ({download_info.size_gb:.1f} GB)"
            f"{info_text}\n"
            f"{space_warning}\n\n"
            f"{question}",
            buttons=buttons
        )
    
    def _format_file_info(self, download_info: DownloadInfo) -> str:
        """Formatta info file estratte"""
        info_text = ""
        
        if download_info.series_info.season:
            info_text = f"\n\n📺 **Rilevato:** {download_info.series_info.series_name}\n"
            info_text += f"📅 Stagione {download_info.series_info.season}"
            if download_info.series_info.episode:
                info_text += f", Episodio {download_info.series_info.episode}"
        else:
            info_text = f"\n\n🎬 **Possibile titolo:** {download_info.movie_folder}"
            if any(x in download_info.filename.lower() for x in ['ep', 'episode', 'x0', 'x1', 'x2']):
                info_text += f"\n⚠️ Sembra una serie TV ma non riesco a identificare la stagione"
        
        return info_text
    
    def _get_space_warning(self, download_info: DownloadInfo) -> str:
        """Genera avviso spazio se necessario"""
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
                f"\n\n🟡 **Avviso spazio:**\n"
                f"File richiede {size_gb:.1f} GB + {self.config.limits.min_free_space_gb} GB riservati\n"
                f"Spazio libero: Film {movies_free:.1f} GB, Serie TV {tv_free:.1f} GB\n"
                f"Il file potrebbe essere messo in coda per spazio."
            )
        
        return ""

    async def text_handler(self, event: events.NewMessage.Event):
        """Handler per messaggi di testo (per inserimento manuale stagione)"""
        if not await self.auth.check_authorized(event):
            return

        # Cerca download in attesa di stagione per questo utente
        waiting_download = None
        for download_info in self.downloads.active_downloads.values():
            if (download_info.user_id == event.sender_id and
                hasattr(download_info, 'waiting_for_season') and
                download_info.waiting_for_season):
                waiting_download = download_info
                break

        if not waiting_download:
            return  # Non c'è nessun download in attesa

        # Prova a parsare il numero stagione
        try:
            season_text = event.text.strip()
            season_num = int(season_text)

            if season_num < 1 or season_num > 50:
                await event.reply("❌ Numero stagione non valido. Inserisci un numero tra 1 e 50.")
                return

            # Resetta il flag di attesa
            waiting_download.waiting_for_season = False
            waiting_download.selected_season = season_num

            # Verifica spazio e procedi con download
            size_gb = waiting_download.size_gb
            space_ok, free_gb = self.space.check_space_available(
                waiting_download.dest_path,
                size_gb
            )

            if not space_ok:
                # Metti in coda spazio
                position = self.downloads.queue_for_space(waiting_download)
                await event.reply(
                    f"📺 **Serie TV** - Stagione {season_num}\n\n"
                    + self.space.format_space_warning(waiting_download.dest_path, size_gb)
                    + f"\nPosizione in coda spazio: #{position}"
                )
                return

            # Metti in coda download
            position = await self.downloads.queue_download(waiting_download)

            await event.reply(
                f"📺 **Serie TV** - Stagione {season_num}\n\n"
                f"📥 **Preparazione download...**\n"
                f"✅ Spazio disponibile: {free_gb:.1f} GB\n"
                f"📊 Posizione in coda: #{position}"
            )

        except ValueError:
            await event.reply("❌ Inserisci solo il numero della stagione (es: 12)")
        except Exception as e:
            self.logger.error(f"Errore gestione stagione manuale: {e}")
            await event.reply("❌ Errore durante la selezione. Riprova.")
            waiting_download.waiting_for_season = False