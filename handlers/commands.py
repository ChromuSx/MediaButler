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
from core.database import DatabaseManager
from core.user_config import UserConfig


class CommandHandlers:
    """Bot command management with interactive menu"""

    def __init__(
        self,
        client: TelegramClient,
        auth_manager: AuthManager,
        space_manager: SpaceManager,
        download_manager: DownloadManager,
        database_manager: DatabaseManager = None,
    ):
        self.client = client
        self.auth = auth_manager
        self.space = space_manager
        self.downloads = download_manager
        self.database = database_manager
        self.config = get_config()
        self.logger = self.config.logger

    async def setup_bot_commands(self):
        """Setup bot commands for autocomplete menu (visible when typing /)"""
        from telethon.tl.functions.bots import SetBotCommandsRequest
        from telethon.tl.types import BotCommand

        # Define all commands with descriptions
        commands = [
            BotCommand(command="start", description="Start bot and show main menu"),
            BotCommand(command="menu", description="Show main menu"),
            BotCommand(command="status", description="Show active downloads status"),
            BotCommand(command="space", description="Show disk space information"),
            BotCommand(command="downloads", description="Show detailed downloads list"),
            BotCommand(command="waiting", description="Show files waiting for space"),
            BotCommand(command="cancel", description="Cancel a specific download"),
            BotCommand(command="cancel_all", description="Cancel all downloads"),
            BotCommand(command="help", description="Show help and available commands"),
            BotCommand(
                command="settings", description="Show and manage global settings"
            ),
            BotCommand(
                command="mysettings",
                description="Show and manage your personal settings",
            ),
            BotCommand(command="subtitles", description="Manage subtitle settings"),
            BotCommand(command="stats", description="Show download statistics"),
            BotCommand(command="history", description="Show download history"),
            BotCommand(command="users", description="[Admin] Show authorized users"),
            BotCommand(command="stop", description="[Admin] Stop the bot"),
        ]

        try:
            # Set commands using Telegram Bot API
            await self.client(
                SetBotCommandsRequest(
                    scope=None,  # Default scope (all users)
                    lang_code="",  # Default language
                    commands=commands,
                )
            )
            self.logger.info(f"✅ Bot commands configured ({len(commands)} commands)")
        except Exception as e:
            self.logger.warning(f"Failed to set bot commands: {e}")

    def register(self):
        """Register all command handlers"""
        # Main commands
        self.client.on(events.NewMessage(pattern="/start"))(self.start_handler)
        self.client.on(events.NewMessage(pattern="/menu"))(self.menu_handler)
        self.client.on(events.NewMessage(pattern="/status"))(self.status_handler)
        self.client.on(events.NewMessage(pattern="/space"))(self.space_handler)
        self.client.on(events.NewMessage(pattern="/downloads"))(self.downloads_handler)
        self.client.on(events.NewMessage(pattern="/waiting"))(self.waiting_handler)
        self.client.on(events.NewMessage(pattern="/cancel_all"))(
            self.cancel_all_handler
        )
        self.client.on(events.NewMessage(pattern="/cancel"))(self.cancel_handler)
        self.client.on(events.NewMessage(pattern="/stop"))(self.stop_handler)
        self.client.on(events.NewMessage(pattern="/users"))(self.users_handler)
        self.client.on(events.NewMessage(pattern="/help"))(self.help_handler)
        self.client.on(events.NewMessage(pattern="/settings"))(self.settings_handler)
        self.client.on(events.NewMessage(pattern="/subtitles"))(self.subtitles_handler)
        self.client.on(events.NewMessage(pattern="/sub_toggle"))(
            self.subtitle_toggle_handler
        )
        self.client.on(events.NewMessage(pattern="/sub_auto"))(
            self.subtitle_auto_handler
        )
        self.client.on(events.NewMessage(pattern="/stats"))(self.stats_handler)
        self.client.on(events.NewMessage(pattern="/history"))(self.history_handler)
        self.client.on(events.NewMessage(pattern="/mysettings"))(
            self.mysettings_handler
        )

        # Callback handler for buttons
        self.client.on(events.CallbackQuery(pattern="menu_"))(
            self.menu_callback_handler
        )
        self.client.on(events.CallbackQuery(pattern="cancel_"))(
            self.cancel_callback_handler
        )
        self.client.on(events.CallbackQuery(pattern="stop_"))(
            self.stop_callback_handler
        )
        self.client.on(events.CallbackQuery(pattern="sub_"))(
            self.subtitle_callback_handler
        )
        self.client.on(events.CallbackQuery(pattern="stats_"))(
            self.stats_callback_handler
        )
        self.client.on(events.CallbackQuery(pattern="userset_"))(
            self.user_settings_callback_handler
        )

        self.logger.info("Command handlers registered with inline menu")

    def _create_main_menu(self, is_admin: bool = False):
        """Create main menu with inline buttons"""
        buttons = [
            [
                Button.inline("📊 Status", "menu_status"),
                Button.inline("💾 Space", "menu_space"),
                Button.inline("📥 Downloads", "menu_downloads"),
            ],
            [
                Button.inline("⏳ Waiting", "menu_waiting"),
                Button.inline("📝 Subtitles", "menu_subtitles"),
                Button.inline("⚙️ Global Settings", "menu_settings"),
            ],
            [
                Button.inline("👤 My Settings", "userset_main"),
                Button.inline("📈 Stats", "stats_refresh"),
                Button.inline("❓ Help", "menu_help"),
            ],
            [Button.inline("❌ Cancel All", "menu_cancel_all")],
        ]

        if is_admin:
            buttons.append(
                [
                    Button.inline("👥 Users", "menu_users"),
                    Button.inline("🛑 Stop Bot", "menu_stop"),
                ]
            )

        return buttons

    def _create_quick_menu(self):
        """Create quick menu with main actions"""
        return [
            [
                Button.inline("📊 Status", "menu_status"),
                Button.inline("📥 Downloads", "menu_downloads"),
            ],
            [Button.inline("📱 Full Menu", "menu_full")],
        ]

    async def start_handler(self, event: events.NewMessage.Event):
        """Handler /start"""
        if not await self.auth.check_authorized(event):
            return

        user = await event.get_sender()
        self.logger.info(f"/start from {user.username} (ID: {user.id})")

        is_admin = self.auth.is_admin(user.id)

        # Welcome message
        welcome_text = self._format_welcome_message(user.id, is_admin)

        # Send with inline menu
        await event.reply(
            welcome_text, buttons=self._create_main_menu(is_admin), link_preview=False
        )

    async def menu_handler(self, event: events.NewMessage.Event):
        """Handler /menu"""
        if not await self.auth.check_authorized(event):
            return

        is_admin = self.auth.is_admin(event.sender_id)

        await event.reply(
            "🎬 **MediaButler - Main Menu**\n\n" "Select an option:",
            buttons=self._create_main_menu(is_admin),
        )

    async def status_handler(self, event: events.NewMessage.Event):
        """Handler /status"""
        if not await self.auth.check_authorized(event):
            return

        status_text = self._get_status_text()

        buttons = [
            [
                Button.inline("🔄 Refresh", "menu_status"),
                Button.inline("📱 Menu", "menu_back"),
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
                Button.inline("📱 Menu", "menu_back"),
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
                Button.inline("❌ Cancel All", "menu_cancel_all"),
            ],
            [Button.inline("📱 Menu", "menu_back")],
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
                Button.inline("📱 Menu", "menu_back"),
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
                buttons=[[Button.inline("📱 Menu", "menu_back")]],
            )
            return

        text = "**❌ Select download to cancel:**\n\n"
        buttons = []

        for idx, info in enumerate(active, 1):
            filename_short = (
                info.filename[:30] + "..." if len(info.filename) > 30 else info.filename
            )
            text += f"{idx}. `{filename_short}`\n"
            text += f"   {info.progress:.1f}% - {info.size_gb:.1f} GB\n\n"

            buttons.append(
                [Button.inline(f"❌ Cancel #{idx}", f"cancel_{info.message_id}")]
            )

        buttons.append(
            [
                Button.inline("❌ Cancel All", "menu_cancel_all"),
                Button.inline("📱 Menu", "menu_back"),
            ]
        )

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
                buttons=[[Button.inline("📱 Menu", "menu_back")]],
            )
            return

        buttons = [
            [
                Button.inline("✅ Confirm", "cancel_confirm"),
                Button.inline("❌ Cancel", "menu_back"),
            ]
        ]

        await event.reply(
            f"⚠️ **Confirm cancellation**\n\n"
            f"You are about to cancel:\n"
            f"• Active downloads: {active}\n"
            f"• Queued: {queued}\n"
            f"• Waiting: {waiting}\n\n"
            f"**Total: {total} operations**\n\n"
            f"Confirm?",
            buttons=buttons,
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

        await event.reply(help_text, buttons=self._create_quick_menu())

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
                Button.inline("❌ Cancel", "menu_back"),
            ]
        ]

        await event.reply(
            "🛑 **Confirm Bot Stop**\n\n"
            "⚠️ This action:\n"
            "• Will cancel all downloads\n"
            "• Will stop the bot\n"
            "• Will require manual restart\n\n"
            "Confirm?",
            buttons=buttons,
        )

    async def menu_callback_handler(self, event: events.CallbackQuery.Event):
        """Handler for menu callbacks"""
        if not await self.auth.check_callback_authorized(event):
            return

        action = event.data.decode("utf-8").replace("menu_", "")

        # Menu navigation
        if action == "back" or action == "full":
            is_admin = self.auth.is_admin(event.sender_id)
            await event.edit(
                "🎬 **MediaButler - Main Menu**\n\n" "Select an option:",
                buttons=self._create_main_menu(is_admin),
            )
        elif action == "refresh":
            is_admin = self.auth.is_admin(event.sender_id)
            await event.edit(
                "🎬 **MediaButler - Main Menu**\n\n" "Select an option:",
                buttons=self._create_main_menu(is_admin),
            )
            await event.answer("✅ Menu updated")
        else:
            await self._handle_menu_action(event, action)

    async def cancel_callback_handler(self, event: events.CallbackQuery.Event):
        """Handler for cancellations"""
        data = event.data.decode("utf-8")

        if data == "cancel_confirm":
            total_cancelled = self.downloads.cancel_all_downloads()

            await event.edit(
                f"✅ **Cancellation Completed**\n\n"
                f"Cancelled {total_cancelled} operations.",
                buttons=[[Button.inline("📱 Menu", "menu_back")]],
            )
        else:
            # Cancella singolo download
            msg_id = int(data.replace("cancel_", ""))
            if self.downloads.cancel_download(msg_id):
                await event.answer("✅ Download canceled")

                # Update list
                downloads_text = self._get_downloads_detailed()
                buttons = [
                    [
                        Button.inline("🔄 Refresh", "menu_downloads"),
                        Button.inline("📱 Menu", "menu_back"),
                    ]
                ]

                await event.edit(downloads_text, buttons=buttons)
            else:
                await event.answer("❌ Download not found", alert=True)

    async def stop_callback_handler(self, event: events.CallbackQuery.Event):
        """Handler for bot stop"""
        if event.data.decode("utf-8") == "stop_confirm":
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
            "status": self._get_status_text,
            "space": self.space.format_disk_status,
            "downloads": self._get_downloads_detailed,
            "waiting": self._get_waiting_text,
            "subtitles": self._get_subtitle_status,
            "settings": self._get_settings_text,
            "help": self._get_help_text,
            "users": self._get_users_text,
            "cancel_all": self._get_cancel_confirmation,
        }

        if action in content_map:
            content = content_map[action]()

            buttons = []

            # Specific buttons for each action
            if action in ["status", "space", "downloads", "waiting"]:
                buttons.append(
                    [
                        Button.inline("🔄 Refresh", f"menu_{action}"),
                        Button.inline("📱 Menu", "menu_back"),
                    ]
                )
            elif action == "subtitles":
                buttons = self._create_subtitle_menu()
            elif action == "cancel_all":
                buttons = [
                    [
                        Button.inline("✅ Confirm", "cancel_confirm"),
                        Button.inline("❌ Cancel", "menu_back"),
                    ]
                ]
            elif action == "users":
                if not self.auth.is_admin(event.sender_id):
                    await event.answer("❌ Administrators only", alert=True)
                    return
                buttons = [[Button.inline("📱 Menu", "menu_back")]]
            elif action == "stop":
                if not self.auth.is_admin(event.sender_id):
                    await event.answer("❌ Administrators only", alert=True)
                    return
                buttons = [
                    [
                        Button.inline("✅ Confirm Stop", "stop_confirm"),
                        Button.inline("❌ Cancel", "menu_back"),
                    ]
                ]
                content = (
                    "🛑 **Confirm Bot Stop**\n\n⚠️ This action:\n"
                    "• Will cancel all downloads\n"
                    "• Will stop the bot\n"
                    "• Will require manual restart\n\nConfirm?"
                )
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
        tmdb_status = (
            "TMDB Active" if self.config.tmdb.is_enabled else "TMDB Not configured"
        )

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
                    status_text += (
                        f"  {info.progress:.1f}% - {info.speed_mbps:.1f} MB/s\n"
                    )
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
            return "📭 **No active downloads**\n\n" "Send a video file to start."

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
            return "✅ **No files waiting**\n\n" "All downloads have sufficient space."

        text = f"⏳ **Files waiting for space ({waiting_count})**\n\n"

        for idx, item in enumerate(self.downloads.space_waiting_queue[:10], 1):
            info = item.download_info
            text += f"**{idx}.** `{info.filename[:35]}{'...' if len(info.filename) > 35 else ''}`\n"
            text += f"    📏 {info.size_gb:.1f} GB | 📂 {info.media_type.value}\n"

        if waiting_count > 10:
            text += f"\n...and {waiting_count - 10} more files"

        return text

    def _get_settings_text(self) -> str:
        """Settings text"""
        tmdb_status = (
            "✅ Active" if self.config.tmdb.is_enabled else "❌ Not configured"
        )

        return (
            "⚙️ **Current Settings**\n\n"
            f"**Download:**\n"
            f"• Concurrent: {self.config.limits.max_concurrent_downloads}\n"
            f"• Max size: {self.config.limits.max_file_size_gb} GB\n\n"
            f"**Space:**\n"
            f"• Minimum reserved: {self.config.limits.min_free_space_gb} GB\n"
            f"• Warning threshold: {self.config.limits.warning_threshold_gb} GB\n"
            f"• Check every: {self.config.limits.space_check_interval}s\n\n"
            f"**TMDB:**\n"
            f"• Status: {tmdb_status}\n"
            f"• Language: {self.config.tmdb.language}\n\n"
            f"**Paths:**\n"
            f"• Movies: `{self.config.paths.movies}`\n"
            f"• TV Shows: `{self.config.paths.tv}`\n"
            f"• Temp: `{self.config.paths.temp}`\n\n"
            f"ℹ️ Edit `.env` to change."
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
            "1. Edit `AUTHORIZED_USERS` in `.env`\n"
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
            f"⚠️ **Confirm Cancellation**\n\n"
            f"You are about to cancel:\n"
            f"• Active downloads: {active}\n"
            f"• Queued: {queued}\n"
            f"• Waiting: {waiting}\n\n"
            f"**Total: {total} operations**\n\n"
            f"Are you sure?"
        )

    async def subtitles_handler(self, event):
        """Handler for /subtitles command"""
        if not await self.auth.check_authorized(event):
            return

        await event.reply(
            self._get_subtitle_status(), buttons=self._create_subtitle_menu()
        )

    async def subtitle_toggle_handler(self, event):
        """Handler for /sub_toggle command - enable/disable subtitles"""
        if not await self.auth.check_authorized(event):
            return

        await event.reply(
            "⚙️ **Subtitle Configuration**\n\n"
            "To modify subtitle settings, update the .env file:\n\n"
            "• `SUBTITLE_ENABLED=true/false`\n"
            "• `SUBTITLE_AUTO_DOWNLOAD=true/false`\n"
            "• `SUBTITLE_LANGUAGES=it,en`\n\n"
            "Restart the bot to apply changes."
        )

    async def subtitle_auto_handler(self, event):
        """Handler for /sub_auto command - toggle automatic download"""
        if not await self.auth.check_authorized(event):
            return

        await event.reply(
            "⚙️ **Automatic Subtitle Download**\n\n"
            "To enable/disable automatic download, "
            "edit `SUBTITLE_AUTO_DOWNLOAD=true/false` in the .env file\n\n"
            "Restart the bot to apply changes."
        )

    async def subtitle_callback_handler(self, event):
        """Handler for subtitle button callbacks"""
        if not await self.auth.check_authorized(event):
            await event.answer("❌ Not authorized")
            return

        try:
            data = event.data.decode("utf-8")

            if data == "sub_status":
                await event.edit(
                    self._get_subtitle_status(), buttons=self._create_subtitle_menu()
                )

            elif data == "sub_config":
                await event.edit(
                    "⚙️ **Subtitle Configuration**\n\n"
                    "To modify settings, edit the .env file:\n\n"
                    "• `SUBTITLE_ENABLED=true/false`\n"
                    "• `SUBTITLE_AUTO_DOWNLOAD=true/false`\n"
                    "• `SUBTITLE_LANGUAGES=it,en,es`\n"
                    "• `OPENSUBTITLES_USERNAME=username`\n"
                    "• `OPENSUBTITLES_PASSWORD=password`\n\n"
                    "Restart the bot to apply changes.",
                    buttons=[[Button.inline("🔙 Back", "sub_status")]],
                )

            elif data == "sub_back_main":
                user_id = event.sender_id
                is_admin = self.auth.is_admin(user_id)
                await event.edit(
                    "🎬 **MediaButler - Main Menu**\n\n" "Select an option:",
                    buttons=self._create_main_menu(is_admin),
                )

            await event.answer()

        except Exception as e:
            self.logger.error(f"Subtitle callback error: {e}")
            await event.answer("❌ Error")

    def _get_subtitle_status(self) -> str:
        """Get subtitle system status"""
        config = self.config.subtitles

        status_icon = "✅" if config.enabled else "❌"
        auto_icon = "✅" if config.auto_download else "❌"
        auth_icon = "✅" if config.is_opensubtitles_configured else "❌"

        return (
            f"📝 **Subtitle Status**\n\n"
            f"{status_icon} System enabled: **{'Yes' if config.enabled else 'No'}**\n"
            f"{auto_icon} Auto-download: **{'Yes' if config.auto_download else 'No'}**\n"
            f"🌍 Languages: **{', '.join(config.languages)}**\n"
            f"{auth_icon} OpenSubtitles configured: **{'Yes' if config.is_opensubtitles_configured else 'No'}**\n"
            f"📄 Preferred format: **{config.preferred_format}**\n\n"
            f"User Agent: `{config.opensubtitles_user_agent}`"
        )

    def _create_subtitle_menu(self):
        """Create subtitle menu"""
        return [
            [
                Button.inline("🔄 Refresh", "sub_status"),
                Button.inline("⚙️ Configuration", "sub_config"),
            ],
            [Button.inline("🔙 Main Menu", "sub_back_main")],
        ]

    async def stats_handler(self, event):
        """Handler for /stats command - show download statistics"""
        if not await self.auth.check_authorized(event):
            return

        if not self.database:
            await event.reply(
                "❌ **Database not enabled**\n\nEnable database in .env to use statistics."
            )
            return

        try:
            user_id = event.sender_id
            user_stats = await self.database.get_user_stats(user_id)
            global_stats = await self.database.get_all_stats()

            text = await self._format_stats_message(user_stats, global_stats, user_id)

            buttons = [
                [
                    Button.inline("🔄 Refresh", "stats_refresh"),
                    Button.inline("📊 Global Stats", "stats_global"),
                ],
                [
                    Button.inline("📝 My History", f"stats_history_{user_id}"),
                    Button.inline("📱 Menu", "menu_back"),
                ],
            ]

            await event.reply(text, buttons=buttons)

        except Exception as e:
            self.logger.error(f"Error in stats handler: {e}", exc_info=True)
            await event.reply(f"❌ Error retrieving statistics: {str(e)}")

    async def history_handler(self, event):
        """Handler for /history command - show download history"""
        if not await self.auth.check_authorized(event):
            return

        if not self.database:
            await event.reply(
                "❌ **Database not enabled**\n\nEnable database in .env to use history."
            )
            return

        try:
            user_id = event.sender_id
            downloads = await self.database.get_user_downloads(user_id, limit=20)

            if not downloads:
                await event.reply(
                    "📭 **No download history**\n\nYou haven't downloaded any files yet.",
                    buttons=[[Button.inline("📱 Menu", "menu_back")]],
                )
                return

            text = self._format_history_message(downloads)

            buttons = [
                [
                    Button.inline("🔄 Refresh", f"stats_history_{user_id}"),
                    Button.inline("📱 Menu", "menu_back"),
                ]
            ]

            await event.reply(text, buttons=buttons)

        except Exception as e:
            self.logger.error(f"Error in history handler: {e}", exc_info=True)
            await event.reply(f"❌ Error retrieving history: {str(e)}")

    async def stats_callback_handler(self, event):
        """Handler for statistics button callbacks"""
        if not await self.auth.check_authorized(event):
            await event.answer("❌ Not authorized")
            return

        if not self.database:
            await event.answer("❌ Database not enabled")
            return

        try:
            data = event.data.decode("utf-8")

            if data == "stats_refresh":
                user_id = event.sender_id
                user_stats = await self.database.get_user_stats(user_id)
                global_stats = await self.database.get_all_stats()

                text = await self._format_stats_message(
                    user_stats, global_stats, user_id
                )

                buttons = [
                    [
                        Button.inline("🔄 Refresh", "stats_refresh"),
                        Button.inline("📊 Global Stats", "stats_global"),
                    ],
                    [
                        Button.inline("📝 My History", f"stats_history_{user_id}"),
                        Button.inline("📱 Menu", "menu_back"),
                    ],
                ]

                await event.edit(text, buttons=buttons)

            elif data == "stats_global":
                global_stats = await self.database.get_all_stats()
                text = self._format_global_stats(global_stats)

                buttons = [
                    [
                        Button.inline("👤 My Stats", "stats_refresh"),
                        Button.inline("📱 Menu", "menu_back"),
                    ]
                ]

                await event.edit(text, buttons=buttons)

            elif data.startswith("stats_history_"):
                user_id = int(data.split("_")[2])
                downloads = await self.database.get_user_downloads(user_id, limit=20)

                text = self._format_history_message(downloads)

                buttons = [
                    [
                        Button.inline("🔄 Refresh", f"stats_history_{user_id}"),
                        Button.inline("📱 Menu", "menu_back"),
                    ]
                ]

                await event.edit(text, buttons=buttons)

            await event.answer()

        except Exception as e:
            self.logger.error(f"Stats callback error: {e}", exc_info=True)
            await event.answer("❌ Error")

    async def _format_stats_message(self, user_stats, global_stats, user_id):
        """Format statistics message"""
        if not user_stats:
            return (
                f"📊 **Your Statistics**\n\n"
                f"👤 User ID: `{user_id}`\n\n"
                f"No downloads yet. Send a file to get started!"
            )

        total_gb = (
            user_stats["total_bytes"] / (1024**3) if user_stats["total_bytes"] else 0
        )
        success_rate = (
            (user_stats["successful_downloads"] / user_stats["total_downloads"] * 100)
            if user_stats["total_downloads"] > 0
            else 0
        )

        text = (
            f"📊 **Your Statistics**\n\n"
            f"👤 User ID: `{user_id}`\n\n"
            f"**📥 Downloads:**\n"
            f"• Total: **{user_stats['total_downloads']}**\n"
            f"• Successful: **{user_stats['successful_downloads']}** ✅\n"
            f"• Failed: **{user_stats['failed_downloads']}** ❌\n"
            f"• Cancelled: **{user_stats['cancelled_downloads']}** 🚫\n"
            f"• Success rate: **{success_rate:.1f}%**\n\n"
            f"**💾 Data:**\n"
            f"• Total downloaded: **{total_gb:.2f} GB**\n\n"
            f"**📅 Activity:**\n"
            f"• First download: {user_stats['first_download'][:16] if user_stats['first_download'] else 'N/A'}\n"
            f"• Last download: {user_stats['last_download'][:16] if user_stats['last_download'] else 'N/A'}\n\n"
            f"**🌍 Global rank:**\n"
        )

        # Add user rank
        top_users = global_stats.get("top_users", [])
        user_rank = next(
            (i + 1 for i, u in enumerate(top_users) if u["user_id"] == user_id), None
        )

        if user_rank:
            text += f"• Position: **#{user_rank}** of {len(top_users)} users\n"
        else:
            text += f"• Not in top {len(top_users)}\n"

        return text

    def _format_global_stats(self, stats):
        """Format global statistics message"""
        total_gb = stats.get("total_gb", 0)

        text = (
            f"🌍 **Global Statistics**\n\n"
            f"**📊 Overall:**\n"
            f"• Total downloads: **{stats.get('total_downloads', 0)}**\n"
            f"• Total data: **{total_gb:.2f} GB**\n"
            f"• Last 24h: **{stats.get('recent_24h', 0)}** downloads\n\n"
            f"**📈 By Status:**\n"
        )

        status_counts = stats.get("status_counts", {})
        for status, count in status_counts.items():
            emoji = {
                "completed": "✅",
                "failed": "❌",
                "cancelled": "🚫",
                "downloading": "⬇️",
                "queued": "⏳",
            }.get(status, "📄")
            text += f"• {emoji} {status.capitalize()}: **{count}**\n"

        text += "\n**👥 Top Users:**\n"
        top_users = stats.get("top_users", [])
        for i, user in enumerate(top_users[:5], 1):
            user_gb = user["total_bytes"] / (1024**3) if user["total_bytes"] else 0
            text += f"{i}. User `{user['user_id']}` - **{user['total_downloads']}** downloads ({user_gb:.1f} GB)\n"

        text += "\n**📺 Top Series:**\n"
        top_series = stats.get("top_series", [])
        for i, series in enumerate(top_series[:5], 1):
            text += f"{i}. {series['series_name']} - **{series['count']}** episodes\n"

        return text

    def _format_history_message(self, downloads):
        """Format download history message"""
        if not downloads:
            return "📭 **No download history**"

        text = f"📝 **Download History** (last {len(downloads)})\n\n"

        for i, dl in enumerate(downloads[:10], 1):
            status_emoji = {
                "completed": "✅",
                "failed": "❌",
                "cancelled": "🚫",
                "downloading": "⬇️",
            }.get(dl["status"], "❓")

            size_gb = dl["size_bytes"] / (1024**3) if dl["size_bytes"] else 0
            filename = (
                dl["filename"][:30] + "..."
                if len(dl["filename"]) > 30
                else dl["filename"]
            )

            text += f"**{i}.** {status_emoji} `{filename}`\n"
            text += f"    📏 {size_gb:.2f} GB"

            if dl["media_type"] == "tv" and dl["series_name"]:
                text += f" | 📺 {dl['series_name']}"
                if dl["season"] and dl["episode"]:
                    text += f" S{dl['season']:02d}E{dl['episode']:02d}"
            elif dl["media_type"] == "movie" and dl["movie_title"]:
                text += f" | 🎬 {dl['movie_title']}"

            text += f"\n    📅 {dl['created_at'][:16]}\n\n"

        if len(downloads) > 10:
            text += f"_...and {len(downloads) - 10} more_"

        return text

    async def mysettings_handler(self, event):
        """Handler for /mysettings command - manage personal settings"""
        if not await self.auth.check_authorized(event):
            return

        if not self.database:
            await event.reply(
                "❌ **Database not enabled**\n\nUser settings require database to be enabled."
            )
            return

        try:
            user_id = event.sender_id
            user_config = UserConfig(user_id, self.database)

            text = await self._format_my_settings_message(user_config)
            buttons = self._create_my_settings_menu()

            await event.reply(text, buttons=buttons)

        except Exception as e:
            self.logger.error(f"Error in mysettings handler: {e}", exc_info=True)
            await event.reply(f"❌ Error loading settings: {str(e)}")

    def _create_my_settings_menu(self):
        """Create user settings menu"""
        return [
            [
                Button.inline("📁 Paths", "userset_paths"),
                Button.inline("📥 Downloads", "userset_downloads"),
            ],
            [
                Button.inline("📝 Subtitles", "userset_subtitles"),
                Button.inline("🔔 Notifications", "userset_notifications"),
            ],
            [
                Button.inline("🎨 Interface", "userset_interface"),
                Button.inline("🔄 Reset All", "userset_reset_confirm"),
            ],
            [Button.inline("📱 Main Menu", "menu_back")],
        ]

    async def user_settings_callback_handler(self, event):
        """Handler for user settings callbacks"""
        if not await self.auth.check_authorized(event):
            await event.answer("❌ Not authorized")
            return

        if not self.database:
            await event.answer("❌ Database not enabled")
            return

        try:
            data = event.data.decode("utf-8")
            user_id = event.sender_id
            user_config = UserConfig(user_id, self.database)

            if data == "userset_main":
                # Return to main settings
                text = await self._format_my_settings_message(user_config)
                buttons = self._create_my_settings_menu()
                await event.edit(text, buttons=buttons)

            elif data == "userset_paths":
                text = await self._format_paths_settings(user_config)
                buttons = [[Button.inline("🔙 Back", "userset_main")]]
                await event.edit(text, buttons=buttons)

            elif data == "userset_downloads":
                text = await self._format_downloads_settings(user_config)
                buttons = [
                    [
                        Button.inline(
                            (
                                "Auto-confirm: ON"
                                if await user_config.get_auto_confirm_threshold() < 100
                                else "Auto-confirm: OFF"
                            ),
                            "userset_toggle_autoconfirm",
                        )
                    ],
                    [Button.inline("🔙 Back", "userset_main")],
                ]
                await event.edit(text, buttons=buttons)

            elif data == "userset_subtitles":
                text = await self._format_subtitles_settings(user_config)
                sub_enabled = await user_config.get_subtitle_enabled()
                auto_dl = await user_config.get_subtitle_auto_download()

                buttons = [
                    [
                        Button.inline(
                            f"{'✅' if sub_enabled else '❌'} Subtitles",
                            "userset_toggle_sub_enabled",
                        ),
                        Button.inline(
                            f"{'✅' if auto_dl else '❌'} Auto-DL",
                            "userset_toggle_sub_auto",
                        ),
                    ],
                    [Button.inline("🔙 Back", "userset_main")],
                ]
                await event.edit(text, buttons=buttons)

            elif data == "userset_notifications":
                text = await self._format_notifications_settings(user_config)
                notify_complete = await user_config.get_notify_download_complete()
                notify_failed = await user_config.get_notify_download_failed()
                notify_space = await user_config.get_notify_low_space()

                buttons = [
                    [
                        Button.inline(
                            f"{'✅' if notify_complete else '❌'} Complete",
                            "userset_toggle_notify_complete",
                        ),
                        Button.inline(
                            f"{'✅' if notify_failed else '❌'} Failed",
                            "userset_toggle_notify_failed",
                        ),
                    ],
                    [
                        Button.inline(
                            f"{'✅' if notify_space else '❌'} Low Space",
                            "userset_toggle_notify_space",
                        )
                    ],
                    [Button.inline("🔙 Back", "userset_main")],
                ]
                await event.edit(text, buttons=buttons)

            elif data == "userset_interface":
                text = await self._format_interface_settings(user_config)
                compact = await user_config.get_compact_messages()

                buttons = [
                    [
                        Button.inline(
                            f"{'✅' if compact else '❌'} Compact Mode",
                            "userset_toggle_compact",
                        )
                    ],
                    [Button.inline("🔙 Back", "userset_main")],
                ]
                await event.edit(text, buttons=buttons)

            # Toggle handlers
            elif data == "userset_toggle_sub_enabled":
                current = await user_config.get_subtitle_enabled()
                await user_config.set_subtitle_enabled(not current)
                await event.answer(
                    f"✅ Subtitles {'enabled' if not current else 'disabled'}"
                )
                # Refresh subtitle view
                text = await self._format_subtitles_settings(user_config)
                sub_enabled = await user_config.get_subtitle_enabled()
                auto_dl = await user_config.get_subtitle_auto_download()
                buttons = [
                    [
                        Button.inline(
                            f"{'✅' if sub_enabled else '❌'} Subtitles",
                            "userset_toggle_sub_enabled",
                        ),
                        Button.inline(
                            f"{'✅' if auto_dl else '❌'} Auto-DL",
                            "userset_toggle_sub_auto",
                        ),
                    ],
                    [Button.inline("🔙 Back", "userset_main")],
                ]
                await event.edit(text, buttons=buttons)

            elif data == "userset_toggle_sub_auto":
                current = await user_config.get_subtitle_auto_download()
                await user_config.set_subtitle_auto_download(not current)
                await event.answer(
                    f"✅ Auto-download {'enabled' if not current else 'disabled'}"
                )
                # Refresh subtitle view
                text = await self._format_subtitles_settings(user_config)
                sub_enabled = await user_config.get_subtitle_enabled()
                auto_dl = await user_config.get_subtitle_auto_download()
                buttons = [
                    [
                        Button.inline(
                            f"{'✅' if sub_enabled else '❌'} Subtitles",
                            "userset_toggle_sub_enabled",
                        ),
                        Button.inline(
                            f"{'✅' if auto_dl else '❌'} Auto-DL",
                            "userset_toggle_sub_auto",
                        ),
                    ],
                    [Button.inline("🔙 Back", "userset_main")],
                ]
                await event.edit(text, buttons=buttons)

            elif data == "userset_toggle_notify_complete":
                current = await user_config.get_notify_download_complete()
                await user_config.set_notify_download_complete(not current)
                await event.answer(
                    f"✅ Notification {'enabled' if not current else 'disabled'}"
                )
                # Refresh notifications view
                text = await self._format_notifications_settings(user_config)
                notify_complete = await user_config.get_notify_download_complete()
                notify_failed = await user_config.get_notify_download_failed()
                notify_space = await user_config.get_notify_low_space()
                buttons = [
                    [
                        Button.inline(
                            f"{'✅' if notify_complete else '❌'} Complete",
                            "userset_toggle_notify_complete",
                        ),
                        Button.inline(
                            f"{'✅' if notify_failed else '❌'} Failed",
                            "userset_toggle_notify_failed",
                        ),
                    ],
                    [
                        Button.inline(
                            f"{'✅' if notify_space else '❌'} Low Space",
                            "userset_toggle_notify_space",
                        )
                    ],
                    [Button.inline("🔙 Back", "userset_main")],
                ]
                await event.edit(text, buttons=buttons)

            elif data == "userset_toggle_notify_failed":
                current = await user_config.get_notify_download_failed()
                await user_config.set_notify_download_failed(not current)
                await event.answer(
                    f"✅ Notification {'enabled' if not current else 'disabled'}"
                )
                # Refresh notifications view
                text = await self._format_notifications_settings(user_config)
                notify_complete = await user_config.get_notify_download_complete()
                notify_failed = await user_config.get_notify_download_failed()
                notify_space = await user_config.get_notify_low_space()
                buttons = [
                    [
                        Button.inline(
                            f"{'✅' if notify_complete else '❌'} Complete",
                            "userset_toggle_notify_complete",
                        ),
                        Button.inline(
                            f"{'✅' if notify_failed else '❌'} Failed",
                            "userset_toggle_notify_failed",
                        ),
                    ],
                    [
                        Button.inline(
                            f"{'✅' if notify_space else '❌'} Low Space",
                            "userset_toggle_notify_space",
                        )
                    ],
                    [Button.inline("🔙 Back", "userset_main")],
                ]
                await event.edit(text, buttons=buttons)

            elif data == "userset_toggle_notify_space":
                current = await user_config.get_notify_low_space()
                await user_config.set_notify_low_space(not current)
                await event.answer(
                    f"✅ Notification {'enabled' if not current else 'disabled'}"
                )
                # Refresh notifications view
                text = await self._format_notifications_settings(user_config)
                notify_complete = await user_config.get_notify_download_complete()
                notify_failed = await user_config.get_notify_download_failed()
                notify_space = await user_config.get_notify_low_space()
                buttons = [
                    [
                        Button.inline(
                            f"{'✅' if notify_complete else '❌'} Complete",
                            "userset_toggle_notify_complete",
                        ),
                        Button.inline(
                            f"{'✅' if notify_failed else '❌'} Failed",
                            "userset_toggle_notify_failed",
                        ),
                    ],
                    [
                        Button.inline(
                            f"{'✅' if notify_space else '❌'} Low Space",
                            "userset_toggle_notify_space",
                        )
                    ],
                    [Button.inline("🔙 Back", "userset_main")],
                ]
                await event.edit(text, buttons=buttons)

            elif data == "userset_toggle_compact":
                current = await user_config.get_compact_messages()
                await user_config.set_compact_messages(not current)
                await event.answer(
                    f"✅ Compact mode {'enabled' if not current else 'disabled'}"
                )
                # Refresh interface view
                text = await self._format_interface_settings(user_config)
                compact = await user_config.get_compact_messages()
                buttons = [
                    [
                        Button.inline(
                            f"{'✅' if compact else '❌'} Compact Mode",
                            "userset_toggle_compact",
                        )
                    ],
                    [Button.inline("🔙 Back", "userset_main")],
                ]
                await event.edit(text, buttons=buttons)

            elif data == "userset_reset_confirm":
                buttons = [
                    [
                        Button.inline("✅ Yes, Reset", "userset_reset_confirmed"),
                        Button.inline("❌ Cancel", "userset_main"),
                    ]
                ]
                await event.edit(
                    "⚠️ **Reset All Settings?**\n\n"
                    "This will reset all your personal settings to global defaults.\n\n"
                    "Are you sure?",
                    buttons=buttons,
                )

            elif data == "userset_reset_confirmed":
                await user_config.reset_to_defaults()
                await event.answer("✅ Settings reset to defaults")
                text = await self._format_my_settings_message(user_config)
                buttons = self._create_my_settings_menu()
                await event.edit(text, buttons=buttons)

            else:
                # Unknown callback, just acknowledge
                await event.answer()

        except Exception as e:
            self.logger.error(f"User settings callback error: {e}", exc_info=True)
            await event.answer("❌ Error")

    async def _format_my_settings_message(self, user_config: UserConfig):
        """Format main settings overview"""
        settings = await user_config.get_all_settings()

        return (
            f"⚙️ **My Personal Settings**\n\n"
            f"These are your personal preferences.\n"
            f"They override global defaults.\n\n"
            f"**📁 Paths:**\n"
            f"• Movies: `{settings['movies_path']}`\n"
            f"• TV Shows: `{settings['tv_path']}`\n\n"
            f"**📥 Downloads:**\n"
            f"• Max concurrent: {settings['max_concurrent_downloads']}\n"
            f"• Auto-confirm threshold: {settings['auto_confirm_threshold']}%\n\n"
            f"**📝 Subtitles:**\n"
            f"• Enabled: {'✅ Yes' if settings['subtitle_enabled'] else '❌ No'}\n"
            f"• Languages: {', '.join(settings['subtitle_languages'])}\n"
            f"• Auto-download: {'✅ Yes' if settings['subtitle_auto_download'] else '❌ No'}\n\n"
            f"**🔔 Notifications:**\n"
            f"• Complete: {'✅' if settings['notify_download_complete'] else '❌'} "
            f"Failed: {'✅' if settings['notify_download_failed'] else '❌'} "
            f"Low space: {'✅' if settings['notify_low_space'] else '❌'}\n\n"
            f"**💡 Tap a category to customize**"
        )

    async def _format_paths_settings(self, user_config: UserConfig):
        """Format paths settings"""
        movies = await user_config.get_movies_path()
        tv = await user_config.get_tv_path()

        return (
            f"📁 **Path Settings**\n\n"
            f"**Movies:**\n"
            f"`{movies}`\n\n"
            f"**TV Shows:**\n"
            f"`{tv}`\n\n"
            f"ℹ️ Contact admin to change paths"
        )

    async def _format_downloads_settings(self, user_config: UserConfig):
        """Format download settings"""
        max_concurrent = await user_config.get_max_concurrent_downloads()
        threshold = await user_config.get_auto_confirm_threshold()
        tmdb_lang = await user_config.get_tmdb_language()

        return (
            f"📥 **Download Settings**\n\n"
            f"**Max Concurrent Downloads:**\n"
            f"{max_concurrent} at a time\n\n"
            f"**Auto-Confirm Threshold:**\n"
            f"{threshold}% (TMDB confidence)\n"
            f"_Skip confirmation if match >= {threshold}%_\n\n"
            f"**TMDB Language:**\n"
            f"{tmdb_lang}\n\n"
            f"ℹ️ Contact admin to adjust limits"
        )

    async def _format_subtitles_settings(self, user_config: UserConfig):
        """Format subtitle settings"""
        enabled = await user_config.get_subtitle_enabled()
        languages = await user_config.get_subtitle_languages()
        auto_dl = await user_config.get_subtitle_auto_download()
        format = await user_config.get_subtitle_format()

        return (
            f"📝 **Subtitle Settings**\n\n"
            f"**System Enabled:**\n"
            f"{'✅ Yes' if enabled else '❌ No'}\n\n"
            f"**Languages:**\n"
            f"{', '.join(languages)}\n\n"
            f"**Auto-Download:**\n"
            f"{'✅ Yes' if auto_dl else '❌ No'}\n\n"
            f"**Format:**\n"
            f"{format}\n\n"
            f"💡 Toggle settings with buttons below"
        )

    async def _format_notifications_settings(self, user_config: UserConfig):
        """Format notification settings"""
        complete = await user_config.get_notify_download_complete()
        failed = await user_config.get_notify_download_failed()
        space = await user_config.get_notify_low_space()

        return (
            f"🔔 **Notification Settings**\n\n"
            f"Choose which events trigger notifications:\n\n"
            f"**Download Complete:**\n"
            f"{'✅ Enabled' if complete else '❌ Disabled'}\n\n"
            f"**Download Failed:**\n"
            f"{'✅ Enabled' if failed else '❌ Disabled'}\n\n"
            f"**Low Space Warning:**\n"
            f"{'✅ Enabled' if space else '❌ Disabled'}\n\n"
            f"💡 Toggle with buttons below"
        )

    async def _format_interface_settings(self, user_config: UserConfig):
        """Format interface settings"""
        ui_lang = await user_config.get_ui_language()
        compact = await user_config.get_compact_messages()

        return (
            f"🎨 **Interface Settings**\n\n"
            f"**UI Language:**\n"
            f"{ui_lang.upper()}\n\n"
            f"**Compact Messages:**\n"
            f"{'✅ Enabled - Concise messages' if compact else '❌ Disabled - Detailed messages'}\n\n"
            f"💡 Customize your experience"
        )
