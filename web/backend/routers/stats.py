"""
Statistics router
"""
from fastapi import APIRouter, Depends, Request
from typing import List
from datetime import datetime, timedelta
from web.backend.models import (
    OverviewStats,
    DownloadStats,
    UserStats,
    MediaTypeStats
)
from web.backend.auth import get_current_user, AuthUser
from core.database import DatabaseManager

router = APIRouter()


def get_db(request: Request) -> DatabaseManager:
    """Get database from app state"""
    return request.app.state.database


@router.get("/overview", response_model=OverviewStats)
async def get_overview_stats(
    db: DatabaseManager = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Get overview statistics"""
    # Get all stats from database
    all_stats = await db.get_all_stats()

    # Get active downloads count (would need to integrate with actual bot state)
    active_downloads = 0

    # Get queue length (would need to integrate with actual bot state)
    queue_length = 0

    # Get available space (would need to check actual filesystem)
    available_space_gb = 100.0  # Placeholder

    return OverviewStats(
        total_downloads=all_stats.get("total_downloads", 0),
        successful_downloads=all_stats.get("successful_downloads", 0),
        failed_downloads=all_stats.get("failed_downloads", 0),
        total_size_gb=all_stats.get("total_size_gb", 0.0),
        total_users=all_stats.get("total_users", 0),
        active_downloads=active_downloads,
        queue_length=queue_length,
        available_space_gb=available_space_gb
    )


@router.get("/downloads-trend", response_model=List[DownloadStats])
async def get_downloads_trend(
    days: int = 7,
    db: DatabaseManager = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Get download trends over time"""
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Query database for downloads grouped by date
    query = """
        SELECT
            DATE(created_at) as date,
            COUNT(*) as count,
            COALESCE(SUM(size_bytes) / 1073741824.0, 0) as size_gb
        FROM downloads
        WHERE created_at >= ? AND created_at <= ?
        GROUP BY DATE(created_at)
        ORDER BY date ASC
    """

    async with db._connection.execute(query, (start_date, end_date)) as cursor:
        rows = await cursor.fetchall()

    results = []
    for row in rows:
        results.append(DownloadStats(
            date=row[0],
            count=row[1],
            size_gb=round(row[2], 2)
        ))

    return results


@router.get("/media-types", response_model=MediaTypeStats)
async def get_media_type_stats(
    db: DatabaseManager = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Get statistics by media type"""
    query = """
        SELECT
            media_type,
            COUNT(*) as count,
            COALESCE(SUM(size_bytes) / 1073741824.0, 0) as size_gb
        FROM downloads
        WHERE status = 'COMPLETED'
        GROUP BY media_type
    """

    async with db._connection.execute(query) as cursor:
        rows = await cursor.fetchall()

    movies = 0
    tv_shows = 0
    movies_gb = 0.0
    tv_shows_gb = 0.0

    for row in rows:
        media_type = row[0]
        count = row[1]
        size_gb = row[2]

        if media_type == "MOVIE":
            movies = count
            movies_gb = size_gb
        elif media_type == "TV_SHOW":
            tv_shows = count
            tv_shows_gb = size_gb

    return MediaTypeStats(
        movies=movies,
        tv_shows=tv_shows,
        movies_gb=round(movies_gb, 2),
        tv_shows_gb=round(tv_shows_gb, 2)
    )


@router.get("/top-users", response_model=List[UserStats])
async def get_top_users(
    limit: int = 10,
    db: DatabaseManager = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Get top users by download count"""
    query = """
        SELECT
            user_id,
            total_downloads,
            COALESCE(total_bytes / 1073741824.0, 0) as total_gb,
            CASE
                WHEN total_downloads > 0
                THEN (CAST(successful_downloads AS FLOAT) / total_downloads) * 100
                ELSE 0
            END as success_rate,
            last_download
        FROM user_stats
        ORDER BY total_downloads DESC
        LIMIT ?
    """

    async with db._connection.execute(query, (limit,)) as cursor:
        rows = await cursor.fetchall()

    results = []
    for row in rows:
        results.append(UserStats(
            user_id=row[0],
            username=f"User {row[0]}",  # Would need to fetch actual username
            total_downloads=row[1],
            total_size_gb=round(row[2], 2),
            success_rate=round(row[3], 1),
            last_download=datetime.fromisoformat(row[4]) if row[4] else None
        ))

    return results
