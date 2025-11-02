#!/usr/bin/env python3
"""
MediaButler - Telegram Bot for media organization
Main entry point
"""
import sys
import asyncio
from pathlib import Path

# Add current directory to path for relative imports
sys.path.insert(0, str(Path(__file__).parent))

from telethon import TelegramClient
from core.config import get_config
from core.auth import AuthManager
from core.space_manager import SpaceManager
from core.tmdb_client import TMDBClient
from core.downloader import DownloadManager, set_database_manager
from core.database import DatabaseManager
from handlers.commands import CommandHandlers
from handlers.callbacks import CallbackHandlers
from handlers.files import FileHandlers


class MediaButler:
    """Main MediaButler bot class"""
    
    def __init__(self):
        """Initialize the bot"""
        self.config = get_config()
        self.logger = self.config.logger

        # Log configuration
        self.config.log_config()

        # Initialize Telegram client
        self.client = TelegramClient(
            self.config.telegram.session_path,
            self.config.telegram.api_id,
            self.config.telegram.api_hash,
            connection_retries=5,
            retry_delay=1,
            auto_reconnect=True
        )

        # Initialize database (will be connected in start())
        self.database_manager = None
        if self.config.database.enabled:
            self.database_manager = DatabaseManager(self.config.database.path)

        # Initialize managers
        self.auth_manager = AuthManager()
        self.space_manager = SpaceManager()
        self.tmdb_client = TMDBClient() if self.config.tmdb.is_enabled else None
        self.download_manager = DownloadManager(
            client=self.client,
            space_manager=self.space_manager,
            tmdb_client=self.tmdb_client
        )
        
        # Initialize handlers
        self.command_handlers = CommandHandlers(
            client=self.client,
            auth_manager=self.auth_manager,
            space_manager=self.space_manager,
            download_manager=self.download_manager,
            database_manager=self.database_manager
        )
        
        self.callback_handlers = CallbackHandlers(
            client=self.client,
            auth_manager=self.auth_manager,
            download_manager=self.download_manager,
            space_manager=self.space_manager
        )
        
        self.file_handlers = FileHandlers(
            client=self.client,
            auth_manager=self.auth_manager,
            download_manager=self.download_manager,
            tmdb_client=self.tmdb_client,
            space_manager=self.space_manager,
            database_manager=self.database_manager
        )
        
    async def start(self):
        """Start the bot"""
        self.logger.info("=== MEDIABUTLER ENHANCED - STARTING ===")

        # Connect to database
        if self.database_manager:
            await self.database_manager.connect()
            set_database_manager(self.database_manager)
            self.logger.info("✅ Database initialized")

        # Start Telegram client
        await self.client.start(bot_token=self.config.telegram.bot_token)

        # Register handlers
        self.command_handlers.register()
        self.callback_handlers.register()
        self.file_handlers.register()

        # Setup bot commands for autocomplete
        await self.command_handlers.setup_bot_commands()

        # Start workers
        await self.download_manager.start_workers()

        self.logger.info("✅ Bot started and ready!")
        self.logger.info(f"👥 Authorized users: {len(self.auth_manager.authorized_users)}")
        self.logger.info(f"🎯 TMDB: {'Active' if self.tmdb_client else 'Disabled'}")
        self.logger.info(f"💾 Database: {'Active' if self.database_manager else 'Disabled'}")
        self.logger.info(f"📥 Concurrent downloads: max {self.config.limits.max_concurrent_downloads}")
        self.logger.info(f"💾 Minimum reserved space: {self.config.limits.min_free_space_gb} GB")

        # Keep the bot running
        try:
            await self.client.run_until_disconnected()
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the bot"""
        self.logger.info("Stopping bot...")

        # Stop download manager
        await self.download_manager.stop()

        # Close database
        if self.database_manager:
            await self.database_manager.close()
            self.logger.info("Database connection closed")

        # Disconnect client
        await self.client.disconnect()

        self.logger.info("Bot stopped")
    
    def run(self):
        """Run the bot"""
        try:
            self.client.loop.run_until_complete(self.start())
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Critical error: {e}", exc_info=True)
        finally:
            sys.exit(0)


def main():
    """Main entry point"""
    bot = MediaButler()
    bot.run()


if __name__ == '__main__':
    main()