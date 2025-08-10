# 🎬 TeleDrop - Telegram Media Organizer Bot

<div align="center">
  <img src="logo.png" alt="TeleDrop" width="200">
</div>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/docker-ready-brightgreen.svg" alt="Docker Ready">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/telegram-bot-blue.svg" alt="Telegram Bot">
</p>

<p align="center">
  <strong>Your personal Telegram media librarian - Download, organize, and manage your media files with smart folder structure</strong>
</p>

## ✨ Features

- 🎬 **Smart Organization** - Automatically creates folders for movies and TV shows
- 📺 **Series Detection** - Recognizes season and episode patterns (S01E01, 1x01, etc.)
- 📁 **Clean Structure** - Movies in individual folders, TV shows organized by series/season
- ⏳ **Queue Management** - Handle multiple downloads with configurable concurrent limits
- 💾 **Space Monitoring** - Real-time disk space checking with automatic queue management
- 👥 **Multi-user Support** - Whitelist system for authorized users
- 🧹 **Smart Cleanup** - Removes empty folders when downloads are cancelled
- 🔄 **Resume Support** - Handles connection interruptions gracefully
- 🐳 **Docker Ready** - Easy deployment with Docker Compose

## 📸 Examples

<details>
<summary>Click to view examples</summary>

### File Detection
```
📁 File received:
Supernatural 4x17.mp4
📏 Size: 363.3 MB (0.4 GB)

📺 Detected: Supernatural
📅 Season 4, Episode 17

Is this a movie or TV show?
[🎬 Movie] [📺 TV Show] [❌ Cancel]
```

### Download Progress
```
📺 TV Show

📥 Downloading...
Supernatural 4x17.mp4

📁 Series: Supernatural/
📅 Season: Season 04/

[████████████░░░░░░░░] 
60.5% - 220.1/363.3 MB
⚡ Speed: 12.5 MB/s
⏱ Time remaining: 11s
🟢 Free space: 1.2 TB
```

### Folder Structure
```
/media/
├── movies/
│   ├── Avatar (2009)/
│   │   └── Avatar.2009.1080p.BluRay.mp4
│   └── Inception (2010)/
│       └── Inception.2010.2160p.WEB-DL.mp4
└── tv/
    ├── Breaking Bad/
    │   ├── Season 01/
    │   │   ├── Breaking.Bad.S01E01.mp4
    │   │   └── Breaking.Bad.S01E02.mp4
    │   └── Season 02/
    └── Supernatural/
        └── Season 04/
            └── Supernatural 4x17.mp4
```
</details>

## 🚀 Quick Start

### Prerequisites

- Telegram API credentials (get from [my.telegram.org](https://my.telegram.org))
- Bot token from [@BotFather](https://t.me/botfather)
- Docker and Docker Compose (optional)
- Python 3.8+ (for manual installation)

### Docker Installation (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/teledrop.git
cd teledrop
```

2. Create `.env` file:
```bash
cp .env.example .env
```

3. Edit `.env` with your credentials:
```env
# Telegram Credentials (Required)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token

# Paths
MOVIES_PATH=/media/movies
TV_PATH=/media/tv
TEMP_PATH=/media/temp

# User whitelist (comma-separated user IDs, leave empty for admin mode)
AUTHORIZED_USERS=

# Settings
MAX_CONCURRENT_DOWNLOADS=3
MIN_FREE_SPACE_GB=5
WARNING_THRESHOLD_GB=10
SPACE_CHECK_INTERVAL=30
```

4. Start with Docker Compose:
```bash
docker-compose up -d
```

### Manual Installation

1. Clone and setup:
```bash
git clone https://github.com/yourusername/teledrop.git
cd teledrop
pip install -r requirements.txt
```

2. Configure `.env` file (same as above)

3. Run the bot:
```bash
python teledrop.py
```

## 📖 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_API_ID` | Your Telegram API ID | Required |
| `TELEGRAM_API_HASH` | Your Telegram API Hash | Required |
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather | Required |
| `MOVIES_PATH` | Path for movie storage | `/media/movies` |
| `TV_PATH` | Path for TV shows storage | `/media/tv` |
| `TEMP_PATH` | Temporary files path | `/media/temp` |
| `AUTHORIZED_USERS` | Comma-separated user IDs | Empty (admin mode) |
| `MAX_CONCURRENT_DOWNLOADS` | Simultaneous downloads | `3` |
| `MIN_FREE_SPACE_GB` | Reserved disk space | `5` |
| `WARNING_THRESHOLD_GB` | Space warning threshold | `10` |
| `SPACE_CHECK_INTERVAL` | Space check interval (seconds) | `30` |

### First Time Setup

1. Start the bot without any `AUTHORIZED_USERS` configured
2. Send `/start` to the bot
3. You'll be added as admin automatically
4. Copy your user ID from the response
5. Add it to `.env` as `AUTHORIZED_USERS=your_id`
6. Restart the bot for permanent access

## 🎯 Usage

### Basic Commands

- `/start` - Initialize bot and show status
- `/status` - View active downloads and queue
- `/space` - Check disk space details
- `/waiting` - Show files waiting for space
- `/cancel_all` - Cancel all active downloads
- `/stop` - Stop the bot (admin only)

### Downloading Media

1. **Forward or send a video file** to the bot
2. Bot will **detect the title** and show information
3. Choose **Movie** or **TV Show**
4. For TV shows without season info, select the season
5. Download starts automatically or queues if needed

### Supported Formats

The bot recognizes various naming patterns:

**TV Shows:**
- `Series.Name.S01E01.1080p.mp4`
- `Series Name 1x01.mp4`
- `Series.Name.Season.1.Episode.1.mp4`
- `Anime Name EP01.mp4`

**Movies:**
- `Movie.Name.2024.1080p.BluRay.mp4`
- `Movie Name (2024).mp4`
- `Movie.Name.[2024].WEB-DL.mp4`

## 🔧 Advanced Features

### Multi-User Management

Add multiple users by updating `AUTHORIZED_USERS`:
```env
AUTHORIZED_USERS=123456789,987654321,555555555
```

### Space Management

The bot automatically:
- Monitors disk space in real-time
- Queues downloads when space is low
- Reserves minimum free space
- Shows color-coded space indicators (🟢🟡🔴)

### Smart Cleanup

When a download is cancelled:
- Deletes partial files
- Removes empty folders
- Preserves folders with existing content

## 🐳 Docker Compose Example

```yaml
version: '3.8'

services:
  teledrop:
    build: .
    container_name: teledrop
    environment:
      - TELEGRAM_API_ID=${TELEGRAM_API_ID}
      - TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - AUTHORIZED_USERS=${AUTHORIZED_USERS}
    volumes:
      - ${MOVIES_PATH}:/media/movies
      - ${TV_PATH}:/media/tv
      - ./session:/app/session
    restart: unless-stopped
```

## 🚧 Roadmap

- [ ] Automatic metadata fetching
- [ ] Integration with Jellyfin/Plex webhooks
- [ ] Duplicate detection
- [ ] Custom naming templates
- [ ] Channel monitoring mode
- [ ] Download statistics
- [ ] Web interface

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Telethon](https://github.com/LonamiWebs/Telethon) - Pure Python 3 MTProto API Telegram client library
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Python-dotenv reads key-value pairs from a .env file

## ⚠️ Disclaimer

This bot is for personal use only. Please respect copyright laws and only download content you have the right to access.

---

<p align="center">
  Made with ❤️ for the self-hosted community
</p>
