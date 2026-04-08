"""
app/services/trends_scraper.py
Scrapes viral content from Instagram, TikTok, YouTube via Apify
Runs every 2 hours via Celery beat
"""
import os
import httpx
from datetime import datetime
from app.core.database import get_supabase_admin

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_BASE = "https://api.apify.com/v2"

NICHES = [
    "бизнес", "бьюти", "фитнес", "еда", "психология",
    "мода", "tech", "путешествия", "юмор", "lifestyle"
]

# ─── APIFY ACTORS ────────────────────────────────────────
ACTORS = {
    "instagram": "apify/instagram-scraper",
    "tiktok": "clockworks/tiktok-scraper",
    "youtube": "streamers/youtube-scraper",
}

def run_apify_actor(actor_id: str, input_data: dict, timeout: int = 120) -> list:
    """Run Apify actor and return results."""
    if not APIFY_TOKEN:
        print("[scraper] no APIFY_API_TOKEN set")
        return []

    try:
        # Start actor run
        res = httpx.post(
            f"{APIFY_BASE}/acts/{actor_id}/runs",
            params={"token": APIFY_TOKEN},
            json=input_data,
            timeout=30
        )
        run = res.json()
        run_id = run.get("data", {}).get("id")
        if not run_id:
            print(f"[scraper] failed to start actor {actor_id}: {run}")
            return []

        print(f"[scraper] started actor {actor_id} run={run_id}")

        # Wait for completion
        import time
        for _ in range(timeout // 5):
            time.sleep(5)
            status_res = httpx.get(
                f"{APIFY_BASE}/actor-runs/{run_id}",
                params={"token": APIFY_TOKEN},
                timeout=10
            )
            status = status_res.json().get("data", {}).get("status")
            if status == "SUCCEEDED":
                break
            elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                print(f"[scraper] actor failed with status: {status}")
                return []

        # Get results
        dataset_id = status_res.json().get("data", {}).get("defaultDatasetId")
        if not dataset_id:
            return []

        items_res = httpx.get(
            f"{APIFY_BASE}/datasets/{dataset_id}/items",
            params={"token": APIFY_TOKEN, "limit": 50},
            timeout=30
        )
        return items_res.json()

    except Exception as e:
        print(f"[scraper] error running actor {actor_id}: {e}")
        return []


def scrape_instagram_reels() -> list:
    """Scrape trending Instagram Reels."""
    results = []
    hashtags = ["reels", "viral", "trending", "бизнес", "фитнес", "бьюти"]

    items = run_apify_actor(
        "apify/instagram-scraper",
        {
            "directUrls": ["https://www.instagram.com/explore/tags/reels/", "https://www.instagram.com/explore/tags/viral/"],
            "resultsType": "posts",
            "resultsLimit": 30,
        }
    )

    for item in items:
        try:
            views = item.get("videoPlayCount", 0) or item.get("likesCount", 0) * 50
            likes = item.get("likesCount", 0)
            if views < 10000:
                continue

            results.append({
                "platform": "instagram",
                "external_id": item.get("id", ""),
                "url": item.get("url", ""),
                "thumbnail_url": item.get("displayUrl", ""),
                "author": item.get("ownerUsername", ""),
                "view_count": views,
                "like_count": likes,
                "comment_count": item.get("commentsCount", 0),
                "duration_seconds": item.get("videoDuration", 0),
                "niche": _detect_niche(item.get("caption", "")),
                "caption": (item.get("caption", "") or "")[:500],
                "xfactor": _calc_xfactor(views, likes),
                "scraped_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            print(f"[scraper] instagram item error: {e}")

    print(f"[scraper] instagram: {len(results)} reels")
    return results


def scrape_tiktok_videos() -> list:
    """Scrape trending TikTok videos."""
    results = []

    items = run_apify_actor(
        "clockworks/tiktok-scraper",
        {
            "hashtags": ["viral", "trending", "fyp", "бизнес", "фитнес"],
            "resultsPerPage": 30,
            "maxResults": 50,
        }
    )

    for item in items:
        try:
            views = item.get("playCount", 0)
            likes = item.get("diggCount", 0)
            if views < 10000:
                continue

            results.append({
                "platform": "tiktok",
                "external_id": item.get("id", ""),
                "url": item.get("webVideoUrl", ""),
                "thumbnail_url": (item.get("covers", {}).get("default", "") or 
                                  item.get("video", {}).get("cover", "") or
                                  item.get("imagePost", {}).get("images", [{}])[0].get("imageURL", {}).get("urlList", [""])[0] or ""),
                "author": item.get("authorMeta", {}).get("name", ""),
                "view_count": views,
                "like_count": likes,
                "comment_count": item.get("commentCount", 0),
                "duration_seconds": item.get("videoMeta", {}).get("duration", 0),
                "niche": _detect_niche(item.get("text", "")),
                "caption": (item.get("text", "") or "")[:500],
                "xfactor": _calc_xfactor(views, likes),
                "scraped_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            print(f"[scraper] tiktok item error: {e}")

    print(f"[scraper] tiktok: {len(results)} videos")
    return results


def scrape_youtube_shorts() -> list:
    """Scrape trending YouTube Shorts."""
    results = []

    items = run_apify_actor(
        "streamers/youtube-scraper",
        {
            "searchKeywords": ["youtube shorts viral", "shorts trending"],
            "maxResults": 30,
            "videoDuration": "short",
        }
    )

    for item in items:
        try:
            views = item.get("viewCount", 0)
            likes = item.get("likes", 0)
            if views < 10000:
                continue

            url = f"https://youtube.com/shorts/{item.get('id', '')}"
            results.append({
                "platform": "youtube",
                "external_id": item.get("id", ""),
                "url": url,
                "thumbnail_url": item.get("thumbnailUrl", ""),
                "author": item.get("channelName", ""),
                "view_count": views,
                "like_count": likes,
                "comment_count": item.get("commentCount", 0),
                "duration_seconds": item.get("duration", 0),
                "niche": _detect_niche(item.get("title", "") + " " + item.get("description", "")),
                "caption": (item.get("title", "") or "")[:500],
                "xfactor": _calc_xfactor(views, likes),
                "scraped_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            print(f"[scraper] youtube item error: {e}")

    print(f"[scraper] youtube: {len(results)} shorts")
    return results


def _detect_niche(text: str) -> str:
    text = (text or "").lower()
    niche_map = {
        "бизнес": ["бизнес", "деньги", "заработ", "business", "money", "entrepreneur"],
        "бьюти": ["бьюти", "макияж", "beauty", "makeup", "уход", "косметик"],
        "фитнес": ["фитнес", "спорт", "тренировк", "fitness", "workout", "gym"],
        "еда": ["еда", "рецепт", "готов", "food", "recipe", "cook"],
        "психология": ["психолог", "саморазвит", "motivation", "мотивац"],
        "мода": ["мода", "стиль", "fashion", "style", "outfit"],
        "tech": ["tech", "ai", "технолог", "программ", "айти"],
        "путешествия": ["путешеств", "travel", "поездк", "трип"],
        "юмор": ["юмор", "смешн", "funny", "comedy", "приколы"],
    }
    for niche, keywords in niche_map.items():
        if any(kw in text for kw in keywords):
            return niche
    return "lifestyle"


def _calc_xfactor(views: int, likes: int) -> float:
    """X-factor = views / average views for similar content."""
    if views <= 0:
        return 0.0
    avg_views = 50000
    return round(views / avg_views, 1)


def save_trends_to_db(trends: list):
    """Save scraped trends to Supabase."""
    if not trends:
        return

    db = get_supabase_admin()
    saved = 0

    for trend in trends:
        try:
            # Upsert by external_id
            db.table("trends").upsert(
                trend,
                on_conflict="external_id"
            ).execute()
            saved += 1
        except Exception as e:
            print(f"[scraper] save error: {e}")

    print(f"[scraper] saved {saved}/{len(trends)} trends to DB")


def run_full_scrape():
    """Run full scrape for all platforms. Called by Celery beat every 2h."""
    print(f"[scraper] START full scrape at {datetime.utcnow()}")
    all_trends = []

    # Instagram first
    try:
        ig = scrape_instagram_reels()
        all_trends.extend(ig)
    except Exception as e:
        print(f"[scraper] instagram failed: {e}")

    # TikTok
    try:
        tt = scrape_tiktok_videos()
        all_trends.extend(tt)
    except Exception as e:
        print(f"[scraper] tiktok failed: {e}")

    # YouTube
    try:
        yt = scrape_youtube_shorts()
        all_trends.extend(yt)
    except Exception as e:
        print(f"[scraper] youtube failed: {e}")

    # Save all
    save_trends_to_db(all_trends)
    print(f"[scraper] DONE. Total: {len(all_trends)} trends")
    return len(all_trends)
