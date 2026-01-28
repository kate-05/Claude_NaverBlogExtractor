"""Post list and content crawler for Naver Blog."""

import re
import time
import json
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List, Callable

from config import HEADERS, REQUEST_DELAY


class PostCrawler:
    """Crawls post list and individual post content."""

    def __init__(self, progress_callback: Callable[[str], None] = None):
        self.progress_callback = progress_callback
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _log(self, message: str):
        if self.progress_callback:
            self.progress_callback(message)

    def get_post_list(self, blog_id: str,
                      page_size: int = 30) -> List[Dict[str, Any]]:
        """Fetch all post IDs and basic info for a blog.

        Uses the Naver Blog post list API for pagination.

        Args:
            blog_id: Naver blog ID
            page_size: Number of posts per page

        Returns:
            List of dicts with id, blog_id, title, post_url
        """
        all_posts = []
        current_page = 1
        self._log("글 목록 가져오는 중...")

        while True:
            posts = self._fetch_post_page(blog_id, current_page, page_size)
            if not posts:
                break

            all_posts.extend(posts)
            self._log(f"글 목록: {len(all_posts)}개 수집됨 (페이지 {current_page})")

            if len(posts) < page_size:
                break

            current_page += 1
            time.sleep(REQUEST_DELAY)

        self._log(f"총 {len(all_posts)}개 글 목록 수집 완료")
        return all_posts

    def _fetch_post_page(self, blog_id: str, page: int,
                         page_size: int) -> List[Dict[str, Any]]:
        """Fetch a single page of post list."""
        # Use the post list API
        url = (f"https://blog.naver.com/PostTitleListAsync.naver"
               f"?blogId={blog_id}&viewdate=&currentPage={page}"
               f"&categoryNo=0&parentCategoryNo=0"
               f"&countPerPage={page_size}")

        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()

            # The response is a JS-like format, parse it
            text = resp.text.strip()
            # Try to extract post data from the response
            posts = self._parse_post_list_response(text, blog_id)
            if posts:
                return posts
        except requests.RequestException as e:
            self._log(f"글 목록 페이지 {page} 실패: {e}")
            return []

        # Fallback: scrape the HTML post list page
        return self._fetch_post_page_html(blog_id, page, page_size)

    def _parse_post_list_response(self, text: str,
                                  blog_id: str) -> List[Dict[str, Any]]:
        """Parse the PostTitleListAsync response."""
        from urllib.parse import unquote_plus

        posts = []

        # Try JSON parse first (API returns JSON-like format)
        # The response may contain invalid escapes like \' in HTML fragments
        try:
            sanitized = text.replace("\\'", "'")
            data = json.loads(sanitized)
            post_list = data.get('postList', [])
            for item in post_list:
                log_no = str(item.get('logNo', ''))
                if not log_no:
                    continue
                title = item.get('title', '')
                if title:
                    title = unquote_plus(title)
                post_url = f"https://blog.naver.com/{blog_id}/{log_no}"
                posts.append({
                    'id': f"{blog_id}_{log_no}",
                    'blog_id': blog_id,
                    'title': title or None,
                    'post_url': post_url,
                    'log_no': log_no,
                })
            return posts
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: regex extraction
        log_nos = re.findall(r'"logNo"\s*:\s*"?(\d+)"?', text)
        titles = re.findall(r'"title"\s*:\s*"([^"]*)"', text)

        if not log_nos:
            log_nos = re.findall(r'logNo=(\d+)', text)

        for i, log_no in enumerate(log_nos):
            title = titles[i] if i < len(titles) else None
            if title:
                title = unquote_plus(title)

            post_url = f"https://blog.naver.com/{blog_id}/{log_no}"
            posts.append({
                'id': f"{blog_id}_{log_no}",
                'blog_id': blog_id,
                'title': title,
                'post_url': post_url,
                'log_no': log_no,
            })

        return posts

    def _fetch_post_page_html(self, blog_id: str, page: int,
                              page_size: int) -> List[Dict[str, Any]]:
        """Fallback: Scrape post list from HTML page."""
        url = (f"https://blog.naver.com/PostList.naver"
               f"?blogId={blog_id}&from=postList"
               f"&categoryNo=0&currentPage={page}")

        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            posts = []
            # Find post links
            for link in soup.find_all('a', href=True):
                href = link['href']
                match = re.search(
                    rf'/{blog_id}/(\d+)', href
                )
                if match:
                    log_no = match.group(1)
                    post_id = f"{blog_id}_{log_no}"
                    # Avoid duplicates
                    if not any(p['id'] == post_id for p in posts):
                        title = link.get_text(strip=True) or None
                        posts.append({
                            'id': post_id,
                            'blog_id': blog_id,
                            'title': title if title and len(title) > 1 else None,
                            'post_url': f"https://blog.naver.com/{blog_id}/{log_no}",
                            'log_no': log_no,
                        })

            return posts

        except requests.RequestException:
            return []

    def get_post_content(self, blog_id: str,
                         log_no: str) -> Optional[Dict[str, Any]]:
        """Fetch a single post's full content using mobile version.

        Args:
            blog_id: Blog ID
            log_no: Post log number

        Returns:
            Dict with title, content, category, post_date or None
        """
        url = f"https://m.blog.naver.com/{blog_id}/{log_no}"

        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            self._log(f"글 내용 가져오기 실패 ({log_no}): {e}")
            return None

        soup = BeautifulSoup(resp.text, 'html.parser')

        title = self._extract_title(soup)
        content = self._extract_content(soup)
        category = self._extract_category(soup)
        post_date = self._extract_date(soup)

        time.sleep(REQUEST_DELAY)

        return {
            'title': title,
            'content': content,
            'category': category,
            'post_date': post_date,
        }

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract post title."""
        # Mobile version selectors
        for selector in [
            'div.se-title-text',
            'h3.se_textarea',
            'div.tit_h3',
            'div.__se_title_area',
            'h3.tit_view',
            'div.se-module-text h3',
        ]:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if text:
                    return text

        # Try og:title meta
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()

        return None

    def _extract_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract post body text content."""
        # Smart Editor ONE (SE) content area
        for selector in [
            'div.se-main-container',
            'div.__se_component_area',
            'div.post-view',
            'div#postViewArea',
            'div.se_component_wrap',
        ]:
            elem = soup.select_one(selector)
            if elem:
                # Remove script/style tags
                for tag in elem.find_all(['script', 'style']):
                    tag.decompose()

                # Get text with paragraph breaks
                paragraphs = []
                for p in elem.find_all(['p', 'div', 'span'],
                                       class_=re.compile(
                                           r'se-text|se-module-text'
                                       )):
                    text = p.get_text(strip=True)
                    if text:
                        paragraphs.append(text)

                if paragraphs:
                    return '\n'.join(paragraphs)

                # Fallback: get all text
                text = elem.get_text(separator='\n', strip=True)
                if text:
                    return text

        # og:description fallback
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()

        return None

    def _extract_category(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract post category."""
        for selector in [
            'a.blog_ctg',
            'em.category',
            'a.pcol2',
            'span.cate',
            'a[class*="category"]',
        ]:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if text:
                    return text

        return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract post date."""
        for selector in [
            '.blog_date',
            'span.se_publishDate',
            'span.date',
            'p.date',
            'span[class*="date"]',
        ]:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if text:
                    # Clean up the date string
                    text = text.replace('/', '.').strip()
                    return text

        return None
