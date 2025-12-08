"""
Pytest configuration and fixtures for MediaButler tests
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import Config, PathsConfig, LimitsConfig, TMDBConfig, AuthConfig
from core.database import DatabaseManager
from core.space_manager import SpaceManager


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for the test session.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """
    Create a temporary directory for test files.
    Automatically cleaned up after test.
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_paths(temp_dir):
    """
    Create test paths configuration with temp directories.
    """
    movies_path = temp_dir / "movies"
    tv_path = temp_dir / "tv"
    temp_path = temp_dir / "temp"

    movies_path.mkdir(parents=True, exist_ok=True)
    tv_path.mkdir(parents=True, exist_ok=True)
    temp_path.mkdir(parents=True, exist_ok=True)

    return PathsConfig(
        movies=movies_path,
        tv=tv_path,
        temp=temp_path
    )


@pytest.fixture
def test_limits():
    """
    Create test limits configuration.
    """
    return LimitsConfig(
        max_concurrent_downloads=2,
        min_free_space_gb=1.0,
        warning_threshold_gb=2.0,
        space_check_interval=10,
        max_file_size_gb=5.0
    )


@pytest.fixture
def test_tmdb_config():
    """
    Create test TMDB configuration.
    """
    return TMDBConfig(
        api_key="test_api_key",
        language="en-US"
    )


@pytest.fixture
def test_auth_config():
    """
    Create test auth configuration.
    """
    return AuthConfig(
        authorized_users=[123456, 789012],
        admin_mode=False
    )


@pytest.fixture
async def test_database(temp_dir):
    """
    Create a test database with temp file.
    Automatically cleaned up after test.
    """
    db_path = temp_dir / "test_mediabutler.db"
    db = DatabaseManager(db_path)
    await db.connect()

    yield db

    await db.close()
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def space_manager(test_paths):
    """
    Create a SpaceManager instance for testing.
    """
    return SpaceManager()


@pytest.fixture
def mock_telegram_client():
    """
    Create a mock Telethon client for testing.
    """
    client = AsyncMock()
    client.is_connected.return_value = True
    client.get_me = AsyncMock(return_value=Mock(id=123456, username="test_bot"))
    return client


@pytest.fixture
def mock_tmdb_client():
    """
    Create a mock TMDB client for testing.
    """
    client = AsyncMock()
    client.search_movie = AsyncMock(return_value=[
        {
            "id": 550,
            "title": "Fight Club",
            "release_date": "1999-10-15",
            "confidence": 95
        }
    ])
    client.search_tv = AsyncMock(return_value=[
        {
            "id": 1396,
            "name": "Breaking Bad",
            "first_air_date": "2008-01-20",
            "confidence": 98
        }
    ])
    return client


@pytest.fixture
def sample_video_file(temp_dir):
    """
    Create a sample video file for testing.
    """
    video_path = temp_dir / "sample_video.mp4"
    video_path.write_bytes(b"fake video content" * 1000)  # ~18KB
    yield video_path
    if video_path.exists():
        video_path.unlink()


@pytest.fixture
def sample_movie_name():
    """
    Sample movie filename for testing.
    """
    return "Fight.Club.1999.1080p.BluRay.x264.mp4"


@pytest.fixture
def sample_tv_name():
    """
    Sample TV show filename for testing.
    """
    return "Breaking.Bad.S01E01.Pilot.720p.WEB-DL.mp4"


# Test data fixtures
@pytest.fixture
def sample_download_data():
    """
    Sample download data for testing.
    """
    return {
        "user_id": 123456,
        "filename": "test_movie.mp4",
        "size_bytes": 1024 * 1024 * 100,  # 100MB
        "media_type": "MOVIE",
        "tmdb_id": 550,
        "final_path": "/media/movies/Test Movie (2023)/Test Movie (2023).mp4"
    }


@pytest.fixture
def sample_user_data():
    """
    Sample user data for testing.
    """
    return {
        "user_id": 123456,
        "username": "test_user",
        "first_name": "Test",
        "last_name": "User",
        "is_admin": False
    }
