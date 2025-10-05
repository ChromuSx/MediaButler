"""
Database migration script for MediaButler
Migrates from old user_preferences schema to new expanded schema
"""
import asyncio
import sqlite3
from pathlib import Path


async def migrate_database():
    """Migrate database to new schema"""
    db_path = Path("data/mediabutler.db")

    if not db_path.exists():
        print(f"[OK] Database not found at {db_path} - will be created with new schema on first run")
        return

    print(f"[MIGRATING] Database: {db_path}")

    # Connect with sqlite3 directly for migration
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check if table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='user_preferences'
    """)

    if not cursor.fetchone():
        print("[OK] user_preferences table doesn't exist - will be created with new schema")
        conn.close()
        return

    # Get current columns
    cursor.execute("PRAGMA table_info(user_preferences)")
    columns = {row[1] for row in cursor.fetchall()}

    print(f"[INFO] Current columns: {columns}")

    # Check if migration is needed
    new_columns = {
        'movies_path', 'tv_path', 'max_concurrent_downloads', 'auto_confirm_threshold',
        'tmdb_language', 'subtitle_enabled', 'subtitle_languages',
        'subtitle_auto_download', 'subtitle_format', 'notify_download_complete',
        'notify_download_failed', 'notify_low_space', 'ui_language', 'compact_messages'
    }

    missing_columns = new_columns - columns

    if not missing_columns:
        print("[OK] Database already up to date!")
        conn.close()
        return

    print(f"[MIGRATE] Missing columns: {missing_columns}")
    print("[MIGRATE] Performing migration...")

    # Backup old data
    cursor.execute("SELECT * FROM user_preferences")
    old_data = cursor.fetchall()

    # Get old column names
    cursor.execute("PRAGMA table_info(user_preferences)")
    old_columns = [row[1] for row in cursor.fetchall()]

    print(f"[BACKUP] Backed up {len(old_data)} user preference records")

    # Drop old table
    cursor.execute("DROP TABLE user_preferences")
    print("[DROP] Dropped old table")

    # Create new table with expanded schema
    cursor.execute("""
        CREATE TABLE user_preferences (
            user_id INTEGER PRIMARY KEY,

            -- Paths (override global defaults)
            movies_path TEXT,
            tv_path TEXT,

            -- Download settings
            max_concurrent_downloads INTEGER,
            auto_confirm_threshold INTEGER DEFAULT 70,

            -- TMDB settings
            tmdb_language TEXT,

            -- Subtitle settings
            subtitle_enabled BOOLEAN,
            subtitle_languages TEXT,
            subtitle_auto_download BOOLEAN DEFAULT 0,
            subtitle_format TEXT,

            -- Notification settings
            notify_download_complete BOOLEAN DEFAULT 1,
            notify_download_failed BOOLEAN DEFAULT 1,
            notify_low_space BOOLEAN DEFAULT 1,

            -- UI settings
            ui_language TEXT DEFAULT 'en',
            compact_messages BOOLEAN DEFAULT 0,

            -- Timestamps
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("[CREATE] Created new table with expanded schema")

    # Migrate old data
    migrated = 0
    for row in old_data:
        user_id = row[0]
        old_values = dict(zip(old_columns, row))

        # Map old columns to new columns
        subtitle_languages = old_values.get('preferred_subtitle_languages')
        auto_download = old_values.get('auto_download_subtitles', 0)

        # Insert with new schema
        cursor.execute("""
            INSERT INTO user_preferences (
                user_id,
                subtitle_languages,
                subtitle_auto_download,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            subtitle_languages,
            auto_download,
            old_values.get('created_at'),
            old_values.get('updated_at')
        ))
        migrated += 1

    conn.commit()
    print(f"[MIGRATE] Migrated {migrated} user preference records")

    # Verify migration
    cursor.execute("SELECT COUNT(*) FROM user_preferences")
    count = cursor.fetchone()[0]
    print(f"[VERIFY] Verified {count} records in new table")

    conn.close()
    print("[SUCCESS] Migration completed successfully!")


if __name__ == "__main__":
    print("=" * 60)
    print("MediaButler Database Migration")
    print("=" * 60)
    asyncio.run(migrate_database())
    print("=" * 60)
    print("[DONE] You can now start the bot.")
    print("=" * 60)
