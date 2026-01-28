"""Utility functions for Naver Blog Crawler."""

import json
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from config import PROGRESS_PATH, CrawlStep


def extract_blog_id(url: str) -> Optional[str]:
    """Extract blog ID from various Naver Blog URL formats.

    Supported formats:
        https://blog.naver.com/블로그ID
        https://m.blog.naver.com/블로그ID
        https://blog.naver.com/PostList.naver?blogId=블로그ID
        https://blog.naver.com/PostView.naver?blogId=블로그ID&logNo=...
    """
    patterns = [
        r'blog\.naver\.com/PostList\.naver\?.*?blogId=([^&]+)',
        r'blog\.naver\.com/PostView\.naver\?.*?blogId=([^&]+)',
        r'blog\.naver\.com/([A-Za-z0-9_-]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            blog_id = match.group(1)
            # Filter out known non-blog-ID paths
            if blog_id not in ('PostList.naver', 'PostView.naver',
                               'NBlogTop.naver', 'SectionPostList.naver',
                               'PostList', 'PostView', 'NBlogTop',
                               'SectionPostList'):
                return blog_id

    return None


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be safe for use as a filename."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    name = name.strip('. ')
    if len(name) > 200:
        name = name[:200]
    return name or 'unnamed'


def parse_datetime(date_str: str) -> Optional[datetime]:
    """Parse datetime string in various formats."""
    if not date_str:
        return None

    formats = [
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%Y.%m.%d.',
        '%Y.%m.%d',
        '%Y. %m. %d.',
        '%Y. %m. %d',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    return None


def format_number(num: int) -> str:
    """Format large numbers with K/M suffixes."""
    if num is None:
        return "N/A"

    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


# ==================== Progress File Management ====================

def load_progress(progress_path: Path = PROGRESS_PATH) -> Dict[str, Any]:
    """Load progress data from JSON file."""
    if not os.path.exists(progress_path):
        return {'last_updated': None, 'blogs': []}

    try:
        with open(progress_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {'last_updated': None, 'blogs': []}


def save_progress(progress_data: Dict[str, Any],
                  progress_path: Path = PROGRESS_PATH) -> bool:
    """Save progress data to JSON file."""
    try:
        progress_data['last_updated'] = datetime.now().isoformat()
        with open(progress_path, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
        return True
    except IOError:
        return False


def has_incomplete_work(progress_data: Dict[str, Any]) -> bool:
    """Check if there's any incomplete work in progress data."""
    blogs = progress_data.get('blogs', [])
    for blog in blogs:
        if blog.get('status') == 'in_progress':
            return True

        steps = blog.get('steps_completed', {})
        for step in CrawlStep.all_steps():
            if steps.get(step) in ['pending', 'in_progress']:
                return True

    return False


def get_blog_progress(progress_data: Dict[str, Any],
                      blog_id: str) -> Optional[Dict[str, Any]]:
    """Get progress data for a specific blog."""
    for blog in progress_data.get('blogs', []):
        if blog.get('blog_id') == blog_id:
            return blog
    return None


def update_blog_progress(progress_data: Dict[str, Any],
                         blog_id: str,
                         blog_name: str = None,
                         status: str = None,
                         total_posts: int = None,
                         current_post_index: int = None,
                         step: str = None,
                         step_status: str = None) -> Dict[str, Any]:
    """Update or create blog progress data."""
    blog_progress = get_blog_progress(progress_data, blog_id)

    if not blog_progress:
        blog_progress = {
            'blog_id': blog_id,
            'blog_name': blog_name,
            'status': status or 'pending',
            'total_posts': total_posts or 0,
            'current_post_index': current_post_index or 0,
            'steps_completed': {s: 'pending' for s in CrawlStep.all_steps()}
        }
        if 'blogs' not in progress_data:
            progress_data['blogs'] = []
        progress_data['blogs'].append(blog_progress)
    else:
        if blog_name:
            blog_progress['blog_name'] = blog_name
        if status:
            blog_progress['status'] = status
        if total_posts is not None:
            blog_progress['total_posts'] = total_posts
        if current_post_index is not None:
            blog_progress['current_post_index'] = current_post_index
        if step and step_status:
            if 'steps_completed' not in blog_progress:
                blog_progress['steps_completed'] = {}
            blog_progress['steps_completed'][step] = step_status

    return progress_data


def remove_blog_from_progress(progress_data: Dict[str, Any],
                              blog_id: str) -> Dict[str, Any]:
    """Remove a blog from progress data."""
    blogs = progress_data.get('blogs', [])
    progress_data['blogs'] = [
        b for b in blogs if b.get('blog_id') != blog_id
    ]
    return progress_data


def get_next_incomplete_step(blog_progress: Dict[str, Any]) -> Optional[str]:
    """Get the next incomplete step for a blog."""
    steps = blog_progress.get('steps_completed', {})

    # First, check for any in_progress step (resume)
    for step in CrawlStep.all_steps():
        if steps.get(step) == 'in_progress':
            return step

    # Then, find the first pending step
    for step in CrawlStep.all_steps():
        status = steps.get(step, 'pending')
        if status == 'pending':
            return step

    return None


# ==================== Export Functions ====================

def export_to_json(data: Dict[str, Any], filepath: str) -> bool:
    """Export data to JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except IOError:
        return False


def export_to_csv(data: List[Dict[str, Any]], filepath: str,
                  fieldnames: List[str] = None) -> bool:
    """Export data to CSV file."""
    import csv

    if not data:
        return False

    if not fieldnames:
        fieldnames = list(data[0].keys())

    try:
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames,
                                    extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)
        return True
    except IOError:
        return False
