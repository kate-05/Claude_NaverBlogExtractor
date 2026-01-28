"""SQLite database table definitions for Naver Blog Crawler."""

import sqlite3
from pathlib import Path

CREATE_BLOGS_TABLE = """
CREATE TABLE IF NOT EXISTS blogs (
    id TEXT PRIMARY KEY,
    blog_name TEXT NOT NULL,
    author_name TEXT,
    url TEXT NOT NULL,
    post_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_POSTS_TABLE = """
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    blog_id TEXT NOT NULL,
    title TEXT,
    content TEXT,
    category TEXT,
    post_url TEXT,
    post_date DATETIME,
    comment_count INTEGER DEFAULT 0,
    sympathy_count INTEGER DEFAULT 0,
    crawl_status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (blog_id) REFERENCES blogs(id)
);
"""

CREATE_REACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS reactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL,
    reaction_type TEXT NOT NULL,
    count INTEGER DEFAULT 0,
    FOREIGN KEY (post_id) REFERENCES posts(id),
    UNIQUE(post_id, reaction_type)
);
"""

CREATE_COMMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL,
    parent_id TEXT,
    author TEXT,
    content TEXT,
    like_count INTEGER DEFAULT 0,
    written_at DATETIME,
    is_reply INTEGER DEFAULT 0,
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (parent_id) REFERENCES comments(id)
);
"""

CREATE_PROGRESS_TABLE = """
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blog_id TEXT NOT NULL UNIQUE,
    current_post_index INTEGER DEFAULT 0,
    total_posts INTEGER DEFAULT 0,
    current_step TEXT DEFAULT 'blog_info',
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (blog_id) REFERENCES blogs(id)
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_posts_blog_id ON posts(blog_id);",
    "CREATE INDEX IF NOT EXISTS idx_reactions_post_id ON reactions(post_id);",
    "CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);",
    "CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON comments(parent_id);",
    "CREATE INDEX IF NOT EXISTS idx_progress_blog_id ON progress(blog_id);",
]


def init_database(db_path: Path) -> sqlite3.Connection:
    """Initialize the SQLite database with all required tables."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(CREATE_BLOGS_TABLE)
    cursor.execute(CREATE_POSTS_TABLE)
    cursor.execute(CREATE_REACTIONS_TABLE)
    cursor.execute(CREATE_COMMENTS_TABLE)
    cursor.execute(CREATE_PROGRESS_TABLE)

    for index_sql in CREATE_INDEXES:
        cursor.execute(index_sql)

    conn.commit()

    return conn
