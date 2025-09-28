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
    
    # Pattern per identificare serie TV con scoring di confidenza
    TV_PATTERNS = [
        # Pattern ad alta confidenza (90-100)
        (r'[Ss](\d{1,2})[Ee](\d{1,3})', 'standard', 100),              # S01E01
        (r'[Ss](\d{1,2})\s*[Ee](\d{1,3})', 'spaced', 95),              # S01 E01
        (r'Season\s*(\d{1,2})\s*Episode\s*(\d{1,3})', 'verbose', 90),  # Season 1 Episode 1

        # Pattern media confidenza (70-89)
        (r'(\d{1,2})\s+x\s+(\d{1,3})', 'x_format_spaced', 88),        # 12 x 5
        (r'(\d{1,2})x(\d{1,3})', 'x_format', 85),                      # 1x01
        (r'[\.\s\-_](\d{1,2})x(\d{1,3})', 'x_format_sep', 80),        # .1x01
        (r'[Ss](\d{1,2})[Ee](\d{1,3})-[Ee](\d{1,3})', 'multi_episode', 75), # S01E01-E03

        # Pattern nuovi
        (r'(\d{1,2})\.(\d{1,3})', 'dot_format', 70),                   # 1.01
        (r'[\[\(](\d{1,3})[\]\)]', 'anime_bracket', 75),               # [01] per anime
        (r'(?:Episode|Ep)[\s\.]?(\d{1,3})', 'episode_word', 65),       # Episode 1
        (r'[Pp]art[\s\.]?(\d{1,3})', 'part_format', 60),              # Part 1

        # Pattern a bassa confidenza (50-69)
        (r'(\d)(\d{2})(?![0-9])', 'concatenated', 55),                 # 101 (1x01)
        (r'[Ee][Pp][\.\s]?(\d{1,3})', 'episode_only', 50),            # EP01
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
        Estrae informazioni serie TV dal nome file con confidence scoring

        Args:
            filename: Nome file

        Returns:
            SeriesInfo con dati estratti
        """
        best_match = None
        best_confidence = 0

        # Prova tutti i pattern con scoring
        for pattern, pattern_type, confidence in cls.TV_PATTERNS:
            match = re.search(pattern, filename, re.IGNORECASE)

            if match:
                season = None
                episode = None
                end_episode = None

                # Gestione pattern specifici
                if pattern_type == 'episode_only' or pattern_type == 'episode_word' or pattern_type == 'part_format':
                    season = 1
                    episode = int(match.group(1))
                elif pattern_type == 'anime_bracket':
                    season = 1
                    episode = int(match.group(1))
                elif pattern_type == 'concatenated':
                    # 101 = S1E01
                    season = int(match.group(1))
                    episode = int(match.group(2))
                elif pattern_type == 'multi_episode':
                    season = int(match.group(1))
                    episode = int(match.group(2))
                    end_episode = int(match.group(3)) if len(match.groups()) >= 3 else None
                else:
                    season = int(match.group(1))
                    episode = int(match.group(2))

                # Validazione
                if not cls._validate_season_episode(season, episode):
                    continue

                # Calcola confidence totale
                total_confidence = confidence

                # Bonus per context
                total_confidence += cls._calculate_context_bonus(filename, match, pattern_type)

                if total_confidence > best_confidence:
                    best_confidence = total_confidence

                    # Estrai solo la parte del nome serie (prima del pattern SE)
                    series_name_raw = filename[:match.start()].strip()

                    # Rimuovi separatori finali comuni (./-/_)
                    series_name_raw = re.sub(r'[\.\-_\s]+$', '', series_name_raw)

                    # Se il nome sembra contenere ancora info extra (anni, qualità, ecc),
                    # prova a pulirlo ulteriormente
                    series_name = cls._extract_clean_series_name(series_name_raw)

                    # Estrai titolo episodio se possibile
                    episode_title = cls._extract_episode_title(filename, match)

                    best_match = {
                        'series_name': series_name,
                        'season': season,
                        'episode': episode,
                        'end_episode': end_episode,
                        'episode_title': episode_title,
                        'confidence': total_confidence
                    }

        # Se non trovato nulla, usa il nome file senza estensione
        if not best_match:
            series_name = os.path.splitext(filename)[0]
            best_match = {
                'series_name': series_name,
                'season': None,
                'episode': None,
                'end_episode': None,
                'episode_title': None,
                'confidence': 0
            }

        # Pulisci il nome serie
        clean_name = cls.clean_media_name(best_match['series_name'])

        return SeriesInfo(
            series_name=cls.sanitize_filename(clean_name),
            season=best_match['season'],
            episode=best_match['episode'],
            episode_title=best_match['episode_title'],
            end_episode=best_match['end_episode'],
            confidence=best_match['confidence']
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

    @classmethod
    def _validate_season_episode(cls, season: int, episode: int) -> bool:
        """
        Valida numeri stagione/episodio

        Args:
            season: Numero stagione
            episode: Numero episodio

        Returns:
            True se validi
        """
        if season is None or episode is None:
            return False

        # Controlli ragionevolezza
        if season < 1 or season > 50:  # Max 50 stagioni
            return False

        if episode < 1 or episode > 999:  # Max 999 episodi
            return False

        # Controllo episodi troppo alti per stagioni basse (eccetto anime)
        if season <= 5 and episode > 100 and episode < 999:
            return False

        return True

    @classmethod
    def _calculate_context_bonus(cls, filename: str, match, pattern_type: str) -> int:
        """
        Calcola bonus di confidenza basato sul contesto

        Args:
            filename: Nome file completo
            match: Match regex
            pattern_type: Tipo di pattern

        Returns:
            Bonus confidenza (0-20)
        """
        bonus = 0

        # Bonus se il pattern è circondato da separatori
        start_char = filename[match.start()-1] if match.start() > 0 else ' '
        end_char = filename[match.end()] if match.end() < len(filename) else ' '

        if start_char in [' ', '.', '-', '_', '[', '(']:
            bonus += 5
        if end_char in [' ', '.', '-', '_', ']', ')']:
            bonus += 5

        # Bonus per presenza di parole chiave serie TV
        tv_keywords = ['series', 'season', 'episode', 'ep', 'stagione']
        filename_lower = filename.lower()

        for keyword in tv_keywords:
            if keyword in filename_lower:
                bonus += 3
                break

        # Malus per formati che potrebbero essere anni
        if pattern_type == 'concatenated':
            # Se sembra un anno (1900-2030), riduci confidence
            full_num = int(match.group(0)) if match.group(0).isdigit() else 0
            if 1900 <= full_num <= 2030:
                bonus -= 10

        return max(0, min(20, bonus))  # Limita tra 0 e 20

    @classmethod
    def _extract_clean_series_name(cls, raw_name: str) -> str:
        """
        Estrae il nome serie pulito rimuovendo tag extra

        Args:
            raw_name: Nome serie grezzo

        Returns:
            Nome serie pulito
        """
        # Lista di separatori che potrebbero indicare inizio di metadati extra
        separators = ['.', '-', '_', ' ']

        # Prova a trovare un punto naturale di taglio
        # Prima cerca pattern comuni che indicano fine del titolo
        end_patterns = [
            r'(?i)\b(?:' + '|'.join(cls.QUALITY_TAGS) + r')\b',  # Tag qualità
            r'\b\d{4}\b',  # Anno
            r'\b(?:season|s)\d+\b',  # Stagione
            r'\b(?:complete|completa)\b',  # Serie completa
            r'\b(?:multi|dual)\b',  # Audio multi
        ]

        clean_name = raw_name

        for pattern in end_patterns:
            match = re.search(pattern, clean_name)
            if match:
                # Taglia al primo match e pulisci
                clean_name = clean_name[:match.start()].strip()
                clean_name = re.sub(r'[\.\-_\s]+$', '', clean_name)
                break

        # Se il nome è ancora vuoto o troppo corto, usa l'originale
        if len(clean_name.strip()) < 3:
            clean_name = raw_name

        return clean_name

    @classmethod
    def _extract_episode_title(cls, filename: str, match) -> Optional[str]:
        """
        Estrae titolo episodio dal nome file

        Args:
            filename: Nome file
            match: Match regex del pattern SE

        Returns:
            Titolo episodio se trovato
        """
        # Cerca dopo il pattern SE fino a tag qualità o fine
        after_match = filename[match.end():].strip()

        # Pattern per trovare titolo (fino a tag qualità o parentesi)
        title_patterns = [
            r'^[\s\-\.]*(.+?)[\[\(]',  # Fino a [ o (
            r'^[\s\-\.]*(.+?)\s+(?:' + '|'.join(cls.QUALITY_TAGS) + r')',  # Fino a tag qualità
            r'^[\s\-\.]*(.+?)\.(?:mkv|mp4|avi|mov|wmv|flv|webm|ts)$',  # Fino a estensione
            r'^[\s\-\.]*(.+?)$'  # Resto della stringa
        ]

        for pattern in title_patterns:
            title_match = re.search(pattern, after_match, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                # Pulisci il titolo
                title = re.sub(r'[\-\.]+$', '', title).strip()
                if len(title) > 3:  # Minimo 3 caratteri per essere valido
                    return cls.sanitize_filename(title)

        return None