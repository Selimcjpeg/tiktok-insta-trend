"""
Creator Analytics - Aggregate and analyze creators from video results
"""

from typing import List, Dict
from collections import defaultdict
from statistics import mean


def aggregate_creators(videos: List[Dict]) -> List[Dict]:
    """Aggregate videos by creator and calculate creator-level metrics."""
    if not videos:
        return []

    creators = defaultdict(lambda: {
        'username': '',
        'videos': [],
        'total_views': 0,
        'total_likes': 0,
        'total_comments': 0,
        'total_shares': 0,
        'total_engagement': 0,
        'video_count': 0
    })

    for video in videos:
        username = video.get('author_username', 'unknown')
        creators[username]['username'] = username
        creators[username]['videos'].append(video)
        creators[username]['total_views'] += video.get('views', 0)
        creators[username]['total_likes'] += video.get('likes', 0)
        creators[username]['total_comments'] += video.get('comments', 0)
        creators[username]['total_shares'] += video.get('shares', 0)
        creators[username]['total_engagement'] += video.get('engagement_rate', 0)
        creators[username]['video_count'] += 1

    creator_stats = []
    for username, data in creators.items():
        if data['video_count'] == 0:
            continue

        avg_views = data['total_views'] / data['video_count']
        avg_engagement = data['total_engagement'] / data['video_count']
        best_video = max(data['videos'], key=lambda v: v.get('views', 0))

        creator_stats.append({
            'username': username,
            'video_count': data['video_count'],
            'avg_views': avg_views,
            'avg_engagement': avg_engagement,
            'avg_likes': data['total_likes'] / data['video_count'],
            'avg_comments': data['total_comments'] / data['video_count'],
            'avg_shares': data['total_shares'] / data['video_count'],
            'total_views': data['total_views'],
            'best_video': {
                'caption': best_video.get('caption', '')[:50] + '...',
                'views': best_video.get('views', 0),
                'engagement_rate': best_video.get('engagement_rate', 0),
                'url': best_video.get('video_url', '')
            },
            'videos': data['videos']
        })

    creator_stats.sort(key=lambda x: x['avg_engagement'], reverse=True)
    return creator_stats


def classify_creator_tier(avg_views: int, video_count: int, avg_engagement: float) -> str:
    """Classify creator into tier based on performance."""
    if avg_views > 1_000_000 and avg_engagement > 5.0:
        return "🔥 Top Performer"
    if avg_views > 500_000 or avg_engagement > 8.0:
        return "⭐ Strong"
    if video_count >= 3 and avg_engagement > 6.0:
        return "📈 Rising"
    if avg_engagement > 7.0:
        return "🌱 Emerging"
    return "📊 Standard"


def find_micro_influencers(creator_stats: List[Dict], min_engagement: float = 7.0, max_avg_views: int = 500_000) -> List[Dict]:
    """Find micro-influencers: high engagement but not massive views."""
    return [
        c for c in creator_stats
        if c['avg_engagement'] >= min_engagement
        and c['avg_views'] <= max_avg_views
        and c['video_count'] >= 2
    ]
