"""Database manager for CRUD operations and progress tracking."""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from database.models import init_database
from config import DATABASE_PATH, Status, CrawlStep


class DatabaseManager:
    """Manages all database operations for the Naver Blog Crawler."""

    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self.conn = init_database(db_path)

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    # ==================== Blog Operations ====================

    def add_blog(self, blog_id: str, blog_name: str, url: str,
                 author_name: str = None, post_count: int = 0) -> bool:
        """Add a new blog to the database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO blogs (id, blog_name, author_name, url, post_count, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (blog_id, blog_name, author_name, url, post_count, Status.PENDING))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_blog(self, blog_id: str) -> Optional[Dict[str, Any]]:
        """Get blog information by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM blogs WHERE id = ?", (blog_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_blogs(self) -> List[Dict[str, Any]]:
        """Get all blogs from the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM blogs ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def update_blog_status(self, blog_id: str, status: str) -> bool:
        """Update blog crawling status."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE blogs SET status = ? WHERE id = ?
        """, (status, blog_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_blog_post_count(self, blog_id: str, count: int) -> bool:
        """Update the total post count for a blog."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE blogs SET post_count = ? WHERE id = ?
        """, (count, blog_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_blog_info(self, blog_id: str, blog_name: str = None,
                         author_name: str = None) -> bool:
        """Update blog name and author name."""
        updates = []
        params = []
        if blog_name is not None:
            updates.append("blog_name = ?")
            params.append(blog_name)
        if author_name is not None:
            updates.append("author_name = ?")
            params.append(author_name)
        if not updates:
            return False
        params.append(blog_id)
        cursor = self.conn.cursor()
        cursor.execute(f"""
            UPDATE blogs SET {', '.join(updates)} WHERE id = ?
        """, params)
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_blog(self, blog_id: str) -> bool:
        """Delete a blog and all associated data."""
        cursor = self.conn.cursor()

        # Get all post IDs for this blog
        cursor.execute("SELECT id FROM posts WHERE blog_id = ?", (blog_id,))
        post_ids = [row['id'] for row in cursor.fetchall()]

        # Delete comments and reactions for all posts
        for post_id in post_ids:
            cursor.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
            cursor.execute("DELETE FROM reactions WHERE post_id = ?", (post_id,))

        # Delete posts
        cursor.execute("DELETE FROM posts WHERE blog_id = ?", (blog_id,))

        # Delete progress
        cursor.execute("DELETE FROM progress WHERE blog_id = ?", (blog_id,))

        # Delete blog
        cursor.execute("DELETE FROM blogs WHERE id = ?", (blog_id,))

        self.conn.commit()
        return True

    # ==================== Post Operations ====================

    def add_post(self, post_id: str, blog_id: str, title: str = None,
                 post_url: str = None) -> bool:
        """Add a new post to the database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO posts (id, blog_id, title, post_url)
                VALUES (?, ?, ?, ?)
            """, (post_id, blog_id, title, post_url))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def add_posts_batch(self, posts: List[Dict[str, Any]]) -> int:
        """Add multiple posts in a batch."""
        cursor = self.conn.cursor()
        added = 0
        for post in posts:
            try:
                cursor.execute("""
                    INSERT INTO posts (id, blog_id, title, post_url)
                    VALUES (?, ?, ?, ?)
                """, (post['id'], post['blog_id'],
                      post.get('title'), post.get('post_url')))
                added += 1
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()
        return added

    def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Get post information by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_blog_posts(self, blog_id: str) -> List[Dict[str, Any]]:
        """Get all posts for a blog."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM posts WHERE blog_id = ?
            ORDER BY created_at
        """, (blog_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_posts_by_status(self, blog_id: str,
                            crawl_status: str = None) -> List[Dict[str, Any]]:
        """Get posts filtered by crawl status."""
        cursor = self.conn.cursor()
        conditions = ["blog_id = ?"]
        params = [blog_id]

        if crawl_status:
            conditions.append("crawl_status = ?")
            params.append(crawl_status)

        query = f"SELECT * FROM posts WHERE {' AND '.join(conditions)}"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def update_post_content(self, post_id: str, title: str = None,
                            content: str = None, category: str = None,
                            post_date: str = None) -> bool:
        """Update post content details."""
        updates = []
        params = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if post_date is not None:
            updates.append("post_date = ?")
            params.append(post_date)

        if not updates:
            return False

        params.append(post_id)
        cursor = self.conn.cursor()
        cursor.execute(f"""
            UPDATE posts SET {', '.join(updates)} WHERE id = ?
        """, params)
        self.conn.commit()
        return cursor.rowcount > 0

    def update_post_crawl_status(self, post_id: str, status: str) -> bool:
        """Update post crawl status."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE posts SET crawl_status = ? WHERE id = ?
        """, (status, post_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_post_sympathy_count(self, post_id: str, count: int) -> bool:
        """Update post total sympathy count."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE posts SET sympathy_count = ? WHERE id = ?
        """, (count, post_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_post_comment_count(self, post_id: str, count: int) -> bool:
        """Update post comment count."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE posts SET comment_count = ? WHERE id = ?
        """, (count, post_id))
        self.conn.commit()
        return cursor.rowcount > 0

    # ==================== Reaction Operations ====================

    def add_reaction(self, post_id: str, reaction_type: str,
                     count: int) -> bool:
        """Add or update a reaction for a post."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO reactions (post_id, reaction_type, count)
                VALUES (?, ?, ?)
            """, (post_id, reaction_type, count))
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False

    def add_reactions_batch(self, reactions: List[Dict[str, Any]]) -> int:
        """Add multiple reactions in a batch."""
        cursor = self.conn.cursor()
        added = 0
        for reaction in reactions:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO reactions (post_id, reaction_type, count)
                    VALUES (?, ?, ?)
                """, (reaction['post_id'], reaction['reaction_type'],
                      reaction.get('count', 0)))
                added += 1
            except sqlite3.Error:
                pass
        self.conn.commit()
        return added

    def get_reactions(self, post_id: str) -> List[Dict[str, Any]]:
        """Get all reactions for a post."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM reactions WHERE post_id = ?
        """, (post_id,))
        return [dict(row) for row in cursor.fetchall()]

    # ==================== Comment Operations ====================

    def add_comment(self, comment_id: str, post_id: str, author: str,
                    content: str, like_count: int = 0,
                    written_at: str = None, parent_id: str = None,
                    is_reply: int = 0) -> bool:
        """Add a comment for a post."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO comments
                (id, post_id, parent_id, author, content, like_count, written_at, is_reply)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (comment_id, post_id, parent_id, author, content,
                  like_count, written_at, is_reply))
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False

    def add_comments_batch(self, comments: List[Dict[str, Any]]) -> int:
        """Add multiple comments in a batch."""
        cursor = self.conn.cursor()
        added = 0
        for comment in comments:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO comments
                    (id, post_id, parent_id, author, content, like_count, written_at, is_reply)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    comment['id'],
                    comment['post_id'],
                    comment.get('parent_id'),
                    comment.get('author'),
                    comment.get('content'),
                    comment.get('like_count', 0),
                    comment.get('written_at'),
                    comment.get('is_reply', 0),
                ))
                added += 1
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()
        return added

    def get_comments(self, post_id: str,
                     include_replies: bool = True) -> List[Dict[str, Any]]:
        """Get all comments for a post."""
        cursor = self.conn.cursor()
        if include_replies:
            cursor.execute("""
                SELECT * FROM comments WHERE post_id = ?
                ORDER BY written_at
            """, (post_id,))
        else:
            cursor.execute("""
                SELECT * FROM comments WHERE post_id = ? AND is_reply = 0
                ORDER BY written_at
            """, (post_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_comment_count(self, post_id: str) -> int:
        """Get the number of comments for a post."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM comments WHERE post_id = ?
        """, (post_id,))
        return cursor.fetchone()['count']

    # ==================== Progress Operations ====================

    def init_progress(self, blog_id: str, total_posts: int) -> bool:
        """Initialize progress tracking for a blog."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO progress
                (blog_id, current_post_index, total_posts, current_step, last_updated)
                VALUES (?, 0, ?, ?, ?)
            """, (blog_id, total_posts, CrawlStep.BLOG_INFO,
                  datetime.now().isoformat()))
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False

    def get_progress(self, blog_id: str) -> Optional[Dict[str, Any]]:
        """Get progress for a blog."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM progress WHERE blog_id = ?
        """, (blog_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_progress(self, blog_id: str, current_post_index: int = None,
                        current_step: str = None) -> bool:
        """Update progress for a blog."""
        updates = ["last_updated = ?"]
        params = [datetime.now().isoformat()]

        if current_post_index is not None:
            updates.append("current_post_index = ?")
            params.append(current_post_index)
        if current_step is not None:
            updates.append("current_step = ?")
            params.append(current_step)

        params.append(blog_id)
        cursor = self.conn.cursor()
        cursor.execute(f"""
            UPDATE progress SET {', '.join(updates)} WHERE blog_id = ?
        """, params)
        self.conn.commit()
        return cursor.rowcount > 0

    # ==================== Statistics ====================

    def get_blog_stats(self, blog_id: str) -> Dict[str, Any]:
        """Get statistics for a blog."""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) as total FROM posts WHERE blog_id = ?
        """, (blog_id,))
        total_posts = cursor.fetchone()['total']

        cursor.execute("""
            SELECT COUNT(*) as count FROM posts
            WHERE blog_id = ? AND crawl_status = ?
        """, (blog_id, Status.COMPLETED))
        posts_completed = cursor.fetchone()['count']

        cursor.execute("""
            SELECT COUNT(*) as count FROM comments c
            JOIN posts p ON c.post_id = p.id
            WHERE p.blog_id = ?
        """, (blog_id,))
        total_comments = cursor.fetchone()['count']

        return {
            'total_posts': total_posts,
            'posts_completed': posts_completed,
            'total_comments': total_comments,
        }
