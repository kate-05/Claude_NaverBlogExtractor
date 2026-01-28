"""Shared Selenium WebDriver for Naver Blog crawling."""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

_driver = None


def get_shared_driver():
    """Get or create a shared headless Chrome WebDriver."""
    global _driver
    if _driver is None:
        opts = Options()
        opts.add_argument('--headless=new')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-gpu')
        opts.add_argument('--window-size=1920,1080')
        opts.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
        _driver = webdriver.Chrome(options=opts)
    return _driver


def close_shared_driver():
    """Close the shared WebDriver if open."""
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None
