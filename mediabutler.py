#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
import shutil
import re
import json
import aiohttp
from datetime import datetime
from pathlib import Path
from telethon import TelegramClient, events, Button
from telethon.tl.types import DocumentAttributeFilename
import time
from collections import defaultdict

# Load environment variables if available
try:
    from dotenv import load_dotenv
    env_path = Path('.env')
    if env_path.exists():
        print(f"✅ .env file found at: {env_path.absolute()}")
        load_dotenv()
        print("✅ .env file loaded successfully")
    else:
        print(f"❌ .env file NOT found in: {Path.cwd()}")
        print("   Make sure the .env file is in the same directory as the bot")
except ImportError:
    print("⚠️ python-dotenv not installed. Use: pip install python-dotenv")
    print("   Looking for variables in system environment...")

# ===== CONFIGURATION FROM ENVIRONMENT =====
API_ID = int(os.getenv('TELEGRAM_API_ID', '0'))
API_HASH = os.getenv('TELEGRAM_API_HASH', '')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# TMDB Configuration
TMDB_API_KEY = os.getenv('TMDB_API_KEY', '')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p/'
TMDB_LANGUAGE = os.getenv('TMDB_LANGUAGE', 'it-IT')  # Italiano di default

# Temporary debug
print(f"\n🔍 Debug variables:")
print(f"API_ID: {API_ID}")
print(f"API_HASH present: {'Yes' if API_HASH else 'No'}")
print(f"BOT_TOKEN present: {'Yes' if BOT_TOKEN else 'No'}")
print(f"TMDB_API_KEY present: {'Yes' if TMDB_API_KEY else 'No'}")
print(f"Current directory: {Path.cwd()}\n")

# ===== SECURITY - USER WHITELIST =====
AUTHORIZED_USERS_STR = os.getenv('AUTHORIZED_USERS', '')
AUTHORIZED_USERS = [int(uid.strip()) for uid in AUTHORIZED_USERS_STR.split(',') if uid.strip()]
ADMIN_MODE = len(AUTHORIZED_USERS) == 0

# ===== PATHS =====
MOVIES_PATH = os.getenv('MOVIES_PATH', '/media/movies')
TV_PATH = os.getenv('TV_PATH', '/media/tv')
TEMP_PATH = os.getenv('TEMP_PATH', '/media/temp')

# ===== LIMITS AND THRESHOLDS =====
MAX_CONCURRENT_DOWNLOADS = int(os.getenv('MAX_CONCURRENT_DOWNLOADS', '3'))
MIN_FREE_SPACE_GB = float(os.getenv('MIN_FREE_SPACE_GB', '5'))
WARNING_THRESHOLD_GB = float(os.getenv('WARNING_THRESHOLD_GB', '10'))
SPACE_CHECK_INTERVAL = int(os.getenv('SPACE_CHECK_INTERVAL', '30'))

# ===== TELETHON SESSION =====
if sys.platform == "win32":
    SESSION_PATH = os.getenv('SESSION_PATH', './session/bot_session')
else:
    SESSION_PATH = os.getenv('SESSION_PATH', '/app/session/bot_session')

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Verify configuration
if not all([API_ID, API_HASH, BOT_TOKEN]):
    logger.error("ERROR: Missing Telegram credentials in environment variables!")
    logger.error("Configure: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN")
    sys.exit(1)

# Create directories
Path(MOVIES_PATH).mkdir(parents=True, exist_ok=True)
Path(TV_PATH).mkdir(parents=True, exist_ok=True)
Path(TEMP_PATH).mkdir(parents=True, exist_ok=True)
Path(os.path.dirname(SESSION_PATH)).mkdir(parents=True, exist_ok=True)

logger.info(f"Configuration loaded:")
logger.info(f"  Movies: {MOVIES_PATH}")
logger.info(f"  TV: {TV_PATH}")
logger.info(f"  Authorized users: {len(AUTHORIZED_USERS)}")
logger.info(f"  Minimum free space: {MIN_FREE_SPACE_GB} GB")
logger.info(f"  TMDB Integration: {'Enabled' if TMDB_API_KEY else 'Disabled'}")

# Create client
client = TelegramClient(
    SESSION_PATH, 
    API_ID, 
    API_HASH,
    connection_retries=5,
    retry_delay=1,
    auto_reconnect=True
).start(bot_token=BOT_TOKEN)

# Download management dictionaries
active_downloads = {}
download_tasks = {}
download_queue = asyncio.Queue()
space_waiting_queue = []
cancelled_downloads = set()

# ===== TMDB API FUNCTIONS =====
async def search_tmdb(query, media_type=None):
    """Search TMDB for movies and TV shows"""
    if not TMDB_API_KEY:
        return None
    
    try:
        # Clean query
        query = re.sub(r'[Ss]\d+[Ee]\d+.*', '', query).strip()  # Remove episode info
        query = re.sub(r'\(\d{4}\)', '', query).strip()  # Remove year in parentheses
        query = re.sub(r'\d{4}$', '', query).strip()  # Remove year at end
        query = re.sub(r'[\._]', ' ', query)  # Replace dots and underscores
        
        # Search endpoint - multi search gets both movies and TV
        endpoint = '/search/multi' if not media_type else f'/search/{media_type}'
        
        async with aiohttp.ClientSession() as session:
            params = {
                'api_key': TMDB_API_KEY,
                'query': query,
                'language': TMDB_LANGUAGE,
                'include_adult': 'false'
            }
            
            async with session.get(f"{TMDB_BASE_URL}{endpoint}", params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('results', [])
                else:
                    logger.warning(f"TMDB API error: {response.status}")
                    return None
                    
    except asyncio.TimeoutError:
        logger.warning("TMDB API timeout")
        return None
    except Exception as e:
        logger.error(f"TMDB search error: {e}")
        return None

async def get_episode_details(tv_id, season, episode):
    """Get specific episode details from TMDB"""
    if not TMDB_API_KEY:
        return None
        
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                'api_key': TMDB_API_KEY,
                'language': TMDB_LANGUAGE
            }
            
            url = f"{TMDB_BASE_URL}/tv/{tv_id}/season/{season}/episode/{episode}"
            async with session.get(url, params=params, timeout=5) as response:
                if response.status == 200:
                    return await response.json()
                    
    except Exception as e:
        logger.error(f"TMDB episode details error: {e}")
        
    return None

def format_tmdb_result(result, season_num=None, episode_num=None):
    """Format TMDB result for display"""
    media_type = result.get('media_type', 'movie')
    
    # Build basic info
    if media_type == 'tv' or 'first_air_date' in result:
        title = result.get('name', 'Unknown')
        year = result.get('first_air_date', '')[:4]
        emoji = "📺"
        media_type_str = "Serie TV"
    else:
        title = result.get('title', 'Unknown')
        year = result.get('release_date', '')[:4]
        emoji = "🎬"
        media_type_str = "Film"
    
    # Rating
    rating = result.get('vote_average', 0)
    rating_str = f"⭐ {rating:.1f}/10" if rating > 0 else ""
    
    # Poster URL
    poster_path = result.get('poster_path', '')
    poster_url = f"{TMDB_IMAGE_BASE}w200{poster_path}" if poster_path else None
    
    # Overview (truncate if too long)
    overview = result.get('overview', '')
    if len(overview) > 300:
        overview = overview[:297] + "..."
    
    # Build formatted text
    text = f"{emoji} **{media_type_str}**\n\n"
    text += f"**{title}**"
    if year:
        text += f" ({year})"
    text += "\n"
    
    if season_num and episode_num:
        text += f"📅 Stagione {season_num}, Episodio {episode_num}\n"
    
    if rating_str:
        text += f"{rating_str}\n"
    
    if overview:
        text += f"\n📝 {overview}\n"
    
    return text, poster_url

def create_clean_filename(tmdb_result, original_filename, is_movie=True, season=None, episode=None, episode_title=None):
    """Create clean filename based on TMDB data"""
    extension = os.path.splitext(original_filename)[1]
    
    if is_movie:
        title = tmdb_result.get('title', 'Unknown')
        year = tmdb_result.get('release_date', '')[:4]
        
        # Check for Italian tags in original
        has_ita = any(tag in original_filename.upper() for tag in ['ITA', 'ITALIAN', 'SUBITA'])
        
        # Clean title
        title = re.sub(r'[<>:"|?*]', '', title)
        
        if year:
            folder_name = f"{title} ({year})"
        else:
            folder_name = title
            
        if has_ita:
            folder_name += " [ITA]"
            
        filename = folder_name + extension
        
    else:  # TV Show
        title = tmdb_result.get('name', 'Unknown')
        title = re.sub(r'[<>:"|?*]', '', title)
        
        # Check for Italian tags
        has_ita = any(tag in original_filename.upper() for tag in ['ITA', 'ITALIAN', 'SUBITA'])
        
        series_folder = title
        if has_ita:
            series_folder += " [ITA]"
            
        if season and episode:
            # Format: Series Name - S01E01 - Episode Title.ext
            filename = f"{title} - S{season:02d}E{episode:02d}"
            if episode_title:
                # Clean episode title
                episode_title = re.sub(r'[<>:"|?*]', '', episode_title)
                filename += f" - {episode_title}"
            filename += extension
        else:
            filename = original_filename  # Fallback
            
        folder_name = series_folder
    
    return folder_name, filename

# ===== FILE/FOLDER NAME UTILITIES (Enhanced) =====
def sanitize_filename(filename):
    """Clean filename from problematic characters"""
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    filename = re.sub(r'\.+', '.', filename)
    filename = re.sub(r'\s+', ' ', filename).strip()
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200-len(ext)] + ext
    return filename

def extract_movie_info(filename):
    """Extract movie information from filename with better cleaning"""
    name = os.path.splitext(filename)[0]
    
    # Find year
    year_match = re.search(r'[\(\[]?(\d{4})[\)\]]?', name)
    year = year_match.group(1) if year_match else None
    
    if year:
        name = re.sub(r'[\(\[]?\d{4}[\)\]]?.*', '', name).strip()
    
    # Clean technical tags more aggressively
    quality_tags = ['1080p', '720p', '2160p', '4K', 'BluRay', 'WEBRip', 'WEB-DL', 
                   'HDTV', 'DVDRip', 'BRRip', 'x264', 'x265', 'HEVC', 'HDR', 
                   'ITA', 'ENG', 'SUBITA', 'DDP5.1', 'AC3', 'AAC', 'AMZN', 
                   'NF', 'DSNP', 'DLMux', 'BDMux']
    
    for tag in quality_tags:
        name = re.sub(rf'\b{tag}\b', '', name, flags=re.IGNORECASE)
    
    # Clean separators
    name = re.sub(r'(?<!\s)\.(?!\s)', ' ', name)
    name = name.replace('_', ' ')
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'[\-\.\s]+$', '', name).strip()
    
    if year:
        folder_name = f"{name} ({year})"
    else:
        folder_name = name
    
    return sanitize_filename(folder_name)

def extract_series_info(filename):
    """Extract series information from filename (enhanced)"""
    patterns = [
        r'[Ss](\d+)[Ee](\d+)',              # S01E01
        r'[Ss](\d+)\s*[Ee](\d+)',           # S01 E01
        r'Season\s*(\d+)\s*Episode\s*(\d+)', # Season 1 Episode 1
        r'(\d+)x(\d+)',                      # 1x01
        r'\s(\d+)x(\d+)',                    # " 1x01"
        r'[\.\s\-_](\d+)x(\d+)',            # .1x01
        r'[Ee][Pp][\.\s]?(\d+)',            # EP01
        r'\.(\d+)x(\d+)\.',                 # .1x01.
    ]
    
    original_filename = filename
    season = None
    episode = None
    series_name = None
    
    for pattern in patterns:
        if pattern in [r'[Ee][Pp][\.\s]?(\d+)']:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                season = 1
                episode = int(match.group(1))
                series_name = filename[:match.start()].strip()
                break
        else:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                try:
                    season = int(match.group(1))
                    episode = int(match.group(2))
                    series_name = filename[:match.start()].strip()
                    break
                except:
                    continue
    
    if not series_name:
        series_name = os.path.splitext(filename)[0]
    
    # Better cleaning
    quality_tags = ['1080p', '720p', '2160p', '4K', 'BluRay', 'WEBRip', 'WEB-DL', 
                   'HDTV', 'DVDRip', 'x264', 'x265', 'HEVC', 'HDR', 'ITA', 'ENG', 
                   'SUBITA', 'DDP5.1', 'AC3', 'AAC', 'AMZN', 'NF', 'DSNP', 'DLMux']
    
    for tag in quality_tags:
        series_name = re.sub(rf'\b{tag}\b', '', series_name, flags=re.IGNORECASE)
    
    series_name = re.sub(r'[\(\[]?\d{4}[\)\]]?\s*$', '', series_name)
    series_name = re.sub(r'[\s\-_.]+$', '', series_name)
    series_name = re.sub(r'(?<!\s)\.(?!\s)', ' ', series_name)
    series_name = series_name.replace('_', ' ')
    series_name = re.sub(r'\s+', ' ', series_name).strip()
    
    logger.info(f"Series extract: '{original_filename}' -> Name: '{series_name}', S{season}E{episode}")
    
    return {
        'series_name': sanitize_filename(series_name) if series_name else "Unknown Series",
        'season': season,
        'episode': episode
    }

# ===== SPACE UTILITIES =====
def get_free_space_gb(path):
    """Get free space in GB for specified path"""
    try:
        stat = shutil.disk_usage(path)
        free_gb = stat.free / (1024 * 1024 * 1024)
        return free_gb
    except Exception as e:
        logger.error(f"Error checking space for {path}: {e}")
        return 0

def get_disk_usage(path):
    """Get complete disk usage information"""
    try:
        stat = shutil.disk_usage(path)
        return {
            'total_gb': stat.total / (1024 * 1024 * 1024),
            'used_gb': stat.used / (1024 * 1024 * 1024),
            'free_gb': stat.free / (1024 * 1024 * 1024),
            'percent_used': (stat.used / stat.total) * 100
        }
    except Exception as e:
        logger.error(f"Error checking disk: {e}")
        return None

def format_size_gb(size_bytes):
    """Format size from bytes to GB"""
    return size_bytes / (1024 * 1024 * 1024)

def check_space_available(path, required_gb):
    """Check if there's enough space for download"""
    free_gb = get_free_space_gb(path)
    total_required = required_gb + MIN_FREE_SPACE_GB
    return free_gb >= total_required, free_gb

# ===== AUTHORIZATION FUNCTIONS =====
async def check_authorized(event):
    """Check if user is authorized"""
    user_id = event.sender_id
    user = await event.get_sender()
    username = user.username or "NoUsername"
    
    if ADMIN_MODE and len(AUTHORIZED_USERS) == 0:
        AUTHORIZED_USERS.append(user_id)
        logger.info(f"First user added as admin: {username} (ID: {user_id})")
        await event.reply(
            f"🔐 **First Access - Admin Mode**\n\n"
            f"You have been added as administrator!\n"
            f"Your ID: `{user_id}`\n\n"
            f"Add `AUTHORIZED_USERS={user_id}` to .env file to make it permanent."
        )
        return True
    
    if user_id not in AUTHORIZED_USERS:
        logger.warning(f"Unauthorized access attempt by: {username} (ID: {user_id})")
        await event.reply(
            f"❌ **Access Denied**\n\n"
            f"You are not authorized to use this bot.\n"
            f"Your ID: `{user_id}`\n\n"
            f"Contact the administrator to be added."
        )
        return False
    
    return True

# ===== COMMAND HANDLERS =====
@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Handle /start command"""
    if not await check_authorized(event):
        return
        
    user = await event.get_sender()
    logger.info(f"/start command from {user.username} (ID: {user.id})")
    
    # Show space info
    movies_usage = get_disk_usage(MOVIES_PATH)
    tv_usage = get_disk_usage(TV_PATH)
    
    space_info = "\n💾 **Available Space:**\n"
    if movies_usage:
        space_info += f"• Movies: {movies_usage['free_gb']:.1f} GB free\n"
    if tv_usage and tv_usage != movies_usage:
        space_info += f"• TV Shows: {tv_usage['free_gb']:.1f} GB free\n"
    
    tmdb_status = "✅ TMDB Integration Active" if TMDB_API_KEY else "⚠️ TMDB not configured"
    
    await event.reply(
        f"🎬 **MediaButler - Media Server Bot**\n\n"
        f"✅ Access granted!\n"
        f"🆔 Your ID: `{user.id}`\n"
        f"🐳 Running in Docker\n"
        f"🎯 {tmdb_status}\n"
        f"{space_info}\n"
        f"📊 **Commands:**\n"
        f"• `/status` - Show downloads and space\n"
        f"• `/space` - Disk space details\n"
        f"• `/waiting` - Files waiting for space\n"
        f"• `/cancel_all` - Cancel all downloads\n"
        f"• `/stop` - Stop the bot (admin only)\n\n"
        f"⚙️ **Settings:**\n"
        f"• Minimum reserved space: {MIN_FREE_SPACE_GB} GB\n"
        f"• Concurrent downloads: max {MAX_CONCURRENT_DOWNLOADS}\n"
        f"• 📁 Automatic folder organization\n"
        f"• 🎯 Smart content recognition\n\n"
        f"Send files to start!"
    )

@client.on(events.NewMessage(pattern='/space'))
async def space_handler(event):
    """Show disk space details"""
    if not await check_authorized(event):
        return
    
    movies_usage = get_disk_usage(MOVIES_PATH)
    tv_usage = get_disk_usage(TV_PATH)
    
    space_text = "💾 **Disk Space Status**\n\n"
    
    if movies_usage:
        emoji = "🟢" if movies_usage['free_gb'] > WARNING_THRESHOLD_GB else "🟡" if movies_usage['free_gb'] > MIN_FREE_SPACE_GB else "🔴"
        space_text += f"{emoji} **Movies Disk:**\n"
        space_text += f"• Total: {movies_usage['total_gb']:.1f} GB\n"
        space_text += f"• Used: {movies_usage['used_gb']:.1f} GB ({movies_usage['percent_used']:.1f}%)\n"
        space_text += f"• Free: {movies_usage['free_gb']:.1f} GB\n\n"
    
    if tv_usage and tv_usage != movies_usage:
        emoji = "🟢" if tv_usage['free_gb'] > WARNING_THRESHOLD_GB else "🟡" if tv_usage['free_gb'] > MIN_FREE_SPACE_GB else "🔴"
        space_text += f"{emoji} **TV Shows Disk:**\n"
        space_text += f"• Total: {tv_usage['total_gb']:.1f} GB\n"
        space_text += f"• Used: {tv_usage['used_gb']:.1f} GB ({tv_usage['percent_used']:.1f}%)\n"
        space_text += f"• Free: {tv_usage['free_gb']:.1f} GB\n\n"
    
    space_text += f"⚙️ **Configured thresholds:**\n"
    space_text += f"• Minimum space: {MIN_FREE_SPACE_GB} GB\n"
    space_text += f"• Warning below: {WARNING_THRESHOLD_GB} GB"
    
    await event.reply(space_text)

@client.on(events.NewMessage(pattern='/waiting'))
async def waiting_handler(event):
    """Show files waiting for space"""
    if not await check_authorized(event):
        return
    
    if not space_waiting_queue:
        await event.reply("✅ No files waiting for space")
        return
    
    waiting_text = "⏳ **Files waiting for space:**\n\n"
    
    for idx, (msg_id, info) in enumerate(space_waiting_queue, 1):
        waiting_text += f"{idx}. `{info['filename'][:40]}...`\n"
        waiting_text += f"   📏 Requires: {format_size_gb(info['size']):.1f} GB\n"
        waiting_text += f"   📂 Destination: {info['media_type']}\n\n"
    
    waiting_text += f"📊 Total waiting: {len(space_waiting_queue)} files"
    await event.reply(waiting_text)

@client.on(events.NewMessage(pattern='/status'))
async def status_handler(event):
    """Show download status and space"""
    if not await check_authorized(event):
        return
    
    status_text = "📊 **System Status**\n\n"
    
    if download_tasks:
        status_text += "**Active downloads:**\n"
        for msg_id, info in active_downloads.items():
            if msg_id in download_tasks:
                status_text += f"📥 `{info['filename'][:30]}...`\n"
                if 'progress' in info:
                    status_text += f"   Progress: {info['progress']:.1f}%\n"
                status_text += "\n"
    else:
        status_text += "📭 No active downloads\n\n"
    
    queue_size = download_queue.qsize()
    if queue_size > 0:
        status_text += f"⏳ **In queue:** {queue_size} files\n"
    
    if space_waiting_queue:
        status_text += f"⏸️ **Waiting for space:** {len(space_waiting_queue)} files\n"
    
    status_text += "\n💾 **Disk space:**\n"
    movies_free = get_free_space_gb(MOVIES_PATH)
    tv_free = get_free_space_gb(TV_PATH)
    
    emoji_movies = "🟢" if movies_free > WARNING_THRESHOLD_GB else "🟡" if movies_free > MIN_FREE_SPACE_GB else "🔴"
    emoji_tv = "🟢" if tv_free > WARNING_THRESHOLD_GB else "🟡" if tv_free > MIN_FREE_SPACE_GB else "🔴"
    
    status_text += f"{emoji_movies} Movies: {movies_free:.1f} GB free\n"
    if tv_free != movies_free:
        status_text += f"{emoji_tv} TV Shows: {tv_free:.1f} GB free\n"
    
    await event.reply(status_text)

@client.on(events.NewMessage(pattern='/cancel_all'))
async def cancel_all_handler(event):
    """Cancel all downloads"""
    if not await check_authorized(event):
        return
        
    cancelled = 0
    
    for msg_id in list(active_downloads.keys()):
        cancelled_downloads.add(msg_id)
    
    for msg_id, task in list(download_tasks.items()):
        task.cancel()
        cancelled += 1
    
    while not download_queue.empty():
        try:
            msg_id, _ = download_queue.get_nowait()
            cancelled_downloads.add(msg_id)
            cancelled += 1
        except:
            break
    
    waiting_cancelled = len(space_waiting_queue)
    space_waiting_queue.clear()
    cancelled += waiting_cancelled
    
    download_tasks.clear()
    active_downloads.clear()
    
    await event.reply(
        f"❌ **Cancellation completed**\n\n"
        f"• Active downloads cancelled: {len(download_tasks)}\n"
        f"• Queued files cancelled: {download_queue.qsize()}\n"
        f"• Files waiting for space cancelled: {waiting_cancelled}\n\n"
        f"Total: {cancelled} operations cancelled"
    )

@client.on(events.NewMessage(pattern='/stop'))
async def stop_handler(event):
    """Stop the bot - admin only"""
    if not await check_authorized(event):
        return
    
    if event.sender_id != AUTHORIZED_USERS[0]:
        await event.reply("❌ Only the administrator can stop the bot")
        return
    
    await event.reply("🛑 **Shutting down bot...**")
    
    logger.info("Shutdown requested by administrator")
    
    for msg_id in list(active_downloads.keys()):
        cancelled_downloads.add(msg_id)
    
    for task in download_tasks.values():
        task.cancel()
    
    await asyncio.sleep(2)
    await client.disconnect()
    sys.exit(0)

# ===== FILE HANDLER (Enhanced with TMDB) =====
@client.on(events.NewMessage(func=lambda e: e.file))
async def file_handler(event):
    """Handle received files with TMDB integration"""
    if not await check_authorized(event):
        return
        
    logger.info(f"File received from user {event.sender_id}, size: {event.file.size / (1024*1024):.1f} MB")
    
    if event.file.size > 10 * 1024 * 1024 * 1024:
        await event.reply("⚠️ File too large! Maximum limit: 10GB")
        return
    
    filename = "unknown"
    if hasattr(event.file, 'name') and event.file.name:
        filename = event.file.name
    elif event.document:
        for attr in event.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                filename = attr.file_name
                break
    
    if not filename or filename == "unknown":
        filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    
    # Check if there's text in the message (for forwarded files)
    message_text = event.message.message if event.message.message else ""
    detected_name = None
    
    if message_text and (filename.startswith("video_") or filename == "unknown"):
        detected_name = message_text.strip()
        if not any(detected_name.endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov']):
            ext = os.path.splitext(filename)[1] or '.mp4'
            detected_name += ext
        logger.info(f"Name detected from message text: {detected_name}")
    
    display_filename = detected_name if detected_name else filename
    
    size_mb = event.file.size / (1024 * 1024)
    size_gb = format_size_gb(event.file.size)
    
    movies_space_ok, movies_free = check_space_available(MOVIES_PATH, size_gb)
    tv_space_ok, tv_free = check_space_available(TV_PATH, size_gb)
    
    space_warning = ""
    if not movies_space_ok and not tv_space_ok:
        space_warning = (
            f"\n\n🟡 **Space warning:**\n"
            f"File requires {size_gb:.1f} GB + {MIN_FREE_SPACE_GB} GB reserved\n"
            f"Free space: Movies {movies_free:.1f} GB, TV Shows {tv_free:.1f} GB\n"
            f"File might be queued for space."
        )
    
    # Extract info from name
    movie_folder = extract_movie_info(display_filename)
    series_info = extract_series_info(display_filename)
    
    # Try TMDB search if API key is configured
    tmdb_results = None
    tmdb_confidence = 0
    selected_tmdb = None
    
    if TMDB_API_KEY:
        initial_msg = await event.reply("🔍 **Searching TMDB database...**")
        
        # Determine search query
        if series_info['season']:
            search_query = series_info['series_name']
            media_hint = 'tv'
        else:
            search_query = movie_folder
            media_hint = None
        
        tmdb_results = await search_tmdb(search_query, media_hint)
        
        if tmdb_results and len(tmdb_results) > 0:
            # Calculate confidence based on various factors
            first_result = tmdb_results[0]
            
            # Check title similarity
            if media_hint == 'tv':
                result_title = first_result.get('name', '').lower()
                search_title = series_info['series_name'].lower()
            else:
                result_title = first_result.get('title', '').lower()
                search_title = movie_folder.lower()
            
            # Simple confidence calculation
            if result_title == search_title:
                tmdb_confidence = 95
            elif search_title in result_title or result_title in search_title:
                tmdb_confidence = 80
            else:
                tmdb_confidence = 60
            
            # Boost confidence if year matches for movies
            if media_hint != 'tv':
                year_match = re.search(r'(\d{4})', display_filename)
                if year_match:
                    file_year = year_match.group(1)
                    result_year = first_result.get('release_date', '')[:4]
                    if file_year == result_year:
                        tmdb_confidence = min(100, tmdb_confidence + 15)
            
            selected_tmdb = first_result
    
    # Prepare display based on TMDB results
    if selected_tmdb and tmdb_confidence >= 80:
        # High confidence - show TMDB result
        text, poster_url = format_tmdb_result(selected_tmdb, series_info.get('season'), series_info.get('episode'))
        
        info_text = f"📁 **File:** `{display_filename}`\n"
        info_text += f"📏 **Size:** {size_mb:.1f} MB ({size_gb:.1f} GB)\n\n"
        info_text += f"✅ **TMDB Match** ({tmdb_confidence}% confidence)\n\n"
        info_text += text
        
        # Add poster URL if available
        if poster_url:
            info_text = f"[​]({poster_url})" + info_text  # Hidden link for preview
        
        buttons = [
            [
                Button.inline("✅ Confirm", f"confirm_{event.message.id}"),
                Button.inline("🔄 Search Again", f"search_{event.message.id}")
            ],
            [
                Button.inline("🎬 Movie", f"movie_{event.message.id}"),
                Button.inline("📺 TV Show", f"tv_{event.message.id}")
            ],
            [Button.inline("❌ Cancel", f"cancel_{event.message.id}")]
        ]
        
        await initial_msg.edit(info_text + space_warning, buttons=buttons, link_preview=True)
        
    elif selected_tmdb and tmdb_confidence >= 60:
        # Medium confidence - show options
        info_text = f"📁 **File:** `{display_filename}`\n"
        info_text += f"📏 **Size:** {size_mb:.1f} MB ({size_gb:.1f} GB)\n\n"
        info_text += f"🔍 **Possible matches found:**\n\n"
        
        # Show top 3 results
        for idx, result in enumerate(tmdb_results[:3], 1):
            if 'name' in result:  # TV show
                title = result.get('name', 'Unknown')
                year = result.get('first_air_date', '')[:4]
                emoji = "📺"
            else:  # Movie
                title = result.get('title', 'Unknown')
                year = result.get('release_date', '')[:4]
                emoji = "🎬"
            
            info_text += f"{idx}. {emoji} **{title}**"
            if year:
                info_text += f" ({year})"
            info_text += "\n"
        
        info_text += "\n**Select the correct one or choose type:**"
        
        buttons = []
        # Add buttons for each result
        for idx, result in enumerate(tmdb_results[:3], 1):
            title = result.get('name' if 'name' in result else 'title', 'Unknown')
            if len(title) > 20:
                title = title[:17] + "..."
            buttons.append([Button.inline(f"{idx}. {title}", f"tmdb_{idx}_{event.message.id}")])
        
        buttons.append([
            Button.inline("🎬 Movie", f"movie_{event.message.id}"),
            Button.inline("📺 TV Show", f"tv_{event.message.id}")
        ])
        buttons.append([Button.inline("❌ Cancel", f"cancel_{event.message.id}")])
        
        await initial_msg.edit(info_text + space_warning, buttons=buttons)
        
    else:
        # No TMDB match or low confidence - fallback to original behavior
        info_text = ""
        if series_info['season']:
            info_text = f"\n\n📺 **Detected:** {series_info['series_name']}\n"
            info_text += f"📅 Season {series_info['season']}"
            if series_info['episode']:
                info_text += f", Episode {series_info['episode']}"
        else:
            info_text = f"\n\n🎬 **Possible title:** {movie_folder}"
            if any(x in display_filename.lower() for x in ['ep', 'episode', 'x0', 'x1', 'x2']):
                info_text += f"\n⚠️ Looks like a TV show but can't identify the season"
        
        if TMDB_API_KEY and not tmdb_results:
            info_text += "\n\n⚠️ No TMDB match found - using filename info"
        
        buttons = [
            [
                Button.inline("🎬 Movie", f"movie_{event.message.id}"),
                Button.inline("📺 TV Show", f"tv_{event.message.id}")
            ],
            [Button.inline("❌ Cancel", f"cancel_{event.message.id}")]
        ]
        
        if initial_msg:
            await initial_msg.edit(
                f"📁 **File received:**\n"
                f"`{display_filename}`\n"
                f"📏 Size: **{size_mb:.1f} MB** ({size_gb:.1f} GB)"
                f"{info_text}\n"
                f"{space_warning}\n\n"
                f"**Is this a movie or TV show?**",
                buttons=buttons
            )
        else:
            msg = await event.reply(
                f"📁 **File received:**\n"
                f"`{display_filename}`\n"
                f"📏 Size: **{size_mb:.1f} MB** ({size_gb:.1f} GB)"
                f"{info_text}\n"
                f"{space_warning}\n\n"
                f"**Is this a movie or TV show?**",
                buttons=buttons
            )
            initial_msg = msg
    
    # Store download info with TMDB data
    active_downloads[event.message.id] = {
        'filename': detected_name if detected_name else filename,
        'size': event.file.size,
        'message': event.message,
        'progress_msg': initial_msg,
        'progress': 0,
        'user_id': event.sender_id,
        'movie_folder': movie_folder,
        'series_info': series_info,
        'tmdb_results': tmdb_results,
        'selected_tmdb': selected_tmdb,
        'tmdb_confidence': tmdb_confidence
    }

@client.on(events.CallbackQuery)
async def callback_handler(event):
    """Handle button clicks with TMDB support"""
    if event.sender_id not in AUTHORIZED_USERS:
        await event.answer("❌ Not authorized", alert=True)
        return
        
    data = event.data.decode('utf-8')
    
    # Handle TMDB selection
    if data.startswith('tmdb_'):
        parts = data.split('_')
        result_idx = int(parts[1]) - 1
        msg_id = int(parts[2])
        
        if msg_id not in active_downloads:
            await event.answer("❌ Download expired or already completed")
            return
        
        download_info = active_downloads[msg_id]
        if download_info['tmdb_results'] and result_idx < len(download_info['tmdb_results']):
            download_info['selected_tmdb'] = download_info['tmdb_results'][result_idx]
            download_info['tmdb_confidence'] = 100  # User confirmed
            
            # Determine if it's a movie or TV show
            if 'name' in download_info['selected_tmdb']:  # TV show
                await callback_handler_process(event, 'tv', msg_id)
            else:  # Movie
                await callback_handler_process(event, 'movie', msg_id)
        return
    
    # Handle confirm from high confidence match
    if data.startswith('confirm_'):
        msg_id = int(data.split('_')[1])
        
        if msg_id not in active_downloads:
            await event.answer("❌ Download expired or already completed")
            return
        
        download_info = active_downloads[msg_id]
        # Auto-detect movie vs TV from TMDB result
        if download_info.get('selected_tmdb'):
            if 'name' in download_info['selected_tmdb']:  # TV show
                await callback_handler_process(event, 'tv', msg_id)
            else:  # Movie
                await callback_handler_process(event, 'movie', msg_id)
        return
    
    # Handle search again
    if data.startswith('search_'):
        msg_id = int(data.split('_')[1])
        
        if msg_id not in active_downloads:
            await event.answer("❌ Download expired or already completed")
            return
        
        # Clear TMDB selection and show manual selection
        download_info = active_downloads[msg_id]
        download_info['selected_tmdb'] = None
        download_info['tmdb_confidence'] = 0
        
        buttons = [
            [
                Button.inline("🎬 Movie", f"movie_{msg_id}"),
                Button.inline("📺 TV Show", f"tv_{msg_id}")
            ],
            [Button.inline("❌ Cancel", f"cancel_{msg_id}")]
        ]
        
        await event.edit(
            f"📁 **File:** `{download_info['filename']}`\n"
            f"📏 **Size:** {format_size_gb(download_info['size']):.1f} GB\n\n"
            f"**Please select media type:**",
            buttons=buttons
        )
        return
    
    # Handle season selection
    if data.startswith('season_'):
        parts = data.split('_')
        season_num = int(parts[1])
        msg_id = int(parts[2])
        
        if msg_id not in active_downloads:
            await event.answer("❌ Download expired or already completed")
            return
        
        download_info = active_downloads[msg_id]
        download_info['selected_season'] = season_num
        
        size_gb = format_size_gb(download_info['size'])
        space_ok, free_gb = check_space_available(download_info['dest_path'], size_gb)
        
        if not space_ok:
            space_waiting_queue.append((msg_id, download_info))
            await event.edit(
                f"{download_info['emoji']} **{download_info['media_type']}**\n"
                f"📅 Season {season_num}\n\n"
                f"⏸️ **Waiting for space**\n\n"
                f"❌ Insufficient space!\n"
                f"📊 Required: {size_gb:.1f} GB (+ {MIN_FREE_SPACE_GB} GB reserved)\n"
                f"💾 Available: {free_gb:.1f} GB\n\n"
                f"Download will start automatically when space is available."
            )
            return
        
        await download_queue.put((msg_id, download_info))
        await event.edit(
            f"{download_info['emoji']} **{download_info['media_type']}**\n"
            f"📅 Season {season_num}\n\n"
            f"📥 **Preparing download...**\n"
            f"✅ Space available: {free_gb:.1f} GB"
        )
        return
    
    # Normal processing
    action, msg_id = data.split('_', 1)
    msg_id = int(msg_id)
    
    await callback_handler_process(event, action, msg_id)

async def callback_handler_process(event, action, msg_id):
    """Process callback actions"""
    if msg_id not in active_downloads:
        await event.answer("❌ Download expired or already completed")
        return
    
    download_info = active_downloads[msg_id]
    if download_info['user_id'] != event.sender_id:
        await event.answer("❌ You can only manage your own downloads", alert=True)
        return
    
    if action == "cancel":
        await event.edit("❌ Download cancelled")
        cancelled_downloads.add(msg_id)
        if msg_id in download_tasks:
            download_tasks[msg_id].cancel()
        del active_downloads[msg_id]
        return
    
    if action == "movie":
        dest_path = MOVIES_PATH
        media_type = "Movie"
        emoji = "🎬"
        download_info['is_movie'] = True
    else:  # TV show
        dest_path = TV_PATH
        media_type = "TV Show"
        emoji = "📺"
        download_info['is_movie'] = False
        
        # If TV show and no season info, ask
        if not download_info['series_info']['season']:
            season_buttons = []
            for i in range(1, 6):
                if len(season_buttons) < 1:
                    season_buttons.append([])
                season_buttons[0].append(Button.inline(f"S{i}", f"season_{i}_{msg_id}"))
            
            for i in range(6, 11):
                if len(season_buttons) < 2:
                    season_buttons.append([])
                season_buttons[1].append(Button.inline(f"S{i}", f"season_{i}_{msg_id}"))
            
            season_buttons.append([Button.inline("❌ Cancel", f"cancel_{msg_id}")])
            
            series_name = download_info['series_info']['series_name']
            if download_info.get('selected_tmdb'):
                series_name = download_info['selected_tmdb'].get('name', series_name)
            
            await event.edit(
                f"📺 **TV Show selected**\n\n"
                f"📁 Series: `{series_name}`\n"
                f"📄 File: `{download_info['filename']}`\n\n"
                f"**Which season is this?**",
                buttons=season_buttons
            )
            
            download_info['dest_path'] = dest_path
            download_info['media_type'] = media_type
            download_info['emoji'] = emoji
            download_info['event'] = event
            return
    
    download_info['dest_path'] = dest_path
    download_info['media_type'] = media_type
    download_info['emoji'] = emoji
    download_info['event'] = event
    
    if not download_info['is_movie'] and download_info['series_info']['season']:
        download_info['selected_season'] = download_info['series_info']['season']
    
    size_gb = format_size_gb(download_info['size'])
    space_ok, free_gb = check_space_available(dest_path, size_gb)
    
    if not space_ok:
        space_waiting_queue.append((msg_id, download_info))
        
        await event.edit(
            f"{emoji} **{media_type}** selected\n\n"
            f"⏸️ **Waiting for space**\n\n"
            f"❌ Insufficient space!\n"
            f"📊 Required: {size_gb:.1f} GB (+ {MIN_FREE_SPACE_GB} GB reserved)\n"
            f"💾 Available: {free_gb:.1f} GB\n"
            f"🎯 Need: {(size_gb + MIN_FREE_SPACE_GB - free_gb):.1f} GB more\n\n"
            f"Download will start automatically when space is available.\n"
            f"Position in space queue: #{len(space_waiting_queue)}"
        )
        logger.info(f"File {download_info['filename']} waiting for space")
        return
    
    await download_queue.put((msg_id, download_info))
    
    position = download_queue.qsize()
    if len(download_tasks) >= MAX_CONCURRENT_DOWNLOADS:
        await event.edit(
            f"{emoji} **{media_type}** selected\n\n"
            f"⏳ **Queued** - Position: #{position}\n"
            f"Active downloads: {len(download_tasks)}/{MAX_CONCURRENT_DOWNLOADS}\n\n"
            f"✅ Space available: {free_gb:.1f} GB\n"
            f"Download will start automatically."
        )
    else:
        await event.edit(
            f"{emoji} **{media_type}** selected\n\n"
            f"📥 **Preparing download...**\n"
            f"✅ Space available: {free_gb:.1f} GB"
        )

# ===== WORKERS =====
async def download_worker():
    """Worker that processes download queue"""
    while True:
        try:
            while len(download_tasks) >= MAX_CONCURRENT_DOWNLOADS:
                await asyncio.sleep(1)
            
            msg_id, download_info = await download_queue.get()
            
            if msg_id in cancelled_downloads:
                logger.info(f"Download cancelled from queue: {download_info['filename']}")
                cancelled_downloads.discard(msg_id)
                continue
            
            size_gb = format_size_gb(download_info['size'])
            space_ok, free_gb = check_space_available(download_info['dest_path'], size_gb)
            
            if not space_ok:
                space_waiting_queue.append((msg_id, download_info))
                logger.warning(f"Insufficient space at download time for {download_info['filename']}")
                
                try:
                    await download_info['event'].edit(
                        f"⏸️ **Moved back to space queue**\n\n"
                        f"Space ran out while waiting.\n"
                        f"Required: {size_gb:.1f} GB, Available: {free_gb:.1f} GB"
                    )
                except:
                    pass
                continue
            
            task = asyncio.create_task(download_file(msg_id, download_info))
            download_tasks[msg_id] = task
            
            await task
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in worker: {e}", exc_info=True)

async def space_monitor_worker():
    """Worker that periodically checks space and processes waiting queue"""
    while True:
        try:
            await asyncio.sleep(SPACE_CHECK_INTERVAL)
            
            if not space_waiting_queue:
                continue
            
            processed = []
            
            for msg_id, download_info in space_waiting_queue:
                if msg_id in cancelled_downloads:
                    processed.append((msg_id, download_info))
                    continue
                
                size_gb = format_size_gb(download_info['size'])
                space_ok, free_gb = check_space_available(download_info['dest_path'], size_gb)
                
                if space_ok and len(download_tasks) < MAX_CONCURRENT_DOWNLOADS:
                    await download_queue.put((msg_id, download_info))
                    processed.append((msg_id, download_info))
                    
                    logger.info(f"Space available for {download_info['filename']}, moved to download queue")
                    
                    try:
                        await download_info['event'].edit(
                            f"{download_info['emoji']} **{download_info['media_type']}**\n\n"
                            f"✅ **Space available!**\n"
                            f"📥 Moved to download queue...\n"
                            f"💾 Free space: {free_gb:.1f} GB"
                        )
                    except:
                        pass
            
            for item in processed:
                space_waiting_queue.remove(item)
                    
        except Exception as e:
            logger.error(f"Error in space monitor: {e}", exc_info=True)

async def download_file(msg_id, download_info):
    """Execute download of a single file with TMDB naming"""
    try:
        if msg_id in cancelled_downloads:
            logger.info(f"Download already cancelled: {download_info['filename']}")
            return
            
        event = download_info['event']
        
        # Track created folders
        created_folders = []
        
        # Get episode details if TV show with TMDB match
        episode_title = None
        if not download_info.get('is_movie', True) and download_info.get('selected_tmdb'):
            if download_info['series_info']['episode']:
                episode_details = await get_episode_details(
                    download_info['selected_tmdb']['id'],
                    download_info.get('selected_season', download_info['series_info']['season']),
                    download_info['series_info']['episode']
                )
                if episode_details:
                    episode_title = episode_details.get('name')
        
        # Determine final path with TMDB naming if available
        if download_info.get('selected_tmdb') and download_info.get('tmdb_confidence', 0) >= 60:
            # Use TMDB data for naming
            folder_name, clean_filename = create_clean_filename(
                download_info['selected_tmdb'],
                download_info['filename'],
                download_info.get('is_movie', True),
                download_info.get('selected_season', download_info['series_info']['season']),
                download_info['series_info']['episode'],
                episode_title
            )
            
            if download_info.get('is_movie', True):
                folder_path = Path(download_info['dest_path']) / folder_name
                if not folder_path.exists():
                    created_folders.append(folder_path)
                folder_path.mkdir(parents=True, exist_ok=True)
                filepath = folder_path / clean_filename
            else:
                series_folder = Path(download_info['dest_path']) / folder_name
                season_num = download_info.get('selected_season', 1)
                season_folder = series_folder / f"Season {season_num:02d}"
                
                if not series_folder.exists():
                    created_folders.append(series_folder)
                if not season_folder.exists():
                    created_folders.append(season_folder)
                    
                season_folder.mkdir(parents=True, exist_ok=True)
                filepath = season_folder / clean_filename
        else:
            # Fallback to original naming logic
            if download_info.get('is_movie', True):
                folder_name = download_info['movie_folder']
                folder_path = Path(download_info['dest_path']) / folder_name
                
                if not folder_path.exists():
                    created_folders.append(folder_path)
                    
                folder_path.mkdir(parents=True, exist_ok=True)
                filepath = folder_path / download_info['filename']
            else:
                series_name = download_info['series_info']['series_name']
                season_num = download_info.get('selected_season', 1)
                
                series_folder = Path(download_info['dest_path']) / series_name
                season_folder = series_folder / f"Season {season_num:02d}"
                
                if not series_folder.exists():
                    created_folders.append(series_folder)
                if not season_folder.exists():
                    created_folders.append(season_folder)
                    
                season_folder.mkdir(parents=True, exist_ok=True)
                filepath = season_folder / download_info['filename']
        
        logger.info(f"Download started: {download_info['filename']} -> {filepath}")
        
        # Additional info for user
        if download_info.get('is_movie', True):
            path_info = f"📁 Folder: `{folder_path.name}/`\n"
        else:
            path_info = f"📁 Series: `{series_folder.name}/`\n"
            path_info += f"📅 Season: `Season {season_num:02d}/`\n"
        
        await event.edit(
            f"{download_info['emoji']} **{download_info['media_type']}**\n\n"
            f"📥 **Downloading...**\n"
            f"`{filepath.name}`\n\n"
            f"{path_info}"
            f"Initializing..."
        )
        
        last_update = time.time()
        start_time = time.time()
        
        async def progress_callback(current, total):
            nonlocal last_update
            
            if msg_id in cancelled_downloads:
                raise asyncio.CancelledError("Download cancelled by user")
            
            now = time.time()
            
            if now - last_update < 2:
                return
                
            last_update = now
            progress = (current / total) * 100
            download_info['progress'] = progress
            
            current_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            
            elapsed = now - start_time
            speed = (current / (1024 * 1024)) / elapsed if elapsed > 0 else 0
            
            if speed > 0:
                eta = (total - current) / (speed * 1024 * 1024)
                if eta < 60:
                    eta_str = f"{int(eta)}s"
                else:
                    eta_str = f"{int(eta/60)}m {int(eta%60)}s"
            else:
                eta_str = "calculating..."
            
            filled = int(progress / 5)
            bar = "█" * filled + "░" * (20 - filled)
            
            free_gb = get_free_space_gb(download_info['dest_path'])
            space_emoji = "🟢" if free_gb > WARNING_THRESHOLD_GB else "🟡" if free_gb > MIN_FREE_SPACE_GB else "🔴"
            
            try:
                await event.edit(
                    f"{download_info['emoji']} **{download_info['media_type']}**\n\n"
                    f"📥 **Downloading...**\n"
                    f"`{filepath.name}`\n\n"
                    f"{path_info}"
                    f"`[{bar}]`\n"
                    f"**{progress:.1f}%** - {current_mb:.1f}/{total_mb:.1f} MB\n"
                    f"⚡ Speed: **{speed:.1f} MB/s**\n"
                    f"⏱ Time remaining: **{eta_str}**\n"
                    f"{space_emoji} Free space: **{free_gb:.1f} GB**"
                )
            except:
                pass
        
        await client.download_media(
            download_info['message'],
            filepath,
            progress_callback=progress_callback
        )
        
        if msg_id in cancelled_downloads:
            if filepath.exists():
                filepath.unlink()
            raise asyncio.CancelledError("Download cancelled")
        
        final_free_gb = get_free_space_gb(download_info['dest_path'])
        
        # Relative path to show user
        if download_info.get('is_movie', True):
            display_path = f"{folder_path.name}/{filepath.name}"
        else:
            display_path = f"{series_folder.name}/Season {season_num:02d}/{filepath.name}"
        
        await event.edit(
            f"✅ **Download completed!**\n\n"
            f"{download_info['emoji']} Type: **{download_info['media_type']}**\n"
            f"📁 File: `{filepath.name}`\n"
            f"📂 Path: `{display_path}`\n"
            f"💾 Space remaining: **{final_free_gb:.1f} GB**\n\n"
            f"🎬 Available on your media server!"
        )
        
        logger.info(f"Download completed: {filepath}")
        
    except asyncio.CancelledError:
        logger.info(f"Download cancelled: {download_info['filename']}")
        
        # Delete partial file if exists
        if 'filepath' in locals() and filepath.exists():
            filepath.unlink()
            logger.info(f"Partial file deleted: {filepath}")
        
        # Smart cleanup: Delete empty folders
        if 'filepath' in locals():
            file_folder = filepath.parent
            
            def is_folder_empty(folder):
                try:
                    return not any(folder.iterdir())
                except:
                    return False
            
            if download_info.get('is_movie', True):
                if is_folder_empty(file_folder):
                    try:
                        file_folder.rmdir()
                        logger.info(f"Empty movie folder deleted: {file_folder}")
                    except Exception as e:
                        logger.warning(f"Could not delete movie folder: {e}")
            else:
                season_folder = file_folder
                series_folder = season_folder.parent
                
                if is_folder_empty(season_folder):
                    try:
                        season_folder.rmdir()
                        logger.info(f"Empty season folder deleted: {season_folder}")
                        
                        if is_folder_empty(series_folder):
                            try:
                                series_folder.rmdir()
                                logger.info(f"Empty series folder deleted: {series_folder}")
                            except Exception as e:
                                logger.warning(f"Could not delete series folder: {e}")
                    except Exception as e:
                        logger.warning(f"Could not delete season folder: {e}")
        
        try:
            await event.edit(f"❌ **Download cancelled**\n\nFile: `{download_info['filename']}`")
        except:
            pass
        raise
        
    except Exception as e:
        logger.error(f"Download error: {e}", exc_info=True)
        await event.edit(
            f"❌ **Error during download**\n\n"
            f"File: `{download_info['filename']}`\n"
            f"Error: `{str(e)}`"
        )
    finally:
        if msg_id in download_tasks:
            del download_tasks[msg_id]
        if msg_id in active_downloads:
            del active_downloads[msg_id]
        cancelled_downloads.discard(msg_id)

async def main():
    """Start the bot"""
    logger.info("=== MEDIABUTLER ENHANCED - MEDIA SERVER BOT ===")
    logger.info(f"Authorized users: {len(AUTHORIZED_USERS)}")
    logger.info(f"Minimum reserved space: {MIN_FREE_SPACE_GB} GB")
    logger.info(f"Concurrent downloads: max {MAX_CONCURRENT_DOWNLOADS}")
    logger.info(f"TMDB Integration: {'Enabled' if TMDB_API_KEY else 'Disabled'}")
    logger.info("Automatic folder organization: ENABLED")
    logger.info("Smart content recognition: ENABLED")
    logger.info("Bot ready!")
    
    workers = [
        asyncio.create_task(download_worker()) 
        for _ in range(MAX_CONCURRENT_DOWNLOADS)
    ]
    
    space_monitor = asyncio.create_task(space_monitor_worker())
    workers.append(space_monitor)
    
    try:
        await client.run_until_disconnected()
    finally:
        for w in workers:
            w.cancel()

if __name__ == '__main__':
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
        sys.exit(0)