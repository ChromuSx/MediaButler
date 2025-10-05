# Telegram Media Bot Setup

## 1. Create Bot on Telegram

1. Open Telegram and search for **@BotFather**
2. Send the command `/newbot`
3. Choose a name for your bot (e.g., "Media Server Bot")
4. Choose a username (must end with `bot`, e.g., `my_media_server_bot`)
5. **Save the token** you receive (looks like: `7990136467:AAFFnLkly3EDl_BruaqdbIgjBAmgiYBvupg`)

## 2. Get Telegram API Credentials

1. Go to https://my.telegram.org
2. Log in with your phone number
3. Click on "API Development Tools"
4. Create a new application if you haven't already
5. **Save your API ID and API Hash**

## 3. File Preparation

1. Create the bot directory:
```bash
mkdir -p telegram-media-bot
cd telegram-media-bot
```

2. Create necessary files:

**telegram_media_bot.py** (copy from repository)

**requirements.txt**:
```
telethon==1.36.0
cryptg==0.4.0
python-socks[asyncio]==2.4.3
python-dotenv==1.0.0
```

**Dockerfile**:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot script
COPY telegram_media_bot.py .

# Create directories
RUN mkdir -p /media/movies /media/tv /media/temp /app/session

# Run bot
CMD ["python", "telegram_media_bot.py"]
```

## 4. Configuration

1. Create `.env` file:
```bash
# Telegram credentials
TELEGRAM_API_ID=YOUR_API_ID_HERE
TELEGRAM_API_HASH=YOUR_API_HASH_HERE
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# Paths
MOVIES_PATH=/media/movies
TV_PATH=/media/tv
TEMP_PATH=/media/temp

# Authorized users (comma separated, leave empty for admin mode)
AUTHORIZED_USERS=

# Bot settings
MAX_CONCURRENT_DOWNLOADS=3
MIN_FREE_SPACE_GB=5
WARNING_THRESHOLD_GB=10
SPACE_CHECK_INTERVAL=30
```

2. For Docker Compose, add to your `docker compose.yml`:

```yaml
  telegram-media-bot:
    build: 
      context: ./telegram-media-bot
      dockerfile: Dockerfile
    container_name: telegram-media-bot
    security_opt:
      - no-new-privileges:true
    environment:
      - TELEGRAM_API_ID=${TELEGRAM_API_ID}
      - TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - MOVIES_PATH=/media/movies
      - TV_PATH=/media/tv
      - TEMP_PATH=/media/temp
      - AUTHORIZED_USERS=${AUTHORIZED_USERS}
      - TZ=${TZ}
      - PUID=${PUID}
      - PGID=${PGID}
    volumes:
      - ${MEDIA_PATH}/movies:/media/movies
      - ${MEDIA_PATH}/tv:/media/tv
      - ./telegram-media-bot/session:/app/session
      - ./telegram-media-bot/temp:/media/temp
    restart: unless-stopped
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
```

## 5. Running the Bot

### With Docker:
```bash
docker compose up -d telegram-media-bot
```

### Without Docker:
```bash
pip install -r requirements.txt
python telegram_media_bot.py
```

## 6. First Time Setup

1. Open Telegram and search for your bot using the username you chose
2. Send `/start`
3. The first user automatically becomes admin
4. Note your user ID and add it to `AUTHORIZED_USERS` in `.env` for permanent access

## 7. Usage

1. Forward a video file from any channel to the bot
2. Choose if it's a Movie or TV Show
3. For TV Shows without season info, select the season
4. Wait for download with progress bar!

## 8. Features

- 📁 **Smart folder organization**
  - Movies: `/movies/Movie Name (Year)/file.mp4`
  - TV Shows: `/tv/Series Name/Season 01/file.mp4`

- 🔄 **Queue management**
  - Concurrent download limit
  - Automatic queue processing
  - Space-aware queue

- 💾 **Space monitoring**
  - Minimum space threshold
  - Warning levels
  - Automatic space checking

- 👥 **Multi-user support**
  - User whitelist
  - Admin privileges
  - Per-user download management

## 9. Troubleshooting

### Bot doesn't respond
- Verify token in `.env` file
- Check logs: `docker logs telegram-media-bot`

### Permission errors
- Verify PUID and PGID in `.env` are correct
- Check destination folder permissions

### Slow downloads
- Large files take time
- Speed depends on Telegram servers

### File doesn't appear in media server
- Wait a few minutes for automatic scanning
- Or force a manual scan from your media server dashboard