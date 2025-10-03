"""
Gestione spazio disco e monitoraggio
"""
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from core.config import get_config


@dataclass
class DiskUsage:
    """Informazioni utilizzo disco"""
    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float
    
    @property
    def available_for_download(self) -> float:
        """Spazio disponibile per download (considerando riserva)"""
        config = get_config()
        return max(0, self.free_gb - config.limits.min_free_space_gb)
    
    @property
    def status_emoji(self) -> str:
        """Emoji stato spazio"""
        config = get_config()
        if self.free_gb > config.limits.warning_threshold_gb:
            return "🟢"
        elif self.free_gb > config.limits.min_free_space_gb:
            return "🟡"
        else:
            return "🔴"
    
    def can_download(self, size_gb: float) -> bool:
        """Check if there's space for a download"""
        config = get_config()
        return self.free_gb >= (size_gb + config.limits.min_free_space_gb)


class SpaceManager:
    """Disk space manager"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = self.config.logger
        
    def get_disk_usage(self, path: Path) -> Optional[DiskUsage]:
        """
        Ottieni informazioni utilizzo disco
        
        Args:
            path: Percorso da verificare
            
        Returns:
            DiskUsage o None se errore
        """
        try:
            stat = shutil.disk_usage(str(path))
            return DiskUsage(
                total_gb=stat.total / (1024**3),
                used_gb=stat.used / (1024**3),
                free_gb=stat.free / (1024**3),
                percent_used=(stat.used / stat.total) * 100
            )
        except Exception as e:
            self.logger.error(f"Errore controllo spazio per {path}: {e}")
            return None
    
    def get_free_space_gb(self, path: Path) -> float:
        """
        Ottieni spazio libero in GB
        
        Args:
            path: Percorso da verificare
            
        Returns:
            Spazio libero in GB
        """
        usage = self.get_disk_usage(path)
        return usage.free_gb if usage else 0.0
    
    def check_space_available(
        self, 
        path: Path, 
        required_gb: float
    ) -> Tuple[bool, float]:
        """
        Verifica se c'è spazio sufficiente
        
        Args:
            path: Percorso dove scaricare
            required_gb: Spazio richiesto in GB
            
        Returns:
            (disponibile, spazio_libero_gb)
        """
        usage = self.get_disk_usage(path)
        if not usage:
            return False, 0.0
        
        total_required = required_gb + self.config.limits.min_free_space_gb
        return usage.free_gb >= total_required, usage.free_gb
    
    def get_all_disk_usage(self) -> Dict[str, DiskUsage]:
        """
        Ottieni utilizzo disco per tutti i percorsi
        
        Returns:
            Dizionario con utilizzo per ogni percorso
        """
        usage = {}
        
        # Movies
        movies_usage = self.get_disk_usage(self.config.paths.movies)
        if movies_usage:
            usage['movies'] = movies_usage
        
        # TV Shows
        tv_usage = self.get_disk_usage(self.config.paths.tv)
        if tv_usage:
            usage['tv'] = tv_usage
        
        # Se sono sullo stesso disco, mantieni solo uno
        if 'movies' in usage and 'tv' in usage:
            if usage['movies'].total_gb == usage['tv'].total_gb:
                usage['media'] = usage['movies']
                del usage['movies']
                del usage['tv']
        
        return usage
    
    def format_disk_status(self) -> str:
        """
        Formatta stato disco per display
        
        Returns:
            Stringa formattata con stato dischi
        """
        usage = self.get_all_disk_usage()
        
        if not usage:
            return "❌ Impossibile verificare lo spazio disco"
        
        status = "💾 **Stato Spazio Disco**\n\n"
        
        for name, disk in usage.items():
            display_name = name.capitalize()
            status += f"{disk.status_emoji} **{display_name}:**\n"
            status += f"• Totale: {disk.total_gb:.1f} GB\n"
            status += f"• Usato: {disk.used_gb:.1f} GB ({disk.percent_used:.1f}%)\n"
            status += f"• Libero: {disk.free_gb:.1f} GB\n"
            status += f"• Disponibile per download: {disk.available_for_download:.1f} GB\n\n"
        
        status += f"⚙️ **Soglie configurate:**\n"
        status += f"• Spazio minimo: {self.config.limits.min_free_space_gb} GB\n"
        status += f"• Avviso sotto: {self.config.limits.warning_threshold_gb} GB"
        
        return status
    
    def format_space_warning(
        self, 
        path: Path, 
        required_gb: float
    ) -> str:
        """
        Formatta avviso spazio insufficiente
        
        Args:
            path: Percorso destinazione
            required_gb: Spazio richiesto
            
        Returns:
            Messaggio di avviso formattato
        """
        usage = self.get_disk_usage(path)
        if not usage:
            return "⚠️ Impossibile verificare lo spazio disponibile"
        
        total_required = required_gb + self.config.limits.min_free_space_gb
        missing = total_required - usage.free_gb
        
        return (
            f"⏸️ **Waiting for space**\n\n"
            f"❌ Insufficient space!\n"
            f"📊 Required: {required_gb:.1f} GB (+ {self.config.limits.min_free_space_gb} GB reserved)\n"
            f"💾 Available: {usage.free_gb:.1f} GB\n"
            f"🎯 Missing: {missing:.1f} GB\n\n"
            f"The download will start automatically when there's space."
        )
    
    def cleanup_empty_folders(self, folder_path: Path) -> bool:
        """
        Rimuove cartelle vuote
        
        Args:
            folder_path: Percorso cartella da verificare
            
        Returns:
            True se rimossa, False altrimenti
        """
        try:
            if folder_path.exists() and not any(folder_path.iterdir()):
                folder_path.rmdir()
                self.logger.info(f"Cartella vuota rimossa: {folder_path}")
                return True
        except Exception as e:
            self.logger.warning(f"Impossibile rimuovere cartella {folder_path}: {e}")
        
        return False
    
    def smart_cleanup(self, file_path: Path, is_movie: bool = True):
        """
        Pulizia intelligente dopo cancellazione download
        
        Args:
            file_path: Percorso file cancellato
            is_movie: True se film, False se serie TV
        """
        try:
            # Rimuovi file parziale se esiste
            if file_path.exists():
                file_path.unlink()
                self.logger.info(f"File parziale eliminato: {file_path}")
            
            # Pulizia cartelle vuote
            if is_movie:
                # Per i film, rimuovi la cartella del film se vuota
                movie_folder = file_path.parent
                self.cleanup_empty_folders(movie_folder)
            else:
                # Per le serie TV, rimuovi stagione e serie se vuote
                season_folder = file_path.parent
                series_folder = season_folder.parent
                
                if self.cleanup_empty_folders(season_folder):
                    self.cleanup_empty_folders(series_folder)
                    
        except Exception as e:
            self.logger.error(f"Errore durante pulizia: {e}")