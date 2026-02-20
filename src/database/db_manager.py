import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import os


class DatabaseManager:
    def __init__(self, db_path: str = "data/trends.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self.init_database()

    def _ensure_db_directory(self):
        """Create data directory if it doesn't exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Initialize database with schema"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # TikTok posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tiktok_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE NOT NULL,
                author_username TEXT,
                caption TEXT,
                video_url TEXT,
                cover_url TEXT,
                audio_id TEXT,
                audio_title TEXT,
                audio_author TEXT,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                engagement_rate REAL,
                created_at DATETIME,
                discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                search_keyword TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Instagram Reels table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS instagram_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shortcode TEXT UNIQUE NOT NULL,
                owner_username TEXT,
                caption TEXT,
                post_url TEXT,
                video_url TEXT,
                thumbnail_url TEXT,
                audio_id TEXT,
                audio_name TEXT,
                audio_artist TEXT,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                engagement_rate REAL,
                created_at DATETIME,
                discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                matched_audio_id TEXT,
                search_keyword TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Audio/Music tracks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audio_tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audio_id TEXT UNIQUE NOT NULL,
                title TEXT,
                artist TEXT,
                platform TEXT,
                usage_count INTEGER DEFAULT 0,
                avg_engagement REAL,
                is_trending BOOLEAN DEFAULT 0,
                last_checked DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Snapshots for velocity tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                video_id TEXT,
                likes INTEGER,
                comments INTEGER,
                views INTEGER,
                shares INTEGER,
                snapshot_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Search history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                result_count INTEGER,
                searched_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tiktok_created_at ON tiktok_posts(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_instagram_created_at ON instagram_posts(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tiktok_keyword ON tiktok_posts(search_keyword)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_instagram_keyword ON instagram_posts(search_keyword)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audio_trending ON audio_tracks(is_trending, usage_count)')

        conn.commit()
        conn.close()

    # TikTok Posts
    def insert_tiktok_post(self, post_data: Dict):
        """Insert or update a TikTok post"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO tiktok_posts
            (video_id, author_username, caption, video_url, cover_url,
             audio_id, audio_title, audio_author, likes, comments, shares, views,
             engagement_rate, created_at, search_keyword, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            post_data['video_id'],
            post_data.get('author_username'),
            post_data.get('caption'),
            post_data.get('video_url'),
            post_data.get('cover_url'),
            post_data.get('audio_id'),
            post_data.get('audio_title'),
            post_data.get('audio_author'),
            post_data.get('likes', 0),
            post_data.get('comments', 0),
            post_data.get('shares', 0),
            post_data.get('views', 0),
            post_data.get('engagement_rate', 0.0),
            post_data.get('created_at'),
            post_data.get('search_keyword'),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def get_tiktok_posts(self, keyword: Optional[str] = None, days_ago: int = 30, limit: int = 50) -> List[Dict]:
        """Get TikTok posts with optional filters"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = '''
            SELECT * FROM tiktok_posts
            WHERE datetime(created_at) >= datetime('now', ?)
        '''
        params = [f'-{days_ago} days']

        if keyword:
            query += ' AND search_keyword = ?'
            params.append(keyword)

        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # Instagram Posts
    def insert_instagram_post(self, post_data: Dict):
        """Insert or update an Instagram post"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO instagram_posts
            (shortcode, owner_username, caption, post_url, video_url, thumbnail_url,
             audio_id, audio_name, audio_artist, likes, comments, views,
             engagement_rate, created_at, matched_audio_id, search_keyword, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            post_data['shortcode'],
            post_data.get('owner_username'),
            post_data.get('caption'),
            post_data.get('post_url'),
            post_data.get('video_url'),
            post_data.get('thumbnail_url'),
            post_data.get('audio_id'),
            post_data.get('audio_name'),
            post_data.get('audio_artist'),
            post_data.get('likes', 0),
            post_data.get('comments', 0),
            post_data.get('views', 0),
            post_data.get('engagement_rate', 0.0),
            post_data.get('created_at'),
            post_data.get('matched_audio_id'),
            post_data.get('search_keyword'),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def get_instagram_posts(self, keyword: Optional[str] = None, days_ago: int = 30, limit: int = 50) -> List[Dict]:
        """Get Instagram posts with optional filters"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = '''
            SELECT * FROM instagram_posts
            WHERE datetime(created_at) >= datetime('now', ?)
        '''
        params = [f'-{days_ago} days']

        if keyword:
            query += ' AND search_keyword = ?'
            params.append(keyword)

        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # Audio Tracks
    def insert_audio_track(self, audio_data: Dict):
        """Insert or update an audio track"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO audio_tracks
            (audio_id, title, artist, platform, usage_count, avg_engagement, is_trending, last_checked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            audio_data['audio_id'],
            audio_data.get('title'),
            audio_data.get('artist'),
            audio_data.get('platform'),
            audio_data.get('usage_count', 0),
            audio_data.get('avg_engagement', 0.0),
            audio_data.get('is_trending', 0),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    # Search History
    def insert_search_history(self, keyword: str, result_count: int):
        """Insert search history record"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO search_history (keyword, result_count, searched_at)
            VALUES (?, ?, ?)
        ''', (keyword, result_count, datetime.now().isoformat()))

        conn.commit()
        conn.close()


def init_database(db_path: str = "data/trends.db"):
    """Initialize database - convenience function"""
    db = DatabaseManager(db_path)
    print(f"✅ Database initialized at {db_path}")
    return db


if __name__ == "__main__":
    # Test database creation
    db = init_database()
    print("Database tables created successfully!")
