"""
Sistema di internazionalizzazione per MediaButler
Supporta più lingue con fallback automatico
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class LocaleConfig:
    """Configurazione locale"""
    code: str
    name: str
    emoji: str
    rtl: bool = False

class I18nManager:
    """Gestore internazionalizzazione"""
    
    # Lingue supportate
    SUPPORTED_LOCALES = {
        'it': LocaleConfig('it', 'Italiano', '🇮🇹'),
        'en': LocaleConfig('en', 'English', '🇺🇸'),
        'es': LocaleConfig('es', 'Español', '🇪🇸'),
        'fr': LocaleConfig('fr', 'Français', '🇫🇷'),
        'de': LocaleConfig('de', 'Deutsch', '🇩🇪'),
        'pt': LocaleConfig('pt', 'Português', '🇵🇹'),
        'ru': LocaleConfig('ru', 'Русский', '🇷🇺'),
        'zh': LocaleConfig('zh', '中文', '🇨🇳'),
        'ja': LocaleConfig('ja', '日本語', '🇯🇵'),
        'ar': LocaleConfig('ar', 'العربية', '🇸🇦', rtl=True)
    }
    
    def __init__(self, default_locale: str = 'it'):
        """
        Inizializza il gestore i18n
        
        Args:
            default_locale: Lingua predefinita
        """
        self.default_locale = default_locale
        self.current_locale = default_locale
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.user_locales: Dict[int, str] = {}  # user_id -> locale
        
        # Directory delle traduzioni
        self.locales_dir = Path(__file__).parent.parent / 'locales'
        self.locales_dir.mkdir(exist_ok=True)
        
        # Carica tutte le traduzioni
        self._load_all_translations()
    
    def _load_all_translations(self):
        """Carica tutte le traduzioni disponibili"""
        for locale_code in self.SUPPORTED_LOCALES:
            self._load_translation(locale_code)
    
    def _load_translation(self, locale: str):
        """
        Carica traduzione per una lingua specifica
        
        Args:
            locale: Codice lingua (es: 'it', 'en')
        """
        locale_file = self.locales_dir / f'{locale}.json'
        
        if locale_file.exists():
            try:
                with open(locale_file, 'r', encoding='utf-8') as f:
                    self.translations[locale] = json.load(f)
            except Exception as e:
                print(f"Errore caricamento {locale}.json: {e}")
                self.translations[locale] = {}
        else:
            self.translations[locale] = {}
    
    def set_user_locale(self, user_id: int, locale: str):
        """
        Imposta lingua per un utente specifico
        
        Args:
            user_id: ID utente Telegram
            locale: Codice lingua
        """
        if locale in self.SUPPORTED_LOCALES:
            self.user_locales[user_id] = locale
        else:
            raise ValueError(f"Lingua non supportata: {locale}")
    
    def get_user_locale(self, user_id: int) -> str:
        """
        Ottieni lingua per un utente
        
        Args:
            user_id: ID utente Telegram
            
        Returns:
            Codice lingua dell'utente
        """
        return self.user_locales.get(user_id, self.default_locale)
    
    def t(self, key: str, user_id: Optional[int] = None, **kwargs) -> str:
        """
        Traduce una chiave per un utente specifico
        
        Args:
            key: Chiave di traduzione (es: 'commands.start.welcome')
            user_id: ID utente (opzionale)
            **kwargs: Parametri per interpolazione
            
        Returns:
            Testo tradotto
        """
        if user_id is not None and not kwargs.get('user_id'):
            kwargs['user_id'] = user_id  # Assicurati che user_id sia sempre passato per l'interpolazione
        locale = self.get_user_locale(user_id) if user_id else self.current_locale
        return self._get_translation(key, locale, **kwargs)
    
    def _get_translation(self, key: str, locale: str, **kwargs) -> str:
        """
        Ottieni traduzione per chiave e lingua specifiche
        
        Args:
            key: Chiave traduzione
            locale: Codice lingua
            **kwargs: Parametri interpolazione
            
        Returns:
            Testo tradotto
        """
        
        # Cerca nella lingua richiesta
        translation = self._find_nested_key(self.translations.get(locale, {}), key)
        
        # Fallback alla lingua predefinita
        if translation is None:
            translation = self._find_nested_key(
                self.translations.get(self.default_locale, {}), key
            )
        
        # Fallback alla chiave stessa se non trovata
        if translation is None:
            translation = key
        
        # Interpolazione parametri
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except (KeyError, ValueError):
                print(f"Errore interpolazione per chiave: {key} con params: {kwargs}")
        
        return translation
    
    def _find_nested_key(self, data: Dict[str, Any], key: str) -> Optional[str]:
        """
        Trova chiave annidata nel dizionario traduzioni
        
        Args:
            data: Dizionario traduzioni
            key: Chiave con notazione punto (es: 'menu.main.title')
            
        Returns:
            Valore traduzione o None
        """
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return current if isinstance(current, str) else None
    
    def get_locale_info(self, locale: str) -> Optional[LocaleConfig]:
        """
        Ottieni informazioni su una lingua
        
        Args:
            locale: Codice lingua
            
        Returns:
            Configurazione lingua o None
        """
        return self.SUPPORTED_LOCALES.get(locale)
    
    def get_available_locales(self) -> Dict[str, LocaleConfig]:
        """
        Ottieni tutte le lingue disponibili
        
        Returns:
            Dizionario lingue supportate
        """
        return self.SUPPORTED_LOCALES.copy()
    
    def create_language_menu_buttons(self, user_id: int):
        """
        Crea bottoni per selezione lingua
        
        Args:
            user_id: ID utente
            
        Returns:
            Lista bottoni per Telegram
        """
        from telethon import Button
        
        current_locale = self.get_user_locale(user_id)
        buttons = []
        
        # Crea righe di 2 bottoni
        locale_items = list(self.SUPPORTED_LOCALES.items())
        for i in range(0, len(locale_items), 2):
            row = []
            for j in range(2):
                if i + j < len(locale_items):
                    code, config = locale_items[i + j]
                    marker = "✅" if code == current_locale else ""
                    text = f"{config.emoji} {config.name} {marker}"
                    row.append(Button.inline(text, f"lang_{code}"))
            buttons.append(row)
        
        # Bottone indietro
        buttons.append([Button.inline(
            self.t('buttons.back', user_id), 
            "menu_back"
        )])
        
        return buttons

# Istanza globale
_i18n_manager = None

def get_i18n() -> I18nManager:
    """
    Ottieni istanza globale del gestore i18n
    
    Returns:
        Gestore internazionalizzazione
    """
    global _i18n_manager
    if _i18n_manager is None:
        # Leggi lingua predefinita dalle variabili ambiente
        default_lang = os.getenv('DEFAULT_LANGUAGE', 'it')
        _i18n_manager = I18nManager(default_lang)
    return _i18n_manager

def t(key: str, user_id: Optional[int] = None, **kwargs) -> str:
    """
    Funzione di convenienza per traduzione
    
    Args:
        key: Chiave traduzione
        user_id: ID utente
        **kwargs: Parametri interpolazione
        
    Returns:
        Testo tradotto
    """
    return get_i18n().t(key, user_id, **kwargs)