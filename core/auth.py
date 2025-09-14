"""
Gestione autenticazione e autorizzazioni
"""
from typing import Optional, List
from telethon import events
from core.config import get_config


class AuthManager:
    """Gestore autenticazione utenti"""
    
    def __init__(self):
        self.config = get_config()
        self.authorized_users = self.config.auth.authorized_users.copy()
        self.admin_mode = self.config.auth.admin_mode
        
    async def check_authorized(self, event: events.NewMessage.Event) -> bool:
        """
        Verifica se l'utente è autorizzato
        
        Args:
            event: Evento Telegram
            
        Returns:
            True se autorizzato, False altrimenti
        """
        user_id = event.sender_id
        user = await event.get_sender()
        username = user.username or "NoUsername"
        
        # Modalità admin: primo utente diventa admin
        if self.admin_mode and len(self.authorized_users) == 0:
            self.authorized_users.append(user_id)
            self.config.logger.info(f"First user added as admin: {username} (ID: {user_id})")
            
            await event.reply(
                f"🔐 **Primo Accesso - Modalità Admin**\n\n"
                f"Sei stato aggiunto come amministratore!\n"
                f"Il tuo ID: `{user_id}`\n\n"
                f"Aggiungi `AUTHORIZED_USERS={user_id}` al file .env per renderlo permanente."
            )
            return True
        
        # Verifica autorizzazione
        if user_id not in self.authorized_users:
            self.config.logger.warning(
                f"Tentativo di accesso non autorizzato da: {username} (ID: {user_id})"
            )
            
            await event.reply(
                f"❌ **Accesso Negato**\n\n"
                f"Non sei autorizzato ad usare questo bot.\n"
                f"Il tuo ID: `{user_id}`\n\n"
                f"Contatta l'amministratore per essere aggiunto."
            )
            return False
        
        return True
    
    async def check_callback_authorized(
        self, 
        event: events.CallbackQuery.Event
    ) -> bool:
        """
        Verifica autorizzazione per callback
        
        Args:
            event: Evento callback
            
        Returns:
            True se autorizzato, False altrimenti
        """
        if event.sender_id not in self.authorized_users:
            await event.answer("❌ Non autorizzato", alert=True)
            return False
        return True
    
    def is_admin(self, user_id: int) -> bool:
        """
        Verifica se l'utente è admin
        
        Args:
            user_id: ID utente Telegram
            
        Returns:
            True se è admin (primo utente)
        """
        if not self.authorized_users:
            return False
        return user_id == self.authorized_users[0]
    
    def is_authorized(self, user_id: int) -> bool:
        """
        Verifica se l'utente è autorizzato
        
        Args:
            user_id: ID utente Telegram
            
        Returns:
            True se autorizzato
        """
        return user_id in self.authorized_users
    
    def add_user(self, user_id: int) -> bool:
        """
        Aggiunge un utente autorizzato
        
        Args:
            user_id: ID utente da aggiungere
            
        Returns:
            True se aggiunto, False se già presente
        """
        if user_id not in self.authorized_users:
            self.authorized_users.append(user_id)
            return True
        return False
    
    def remove_user(self, user_id: int) -> bool:
        """
        Rimuove un utente autorizzato
        
        Args:
            user_id: ID utente da rimuovere
            
        Returns:
            True se rimosso, False se non presente
        """
        if user_id in self.authorized_users and user_id != self.authorized_users[0]:
            self.authorized_users.remove(user_id)
            return True
        return False
    
    def get_authorized_users(self) -> List[int]:
        """
        Ottieni lista utenti autorizzati
        
        Returns:
            Lista ID utenti autorizzati
        """
        return self.authorized_users.copy()
    
    def get_admin_id(self) -> Optional[int]:
        """
        Ottieni ID dell'admin
        
        Returns:
            ID admin o None
        """
        return self.authorized_users[0] if self.authorized_users else None
    
    async def require_admin(
        self, 
        event: events.NewMessage.Event
    ) -> bool:
        """
        Richiede privilegi admin
        
        Args:
            event: Evento Telegram
            
        Returns:
            True se è admin, False altrimenti
        """
        user_id = event.sender_id
        
        if not self.is_admin(user_id):
            await event.reply("❌ Solo l'amministratore può eseguire questo comando")
            return False
        
        return True
    
    def can_manage_download(
        self, 
        user_id: int, 
        download_user_id: int
    ) -> bool:
        """
        Verifica se un utente può gestire un download
        
        Args:
            user_id: ID utente che vuole gestire
            download_user_id: ID utente proprietario del download
            
        Returns:
            True se può gestire (proprietario o admin)
        """
        return user_id == download_user_id or self.is_admin(user_id)