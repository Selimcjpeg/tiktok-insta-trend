"""
TikTok scraper — Apify-based keyword and profile search
"""

from typing import List, Dict
import os


class TikTokScraper:

    def __init__(self):
        self.apify_scraper = None

    def _get_apify(self):
        if self.apify_scraper is None:
            from .apify_tiktok_scraper import ApifyTikTokScraper
            self.apify_scraper = ApifyTikTokScraper()
        return self.apify_scraper

    def search_by_keyword(self, keyword: str, max_results: int = 50, days_ago: int = 10) -> List[Dict]:
        if not os.getenv('APIFY_API_TOKEN'):
            raise Exception(
                "TikTok search requires Apify.\n"
                "Set APIFY_API_TOKEN in .env to enable search."
            )
        return self._get_apify().search_by_keyword(keyword, max_results, days_ago)

    def search_by_username(self, username: str, max_results: int = 50) -> List[Dict]:
        if not os.getenv('APIFY_API_TOKEN'):
            raise Exception(
                "Profile Deep Dive requires Apify.\n"
                "Set APIFY_API_TOKEN in .env to enable this feature."
            )
        return self._get_apify().search_by_username(username, max_results)
