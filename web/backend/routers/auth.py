"""
Authentication router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address
from web.backend.models import LoginRequest, TokenResponse, UserInfo
from web.backend.auth import (
    create_access_token,
    get_current_user,
    verify_password,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    AuthUser
)

router = APIRouter()

# Rate limiter for this router
limiter = Limiter(key_func=get_remote_address)


# In-memory user store for demo - in production, use database
# Default admin user: username="admin", password="admin"
USERS_DB = {
    "admin": {
        "user_id": 1,
        "username": "admin",
        "password_hash": get_password_hash("admin"),
        "is_admin": True,
        "telegram_id": None
    }
}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # Strict rate limit to prevent brute force attacks
async def login(request: Request, credentials: LoginRequest):
    """
    Login endpoint - returns JWT token

    Rate limited to 5 attempts per minute per IP to prevent brute force attacks.
    """
    user = USERS_DB.get(credentials.username)

    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "user_id": user["user_id"],
            "username": user["username"],
            "is_admin": user["is_admin"],
            "telegram_id": user.get("telegram_id")
        },
        expires_delta=access_token_expires
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: AuthUser = Depends(get_current_user)):
    """Get current user information"""
    return UserInfo(
        user_id=current_user.user_id,
        username=current_user.username,
        is_admin=current_user.is_admin,
        telegram_id=current_user.telegram_id
    )


@router.post("/logout")
async def logout(current_user: AuthUser = Depends(get_current_user)):
    """Logout endpoint - client should discard token"""
    return {"message": "Successfully logged out"}
