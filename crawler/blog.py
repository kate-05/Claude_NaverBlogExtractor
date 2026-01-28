"""Blog metadata crawler for Naver Blog."""

import re
import time
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, Callable

from config import HEADERS, BLOG_REQUEST_DELAY


class BlogCrawler:
    """Crawls blog-level metadata (name, author)."""

    def __init__(self, progress_callback: Callable[[str], None] = None):
        self.progress_callback = progress_callback
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _log(self, message: str):
        if self.progress_callback:
            self.progress_callback(message)

    def get_blog_info(self, blog_id: str) -> Optional[Dict[str, Any]]:
        """Fetch blog metadata from Naver.

        Args:
            blog_id: Naver blog ID

        Returns:
            Dict with id, blog_name, author_name, url, post_count or None
        """
        url = f"https://m.blog.naver.com/{blog_id}"
        self._log(f"블로그 정보 가져오는 중: {blog_id}")

        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            self._log(f"블로그 접근 실패: {e}")
            return None

        soup = BeautifulSoup(resp.text, 'html.parser')

        blog_name = self._extract_blog_name(soup, blog_id)
        author_name = self._extract_author_name(soup, blog_id)
        post_count = self._get_post_count(blog_id)

        time.sleep(BLOG_REQUEST_DELAY)

        return {
            'id': blog_id,
            'blog_name': blog_name or blog_id,
            'author_name': author_name or blog_id,
            'url': f"https://blog.naver.com/{blog_id}",
            'post_count': post_count,
        }

    def _extract_blog_name(self, soup: BeautifulSoup,
                           blog_id: str) -> Optional[str]:
        """Extract blog title from page."""
        # Try meta og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title['content'].strip()
            if title:
                # Remove trailing " : 네이버 블로그" if present
                title = re.sub(r'\s*:\s*네이버\s*블로그\s*$', '', title)
                return title

        # Try title tag
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
            title = re.sub(r'\s*:\s*네이버\s*블로그\s*$', '', title)
            if title:
                return title

        # Try blog nickname area
        nick = soup.find('span', class_='nick')
        if nick:
            return nick.get_text(strip=True)

        return None

    def _extract_author_name(self, soup: BeautifulSoup,
                             blog_id: str) -> Optional[str]:
        """Extract author nickname from page."""
        # Try nickname span
        nick = soup.find('span', class_='nick')
        if nick:
            return nick.get_text(strip=True)

        # Try profile area
        profile_nick = soup.find('strong', class_='nick')
        if profile_nick:
            return profile_nick.get_text(strip=True)

        # Try meta author
        meta_author = soup.find('meta', attrs={'name': 'author'})
        if meta_author and meta_author.get('content'):
            return meta_author['content'].strip()

        return None

    def _get_post_count(self, blog_id: str) -> int:
        """Get the total number of posts via blog post list page."""
        url = (f"https://blog.naver.com/PostList.naver"
               f"?blogId={blog_id}&categoryNo=0&from=postList")

        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Try to find total post count from the page
            count_area = soup.find('span', class_='category_title')
            if count_area:
                match = re.search(r'(\d[\d,]*)', count_area.get_text())
                if match:
                    return int(match.group(1).replace(',', ''))

            # Fallback: try the category count area
            count_elem = soup.find('em', class_='cnt')
            if count_elem:
                text = count_elem.get_text(strip=True)
                match = re.search(r'(\d[\d,]*)', text)
                if match:
                    return int(match.group(1).replace(',', ''))

        except requests.RequestException:
            pass

        return 0

    def verify_blog_exists(self, blog_id: str) -> bool:
        """Check if a blog ID is valid and accessible."""
        url = f"https://m.blog.naver.com/{blog_id}"
        try:
            resp = self.session.get(url, timeout=10, allow_redirects=False)
            return resp.status_code == 200
        except requests.RequestException:
            return False
