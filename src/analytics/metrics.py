"""
Analytics and metrics calculation module
"""

from datetime import datetime, timedelta
from typing import List, Dict


def calculate_engagement_rate(likes: int, comments: int, shares: int, views: int) -> float:
    if views == 0:
        return 0.0
    return ((likes + comments + shares) / views) * 100


def filter_by_quality(posts: List[Dict], min_views: int = 10_000, min_interactions: int = 500) -> List[Dict]:
    """
    Filter posts by minimum reach and interaction thresholds.
    Removes high-engagement-rate-but-zero-reach content.
    min_interactions = likes + comments + shares
    """
    return [
        p for p in posts
        if p.get('views', 0) >= min_views
        and (p.get('likes', 0) + p.get('comments', 0) + p.get('shares', 0)) >= min_interactions
    ]


def filter_by_date_range(posts: List[Dict], days_ago: int) -> List[Dict]:
    """Filter posts created within the last N days."""
    cutoff = datetime.now() - timedelta(days=days_ago)
    filtered = []
    for post in posts:
        created_at_str = post.get('created_at')
        if not created_at_str:
            continue
        try:
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            if created_at >= cutoff:
                filtered.append(post)
        except Exception:
            continue
    return filtered


def sort_by_metric(posts: List[Dict], sort_by: str) -> List[Dict]:
    """Sort posts by the specified metric (descending)."""
    key_map = {
        'views': lambda p: p.get('views', 0),
        'comments': lambda p: p.get('comments', 0),
        'shares': lambda p: p.get('shares', 0),
        'engagement_rate': lambda p: p.get('engagement_rate', 0),
        'trend_score': lambda p: _composite_score(p),
    }
    key_fn = key_map.get(sort_by, lambda p: p.get('engagement_rate', 0))
    return sorted(posts, key=key_fn, reverse=True)


def _composite_score(post: Dict) -> float:
    """Composite trend score: engagement (40%) + views (60% normalized)."""
    engagement = min(post.get('engagement_rate', 0) * 10, 100)
    views_score = min(post.get('views', 0) / 100_000, 100)
    return engagement * 0.4 + views_score * 0.6
