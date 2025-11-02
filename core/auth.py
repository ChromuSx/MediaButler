"""
Authentication and authorization management
"""
from typing import Optional, List, TYPE_CHECKING
from telethon import events
from core.config import get_config

if TYPE_CHECKING:
    from core.database import DatabaseManager


class AuthManager:
    """User authentication manager with database-backed dynamic user management"""

    def __init__(self, db_manager: Optional['DatabaseManager'] = None):
        self.config = get_config()
        self.db_manager = db_manager
        self.authorized_users = self.config.auth.authorized_users.copy()
        self.admin_mode = self.config.auth.admin_mode
        self._initialized = False

    async def initialize(self):
        """
        Initialize AuthManager with database synchronization
        Must be called after database is connected
        """
        if self._initialized or not self.db_manager:
            return

        # Sync users from .env to database
        if self.authorized_users:
            await self.db_manager.sync_authorized_users_from_config(self.authorized_users)

        # Load all authorized users from database
        await self.reload_users()
        self._initialized = True
        self.config.logger.info(f"AuthManager initialized with {len(self.authorized_users)} users")

    async def reload_users(self):
        """Reload authorized users from database"""
        if not self.db_manager:
            return

        db_users = await self.db_manager.get_authorized_users()
        self.authorized_users = [user['user_id'] for user in db_users if not user.get('is_banned', False)]
        self.config.logger.info(f"Reloaded {len(self.authorized_users)} authorized users from database")
        
    async def check_authorized(self, event: events.NewMessage.Event) -> bool:
        """
        Check if user is authorized

        Args:
            event: Telegram event

        Returns:
            True if authorized, False otherwise
        """
        user_id = event.sender_id
        user = await event.get_sender()
        username = user.username or "NoUsername"

        # Admin mode: first user becomes admin
        if self.admin_mode and len(self.authorized_users) == 0:
            self.authorized_users.append(user_id)
            self.config.logger.info(f"First user added as admin: {username} (ID: {user_id})")

            # Add to database if available
            if self.db_manager:
                await self.db_manager.add_authorized_user(
                    user_id=user_id,
                    telegram_username=username,
                    is_admin=True,
                    notes="First user - auto-added as admin"
                )

            await event.reply(
                f"🔐 **First Access - Admin Mode**\n\n"
                f"You have been added as administrator!\n"
                f"Your ID: `{user_id}`\n\n"
                f"Add `AUTHORIZED_USERS={user_id}` to the .env file to make it permanent."
            )
            return True

        # Check authorization
        if user_id not in self.authorized_users:
            self.config.logger.warning(
                f"Unauthorized access attempt from: {username} (ID: {user_id})"
            )

            await event.reply(
                f"❌ **Access Denied**\n\n"
                f"You are not authorized to use this bot.\n"
                f"Your ID: `{user_id}`\n\n"
                f"Contact the administrator to be added."
            )
            return False

        # Update last seen and username in database
        if self.db_manager:
            # Update username if changed
            db_user = await self.db_manager.get_authorized_user(user_id)
            if db_user and db_user.get('telegram_username') != username:
                await self.db_manager.update_authorized_user(user_id, telegram_username=username)

            # Update last seen
            await self.db_manager.update_user_last_seen(user_id)

        return True
    
    async def check_callback_authorized(
        self, 
        event: events.CallbackQuery.Event
    ) -> bool:
        """
        Check authorization for callback

        Args:
            event: Callback event

        Returns:
            True if authorized, False otherwise
        """
        if event.sender_id not in self.authorized_users:
            await event.answer("❌ Not authorized", alert=True)
            return False
        return True
    
    def is_admin(self, user_id: int) -> bool:
        """
        Check if user is admin

        Args:
            user_id: Telegram user ID

        Returns:
            True if admin (first user)
        """
        if not self.authorized_users:
            return False
        return user_id == self.authorized_users[0]
    
    def is_authorized(self, user_id: int) -> bool:
        """
        Check if user is authorized

        Args:
            user_id: Telegram user ID

        Returns:
            True if authorized
        """
        return user_id in self.authorized_users
    
    async def add_user(
        self,
        user_id: int,
        telegram_username: Optional[str] = None,
        is_admin: bool = False,
        added_by: Optional[int] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Add an authorized user (with database sync)

        Args:
            user_id: User ID to add
            telegram_username: Telegram username
            is_admin: Is admin user
            added_by: User ID who added this user
            notes: Optional notes

        Returns:
            True if added, False if already present
        """
        if user_id in self.authorized_users:
            return False

        # Add to database
        if self.db_manager:
            success = await self.db_manager.add_authorized_user(
                user_id=user_id,
                telegram_username=telegram_username,
                is_admin=is_admin,
                added_by=added_by,
                notes=notes
            )
            if not success:
                return False

        # Add to in-memory list
        self.authorized_users.append(user_id)
        self.config.logger.info(f"Added authorized user: {user_id} ({telegram_username})")
        return True

    async def remove_user(self, user_id: int) -> bool:
        """
        Remove an authorized user (with database sync)

        Args:
            user_id: User ID to remove

        Returns:
            True if removed, False if not present or is first admin
        """
        # Don't allow removing the first admin
        if user_id not in self.authorized_users:
            return False

        first_admin = self.get_admin_id()
        if user_id == first_admin:
            self.config.logger.warning(f"Cannot remove first admin: {user_id}")
            return False

        # Remove from database (soft delete)
        if self.db_manager:
            await self.db_manager.remove_authorized_user(user_id)

        # Remove from in-memory list
        self.authorized_users.remove(user_id)
        self.config.logger.info(f"Removed authorized user: {user_id}")
        return True

    async def update_user(
        self,
        user_id: int,
        telegram_username: Optional[str] = None,
        is_admin: Optional[bool] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update authorized user information

        Args:
            user_id: User ID to update
            telegram_username: New username
            is_admin: New admin status
            notes: New notes

        Returns:
            True if updated, False otherwise
        """
        if user_id not in self.authorized_users:
            return False

        # Update in database
        if self.db_manager:
            return await self.db_manager.update_authorized_user(
                user_id=user_id,
                telegram_username=telegram_username,
                is_admin=is_admin,
                notes=notes
            )

        return False
    
    def get_authorized_users(self) -> List[int]:
        """
        Get list of authorized users

        Returns:
            List of authorized user IDs
        """
        return self.authorized_users.copy()
    
    def get_admin_id(self) -> Optional[int]:
        """
        Get admin ID

        Returns:
            Admin ID or None
        """
        return self.authorized_users[0] if self.authorized_users else None
    
    async def require_admin(
        self, 
        event: events.NewMessage.Event
    ) -> bool:
        """
        Require admin privileges

        Args:
            event: Telegram event

        Returns:
            True if admin, False otherwise
        """
        user_id = event.sender_id
        
        if not self.is_admin(user_id):
            await event.reply("❌ Only the administrator can execute this command")
            return False
        
        return True
    
    def can_manage_download(
        self, 
        user_id: int, 
        download_user_id: int
    ) -> bool:
        """
        Check if a user can manage a download

        Args:
            user_id: ID of user who wants to manage
            download_user_id: ID of download owner

        Returns:
            True if can manage (owner or admin)
        """
        return user_id == download_user_id or self.is_admin(user_id)