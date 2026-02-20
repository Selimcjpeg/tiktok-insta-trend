"""
Apify-based Instagram scraper — seed profile, native related accounts, hashtag discovery
"""

import re
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()


class ApifyInstagramScraper:
    ACTOR_IG = "apify/instagram-scraper"
    ACTOR_RELATED = "scrapio/instagram-related-person-scraper"

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv('APIFY_API_TOKEN')
        if not self.api_token:
            raise ValueError("Apify API token required! Set APIFY_API_TOKEN in .env")
        self.client = ApifyClient(self.api_token)

    # ------------------------------------------------------------------ #
    #  Seed profile                                                        #
    # ------------------------------------------------------------------ #

    def get_seed_profile(self, username: str, post_limit: int = 12) -> Dict:
        """Scrape seed account's recent posts → extract profile info + hashtags."""
        print(f"📊 Fetching seed profile @{username}...")
        run_input = {
            "directUrls": [f"https://www.instagram.com/{username}/"],
            "resultsType": "posts",
            "resultsLimit": post_limit,
            "shouldDownloadVideos": False,
            "shouldDownloadPhotos": False,
        }
        run = self.client.actor(self.ACTOR_IG).call(run_input=run_input)
        posts = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
        return self._profile_from_posts(posts, username)

    # ------------------------------------------------------------------ #
    #  Instagram native related accounts                                   #
    # ------------------------------------------------------------------ #

    def get_related_accounts(self, username: str) -> List[Dict]:
        """Instagram's own 'similar accounts' via scrapio actor."""
        print(f"🔗 Fetching Instagram native related accounts for @{username}...")
        try:
            run_input = {"usernames": [username]}
            run = self.client.actor(self.ACTOR_RELATED).call(run_input=run_input)
            items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
            print(f"  ✓ Got {len(items)} native related accounts")
            return items
        except Exception as e:
            print(f"  ⚠️ Native related accounts unavailable: {e}")
            return []

    # ------------------------------------------------------------------ #
    #  Hashtag-based candidate discovery                                   #
    # ------------------------------------------------------------------ #

    def get_hashtag_candidates(
        self, hashtags: List[str], limit_per_tag: int = 25
    ) -> List[Dict]:
        """Scrape posts from each hashtag → return partial profile dicts."""
        profiles: Dict[str, Dict] = {}
        for hashtag in hashtags[:4]:  # cap at 4 to control Apify cost
            print(f"  🏷️ Scanning #{hashtag}...")
            try:
                run_input = {
                    "directUrls": [f"https://www.instagram.com/explore/tags/{hashtag}/"],
                    "resultsType": "posts",
                    "resultsLimit": limit_per_tag,
                    "shouldDownloadVideos": False,
                    "shouldDownloadPhotos": False,
                }
                run = self.client.actor(self.ACTOR_IG).call(run_input=run_input)
                for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                    uname = (
                        item.get("ownerUsername")
                        or item.get("owner", {}).get("username", "")
                    )
                    if not uname:
                        continue
                    if uname not in profiles:
                        profiles[uname] = self._partial_profile_from_post(item, uname)
                    else:
                        # Accumulate hashtags from additional posts
                        for tag in _extract_hashtags(item.get("caption", "")):
                            if tag not in profiles[uname]["hashtags"]:
                                profiles[uname]["hashtags"].append(tag)
            except Exception as e:
                print(f"    ⚠️ Error scanning #{hashtag}: {e}")

        print(f"  ✓ Found {len(profiles)} unique candidate profiles from hashtags")
        return list(profiles.values())

    # ------------------------------------------------------------------ #
    #  Internal parsers                                                    #
    # ------------------------------------------------------------------ #

    def _profile_from_posts(self, posts: List[Dict], username: str) -> Dict:
        if not posts:
            return {
                "username": username,
                "full_name": "",
                "biography": "",
                "followers": 0,
                "profile_pic": "",
                "hashtags": [],
                "avg_likes": 0,
                "avg_views": 0,
            }

        first = posts[0]
        all_hashtags: List[str] = []
        total_likes = total_comments = total_views = 0

        for post in posts:
            all_hashtags.extend(_extract_hashtags(post.get("caption", "")))
            total_likes += post.get("likesCount", 0)
            total_comments += post.get("commentsCount", 0)
            total_views += post.get("videoViewCount", 0)

        n = len(posts)
        return {
            "username": username,
            "full_name": (
                first.get("ownerFullName")
                or first.get("owner", {}).get("full_name", "")
                or ""
            ),
            "biography": (
                first.get("ownerBiography")
                or first.get("biography", "")
                or ""
            ),
            "followers": (
                first.get("ownerFollowers")
                or first.get("followersCount", 0)
                or 0
            ),
            "profile_pic": (
                first.get("ownerProfilePicUrl")
                or first.get("profilePicUrl", "")
                or ""
            ),
            "hashtags": list(dict.fromkeys(all_hashtags)),  # deduplicated, order kept
            "avg_likes": total_likes / n if n else 0,
            "avg_comments": total_comments / n if n else 0,
            "avg_views": total_views / n if n else 0,
            "post_count": n,
        }

    def _partial_profile_from_post(self, post: Dict, username: str) -> Dict:
        owner = post.get("owner", {})
        return {
            "username": username,
            "full_name": post.get("ownerFullName") or owner.get("full_name", "") or "",
            "biography": post.get("ownerBiography") or "",
            "followers": (
                post.get("ownerFollowers")
                or owner.get("followersCount", 0)
                or 0
            ),
            "profile_pic": (
                post.get("ownerProfilePicUrl")
                or owner.get("profilePicUrl", "")
                or ""
            ),
            "hashtags": _extract_hashtags(post.get("caption", "")),
            "avg_likes": post.get("likesCount", 0),
            "avg_comments": post.get("commentsCount", 0),
            "avg_views": post.get("videoViewCount", 0),
        }


def _extract_hashtags(text: str) -> List[str]:
    return [t.lower() for t in re.findall(r"#(\w+)", text or "")]
