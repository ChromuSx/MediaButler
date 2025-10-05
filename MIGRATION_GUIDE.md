# Database Migration Guide

## Overview

MediaButler now includes an expanded user preferences system that requires a database schema update.

## When to Migrate

You need to migrate if:
- You're upgrading from an older version of MediaButler
- You see errors like: `table user_preferences has no column named subtitle_enabled`
- You want to use the new user-specific configuration features

## How to Migrate

### Option 1: Automatic Migration (Recommended)

Run the migration script before starting the bot:

```bash
python migrate_database.py
```

### Option 2: Fresh Start

If you don't need to preserve user preferences:

1. Stop the bot
2. Delete the database file:
   ```bash
   rm data/mediabutler.db
   ```
3. Start the bot - it will create a new database with the correct schema

## What Gets Migrated

The migration script:
- ✅ Backs up existing user preferences
- ✅ Drops the old `user_preferences` table
- ✅ Creates new table with expanded schema
- ✅ Migrates existing data where applicable
- ✅ Verifies migration success

### Old Schema → New Schema Mapping

| Old Column | New Column | Notes |
|------------|------------|-------|
| `preferred_subtitle_languages` | `subtitle_languages` | Preserved |
| `auto_download_subtitles` | `subtitle_auto_download` | Preserved |
| `notifications_enabled` | _removed_ | Replaced by specific notification settings |
| `preferred_quality` | _removed_ | Not applicable to this bot type |
| _n/a_ | `subtitle_enabled` | New - per-user subtitle system toggle |
| _n/a_ | `auto_confirm_threshold` | New - auto-confirm TMDB matches |
| _n/a_ | `notify_download_complete` | New - granular notification control |
| _n/a_ | `notify_download_failed` | New - granular notification control |
| _n/a_ | `notify_low_space` | New - granular notification control |
| _n/a_ | `compact_messages` | New - UI preference |
| _n/a_ | `ui_language` | New - language preference |
| _n/a_ | `movies_path` | New - custom paths per user |
| _n/a_ | `tv_path` | New - custom paths per user |
| _n/a_ | `max_concurrent_downloads` | New - per-user limits |
| _n/a_ | `tmdb_language` | New - TMDB language preference |
| _n/a_ | `subtitle_format` | New - preferred subtitle format |

## New Features After Migration

Once migrated, users can:

- Set their own subtitle languages
- Configure auto-confirm threshold for TMDB matches
- Choose which notifications to receive
- Use compact or detailed message formats
- Customize UI language
- And more!

Access via: `/mysettings`

## Troubleshooting

### Migration Fails

If migration fails:
1. Backup your database: `cp data/mediabutler.db data/mediabutler.db.backup`
2. Try Option 2 (Fresh Start) above
3. Restore data manually if needed

### "Database is locked" Error

If you get a locked database error:
1. Stop the bot completely
2. Wait 5 seconds
3. Run migration again

### Verify Migration Success

After migration, start the bot and run:
```
/mysettings
```

You should see the new settings interface with all options available.

## Support

If you encounter issues:
1. Check the migration script output for errors
2. Verify Python version (3.10+)
3. Check file permissions on `data/` directory
4. Review bot logs for additional error details

---

**Note:** This migration is safe and non-destructive. Your download history and statistics are NOT affected - only the user_preferences table is modified.
