# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MediaButler is a Python-based Telegram bot for automatic media library organization. It uses the Telethon library for Telegram integration, downloads media files, organizes them by type (movies/TV series), and integrates with TMDB for metadata retrieval.

## Development Commands

### Running the Bot
```bash
# Run locally with Python
python main.py

# Run with Docker Compose (recommended)
docker compose up -d

# Build Docker image
docker build -t mediabutler:latest .
```

### Environment Setup
```bash
# Copy example environment file
cp .env.example .env

# Install dependencies
pip install -r requirements.txt

# For development, install additional tools
pip install black flake8 mypy pytest
```

### Code Quality Commands (if available)
```bash
# Format code
black .

# Lint code
flake8 . --max-line-length=100

# Type checking
mypy .

# Run tests (if test directory exists)
python -m pytest tests/
```

## Core Architecture

### Main Components

1. **Main Entry Point (`main.py`)**: MediaButler class that orchestrates all components
2. **Core Modules (`core/`)**:
   - `config.py`: Centralized configuration with dataclasses for different config sections
   - `auth.py`: Multi-user authorization system with admin privileges
   - `downloader.py`: Async download manager with queue system and concurrent workers
   - `space_manager.py`: Disk space monitoring with automatic cleanup
   - `tmdb_client.py`: TMDB API integration for movie/TV metadata

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

### Key Architecture Patterns

- **Async/Await**: Heavy use of asyncio for concurrent operations
- **Manager Pattern**: Each core component is a manager class (AuthManager, SpaceManager, etc.)
- **Handler Registration**: Telethon event handlers are registered in handler classes
- **Configuration System**: Centralized config with environment variable loading
- **Queue-based Downloads**: Async queue system with worker pattern for downloads
- **Space-aware Processing**: Downloads respect disk space limits with waiting queues

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

### Configuration System

Uses dataclass-based configuration with sections:
- `TelegramConfig`: API credentials and session
- `TMDBConfig`: TMDB API settings with enabled check
- `PathsConfig`: Media storage paths
- `LimitsConfig`: Download and space constraints

Environment variables are loaded via python-dotenv, with fallback defaults.

### Download Flow

1. File received → FileHandlers processes → Name parsing
2. TMDB search (if enabled) → User selection via inline buttons
3. Download queued → Worker picks up → Space check
4. If space available: download directly
5. If space insufficient: queue in space_waiting_queue
6. Space monitor periodically processes waiting queue

### Key Dependencies

- `telethon`: Telegram MTProto client
- `aiohttp`: Async HTTP for TMDB API calls
- `python-dotenv`: Environment variable loading
- `cryptg`: Telegram encryption optimization

## Important Notes

- **All code, comments, strings, and user-facing messages must be in English**
- Previously used Italian but has been fully translated to English for international accessibility
- Main entry point is `main.py`, not `mediabutler.py` (Dockerfile needs updating)
- Session files are stored in configurable location for persistence
- All handlers use auth checks before processing
- Download manager uses retry logic with exponential backoff
- Space management includes automatic queue processing when space becomes available

## Code Language Standards

- **Comments**: All code comments must be in English
- **Docstrings**: All class and method documentation must be in English
- **User Interface**: All user-facing messages, buttons, and menu text must be in English
- **Log Messages**: All logging messages must be in English
- **Variable Names**: Use English variable and function names
- **Error Messages**: All error and status messages must be in English

When adding new code or modifying existing code, ensure all text follows English-only standards for consistency and international accessibility.