"""Configuration settings for Naver Blog Crawler."""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Database settings
DATABASE_NAME = "naver_blog_crawler.db"
DATABASE_PATH = BASE_DIR / DATABASE_NAME

# Progress file
PROGRESS_FILE = "crawl_progress.json"
PROGRESS_PATH = BASE_DIR / PROGRESS_FILE

# Rate limiting (seconds between requests)
REQUEST_DELAY = 1.5  # Delay between individual post requests
BLOG_REQUEST_DELAY = 2.0  # Delay after blog info requests
COMMENT_REQUEST_DELAY = 1.0  # Delay between comment page requests

# Request settings
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
}

# Export settings
EXPORT_DIR = BASE_DIR / "exports"

# GUI settings
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
APPEARANCE_MODE = "dark"  # "dark", "light", or "system"
COLOR_THEME = "blue"  # "blue", "green", "dark-blue"

# Access code settings (for distribution control)
# Format: "CODE": "YYYY-MM-DD" (expiry date)
ACCESS_CODES = {
    "KATE2026Q1": "2026-03-31",  # 1분기 수강생
    "KATE2026Q2": "2026-06-30",  # 2분기 수강생
    "KATE2026Q3": "2026-09-30",  # 3분기 수강생
    "KATE2026Q4": "2026-12-31",  # 4분기 수강생
}

# Status constants
class Status:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    FAILED = "failed"

# Crawling steps
class CrawlStep:
    BLOG_INFO = "blog_info"
    POST_LIST = "post_list"
    POST_CONTENT = "post_content"
    REACTIONS = "reactions"
    COMMENTS = "comments"

    @classmethod
    def all_steps(cls):
        return [
            cls.BLOG_INFO,
            cls.POST_LIST,
            cls.POST_CONTENT,
            cls.REACTIONS,
            cls.COMMENTS,
        ]
