"""Comment and reply crawler for Naver Blog posts."""

import re
import time
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List, Callable

from config import HEADERS, COMMENT_REQUEST_DELAY


class CommentCrawler:
    """Crawls comments and replies for blog posts using Selenium."""

    def __init__(self, progress_callback: Callable[[str], None] = None):
        self.progress_callback = progress_callback

    def _log(self, message: str):
        if self.progress_callback:
            self.progress_callback(message)

    def get_comments(self, blog_id: str,
                     log_no: str) -> List[Dict[str, Any]]:
        """Fetch all comments and replies for a post.

        Uses Selenium to load the fully-rendered blog page,
        then parses comment elements from the DOM.

        Args:
            blog_id: Blog ID
            log_no: Post log number

        Returns:
            List of comment dicts with id, post_id, parent_id, author,
            content, like_count, written_at, is_reply
        """
        post_id = f"{blog_id}_{log_no}"

        try:
            return self._fetch_comments_selenium(blog_id, log_no, post_id)
        except Exception as e:
            self._log(f"댓글 가져오기 실패 ({log_no}): {e}")
            return []

    def _fetch_comments_selenium(self, blog_id: str, log_no: str,
                                  post_id: str) -> List[Dict[str, Any]]:
        """Fetch comments using Selenium-rendered page."""
        from crawler.selenium_helper import get_shared_driver
        from selenium.webdriver.common.by import By

        driver = get_shared_driver()

        url = f"https://blog.naver.com/{blog_id}/{log_no}"
        driver.get(url)
        time.sleep(3)

        # Switch to mainFrame iframe
        try:
            iframe = driver.find_element(By.ID, 'mainFrame')
            driver.switch_to.frame(iframe)
        except Exception:
            pass

        # Scroll to bottom to trigger comment loading
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(2)

        # Click comment button/area to trigger comment loading
        click_selectors = [
            '.btn_comment',
            '.area_comment',
            'a[class*="comment"]',
        ]
        for sel in click_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elements:
                    if el.is_displayed():
                        driver.execute_script("arguments[0].click();", el)
                        time.sleep(1)
                        break
            except Exception:
                pass

        time.sleep(3)

        # Wait for comment elements to appear in page source
        for _ in range(10):
            src = driver.page_source
            if re.search(r'class="[^"]*u_cbox_nick[^"]*"', src):
                break
            time.sleep(1)

        # Collect comments from all pages
        all_comments = []
        seen_ids = set()
        max_pages = 50  # Safety limit

        for page_num in range(max_pages):
            src = driver.page_source
            soup = BeautifulSoup(src, 'html.parser')

            # Parse comments from current page
            page_comments = self._parse_cbox_comments(soup, post_id)
            if not page_comments:
                page_comments = self._parse_naver_blog_comments(
                    soup, post_id, log_no
                )
            if not page_comments:
                page_comments = self._parse_comments_regex(src, post_id)

            # Add only new comments (avoid duplicates)
            new_count = 0
            for c in page_comments:
                if c['id'] not in seen_ids:
                    seen_ids.add(c['id'])
                    all_comments.append(c)
                    new_count += 1

            # Try to go to next page
            try:
                # Find next page button
                next_btns = driver.find_elements(
                    By.CSS_SELECTOR, '.u_cbox_page a.u_cbox_next'
                )
                next_btn = None
                for btn in next_btns:
                    if btn.is_displayed() and btn.is_enabled():
                        # Check if it's not disabled
                        classes = btn.get_attribute('class') or ''
                        if 'disabled' not in classes and 'dimmed' not in classes:
                            next_btn = btn
                            break

                if next_btn:
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(2)
                else:
                    # No next button, try clicking page numbers
                    page_nums = driver.find_elements(
                        By.CSS_SELECTOR, '.u_cbox_page .u_cbox_num_page'
                    )
                    clicked = False
                    for pn in page_nums:
                        try:
                            num_text = pn.text.strip()
                            if num_text.isdigit() and int(num_text) == page_num + 2:
                                driver.execute_script("arguments[0].click();", pn)
                                time.sleep(2)
                                clicked = True
                                break
                        except Exception:
                            pass
                    if not clicked:
                        break  # No more pages
            except Exception:
                break

        # Try to switch back to default content
        try:
            driver.switch_to.default_content()
        except Exception:
            pass

        return all_comments

    def _parse_cbox_comments(self, soup: BeautifulSoup,
                              post_id: str) -> List[Dict[str, Any]]:
        """Parse standard Naver cbox comment elements."""
        comments = []

        comment_items = soup.select('li.u_cbox_comment')
        if not comment_items:
            comment_items = soup.select('.u_cbox_comment_box')

        for item in comment_items:
            comment_id = self._extract_comment_id(item)

            # Author
            nick = (item.select_one('.u_cbox_nick')
                    or item.select_one('.u_cbox_name'))
            author = nick.get_text(strip=True) if nick else ''

            # Content
            content_el = (item.select_one('.u_cbox_contents')
                          or item.select_one('.u_cbox_text_wrap')
                          or item.select_one('.u_cbox_comment'))
            content = content_el.get_text(strip=True) if content_el else ''

            if not author and not content:
                continue

            # Date
            date_el = item.select_one('.u_cbox_date')
            written_at = date_el.get_text(strip=True) if date_el else ''

            # Like count
            like_el = item.select_one('.u_cbox_cnt_recomm')
            like_count = 0
            if like_el:
                like_text = like_el.get_text(strip=True)
                like_count = int(like_text) if like_text.isdigit() else 0

            # Reply detection
            is_reply = ('reply' in ' '.join(item.get('class', []))
                        or bool(item.select_one('.u_cbox_reply_area')))

            parent_id = None
            if is_reply:
                parent_el = item.find_previous(
                    class_=lambda c: c and 'u_cbox_comment' in ' '.join(c)
                                     and 'reply' not in ' '.join(c)
                )
                if parent_el:
                    parent_cid = self._extract_comment_id(parent_el)
                    if parent_cid:
                        parent_id = f"{post_id}_c{parent_cid}"

            comments.append({
                'id': f"{post_id}_c{comment_id}" if comment_id else f"{post_id}_c{len(comments)}",
                'post_id': post_id,
                'parent_id': parent_id,
                'author': author,
                'content': content,
                'like_count': like_count,
                'written_at': written_at,
                'is_reply': 1 if is_reply else 0,
            })

        return comments

    def _parse_naver_blog_comments(self, soup: BeautifulSoup,
                                    post_id: str,
                                    log_no: str) -> List[Dict[str, Any]]:
        """Parse Naver blog's own comment module structure."""
        comments = []

        # Find elements matching naverComment_{id}_{logNo}__comment_{commentNo}
        pattern = re.compile(
            rf'naverComment_\d+_{log_no}__comment_(\d+)'
        )
        comment_elements = soup.find_all(
            class_=lambda c: c and any(pattern.match(cls) for cls in c)
        )

        if not comment_elements:
            return []

        for el in comment_elements:
            # Extract comment number from class
            classes = ' '.join(el.get('class', []))
            match = pattern.search(classes)
            comment_no = match.group(1) if match else str(len(comments))

            text = el.get_text(strip=True)
            if not text:
                continue

            # Try to extract structured data
            nick = el.select_one('[class*="nick"], [class*="name"]')
            content_el = el.select_one(
                '[class*="contents"], [class*="text_wrap"], [class*="comment"]'
            )
            date_el = el.select_one('[class*="date"]')
            like_el = el.select_one('[class*="recomm"]')

            author = nick.get_text(strip=True) if nick else ''
            content = content_el.get_text(strip=True) if content_el else text
            written_at = date_el.get_text(strip=True) if date_el else ''

            like_count = 0
            if like_el:
                like_text = like_el.get_text(strip=True)
                like_count = int(like_text) if like_text.isdigit() else 0

            is_reply = 'reply' in classes.lower()

            comments.append({
                'id': f"{post_id}_c{comment_no}",
                'post_id': post_id,
                'parent_id': None,
                'author': author,
                'content': content,
                'like_count': like_count,
                'written_at': written_at,
                'is_reply': 1 if is_reply else 0,
            })

        return comments

    def _parse_comments_regex(self, html: str,
                               post_id: str) -> List[Dict[str, Any]]:
        """Last resort: extract comment data using regex patterns."""
        comments = []

        # Pattern for nick + content pairs
        nick_pattern = r'u_cbox_nick[^>]*>([^<]+)<'
        content_pattern = r'u_cbox_contents[^>]*>([^<]+)<'

        nicks = re.findall(nick_pattern, html)
        contents = re.findall(content_pattern, html)

        for i in range(min(len(nicks), len(contents))):
            author = nicks[i].strip()
            content = contents[i].strip()
            if not author or not content:
                continue

            comments.append({
                'id': f"{post_id}_c{i}",
                'post_id': post_id,
                'parent_id': None,
                'author': author,
                'content': re.sub(r'<[^>]+>', '', content).strip(),
                'like_count': 0,
                'written_at': '',
                'is_reply': 0,
            })

        return comments

    def _extract_comment_id(self, element) -> str:
        """Extract comment ID from element classes or attributes."""
        classes = ' '.join(element.get('class', []))
        match = re.search(r'comment[_-]?(\d+)', classes)
        if match:
            return match.group(1)

        data_id = element.get('data-comment-id', '')
        if data_id:
            return data_id

        return ''
