# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MediaButler is a Python-based Telegram bot for automatic media library organization. It uses Telethon for Telegram integration, downloads media files, organizes them by type (movies/TV series), and integrates with TMDB for metadata. The project now includes a FastAPI backend and React frontend for web dashboard management.

## Development Commands

### Running the Bot

```bash
# Run locally with Python
python main.py

# Run with Docker Compose (recommended - runs bot, API, and web dashboard)
docker compose up -d

# Build Docker image
docker build -t mediabutler:latest .
```

### Environment Setup

```bash
# Copy example environment file
cp .env.example .env

# Install Python dependencies
pip install -r requirements.txt
```

### Web Dashboard Development

```bash
# Backend (FastAPI) - from project root
python -m web.backend.main

# Frontend (React + Vite) - from web/frontend directory
cd web/frontend
npm install
npm run dev

# Production build
npm run build
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 . --max-line-length=100

# Type checking
mypy .

# Frontend linting
cd web/frontend && npm run lint
```

## Core Architecture

### Main Components

1. **Main Entry Point (`main.py`)**: MediaButler class orchestrates all components
2. **Core Modules (`core/`)**:
   - `config.py`: Dataclass-based configuration with environment variable loading
   - `auth.py`: Multi-user authorization with admin privileges
   - `downloader.py`: Async download manager with queue system and concurrent workers
   - `space_manager.py`: Disk space monitoring with automatic cleanup
   - `tmdb_client.py`: TMDB API integration for movie/TV metadata
   - `database.py`: SQLite database for download history and statistics
   - `subtitle_manager.py`: OpenSubtitles integration for subtitle downloads

3. **Handlers (`handlers/`)**:
   - `commands.py`: Telegram command handlers with inline menu system
   - `callbacks.py`: Inline button callback handlers
   - `files.py`: File processing and media type detection

4. **Models (`models/`)**:
   - `download.py`: DownloadInfo, DownloadStatus, QueueItem dataclasses

5. **Utils (`utils/`)**:
   - `naming.py`: File name parsing and folder structure creation
   - `formatters.py`: Telegram message formatting and progress bars
   - `helpers.py`: Retry logic, validation, rate limiting utilities

6. **Web (`web/`)**:
   - `backend/`: FastAPI REST API with JWT authentication, WebSocket support
   - `frontend/`: React + Vite dashboard with Tailwind CSS

### Key Architecture Patterns

- **Async/Await**: Heavy use of asyncio for concurrent operations
- **Manager Pattern**: Each core component is a manager class (AuthManager, SpaceManager, etc.)
- **Handler Registration**: Telethon event handlers are registered in handler classes
- **Dataclass Configuration**: Centralized config with sections (TelegramConfig, TMDBConfig, PathsConfig, LimitsConfig, etc.)
- **Queue-based Downloads**: Async queue system with worker pattern for downloads
- **Space-aware Processing**: Downloads respect disk space limits with waiting queues
- **Database Persistence**: SQLite database tracks download history, statistics, and user preferences

### File Organization Strategy

The bot automatically organizes files into:
```
/media/
├── movies/
│   └── Movie Title (Year)/
│       └── Movie Title (Year).ext
└── tv/
    └── Series Name [Language]/
        └── Season XX/
            └── Series Name - SXXEXX - Episode Title.ext
```

### Download Flow

1. File received → FileHandlers processes → Name parsing
2. TMDB search (if enabled) → User selection via inline buttons
3. Download queued → Worker picks up → Space check
4. If space available: download directly
5. If space insufficient: queue in space_waiting_queue
6. Space monitor periodically processes waiting queue
7. If database enabled: save download record
8. If subtitles enabled: optionally auto-download subtitles

### Multi-Service Architecture

The project runs three services (defined in docker-compose.yml):
- **mediabutler-bot**: Telegram bot (main.py)
- **mediabutler-api**: FastAPI backend (web/backend/main.py)
- **mediabutler-web**: React frontend (web/frontend)

Services communicate via shared database and filesystem. The API can query download status and statistics from the database that the bot populates.

### Key Dependencies

**Python:**
- `telethon`: Telegram MTProto client
- `aiohttp`: Async HTTP for TMDB/OpenSubtitles API calls
- `aiosqlite`: Async SQLite database
- `fastapi` + `uvicorn`: Web API backend
- `python-dotenv`: Environment variable loading
- `cryptg`: Telegram encryption optimization

**JavaScript:**
- `react` + `react-dom`: UI framework
- `vite`: Frontend build tool
- `tailwindcss`: CSS framework
- `axios`: HTTP client for API calls
- `recharts`: Data visualization

## Important Notes

- **All code, comments, strings, and user-facing messages must be in English**
- Main entry point is `main.py` (not `mediabutler.py`)
- Session files stored in configurable location for persistence
- All handlers use auth checks before processing
- Download manager uses retry logic with exponential backoff
- Space management includes automatic queue processing when space becomes available
- Database is optional but enables download history and web dashboard statistics
- Web dashboard requires JWT_SECRET_KEY configuration for production use
