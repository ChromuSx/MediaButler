"""
Gestione download e code
"""
import asyncio
import time
from pathlib import Path
from typing import Dict, Optional, Set
from collections import defaultdict
from telethon import TelegramClient
from core.config import get_config
from core.space_manager import SpaceManager
from core.tmdb_client import TMDBClient
from models.download import DownloadInfo, DownloadStatus, QueueItem
from utils.helpers import RetryHelpers
from utils.naming import FileNameParser


class DownloadManager:
    """Gestore download e code"""
    
    def __init__(
        self,
        client: TelegramClient,
        space_manager: SpaceManager,
        tmdb_client: Optional[TMDBClient] = None
    ):
        self.client = client
        self.space_manager = space_manager
        self.tmdb_client = tmdb_client
        self.config = get_config()
        self.logger = self.config.logger
        
        # Strutture dati per gestione download
        self.active_downloads: Dict[int, DownloadInfo] = {}
        self.download_tasks: Dict[int, asyncio.Task] = {}
        self.download_queue = asyncio.Queue()
        self.space_waiting_queue: list[QueueItem] = []
        self.cancelled_downloads: Set[int] = set()
        
        # Workers
        self.workers = []
        self.space_monitor_task = None
        
    async def start_workers(self):
        """Avvia workers per processare download"""
        # Crea worker download
        for i in range(self.config.limits.max_concurrent_downloads):
            worker = asyncio.create_task(self._download_worker())
            self.workers.append(worker)
        
        # Avvia monitor spazio
        self.space_monitor_task = asyncio.create_task(self._space_monitor_worker())
        
        self.logger.info(f"Avviati {len(self.workers)} download workers")
    
    async def stop(self):
        """Ferma tutti i workers"""
        # Cancella tutti i download attivi
        for msg_id in list(self.active_downloads.keys()):
            self.cancelled_downloads.add(msg_id)
        
        # Cancella task
        for task in self.download_tasks.values():
            task.cancel()
        
        # Ferma workers
        for worker in self.workers:
            worker.cancel()
        
        if self.space_monitor_task:
            self.space_monitor_task.cancel()
        
        # Attendi chiusura
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.logger.info("Download manager fermato")
    
    def add_download(self, download_info: DownloadInfo) -> bool:
        """
        Aggiunge un download
        
        Args:
            download_info: Info download
            
        Returns:
            True se aggiunto, False se già presente
        """
        if download_info.message_id in self.active_downloads:
            return False
        
        self.active_downloads[download_info.message_id] = download_info
        return True
    
    async def queue_download(self, download_info: DownloadInfo) -> int:
        """
        Mette in coda un download
        
        Args:
            download_info: Info download
            
        Returns:
            Posizione in coda
        """
        queue_item = QueueItem(download_info=download_info)
        await self.download_queue.put(queue_item)
        
        download_info.status = DownloadStatus.QUEUED
        return self.download_queue.qsize()
    
    def queue_for_space(self, download_info: DownloadInfo) -> int:
        """
        Mette in coda per spazio
        
        Args:
            download_info: Info download
            
        Returns:
            Posizione in coda spazio
        """
        queue_item = QueueItem(download_info=download_info)
        self.space_waiting_queue.append(queue_item)
        
        download_info.status = DownloadStatus.WAITING_SPACE
        return len(self.space_waiting_queue)
    
    def cancel_download(self, message_id: int) -> bool:
        """
        Cancella un download
        
        Args:
            message_id: ID messaggio
            
        Returns:
            True se cancellato
        """
        self.cancelled_downloads.add(message_id)
        
        if message_id in self.download_tasks:
            self.download_tasks[message_id].cancel()
            return True
        
        if message_id in self.active_downloads:
            self.active_downloads[message_id].status = DownloadStatus.CANCELLED
            return True
        
        return False
    
    def cancel_all_downloads(self) -> int:
        """
        Cancella tutti i download
        
        Returns:
            Numero download cancellati
        """
        cancelled = 0
        
        # Cancella attivi
        for msg_id in list(self.active_downloads.keys()):
            if self.cancel_download(msg_id):
                cancelled += 1
        
        # Svuota code
        while not self.download_queue.empty():
            try:
                queue_item = self.download_queue.get_nowait()
                self.cancelled_downloads.add(queue_item.download_info.message_id)
                cancelled += 1
            except:
                break
        
        # Svuota coda spazio
        for item in self.space_waiting_queue:
            self.cancelled_downloads.add(item.download_info.message_id)
            cancelled += 1
        self.space_waiting_queue.clear()
        
        return cancelled
    
    def get_active_downloads(self) -> list[DownloadInfo]:
        """Ottieni download attivi"""
        return [
            info for msg_id, info in self.active_downloads.items()
            if msg_id in self.download_tasks
        ]
    
    def get_queued_count(self) -> int:
        """Ottieni numero file in coda"""
        return self.download_queue.qsize()
    
    def get_space_waiting_count(self) -> int:
        """Ottieni numero file in attesa spazio"""
        return len(self.space_waiting_queue)
    
    def get_download_info(self, message_id: int) -> Optional[DownloadInfo]:
        """Ottieni info download"""
        return self.active_downloads.get(message_id)
    
    def is_downloading(self, message_id: int) -> bool:
        """Verifica se sta scaricando"""
        return message_id in self.download_tasks
    
    async def _download_worker(self):
        """Worker che processa coda download"""
        while True:
            try:
                # Attendi slot libero
                while len(self.download_tasks) >= self.config.limits.max_concurrent_downloads:
                    await asyncio.sleep(1)
                
                # Prendi dalla coda
                queue_item = await self.download_queue.get()
                download_info = queue_item.download_info
                msg_id = download_info.message_id
                
                # Verifica se cancellato
                if msg_id in self.cancelled_downloads:
                    self.logger.info(f"Download cancellato dalla coda: {download_info.filename}")
                    self.cancelled_downloads.discard(msg_id)
                    continue
                
                # Verifica spazio
                size_gb = download_info.size_gb
                space_ok, free_gb = self.space_manager.check_space_available(
                    download_info.dest_path,
                    size_gb
                )
                
                if not space_ok:
                    # Rimetti in coda spazio
                    self.queue_for_space(download_info)
                    self.logger.warning(
                        f"Spazio insufficiente per {download_info.filename}, "
                        f"messo in coda spazio"
                    )
                    
                    # Notifica utente se possibile
                    if download_info.event:
                        try:
                            await download_info.event.edit(
                                self.space_manager.format_space_warning(
                                    download_info.dest_path,
                                    size_gb
                                )
                            )
                        except:
                            pass
                    continue
                
                # Avvia download
                task = asyncio.create_task(self._download_file(download_info))
                self.download_tasks[msg_id] = task
                
                # Attendi completamento
                await task
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Errore in download worker: {e}", exc_info=True)
    
    async def _space_monitor_worker(self):
        """Worker che monitora spazio e processa coda attesa"""
        while True:
            try:
                await asyncio.sleep(self.config.limits.space_check_interval)
                
                if not self.space_waiting_queue:
                    continue
                
                processed = []
                
                for queue_item in self.space_waiting_queue:
                    download_info = queue_item.download_info
                    msg_id = download_info.message_id
                    
                    # Verifica se cancellato
                    if msg_id in self.cancelled_downloads:
                        processed.append(queue_item)
                        continue
                    
                    # Verifica spazio
                    size_gb = download_info.size_gb
                    space_ok, free_gb = self.space_manager.check_space_available(
                        download_info.dest_path,
                        size_gb
                    )
                    
                    # Se c'è spazio e slot libero, sposta in coda download
                    if space_ok and len(self.download_tasks) < self.config.limits.max_concurrent_downloads:
                        await self.download_queue.put(queue_item)
                        processed.append(queue_item)
                        
                        self.logger.info(
                            f"Spazio disponibile per {download_info.filename}, "
                            f"spostato in coda download"
                        )
                        
                        # Notifica utente
                        if download_info.event:
                            try:
                                await download_info.event.edit(
                                    f"{download_info.emoji} **{download_info.media_type}**\n\n"
                                    f"✅ **Spazio disponibile!**\n"
                                    f"📥 Spostato in coda download...\n"
                                    f"💾 Spazio libero: {free_gb:.1f} GB"
                                )
                            except:
                                pass
                
                # Rimuovi processati
                for item in processed:
                    self.space_waiting_queue.remove(item)
                
            except Exception as e:
                self.logger.error(f"Errore in space monitor: {e}", exc_info=True)
    
    async def _download_file(self, download_info: DownloadInfo):
        """Esegue download di un file con retry e gestione sicura"""
        msg_id = download_info.message_id
        
        try:
            # Verifica cancellazione
            if msg_id in self.cancelled_downloads:
                self.logger.info(f"Download già cancellato: {download_info.filename}")
                return
            
            # Aggiorna stato
            download_info.status = DownloadStatus.DOWNLOADING
            download_info.start_time = time.time()
            
            # Prepara percorsi
            filepath = self._prepare_file_path(download_info)
            download_info.final_path = filepath
            
            # Controlla se file già esiste (evita duplicati)
            if filepath.exists():
                existing_hash = FileHelpers.get_file_hash(filepath)
                self.logger.warning(f"File già esistente: {filepath} (hash: {existing_hash})")
                
                # Notifica utente
                if download_info.event:
                    await download_info.event.edit(
                        f"⚠️ **File già presente**\n\n"
                        f"Il file `{filepath.name}` esiste già nella destinazione.\n"
                        f"Download annullato per evitare duplicati."
                    )
                return
            
            self.logger.info(f"Download avviato: {download_info.filename} -> {filepath}")
            
            # Info per display
            path_info = self._get_path_info(download_info, filepath)
            
            # Notifica inizio
            if download_info.event:
                await download_info.event.edit(
                    f"{download_info.emoji} **{download_info.media_type}**\n\n"
                    f"📥 **Download in corso...**\n"
                    f"`{filepath.name}`\n\n"
                    f"{path_info}"
                    f"Inizializzazione..."
                )
            
            # Callback progresso
            last_update = time.time()
            
            async def progress_callback(current, total):
                nonlocal last_update
                
                # Verifica cancellazione
                if msg_id in self.cancelled_downloads:
                    raise asyncio.CancelledError("Download cancellato dall'utente")
                
                now = time.time()
                if now - last_update < 2:  # Aggiorna ogni 2 secondi
                    return
                
                last_update = now
                await self._update_progress(download_info, current, total, path_info)
            
            # Download in temp prima, poi sposta (più sicuro)
            temp_path = self.config.paths.temp / f"{msg_id}_{filepath.name}"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Scarica con retry automatico
            @RetryHelpers.async_retry(max_attempts=3, delay=2, exceptions=(Exception,))
            async def download_with_retry():
                return await self.client.download_media(
                    download_info.message,
                    temp_path,
                    progress_callback=progress_callback
                )
            
            await download_with_retry()
            
            # Verifica cancellazione finale
            if msg_id in self.cancelled_downloads:
                if temp_path.exists():
                    temp_path.unlink()
                raise asyncio.CancelledError("Download cancellato")
            
            # Sposta file in posizione finale (atomico)
            if not FileHelpers.safe_move(temp_path, filepath):
                raise Exception("Impossibile spostare file nella destinazione finale")
            
            # Completato
            download_info.status = DownloadStatus.COMPLETED
            download_info.end_time = time.time()
            
            # Calcola hash per deduplicazione futura
            file_hash = await AsyncHelpers.run_with_timeout(
                asyncio.to_thread(FileHelpers.get_file_hash, filepath),
                timeout=30,
                default="unknown"
            )
            self.logger.info(f"File completato: {filepath} (hash: {file_hash})")
            
            # Notifica completamento
            await self._notify_completion(download_info, filepath)
            
        except asyncio.CancelledError:
            self.logger.info(f"Download cancellato: {download_info.filename}")
            download_info.status = DownloadStatus.CANCELLED
            
            # Pulizia file temporaneo
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            
            # Pulizia file finale e cartelle
            if download_info.final_path and download_info.final_path.exists():
                self.space_manager.smart_cleanup(
                    download_info.final_path,
                    download_info.is_movie
                )
            
            # Notifica cancellazione
            if download_info.event:
                try:
                    await download_info.event.edit(
                        f"❌ **Download cancellato**\n\n"
                        f"File: `{download_info.filename}`"
                    )
                except:
                    pass
            
        except Exception as e:
            self.logger.error(f"Errore download: {e}", exc_info=True)
            download_info.status = DownloadStatus.FAILED
            download_info.error_message = str(e)
            
            # Pulizia file temporaneo se esiste
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            
            # Notifica errore
            if download_info.event:
                try:
                    await download_info.event.edit(
                        f"❌ **Errore durante il download**\n\n"
                        f"File: `{download_info.filename}`\n"
                        f"Errore: `{str(e)}`"
                    )
                except:
                    pass
                    
        finally:
            # Rimuovi da strutture
            if msg_id in self.download_tasks:
                del self.download_tasks[msg_id]
            if msg_id in self.active_downloads:
                del self.active_downloads[msg_id]
            self.cancelled_downloads.discard(msg_id)
    
    def _prepare_file_path(self, download_info: DownloadInfo) -> Path:
        """Prepara percorso file finale"""
        # Determina nome file e cartella
        if download_info.selected_tmdb and download_info.tmdb_confidence >= 60:
            # Usa naming TMDB
            folder_name, filename = FileNameParser.create_tmdb_filename(
                download_info.selected_tmdb,
                download_info.original_filename,
                download_info.series_info
            )
        else:
            # Usa naming base
            folder_name = download_info.movie_folder or download_info.display_name
            filename = download_info.filename
        
        # Crea struttura cartelle
        if download_info.is_movie:
            folder_path = download_info.dest_path / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)
            download_info.created_folders.append(folder_path)
            filepath = folder_path / filename
        else:
            # Serie TV
            series_folder = download_info.dest_path / folder_name
            season_folder = series_folder / f"Season {download_info.selected_season:02d}"
            season_folder.mkdir(parents=True, exist_ok=True)
            
            if not series_folder.exists():
                download_info.created_folders.append(series_folder)
            if not season_folder.exists():
                download_info.created_folders.append(season_folder)
            
            filepath = season_folder / filename
        
        return filepath
    
    def _get_path_info(self, download_info: DownloadInfo, filepath: Path) -> str:
        """Genera info percorso per display"""
        if download_info.is_movie:
            return f"📁 Cartella: `{filepath.parent.name}/`\n"
        else:
            season_folder = filepath.parent
            series_folder = season_folder.parent
            return (
                f"📁 Serie: `{series_folder.name}/`\n"
                f"📅 Stagione: `{season_folder.name}/`\n"
            )
    
    async def _update_progress(
        self,
        download_info: DownloadInfo,
        current: int,
        total: int,
        path_info: str
    ):
        """Aggiorna progresso download"""
        progress = (current / total) * 100
        download_info.progress = progress
        
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        
        # Calcola velocità ed ETA
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
            eta_str = "calcolo..."
        
        # Progress bar
        filled = int(progress / 5)
        bar = "█" * filled + "░" * (20 - filled)
        
        # Stato spazio
        free_gb = self.space_manager.get_free_space_gb(download_info.dest_path)
        space_emoji = "🟢" if free_gb > self.config.limits.warning_threshold_gb else "🟡" if free_gb > self.config.limits.min_free_space_gb else "🔴"
        
        # Aggiorna messaggio
        if download_info.event:
            try:
                await download_info.event.edit(
                    f"{download_info.emoji} **{download_info.media_type}**\n\n"
                    f"📥 **Download in corso...**\n"
                    f"`{download_info.final_path.name}`\n\n"
                    f"{path_info}"
                    f"`[{bar}]`\n"
                    f"**{progress:.1f}%** - {current_mb:.1f}/{total_mb:.1f} MB\n"
                    f"⚡ Velocità: **{speed:.1f} MB/s**\n"
                    f"⏱ Tempo rimanente: **{eta_str}**\n"
                    f"{space_emoji} Spazio libero: **{free_gb:.1f} GB**"
                )
            except:
                pass
    
    async def _notify_completion(self, download_info: DownloadInfo, filepath: Path):
        """Notifica completamento download"""
        final_free_gb = self.space_manager.get_free_space_gb(download_info.dest_path)
        
        # Percorso relativo per display
        if download_info.is_movie:
            display_path = f"{filepath.parent.name}/{filepath.name}"
        else:
            season_folder = filepath.parent
            series_folder = season_folder.parent
            display_path = f"{series_folder.name}/{season_folder.name}/{filepath.name}"
        
        if download_info.event:
            try:
                await download_info.event.edit(
                    f"✅ **Download completato!**\n\n"
                    f"{download_info.emoji} Tipo: **{download_info.media_type}**\n"
                    f"📁 File: `{filepath.name}`\n"
                    f"📂 Percorso: `{display_path}`\n"
                    f"💾 Spazio rimanente: **{final_free_gb:.1f} GB**\n\n"
                    f"🎬 Disponibile sul tuo media server!"
                )
            except:
                pass
        
        self.logger.info(f"Download completato: {filepath}")