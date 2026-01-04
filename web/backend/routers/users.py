"""
Users router - Manages authorized users
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from typing import List
from datetime import datetime
from web.backend.models import UserListItem, UserDetail, UserUpdate, UserCreateRequest
from web.backend.auth import require_admin, AuthUser
from core.database import DatabaseManager
from core.auth import AuthManager
from web.backend.websocket import notify_user_added, notify_user_removed

router = APIRouter()


def get_db(request: Request) -> DatabaseManager:
    """Get database from app state"""
    return request.app.state.database


def get_auth_manager(request: Request) -> AuthManager:
    """Get auth manager from app state"""
    return request.app.state.auth_manager


@router.get("/", response_model=List[UserListItem])
async def list_users(
    db: DatabaseManager = Depends(get_db),
    current_user: AuthUser = Depends(require_admin),
):
    """List all authorized users with their stats (admin only)"""
    query = """
        SELECT
            au.user_id,
            au.telegram_username,
            au.is_admin,
            au.is_banned,
            au.last_seen,
            au.notes,
            COALESCE(us.total_downloads, 0) as total_downloads,
            COALESCE(us.total_bytes / 1073741824.0, 0) as total_gb
        FROM authorized_users au
        LEFT JOIN user_stats us ON au.user_id = us.user_id
        WHERE au.is_banned = 0
        ORDER BY au.is_admin DESC, au.added_at ASC
    """

    async with db._connection.execute(query) as cursor:
        rows = await cursor.fetchall()

    users = []
    for row in rows:
        users.append(
            UserListItem(
                user_id=row[0],
                telegram_id=row[0],
                username=row[1] or f"User {row[0]}",
                is_admin=bool(row[2]),
                is_banned=bool(row[3]),
                last_active=datetime.fromisoformat(row[4]) if row[4] else None,
                notes=row[5],
                total_downloads=row[6],
                total_size_gb=round(row[7], 2),
            )
        )

    return users


@router.post("/", response_model=UserListItem, status_code=201)
async def create_user(
    user_data: UserCreateRequest,
    db: DatabaseManager = Depends(get_db),
    auth_manager: AuthManager = Depends(get_auth_manager),
    current_user: AuthUser = Depends(require_admin),
):
    """Add a new authorized user (admin only)"""
    # Check if user already exists
    existing = await db.get_authorized_user(user_data.user_id)
    if existing:
        if existing.get("is_banned"):
            # Unban the user
            await db.update_authorized_user(user_data.user_id, is_banned=False)
            await auth_manager.reload_users()
            raise HTTPException(status_code=200, detail="User unbanned successfully")
        else:
            raise HTTPException(status_code=400, detail="User already authorized")

    # Add user via AuthManager (which syncs with database)
    success = await auth_manager.add_user(
        user_id=user_data.user_id,
        telegram_username=user_data.telegram_username,
        is_admin=user_data.is_admin,
        added_by=current_user.user_id,
        notes=user_data.notes,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to add user")

    # Notify via WebSocket
    await notify_user_added(user_data.user_id, user_data.telegram_username or f"User {user_data.user_id}")

    # Return the created user
    user = await db.get_authorized_user(user_data.user_id)
    return UserListItem(
        user_id=user["user_id"],
        telegram_id=user["user_id"],
        username=user["telegram_username"] or f"User {user['user_id']}",
        is_admin=bool(user["is_admin"]),
        is_banned=bool(user.get("is_banned", False)),
        last_active=(datetime.fromisoformat(user["last_seen"]) if user.get("last_seen") else None),
        notes=user.get("notes"),
        total_downloads=0,
        total_size_gb=0.0,
    )


@router.get("/{user_id}", response_model=UserDetail)
async def get_user_details(
    user_id: int,
    db: DatabaseManager = Depends(get_db),
    current_user: AuthUser = Depends(require_admin),
):
    """Get detailed user information (admin only)"""
    # Get authorized user info
    auth_user = await db.get_authorized_user(user_id)
    if not auth_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user stats
    stats = await db.get_user_stats(user_id)

    # Calculate success rate
    total = stats.get("total_downloads", 0) if stats else 0
    successful = stats.get("successful_downloads", 0) if stats else 0
    success_rate = (successful / total * 100) if total > 0 else 0

    # Get user preferences
    prefs = await db.get_user_preferences(user_id)

    return UserDetail(
        user_id=user_id,
        telegram_id=user_id,
        username=auth_user["telegram_username"] or f"User {user_id}",
        is_admin=bool(auth_user["is_admin"]),
        is_banned=bool(auth_user.get("is_banned", False)),
        notes=auth_user.get("notes"),
        total_downloads=total,
        total_size_gb=(round(stats.get("total_bytes", 0) / 1073741824.0, 2) if stats else 0.0),
        last_active=(datetime.fromisoformat(auth_user["last_seen"]) if auth_user.get("last_seen") else None),
        success_rate=round(success_rate, 1),
        failed_downloads=stats.get("failed_downloads", 0) if stats else 0,
        cancelled_downloads=stats.get("cancelled_downloads", 0) if stats else 0,
        avg_file_size_gb=0.0,  # Would need to calculate from downloads table
        preferences=prefs,
        added_at=(datetime.fromisoformat(auth_user["added_at"]) if auth_user.get("added_at") else None),
        added_by=auth_user.get("added_by"),
    )


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    update: UserUpdate,
    db: DatabaseManager = Depends(get_db),
    auth_manager: AuthManager = Depends(get_auth_manager),
    current_user: AuthUser = Depends(require_admin),
):
    """Update user settings (admin only)"""
    # Check if user exists
    auth_user = await db.get_authorized_user(user_id)
    if not auth_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update via AuthManager
    success = await auth_manager.update_user(
        user_id=user_id,
        telegram_username=update.telegram_username,
        is_admin=update.is_admin,
        notes=update.notes,
    )

    # Handle ban separately (doesn't go through AuthManager)
    if update.is_banned is not None:
        await db.update_authorized_user(user_id, is_banned=update.is_banned)
        if update.is_banned:
            # Remove from in-memory list
            await auth_manager.reload_users()

    if not success and update.is_banned is None:
        raise HTTPException(status_code=500, detail="Failed to update user")

    return {
        "message": f"User {user_id} updated",
        "updates": update.dict(exclude_none=True),
    }


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: DatabaseManager = Depends(get_db),
    auth_manager: AuthManager = Depends(get_auth_manager),
    current_user: AuthUser = Depends(require_admin),
):
    """Remove authorized user (admin only)"""
    # Check if user exists
    auth_user = await db.get_authorized_user(user_id)
    if not auth_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Remove via AuthManager (soft delete by banning)
    success = await auth_manager.remove_user(user_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove this user (may be first admin or not found)",
        )

    # Notify via WebSocket
    await notify_user_removed(user_id)

    return {"message": f"User {user_id} removed successfully"}
