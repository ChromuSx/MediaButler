# Quick Start Guide - MediaButler Web Dashboard

Get the dashboard running in 5 minutes!

## Prerequisites

- Python 3.10+ already installed (for MediaButler bot)
- Node.js 18+ and npm installed ([Download](https://nodejs.org/))

## Step 1: Install Backend Dependencies

From the **project root directory**:

```bash
pip install -r requirements.txt
```

This installs FastAPI, uvicorn, and other required packages.

## Step 2: Start the Backend API

From the **project root directory**:

```bash
python -m web.backend.main
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

✅ API is now running on `http://localhost:8000`

Check it: Open `http://localhost:8000/docs` in your browser to see the API documentation.

## Step 3: Install Frontend Dependencies

Open a **new terminal window**, then:

```bash
cd web/frontend
npm install
```

This will take a minute to download React and other dependencies.

## Step 4: Start the Frontend

```bash
npm run dev
```

You should see:
```
VITE v5.0.8  ready in 500 ms

➜  Local:   http://localhost:3000/
```

✅ Dashboard is now running on `http://localhost:3000`

## Step 5: Login

1. Open `http://localhost:3000` in your browser
2. Login with default credentials:
   - **Username**: `admin`
   - **Password**: `admin`

🎉 **You're in!** The dashboard should now display your MediaButler statistics.

## What's Next?

### Run Both Services Together

You need to keep both terminals running:
- Terminal 1: Backend API (port 8000)
- Terminal 2: Frontend React app (port 3000)

### Integrate with MediaButler Bot

The dashboard automatically connects to the same SQLite database that MediaButler uses.

Make sure your `.env` file has:
```
DATABASE_ENABLED=true
DATABASE_PATH=data/mediabutler.db
```

Start MediaButler bot in a third terminal:
```bash
python main.py
```

Now when you download files via Telegram, you'll see them appear in the dashboard in real-time!

### Explore Features

- **Dashboard**: View statistics, charts, and trends
- **Downloads**: Monitor active downloads and history
- **Users**: See all users and their activity (admin only)
- **Settings**: Configure bot settings

### Production Setup

For production deployment with nginx/Apache, see [web/README.md](README.md#production-deployment).

## Troubleshooting

### Backend Error: "ModuleNotFoundError: No module named 'fastapi'"

Run: `pip install -r requirements.txt` from project root

### Frontend Error: "command not found: npm"

Install Node.js from https://nodejs.org/

### Port 8000 already in use

Change the port in `web/backend/main.py`:
```python
uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
```

And update `web/frontend/vite.config.js`:
```javascript
proxy: {
  '/api': {
    target: 'http://localhost:8001',  // Changed port
    ...
  }
}
```

### Can't see any data in dashboard

1. Make sure MediaButler bot is using the database (`DATABASE_ENABLED=true`)
2. Run the bot and download at least one file
3. Refresh the dashboard

## Quick Commands Reference

### Backend
```bash
# Start backend (development) - from project root
python -m web.backend.main

# Start backend (production) - from project root
uvicorn web.backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend
```bash
# Install dependencies
cd web/frontend && npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Full Stack
Run all three services for complete experience (from project root):

**Terminal 1** - Backend API:
```bash
python -m web.backend.main
```

**Terminal 2** - Frontend:
```bash
cd web/frontend && npm run dev
```

**Terminal 3** - MediaButler Bot:
```bash
python main.py
```

## Need Help?

- Full documentation: [web/README.md](README.md)
- API docs: http://localhost:8000/docs (when running)
- Report issues: https://github.com/your-repo/issues
