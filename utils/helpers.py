"""
Helper utility generiche per MediaButler
"""
import os
import asyncio
import hashlib
from pathlib import Path
from typing import Any, Callable, Optional, Union
from functools import wraps
import time


class FileHelpers:
    """Helper per operazioni su file"""
    
    @staticmethod
    def get_file_hash(filepath: Path, algorithm: str = 'md5') -> str:
        """
        Calcola hash di un file
        
        Args:
            filepath: Percorso file
            algorithm: Algoritmo hash (md5, sha1, sha256)
            
        Returns:
            Hash esadecimale
        """
        hash_func = getattr(hashlib, algorithm)()
        
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    @staticmethod
    def safe_move(source: Path, destination: Path) -> bool:
        """
        Sposta file in modo sicuro
        
        Args:
            source: File sorgente
            destination: Destinazione
            
        Returns:
            True se successo
        """
        try:
            # Crea directory destinazione se non esiste
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Sposta file
            source.rename(destination)
            return True
            
        except Exception as e:
            print(f"Errore spostamento file: {e}")
            return False
    
    @staticmethod
    def get_video_extensions() -> list[str]:
        """
        Ottieni estensioni video supportate
        
        Returns:
            Lista estensioni
        """
        return [
            '.mp4', '.mkv', '.avi', '.mov', '.wmv',
            '.flv', '.webm', '.m4v', '.mpg', '.mpeg',
            '.3gp', '.ts', '.m2ts', '.vob', '.divx'
        ]
    
    @staticmethod
    def is_video_file(filename: str) -> bool:
        """
        Verifica se è un file video
        
        Args:
            filename: Nome file
            
        Returns:
            True se video
        """
        ext = Path(filename).suffix.lower()
        return ext in FileHelpers.get_video_extensions()
    
    @staticmethod
    def find_duplicate_files(directory: Path) -> dict[str, list[Path]]:
        """
        Trova file duplicati basandosi sull'hash
        
        Args:
            directory: Directory da scansionare
            
        Returns:
            Dict con hash -> lista file
        """
        hash_map = {}
        
        for filepath in directory.rglob('*'):
            if filepath.is_file():
                file_hash = FileHelpers.get_file_hash(filepath)
                
                if file_hash not in hash_map:
                    hash_map[file_hash] = []
                hash_map[file_hash].append(filepath)
        
        # Ritorna solo duplicati
        return {
            hash_val: files 
            for hash_val, files in hash_map.items() 
            if len(files) > 1
        }


class RetryHelpers:
    """Helper per retry e resilienza"""
    
    @staticmethod
    def retry(
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,)
    ):
        """
        Decorator per retry automatico
        
        Args:
            max_attempts: Numero massimo tentativi
            delay: Ritardo iniziale tra tentativi
            backoff: Moltiplicatore ritardo
            exceptions: Eccezioni da catturare
            
        Usage:
            @retry(max_attempts=3, delay=1)
            def unstable_function():
                ...
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                attempt = 0
                current_delay = delay
                
                while attempt < max_attempts:
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        attempt += 1
                        if attempt >= max_attempts:
                            raise
                        
                        print(f"Tentativo {attempt}/{max_attempts} fallito: {e}")
                        time.sleep(current_delay)
                        current_delay *= backoff
                
                return None
            
            return wrapper
        return decorator
    
    @staticmethod
    def async_retry(
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,)
    ):
        """
        Decorator per retry automatico async
        
        Args:
            max_attempts: Numero massimo tentativi
            delay: Ritardo iniziale
            backoff: Moltiplicatore ritardo
            exceptions: Eccezioni da catturare
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                attempt = 0
                current_delay = delay
                
                while attempt < max_attempts:
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        attempt += 1
                        if attempt >= max_attempts:
                            raise
                        
                        print(f"Tentativo {attempt}/{max_attempts} fallito: {e}")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                
                return None
            
            return wrapper
        return decorator


class ValidationHelpers:
    """Helper per validazioni"""
    
    @staticmethod
    def is_valid_telegram_id(user_id: Any) -> bool:
        """
        Valida ID utente Telegram
        
        Args:
            user_id: ID da validare
            
        Returns:
            True se valido
        """
        try:
            user_id = int(user_id)
            return user_id > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def sanitize_path(path_str: str) -> str:
        """
        Sanitizza percorso file
        
        Args:
            path_str: Percorso da sanitizzare
            
        Returns:
            Percorso sanitizzato
        """
        # Rimuovi caratteri pericolosi
        dangerous_chars = ['..', '~', '$', '`', '|', ';', '&', '>', '<']
        
        for char in dangerous_chars:
            path_str = path_str.replace(char, '')
        
        # Rimuovi spazi multipli
        path_str = ' '.join(path_str.split())
        
        return path_str.strip()
    
    @staticmethod
    def validate_file_size(
        size_bytes: int,
        min_size: int = 1024,  # 1 KB
        max_size: int = 10 * 1024**3  # 10 GB
    ) -> tuple[bool, str]:
        """
        Valida dimensione file
        
        Args:
            size_bytes: Dimensione in bytes
            min_size: Dimensione minima
            max_size: Dimensione massima
            
        Returns:
            (valido, messaggio_errore)
        """
        if size_bytes < min_size:
            return False, f"File troppo piccolo (minimo {min_size} bytes)"
        
        if size_bytes > max_size:
            max_gb = max_size / (1024**3)
            return False, f"File troppo grande (massimo {max_gb:.1f} GB)"
        
        return True, "OK"


class AsyncHelpers:
    """Helper per operazioni asincrone"""
    
    @staticmethod
    async def run_with_timeout(
        coro: Callable,
        timeout: float,
        default: Any = None
    ) -> Any:
        """
        Esegue coroutine con timeout
        
        Args:
            coro: Coroutine da eseguire
            timeout: Timeout in secondi
            default: Valore default se timeout
            
        Returns:
            Risultato o default
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            return default
    
    @staticmethod
    async def gather_with_limit(
        coros: list,
        limit: int = 5
    ) -> list:
        """
        Esegue coroutine con limite concorrenza
        
        Args:
            coros: Lista coroutine
            limit: Limite esecuzioni simultanee
            
        Returns:
            Lista risultati
        """
        semaphore = asyncio.Semaphore(limit)
        
        async def limited_coro(coro):
            async with semaphore:
                return await coro
        
        return await asyncio.gather(
            *[limited_coro(coro) for coro in coros],
            return_exceptions=True
        )
    
    @staticmethod
    def create_task_safe(coro: Callable) -> asyncio.Task:
        """
        Crea task in modo sicuro
        
        Args:
            coro: Coroutine
            
        Returns:
            Task creato
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        
        return loop.create_task(coro)


class SystemHelpers:
    """Helper di sistema"""
    
    @staticmethod
    def get_memory_usage() -> dict[str, float]:
        """
        Ottieni utilizzo memoria
        
        Returns:
            Dict con info memoria
        """
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            return {
                'total_gb': memory.total / (1024**3),
                'available_gb': memory.available / (1024**3),
                'percent': memory.percent,
                'used_gb': memory.used / (1024**3)
            }
        except ImportError:
            return {
                'error': 'psutil not installed'
            }
    
    @staticmethod
    def get_cpu_usage() -> float:
        """
        Ottieni utilizzo CPU
        
        Returns:
            Percentuale utilizzo CPU
        """
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except ImportError:
            return -1
    
    @staticmethod
    def is_docker() -> bool:
        """
        Verifica se in esecuzione in Docker
        
        Returns:
            True se in Docker
        """
        # Verifica file .dockerenv
        if Path('/.dockerenv').exists():
            return True
        
        # Verifica cgroup
        try:
            with open('/proc/self/cgroup', 'r') as f:
                return 'docker' in f.read()
        except:
            return False
    
    @staticmethod
    def get_environment() -> str:
        """
        Ottieni ambiente esecuzione
        
        Returns:
            Nome ambiente (docker/local/unknown)
        """
        if SystemHelpers.is_docker():
            return 'docker'
        elif os.getenv('VIRTUAL_ENV'):
            return 'virtualenv'
        else:
            return 'local'


class RateLimiter:
    """Rate limiter semplice"""
    
    def __init__(self, max_calls: int, period: float):
        """
        Inizializza rate limiter
        
        Args:
            max_calls: Numero massimo chiamate
            period: Periodo in secondi
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []
    
    async def acquire(self):
        """Acquisisce permesso per chiamata"""
        now = time.time()
        
        # Rimuovi chiamate vecchie
        self.calls = [
            call_time for call_time in self.calls
            if now - call_time < self.period
        ]
        
        # Se troppo chiamate, attendi
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                return await self.acquire()
        
        # Registra chiamata
        self.calls.append(now)
    
    def can_proceed(self) -> bool:
        """
        Verifica se può procedere (non bloccante)
        
        Returns:
            True se può procedere
        """
        now = time.time()
        
        # Rimuovi chiamate vecchie
        self.calls = [
            call_time for call_time in self.calls
            if now - call_time < self.period
        ]
        
        return len(self.calls) < self.max_calls


# Funzioni utility standalone
def human_readable_size(size_bytes: int) -> str:
    """
    Converte bytes in formato leggibile
    
    Args:
        size_bytes: Dimensione in bytes
        
    Returns:
        Stringa formattata (es: "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Tronca testo con ellipsis
    
    Args:
        text: Testo da troncare
        max_length: Lunghezza massima
        suffix: Suffisso da aggiungere
        
    Returns:
        Testo troncato
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def chunks(lst: list, n: int):
    """
    Divide lista in chunk
    
    Args:
        lst: Lista da dividere
        n: Dimensione chunk
        
    Yields:
        Chunk della lista
    """
    for i in range(0, len(lst), n):
        yield lst[i:i + n]