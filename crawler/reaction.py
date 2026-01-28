"""Reaction (공감) crawler for Naver Blog posts."""

import re
import json
import time
import requests
from typing import Optional, Dict, Any, List, Callable

from config import HEADERS, REQUEST_DELAY


class ReactionCrawler:
    """Crawls sympathy/reaction data for blog posts."""

    def __init__(self, progress_callback: Callable[[str], None] = None):
        self.progress_callback = progress_callback
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _log(self, message: str):
        if self.progress_callback:
            self.progress_callback(message)

    def get_reactions(self, blog_id: str,
                      log_no: str) -> Optional[Dict[str, Any]]:
        """Fetch reaction/sympathy data for a post.

        Args:
            blog_id: Blog ID
            log_no: Post log number

        Returns:
            Dict with 'total_count' and 'reactions' list, or None
        """
        result = self._fetch_from_like_api(blog_id, log_no)
        if result is not None:
            return result

        # Fallback: scrape from post page via Selenium
        return self._fetch_from_selenium(blog_id, log_no)

    def _fetch_from_like_api(self, blog_id: str,
                             log_no: str) -> Optional[Dict[str, Any]]:
        """Fetch reactions via Naver's blogserver like API."""
        from urllib.parse import quote

        q_param = quote(f"BLOG[{blog_id}_{log_no}]")
        url = (f"https://apis.naver.com/blogserver/like/v1/search/contents"
               f"?suppress_response_codes=true&pool=blogid"
               f"&q={q_param}&isDuplication=false&cssIds=BLOG_PC")

        headers = {
            **HEADERS,
            'Referer': f'https://blog.naver.com/{blog_id}/{log_no}',
        }

        try:
            resp = self.session.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = json.loads(resp.text)

            contents = data.get('contents', [])
            if not contents:
                return {'total_count': 0, 'reactions': []}

            content = contents[0]
            reaction_list = content.get('reactions', [])

            reactions = []
            total_count = 0
            for r in reaction_list:
                rtype = r.get('reactionType', '')
                count = r.get('count', 0)
                if count > 0:
                    reactions.append({
                        'reaction_type': self._map_reaction_type(rtype),
                        'count': count,
                    })
                    total_count += count

            return {
                'total_count': total_count,
                'reactions': reactions,
            }

        except (requests.RequestException, json.JSONDecodeError, KeyError):
            return None

    def _fetch_from_selenium(self, blog_id: str,
                             log_no: str) -> Optional[Dict[str, Any]]:
        """Fallback: extract reactions from Selenium-rendered page."""
        try:
            from crawler.selenium_helper import get_shared_driver
            from bs4 import BeautifulSoup

            driver = get_shared_driver()
            url = f"https://blog.naver.com/{blog_id}/{log_no}"
            driver.get(url)
            time.sleep(3)

            try:
                from selenium.webdriver.common.by import By
                iframe = driver.find_element(By.ID, 'mainFrame')
                driver.switch_to.frame(iframe)
            except Exception:
                pass

            # Wait for reaction counts to load
            for _ in range(5):
                src = driver.page_source
                counts = re.findall(
                    r'u_likeit_list_count[^>]*>(\d+)<', src
                )
                non_zero = [c for c in counts if c != '0']
                if non_zero:
                    break
                time.sleep(1)

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            driver.switch_to.default_content()

            sympathy_area = soup.select_one('div.area_sympathy')
            if not sympathy_area:
                return {'total_count': 0, 'reactions': []}

            reactions = []
            total_count = 0
            seen_types = set()

            for item in sympathy_area.select('.u_likeit_list'):
                classes = [c for c in item.get('class', [])
                           if c != 'u_likeit_list']
                rtype = classes[0] if classes else None
                if not rtype or rtype in seen_types:
                    continue
                seen_types.add(rtype)

                count_el = item.select_one('._count')
                count = int(count_el.get_text(strip=True) or '0') \
                    if count_el else 0

                if count > 0:
                    reactions.append({
                        'reaction_type': self._map_reaction_type(rtype),
                        'count': count,
                    })
                    total_count += count

            return {
                'total_count': total_count,
                'reactions': reactions,
            }

        except Exception:
            return {'total_count': 0, 'reactions': []}

    def _map_reaction_type(self, code: str) -> str:
        """Map reaction type code to Korean name."""
        mapping = {
            'like': '좋아요',
            'sympathy': '공감',
            'cheer': '응원해요',
            'congrats': '축하해요',
            'love': '사랑해요',
            'wow': '놀라워요',
            'sad': '슬퍼요',
            'angry': '화나요',
            'fun': '재미있어요',
            'useful': '유용해요',
            'creative': '창의적이에요',
            'touching': '감동이에요',
            'impressive': '칭찬해요',
            'interesting': '흥미로워요',
            'thanks': '고마워요',
            'haha': '웃겨요',
        }
        return mapping.get(code.lower(), code)
