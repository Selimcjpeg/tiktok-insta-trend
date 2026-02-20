"""
Trend Tracker - Main Streamlit App
Cross-platform TikTok & Instagram Reels trend discovery
"""

import streamlit as st
from datetime import datetime, timedelta
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Streamlit Cloud: copy secrets to os.environ so all modules can use os.getenv()
# Locally, .env is used. On Streamlit Cloud, secrets are set in the dashboard.
try:
    for _k, _v in st.secrets.items():
        os.environ.setdefault(_k, str(_v))
except Exception:
    pass

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scraper.tiktok_scraper import TikTokScraper
from database.db_manager import DatabaseManager
from discovery.keyword_discovery import TikTokKeywordDiscovery
from analytics.metrics import (
    filter_by_date_range,
    filter_by_quality,
    sort_by_metric,
)
from analytics.creator_analytics import (
    aggregate_creators,
    classify_creator_tier,
    find_micro_influencers
)


# Page configuration
st.set_page_config(
    page_title="Trend Tracker",
    page_icon="🔥",
    layout="wide"
)

# Initialize services
@st.cache_resource
def get_db():
    return DatabaseManager()

@st.cache_resource
def get_tiktok_scraper():
    return TikTokScraper()


def init_session_state():
    """Initialize session state variables"""
    if 'tiktok_results' not in st.session_state:
        st.session_state.tiktok_results = []
    if 'search_keyword' not in st.session_state:
        st.session_state.search_keyword = ""
    if 'show_creators' not in st.session_state:
        st.session_state.show_creators = False
    if 'deep_dive_username' not in st.session_state:
        st.session_state.deep_dive_username = None
    if 'deep_dive_results' not in st.session_state:
        st.session_state.deep_dive_results = []
    if 'trending_keywords' not in st.session_state:
        st.session_state.trending_keywords = []
    if 'trending_keywords_country' not in st.session_state:
        st.session_state.trending_keywords_country = 'US'
    if 'transcripts' not in st.session_state:
        st.session_state.transcripts = {}  # {video_id: transcript_text}
    if 'scripts' not in st.session_state:
        st.session_state.scripts = {}  # {video_id: repurposed content dict}
    if 'ig_similar_results' not in st.session_state:
        st.session_state.ig_similar_results = None


def display_keyword_discovery():
    """
    Expander section: fetch trending keywords from TikTok Creative Center
    and let user launch a search with one click.
    """
    with st.expander("🔥 Discover Trending Keywords", expanded=False):
        col_btn, col_country, col_info = st.columns([2, 1, 3])

        with col_country:
            country = st.selectbox(
                "Country",
                ["US", "GB", "TR", "DE", "FR", "BR", "AU", "CA"],
                index=0,
                key="discovery_country",
                label_visibility="collapsed",
            )

        with col_btn:
            fetch_clicked = st.button(
                "🔍 Fetch Trending Topics",
                type="secondary",
                use_container_width=True,
            )

        with col_info:
            st.caption(
                "Pulls trending hashtags from TikTok Creative Center (last 7 days) "
                "and converts them to search keywords via Claude Haiku."
            )

        if fetch_clicked:
            with st.spinner("Fetching trending topics from TikTok Creative Center..."):
                try:
                    discovery = TikTokKeywordDiscovery()
                    keywords = discovery.discover(country=country)
                    st.session_state.trending_keywords = keywords
                    st.session_state.trending_keywords_country = country
                except Exception as e:
                    st.error(f"❌ Could not fetch trending topics: {e}")
                    st.info(
                        "TikTok Creative Center may be temporarily unavailable. "
                        "Try again in a few minutes, or enter a keyword manually."
                    )

        keywords = st.session_state.trending_keywords
        if keywords:
            st.markdown(
                f"**Top trending topics** · {st.session_state.trending_keywords_country} · last 7 days"
            )

            # 2-column grid of keyword + Search button
            col_pairs = [keywords[i:i+2] for i in range(0, len(keywords), 2)]
            for pair in col_pairs:
                cols = st.columns(2)
                for i, kw in enumerate(pair):
                    with cols[i]:
                        kw_col, btn_col = st.columns([3, 1])
                        with kw_col:
                            st.markdown(f"**{kw}**")
                        with btn_col:
                            if st.button(
                                "Search",
                                key=f"disc_search_{kw}",
                                use_container_width=True,
                            ):
                                _run_discovery_search(kw)


def _run_discovery_search(keyword: str):
    """Run a search triggered from the discovery section (default params)."""
    with st.spinner(f"🔍 Searching for '{keyword}'..."):
        try:
            tiktok_scraper = get_tiktok_scraper()
            db = get_db()
            results = tiktok_scraper.search_by_keyword(
                keyword, max_results=100, days_ago=10
            )
            for video in results:
                db.insert_tiktok_post(video)
            results = filter_by_date_range(results, 10)
            results = sort_by_metric(results, 'engagement_rate')
            st.session_state.tiktok_results = results
            st.session_state.search_keyword = keyword
            st.session_state.show_creators = False
            st.rerun()
        except Exception as e:
            st.error(f"❌ Search failed: {e}")


def display_trend_search():
    # --- Keyword Discovery Section ---
    display_keyword_discovery()

    # Main search input
    keyword = st.text_input(
        "🔍 Search for trending content",
        placeholder="e.g. dance tutorial, cooking hack, workout routine",
        key="keyword_input"
    )

    # Filters in columns
    col_filter1, col_filter2, col_filter3 = st.columns(3)

    with col_filter1:
        date_range = st.selectbox(
            "📅 Content Age",
            ["Last 7 days", "Last 10 days", "Last 30 days", "All time"],
            index=1
        )

    with col_filter2:
        sort_by = st.selectbox(
            "🎯 Optimize for",
            ["Engagement Rate", "Views", "Comments", "Shares", "Trend Score"],
            help="Choose what metric to prioritize in results"
        )

    with col_filter3:
        platform = st.radio(
            "Platform",
            ["Both", "TikTok", "Instagram"],
            horizontal=True
        )

    # Quality filters (second row)
    col_q1, col_q2 = st.columns(2)

    _views_options = {"10K+": 10_000, "25K+": 25_000, "50K+": 50_000, "100K+": 100_000}
    _inter_options = {"500+": 500, "1K+": 1_000, "2K+": 2_000, "5K+": 5_000}

    with col_q1:
        min_views_label = st.selectbox(
            "👁️ Min Views",
            list(_views_options.keys()),
            index=0,
            help="Minimum view count — removes zero-reach content"
        )

    with col_q2:
        min_inter_label = st.selectbox(
            "💬 Min Interactions",
            list(_inter_options.keys()),
            index=0,
            help="Minimum total likes+comments+shares — removes high-rate-but-no-reach content"
        )

    min_views = _views_options[min_views_label]
    min_interactions = _inter_options[min_inter_label]

    # Search button
    search_clicked = st.button("Search", type="primary", use_container_width=True)

    if search_clicked:
        if not keyword:
            st.warning("⚠️ Please enter a search keyword")
            return

        days_map = {
            "Last 7 days": 7,
            "Last 10 days": 10,
            "Last 30 days": 30,
            "All time": 365
        }
        days_ago = days_map.get(date_range, 10)

        with st.spinner(f"🔍 Searching for '{keyword}'... (This may take 30-60 seconds)"):
            tiktok_scraper = get_tiktok_scraper()
            db = get_db()

            tiktok_results = []

            if platform in ["Both", "TikTok"]:
                try:
                    tiktok_results = tiktok_scraper.search_by_keyword(
                        keyword,
                        max_results=100,
                        days_ago=days_ago
                    )

                    for video in tiktok_results:
                        db.insert_tiktok_post(video)

                    tiktok_results = filter_by_date_range(tiktok_results, days_ago)
                    tiktok_results = sort_by_metric(tiktok_results, sort_by.lower().replace(' ', '_'))

                except Exception as e:
                    st.error(f"❌ TikTok search failed: {e}")

        # Store results in session state, reset creator view on new search
        st.session_state.tiktok_results = tiktok_results
        st.session_state.search_keyword = keyword
        st.session_state.show_creators = False

    # --- Display results from session state ---
    raw_results = st.session_state.tiktok_results
    current_keyword = st.session_state.search_keyword

    # Apply quality filter reactively (doesn't require re-search)
    results = filter_by_quality(raw_results, min_views=min_views, min_interactions=min_interactions)

    if results:
        st.divider()

        # Show filter impact if any videos were removed
        removed = len(raw_results) - len(results)
        if removed > 0:
            st.caption(f"Showing {len(results)} of {len(raw_results)} videos · {removed} filtered out (below {min_views_label} views or {min_inter_label} interactions)")

        # Video results
        st.subheader(f"🎵 TikTok Videos ({len(results)})")
        cols = st.columns(2)
        for idx, video in enumerate(results[:10]):
            with cols[idx % 2]:
                display_video_card(video, "tiktok", sort_by.lower().replace(' ', '_'))

        st.divider()

        # Creator analysis — opt-in button
        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            analyze_clicked = st.button(
                "👥 Analyze Top Creators",
                type="secondary",
                use_container_width=True,
                help="Aggregates creator stats from search results — no extra API call"
            )
        with col_info:
            st.caption("Analyzes creators from above results. No additional API usage.")

        if analyze_clicked:
            st.session_state.show_creators = True

        if st.session_state.show_creators:
            display_top_creators(results, current_keyword)

    elif not search_clicked and not results:
        # Welcome message (only when no results yet)
        st.info("👆 Enter a keyword and click Search to find trending content")

        st.markdown("### 💡 Try these examples:")
        st.markdown("""
        - 🕺 **dance tutorial**
        - 🍳 **cooking hack**
        - 💪 **workout routine**
        - 🎨 **art tutorial**
        - 📱 **tech review**
        """)

    elif not results and raw_results:
        st.warning(
            f"All {len(raw_results)} results were filtered out by quality thresholds. "
            f"Try lowering the Min Views ({min_views_label}) or Min Interactions ({min_inter_label}) filters."
        )
    elif search_clicked and not raw_results:
        st.info("No results found for this keyword and date range.")

    # --- Deep Dive Section ---
    if st.session_state.deep_dive_username:
        username = st.session_state.deep_dive_username
        st.divider()

        # Fetch if not yet loaded
        if not st.session_state.deep_dive_results:
            with st.spinner(f"🔍 Fetching last 50 videos from @{username}... (~$0.10-0.20 Apify cost)"):
                try:
                    tiktok_scraper = get_tiktok_scraper()
                    deep_dive_videos = tiktok_scraper.search_by_username(username, max_results=50)
                    st.session_state.deep_dive_results = deep_dive_videos
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Deep Dive failed: {e}")
                    st.session_state.deep_dive_username = None
        else:
            display_creator_deep_dive(username, st.session_state.deep_dive_results)


# ─────────────────────────────────────────────────────────────────────────── #
#  Instagram: Benzer Hesap Bul                                                #
# ─────────────────────────────────────────────────────────────────────────── #

def display_instagram_similar():
    st.subheader("🤝 Instagram Benzer Hesap Bul")
    st.markdown(
        "Bir Instagram hesabı gir — aynı nişte içerik üreten benzer hesapları bul.\n\n"
        "_Instagram'ın kendi 'benzer hesap' algoritması + hashtag analizi + çoklu skor kullanılır._"
    )

    col_input, col_btn = st.columns([3, 1])
    with col_input:
        seed_input = st.text_input(
            "Instagram kullanıcı adı",
            placeholder="ornekkullanici  (@ olmadan)",
            key="ig_seed_input",
            label_visibility="collapsed",
        )
    with col_btn:
        find_clicked = st.button(
            "Benzer Hesapları Bul",
            type="primary",
            use_container_width=True,
            key="ig_find_btn",
        )

    if find_clicked:
        username = seed_input.strip().lstrip("@")
        if not username:
            st.warning("⚠️ Lütfen bir kullanıcı adı gir")
            return

        with st.spinner(f"🔍 @{username} analiz ediliyor... (1-3 dakika sürebilir)"):
            try:
                from discovery.instagram_similar import find_similar_accounts
                result = find_similar_accounts(username, max_results=20)
                st.session_state.ig_similar_results = result
            except Exception as e:
                st.error(f"❌ Hata: {e}")
                return

    # ── Display results ─────────────────────────────────────────────── #
    result = st.session_state.get("ig_similar_results")
    if not result:
        st.info("👆 Bir kullanıcı adı gir ve butona bas")
        return

    seed = result.get("seed", {})
    similar = result.get("similar", [])

    # Seed profile banner
    st.divider()
    sc1, sc2 = st.columns([1, 4])
    with sc1:
        if seed.get("profile_pic"):
            st.image(seed["profile_pic"], width=80)
    with sc2:
        st.markdown(f"**@{seed.get('username', '')}** {seed.get('full_name', '')}")
        if seed.get("biography"):
            st.caption(seed["biography"][:120])
        sm1, sm2, sm3 = st.columns(3)
        with sm1:
            st.metric("Takipçi", _format_number(seed.get("followers", 0)))
        with sm2:
            st.metric("Ort. Like", _format_number(int(seed.get("avg_likes", 0))))
        with sm3:
            st.metric("Hashtag", len(seed.get("hashtags", [])))

    st.divider()
    st.markdown(f"### Benzer {len(similar)} Hesap Bulundu")

    if not similar:
        st.warning("Benzer hesap bulunamadı. Hashtag kullanmayan özel bir hesap olabilir.")
        return

    cols = st.columns(2)
    for idx, acc in enumerate(similar):
        with cols[idx % 2]:
            with st.container(border=True):
                r1, r2 = st.columns([1, 3])
                with r1:
                    if acc.get("profile_pic"):
                        st.image(acc["profile_pic"], width=60)
                    else:
                        st.markdown("👤")
                with r2:
                    badge = " ⭐" if acc.get("is_native_related") else ""
                    st.markdown(f"**@{acc.get('username', '')}**{badge}")
                    if acc.get("full_name"):
                        st.caption(acc["full_name"])

                if acc.get("biography"):
                    st.caption(acc["biography"][:100])

                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Takipçi", _format_number(acc.get("followers", 0)))
                with m2:
                    st.metric("Benzerlik", f"{acc.get('similarity_score', 0):.0f}%")
                with m3:
                    st.metric("Ort. Like", _format_number(int(acc.get("avg_likes", 0))))

                for reason in acc.get("similarity_reasons", []):
                    st.caption(f"• {reason}")

                st.link_button(
                    "Profili Gör",
                    acc.get("instagram_url", f"https://www.instagram.com/{acc.get('username', '')}/"),
                    use_container_width=True,
                )


def main():
    init_session_state()

    st.title("🔥 Trend Tracker")
    st.markdown("*TikTok trend arama & Instagram benzer hesap keşfi*")

    tab_trend, tab_instagram = st.tabs(["🔍 TikTok Trend Arama", "🤝 Instagram Benzer Hesap"])

    with tab_trend:
        display_trend_search()

    with tab_instagram:
        display_instagram_similar()


def display_top_creators(videos: list, keyword: str):
    """Display aggregated creator analysis from search results"""
    creators = aggregate_creators(videos)

    if not creators:
        st.info("Not enough data to analyze creators.")
        return

    st.subheader(f"👥 Top Creators for \"{keyword}\"")

    # Summary metrics
    total_creators = len(creators)
    micro_influencers = find_micro_influencers(creators)

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Unique Creators", total_creators)
    with m2:
        st.metric("Total Videos Analyzed", len(videos))
    with m3:
        st.metric("Micro-Influencers Found", len(micro_influencers),
                  help="High engagement (<500K avg views) — easiest to replicate")

    st.divider()

    # Creator cards
    for i, creator in enumerate(creators[:15]):
        tier = classify_creator_tier(
            creator['avg_views'],
            creator['video_count'],
            creator['avg_engagement']
        )

        followers = creator['videos'][0].get('author_followers', 0) if creator['videos'] else 0
        verified = creator['videos'][0].get('author_verified', False) if creator['videos'] else False

        with st.container():
            col_rank, col_info, col_metrics, col_action = st.columns([0.5, 2.5, 3, 1.5])

            with col_rank:
                st.markdown(f"### #{i+1}")

            with col_info:
                username = creator['username']
                verified_badge = " ✓" if verified else ""
                st.markdown(f"**@{username}{verified_badge}**")
                st.caption(tier)
                if followers > 0:
                    st.caption(f"👥 {_format_number(followers)} followers")
                st.caption(f"📹 {creator['video_count']} video in this search")

            with col_metrics:
                mc1, mc2, mc3 = st.columns(3)
                with mc1:
                    st.metric("Avg Views", _format_number(int(creator['avg_views'])))
                with mc2:
                    st.metric("Avg Engagement", f"{creator['avg_engagement']:.1f}%")
                with mc3:
                    st.metric("Best Video", _format_number(creator['best_video']['views']))

            with col_action:
                tiktok_url = f"https://www.tiktok.com/@{creator['username']}"
                st.link_button("TikTok Profile", tiktok_url, use_container_width=True)
                if creator['best_video']['url']:
                    st.link_button("Best Video", creator['best_video']['url'], use_container_width=True)
                if st.button(
                    "🔍 Deep Dive",
                    key=f"deepdive_{creator['username']}",
                    use_container_width=True,
                    help="Fetch last 50 videos from this creator (~$0.10-0.20 Apify cost)"
                ):
                    st.session_state.deep_dive_username = creator['username']
                    st.session_state.deep_dive_results = []
                    st.rerun()

        # Best video caption preview
        best_caption = creator['best_video']['caption']
        if best_caption:
            st.caption(f"🏆 Best: \"{best_caption}\"")

        st.markdown("---")

    # Micro-influencer highlight
    if micro_influencers:
        st.subheader("🌱 Micro-Influencers Worth Watching")
        st.caption("High engagement rate but not yet massive — content strategies easiest to analyze and replicate")

        cols = st.columns(min(len(micro_influencers), 3))
        for i, creator in enumerate(micro_influencers[:3]):
            with cols[i]:
                st.markdown(f"**@{creator['username']}**")
                st.metric("Engagement", f"{creator['avg_engagement']:.1f}%")
                st.metric("Avg Views", _format_number(int(creator['avg_views'])))
                tiktok_url = f"https://www.tiktok.com/@{creator['username']}"
                st.link_button("View", tiktok_url, use_container_width=True)


def display_video_card(video: dict, platform: str, sort_by: str):
    """Display a video card"""
    video_id = video.get('video_id', '')

    with st.container():
        st.markdown(f"**@{video['author_username']}**")

        if video.get('cover_url'):
            st.image(video['cover_url'], use_column_width=True)

        caption = video.get('caption', '')[:100]
        if len(video.get('caption', '')) > 100:
            caption += "..."
        st.caption(caption)

        metric_cols = st.columns(3)

        with metric_cols[0]:
            if sort_by == "views":
                st.metric("👁️ Views", f"{video.get('views', 0):,}")
            elif sort_by == "comments":
                st.metric("💬 Comments", f"{video.get('comments', 0):,}")
            elif sort_by == "shares":
                st.metric("🔄 Shares", f"{video.get('shares', 0):,}")
            else:
                st.metric("📊 Engagement", f"{video.get('engagement_rate', 0):.1f}%")

        with metric_cols[1]:
            st.metric("❤️ Likes", f"{video.get('likes', 0):,}")

        with metric_cols[2]:
            created_at = datetime.fromisoformat(video['created_at'].replace('Z', '+00:00'))
            days_old = (datetime.now() - created_at.replace(tzinfo=None)).days
            st.metric("📅 Age", f"{days_old}d ago")

        if video.get('audio_title'):
            st.caption(f"🎵 {video['audio_title']}")

        # Action buttons
        if video.get('video_url'):
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                st.link_button("▶ TikTok'ta İzle", video['video_url'], use_container_width=True)
            with btn_col2:
                transcript_key = f"transcript_{video_id}"
                if transcript_key in st.session_state.transcripts:
                    if st.button("📝 Transkript ✓", key=f"tbtn_{video_id}", use_container_width=True):
                        # Toggle: delete to hide
                        del st.session_state.transcripts[transcript_key]
                        st.rerun()
                else:
                    if st.button("📝 Transkript Al", key=f"tbtn_{video_id}", use_container_width=True):
                        with st.spinner("Video indiriliyor ve transkript çıkarılıyor..."):
                            try:
                                from transcript.extractor import extract_transcript
                                text = extract_transcript(
                                    video_url=video['video_url'],
                                    download_url=video.get('download_url', ''),
                                )
                                st.session_state.transcripts[transcript_key] = text
                            except Exception as e:
                                st.session_state.transcripts[transcript_key] = f"❌ Hata: {e}"
                        st.rerun()

        # Show transcript if available
        transcript_key = f"transcript_{video_id}"
        script_key = f"script_{video_id}"
        if transcript_key in st.session_state.transcripts:
            transcript_text = st.session_state.transcripts[transcript_key]
            with st.expander("📄 Transkript", expanded=True):
                st.text_area(
                    label="",
                    value=transcript_text,
                    height=150,
                    key=f"ta_{video_id}",
                    label_visibility="collapsed"
                )
                st.caption("Metni seçip kopyalayabilirsin.")

            # Script generation button (only if transcript exists and not an error)
            if not transcript_text.startswith("❌"):
                if script_key not in st.session_state.scripts:
                    if st.button("✍️ Türkçe Script Oluştur", key=f"sbtn_{video_id}", use_container_width=True, type="primary"):
                        with st.spinner("GPT-4o-mini içeriği adapte ediyor..."):
                            try:
                                from content.repurpose import repurpose_for_turkish
                                result = repurpose_for_turkish(transcript_text)
                                st.session_state.scripts[script_key] = result
                            except Exception as e:
                                st.session_state.scripts[script_key] = {"error": str(e)}
                        st.rerun()
                else:
                    if st.button("✍️ Script ✓ (Yenile)", key=f"sbtn_{video_id}", use_container_width=True):
                        del st.session_state.scripts[script_key]
                        st.rerun()

        # Show generated script if available
        if script_key in st.session_state.scripts:
            result = st.session_state.scripts[script_key]
            if "error" in result:
                st.error(f"❌ Script hatası: {result['error']}")
            else:
                with st.expander("✍️ Türkçe Script & İçerik", expanded=True):
                    # Content type + core message
                    st.caption(f"📌 **{result.get('content_type', '').upper()}** — {result.get('core_message', '')}")
                    st.divider()

                    tab_script, tab_desc, tab_hook = st.tabs(["📝 Script", "📢 Descriptions", "🎯 Hook"])

                    with tab_script:
                        st.text_area(
                            label="",
                            value=result.get('script', ''),
                            height=250,
                            key=f"script_ta_{video_id}",
                            label_visibility="collapsed"
                        )

                    with tab_desc:
                        for i, desc in enumerate(result.get('descriptions', []), 1):
                            tone_label = {"samimi": "Samimi", "merak_uyandiran": "Merak Uyandıran", "direkt_guclu": "Direkt/Güçlü"}.get(desc.get('tone', ''), desc.get('tone', ''))
                            st.markdown(f"**{i}. {tone_label}**")
                            st.text_area(
                                label="",
                                value=desc.get('text', ''),
                                height=70,
                                key=f"desc_{i}_{video_id}",
                                label_visibility="collapsed"
                            )
                            hashtags = " ".join(f"#{h.lstrip('#')}" for h in desc.get('hashtags', []))
                            if hashtags:
                                st.caption(hashtags)

                    with tab_hook:
                        hook = result.get('hook', {})
                        st.markdown(f"**Hook:** {hook.get('text', '')}")
                        st.caption(f"Format: `{hook.get('format', '')}` — {hook.get('reasoning', '')}")

        st.markdown("---")


def display_creator_deep_dive(username: str, videos: list):
    """Display deep dive analysis for a creator's last 50 videos"""
    col_header, col_close = st.columns([5, 1])
    with col_header:
        st.subheader(f"🔍 Deep Dive: @{username}")
    with col_close:
        if st.button("✕ Close", key="close_deep_dive"):
            st.session_state.deep_dive_username = None
            st.session_state.deep_dive_results = []
            st.rerun()

    if not videos:
        st.info("No videos found for this creator.")
        return

    # --- Summary metrics ---
    total_views = sum(v.get('views', 0) for v in videos)
    avg_views = total_views / len(videos)
    avg_engagement = sum(v.get('engagement_rate', 0) for v in videos) / len(videos)
    avg_likes = sum(v.get('likes', 0) for v in videos) / len(videos)
    top_video = max(videos, key=lambda v: v.get('views', 0))

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Videos Analyzed", len(videos))
    with m2:
        st.metric("Avg Views", _format_number(int(avg_views)))
    with m3:
        st.metric("Avg Engagement", f"{avg_engagement:.1f}%")
    with m4:
        st.metric("Avg Likes", _format_number(int(avg_likes)))

    st.divider()

    # --- Audio pattern analysis ---
    audio_counts = {}
    for v in videos:
        audio = v.get('audio_title', 'Unknown')
        audio_counts[audio] = audio_counts.get(audio, 0) + 1

    top_audios = sorted(audio_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    unique_audio_count = len(audio_counts)

    col_audio, col_top = st.columns([1, 2])
    with col_audio:
        st.markdown("**🎵 Audio Strategy**")
        st.caption(f"{unique_audio_count} unique tracks in {len(videos)} videos")
        reuse_rate = 1 - (unique_audio_count / len(videos))
        if reuse_rate > 0.4:
            st.caption("🔁 Frequently reuses same audio")
        else:
            st.caption("🎼 Mostly original/varied audio")
        for audio_title, count in top_audios:
            st.caption(f"• {audio_title[:40]} ({count}x)")

    with col_top:
        st.markdown("**🏆 Best Performing Video**")
        st.caption(top_video.get('caption', '')[:100])
        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            st.metric("Views", _format_number(top_video.get('views', 0)))
        with tc2:
            st.metric("Likes", _format_number(top_video.get('likes', 0)))
        with tc3:
            st.metric("Engagement", f"{top_video.get('engagement_rate', 0):.1f}%")
        if top_video.get('video_url'):
            st.link_button("Watch Best Video", top_video['video_url'])

    st.divider()

    # --- Recent videos grid ---
    st.markdown(f"**📹 Recent Videos ({len(videos)})**")
    cols = st.columns(3)
    for idx, video in enumerate(videos[:15]):
        with cols[idx % 3]:
            if video.get('cover_url'):
                st.image(video['cover_url'], use_column_width=True)
            caption = video.get('caption', '')[:60]
            st.caption(caption)
            vc1, vc2 = st.columns(2)
            with vc1:
                st.metric("Views", _format_number(video.get('views', 0)))
            with vc2:
                st.metric("Eng%", f"{video.get('engagement_rate', 0):.1f}%")
            if video.get('video_url'):
                st.link_button("Watch", video['video_url'], use_container_width=True)
            st.markdown("---")


def _format_number(n: int) -> str:
    """Format large numbers: 1500000 → 1.5M"""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


if __name__ == "__main__":
    main()
