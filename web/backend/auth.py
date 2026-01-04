"""
Authentication and authorization utilities
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
import secrets
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "43200"))  # Default: 30 days


def _load_or_generate_secret_key() -> str:
    """
    Load JWT secret key from environment or generate a secure one.

    Security features:
    - Loads from JWT_SECRET_KEY environment variable
    - Validates that default weak key is not used in production
    - Generates and persists a secure random key if needed
    - Warns if using insecure configuration

    Returns:
        Secure JWT secret key
    """
    env_key = os.getenv("JWT_SECRET_KEY", "")

    # Check for weak default key
    weak_defaults = [
        "",
        "change-this-secret-key-in-production",
        "secret",
        "test",
        "development",
    ]

    if env_key and env_key not in weak_defaults:
        logger.info("JWT secret key loaded from environment")
        return env_key

    # Warn about insecure configuration
    if env_key in weak_defaults[1:]:  # Not empty, but weak
        logger.warning(
            f"SECURITY WARNING: JWT_SECRET_KEY is set to a weak default value. "
            f"Please set a secure random key in your .env file!"
        )

    # Generate secure random key and persist it
    secret_file = Path("data/.jwt_secret")

    # Try to load existing secret
    if secret_file.exists():
        try:
            with open(secret_file, "r") as f:
                stored_key = f.read().strip()
                if stored_key and len(stored_key) >= 32:
                    logger.info("JWT secret key loaded from file")
                    return stored_key
        except Exception as e:
            logger.warning(f"Could not load stored JWT secret: {e}")

    # Generate new secure key
    new_key = secrets.token_urlsafe(32)

    # Try to persist it
    try:
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        with open(secret_file, "w") as f:
            f.write(new_key)
        secret_file.chmod(0o600)  # Read/write for owner only
        logger.info(f"Generated new JWT secret key and saved to {secret_file}")
        logger.warning(
            "IMPORTANT: For production, set JWT_SECRET_KEY in .env file. " "Using auto-generated key from file."
        )
    except Exception as e:
        logger.error(f"Could not persist JWT secret key: {e}")
        logger.warning("Using ephemeral JWT secret key - tokens will expire on restart!")

    return new_key


SECRET_KEY = _load_or_generate_secret_key()

# HTTP Bearer scheme
security = HTTPBearer()


class AuthUser:
    """Represents an authenticated user"""

    def __init__(
        self,
        user_id: int,
        username: str,
        is_admin: bool,
        telegram_id: Optional[int] = None,
    ):
        self.user_id = user_id
        self.username = username
        self.is_admin = is_admin
        self.telegram_id = telegram_id


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Hash a password"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthUser:
    """Get the current authenticated user from JWT token"""
    token = credentials.credentials
    payload = decode_access_token(token)

    user_id: int = payload.get("user_id")
    username: str = payload.get("username")
    is_admin: bool = payload.get("is_admin", False)
    telegram_id: Optional[int] = payload.get("telegram_id")

    if user_id is None or username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthUser(user_id=user_id, username=username, is_admin=is_admin, telegram_id=telegram_id)


async def require_admin(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
    """Require the current user to be an admin"""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user
