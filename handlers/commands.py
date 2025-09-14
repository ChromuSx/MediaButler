"""
Handler per comandi Telegram con menu interattivo inline
"""
import sys
import asyncio
from telethon import TelegramClient, events, Button
from core.auth import AuthManager
from core.space_manager import SpaceManager
from core.downloader import DownloadManager
from core.config import get_config
from utils.helpers import human_readable_size, FileHelpers


class CommandHandlers:
    """Gestione comandi bot con menu interattivo"""
    
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
        # Comandi principali
        self.client.on(events.NewMessage(pattern='/start'))(self.start_handler)
        self.client.on(events.NewMessage(pattern='/menu'))(self.menu_handler)
        self.client.on(events.NewMessage(pattern='/status'))(self.status_handler)
        self.client.on(events.NewMessage(pattern='/space'))(self.space_handler)
        self.client.on(events.NewMessage(pattern='/downloads'))(self.downloads_handler)
        self.client.on(events.NewMessage(pattern='/waiting'))(self.waiting_handler)
        self.client.on(events.NewMessage(pattern='/cancel_all'))(self.cancel_all_handler)
        self.client.on(events.NewMessage(pattern='/cancel'))(self.cancel_handler)
        self.client.on(events.NewMessage(pattern='/stop'))(self.stop_handler)
        self.client.on(events.NewMessage(pattern='/users'))(self.users_handler)
        self.client.on(events.NewMessage(pattern='/help'))(self.help_handler)
        self.client.on(events.NewMessage(pattern='/settings'))(self.settings_handler)
        
        # Callback handler per bottoni
        self.client.on(events.CallbackQuery(pattern='menu_'))(self.menu_callback_handler)
        self.client.on(events.CallbackQuery(pattern='cancel_'))(self.cancel_callback_handler)
        self.client.on(events.CallbackQuery(pattern='stop_'))(self.stop_callback_handler)
        
        self.logger.info("Handler comandi registrati con menu inline")
    
    def _create_main_menu(self, is_admin: bool = False):
        """Crea menu principale con bottoni inline"""
        buttons = [
            [
                Button.inline("📊 Stato", "menu_status"),
                Button.inline("💾 Spazio", "menu_space"),
                Button.inline("📥 Downloads", "menu_downloads")
            ],
            [
                Button.inline("⏳ In Attesa", "menu_waiting"),
                Button.inline("⚙️ Impostazioni", "menu_settings"),
                Button.inline("❓ Aiuto", "menu_help")
            ],
            [
                Button.inline("❌ Cancella Tutto", "menu_cancel_all"),
                Button.inline("🔄 Aggiorna", "menu_refresh")
            ]
        ]
        
        if is_admin:
            buttons.append([
                Button.inline("👥 Utenti", "menu_users"),
                Button.inline("🛑 Stop Bot", "menu_stop")
            ])
        
        return buttons
    
    def _create_quick_menu(self):
        """Crea menu rapido con azioni principali"""
        return [
            [
                Button.inline("📊 Stato", "menu_status"),
                Button.inline("📥 Downloads", "menu_downloads")
            ],
            [
                Button.inline("📱 Menu Completo", "menu_full")
            ]
        ]
    
    async def start_handler(self, event: events.NewMessage.Event):
        """Handler /start"""
        if not await self.auth.check_authorized(event):
            return
        
        user = await event.get_sender()
        self.logger.info(f"/start da {user.username} (ID: {user.id})")
        
        is_admin = self.auth.is_admin(user.id)
        
        # Messaggio di benvenuto
        welcome_text = self._format_welcome_message(user.id, is_admin)
        
        # Invia con menu inline
        await event.reply(
            welcome_text,
            buttons=self._create_main_menu(is_admin),
            link_preview=False
        )
    
    async def menu_handler(self, event: events.NewMessage.Event):
        """Handler /menu"""
        if not await self.auth.check_authorized(event):
            return
        
        is_admin = self.auth.is_admin(event.sender_id)
        
        await event.reply(
            "🎬 **MediaButler - Menu Principale**\n\n"
            "Seleziona un'opzione:",
            buttons=self._create_main_menu(is_admin)
        )
    
    async def status_handler(self, event: events.NewMessage.Event):
        """Handler /status"""
        if not await self.auth.check_authorized(event):
            return
        
        status_text = self._get_status_text()
        
        buttons = [
            [
                Button.inline("🔄 Aggiorna", "menu_status"),
                Button.inline("📱 Menu", "menu_back")
            ]
        ]
        
        await event.reply(status_text, buttons=buttons)
    
    async def space_handler(self, event: events.NewMessage.Event):
        """Handler /space"""
        if not await self.auth.check_authorized(event):
            return
        
        space_text = self.space.format_disk_status()
        
        buttons = [
            [
                Button.inline("🔄 Aggiorna", "menu_space"),
                Button.inline("📱 Menu", "menu_back")
            ]
        ]
        
        await event.reply(space_text, buttons=buttons)
    
    async def downloads_handler(self, event: events.NewMessage.Event):
        """Handler /downloads"""
        if not await self.auth.check_authorized(event):
            return
        
        downloads_text = self._get_downloads_detailed()
        
        buttons = [
            [
                Button.inline("🔄 Aggiorna", "menu_downloads"),
                Button.inline("❌ Cancella Tutti", "menu_cancel_all")
            ],
            [Button.inline("📱 Menu", "menu_back")]
        ]
        
        await event.reply(downloads_text, buttons=buttons)
    
    async def waiting_handler(self, event: events.NewMessage.Event):
        """Handler /waiting"""
        if not await self.auth.check_authorized(event):
            return
        
        waiting_text = self._get_waiting_text()
        
        buttons = [
            [
                Button.inline("🔄 Aggiorna", "menu_waiting"),
                Button.inline("📱 Menu", "menu_back")
            ]
        ]
        
        await event.reply(waiting_text, buttons=buttons)
    
    async def cancel_handler(self, event: events.NewMessage.Event):
        """Handler /cancel"""
        if not await self.auth.check_authorized(event):
            return
        
        active = self.downloads.get_active_downloads()
        
        if not active:
            await event.reply(
                "📭 **Nessun download attivo da cancellare**",
                buttons=[[Button.inline("📱 Menu", "menu_back")]]
            )
            return
        
        text = "**❌ Seleziona download da cancellare:**\n\n"
        buttons = []
        
        for idx, info in enumerate(active, 1):
            filename_short = info.filename[:30] + "..." if len(info.filename) > 30 else info.filename
            text += f"{idx}. `{filename_short}`\n"
            text += f"   {info.progress:.1f}% - {info.size_gb:.1f} GB\n\n"
            
            buttons.append([
                Button.inline(f"❌ Cancella #{idx}", f"cancel_{info.message_id}")
            ])
        
        buttons.append([
            Button.inline("❌ Cancella Tutti", "menu_cancel_all"),
            Button.inline("📱 Menu", "menu_back")
        ])
        
        await event.reply(text, buttons=buttons)
    
    async def cancel_all_handler(self, event: events.NewMessage.Event):
        """Handler /cancel_all"""
        if not await self.auth.check_authorized(event):
            return
        
        active = len(self.downloads.get_active_downloads())
        queued = self.downloads.get_queued_count()
        waiting = self.downloads.get_space_waiting_count()
        total = active + queued + waiting
        
        if total == 0:
            await event.reply(
                "✅ **Nessun download da cancellare**",
                buttons=[[Button.inline("📱 Menu", "menu_back")]]
            )
            return
        
        buttons = [
            [
                Button.inline("✅ Conferma", "cancel_confirm"),
                Button.inline("❌ Annulla", "menu_back")
            ]
        ]
        
        await event.reply(
            f"⚠️ **Conferma cancellazione**\n\n"
            f"Stai per cancellare:\n"
            f"• Download attivi: {active}\n"
            f"• In coda: {queued}\n"
            f"• In attesa: {waiting}\n\n"
            f"**Totale: {total} operazioni**\n\n"
            f"Confermi?",
            buttons=buttons
        )
    
    async def settings_handler(self, event: events.NewMessage.Event):
        """Handler /settings"""
        if not await self.auth.check_authorized(event):
            return
        
        settings_text = self._get_settings_text()
        
        buttons = [[Button.inline("📱 Menu", "menu_back")]]
        
        await event.reply(settings_text, buttons=buttons)
    
    async def help_handler(self, event: events.NewMessage.Event):
        """Handler /help"""
        if not await self.auth.check_authorized(event):
            return
        
        help_text = self._get_help_text()
        
        await event.reply(
            help_text,
            buttons=self._create_quick_menu()
        )
    
    async def users_handler(self, event: events.NewMessage.Event):
        """Handler /users (admin)"""
        if not await self.auth.check_authorized(event):
            return
        
        if not await self.auth.require_admin(event):
            return
        
        users_text = self._get_users_text()
        
        buttons = [[Button.inline("📱 Menu", "menu_back")]]
        
        await event.reply(users_text, buttons=buttons)
    
    async def stop_handler(self, event: events.NewMessage.Event):
        """Handler /stop (admin)"""
        if not await self.auth.check_authorized(event):
            return
        
        if not await self.auth.require_admin(event):
            return
        
        buttons = [
            [
                Button.inline("✅ Conferma Arresto", "stop_confirm"),
                Button.inline("❌ Annulla", "menu_back")
            ]
        ]
        
        await event.reply(
            "🛑 **Conferma Arresto Bot**\n\n"
            "⚠️ Questa azione:\n"
            "• Cancellerà tutti i download\n"
            "• Fermerà il bot\n"
            "• Richiederà riavvio manuale\n\n"
            "Confermi?",
            buttons=buttons
        )
    
    async def menu_callback_handler(self, event: events.CallbackQuery.Event):
        """Handler per callback menu"""
        if not await self.auth.check_callback_authorized(event):
            return
        
        action = event.data.decode('utf-8').replace('menu_', '')
        
        # Menu navigation
        if action == 'back' or action == 'full':
            is_admin = self.auth.is_admin(event.sender_id)
            await event.edit(
                "🎬 **MediaButler - Menu Principale**\n\n"
                "Seleziona un'opzione:",
                buttons=self._create_main_menu(is_admin)
            )
        elif action == 'refresh':
            is_admin = self.auth.is_admin(event.sender_id)
            await event.edit(
                "🎬 **MediaButler - Menu Principale**\n\n"
                "Seleziona un'opzione:",
                buttons=self._create_main_menu(is_admin)
            )
            await event.answer("✅ Menu aggiornato")
        else:
            await self._handle_menu_action(event, action)
    
    async def cancel_callback_handler(self, event: events.CallbackQuery.Event):
        """Handler per cancellazioni"""
        data = event.data.decode('utf-8')
        
        if data == 'cancel_confirm':
            total_cancelled = self.downloads.cancel_all_downloads()
            
            await event.edit(
                f"✅ **Cancellazione Completata**\n\n"
                f"Sono state cancellate {total_cancelled} operazioni.",
                buttons=[[Button.inline("📱 Menu", "menu_back")]]
            )
        else:
            # Cancella singolo download
            msg_id = int(data.replace('cancel_', ''))
            if self.downloads.cancel_download(msg_id):
                await event.answer("✅ Download cancellato")
                
                # Aggiorna lista
                downloads_text = self._get_downloads_detailed()
                buttons = [
                    [
                        Button.inline("🔄 Aggiorna", "menu_downloads"),
                        Button.inline("📱 Menu", "menu_back")
                    ]
                ]
                
                await event.edit(downloads_text, buttons=buttons)
            else:
                await event.answer("❌ Download non trovato", alert=True)
    
    async def stop_callback_handler(self, event: events.CallbackQuery.Event):
        """Handler per stop bot"""
        if event.data.decode('utf-8') == 'stop_confirm':
            if not self.auth.is_admin(event.sender_id):
                await event.answer("❌ Solo amministratori", alert=True)
                return
            
            await event.edit("🛑 **Arresto in corso...**")
            
            self.logger.info("Arresto richiesto dall'amministratore")
            self.downloads.cancel_all_downloads()
            
            await asyncio.sleep(2)
            await self.client.disconnect()
            sys.exit(0)
    
    async def _handle_menu_action(self, event, action: str):
        """Gestisce azioni menu"""
        content_map = {
            'status': self._get_status_text,
            'space': self.space.format_disk_status,
            'downloads': self._get_downloads_detailed,
            'waiting': self._get_waiting_text,
            'settings': self._get_settings_text,
            'help': self._get_help_text,
            'users': self._get_users_text,
            'cancel_all': self._get_cancel_confirmation
        }
        
        if action in content_map:
            content = content_map[action]()
            
            buttons = []
            
            # Bottoni specifici per ogni azione
            if action in ['status', 'space', 'downloads', 'waiting']:
                buttons.append([
                    Button.inline("🔄 Aggiorna", f"menu_{action}"),
                    Button.inline("📱 Menu", "menu_back")
                ])
            elif action == 'cancel_all':
                buttons = [
                    [
                        Button.inline("✅ Conferma", "cancel_confirm"),
                        Button.inline("❌ Annulla", "menu_back")
                    ]
                ]
            elif action == 'users':
                if not self.auth.is_admin(event.sender_id):
                    await event.answer("❌ Solo amministratori", alert=True)
                    return
                buttons = [[Button.inline("📱 Menu", "menu_back")]]
            elif action == 'stop':
                if not self.auth.is_admin(event.sender_id):
                    await event.answer("❌ Solo amministratori", alert=True)
                    return
                buttons = [
                    [
                        Button.inline("✅ Conferma Arresto", "stop_confirm"),
                        Button.inline("❌ Annulla", "menu_back")
                    ]
                ]
                content = "🛑 **Conferma Arresto Bot**\n\n⚠️ Questa azione:\n• Cancellerà tutti i download\n• Fermerà il bot\n• Richiederà riavvio manuale\n\nConfermi?"
            else:
                buttons = [[Button.inline("📱 Menu", "menu_back")]]
            
            await event.edit(content, buttons=buttons)
    
    # Funzioni helper per generare contenuti
    def _format_welcome_message(self, user_id: int, is_admin: bool) -> str:
        """Messaggio di benvenuto formattato"""
        disk_usage = self.space.get_all_disk_usage()
        total_free = sum(usage.free_gb for usage in disk_usage.values())
        
        active = len(self.downloads.get_active_downloads())
        queued = self.downloads.get_queued_count()
        
        tmdb_emoji = "🎯" if self.config.tmdb.is_enabled else "⚠️"
        tmdb_status = "TMDB Attivo" if self.config.tmdb.is_enabled else "TMDB Non configurato"
        
        role = "👑 Amministratore" if is_admin else "👤 Utente"
        
        # Lista comandi per accesso rapido
        commands_list = (
            "**📝 Comandi rapidi:**\n"
            "`/status` - Stato sistema\n"
            "`/downloads` - Download attivi\n"
            "`/space` - Spazio disco\n"
            "`/menu` - Menu completo\n"
            "`/help` - Aiuto"
        )
        
        if is_admin:
            commands_list += "\n`/users` - Gestione utenti\n`/stop` - Arresta bot"
        
        return (
            f"🎬 **MediaButler - Organizzatore Media**\n\n"
            f"Benvenuto! {role}\n"
            f"ID: `{user_id}`\n\n"
            f"**📊 Stato Sistema:**\n"
            f"• 💾 Spazio: {total_free:.1f} GB liberi\n"
            f"• 📥 Attivi: {active} download\n"
            f"• ⏳ In coda: {queued} file\n"
            f"• {tmdb_emoji} {tmdb_status}\n\n"
            f"**📤 Per iniziare:** Invia un file video\n\n"
            f"{commands_list}\n\n"
            f"**💡 Usa il menu sotto per navigare facilmente!**"
        )
    
    def _get_status_text(self) -> str:
        """Genera testo stato sistema"""
        status_text = "📊 **Stato Sistema**\n\n"
        
        active = self.downloads.get_active_downloads()
        if active:
            status_text += f"**📥 Download attivi ({len(active)}):**\n"
            for info in active[:5]:
                status_text += f"• `{info.filename[:30]}{'...' if len(info.filename) > 30 else ''}`\n"
                if info.progress > 0:
                    status_text += f"  {info.progress:.1f}% - {info.speed_mbps:.1f} MB/s\n"
            if len(active) > 5:
                status_text += f"  ...e altri {len(active) - 5}\n"
            status_text += "\n"
        else:
            status_text += "📭 Nessun download attivo\n\n"
        
        queue_count = self.downloads.get_queued_count()
        space_waiting = self.downloads.get_space_waiting_count()
        
        if queue_count > 0:
            status_text += f"⏳ **In coda:** {queue_count} file\n"
        if space_waiting > 0:
            status_text += f"⏸️ **In attesa spazio:** {space_waiting} file\n"
        
        status_text += "\n💾 **Spazio:**\n"
        disk_usage = self.space.get_all_disk_usage()
        
        for name, usage in disk_usage.items():
            status_text += f"{usage.status_emoji} {name.capitalize()}: {usage.free_gb:.1f} GB liberi\n"
        
        return status_text
    
    def _get_downloads_detailed(self) -> str:
        """Dettagli download attivi"""
        active = self.downloads.get_active_downloads()
        
        if not active:
            return (
                "📭 **Nessun download attivo**\n\n"
                "Invia un file video per iniziare."
            )
        
        text = f"📥 **Download Attivi ({len(active)})**\n\n"
        
        for idx, info in enumerate(active, 1):
            text += f"**{idx}. {info.filename[:35]}{'...' if len(info.filename) > 35 else ''}**\n"
            text += f"📏 {info.size_gb:.1f} GB | "
            text += f"👤 User {info.user_id}\n"
            
            if info.progress > 0:
                filled = int(info.progress / 10)
                bar = "█" * filled + "░" * (10 - filled)
                text += f"`[{bar}]` {info.progress:.1f}%\n"
                
                if info.speed_mbps > 0:
                    text += f"⚡ {info.speed_mbps:.1f} MB/s"
                
                if info.eta_seconds:
                    eta_min = info.eta_seconds // 60
                    text += f" | ⏱ {eta_min}m rimanenti"
                
                text += "\n"
            
            text += "\n"
        
        return text
    
    def _get_waiting_text(self) -> str:
        """Testo file in attesa"""
        waiting_count = self.downloads.get_space_waiting_count()
        
        if waiting_count == 0:
            return (
                "✅ **Nessun file in attesa**\n\n"
                "Tutti i download hanno spazio sufficiente."
            )
        
        text = f"⏳ **File in attesa di spazio ({waiting_count})**\n\n"
        
        for idx, item in enumerate(self.downloads.space_waiting_queue[:10], 1):
            info = item.download_info
            text += f"**{idx}.** `{info.filename[:35]}{'...' if len(info.filename) > 35 else ''}`\n"
            text += f"    📏 {info.size_gb:.1f} GB | 📂 {info.media_type.value}\n"
        
        if waiting_count > 10:
            text += f"\n...e altri {waiting_count - 10} file"
        
        return text
    
    def _get_settings_text(self) -> str:
        """Testo impostazioni"""
        tmdb_status = "✅ Attivo" if self.config.tmdb.is_enabled else "❌ Non configurato"
        
        return (
            "⚙️ **Impostazioni Correnti**\n\n"
            f"**Download:**\n"
            f"• Simultanei: {self.config.limits.max_concurrent_downloads}\n"
            f"• Max dimensione: {self.config.limits.max_file_size_gb} GB\n\n"
            f"**Spazio:**\n"
            f"• Minimo riservato: {self.config.limits.min_free_space_gb} GB\n"
            f"• Soglia avviso: {self.config.limits.warning_threshold_gb} GB\n"
            f"• Controllo ogni: {self.config.limits.space_check_interval}s\n\n"
            f"**TMDB:**\n"
            f"• Stato: {tmdb_status}\n"
            f"• Lingua: {self.config.tmdb.language}\n\n"
            f"**Percorsi:**\n"
            f"• Film: `{self.config.paths.movies}`\n"
            f"• Serie: `{self.config.paths.tv}`\n"
            f"• Temp: `{self.config.paths.temp}`\n\n"
            f"ℹ️ Modifica `.env` per cambiare."
        )
    
    def _get_help_text(self) -> str:
        """Testo aiuto"""
        return (
            "❓ **Guida MediaButler**\n\n"
            "**📥 Come usare:**\n"
            "1️⃣ Invia un file video\n"
            "2️⃣ Il bot riconosce il contenuto\n"
            "3️⃣ Conferma o scegli tipo\n"
            "4️⃣ Download automatico\n\n"
            "**📝 Comandi principali:**\n"
            "• `/menu` - Menu interattivo\n"
            "• `/status` - Stato rapido\n"
            "• `/downloads` - Download attivi\n"
            "• `/space` - Spazio disco\n"
            "• `/cancel` - Cancella download\n"
            "• `/help` - Questo aiuto\n\n"
            "**📁 Organizzazione:**\n"
            "• Film: `/movies/Nome (Anno)/`\n"
            "• Serie: `/tv/Serie/Season XX/`\n\n"
            "**💡 Suggerimenti:**\n"
            "• Nomi descrittivi = migliori risultati\n"
            "• Max 10GB per file\n"
            "• I download riprendono dopo riavvio\n\n"
            "Per assistenza, contatta l'admin."
        )
    
    def _get_users_text(self) -> str:
        """Testo gestione utenti"""
        users = self.auth.get_authorized_users()
        admin_id = self.auth.get_admin_id()
        
        text = f"👥 **Utenti Autorizzati ({len(users)})**\n\n"
        
        for idx, user_id in enumerate(users, 1):
            is_admin = " 👑 Admin" if user_id == admin_id else ""
            text += f"**{idx}.** `{user_id}`{is_admin}\n"
        
        text += (
            "\n📝 **Per modificare:**\n"
            "1. Modifica `AUTHORIZED_USERS` in `.env`\n"
            "2. Riavvia il bot\n\n"
            "Il primo utente è sempre admin."
        )
        
        return text
    
    def _get_cancel_confirmation(self) -> str:
        """Testo conferma cancellazione"""
        active = len(self.downloads.get_active_downloads())
        queued = self.downloads.get_queued_count()
        waiting = self.downloads.get_space_waiting_count()
        total = active + queued + waiting
        
        if total == 0:
            return "✅ **Nessun download da cancellare**"
        
        return (
            f"⚠️ **Conferma Cancellazione**\n\n"
            f"Stai per cancellare:\n"
            f"• Download attivi: {active}\n"
            f"• In coda: {queued}\n"
            f"• In attesa: {waiting}\n\n"
            f"**Totale: {total} operazioni**\n\n"
            f"Sei sicuro?"
        )