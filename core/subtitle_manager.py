"""
Gestione download sottotitoli per MediaButler
"""
import os
import asyncio
import aiohttp
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlencode

from core.config import get_config
from utils.helpers import RetryHelpers


@dataclass
class SubtitleInfo:
    """Informazioni sottotitolo"""
    language: str
    filename: str
    download_url: str
    encoding: str = 'utf-8'
    format: str = 'srt'
    rating: float = 0.0
    download_count: int = 0


class OpenSubtitlesAPI:
    """Client per API OpenSubtitles"""

    BASE_URL = 'https://api.opensubtitles.com/api/v1'

    def __init__(self):
        self.config = get_config()
        self.logger = self.config.logger
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': self.config.subtitles.opensubtitles_user_agent}
        )

        if self.config.subtitles.is_opensubtitles_configured:
            await self._authenticate()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _authenticate(self) -> bool:
        """Autentica con OpenSubtitles"""
        if not self.config.subtitles.is_opensubtitles_configured:
            return False

        login_data = {
            'username': self.config.subtitles.opensubtitles_username,
            'password': self.config.subtitles.opensubtitles_password
        }

        try:
            async with self.session.post(f'{self.BASE_URL}/login', json=login_data) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get('token')
                    self.session.headers['Authorization'] = f'Bearer {self.auth_token}'
                    self.logger.info("✅ Autenticazione OpenSubtitles riuscita")
                    return True
                else:
                    self.logger.error(f"❌ Errore autenticazione OpenSubtitles: {response.status}")
                    return False
        except Exception as e:
            self.logger.error(f"❌ Errore connessione OpenSubtitles: {e}")
            return False

    async def search_subtitles(
        self,
        video_path: Path,
        languages: List[str],
        imdb_id: Optional[str] = None,
        season: Optional[int] = None,
        episode: Optional[int] = None
    ) -> List[SubtitleInfo]:
        """Cerca sottotitoli per un video"""

        if not self.session:
            self.logger.error("Sessione non inizializzata")
            return []

        # Calcola hash del file per ricerca più precisa
        file_hash = await self._calculate_file_hash(video_path)
        file_size = video_path.stat().st_size

        # Parametri di ricerca
        params = {
            'languages': ','.join(languages),
            'moviehash': file_hash,
            'moviebytesize': file_size
        }

        # Aggiungi parametri specifici
        if imdb_id:
            params['imdb_id'] = imdb_id.replace('tt', '')

        if season is not None and episode is not None:
            params['season_number'] = season
            params['episode_number'] = episode

        try:
            url = f'{self.BASE_URL}/subtitles?' + urlencode(params)

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_subtitle_results(data)
                else:
                    self.logger.warning(f"⚠️ Ricerca sottotitoli fallita: {response.status}")
                    return []

        except Exception as e:
            self.logger.error(f"❌ Errore ricerca sottotitoli: {e}")
            return []

    def _parse_subtitle_results(self, data: Dict[str, Any]) -> List[SubtitleInfo]:
        """Parsea risultati ricerca sottotitoli"""
        subtitles = []

        for item in data.get('data', []):
            attrs = item.get('attributes', {})
            files = attrs.get('files', [])

            if not files:
                continue

            file_info = files[0]

            subtitle = SubtitleInfo(
                language=attrs.get('language', 'unknown'),
                filename=file_info.get('file_name', 'subtitle.srt'),
                download_url=attrs.get('url', ''),
                encoding=attrs.get('encoding', 'utf-8'),
                format=file_info.get('file_name', '').split('.')[-1] or 'srt',
                rating=float(attrs.get('ratings', 0)),
                download_count=int(attrs.get('download_count', 0))
            )

            subtitles.append(subtitle)

        # Ordina per rating e download count
        subtitles.sort(key=lambda x: (x.rating, x.download_count), reverse=True)
        return subtitles

    async def download_subtitle(self, subtitle_info: SubtitleInfo, output_path: Path) -> bool:
        """Scarica un sottotitolo"""
        try:
            async with self.session.get(subtitle_info.download_url) as response:
                if response.status == 200:
                    content = await response.read()

                    # Scrivi file
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(content)

                    self.logger.info(f"✅ Sottotitolo scaricato: {output_path}")
                    return True
                else:
                    self.logger.error(f"❌ Errore download sottotitolo: {response.status}")
                    return False

        except Exception as e:
            self.logger.error(f"❌ Errore download sottotitolo: {e}")
            return False

    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calcola hash OpenSubtitles per il file"""
        try:
            filesize = file_path.stat().st_size

            # Hash OpenSubtitles: primi e ultimi 64KB del file
            hash_value = filesize

            with open(file_path, 'rb') as f:
                # Primi 64KB
                for _ in range(65536 // 8):
                    buffer = f.read(8)
                    if not buffer:
                        break
                    hash_value += int.from_bytes(buffer, byteorder='little', signed=False)

                # Ultimi 64KB
                if filesize > 65536:
                    f.seek(-65536, 2)
                    for _ in range(65536 // 8):
                        buffer = f.read(8)
                        if not buffer:
                            break
                        hash_value += int.from_bytes(buffer, byteorder='little', signed=False)

            return format(hash_value & 0xFFFFFFFFFFFFFFFF, '016x')

        except Exception as e:
            self.logger.error(f"❌ Errore calcolo hash: {e}")
            return ""


class SubtitleManager:
    """Manager principale per gestione sottotitoli"""

    def __init__(self):
        self.config = get_config()
        self.logger = self.config.logger

    async def download_subtitles_for_video(
        self,
        video_path: Path,
        imdb_id: Optional[str] = None,
        season: Optional[int] = None,
        episode: Optional[int] = None,
        languages: Optional[List[str]] = None,
        force: bool = False
    ) -> List[Path]:
        """
        Scarica sottotitoli per un video

        Args:
            video_path: Percorso del file video
            imdb_id: ID IMDB per ricerca più precisa
            season: Numero stagione (per serie TV)
            episode: Numero episodio (per serie TV)
            languages: Lista lingue da scaricare (default: da config)
            force: Forza download anche se già esistenti

        Returns:
            Lista dei file sottotitoli scaricati
        """

        if not self.config.subtitles.enabled:
            self.logger.debug("Sottotitoli disabilitati")
            return []

        if not video_path.exists():
            self.logger.error(f"File video non trovato: {video_path}")
            return []

        # Usa lingue da config se non specificate
        if languages is None:
            languages = self.config.subtitles.languages

        downloaded_subtitles = []

        async with OpenSubtitlesAPI() as api:
            # Cerca sottotitoli
            self.logger.info(f"🔍 Ricerca sottotitoli per: {video_path.name}")
            subtitles = await api.search_subtitles(
                video_path, languages, imdb_id, season, episode
            )

            if not subtitles:
                self.logger.info("❌ Nessun sottotitolo trovato")
                return []

            # Scarica il migliore per ogni lingua
            for language in languages:
                lang_subtitles = [s for s in subtitles if s.language == language]

                if not lang_subtitles:
                    self.logger.info(f"❌ Nessun sottotitolo trovato per lingua: {language}")
                    continue

                best_subtitle = lang_subtitles[0]  # Già ordinati per qualità

                # Determina nome file output
                subtitle_path = self._get_subtitle_path(video_path, language, best_subtitle.format)

                # Controlla se già esiste
                if subtitle_path.exists() and not force:
                    self.logger.info(f"⏭️ Sottotitolo già esistente: {subtitle_path}")
                    downloaded_subtitles.append(subtitle_path)
                    continue

                # Scarica
                if await api.download_subtitle(best_subtitle, subtitle_path):
                    downloaded_subtitles.append(subtitle_path)
                else:
                    self.logger.error(f"❌ Errore download sottotitolo {language}")

        self.logger.info(f"✅ Scaricati {len(downloaded_subtitles)} sottotitoli")
        return downloaded_subtitles

    def _get_subtitle_path(self, video_path: Path, language: str, format: str) -> Path:
        """Genera percorso file sottotitolo"""
        video_stem = video_path.stem
        subtitle_name = f"{video_stem}.{language}.{format}"
        return video_path.parent / subtitle_name

    async def clean_old_subtitles(self, video_path: Path):
        """Rimuove sottotitoli obsoleti per un video"""
        video_stem = video_path.stem
        video_dir = video_path.parent

        # Cerca file sottotitoli correlati
        subtitle_pattern = f"{video_stem}.*"
        subtitle_extensions = ['.srt', '.sub', '.ass', '.ssa', '.vtt']

        for file_path in video_dir.glob(subtitle_pattern):
            if any(file_path.suffix.lower() == ext for ext in subtitle_extensions):
                try:
                    file_path.unlink()
                    self.logger.info(f"🗑️ Rimosso sottotitolo obsoleto: {file_path}")
                except Exception as e:
                    self.logger.error(f"❌ Errore rimozione sottotitolo: {e}")

    def get_existing_subtitles(self, video_path: Path) -> List[Path]:
        """Ottiene lista sottotitoli esistenti per un video"""
        video_stem = video_path.stem
        video_dir = video_path.parent

        subtitle_extensions = ['.srt', '.sub', '.ass', '.ssa', '.vtt']
        existing_subtitles = []

        for ext in subtitle_extensions:
            for lang in self.config.subtitles.languages:
                subtitle_path = video_dir / f"{video_stem}.{lang}{ext}"
                if subtitle_path.exists():
                    existing_subtitles.append(subtitle_path)

        return existing_subtitles