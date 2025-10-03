"""
Telegram command handlers with interactive inline menu
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
    """Bot command management with interactive menu"""
    
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
        """Register all command handlers"""
        # Main commands
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

        # Callback handler for buttons
        self.client.on(events.CallbackQuery(pattern='menu_'))(self.menu_callback_handler)
        self.client.on(events.CallbackQuery(pattern='cancel_'))(self.cancel_callback_handler)
        self.client.on(events.CallbackQuery(pattern='stop_'))(self.stop_callback_handler)
        self.client.on(events.CallbackQuery(pattern='sub_'))(self.subtitle_callback_handler)
        
        self.logger.info("Command handlers registered with inline menu")
    
    def _create_main_menu(self, is_admin: bool = False):
        """Create main menu with inline buttons"""
        buttons = [
            [
                Button.inline("📊 Status", "menu_status"),
                Button.inline("💾 Space", "menu_space"),
                Button.inline("📥 Downloads", "menu_downloads")
            ],
            [
                Button.inline("⏳ Waiting", "menu_waiting"),
                Button.inline("📝 Subtitles", "menu_subtitles"),
                Button.inline("⚙️ Settings", "menu_settings")
            ],
            [
                Button.inline("❓ Help", "menu_help"),
                Button.inline("❌ Cancel All", "menu_cancel_all")
            ]
        ]
        
        if is_admin:
            buttons.append([
                Button.inline("👥 Users", "menu_users"),
                Button.inline("🛑 Stop Bot", "menu_stop")
            ])
        
        return buttons
    
    def _create_quick_menu(self):
        """Create quick menu with main actions"""
        return [
            [
                Button.inline("📊 Status", "menu_status"),
                Button.inline("📥 Downloads", "menu_downloads")
            ],
            [
                Button.inline("📱 Full Menu", "menu_full")
            ]
        ]
    
    async def start_handler(self, event: events.NewMessage.Event):
        """Handler /start"""
        if not await self.auth.check_authorized(event):
            return
        
        user = await event.get_sender()
        self.logger.info(f"/start da {user.username} (ID: {user.id})")
        
        is_admin = self.auth.is_admin(user.id)
        
        # Welcome message
        welcome_text = self._format_welcome_message(user.id, is_admin)
        
        # Send with inline menu
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
            "🎬 **MediaButler - Main Menu**\n\n"
            "Select an option:",
            buttons=self._create_main_menu(is_admin)
        )
    
    async def status_handler(self, event: events.NewMessage.Event):
        """Handler /status"""
        if not await self.auth.check_authorized(event):
            return
        
        status_text = self._get_status_text()
        
        buttons = [
            [
                Button.inline("🔄 Refresh", "menu_status"),
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
                Button.inline("🔄 Refresh", "menu_space"),
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
                Button.inline("🔄 Refresh", "menu_downloads"),
                Button.inline("❌ Cancel All", "menu_cancel_all")
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
                Button.inline("🔄 Refresh", "menu_waiting"),
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
                "📭 **No active downloads to cancel**",
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
                Button.inline(f"❌ Cancel #{idx}", f"cancel_{info.message_id}")
            ])
        
        buttons.append([
            Button.inline("❌ Cancel All", "menu_cancel_all"),
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
                "✅ **No downloads to cancel**",
                buttons=[[Button.inline("📱 Menu", "menu_back")]]
            )
            return
        
        buttons = [
            [
                Button.inline("✅ Confirm", "cancel_confirm"),
                Button.inline("❌ Cancel", "menu_back")
            ]
        ]
        
        await event.reply(
            f"⚠️ **Confirm cancellation**\n\n"
            f"Stai per cancellare:\n"
            f"• Download attivi: {active}\n"
            f"• In coda: {queued}\n"
            f"• Waiting: {waiting}\n\n"
            f"**Totale: {total} operations**\n\n"
            f"Confirm?",
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
                Button.inline("✅ Confirm Stop", "stop_confirm"),
                Button.inline("❌ Cancel", "menu_back")
            ]
        ]
        
        await event.reply(
            "🛑 **Confirm Bot Stop**\n\n"
            "⚠️ This action:\n"
            "• Will cancel all downloads\n"
            "• Will stop the bot\n"
            "• Will require manual restart\n\n"
            "Confirm?",
            buttons=buttons
        )
    
    async def menu_callback_handler(self, event: events.CallbackQuery.Event):
        """Handler for menu callbacks"""
        if not await self.auth.check_callback_authorized(event):
            return
        
        action = event.data.decode('utf-8').replace('menu_', '')
        
        # Menu navigation
        if action == 'back' or action == 'full':
            is_admin = self.auth.is_admin(event.sender_id)
            await event.edit(
                "🎬 **MediaButler - Main Menu**\n\n"
                "Select an option:",
                buttons=self._create_main_menu(is_admin)
            )
        elif action == 'refresh':
            is_admin = self.auth.is_admin(event.sender_id)
            await event.edit(
                "🎬 **MediaButler - Main Menu**\n\n"
                "Select an option:",
                buttons=self._create_main_menu(is_admin)
            )
            await event.answer("✅ Menu updated")
        else:
            await self._handle_menu_action(event, action)
    
    async def cancel_callback_handler(self, event: events.CallbackQuery.Event):
        """Handler for cancellations"""
        data = event.data.decode('utf-8')
        
        if data == 'cancel_confirm':
            total_cancelled = self.downloads.cancel_all_downloads()
            
            await event.edit(
                f"✅ **Cancellation Completed**\n\n"
                f"Cancelled {total_cancelled} operations.",
                buttons=[[Button.inline("📱 Menu", "menu_back")]]
            )
        else:
            # Cancella singolo download
            msg_id = int(data.replace('cancel_', ''))
            if self.downloads.cancel_download(msg_id):
                await event.answer("✅ Download canceled")
                
                # Update list
                downloads_text = self._get_downloads_detailed()
                buttons = [
                    [
                        Button.inline("🔄 Aggiorna", "menu_downloads"),
                        Button.inline("📱 Menu", "menu_back")
                    ]
                ]
                
                await event.edit(downloads_text, buttons=buttons)
            else:
                await event.answer("❌ Download not found", alert=True)
    
    async def stop_callback_handler(self, event: events.CallbackQuery.Event):
        """Handler for bot stop"""
        if event.data.decode('utf-8') == 'stop_confirm':
            if not self.auth.is_admin(event.sender_id):
                await event.answer("❌ Administrators only", alert=True)
                return
            
            await event.edit("🛑 **Stopping...**")
            
            self.logger.info("Stop requested by administrator")
            self.downloads.cancel_all_downloads()
            
            await asyncio.sleep(2)
            await self.client.disconnect()
            sys.exit(0)
    
    async def _handle_menu_action(self, event, action: str):
        """Handles menu actions"""
        content_map = {
            'status': self._get_status_text,
            'space': self.space.format_disk_status,
            'downloads': self._get_downloads_detailed,
            'waiting': self._get_waiting_text,
            'subtitles': self._get_subtitle_status,
            'settings': self._get_settings_text,
            'help': self._get_help_text,
            'users': self._get_users_text,
            'cancel_all': self._get_cancel_confirmation
        }
        
        if action in content_map:
            content = content_map[action]()
            
            buttons = []
            
            # Specific buttons for each action
            if action in ['status', 'space', 'downloads', 'waiting']:
                buttons.append([
                    Button.inline("🔄 Refresh", f"menu_{action}"),
                    Button.inline("📱 Menu", "menu_back")
                ])
            elif action == 'subtitles':
                buttons = self._create_subtitle_menu()
            elif action == 'cancel_all':
                buttons = [
                    [
                        Button.inline("✅ Conferma", "cancel_confirm"),
                        Button.inline("❌ Annulla", "menu_back")
                    ]
                ]
            elif action == 'users':
                if not self.auth.is_admin(event.sender_id):
                    await event.answer("❌ Administrators only", alert=True)
                    return
                buttons = [[Button.inline("📱 Menu", "menu_back")]]
            elif action == 'stop':
                if not self.auth.is_admin(event.sender_id):
                    await event.answer("❌ Administrators only", alert=True)
                    return
                buttons = [
                    [
                        Button.inline("✅ Confirm Stop", "stop_confirm"),
                        Button.inline("❌ Annulla", "menu_back")
                    ]
                ]
                content = "🛑 **Confirm Bot Stop**\n\n⚠️ This action:\n• Will cancel all downloads\n• Will stop the bot\n• Will require manual restart\n\nConfirm?"
            else:
                buttons = [[Button.inline("📱 Menu", "menu_back")]]
            
            await event.edit(content, buttons=buttons)
    
    # Helper functions to generate content
    def _format_welcome_message(self, user_id: int, is_admin: bool) -> str:
        """Formatted welcome message"""
        disk_usage = self.space.get_all_disk_usage()
        total_free = sum(usage.free_gb for usage in disk_usage.values())
        
        active = len(self.downloads.get_active_downloads())
        queued = self.downloads.get_queued_count()
        
        tmdb_emoji = "🎯" if self.config.tmdb.is_enabled else "⚠️"
        tmdb_status = "TMDB Active" if self.config.tmdb.is_enabled else "TMDB Not configured"
        
        role = "👑 Administrator" if is_admin else "👤 User"
        
        # Quick access command list
        commands_list = (
            "**📝 Quick commands:**\n"
            "`/status` - System status\n"
            "`/downloads` - Active downloads\n"
            "`/space` - Disk space\n"
            "`/menu` - Full menu\n"
            "`/help` - Help"
        )
        
        if is_admin:
            commands_list += "\n`/users` - User management\n`/stop` - Stop bot"
        
        return (
            f"🎬 **MediaButler - Media Organizer**\n\n"
            f"Welcome! {role}\n"
            f"ID: `{user_id}`\n\n"
            f"**📊 System Status:**\n"
            f"• 💾 Space: {total_free:.1f} GB free\n"
            f"• 📥 Active: {active} downloads\n"
            f"• ⏳ Queued: {queued} files\n"
            f"• {tmdb_emoji} {tmdb_status}\n\n"
            f"**📤 To start:** Send a video file\n\n"
            f"{commands_list}\n\n"
            f"**💡 Use the menu below to navigate easily!**"
        )
    
    def _get_status_text(self) -> str:
        """Generate system status text"""
        status_text = "📊 **System Status**\n\n"
        
        active = self.downloads.get_active_downloads()
        if active:
            status_text += f"**📥 Active downloads ({len(active)}):**\n"
            for info in active[:5]:
                status_text += f"• `{info.filename[:30]}{'...' if len(info.filename) > 30 else ''}`\n"
                if info.progress > 0:
                    status_text += f"  {info.progress:.1f}% - {info.speed_mbps:.1f} MB/s\n"
            if len(active) > 5:
                status_text += f"  ...and {len(active) - 5} more\n"
            status_text += "\n"
        else:
            status_text += "📭 No active downloads\n\n"
        
        queue_count = self.downloads.get_queued_count()
        space_waiting = self.downloads.get_space_waiting_count()
        
        if queue_count > 0:
            status_text += f"⏳ **Queued:** {queue_count} files\n"
        if space_waiting > 0:
            status_text += f"⏸️ **Waiting for space:** {space_waiting} files\n"
        
        status_text += "\n💾 **Space:**\n"
        disk_usage = self.space.get_all_disk_usage()
        
        for name, usage in disk_usage.items():
            status_text += f"{usage.status_emoji} {name.capitalize()}: {usage.free_gb:.1f} GB free\n"
        
        return status_text
    
    def _get_downloads_detailed(self) -> str:
        """Active downloads details"""
        active = self.downloads.get_active_downloads()
        
        if not active:
            return (
                "📭 **No active downloads**\n\n"
                "Send a video file to start."
            )
        
        text = f"📥 **Active Downloads ({len(active)})**\n\n"
        
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
                    text += f" | ⏱ {eta_min}m remaining"
                
                text += "\n"
            
            text += "\n"
        
        return text
    
    def _get_waiting_text(self) -> str:
        """Waiting files text"""
        waiting_count = self.downloads.get_space_waiting_count()
        
        if waiting_count == 0:
            return (
                "✅ **No files waiting**\n\n"
                "All downloads have sufficient space."
            )
        
        text = f"⏳ **Files waiting for space ({waiting_count})**\n\n"
        
        for idx, item in enumerate(self.downloads.space_waiting_queue[:10], 1):
            info = item.download_info
            text += f"**{idx}.** `{info.filename[:35]}{'...' if len(info.filename) > 35 else ''}`\n"
            text += f"    📏 {info.size_gb:.1f} GB | 📂 {info.media_type.value}\n"
        
        if waiting_count > 10:
            text += f"\n...e altri {waiting_count - 10} file"
        
        return text
    
    def _get_settings_text(self) -> str:
        """Settings text"""
        tmdb_status = "✅ Active" if self.config.tmdb.is_enabled else "❌ Not configured"
        
        return (
            "⚙️ **Current Settings**\n\n"
            f"**Download:**\n"
            f"• Concurrent: {self.config.limits.max_concurrent_downloads}\n"
            f"• Max size: {self.config.limits.max_file_size_gb} GB\n\n"
            f"**Spazio:**\n"
            f"• Minimum reserved: {self.config.limits.min_free_space_gb} GB\n"
            f"• Warning threshold: {self.config.limits.warning_threshold_gb} GB\n"
            f"• Check every: {self.config.limits.space_check_interval}s\n\n"
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
        """Help text"""
        return (
            "❓ **MediaButler Guide**\n\n"
            "**📥 How to use:**\n"
            "1️⃣ Send a video file\n"
            "2️⃣ Bot recognizes the content\n"
            "3️⃣ Confirm or choose type\n"
            "4️⃣ Automatic download\n\n"
            "**📝 Main commands:**\n"
            "• `/menu` - Interactive menu\n"
            "• `/status` - Quick status\n"
            "• `/downloads` - Active downloads\n"
            "• `/space` - Disk space\n"
            "• `/cancel` - Cancel download\n"
            "• `/help` - This help\n\n"
            "**📁 Organization:**\n"
            "• Movies: `/movies/Name (Year)/`\n"
            "• Series: `/tv/Series/Season XX/`\n\n"
            "**💡 Tips:**\n"
            "• Descriptive names = better results\n"
            "• Max 10GB per file\n"
            "• Downloads resume after restart\n\n"
            "For assistance, contact the admin."
        )
    
    def _get_users_text(self) -> str:
        """User management text"""
        users = self.auth.get_authorized_users()
        admin_id = self.auth.get_admin_id()
        
        text = f"👥 **Authorized Users ({len(users)})**\n\n"
        
        for idx, user_id in enumerate(users, 1):
            is_admin = " 👑 Admin" if user_id == admin_id else ""
            text += f"**{idx}.** `{user_id}`{is_admin}\n"
        
        text += (
            "\n📝 **To modify:**\n"
            "1. Modifica `AUTHORIZED_USERS` in `.env`\n"
            "2. Restart the bot\n\n"
            "The first user is always admin."
        )
        
        return text
    
    def _get_cancel_confirmation(self) -> str:
        """Cancellation confirmation text"""
        active = len(self.downloads.get_active_downloads())
        queued = self.downloads.get_queued_count()
        waiting = self.downloads.get_space_waiting_count()
        total = active + queued + waiting
        
        if total == 0:
            return "✅ **No downloads to cancel**"
        
        return (
            f"⚠️ **Conferma Cancellazione**\n\n"
            f"Stai per cancellare:\n"
            f"• Download attivi: {active}\n"
            f"• In coda: {queued}\n"
            f"• Waiting: {waiting}\n\n"
            f"**Totale: {total} operations**\n\n"
            f"Sei sicuro?"
        )

    async def subtitles_handler(self, event):
        """Handler for /subtitles command"""
        if not await self.auth.check_authorized(event):
            return

        await event.reply(
            self._get_subtitle_status(),
            buttons=self._create_subtitle_menu()
        )

    async def subtitle_toggle_handler(self, event):
        """Handler for /sub_toggle command - enable/disable subtitles"""
        if not await self.auth.check_authorized(event):
            return

        await event.reply(
            "⚙️ **Configurazione Sottotitoli**\n\n"
            "Per modificare le impostazioni sottotitoli, aggiorna il file .env:\n\n"
            "• `SUBTITLE_ENABLED=true/false`\n"
            "• `SUBTITLE_AUTO_DOWNLOAD=true/false`\n"
            "• `SUBTITLE_LANGUAGES=it,en`\n\n"
            "Restart the bot per applicare le modifiche."
        )

    async def subtitle_auto_handler(self, event):
        """Handler for /sub_auto command - toggle automatic download"""
        if not await self.auth.check_authorized(event):
            return

        await event.reply(
            "⚙️ **Download Automatico Sottotitoli**\n\n"
            "Per abilitare/disabilitare il download automatico, "
            "modifica `SUBTITLE_AUTO_DOWNLOAD=true/false` nel file .env\n\n"
            "Restart the bot per applicare le modifiche."
        )

    async def subtitle_callback_handler(self, event):
        """Handler for subtitle button callbacks"""
        if not await self.auth.check_authorized(event):
            await event.answer("❌ Non autorizzato")
            return

        try:
            data = event.data.decode('utf-8')

            if data == "sub_status":
                await event.edit(
                    self._get_subtitle_status(),
                    buttons=self._create_subtitle_menu()
                )

            elif data == "sub_config":
                await event.edit(
                    "⚙️ **Configurazione Sottotitoli**\n\n"
                    "Per modificare le impostazioni, edita il file .env:\n\n"
                    "• `SUBTITLE_ENABLED=true/false`\n"
                    "• `SUBTITLE_AUTO_DOWNLOAD=true/false`\n"
                    "• `SUBTITLE_LANGUAGES=it,en,es`\n"
                    "• `OPENSUBTITLES_USERNAME=username`\n"
                    "• `OPENSUBTITLES_PASSWORD=password`\n\n"
                    "Restart the bot per applicare le modifiche.",
                    buttons=[[Button.inline("🔙 Back", "sub_status")]]
                )

            elif data == "sub_back_main":
                user_id = event.sender_id
                is_admin = self.auth.is_admin(user_id)
                await event.edit(
                    "🎬 **MediaButler - Main Menu**\n\n"
                    "Select an option:",
                    buttons=self._create_main_menu(is_admin)
                )

            await event.answer()

        except Exception as e:
            self.logger.error(f"Subtitle callback error: {e}")
            await event.answer("❌ Errore")

    def _get_subtitle_status(self) -> str:
        """Get subtitle system status"""
        config = self.config.subtitles

        status_icon = "✅" if config.enabled else "❌"
        auto_icon = "✅" if config.auto_download else "❌"
        auth_icon = "✅" if config.is_opensubtitles_configured else "❌"

        return (
            f"📝 **Stato Sottotitoli**\n\n"
            f"{status_icon} Sistema attivo: **{'Sì' if config.enabled else 'No'}**\n"
            f"{auto_icon} Download automatico: **{'Sì' if config.auto_download else 'No'}**\n"
            f"🌍 Lingue: **{', '.join(config.languages)}**\n"
            f"{auth_icon} OpenSubtitles configurato: **{'Sì' if config.is_opensubtitles_configured else 'No'}**\n"
            f"📄 Formato preferito: **{config.preferred_format}**\n\n"
            f"User Agent: `{config.opensubtitles_user_agent}`"
        )

    def _create_subtitle_menu(self):
        """Create subtitle menu"""
        return [
            [
                Button.inline("🔄 Refresh", "sub_status"),
                Button.inline("⚙️ Configuration", "sub_config")
            ],
            [
                Button.inline("🔙 Main Menu", "sub_back_main")
            ]
        ]
    