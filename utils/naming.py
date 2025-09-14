"""
Utility per naming e parsing nomi file
"""
import re
import os
from pathlib import Path
from typing import Optional, Tuple, Dict
from models.download import SeriesInfo, TMDBResult


class FileNameParser:
    """Parser per nomi file media"""
    
    # Pattern per identificare serie TV
    TV_PATTERNS = [
        (r'[Ss](\d+)[Ee](\d+)', 'standard'),              # S01E01
        (r'[Ss](\d+)\s*[Ee](\d+)', 'spaced'),            # S01 E01
        (r'Season\s*(\d+)\s*Episode\s*(\d+)', 'verbose'), # Season 1 Episode 1
        (r'(\d+)x(\d+)', 'x_format'),                     # 1x01
        (r'[\.\s\-_](\d+)x(\d+)', 'x_format_sep'),       # .1x01
        (r'[Ee][Pp][\.\s]?(\d+)', 'episode_only'),        # EP01
    ]
    
    # Tag di qualità da rimuovere
    QUALITY_TAGS = [
        '1080p', '720p', '2160p', '4K', 'BluRay', 'WEBRip', 'WEB-DL',
        'HDTV', 'DVDRip', 'BRRip', 'x264', 'x265', 'HEVC', 'HDR',
        'ITA', 'ENG', 'SUBITA', 'DDP5.1', 'AC3', 'AAC', 'AMZN',
        'NF', 'DSNP', 'DLMux', 'BDMux', 'HDR10', 'DV', 'Atmos',
        'MULTI', 'DUAL', 'SUB', 'EXTENDED', 'REMASTERED', 'DIRECTORS.CUT'
    ]
    
    # Caratteri non validi per nomi file
    INVALID_CHARS = '<>:"|?*'
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Pulisce il nome file da caratteri problematici
        
        Args:
            filename: Nome file da pulire
            
        Returns:
            Nome file pulito
        """
        # Rimuovi caratteri non validi
        for char in cls.INVALID_CHARS:
            filename = filename.replace(char, '')
        
        # Pulisci punti multipli
        filename = re.sub(r'\.+', '.', filename)
        
        # Pulisci spazi multipli
        filename = re.sub(r'\s+', ' ', filename).strip()
        
        # Limita lunghezza
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext
        
        return filename
    
    @classmethod
    def extract_series_info(cls, filename: str) -> SeriesInfo:
        """
        Estrae informazioni serie TV dal nome file
        
        Args:
            filename: Nome file
            
        Returns:
            SeriesInfo con dati estratti
        """
        season = None
        episode = None
        series_name = None
        
        # Prova tutti i pattern
        for pattern, pattern_type in cls.TV_PATTERNS:
            match = re.search(pattern, filename, re.IGNORECASE)
            
            if match:
                if pattern_type == 'episode_only':
                    # Solo episodio, assumiamo stagione 1
                    season = 1
                    episode = int(match.group(1))
                else:
                    season = int(match.group(1))
                    episode = int(match.group(2))
                
                # Estrai nome serie (tutto prima del match)
                series_name = filename[:match.start()].strip()
                break
        
        # Se non trovato nulla, usa il nome file senza estensione
        if not series_name:
            series_name = os.path.splitext(filename)[0]
        
        # Pulisci il nome serie
        series_name = cls.clean_media_name(series_name)
        
        return SeriesInfo(
            series_name=cls.sanitize_filename(series_name),
            season=season,
            episode=episode
        )
    
    @classmethod
    def extract_movie_info(cls, filename: str) -> Tuple[str, Optional[str]]:
        """
        Estrae informazioni film dal nome file
        
        Args:
            filename: Nome file
            
        Returns:
            (nome_film, anno)
        """
        name = os.path.splitext(filename)[0]
        
        # Cerca anno
        year_match = re.search(r'[\(\[]?(\d{4})[\)\]]?', name)
        year = year_match.group(1) if year_match else None
        
        # Rimuovi anno e tutto dopo
        if year:
            name = re.sub(r'[\(\[]?\d{4}[\)\]]?.*', '', name).strip()
        
        # Pulisci nome
        name = cls.clean_media_name(name)
        
        return cls.sanitize_filename(name), year
    
    @classmethod
    def clean_media_name(cls, name: str) -> str:
        """
        Pulisce nome media da tag tecnici
        
        Args:
            name: Nome da pulire
            
        Returns:
            Nome pulito
        """
        # Rimuovi tag qualità
        for tag in cls.QUALITY_TAGS:
            name = re.sub(rf'\b{tag}\b', '', name, flags=re.IGNORECASE)
        
        # Sostituisci separatori comuni
        name = re.sub(r'(?<!\s)\.(?!\s)', ' ', name)  # Punti non circondati da spazi
        name = name.replace('_', ' ')
        
        # Rimuovi parentesi vuote
        name = re.sub(r'\(\s*\)', '', name)
        name = re.sub(r'\[\s*\]', '', name)
        
        # Pulisci caratteri finali
        name = re.sub(r'[\-\.\s]+$', '', name).strip()
        
        # Spazi multipli
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    @classmethod
    def detect_italian_content(cls, filename: str) -> bool:
        """
        Rileva se il contenuto è in italiano
        
        Args:
            filename: Nome file
            
        Returns:
            True se probabilmente italiano
        """
        italian_tags = ['ITA', 'ITALIAN', 'SUBITA', 'iTALiAN', 'DLMux']
        return any(tag in filename.upper() for tag in italian_tags)
    
    @classmethod
    def create_folder_name(
        cls,
        title: str,
        year: Optional[str] = None,
        is_italian: bool = False
    ) -> str:
        """
        Crea nome cartella per media
        
        Args:
            title: Titolo
            year: Anno (per film)
            is_italian: Se contenuto italiano
            
        Returns:
            Nome cartella
        """
        folder_name = title
        
        if year:
            folder_name = f"{title} ({year})"
        
        if is_italian:
            folder_name += " [ITA]"
        
        return cls.sanitize_filename(folder_name)
    
    @classmethod
    def create_episode_filename(
        cls,
        series_name: str,
        season: int,
        episode: int,
        episode_title: Optional[str] = None,
        extension: str = '.mp4'
    ) -> str:
        """
        Crea nome file per episodio
        
        Args:
            series_name: Nome serie
            season: Numero stagione
            episode: Numero episodio
            episode_title: Titolo episodio (opzionale)
            extension: Estensione file
            
        Returns:
            Nome file episodio
        """
        filename = f"{series_name} - S{season:02d}E{episode:02d}"
        
        if episode_title:
            # Pulisci titolo episodio
            episode_title = cls.sanitize_filename(episode_title)
            filename += f" - {episode_title}"
        
        return filename + extension
    
    @classmethod
    def create_tmdb_filename(
        cls,
        tmdb_result: TMDBResult,
        original_filename: str,
        series_info: Optional[SeriesInfo] = None
    ) -> Tuple[str, str]:
        """
        Crea nome file e cartella basato su dati TMDB
        
        Args:
            tmdb_result: Risultato TMDB
            original_filename: Nome file originale
            series_info: Info serie (se TV show)
            
        Returns:
            (nome_cartella, nome_file)
        """
        extension = Path(original_filename).suffix
        is_italian = cls.detect_italian_content(original_filename)
        
        if tmdb_result.is_movie:
            # Film
            folder_name = cls.create_folder_name(
                tmdb_result.title,
                tmdb_result.year,
                is_italian
            )
            filename = folder_name + extension
            
        else:
            # Serie TV
            folder_name = cls.create_folder_name(
                tmdb_result.title,
                is_italian=is_italian
            )
            
            if series_info and series_info.season and series_info.episode:
                filename = cls.create_episode_filename(
                    tmdb_result.title,
                    series_info.season,
                    series_info.episode,
                    series_info.episode_title,
                    extension
                )
            else:
                # Fallback al nome originale
                filename = cls.sanitize_filename(original_filename)
        
        return folder_name, filename