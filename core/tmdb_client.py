"""
Client per integrazione TMDB API
"""
import aiohttp
import asyncio
from typing import Optional, List, Dict, Any
from core.config import get_config
from models.download import TMDBResult, SeriesInfo


class TMDBClient:
    """Client per The Movie Database API"""
    
    def __init__(self):
        self.config = get_config()
        self.api_key = self.config.tmdb.api_key
        self.base_url = self.config.tmdb.base_url
        self.language = self.config.tmdb.language
        self.logger = self.config.logger
        
        # Rate limiter: TMDB permette 40 richieste ogni 10 secondi
        self.rate_limiter = RateLimiter(max_calls=40, period=10)
        
        if not self.api_key:
            self.logger.warning("TMDB API key non configurata")
    
    @RetryHelpers.async_retry(max_attempts=3, delay=1, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def search(
        self, 
        query: str, 
        media_type: Optional[str] = None
    ) -> Optional[List[TMDBResult]]:
        """
        Cerca film e serie TV con retry automatico
        
        Args:
            query: Query di ricerca
            media_type: Tipo media ('movie', 'tv', None per multi)
            
        Returns:
            Lista risultati o None
        """
        if not self.api_key:
            return None
        
        # Applica rate limiting
        await self.rate_limiter.acquire()
        
        try:
            # Pulisci query
            query = self._clean_query(query)
            
            # Endpoint
            if media_type:
                endpoint = f'/search/{media_type}'
            else:
                endpoint = '/search/multi'
            
            # Parametri
            params = {
                'api_key': self.api_key,
                'query': query,
                'language': self.language,
                'include_adult': 'false'
            }
            
            # Richiesta con timeout
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}{endpoint}"
                
                # Usa helper per timeout
                response = await AsyncHelpers.run_with_timeout(
                    session.get(url, params=params),
                    timeout=5,
                    default=None
                )
                
                if response and response.status == 200:
                    data = await response.json()
                    return self._parse_results(data.get('results', []))
                else:
                    self.logger.warning(f"TMDB API error: {response.status if response else 'timeout'}")
                    return None
                        
        except Exception as e:
            self.logger.error(f"TMDB search error: {e}")
            return None
    
    @RetryHelpers.async_retry(max_attempts=2, delay=1)
    async def get_episode_details(
        self, 
        tv_id: int, 
        season: int, 
        episode: int
    ) -> Optional[Dict[str, Any]]:
        """
        Ottieni dettagli episodio con retry
        
        Args:
            tv_id: ID serie TMDB
            season: Numero stagione
            episode: Numero episodio
            
        Returns:
            Dettagli episodio o None
        """
        if not self.api_key:
            return None
        
        # Rate limiting
        await self.rate_limiter.acquire()
        
        try:
            params = {
                'api_key': self.api_key,
                'language': self.language
            }
            
            url = f"{self.base_url}/tv/{tv_id}/season/{season}/episode/{episode}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=5) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.warning(f"TMDB episode API error: {response.status}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"TMDB episode details error: {e}")
            return None
    
    def _clean_query(self, query: str) -> str:
        """
        Pulisce query di ricerca
        
        Args:
            query: Query grezza
            
        Returns:
            Query pulita
        """
        import re
        
        # Rimuovi info episodio
        query = re.sub(r'[Ss]\d+[Ee]\d+.*', '', query).strip()
        
        # Rimuovi anno tra parentesi
        query = re.sub(r'\(\d{4}\)', '', query).strip()
        
        # Rimuovi anno alla fine
        query = re.sub(r'\d{4}$', '', query).strip()
        
        # Sostituisci separatori
        query = re.sub(r'[\._]', ' ', query)
        
        # Spazi multipli
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query
    
    def _parse_results(self, results: List[Dict]) -> List[TMDBResult]:
        """
        Converte risultati API in TMDBResult
        
        Args:
            results: Risultati raw da API
            
        Returns:
            Lista TMDBResult
        """
        parsed = []
        
        for result in results:
            # Determina tipo media
            media_type = result.get('media_type', 'movie')
            
            # Estrai dati base
            if media_type == 'tv' or 'first_air_date' in result:
                title = result.get('name', 'Unknown')
                original_title = result.get('original_name', title)
                year = result.get('first_air_date', '')[:4]
                media_type = 'tv'
            else:
                title = result.get('title', 'Unknown')
                original_title = result.get('original_title', title)
                year = result.get('release_date', '')[:4]
                media_type = 'movie'
            
            tmdb_result = TMDBResult(
                id=result.get('id', 0),
                title=title,
                original_title=original_title,
                media_type=media_type,
                year=year,
                poster_path=result.get('poster_path'),
                backdrop_path=result.get('backdrop_path'),
                overview=result.get('overview', ''),
                vote_average=result.get('vote_average', 0.0)
            )
            
            parsed.append(tmdb_result)
        
        return parsed
    
    def calculate_confidence(
        self, 
        result: TMDBResult, 
        search_query: str,
        original_filename: str = ""
    ) -> int:
        """
        Calcola confidenza match
        
        Args:
            result: Risultato TMDB
            search_query: Query ricerca
            original_filename: Nome file originale
            
        Returns:
            Percentuale confidenza (0-100)
        """
        confidence = 0
        
        # Confronta titoli
        result_title = result.title.lower()
        search_title = search_query.lower()
        
        if result_title == search_title:
            confidence = 95
        elif search_title in result_title or result_title in search_title:
            confidence = 80
        else:
            # Calcola similarità base
            confidence = 60
        
        # Boost per anno se presente
        if original_filename and result.year:
            import re
            year_match = re.search(r'(\d{4})', original_filename)
            if year_match and year_match.group(1) == result.year:
                confidence = min(100, confidence + 15)
        
        return confidence
    
    def format_result(
        self, 
        result: TMDBResult,
        series_info: Optional[SeriesInfo] = None
    ) -> tuple[str, Optional[str]]:
        """
        Formatta risultato per display
        
        Args:
            result: Risultato TMDB
            series_info: Info serie se TV show
            
        Returns:
            (testo_formattato, url_poster)
        """
        # Emoji e tipo
        if result.is_tv_show:
            emoji = "📺"
            media_type_str = "Serie TV"
        else:
            emoji = "🎬"
            media_type_str = "Film"
        
        # Rating
        rating_str = f"⭐ {result.vote_average:.1f}/10" if result.vote_average > 0 else ""
        
        # Overview (tronca se troppo lunga)
        overview = result.overview
        if len(overview) > 300:
            overview = overview[:297] + "..."
        
        # Costruisci testo
        text = f"{emoji} **{media_type_str}**\n\n"
        text += f"**{result.title}**"
        if result.year:
            text += f" ({result.year})"
        text += "\n"
        
        # Info episodio se presente
        if series_info and series_info.season and series_info.episode:
            text += f"📅 Stagione {series_info.season}, Episodio {series_info.episode}\n"
        
        if rating_str:
            text += f"{rating_str}\n"
        
        if overview:
            text += f"\n📝 {overview}\n"
        
        return text, result.poster_url
    
    async def search_with_confidence(
        self,
        filename: str,
        media_hint: Optional[str] = None
    ) -> tuple[Optional[TMDBResult], int]:
        """
        Cerca e calcola confidenza automaticamente
        
        Args:
            filename: Nome file
            media_hint: Suggerimento tipo media
            
        Returns:
            (miglior_risultato, confidenza)
        """
        # Importa parser
        from utils.naming import FileNameParser
        
        # Estrai info dal nome
        if media_hint == 'tv':
            series_info = FileNameParser.extract_series_info(filename)
            search_query = series_info.series_name
        else:
            movie_name, _ = FileNameParser.extract_movie_info(filename)
            search_query = movie_name
        
        # Cerca
        results = await self.search(search_query, media_hint)
        
        if not results:
            return None, 0
        
        # Prendi primo risultato e calcola confidenza
        first_result = results[0]
        confidence = self.calculate_confidence(
            first_result,
            search_query,
            filename
        )
        
        first_result.confidence = confidence
        
        return first_result, confidence