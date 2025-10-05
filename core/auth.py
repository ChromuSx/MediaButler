"""
Authentication and authorization management
"""
from typing import Optional, List
from telethon import events
from core.config import get_config


class AuthManager:
    """User authentication manager"""
    
    def __init__(self):
        self.config = get_config()
        self.authorized_users = self.config.auth.authorized_users.copy()
        self.admin_mode = self.config.auth.admin_mode
        
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
            
            await event.reply(
                f"🔐 **First Access - Admin Mode**\n\n"
                f"You have been added as administrator!\n"
                f"Your ID: `{user_id}`\n\n"
                f"Add `AUTHORIZED_USERS={user_id}` to the .env file to make it permanent."
            )
            return True
        
        # Verifica autorizzazione
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
    
    def add_user(self, user_id: int) -> bool:
        """
        Add an authorized user

        Args:
            user_id: User ID to add

        Returns:
            True if added, False if already present
        """
        if user_id not in self.authorized_users:
            self.authorized_users.append(user_id)
            return True
        return False
    
    def remove_user(self, user_id: int) -> bool:
        """
        Remove an authorized user

        Args:
            user_id: User ID to remove

        Returns:
            True if removed, False if not present
        """
        if user_id in self.authorized_users and user_id != self.authorized_users[0]:
            self.authorized_users.remove(user_id)
            return True
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