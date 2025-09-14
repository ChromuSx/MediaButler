# 🎬 MediaButler - Telegram Media Organizer Bot

<div align="center">
  <img src="logo.png" alt="MediaButler" width="200">
</div>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/docker-ready-brightgreen.svg" alt="Docker Ready">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/telegram-bot-blue.svg" alt="Telegram Bot">
</p>

<p align="center">
  <strong>Modular Telegram bot for automatic organization of your media library</strong>
</p>

## ✨ Features

- 🎬 **Smart Organization** - Automatically creates folders for movies and TV series
- 📺 **Series Detection** - Recognizes season/episode patterns (S01E01, 1x01, etc.)
- 🎯 **TMDB Integration** - Metadata, posters, and automatic renaming
- 📁 **Clean Structure** - Movies in individual folders, series organized by season
- ⏳ **Queue Management** - Multiple downloads with configurable limits
- 💾 **Space Monitoring** - Real-time control with automatic queue management
- 👥 **Multi-user** - Whitelist system for authorized users
- 🔄 **Resilience** - Resume and automatic retry support
- 🐳 **Docker Ready** - Easy deployment with Docker Compose

## 🏗️ Architecture

The project uses a modular architecture for maximum maintainability and extensibility:

```
mediabutler/
├── main.py                 # Main entry point
├── core/                   # Core system modules
│   ├── __init__.py
│   ├── config.py          # Centralized configuration
│   ├── auth.py            # Authentication management
│   ├── downloader.py      # Download and queue management
│   ├── space_manager.py   # Disk space monitoring
│   └── tmdb_client.py     # TMDB API client
├── handlers/              # Telegram event handlers
│   ├── __init__.py
│   ├── commands.py        # Command handlers (/start, /status, etc.)
│   ├── callbacks.py       # Inline button handlers
│   └── files.py           # Received file handlers
├── models/                # Data models
│   ├── __init__.py
│   └── download.py        # Download info dataclass
├── utils/                 # Utilities and helpers
│   ├── __init__.py
│   ├── naming.py          # File name parser and management
│   ├── formatters.py      # Message formatting
│   └── helpers.py         # Generic helpers
└── requirements.txt       # Python dependencies
```

### 📦 Main Modules

#### Core
- **`config`**: Centralized configuration management with validation
- **`auth`**: Multi-user authorization system with admin
- **`downloader`**: Download manager with queues, retry, and error handling
- **`space_manager`**: Space monitoring and smart cleanup
- **`tmdb_client`**: TMDB integration with rate limiting

#### Handlers
- **`commands`**: All bot commands (`/start`, `/status`, `/space`, etc.)
- **`callbacks`**: Inline button and interaction management
- **`files`**: Processing of received files with content recognition

#### Utils
- **`naming`**: Smart file name parsing and folder structure creation
- **`formatters`**: Telegram message formatting and progress bar
- **`helpers`**: Retry logic, validation, rate limiting, async helpers

## 🚀 Quick Start

### Prerequisites

- Python 3.8+ or Docker
- Telegram API credentials ([my.telegram.org](https://my.telegram.org))
- Bot token from [@BotFather](https://t.me/botfather)
- (Optional) TMDB API key for metadata

### Docker Installation (Recommended)

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/mediabutler.git
cd mediabutler
```

2. **Configure environment**:
```bash
cp .env.example .env
nano .env  # Enter your credentials
```

3. **Start with Docker Compose**:
```bash
docker-compose up -d
```

### Manual Installation

1. **Setup Python environment**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure and start**:
```bash
cp .env.example .env
nano .env  # Configure credentials
python main.py
```

## 📖 Configuration

### Main Environment Variables

```env
# Telegram (Required)
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=abcdef123456
TELEGRAM_BOT_TOKEN=123456:ABC-DEF

# TMDB (Optional but recommended)
TMDB_API_KEY=your_tmdb_api_key
TMDB_LANGUAGE=en-US

# Paths
MOVIES_PATH=/media/movies
TV_PATH=/media/tv
TEMP_PATH=/media/temp

# Authorizations
AUTHORIZED_USERS=123456789,987654321

# Limits
MAX_CONCURRENT_DOWNLOADS=3
MIN_FREE_SPACE_GB=5
WARNING_THRESHOLD_GB=10
```

See [`.env.example`](.env.example) for all available options.

## 🎯 Usage

### Bot Commands

| Command      | Description                      | Permissions |
|--------------|----------------------------------|-------------|
| `/start`     | Start bot and show info          | All         |
| `/status`    | Show active downloads and queue  | All         |
| `/space`     | Disk space details               | All         |
| `/waiting`   | Files waiting for space          | All         |
| `/cancel_all`| Cancel all downloads             | All         |
| `/help`      | Show command guide               | All         |
| `/users`     | List authorized users            | Admin       |
| `/stop`      | Stop the bot                     | Admin       |

### Download Workflow

1. **Send/forward** a video file to the bot
2. Bot **analyzes** the name and searches TMDB
3. **Confirm** or select Movie/TV Series
4. For series, **select season** if needed
5. **Automatic download** or queued

### Resulting Folder Structure

```
/media/
├── movies/
│   ├── Avatar (2009)/
│   │   └── Avatar (2009).mp4
│   └── Inception (2010)/
│       └── Inception (2010).mp4
└── tv/
    ├── Breaking Bad [EN]/
    │   ├── Season 01/
    │   │   ├── Breaking Bad - S01E01 - Pilot.mp4
    │   │   └── Breaking Bad - S01E02 - Cat's in the Bag.mp4
    │   └── Season 02/
    └── The Office/
        └── Season 04/
```

## 🔧 Development

### Extending the Bot

The modular design makes it easy to add new features:

#### Add a New Command

1. Create the method in `handlers/commands.py`:
```python
async def mycommand_handler(self, event):
    """Handler for /mycommand"""
    if not await self.auth.check_authorized(event):
        return
    
    # Command logic
    await event.reply("Command response")
```

2. Register in `register()`:
```python
self.client.on(events.NewMessage(pattern='/mycommand'))(self.mycommand_handler)
```

#### Add a Metadata Provider

1. Create a new module in `core/`:
```python
# core/metadata_provider.py
class MetadataProvider:
    async def search(self, query: str):
        # Implement search
        pass
```

2. Integrate in `FileHandlers` or where needed

### Testing

```bash
# Unit tests
python -m pytest tests/

# Test with coverage
python -m pytest --cov=core --cov=handlers --cov=utils tests/
```

### Code Style

The project follows PEP 8:
```bash
# Formatting
black .

# Linting
flake8 . --max-line-length=100

# Type checking
mypy .
```

## 🐳 Docker

### Build Image

```bash
docker build -t mediabutler:latest .
```

### Custom Docker Compose

```yaml
version: '3.8'

services:
  mediabutler:
    image: mediabutler:latest
    container_name: mediabutler
    restart: unless-stopped
    env_file: .env
    volumes:
      - ${MOVIES_PATH}:/media/movies
      - ${TV_PATH}:/media/tv
      - ./session:/app/session
    networks:
      - media_network

networks:
  media_network:
    external: true
```

## 📊 Monitoring

### Logs

```bash
# Docker logs
docker logs -f mediabutler

# Log file (if configured)
tail -f logs/mediabutler.log
```

### Metrics

The bot exposes internal metrics via the `/status` command:
- Active downloads
- Queued files
- Available space
- Download speed

## 🚧 Roadmap

- [ ] Web UI for management
- [ ] Jellyfin/Plex integration
- [ ] Subtitle support
- [ ] Playlist/channel downloads
- [ ] Customizable notifications
- [ ] Configuration backup/restore
- [ ] REST API for integrations
- [ ] Full multi-language support

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the project
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgements

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram MTProto client
- [TMDB](https://www.themoviedb.org) - Metadata database
- [aiohttp](https://github.com/aio-libs/aiohttp) - Asynchronous HTTP client
- Self-hosted community ❤️

## ⚠️ Disclaimer

Bot for personal use. Respect copyright laws and only download content you have rights to.

---

<p align="center">
  Developed with ❤️ for the self-hosted community
</p>