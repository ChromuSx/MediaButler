"""
FastAPI Web Dashboard for MediaButler
"""
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.config import Config
from core.database import DatabaseManager
from core.space_manager import SpaceManager
from core.auth import AuthManager
from web.backend.routers import auth, stats, downloads, users, settings
from web.backend import websocket
from web.backend.websocket import manager as ws_manager


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
    lifespan=lifespan
)

# CORS middleware - allow frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins since frontend is served from same server
    allow_credentials=True,
    allow_methods=["*"],
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
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Mount static files for frontend (production build)
frontend_dist = project_root / "web" / "frontend" / "dist"
if frontend_dist.exists():
    # Serve static assets (JS, CSS, images, etc.)
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

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
            "message": "Frontend not built. Build frontend with 'npm run build' in web/frontend/"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "web.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
