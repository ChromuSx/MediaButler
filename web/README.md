# MediaButler Web Dashboard

Modern web dashboard for MediaButler Telegram bot with real-time updates.

## Features

- **Dashboard Overview**: Real-time statistics, charts, and download trends
- **Download Management**: Monitor active downloads and view history
- **User Management**: View users and their statistics (Admin only)
- **Settings Panel**: Configure bot settings via web interface
- **Real-time Updates**: WebSocket integration for live download progress
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Authentication**: JWT-based secure authentication

## Tech Stack

### Backend
- **FastAPI**: Modern, high-performance Python web framework
- **WebSockets**: Real-time bidirectional communication
- **JWT Authentication**: Secure token-based auth
- **SQLite**: Shared database with Telegram bot

### Frontend
- **React 18**: Modern UI library
- **Vite**: Fast build tool and dev server
- **TailwindCSS**: Utility-first CSS framework
- **Recharts**: Beautiful data visualization
- **Axios**: HTTP client for API requests
- **React Router**: Client-side routing

## Installation

### Backend Setup

1. **Install Python dependencies** (from project root):
```bash
pip install -r requirements.txt
```

2. **Start the API server**:
```bash
cd web/backend
python main.py
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI): `http://localhost:8000/docs`

### Frontend Setup

1. **Install Node.js dependencies**:
```bash
cd web/frontend
npm install
```

2. **Start the development server**:
```bash
npm run dev
```

The dashboard will be available at `http://localhost:3000`

## Default Credentials

- **Username**: `admin`
- **Password**: `admin`

⚠️ **Important**: Change the default password in production!

## Project Structure

```
web/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── auth.py                 # JWT authentication
│   ├── models.py               # Pydantic models
│   ├── websocket.py            # WebSocket manager
│   └── routers/
│       ├── auth.py             # Auth endpoints
│       ├── stats.py            # Statistics endpoints
│       ├── downloads.py        # Downloads endpoints
│       ├── users.py            # Users endpoints
│       └── settings.py         # Settings endpoints
└── frontend/
    ├── src/
    │   ├── components/         # React components
    │   │   └── Layout.jsx      # Main layout with sidebar
    │   ├── pages/              # Page components
    │   │   ├── LoginPage.jsx
    │   │   ├── DashboardPage.jsx
    │   │   ├── DownloadsPage.jsx
    │   │   ├── UsersPage.jsx
    │   │   └── SettingsPage.jsx
    │   ├── services/           # API and WebSocket services
    │   │   ├── api.js
    │   │   └── websocket.js
    │   ├── App.jsx             # Main app component
    │   └── main.jsx            # Entry point
    ├── package.json
    └── vite.config.js
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout

### Statistics
- `GET /api/stats/overview` - Get overview statistics
- `GET /api/stats/downloads-trend` - Get download trends over time
- `GET /api/stats/media-types` - Get statistics by media type
- `GET /api/stats/top-users` - Get top users by downloads

### Downloads
- `GET /api/downloads/history` - Get download history with filters
- `GET /api/downloads/active` - Get active downloads
- `GET /api/downloads/{id}` - Get download details
- `DELETE /api/downloads/{id}` - Cancel download (admin only)

### Users
- `GET /api/users/` - List all users (admin only)
- `GET /api/users/{id}` - Get user details (admin only)
- `PATCH /api/users/{id}` - Update user (admin only)
- `DELETE /api/users/{id}` - Delete user (admin only)

### Settings
- `GET /api/settings/` - Get current settings
- `PATCH /api/settings/` - Update settings (admin only)
- `POST /api/settings/test-tmdb` - Test TMDB connection (admin only)

### WebSocket
- `WS /ws/updates` - Real-time updates stream

## WebSocket Events

The dashboard receives real-time updates via WebSocket:

- `connected` - Connection established
- `download_progress` - Download progress update
- `download_completed` - Download finished successfully
- `download_failed` - Download failed
- `stats_update` - Statistics updated

## Development

### Backend Development

Run with auto-reload:
```bash
cd web/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

Run dev server with hot reload:
```bash
cd web/frontend
npm run dev
```

Build for production:
```bash
npm run build
```

Preview production build:
```bash
npm run preview
```

## Production Deployment

### Backend

1. **Set environment variables**:
```bash
export SECRET_KEY="your-secret-key-here"
export DATABASE_PATH="/path/to/mediabutler.db"
```

2. **Run with production server**:
```bash
uvicorn web.backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Or use Gunicorn:
```bash
gunicorn web.backend.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Frontend

1. **Build for production**:
```bash
cd web/frontend
npm run build
```

2. **Serve static files** with nginx, Apache, or any static file server.

Example nginx configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /path/to/web/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Docker Deployment

Create `web/Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY web/backend ./web/backend
COPY core ./core
COPY models ./models

EXPOSE 8000

CMD ["uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Add to docker compose.yml:
```yaml
services:
  dashboard:
    build:
      context: .
      dockerfile: web/Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_PATH=/app/data/mediabutler.db
```

## Security Considerations

⚠️ **Important Security Notes**:

1. **Change default admin password** immediately in production
2. **Set a strong SECRET_KEY** for JWT signing
3. **Use HTTPS** in production (configure reverse proxy)
4. **Implement rate limiting** on login endpoint
5. **Store SECRET_KEY** in environment variables, not in code
6. **Enable CORS** only for trusted domains
7. **Use database** for user management instead of in-memory dict

## Troubleshooting

### Backend won't start
- Check if port 8000 is already in use
- Verify database path exists and is writable
- Install all requirements: `pip install -r requirements.txt`

### Frontend won't connect to API
- Ensure backend is running on port 8000
- Check browser console for CORS errors
- Verify proxy configuration in `vite.config.js`

### WebSocket disconnects
- Check firewall/proxy settings
- Ensure WebSocket is allowed through reverse proxy
- Check browser console for connection errors

## Future Enhancements

- [ ] User registration and password reset
- [ ] Email notifications for completed downloads
- [ ] Advanced filtering and search
- [ ] Download queue management (reorder, pause, resume)
- [ ] Integration with Plex/Jellyfin APIs
- [ ] Mobile app (React Native)
- [ ] Dark/Light theme toggle
- [ ] Multi-language support

## License

Part of MediaButler project.
