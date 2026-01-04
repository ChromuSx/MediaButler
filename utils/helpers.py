"""
General helper utilities for MediaButler
"""

import os
import asyncio
import hashlib
from pathlib import Path
from typing import Any, Callable, Union
from functools import wraps
import time


class FileHelpers:
    """Helper for file operations"""

    @staticmethod
    def get_file_hash(filepath: Path, algorithm: str = "md5") -> str:
        """
        Calculate file hash (synchronous, blocking)

        Args:
            filepath: File path
            algorithm: Hash algorithm (md5, sha1, sha256)

        Returns:
            Hexadecimal hash

        Note:
            This is a blocking operation. For async contexts, use get_file_hash_async()
        """
        hash_func = getattr(hashlib, algorithm)()

        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)

        return hash_func.hexdigest()

    @staticmethod
    async def get_file_hash_async(
        filepath: Path, algorithm: str = "md5", timeout: float = 30.0
    ) -> str:
        """
        Calculate file hash asynchronously (non-blocking)

        Uses asyncio.to_thread to offload CPU-intensive hashing to thread pool.
        This prevents blocking the event loop for large files.

        Args:
            filepath: File path
            algorithm: Hash algorithm (md5, sha1, sha256)
            timeout: Timeout in seconds (default: 30)

        Returns:
            Hexadecimal hash, or "unknown" if timeout/error

        Example:
            >>> file_hash = await FileHelpers.get_file_hash_async(Path("video.mp4"))
            >>> print(file_hash)  # "5d41402abc4b2a76b9719d911017c592"
        """
        try:
            # Run blocking hash calculation in thread pool
            hash_result = await asyncio.wait_for(
                asyncio.to_thread(FileHelpers.get_file_hash, filepath, algorithm),
                timeout=timeout,
            )
            return hash_result
        except asyncio.TimeoutError:
            return "timeout"
        except Exception as e:
            print(f"Error calculating file hash: {e}")
            return "unknown"

    @staticmethod
    def safe_move(source: Path, destination: Path) -> bool:
        """
        Move file safely

        Args:
            source: Source file
            destination: Destination

        Returns:
            True if successful
        """
        try:
            # Create destination directory if not exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Try rename first (faster)
            try:
                source.rename(destination)
                return True
            except OSError as e:
                # If cross-device link error, use copy + delete
                if e.errno == 18:  # EXDEV: Invalid cross-device link
                    import shutil

                    shutil.copy2(source, destination)
                    source.unlink()
                    return True
                else:
                    raise

        except Exception as e:
            print(f"Error moving file: {e}")
            return False

    @staticmethod
    def get_video_extensions() -> list[str]:
        """
        Get supported video extensions

        Returns:
            Extension list
        """
        return [
            ".mp4",
            ".mkv",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",
            ".m4v",
            ".mpg",
            ".mpeg",
            ".3gp",
            ".ts",
            ".m2ts",
            ".vob",
            ".divx",
        ]

    @staticmethod
    def is_video_file(filename: str) -> bool:
        """
        Check if it's a video file

        Args:
            filename: Filename

        Returns:
            True if video
        """
        ext = Path(filename).suffix.lower()
        return ext in FileHelpers.get_video_extensions()

    @staticmethod
    def get_archive_extensions() -> list[str]:
        """
        Get supported archive extensions

        Returns:
            Extension list
        """
        return [".zip", ".rar", ".7z"]

    @staticmethod
    def is_archive_file(filename: str) -> bool:
        """
        Check if it's an archive file

        Args:
            filename: Filename

        Returns:
            True if archive
        """
        ext = Path(filename).suffix.lower()
        return ext in FileHelpers.get_archive_extensions()

    @staticmethod
    def is_video_or_archive_file(filename: str) -> bool:
        """
        Check if it's a video or archive file

        Args:
            filename: Filename

        Returns:
            True if video or archive
        """
        return FileHelpers.is_video_file(filename) or FileHelpers.is_archive_file(filename)

    @staticmethod
    def find_duplicate_files(directory: Path) -> dict[str, list[Path]]:
        """
        Find duplicate files based on hash

        Args:
            directory: Directory to scan

        Returns:
            Dict with hash -> file list
        """
        hash_map = {}

        for filepath in directory.rglob("*"):
            if filepath.is_file():
                file_hash = FileHelpers.get_file_hash(filepath)

                if file_hash not in hash_map:
                    hash_map[file_hash] = []
                hash_map[file_hash].append(filepath)

        # Return only duplicates
        return {hash_val: files for hash_val, files in hash_map.items() if len(files) > 1}


class RetryHelpers:
    """Helper for retry and resilience"""

    @staticmethod
    def retry(
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,),
    ):
        """
        Decorator for automatic retry

        Args:
            max_attempts: Maximum number of attempts
            delay: Initial delay between attempts
            backoff: Delay multiplier
            exceptions: Exceptions to catch

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

                        print(f"Attempt {attempt}/{max_attempts} failed: {e}")
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
        exceptions: tuple = (Exception,),
    ):
        """
        Decorator for automatic async retry

        Args:
            max_attempts: Maximum number of attempts
            delay: Initial delay
            backoff: Delay multiplier
            exceptions: Exceptions to catch
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

                        print(f"Attempt {attempt}/{max_attempts} failed: {e}")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff

                return None

            return wrapper

        return decorator


class ValidationHelpers:
    """Helper for validations"""

    @staticmethod
    def is_valid_telegram_id(user_id: Any) -> bool:
        """
        Validate Telegram user ID

        Args:
            user_id: ID to validate

        Returns:
            True if valid
        """
        try:
            user_id = int(user_id)
            return user_id > 0
        except (ValueError, TypeError):
            return False

    @staticmethod
    def sanitize_path(path_str: str) -> str:
        """
        Sanitize file path

        Args:
            path_str: Path to sanitize

        Returns:
            Sanitized path
        """
        # Remove dangerous characters
        dangerous_chars = ["..", "~", "$", "`", "|", ";", "&", ">", "<"]

        for char in dangerous_chars:
            path_str = path_str.replace(char, "")

        # Remove multiple spaces
        path_str = " ".join(path_str.split())

        return path_str.strip()

    @staticmethod
    def validate_user_path(
        user_path: Union[str, Path], allowed_base_paths: list[Path]
    ) -> tuple[bool, str]:
        """
        Validate that user-provided path is within allowed base directories.
        Prevents path traversal attacks.

        Args:
            user_path: User-provided path to validate
            allowed_base_paths: List of allowed base directories

        Returns:
            (is_valid, error_message) tuple

        Example:
            >>> validate_user_path('/media/movies/subfolder', [Path('/media')])
            (True, 'OK')
            >>> validate_user_path('/etc/passwd', [Path('/media')])
            (False, 'Path is outside allowed directories')
        """
        try:
            # Convert to Path and resolve to absolute path
            path = Path(user_path).resolve()

            # Check if path is within any allowed base
            for base_path in allowed_base_paths:
                base_resolved = base_path.resolve()
                try:
                    # is_relative_to is available in Python 3.9+
                    if path.is_relative_to(base_resolved):
                        return True, "OK"
                except AttributeError:
                    # Fallback for Python < 3.9
                    try:
                        path.relative_to(base_resolved)
                        return True, "OK"
                    except ValueError:
                        continue

            # Path is not within any allowed base
            allowed_paths_str = ", ".join(str(p) for p in allowed_base_paths)
            return (
                False,
                f"Path must be within allowed directories: {allowed_paths_str}",
            )

        except (ValueError, RuntimeError, OSError) as e:
            return False, f"Invalid path: {str(e)}"

    @staticmethod
    def validate_file_size(
        size_bytes: int,
        min_size: int = 1024,  # 1 KB
        max_size: int = 10 * 1024**3,  # 10 GB
    ) -> tuple[bool, str]:
        """
        Validate file size

        Args:
            size_bytes: Size in bytes
            min_size: Minimum size
            max_size: Maximum size

        Returns:
            (valid, error_message)
        """
        if size_bytes < min_size:
            return False, f"File too small (minimum {min_size} bytes)"

        if size_bytes > max_size:
            max_gb = max_size / (1024**3)
            return False, f"File too large (maximum {max_gb:.1f} GB)"

        return True, "OK"


class AsyncHelpers:
    """Helper for asynchronous operations"""

    @staticmethod
    async def run_with_timeout(coro: Callable, timeout: float, default: Any = None) -> Any:
        """
        Execute coroutine with timeout

        Args:
            coro: Coroutine to execute
            timeout: Timeout in seconds
            default: Default value if timeout

        Returns:
            Result or default
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            return default

    @staticmethod
    async def gather_with_limit(coros: list, limit: int = 5) -> list:
        """
        Execute coroutines with concurrency limit

        Args:
            coros: Coroutine list
            limit: Simultaneous execution limit

        Returns:
            Result list
        """
        semaphore = asyncio.Semaphore(limit)

        async def limited_coro(coro):
            async with semaphore:
                return await coro

        return await asyncio.gather(*[limited_coro(coro) for coro in coros], return_exceptions=True)

    @staticmethod
    def create_task_safe(coro: Callable) -> asyncio.Task:
        """
        Create task safely

        Args:
            coro: Coroutine

        Returns:
            Created task
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        return loop.create_task(coro)


class SystemHelpers:
    """System helpers"""

    @staticmethod
    def get_memory_usage() -> dict[str, float]:
        """
        Get memory usage

        Returns:
            Dict with memory info
        """
        try:
            import psutil

            memory = psutil.virtual_memory()
            return {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "percent": memory.percent,
                "used_gb": memory.used / (1024**3),
            }
        except ImportError:
            return {"error": "psutil not installed"}

    @staticmethod
    def get_cpu_usage() -> float:
        """
        Get CPU usage

        Returns:
            CPU usage percentage
        """
        try:
            import psutil

            return psutil.cpu_percent(interval=1)
        except ImportError:
            return -1

    @staticmethod
    def is_docker() -> bool:
        """
        Check if running in Docker

        Returns:
            True if in Docker
        """
        # Check .dockerenv file
        if Path("/.dockerenv").exists():
            return True

        # Check cgroup
        try:
            with open("/proc/self/cgroup", "r") as f:
                return "docker" in f.read()
        except:
            return False

    @staticmethod
    def get_environment() -> str:
        """
        Get execution environment

        Returns:
            Environment name (docker/local/unknown)
        """
        if SystemHelpers.is_docker():
            return "docker"
        elif os.getenv("VIRTUAL_ENV"):
            return "virtualenv"
        else:
            return "local"


class RateLimiter:
    """Simple rate limiter"""

    def __init__(self, max_calls: int, period: float):
        """
        Initialize rate limiter

        Args:
            max_calls: Maximum number of calls
            period: Period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    async def acquire(self):
        """Acquire permission for call"""
        now = time.time()

        # Remove old calls
        self.calls = [call_time for call_time in self.calls if now - call_time < self.period]

        # If too many calls, wait
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                return await self.acquire()

        # Register call
        self.calls.append(now)

    def can_proceed(self) -> bool:
        """
        Check if can proceed (non-blocking)

        Returns:
            True if can proceed
        """
        now = time.time()

        # Remove old calls
        self.calls = [call_time for call_time in self.calls if now - call_time < self.period]

        return len(self.calls) < self.max_calls


# Standalone utility functions
def human_readable_size(size_bytes: int) -> str:
    """
    Convert bytes to readable format

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g.: "1.5 GB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text with ellipsis

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def chunks(lst: list, n: int):
    """
    Divide list into chunks

    Args:
        lst: List to divide
        n: Chunk size

    Yields:
        List chunk
    """
    for i in range(0, len(lst), n):
        yield lst[i : i + n]
