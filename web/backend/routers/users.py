"""
Users router
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from typing import List
from datetime import datetime
from web.backend.models import UserListItem, UserDetail, UserUpdate
from web.backend.auth import require_admin, AuthUser
from core.database import DatabaseManager

router = APIRouter()


def get_db(request: Request) -> DatabaseManager:
    """Get database from app state"""
    return request.app.state.database


@router.get("/", response_model=List[UserListItem])
async def list_users(
    db: DatabaseManager = Depends(get_db),
    current_user: AuthUser = Depends(require_admin)
):
    """List all users (admin only)"""
    query = """
        SELECT
            us.user_id,
            us.total_downloads,
            COALESCE(us.total_bytes / 1073741824.0, 0) as total_gb,
            us.last_download
        FROM user_stats us
        ORDER BY us.total_downloads DESC
    """

    async with db._connection.execute(query) as cursor:
        rows = await cursor.fetchall()

    users = []
    for row in rows:
        users.append(UserListItem(
            user_id=row[0],
            telegram_id=row[0],  # Assuming user_id is telegram_id
            username=f"User {row[0]}",
            is_admin=False,  # Would need to check actual admin status
            total_downloads=row[1],
            total_size_gb=round(row[2], 2),
            last_active=datetime.fromisoformat(row[3]) if row[3] else None
        ))

    return users


@router.get("/{user_id}", response_model=UserDetail)
async def get_user_details(
    user_id: int,
    db: DatabaseManager = Depends(get_db),
    current_user: AuthUser = Depends(require_admin)
):
    """Get detailed user information (admin only)"""
    # Get user stats
    stats = await db.get_user_stats(user_id)

    if not stats:
        raise HTTPException(status_code=404, detail="User not found")

    # Calculate success rate
    total = stats.get("total_downloads", 0)
    completed = stats.get("completed_downloads", 0)
    success_rate = (completed / total * 100) if total > 0 else 0

    # Get user preferences
    prefs_query = "SELECT * FROM user_preferences WHERE user_id = ?"
    async with db._connection.execute(prefs_query, (user_id,)) as cursor:
        prefs_row = await cursor.fetchone()

    preferences = None
    if prefs_row:
        # Convert row to dict (would need column names)
        preferences = {"raw": "preferences data"}

    return UserDetail(
        user_id=user_id,
        telegram_id=user_id,
        username=f"User {user_id}",
        is_admin=False,
        total_downloads=stats.get("total_downloads", 0),
        total_size_gb=round(stats.get("total_bytes", 0) / 1073741824.0, 2),
        last_active=datetime.fromisoformat(stats["last_download"]) if stats.get("last_download") else None,
        success_rate=round(success_rate, 1),
        failed_downloads=stats.get("failed_downloads", 0),
        cancelled_downloads=stats.get("cancelled_downloads", 0),
        avg_file_size_gb=round(stats.get("avg_file_size_bytes", 0) / 1073741824.0, 2),
        preferences=preferences
    )


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    update: UserUpdate,
    db: DatabaseManager = Depends(get_db),
    current_user: AuthUser = Depends(require_admin)
):
    """Update user settings (admin only)"""
    # This would need a users table to track admin status and bans
    # For now, just return success
    return {"message": f"User {user_id} updated", "updates": update.dict(exclude_none=True)}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: DatabaseManager = Depends(get_db),
    current_user: AuthUser = Depends(require_admin)
):
    """Delete user and all their data (admin only)"""
    # Delete user downloads
    await db._connection.execute("DELETE FROM downloads WHERE user_id = ?", (user_id,))

    # Delete user stats
    await db._connection.execute("DELETE FROM user_stats WHERE user_id = ?", (user_id,))

    # Delete user preferences
    await db._connection.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))

    await db._connection.commit()

    return {"message": f"User {user_id} deleted"}
