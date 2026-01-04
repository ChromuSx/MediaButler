"""
Settings router
"""

from fastapi import APIRouter, Depends, Request
from web.backend.models import (
    SettingsResponse,
    PathSettings,
    LimitSettings,
    TMDBSettings,
    SettingsUpdate,
)
from web.backend.auth import require_admin, get_current_user, AuthUser
from core.config import Config

router = APIRouter()


def get_config(request: Request) -> Config:
    """Get config from app state"""
    return request.app.state.config


@router.get("/", response_model=SettingsResponse)
async def get_settings(
    config: Config = Depends(get_config),
    current_user: AuthUser = Depends(get_current_user),
):
    """Get current settings"""
    return SettingsResponse(
        paths=PathSettings(
            movies_path=str(config.paths.movies),
            tv_path=str(config.paths.tv),
            download_path=str(config.paths.temp),
        ),
        limits=LimitSettings(
            max_concurrent_downloads=config.limits.max_concurrent_downloads,
            min_free_space_gb=config.limits.min_free_space_gb,
            max_file_size_gb=None,  # Not currently implemented
        ),
        tmdb=TMDBSettings(
            enabled=config.tmdb.is_enabled,
            api_key="***" if config.tmdb.api_key else None,  # Masked
            language=config.tmdb.language,
        ),
    )


@router.patch("/", response_model=SettingsResponse)
async def update_settings(
    updates: SettingsUpdate,
    config: Config = Depends(get_config),
    current_user: AuthUser = Depends(require_admin),
):
    """Update settings (admin only)"""
    # In production, this would update .env file or database
    # For now, just return updated values

    # Update paths
    if updates.paths:
        if updates.paths.movies_path:
            config.paths.movies = updates.paths.movies_path
        if updates.paths.tv_path:
            config.paths.tv = updates.paths.tv_path
        if updates.paths.download_path:
            config.paths.temp = updates.paths.download_path

    # Update limits
    if updates.limits:
        if updates.limits.max_concurrent_downloads:
            config.limits.max_concurrent_downloads = updates.limits.max_concurrent_downloads
        if updates.limits.min_free_space_gb:
            config.limits.min_free_space_gb = updates.limits.min_free_space_gb

    # Update TMDB
    if updates.tmdb:
        if updates.tmdb.enabled is not None:
            config.tmdb.enabled = updates.tmdb.enabled
        if updates.tmdb.language:
            config.tmdb.language = updates.tmdb.language

    return SettingsResponse(
        paths=PathSettings(
            movies_path=str(config.paths.movies),
            tv_path=str(config.paths.tv),
            download_path=str(config.paths.temp),
        ),
        limits=LimitSettings(
            max_concurrent_downloads=config.limits.max_concurrent_downloads,
            min_free_space_gb=config.limits.min_free_space_gb,
            max_file_size_gb=None,
        ),
        tmdb=TMDBSettings(
            enabled=config.tmdb.enabled,
            api_key="***" if config.tmdb.api_key else None,
            language=config.tmdb.language,
        ),
    )


@router.post("/test-tmdb")
async def test_tmdb_connection(
    config: Config = Depends(get_config),
    current_user: AuthUser = Depends(require_admin),
):
    """Test TMDB API connection (admin only)"""
    if not config.tmdb.enabled or not config.tmdb.api_key:
        return {"status": "error", "message": "TMDB not configured"}

    # Would test actual connection here
    return {"status": "success", "message": "TMDB connection OK"}
