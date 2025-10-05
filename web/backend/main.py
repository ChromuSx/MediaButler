"""
FastAPI Web Dashboard for MediaButler
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.config import Config
from core.database import DatabaseManager
from core.space_manager import SpaceManager
from web.backend.routers import auth, stats, downloads, users, settings
from web.backend import websocket


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

    # Initialize space manager
    space_manager = SpaceManager()

    # Store in app state
    app.state.config = config
    app.state.database = db
    app.state.space_manager = space_manager
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
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
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


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "MediaButler Dashboard API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "web.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
