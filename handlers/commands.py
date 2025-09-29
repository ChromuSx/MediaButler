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
from core.i18n import get_i18n, t
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
        self.i18n = get_i18n()
    
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
        self.client.on(events.NewMessage(pattern='/subtitles'))(self.subtitles_handler)
        self.client.on(events.NewMessage(pattern='/sub_toggle'))(self.subtitle_toggle_handler)
        self.client.on(events.NewMessage(pattern='/sub_auto'))(self.subtitle_auto_handler)
        self.client.on(events.NewMessage(pattern='/language'))(self.language_handler)

        # Callback handler per bottoni
        self.client.on(events.CallbackQuery(pattern='menu_'))(self.menu_callback_handler)
        self.client.on(events.CallbackQuery(pattern='cancel_'))(self.cancel_callback_handler)
        self.client.on(events.CallbackQuery(pattern='stop_'))(self.stop_callback_handler)
        self.client.on(events.CallbackQuery(pattern='sub_'))(self.subtitle_callback_handler)
        self.client.on(events.CallbackQuery(pattern='lang_'))(self.language_callback_handler)
        
        self.logger.info("Handler comandi registrati con menu inline")
    
    def _create_main_menu(self, is_admin: bool = False, user_id: int = None):
        """Crea menu principale con bottoni inline"""
        buttons = [
            [
                Button.inline(t("commands.menu.main_buttons.status", user_id), "menu_status"),
                Button.inline(t("commands.menu.main_buttons.space", user_id), "menu_space"),
                Button.inline(t("commands.menu.main_buttons.downloads", user_id), "menu_downloads")
            ],
            [
                Button.inline(t("commands.menu.main_buttons.waiting", user_id), "menu_waiting"),
                Button.inline(t("commands.menu.main_buttons.subtitles", user_id), "menu_subtitles"),
                Button.inline(t("commands.menu.main_buttons.settings", user_id), "menu_settings")
            ],
            [
                Button.inline(t("commands.menu.main_buttons.help", user_id), "menu_help"),
                Button.inline(t("commands.menu.main_buttons.language", user_id), "menu_language"),
                Button.inline(t("commands.menu.main_buttons.cancel_all", user_id), "menu_cancel_all")
            ]
        ]
        
        if is_admin:
            buttons.append([
                Button.inline(t("commands.menu.main_buttons.users", user_id), "menu_users"),
                Button.inline(t("commands.menu.main_buttons.stop", user_id), "menu_stop")
            ])
        
        return buttons
    
    def _create_quick_menu(self, user_id: int = None):
        """Crea menu rapido con azioni principali"""
        return [
            [
                Button.inline(t("commands.menu.quick_buttons.status", user_id), "menu_status"),
                Button.inline(t("commands.menu.quick_buttons.downloads", user_id), "menu_downloads")
            ],
            [
                Button.inline(t("commands.menu.quick_buttons.full_menu", user_id), "menu_full")
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
            buttons=self._create_main_menu(is_admin, user.id),
            link_preview=False
        )
    
    async def menu_handler(self, event: events.NewMessage.Event):
        """Handler /menu"""
        if not await self.auth.check_authorized(event):
            return
        
        user_id = event.sender_id
        is_admin = self.auth.is_admin(user_id)
        
        await event.reply(
            t("commands.menu.title", user_id),
            buttons=self._create_main_menu(is_admin, user_id)
        )
    
    async def status_handler(self, event: events.NewMessage.Event):
        """Handler /status"""
        if not await self.auth.check_authorized(event):
            return
        
        user_id = event.sender_id
        status_text = self._get_status_text(user_id)
        
        buttons = [
            [
                Button.inline(t("buttons.refresh", user_id), "menu_status"),
                Button.inline(t("buttons.menu", user_id), "menu_back")
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
        
        user_id = event.sender_id
        downloads_text = self._get_downloads_detailed(user_id)
        
        buttons = [
            [
                Button.inline(t("buttons.refresh", user_id), "menu_downloads"),
                Button.inline(t("commands.menu.main_buttons.cancel_all", user_id), "menu_cancel_all")
            ],
            [Button.inline(t("buttons.menu", user_id), "menu_back")]
        ]
        
        await event.reply(downloads_text, buttons=buttons)
    
    async def waiting_handler(self, event: events.NewMessage.Event):
        """Handler /waiting"""
        if not await self.auth.check_authorized(event):
            return
        
        user_id = event.sender_id
        waiting_text = self._get_waiting_text(user_id)
        
        buttons = [
            [
                Button.inline(t("buttons.refresh", user_id), "menu_waiting"),
                Button.inline(t("buttons.menu", user_id), "menu_back")
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
        
        user_id = event.sender_id
        settings_text = self._get_settings_text(user_id)
        
        buttons = [[Button.inline(t("buttons.menu", user_id), "menu_back")]]
        
        await event.reply(settings_text, buttons=buttons)
    
    async def help_handler(self, event: events.NewMessage.Event):
        """Handler /help"""
        if not await self.auth.check_authorized(event):
            return
        
        user_id = event.sender_id
        help_text = self._get_help_text(user_id)
        
        await event.reply(
            help_text,
            buttons=self._create_quick_menu(user_id)
        )
    
    async def users_handler(self, event: events.NewMessage.Event):
        """Handler /users (admin)"""
        if not await self.auth.check_authorized(event):
            return
        
        if not await self.auth.require_admin(event):
            return
        
        user_id = event.sender_id
        users_text = self._get_users_text(user_id)
        
        buttons = [[Button.inline(t("buttons.menu", user_id), "menu_back")]]
        
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
        user_id = event.sender_id
        
        # Gestione azione lingua
        if action == 'language':
            current_lang = self.i18n.get_locale_info(self.i18n.get_user_locale(user_id))
            title = t("commands.language.title", user_id)
            current_info = t("commands.language.current", user_id, 
                            language=f"{current_lang.emoji} {current_lang.name}")
            
            await event.edit(
                f"{title}\n\n{current_info}",
                buttons=self.i18n.create_language_menu_buttons(user_id)
            )
            return
        
        # Gestione menu principale
        if action == 'back' or action == 'full':
            is_admin = self.auth.is_admin(user_id)
            await event.edit(
                t("commands.menu.title", user_id),
                buttons=self._create_main_menu(is_admin, user_id)
            )
            return
        
        content_map = {
            'status': lambda: self._get_status_text(user_id),
            'space': self.space.format_disk_status,
            'downloads': lambda: self._get_downloads_detailed(user_id),
            'waiting': lambda: self._get_waiting_text(user_id),
            'subtitles': lambda: self._get_subtitle_status(user_id),
            'settings': lambda: self._get_settings_text(user_id),
            'help': lambda: self._get_help_text(user_id),
            'users': lambda: self._get_users_text(user_id),
            'cancel_all': lambda: self._get_cancel_confirmation(user_id)
        }
        
        if action in content_map:
            content = content_map[action]()
            
            buttons = []
            
            # Bottoni specifici per ogni azione
            if action in ['status', 'space', 'downloads', 'waiting']:
                buttons.append([
                    Button.inline(t("buttons.refresh", user_id), f"menu_{action}"),
                    Button.inline(t("buttons.menu", user_id), "menu_back")
                ])
            elif action == 'subtitles':
                buttons = self._create_subtitle_menu(user_id)
            elif action == 'cancel_all':
                buttons = [
                    [
                        Button.inline(t("buttons.confirm", user_id), "cancel_confirm"),
                        Button.inline(t("buttons.cancel", user_id), "menu_back")
                    ]
                ]
            elif action == 'users':
                if not self.auth.is_admin(event.sender_id):
                    await event.answer(t("messages.admin_only_action", user_id), alert=True)
                    return
                buttons = [[Button.inline(t("buttons.menu", user_id), "menu_back")]]
            elif action == 'stop':
                if not self.auth.is_admin(event.sender_id):
                    await event.answer(t("messages.admin_only_action", user_id), alert=True)
                    return
                buttons = [
                    [
                        Button.inline(t("confirmations.stop_bot.button_confirm", user_id), "stop_confirm"),
                        Button.inline(t("buttons.cancel", user_id), "menu_back")
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
        tmdb_status = t("messages.tmdb_active", user_id) if self.config.tmdb.is_enabled else t("messages.tmdb_disabled", user_id)
        
        role = t("commands.start.role_admin", user_id) if is_admin else t("commands.start.role_user", user_id)
        
        # Lista comandi per accesso rapido
        commands_list = t("commands.start.commands_rapid", user_id)
        
        if is_admin:
            commands_list += t("commands.start.commands_admin", user_id)
        
        return t("commands.start.welcome", user_id,
               role=role,
               total_free=f"{total_free:.1f}",
               active=active,
               queued=queued,
               tmdb_emoji=tmdb_emoji,
               tmdb_status=tmdb_status,
               commands_list=commands_list)
    
    def _get_status_text(self, user_id: int = None) -> str:
        """Genera testo stato sistema"""
        status_text = t("commands.status.title", user_id) + "\n\n"
        
        active = self.downloads.get_active_downloads()
        if active:
            status_text += t("commands.status.downloads_active", user_id, count=len(active)) + "\n"
            for info in active[:5]:
                status_text += f"• `{info.filename[:30]}{'...' if len(info.filename) > 30 else ''}`\n"
                if info.progress > 0:
                    status_text += f"  {info.progress:.1f}% - {info.speed_mbps:.1f} MB/s\n"
            if len(active) > 5:
                status_text += t("commands.status.downloads_more", user_id, count=len(active) - 5) + "\n"
            status_text += "\n"
        else:
            status_text += t("commands.status.downloads_none", user_id) + "\n\n"
        
        queue_count = self.downloads.get_queued_count()
        space_waiting = self.downloads.get_space_waiting_count()
        
        if queue_count > 0:
            status_text += t("commands.status.queue_pending", user_id, count=queue_count) + "\n"
        if space_waiting > 0:
            status_text += t("commands.status.queue_waiting_space", user_id, count=space_waiting) + "\n"
        
        status_text += "\n" + t("commands.status.disk_space", user_id) + "\n"
        disk_usage = self.space.get_all_disk_usage()
        
        for name, usage in disk_usage.items():
            status_text += f"{usage.status_emoji} {name.capitalize()}: {usage.free_gb:.1f} GB liberi\n"
        
        return status_text
    
    def _get_downloads_detailed(self, user_id: int = None) -> str:
        """Dettagli download attivi"""
        active = self.downloads.get_active_downloads()
        
        if not active:
            return (
                t("commands.downloads.none", user_id) + "\n\n" +
                t("messages.send_video", user_id)
            )
        
        text = t("commands.downloads.title", user_id) + f" ({len(active)})\n\n"
        
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
    
    def _get_waiting_text(self, user_id: int = None) -> str:
        """Testo file in attesa"""
        waiting_count = self.downloads.get_space_waiting_count()
        
        if waiting_count == 0:
            return t("commands.waiting.none", user_id)
        
        text = t("commands.waiting.title", user_id) + f" ({waiting_count})\n\n"
        
        for idx, item in enumerate(self.downloads.space_waiting_queue[:10], 1):
            info = item.download_info
            filename_display = info.filename[:35] + '...' if len(info.filename) > 35 else info.filename
            text += f"**{idx}.** `{filename_display}`\n"
            text += f"    📏 {info.size_gb:.1f} GB | 📂 {info.media_type.value}\n"
        
        if waiting_count > 10:
            text += "\n" + t("commands.waiting.more", user_id, count=waiting_count - 10)
        
        return text
    
    def _get_settings_text(self, user_id: int = None) -> str:
        """Testo impostazioni"""
        tmdb_status = t("commands.settings.tmdb_status_active", user_id) if self.config.tmdb.is_enabled else t("commands.settings.tmdb_status_disabled", user_id)
        
        return (
            t("commands.settings.title", user_id) + "\n\n" +
            t("commands.settings.downloads", user_id) + "\n" +
            t("commands.settings.concurrent", user_id, count=self.config.limits.max_concurrent_downloads) + "\n" +
            t("commands.settings.max_size", user_id, size=self.config.limits.max_file_size_gb) + "\n\n" +
            t("commands.settings.space_section", user_id) + "\n" +
            t("commands.settings.min_free", user_id, size=self.config.limits.min_free_space_gb) + "\n" +
            t("commands.settings.warning_threshold", user_id, size=self.config.limits.warning_threshold_gb) + "\n" +
            t("commands.settings.check_interval", user_id, seconds=self.config.limits.space_check_interval) + "\n\n" +
            t("commands.settings.tmdb_section", user_id) + "\n" +
            f"• {t('commands.settings.tmdb_status_active' if self.config.tmdb.is_enabled else 'commands.settings.tmdb_status_disabled', user_id)}\n" +
            t("commands.settings.tmdb_language", user_id, language=self.config.tmdb.language) + "\n\n" +
            t("commands.settings.paths_section", user_id) + "\n" +
            t("commands.settings.path_movies", user_id, path=str(self.config.paths.movies)) + "\n" +
            t("commands.settings.path_tv", user_id, path=str(self.config.paths.tv)) + "\n" +
            t("commands.settings.path_temp", user_id, path=str(self.config.paths.temp)) + "\n\n" +
            t("commands.settings.note", user_id)
        )
    
    def _get_help_text(self, user_id: int = None) -> str:
        """Testo aiuto"""
        return (
            t("commands.help.title", user_id) + "\n\n" +
            t("commands.help.usage", user_id) + "\n" +
            t("commands.help.step1", user_id) + "\n" +
            t("commands.help.step2", user_id) + "\n" +
            t("commands.help.step3", user_id) + "\n" +
            t("commands.help.step4", user_id) + "\n\n" +
            t("commands.help.commands", user_id) + "\n" +
            t("commands.help.cmd_menu", user_id) + "\n" +
            t("commands.help.cmd_status", user_id) + "\n" +
            t("commands.help.cmd_downloads", user_id) + "\n" +
            t("commands.help.cmd_space", user_id) + "\n" +
            t("commands.help.cmd_cancel", user_id) + "\n" +
            t("commands.help.cmd_help", user_id) + "\n\n" +
            t("commands.help.organization", user_id) + "\n" +
            t("commands.help.org_movies", user_id) + "\n" +
            t("commands.help.org_tv", user_id) + "\n\n" +
            t("commands.help.tips", user_id) + "\n" +
            t("commands.help.tip1", user_id) + "\n" +
            t("commands.help.tip2", user_id) + "\n" +
            t("commands.help.tip3", user_id) + "\n\n" +
            t("commands.help.support", user_id)
        )
    
    def _get_users_text(self, user_id: int = None) -> str:
        """Testo gestione utenti"""
        users = self.auth.get_authorized_users()
        admin_id = self.auth.get_admin_id()
        
        text = t("commands.users.title", user_id, count=len(users)) + "\n\n"
        
        for idx, user_id_item in enumerate(users, 1):
            is_admin = t("commands.users.admin_marker", user_id) if user_id_item == admin_id else ""
            text += f"**{idx}.** `{user_id_item}`{is_admin}\n"
        
        text += "\n" + t("commands.users.modify_instructions", user_id)
        
        return text
    
    def _get_cancel_confirmation(self, user_id: int = None) -> str:
        """Testo conferma cancellazione"""
        active = len(self.downloads.get_active_downloads())
        queued = self.downloads.get_queued_count()
        waiting = self.downloads.get_space_waiting_count()
        total = active + queued + waiting
        
        if total == 0:
            return t("confirmations.cancel_all.no_downloads", user_id)
        
        return t("confirmations.cancel_all.message", user_id, 
                active=active, queued=queued, total=total)

    async def subtitles_handler(self, event):
        """Handler comando /subtitles"""
        if not await self.auth.check_authorized(event):
            return

        await event.reply(
            self._get_subtitle_status(event.sender_id),
            buttons=self._create_subtitle_menu(event.sender_id)
        )

    async def subtitle_toggle_handler(self, event):
        """Handler comando /sub_toggle - abilita/disabilita sottotitoli"""
        if not await self.auth.check_authorized(event):
            return

        user_id = event.sender_id
        await event.reply(
            t("commands.subtitles.config.toggle_instructions", user_id)
        )

    async def subtitle_auto_handler(self, event):
        """Handler comando /sub_auto - toggle download automatico"""
        if not await self.auth.check_authorized(event):
            return

        user_id = event.sender_id
        await event.reply(
            t("commands.subtitles.config.auto_instructions", user_id)
        )

    async def subtitle_callback_handler(self, event):
        """Handler callback bottoni sottotitoli"""
        if not await self.auth.check_authorized(event):
            await event.answer(t("messages.unauthorized", event.sender_id))
            return

        try:
            user_id = event.sender_id
            data = event.data.decode('utf-8')

            if data == "sub_status":
                await event.edit(
                    self._get_subtitle_status(user_id),
                    buttons=self._create_subtitle_menu(user_id)
                )

            elif data == "sub_config":
                await event.edit(
                    t("commands.subtitles.config.full_instructions", user_id),
                    buttons=[[Button.inline(t("buttons.back", user_id), "sub_status")]]
                )

            elif data == "sub_back_main":
                is_admin = self.auth.is_admin(user_id)
                await event.edit(
                    t("commands.menu.title", user_id),
                    buttons=self._create_main_menu(is_admin, user_id)
                )

            await event.answer()

        except Exception as e:
            self.logger.error(f"Errore callback sottotitoli: {e}")
            await event.answer(t("errors.generic", event.sender_id))

    def _get_subtitle_status(self, user_id: int = None) -> str:
        """Ottieni stato sistema sottotitoli"""
        config = self.config.subtitles

        status_text = t("commands.subtitles.status_enabled", user_id) if config.enabled else t("commands.subtitles.status_disabled", user_id)
        auto_text = t("commands.subtitles.auto_enabled", user_id) if config.auto_download else t("commands.subtitles.auto_disabled", user_id)
        opensubtitles_text = t("commands.subtitles.opensubtitles_configured", user_id) if config.is_opensubtitles_configured else t("commands.subtitles.opensubtitles_missing", user_id)

        return (
            t("commands.subtitles.title", user_id) + "\n\n" +
            status_text + "\n" +
            auto_text + "\n" +
            t("commands.subtitles.languages", user_id, languages=', '.join(config.languages)) + "\n" +
            t("commands.subtitles.format", user_id, format=config.preferred_format) + "\n" +
            opensubtitles_text + "\n\n" +
            f"User Agent: `{config.opensubtitles_user_agent}`" + "\n\n" +
            t("commands.subtitles.note", user_id)
        )

    def _create_subtitle_menu(self, user_id: int = None):
        """Crea menu sottotitoli"""
        return [
            [
                Button.inline(t("commands.subtitles.menu_buttons.refresh", user_id), "sub_status"),
                Button.inline(t("commands.subtitles.menu_buttons.config", user_id), "sub_config")
            ],
            [
                Button.inline(t("buttons.back", user_id), "menu_back")
            ]
        ]
    
    async def language_handler(self, event: events.NewMessage.Event):
        """Handler /language"""
        if not await self.auth.check_authorized(event):
            return
        
        user_id = event.sender_id
        current_lang = self.i18n.get_locale_info(self.i18n.get_user_locale(user_id))
        
        title = t("commands.language.title", user_id)
        current_info = t("commands.language.current", user_id, 
                        language=f"{current_lang.emoji} {current_lang.name}")
        
        await event.reply(
            f"{title}\n\n{current_info}",
            buttons=self.i18n.create_language_menu_buttons(user_id)
        )
    
    async def language_callback_handler(self, event: events.CallbackQuery.Event):
        """Handler callback selezione lingua"""
        if not await self.auth.check_authorized(event):
            return
        
        # Estrai codice lingua dal callback data
        lang_code = event.data.decode().replace('lang_', '')
        user_id = event.sender_id
        
        if lang_code in self.i18n.SUPPORTED_LOCALES:
            # Imposta nuova lingua per l'utente
            self.i18n.set_user_locale(user_id, lang_code)
            
            # Ottieni info lingua
            lang_info = self.i18n.get_locale_info(lang_code)
            
            # Messaggio di conferma
            success_msg = t("commands.language.changed", user_id,
                          language=f"{lang_info.emoji} {lang_info.name}")
            
            await event.edit(
                success_msg,
                buttons=[[Button.inline(t("buttons.menu", user_id), "menu_back")]]
            )
        else:
            await event.answer("❌ Lingua non supportata")
        
        await event.answer()
    