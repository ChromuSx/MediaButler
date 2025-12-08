"""
FastAPI Web Dashboard for MediaButler
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import sys
import os
import logging
from pathlib import Path
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

from core.config import Config
from core.database import DatabaseManager
from core.space_manager import SpaceManager
from core.auth import AuthManager
from web.backend.routers import auth, stats, downloads, users, settings
from web.backend import websocket
from web.backend.websocket import manager as ws_manager

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    print("Starting MediaButler Web Dashboard...")

    # Initialize config
    config = Config()

    # Initialize database
    db = DatabaseManager(config.database.path)
    await db.connect()

    # Initialize AuthManager with database
    auth_manager = AuthManager(db_manager=db)
    await auth_manager.initialize()

    # Initialize space manager
    space_manager = SpaceManager()

    # Store in app state
    app.state.config = config
    app.state.database = db
    app.state.auth_manager = auth_manager
    app.state.space_manager = space_manager
    app.state.websocket_manager = ws_manager
    app.state.download_manager = None  # Will be set when bot is running

    yield

    # Shutdown
    print("Shutting down...")
    await db.close()


# Create FastAPI app
app = FastAPI(
    title="MediaButler Dashboard",
    description="Web Dashboard for MediaButler Telegram Bot",
    version="1.0.0",
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# CORS middleware configuration
def get_allowed_origins() -> list:
    """
    Get allowed CORS origins from environment with secure defaults.

    Security:
    - In production, requires explicit CORS_ORIGINS configuration
    - In development, allows localhost with common ports
    - Warns if using permissive settings
    """
    cors_origins_env = os.getenv("CORS_ORIGINS", "")

    if cors_origins_env:
        # Parse comma-separated origins
        origins = [
            origin.strip() for origin in cors_origins_env.split(",") if origin.strip()
        ]

        # Warn if wildcard is explicitly set
        if "*" in origins:
            logger.warning(
                "SECURITY WARNING: CORS is configured to allow all origins (*). "
                "This should only be used in development!"
            )

        logger.info(f"CORS origins loaded from environment: {origins}")
        return origins

    # Development defaults (localhost with common ports)
    default_origins = [
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    logger.warning(
        f"CORS_ORIGINS not configured. Using development defaults: {default_origins}. "
        f"For production, set CORS_ORIGINS in .env file!"
    )

    return default_origins


allowed_origins = get_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(stats.router, prefix="/api/stats", tags=["Statistics"])
app.include_router(downloads.router, prefix="/api/downloads", tags=["Downloads"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])

# WebSocket endpoint
app.include_router(websocket.router, prefix="/ws")


@app.get("/api/health")
@limiter.limit("60/minute")  # Limit health checks to prevent abuse
async def health_check(request: Request):
    """Health check endpoint"""
    return {"status": "healthy"}


# Mount static files for frontend (production build)
frontend_dist = project_root / "web" / "frontend" / "dist"
if frontend_dist.exists():
    # Serve static assets (JS, CSS, images, etc.)
    app.mount(
        "/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets"
    )

    @app.get("/")
    async def serve_frontend():
        """Serve frontend index.html"""
        return FileResponse(str(frontend_dist / "index.html"))

    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        """Catch-all route for SPA - serve index.html for all non-API routes"""
        # Don't intercept API routes or WebSocket
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            raise HTTPException(status_code=404, detail="Not found")

        # Check if file exists in dist (for static files like favicon, etc.)
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))

        # Otherwise, serve index.html for SPA routing
        return FileResponse(str(frontend_dist / "index.html"))

else:

    @app.get("/")
    async def root():
        """Root endpoint when frontend is not built"""
        return {
            "name": "MediaButler Dashboard API",
            "version": "1.0.0",
            "status": "running",
            "message": "Frontend not built. Build frontend with 'npm run build' in web/frontend/",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "web.backend.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
