"""
Instagram similar account discovery pipeline:
  seed account → native related + hashtag expansion → multi-signal scoring → ranked list
"""

import math
import re
from typing import List, Dict, Tuple

from scraper.apify_instagram_scraper import ApifyInstagramScraper


def find_similar_accounts(seed_username: str, max_results: int = 20) -> Dict:
    """
    Full pipeline: seed → related accounts → scored list.

    Returns:
        {
            "seed": { profile dict },
            "similar": [ { profile + similarity_score + similarity_reasons }, ... ]
        }
    """
    scraper = ApifyInstagramScraper()

    # ── Step 1: Seed profile ─────────────────────────────────────────── #
    seed = scraper.get_seed_profile(seed_username)
    print(f"  Seed: @{seed_username} — {seed.get('followers', 0):,} followers, "
          f"{len(seed.get('hashtags', []))} hashtags found")

    candidates: Dict[str, Dict] = {}
    native_usernames: set = set()

    # ── Step 2: Instagram's own related accounts ─────────────────────── #
    for acc in scraper.get_related_accounts(seed_username):
        uname = acc.get("username", "")
        if uname and uname != seed_username:
            candidates[uname] = acc
            native_usernames.add(uname)

    # ── Step 3: Hashtag expansion ────────────────────────────────────── #
    top_hashtags = seed.get("hashtags", [])[:4]
    if top_hashtags:
        print(f"🏷️ Expanding via hashtags: {top_hashtags}")
        for profile in scraper.get_hashtag_candidates(top_hashtags, limit_per_tag=25):
            uname = profile.get("username", "")
            if uname and uname != seed_username and uname not in candidates:
                candidates[uname] = profile
    else:
        print("⚠️ No hashtags found on seed profile — skipping hashtag expansion")

    print(f"📊 Scoring {len(candidates)} candidate accounts...")

    # ── Step 4: Score and rank ───────────────────────────────────────── #
    scored = []
    for uname, profile in candidates.items():
        score, reasons = _score(seed, profile, uname in native_usernames)
        profile["similarity_score"] = score
        profile["similarity_reasons"] = reasons
        profile["is_native_related"] = uname in native_usernames
        profile["instagram_url"] = f"https://www.instagram.com/{uname}/"
        scored.append(profile)

    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    print(f"✅ Done. Top match: @{scored[0]['username']} ({scored[0]['similarity_score']}%) "
          if scored else "✅ No candidates found.")

    return {
        "seed": seed,
        "similar": scored[:max_results],
    }


# ── Scoring helpers ────────────────────────────────────────────────────── #

def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _follower_proximity(seed_f: int, cand_f: int) -> float:
    """
    1.0 = identical size, decays on log scale.
    3 orders of magnitude apart → 0.0.
    """
    if seed_f <= 0 or cand_f <= 0:
        return 0.3  # neutral score when unknown
    diff = abs(math.log10(max(seed_f, 1)) - math.log10(max(cand_f, 1)))
    return max(0.0, 1.0 - diff / 3.0)


def _bio_keyword_overlap(bio_a: str, bio_b: str) -> float:
    _stop = {
        "i", "a", "the", "and", "or", "in", "on", "at", "to", "for",
        "of", "with", "my", "your", "our", "is", "be", "are", "by"
    }

    def keywords(text: str) -> set:
        return {
            w.lower()
            for w in re.findall(r"\w+", text or "")
            if len(w) > 2 and w.lower() not in _stop
        }

    return _jaccard(keywords(bio_a), keywords(bio_b))


def _score(seed: Dict, candidate: Dict, is_native: bool) -> Tuple[float, List[str]]:
    """Returns (score_0_to_100, human-readable reasons list)."""
    reasons: List[str] = []

    seed_tags = set(seed.get("hashtags", [])[:30])
    cand_tags = set(candidate.get("hashtags", [])[:30])
    hashtag_score = _jaccard(seed_tags, cand_tags)

    follower_score = _follower_proximity(
        seed.get("followers", 0),
        candidate.get("followers", 0),
    )

    bio_score = _bio_keyword_overlap(
        seed.get("biography", ""),
        candidate.get("biography", ""),
    )

    # Weighted combination
    raw = hashtag_score * 0.55 + follower_score * 0.25 + bio_score * 0.20

    # Native boost: Instagram already thinks they're similar
    if is_native:
        raw = min(1.0, raw + 0.15)
        reasons.append("Instagram'ın kendi önerisi")

    if hashtag_score > 0.15:
        shared = list(seed_tags & cand_tags)[:3]
        reasons.append(f"Ortak hashtag: #{', #'.join(shared)}")

    if follower_score > 0.7:
        reasons.append("Benzer kitle büyüklüğü")

    if bio_score > 0.15:
        reasons.append("Bio içeriği örtüşüyor")

    if not reasons:
        reasons.append("Aynı niş hashtag'lerinde aktif")

    return round(raw * 100, 1), reasons
