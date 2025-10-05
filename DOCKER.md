# Docker Deployment Guide

MediaButler can be deployed using Docker and Docker Compose with three services:
- **Telegram Bot**: Handles file downloads via Telegram
- **Web API**: FastAPI backend for the dashboard
- **Web Frontend**: React dashboard for monitoring and management

## Quick Start

### 1. Prerequisites

- Docker Engine 20.10+
- Docker Compose 1.29+

### 2. Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and configure at minimum:
```bash
# Required Telegram credentials
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token

# Optional but recommended
TMDB_API_KEY=your_tmdb_key

# Required for web dashboard security
JWT_SECRET_KEY=your-random-secret-key-here

# User authorization (leave empty for admin mode)
AUTHORIZED_USERS=
```

### 3. Start Services

Start all services:
```bash
docker compose up -d
```

Start only the bot (without web dashboard):
```bash
docker compose up -d mediabutler-bot
```

Start only the web dashboard:
```bash
docker compose up -d mediabutler-api mediabutler-web
```

### 4. Access

- **Telegram Bot**: Search for your bot on Telegram
- **Web Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs

Default credentials for web dashboard:
- Username: `admin`
- Password: `admin`

## Service Architecture

```
┌─────────────────┐
│  Telegram Bot   │  Port: N/A
│  (main.py)      │  Downloads files via Telegram
└────────┬────────┘
         │
         │ Shares database & media
         │
┌────────┴────────┐
│   Web API       │  Port: 8000
│   (FastAPI)     │  REST API + WebSocket
└────────┬────────┘
         │
         │ HTTP API
         │
┌────────┴────────┐
│  Web Frontend   │  Port: 3000
│  (React + Vite) │  Dashboard UI
└─────────────────┘
```

## Volume Mounts

- `./session:/app/session` - Telegram session persistence
- `./data:/app/data` - Database and application data
- `./media/movies:/media/movies` - Movie storage
- `./media/tv:/media/tv` - TV series storage
- `./media/temp:/media/temp` - Temporary downloads

## Customization

### Change Ports

Edit `.env`:
```bash
API_PORT=8080  # Change API port
WEB_PORT=8081  # Change web port
```

### Use External Media Directories

Edit `.env`:
```bash
MOVIES_PATH=/mnt/nas/movies
TV_PATH=/mnt/nas/tv
TEMP_PATH=/tmp/downloads
```

### Production Deployment

For production, update `docker compose.yml`:

1. Build optimized frontend:
```yaml
mediabutler-web:
  build:
    context: ./web/frontend
    dockerfile: Dockerfile.prod  # You'll need to create this
  environment:
    - NODE_ENV=production
```

2. Use secrets for sensitive data:
```yaml
secrets:
  telegram_token:
    external: true
  jwt_secret:
    external: true
```

3. Add reverse proxy (nginx/traefik) for HTTPS

## Useful Commands

View logs:
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f mediabutler-bot
docker compose logs -f mediabutler-api
docker compose logs -f mediabutler-web
```

Restart services:
```bash
docker compose restart
```

Stop services:
```bash
docker compose down
```

Rebuild after code changes:
```bash
docker compose build
docker compose up -d
```

Clean everything (including volumes):
```bash
docker compose down -v
```

## Health Checks

The services include health checks:

- **Bot**: Simple Python availability check
- **API**: HTTP GET to `/api/auth/me`

Check service health:
```bash
docker ps
# Look for "healthy" status
```

## Troubleshooting

### Bot won't start
- Check Telegram credentials in `.env`
- View logs: `docker compose logs mediabutler-bot`
- Ensure session directory is writable

### Web dashboard not accessible
- Check if port 3000 is available: `netstat -tulpn | grep 3000`
- Verify API is running: `curl http://localhost:8000/docs`
- Check logs: `docker compose logs mediabutler-web`

### Database errors
- Ensure `./data` directory exists and is writable
- Check ownership: `chown -R 1000:1000 ./data`

### Permission errors on media files
- Check PUID/PGID in `.env` matches your user
- Verify media directory permissions

## Integration with Media Servers

To integrate with Jellyfin/Plex/Emby:

1. Use the same media paths in both systems
2. Optional: Join the same Docker network

Edit `docker compose.yml`:
```yaml
networks:
  mediabutler-network:
    external: true
    name: media_network  # Your existing media network
```

## Updates

Pull latest changes and rebuild:
```bash
git pull
docker compose down
docker compose build
docker compose up -d
```

## Backup

Backup these directories:
- `./session` - Telegram session
- `./data` - Database and stats
- `./media` - Downloaded files (optional, may be large)

Example backup command:
```bash
tar -czf mediabutler-backup-$(date +%Y%m%d).tar.gz session data
```

## Security Notes

1. **Change default JWT secret** in production
2. **Use strong passwords** for web dashboard
3. **Restrict network access** if exposing publicly
4. **Enable HTTPS** with reverse proxy for production
5. **Keep Docker images updated** regularly
