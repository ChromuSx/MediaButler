"""
Handler per comandi Telegram
"""
import sys
import asyncio
from telethon import TelegramClient, events
from core.auth import AuthManager
from core.space_manager import SpaceManager
from core.downloader import DownloadManager
from core.config import get_config
from utils.helpers import human_readable_size, FileHelpers


class CommandHandlers:
    """Gestione comandi bot"""
    
    def __init__(
        self,
        client: TelegramClient,
        auth_manager: AuthManager,
        space_manager: SpaceManager,
        download_manager: DownloadManager
    ):
        self.client = client
        self.auth = auth_manager
        self.space = space_manager
        self.downloads = download_manager
        self.config = get_config()
        self.logger = self.config.logger
    
    def register(self):
        """Registra tutti gli handler comandi"""
        self.client.on(events.NewMessage(pattern='/start'))(self.start_handler)
        self.client.on(events.NewMessage(pattern='/status'))(self.status_handler)
        self.client.on(events.NewMessage(pattern='/space'))(self.space_handler)
        self.client.on(events.NewMessage(pattern='/waiting'))(self.waiting_handler)
        self.client.on(events.NewMessage(pattern='/cancel_all'))(self.cancel_all_handler)
        self.client.on(events.NewMessage(pattern='/stop'))(self.stop_handler)
        self.client.on(events.NewMessage(pattern='/users'))(self.users_handler)
        self.client.on(events.NewMessage(pattern='/help'))(self.help_handler)
        
        self.logger.info("Handler comandi registrati")
    
    async def start_handler(self, event: events.NewMessage.Event):
        """Handler comando /start"""
        if not await self.auth.check_authorized(event):
            return
        
        user = await event.get_sender()
        self.logger.info(f"/start da {user.username} (ID: {user.id})")
        
        # Info spazio
        disk_usage = self.space.get_all_disk_usage()
        space_info = "\n💾 **Spazio Disponibile:**\n"
        
        for name, usage in disk_usage.items():
            space_info += f"• {name.capitalize()}: {usage.free_gb:.1f} GB liberi\n"
        
        # Stato TMDB
        tmdb_status = "✅ Integrazione TMDB Attiva" if self.config.tmdb.is_enabled else "⚠️ TMDB non configurato"
        
        await event.reply(
            f"🎬 **MediaButler - Bot Media Server**\n\n"
            f"✅ Accesso consentito!\n"
            f"🆔 Il tuo ID: `{user.id}`\n"
            f"🐳 Esecuzione in Docker\n"
            f"🎯 {tmdb_status}\n"
            f"{space_info}\n"
            f"📊 **Comandi:**\n"
            f"• `/status` - Mostra download e spazio\n"
            f"• `/space` - Dettagli spazio disco\n"
            f"• `/waiting` - File in attesa di spazio\n"
            f"• `/cancel_all` - Cancella tutti i download\n"
            f"• `/help` - Mostra aiuto\n"
            f"• `/stop` - Ferma il bot (solo admin)\n\n"
            f"⚙️ **Impostazioni:**\n"
            f"• Spazio minimo riservato: {self.config.limits.min_free_space_gb} GB\n"
            f"• Download simultanei: max {self.config.limits.max_concurrent_downloads}\n"
            f"• 📁 Organizzazione automatica cartelle\n"
            f"• 🎯 Riconoscimento intelligente contenuti\n\n"
            f"Invia file per iniziare!"
        )
    
    async def status_handler(self, event: events.NewMessage.Event):
        """Handler comando /status"""
        if not await self.auth.check_authorized(event):
            return
        
        status_text = "📊 **Stato Sistema**\n\n"
        
        # Download attivi
        active = self.downloads.get_active_downloads()
        if active:
            status_text += "**Download attivi:**\n"
            for info in active:
                status_text += f"📥 `{info.filename[:30]}...`\n"
                if info.progress > 0:
                    status_text += f"   Progresso: {info.progress:.1f}%\n"
                    if info.speed_mbps > 0:
                        status_text += f"   Velocità: {info.speed_mbps:.1f} MB/s\n"
                status_text += "\n"
        else:
            status_text += "📭 Nessun download attivo\n\n"
        
        # Code
        queue_count = self.downloads.get_queued_count()
        if queue_count > 0:
            status_text += f"⏳ **In coda:** {queue_count} file\n"
        
        space_waiting = self.downloads.get_space_waiting_count()
        if space_waiting > 0:
            status_text += f"⏸️ **In attesa di spazio:** {space_waiting} file\n"
        
        # Spazio disco
        status_text += "\n💾 **Spazio disco:**\n"
        disk_usage = self.space.get_all_disk_usage()
        
        for name, usage in disk_usage.items():
            status_text += f"{usage.status_emoji} {name.capitalize()}: {usage.free_gb:.1f} GB liberi\n"
        
        await event.reply(status_text)
    
    async def space_handler(self, event: events.NewMessage.Event):
        """Handler comando /space"""
        if not await self.auth.check_authorized(event):
            return
        
        space_status = self.space.format_disk_status()
        await event.reply(space_status)
    
    async def waiting_handler(self, event: events.NewMessage.Event):
        """Handler comando /waiting"""
        if not await self.auth.check_authorized(event):
            return
        
        waiting_count = self.downloads.get_space_waiting_count()
        
        if waiting_count == 0:
            await event.reply("✅ Nessun file in attesa di spazio")
            return
        
        waiting_text = f"⏳ **File in attesa di spazio:** {waiting_count}\n\n"
        
        # Mostra primi 10
        for idx, item in enumerate(self.downloads.space_waiting_queue[:10], 1):
            info = item.download_info
            waiting_text += f"{idx}. `{info.filename[:40]}...`\n"
            waiting_text += f"   📏 Richiede: {info.size_gb:.1f} GB\n"
            waiting_text += f"   📂 Destinazione: {info.media_type}\n\n"
        
        if waiting_count > 10:
            waiting_text += f"... e altri {waiting_count - 10} file"
        
        await event.reply(waiting_text)
    
    async def cancel_all_handler(self, event: events.NewMessage.Event):
        """Handler comando /cancel_all"""
        if not await self.auth.check_authorized(event):
            return
        
        # Conta elementi prima
        active = len(self.downloads.get_active_downloads())
        queued = self.downloads.get_queued_count()
        waiting = self.downloads.get_space_waiting_count()
        
        # Cancella tutto
        total_cancelled = self.downloads.cancel_all_downloads()
        
        await event.reply(
            f"❌ **Cancellazione completata**\n\n"
            f"• Download attivi cancellati: {active}\n"
            f"• File in coda cancellati: {queued}\n"
            f"• File in attesa spazio cancellati: {waiting}\n\n"
            f"Totale: {total_cancelled} operazioni cancellate"
        )
    
    async def stop_handler(self, event: events.NewMessage.Event):
        """Handler comando /stop"""
        if not await self.auth.check_authorized(event):
            return
        
        # Solo admin può fermare
        if not await self.auth.require_admin(event):
            return
        
        await event.reply("🛑 **Arresto bot in corso...**")
        
        self.logger.info("Arresto richiesto dall'amministratore")
        
        # Cancella download
        self.downloads.cancel_all_downloads()
        
        # Attendi un po'
        await asyncio.sleep(2)
        
        # Disconnetti
        await self.client.disconnect()
        sys.exit(0)
    
    async def users_handler(self, event: events.NewMessage.Event):
        """Handler comando /users (solo admin)"""
        if not await self.auth.check_authorized(event):
            return
        
        if not await self.auth.require_admin(event):
            return
        
        users = self.auth.get_authorized_users()
        admin_id = self.auth.get_admin_id()
        
        users_text = f"👥 **Utenti Autorizzati:** {len(users)}\n\n"
        
        for idx, user_id in enumerate(users, 1):
            is_admin = " 👑" if user_id == admin_id else ""
            users_text += f"{idx}. `{user_id}`{is_admin}\n"
        
        users_text += "\n📝 Per aggiungere utenti, modifica `AUTHORIZED_USERS` nel file .env"
        
        await event.reply(users_text)
    
    async def help_handler(self, event: events.NewMessage.Event):
        """Handler comando /help"""
        if not await self.auth.check_authorized(event):
            return
        
        help_text = """
🎬 **MediaButler - Guida Rapida**

**📥 Come scaricare:**
1. Inoltra o invia un file video al bot
2. Il bot rileverà il titolo e mostrerà info
3. Scegli Film o Serie TV
4. Per serie senza info stagione, seleziona la stagione
5. Il download parte automaticamente o va in coda

**📁 Organizzazione:**
• Film: `/movies/Nome Film (Anno)/file.mp4`
• Serie: `/tv/Nome Serie/Season 01/file.mp4`

**⚙️ Comandi disponibili:**
• `/start` - Inizializza bot e mostra stato
• `/status` - Visualizza download attivi e coda
• `/space` - Controlla spazio disco dettagliato
• `/waiting` - Mostra file in attesa di spazio
• `/cancel_all` - Cancella tutti i download
• `/help` - Mostra questo messaggio
• `/stop` - Ferma il bot (solo admin)

**🎯 Funzionalità:**
• Riconoscimento automatico contenuti
• Integrazione TMDB per metadata
• Gestione intelligente spazio disco
• Code con priorità
• Multi-utente con whitelist

**❓ Problemi comuni:**
• File troppo grande → Limite 10GB
• Download bloccato → Controlla spazio con `/space`
• Bot non risponde → Verifica autorizzazione

Per supporto, contatta l'amministratore.
"""
        
        await event.reply(help_text)
    
    async def duplicates_handler(self, event: events.NewMessage.Event):
        """Handler comando /duplicates - trova file duplicati"""
        if not await self.auth.check_authorized(event):
            return
        
        if not await self.auth.require_admin(event):
            return
        
        await event.reply("🔍 **Ricerca duplicati in corso...**\nQuesto potrebbe richiedere alcuni minuti.")
        
        try:
            # Cerca duplicati in movies e tv
            all_duplicates = {}
            
            # Scansiona movies
            movies_duplicates = await asyncio.to_thread(
                FileHelpers.find_duplicate_files,
                self.config.paths.movies
            )
            
            # Scansiona TV
            tv_duplicates = await asyncio.to_thread(
                FileHelpers.find_duplicate_files,
                self.config.paths.tv
            )
            
            # Unisci risultati
            all_duplicates.update(movies_duplicates)
            all_duplicates.update(tv_duplicates)
            
            if not all_duplicates:
                await event.reply("✅ **Nessun duplicato trovato!**\n\nLa tua libreria è pulita.")
                return
            
            # Formatta risultati
            duplicates_text = "🔍 **File Duplicati Trovati**\n\n"
            total_wasted = 0
            
            for idx, (file_hash, files) in enumerate(all_duplicates.items(), 1):
                duplicates_text += f"**Gruppo {idx}** (hash: `{file_hash[:8]}...`):\n"
                
                for file_path in files:
                    file_size = file_path.stat().st_size
                    duplicates_text += f"• `{file_path.name}`\n"
                    duplicates_text += f"  📁 {file_path.parent.name}/\n"
                    duplicates_text += f"  📏 {human_readable_size(file_size)}\n"
                    
                    # Conta spazio sprecato (tutti tranne il primo)
                    if files.index(file_path) > 0:
                        total_wasted += file_size
                
                duplicates_text += "\n"
                
                # Limita messaggio
                if len(duplicates_text) > 3000:
                    duplicates_text += f"... e altri {len(all_duplicates) - idx} gruppi\n"
                    break
            
            duplicates_text += f"💾 **Spazio sprecato:** {human_readable_size(total_wasted)}\n"
            duplicates_text += f"📊 **Gruppi duplicati:** {len(all_duplicates)}"
            
            await event.reply(duplicates_text)
            
        except Exception as e:
            self.logger.error(f"Errore ricerca duplicati: {e}")
            await event.reply(f"❌ Errore durante la ricerca duplicati: {str(e)}")