# 🎯 TMDB Setup Guide for MediaButler

## What is TMDB?

**The Movie Database (TMDB)** is a community-driven database of movies and TV series that provides:
- 🖼️ High-quality posters and artwork
- 📝 Plots and descriptions
- ⭐ Ratings and reviews
- 🎭 Cast and crew information
- 🌍 Multilingual content (including Italian)

## Why use TMDB?

**Without TMDB:**
- File saved as: `The.Walking.Dead.S11E24.FINAL.ITA.1080p.mkv`
- You have to manually choose Movie/TV
- Messy filenames with technical tags

**With TMDB:**
- File renamed: `The Walking Dead - S11E24 - Rest in Peace.mkv`
- Automatic recognition with poster
- Perfect organization for Jellyfin/Plex

## 📋 Steps to get the API Key

### 1. Register on TMDB

1. Go to https://www.themoviedb.org/signup
2. Fill out the form:
   - Username (choose any)
   - Password (secure!)
   - Email (real, confirmation required)
3. Accept the terms
4. Click "Sign Up"
5. **Confirm the email** you receive

### 2. Request API Key

1. Once logged in, go to: https://www.themoviedb.org/settings/api
2. Click **"Request an API Key"**
3. Choose **"Developer"** (it's free)
4. Fill out the form:
   - **Application Name**: MediaButler Bot (or any name)
   - **Application URL**: You can use http://localhost
   - **Application Summary**: "Personal media organization bot for my home server"
   - **Accept** the terms

### 3. Copy the API Key

After approval (immediate), you will see:
- **API Key (v3 auth)**: `8a7b9c6d5e4f3g2h1i0j9k8l7m6n5o4p` (example)
- **API Read Access Token**: (ignore this)

**Copy only the API Key (v3 auth)!**

### 4. Configure in the Bot

Add to your `.env`:
```bash
# TMDB Configuration
TMDB_API_KEY=8a7b9c6d5e4f3g2h1i0j9k8l7m6n5o4p
TMDB_LANGUAGE=it-IT  # For results in Italian
```

## 🌍 Language Options

You can change `TMDB_LANGUAGE` to get results in other languages:

- `it-IT` - Italian
- `en-US` - English
- `es-ES` - Spanish
- `fr-FR` - French
- `de-DE` - German
- `ja-JP` - Japanese

## 🚀 Test Functionality

After configuration:

1. Restart the bot
2. Use `/start` - it should say "✅ TMDB Integration Active"
3. Send a video file
4. The bot should:
   - Show "🔍 Searching TMDB database..."
   - Find the match with poster
   - Show detailed info

## ⚠️ Troubleshooting

### "TMDB not configured"
- Check that you saved the `.env`
- Make sure the API key is correct
- Restart the bot/container

### No results found
- The filename might be too "messy"
- Try with simpler filenames
- Check the configured language

### Rate Limiting
- TMDB allows 40 requests every 10 seconds
- More than enough for personal use
- If you exceed the limit, wait 10 seconds

## 📊 Free API Limits

With a free account you get:
- ✅ **Unlimited** searches per day
- ✅ **40 requests** every 10 seconds
- ✅ Access to **all** the database
- ✅ **No cost**

More than enough for personal/family use!

## 🎯 Tips for Best Results

1. **Well-named files** = better matches
   - ✅ `Breaking.Bad.S01E01.mkv`
   - ❌ `bb.1x1.ITA.CR@ZY.N@M3.mkv`

2. **Year in movie files** helps a lot:
   - ✅ `Avatar.2009.mkv`
   - ✅ `Avatar (2009).mkv`

3. **Anime episodes**: better with series name
   - ✅ `One Piece 1081.mkv`
   - ❌ `OP1081.mkv`

## 🔒 Privacy and Security

- TMDB **does not track** what you download
- The API key is only to identify your app
- No personal data is shared
- The bot works **locally only**

## 💡 Advanced Features

With TMDB enabled, the bot can:

1. **Auto-detect** movie vs TV show
2. **Rename** with episode titles
3. **Show posters** as preview
4. **Fuzzy match** for messy names
5. **Multi-language** for international content
6. **Safe fallback** if TMDB is offline

## 🆘 Support

Problems with TMDB?
- API Documentation: https://developers.themoviedb.org/3
- TMDB Forum: https://www.themoviedb.org/talk
- Bot GitHub: [your repo]

---

**Note**: TMDB is optional. The bot also works without it, but with TMDB the experience is **much** better!