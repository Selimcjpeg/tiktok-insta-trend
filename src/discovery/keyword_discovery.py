"""
TikTok Keyword Discovery
Scrapes TikTok Creative Center for trending hashtags,
then converts them to search-ready keywords via an LLM.

Supported LLM providers (auto-detected by API key):
  1. Gemini Flash  — GEMINI_API_KEY   (free tier available, cheapest)
  2. GPT-4o mini   — OPENAI_API_KEY   ($0.15/1M tokens)
  3. Claude Haiku  — ANTHROPIC_API_KEY ($0.80/1M tokens)
  4. No LLM        — raw hashtag names (always works, no cost)
"""

import requests
import json
import os
from typing import List, Dict

# Noise hashtags to filter out — these appear on every video
GENERIC_HASHTAGS = {
    'fyp', 'foryou', 'foryoupage', 'viral', 'trending', 'fy',
    'tiktok', 'parati', 'fypシ', 'blowthisup', 'explore',
    'humor', 'comedy', 'meme', 'funny', 'fun', 'cute', 'cool',
    'entertainment', 'fypシ゚viral', 'goviral', 'tiktokviral',
}

CREATIVE_CENTER_URL = "https://ads.tiktok.com/creative_center/api/v1/hashtag/chart/"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://ads.tiktok.com/creative_center/trending-hashtags/pc/en",
    "Origin": "https://ads.tiktok.com",
}

CONVERSION_PROMPT = """These are trending TikTok hashtags (last 7 days):
{hashtag_lines}

Convert these into 10 natural search keywords for a content creator seeking trending content inspiration.
Rules:
- Convert hashtag slang to plain English: "gymtok" → "gym workout", "cleantok" → "cleaning routine"
- Group related hashtags into one keyword (2-4 words)
- Keep keywords specific and content-focused
- Avoid generic phrases like "trending content" or "viral video"

Return ONLY a JSON array of strings, no other text:
["keyword one", "keyword two", ...]"""


def _detect_provider() -> str:
    """Return which LLM provider to use based on available API keys."""
    if os.getenv('GEMINI_API_KEY'):
        return 'gemini'
    if os.getenv('OPENAI_API_KEY'):
        return 'openai'
    if os.getenv('ANTHROPIC_API_KEY'):
        return 'anthropic'
    return 'none'


class TikTokKeywordDiscovery:
    """
    Discovers trending topics from TikTok Creative Center
    and converts them to search-ready keywords.

    Data source: TikTok Creative Center (free, public, last 7 days)
    LLM: auto-detected from env vars (Gemini > OpenAI > Anthropic > none)
    """

    def __init__(self):
        self.provider = _detect_provider()
        print(f"  LLM provider: {self.provider}")

    def get_trending_hashtags(self, country: str = 'US', limit: int = 35) -> List[Dict]:
        """
        Fetch trending hashtags from TikTok Creative Center.

        Returns:
            List of hashtag dicts with 'hashtag_name', 'view_sum', 'publish_cnt'
        """
        params = {
            "period": 7,
            "country_code": country,
            "page": 1,
            "limit": limit,
        }

        try:
            resp = requests.get(
                CREATIVE_CENTER_URL,
                params=params,
                headers=BROWSER_HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            raise Exception(f"TikTok Creative Center API unreachable: {e}")

        if data.get('code') != 0:
            raise Exception(
                f"Creative Center returned error {data.get('code')}: {data.get('msg', '?')}"
            )

        raw_hashtags = data.get('data', {}).get('list', [])

        # Filter out noise hashtags
        filtered = [
            h for h in raw_hashtags
            if h.get('hashtag_name', '').lower().strip('#') not in GENERIC_HASHTAGS
        ]

        return filtered

    def convert_to_keywords(self, hashtags: List[Dict]) -> List[str]:
        """
        Convert trending hashtags into plain-English search keywords using
        whichever LLM is configured. Falls back to raw hashtag names if none.
        """
        if not hashtags:
            return []

        if self.provider == 'none':
            return [h.get('hashtag_name', '') for h in hashtags[:10]]

        hashtag_lines = '\n'.join(
            f"#{h.get('hashtag_name')} — {h.get('view_sum', 0):,} views this week"
            for h in hashtags[:25]
        )
        prompt = CONVERSION_PROMPT.format(hashtag_lines=hashtag_lines)

        try:
            if self.provider == 'gemini':
                return self._convert_with_gemini(prompt)
            elif self.provider == 'openai':
                return self._convert_with_openai(prompt)
            elif self.provider == 'anthropic':
                return self._convert_with_anthropic(prompt)
        except Exception as e:
            print(f"⚠️ LLM conversion failed ({self.provider}): {e}, using raw hashtags")

        return [h.get('hashtag_name', '') for h in hashtags[:10]]

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    def _convert_with_gemini(self, prompt: str) -> List[str]:
        from google import genai
        client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        text = response.text.strip()
        # Strip markdown code block if present
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        return json.loads(text.strip())[:10]

    def _convert_with_openai(self, prompt: str) -> List[str]:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.choices[0].message.content.strip())[:10]

    def _convert_with_anthropic(self, prompt: str) -> List[str]:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.content[0].text.strip())[:10]

    # ------------------------------------------------------------------

    def discover(self, country: str = 'US') -> List[str]:
        """
        Main method: fetch trending hashtags and convert to search keywords.
        """
        print(f"🔍 Fetching trending hashtags from TikTok Creative Center ({country})...")
        hashtags = self.get_trending_hashtags(country)
        print(f"  Found {len(hashtags)} relevant hashtags after filtering")

        print(f"  🤖 Converting to search keywords via {self.provider}...")
        keywords = self.convert_to_keywords(hashtags)
        print(f"  ✅ Generated {len(keywords)} search keywords")

        return keywords
