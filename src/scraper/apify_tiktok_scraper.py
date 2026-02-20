"""
Apify-based TikTok scraper — keyword search and profile fetch
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()


class ApifyTikTokScraper:

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv('APIFY_API_TOKEN')
        if not self.api_token:
            raise ValueError(
                "Apify API token required!\n"
                "Set APIFY_API_TOKEN in .env file."
            )
        self.client = ApifyClient(self.api_token)

    def search_by_keyword(self, keyword: str, max_results: int = 50, days_ago: int = 10) -> List[Dict]:
        print(f"🔍 Searching TikTok via Apify for: '{keyword}'")

        run_input = {
            "searchQueries": [keyword],
            "resultsPerPage": max_results,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }

        print("  📡 Running Apify TikTok Scraper...")
        run = self.client.actor("clockworks/tiktok-scraper").call(run_input=run_input)

        results = []
        cutoff_date = datetime.now() - timedelta(days=days_ago)

        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            try:
                video_data = self._parse_video(item, keyword)
                created_at = datetime.fromisoformat(video_data['created_at'].replace('Z', '+00:00'))
                if created_at.replace(tzinfo=None) >= cutoff_date:
                    results.append(video_data)
                    print(f"  ✓ @{video_data['author_username']} ({video_data['views']:,} views)")
                if len(results) >= max_results:
                    break
            except Exception as e:
                print(f"  ⚠️ Error parsing video: {e}")
                continue

        print(f"✅ Found {len(results)} videos")
        return results

    def search_by_username(self, username: str, max_results: int = 50) -> List[Dict]:
        print(f"👤 Fetching profile deep dive for @{username}...")

        run_input = {
            "profiles": [username],
            "profilesResultsPerPage": max_results,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }

        print(f"  📡 Running Apify TikTok Scraper for @{username}...")
        run = self.client.actor("clockworks/tiktok-scraper").call(run_input=run_input)

        results = []
        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            try:
                results.append(self._parse_video(item, keyword=f"profile:{username}"))
                if len(results) >= max_results:
                    break
            except Exception as e:
                print(f"  ⚠️ Error parsing video: {e}")
                continue

        print(f"✅ Fetched {len(results)} videos from @{username}")
        return results

    def _parse_video(self, item: Dict, keyword: str) -> Dict:
        author = item.get('authorMeta', {})
        music = item.get('musicMeta', {})
        video_meta = item.get('videoMeta', {})

        views = item.get('playCount', 0)
        likes = item.get('diggCount', 0)
        comments = item.get('commentCount', 0)
        shares = item.get('shareCount', 0)

        engagement_rate = ((likes + comments + shares) / views * 100) if views > 0 else 0.0

        created_timestamp = item.get('createTime', 0)
        created_at = (
            datetime.fromtimestamp(created_timestamp).isoformat()
            if created_timestamp
            else datetime.now().isoformat()
        )

        return {
            'video_id': str(item.get('id', '')),
            'author_username': author.get('name', 'unknown'),
            'author_followers': author.get('fans', 0),
            'author_verified': author.get('verified', False),
            'caption': item.get('text', ''),
            'video_url': item.get('webVideoUrl', ''),
            'download_url': video_meta.get('downloadAddr', ''),  # CDN URL for direct download
            'cover_url': video_meta.get('coverUrl', ''),
            'audio_id': str(music.get('musicId', '')),
            'audio_title': music.get('musicName', 'Original Sound'),
            'audio_author': music.get('musicAuthor', ''),
            'likes': likes,
            'comments': comments,
            'shares': shares,
            'views': views,
            'engagement_rate': engagement_rate,
            'created_at': created_at,
            'search_keyword': keyword,
        }
