"""
Pydantic models for API requests/responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Authentication models
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    user_id: int
    username: str
    is_admin: bool
    telegram_id: Optional[int] = None


# Statistics models
class OverviewStats(BaseModel):
    total_downloads: int
    successful_downloads: int
    failed_downloads: int
    total_size_gb: float
    avg_file_size_gb: float
    total_users: int
    active_downloads: int
    queue_length: int
    available_space_gb: float


class DownloadStats(BaseModel):
    date: str
    count: int
    size_gb: float


class UserStats(BaseModel):
    user_id: int
    username: Optional[str]
    total_downloads: int
    total_size_gb: float
    success_rate: float
    last_download: Optional[datetime]


class MediaTypeStats(BaseModel):
    movies: int
    tv_shows: int
    movies_gb: float
    tv_shows_gb: float


# Download models
class DownloadItem(BaseModel):
    id: int
    filename: str
    status: str
    user_id: int
    size_gb: float
    progress: Optional[float] = None
    speed_mbps: Optional[float] = None
    eta_seconds: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    media_type: Optional[str] = None
    movie_title: Optional[str] = None
    series_name: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None


class DownloadHistoryFilter(BaseModel):
    user_id: Optional[int] = None
    status: Optional[str] = None
    media_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=50, le=500)
    offset: int = Field(default=0, ge=0)


class DownloadHistoryResponse(BaseModel):
    items: List[DownloadItem]
    total: int
    limit: int
    offset: int


# User models
class UserListItem(BaseModel):
    user_id: int
    telegram_id: Optional[int]
    username: Optional[str]
    is_admin: bool
    total_downloads: int = 0
    total_size_gb: float = 0.0
    last_active: Optional[datetime] = None
    is_banned: bool = False
    notes: Optional[str] = None


class UserDetail(UserListItem):
    success_rate: float = 0.0
    failed_downloads: int = 0
    cancelled_downloads: int = 0
    avg_file_size_gb: float = 0.0
    preferences: Optional[dict] = None
    added_at: Optional[datetime] = None
    added_by: Optional[int] = None


class UserCreateRequest(BaseModel):
    user_id: int = Field(..., description="Telegram user ID")
    telegram_username: Optional[str] = Field(None, description="Telegram username")
    is_admin: bool = Field(default=False, description="Is admin user")
    notes: Optional[str] = Field(None, description="Optional notes about user")


class UserUpdate(BaseModel):
    telegram_username: Optional[str] = None
    is_admin: Optional[bool] = None
    is_banned: Optional[bool] = None
    notes: Optional[str] = None


# Settings models
class PathSettings(BaseModel):
    movies_path: str
    tv_path: str
    download_path: str


class LimitSettings(BaseModel):
    max_concurrent_downloads: int
    min_free_space_gb: float
    max_file_size_gb: Optional[float] = None


class TMDBSettings(BaseModel):
    enabled: bool
    api_key: Optional[str] = None
    language: str


class SettingsResponse(BaseModel):
    paths: PathSettings
    limits: LimitSettings
    tmdb: TMDBSettings


class SettingsUpdate(BaseModel):
    paths: Optional[PathSettings] = None
    limits: Optional[LimitSettings] = None
    tmdb: Optional[TMDBSettings] = None


# WebSocket models
class WSMessage(BaseModel):
    type: str
    data: dict


class DownloadProgressUpdate(BaseModel):
    download_id: int
    progress: float
    speed_mbps: float
    eta_seconds: int
    status: str
