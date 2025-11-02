"""
Downloads router
"""
from fastapi import APIRouter, Depends, Request, Query
from typing import List, Optional
from datetime import datetime
from web.backend.models import (
    DownloadItem,
    DownloadHistoryFilter,
    DownloadHistoryResponse
)
from web.backend.auth import get_current_user, require_admin, AuthUser
from core.database import DatabaseManager

router = APIRouter()


def get_db(request: Request) -> DatabaseManager:
    """Get database from app state"""
    return request.app.state.database


@router.get("/history", response_model=DownloadHistoryResponse)
async def get_download_history(
    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    media_type: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: DatabaseManager = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Get download history with filters"""
    # Build query
    where_clauses = []
    params = []

    # Non-admin users can only see their own downloads
    if not current_user.is_admin:
        where_clauses.append("user_id = ?")
        params.append(current_user.user_id)
    elif user_id is not None:
        where_clauses.append("user_id = ?")
        params.append(user_id)

    if status:
        where_clauses.append("status = ?")
        params.append(status)

    if media_type:
        where_clauses.append("media_type = ?")
        params.append(media_type)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Count total
    count_query = f"SELECT COUNT(*) FROM downloads WHERE {where_sql}"
    async with db._connection.execute(count_query, params) as cursor:
        total = (await cursor.fetchone())[0]

    # Get items
    query = f"""
        SELECT
            id, filename, status, user_id, size_bytes,
            created_at, completed_at, error_message,
            media_type, movie_title, series_name, season, episode
        FROM downloads
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """

    params.extend([limit, offset])

    async with db._connection.execute(query, params) as cursor:
        rows = await cursor.fetchall()

    items = []
    for row in rows:
        items.append(DownloadItem(
            id=row[0],
            filename=row[1],
            status=row[2],
            user_id=row[3],
            size_gb=round(row[4] / 1073741824.0, 2) if row[4] else 0,
            created_at=datetime.fromisoformat(row[5]),
            completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
            error_message=row[7],
            media_type=row[8],
            movie_title=row[9],
            series_name=row[10],
            season=row[11],
            episode=row[12]
        ))

    return DownloadHistoryResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/active", response_model=List[DownloadItem])
async def get_active_downloads(
    db: DatabaseManager = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Get currently active downloads"""
    # Query downloads that are currently active (downloading, queued, or waiting for space)
    query = """
        SELECT
            id, filename, status, user_id, size_bytes,
            created_at, completed_at, error_message,
            media_type, movie_title, series_name, season, episode
        FROM downloads
        WHERE status IN ('downloading', 'queued', 'waiting_space', 'pending')
        ORDER BY created_at DESC
    """

    async with db._connection.execute(query) as cursor:
        rows = await cursor.fetchall()

    items = []
    for row in rows:
        items.append(DownloadItem(
            id=row[0],
            filename=row[1],
            status=row[2],
            user_id=row[3],
            size_gb=round(row[4] / 1073741824.0, 2) if row[4] else 0,
            created_at=datetime.fromisoformat(row[5]),
            completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
            error_message=row[7],
            media_type=row[8],
            movie_title=row[9],
            series_name=row[10],
            season=row[11],
            episode=row[12],
            progress=0.0,  # Would need real-time data from bot
            speed_mbps=0.0,
            eta_seconds=0
        ))

    return items


@router.delete("/{download_id}")
async def cancel_download(
    download_id: int,
    db: DatabaseManager = Depends(get_db),
    current_user: AuthUser = Depends(require_admin)
):
    """Cancel a download (admin only)"""
    # This would need to integrate with the actual bot's download manager
    # For now, just update database status
    query = "UPDATE downloads SET status = 'CANCELLED' WHERE id = ?"
    await db._connection.execute(query, (download_id,))
    await db._connection.commit()

    return {"message": f"Download {download_id} cancelled"}


@router.get("/{download_id}", response_model=DownloadItem)
async def get_download_details(
    download_id: int,
    db: DatabaseManager = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """Get details of a specific download"""
    query = """
        SELECT
            id, filename, status, user_id, size_bytes,
            created_at, completed_at, error_message,
            media_type, movie_title, series_name, season, episode
        FROM downloads
        WHERE id = ?
    """

    async with db._connection.execute(query, (download_id,)) as cursor:
        row = await cursor.fetchone()

    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Download not found")

    # Check permission
    if not current_user.is_admin and row[3] != current_user.user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Access denied")

    return DownloadItem(
        id=row[0],
        filename=row[1],
        status=row[2],
        user_id=row[3],
        size_gb=round(row[4] / 1073741824.0, 2) if row[4] else 0,
        created_at=datetime.fromisoformat(row[5]),
        completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
        error_message=row[7],
        media_type=row[8],
        movie_title=row[9],
        series_name=row[10],
        season=row[11],
        episode=row[12]
    )
