"""
app/api/trends.py - Returns real trends from DB
"""
from fastapi import APIRouter, Query
from app.core.database import get_supabase_admin

router = APIRouter(prefix="/api/trends", tags=["trends"])

@router.get("/feed")
async def get_trends(
    niche: str = Query("all"),
    platform: str = Query("all"),
    sort: str = Query("xfactor"),
    limit: int = Query(20)
):
    try:
        db = get_supabase_admin()
        query = db.table("trends").select("*")

        if niche != "all":
            query = query.eq("niche", niche)
        if platform != "all":
            query = query.eq("platform", platform)

        if sort == "xfactor":
            query = query.order("xfactor", desc=True)
        elif sort == "views":
            query = query.order("view_count", desc=True)
        elif sort == "recent":
            query = query.order("scraped_at", desc=True)

        result = query.limit(limit).execute()
        return result.data or []

    except Exception as e:
        print(f"[trends] error: {e}")
        return []

@router.get("/niches")
async def get_niches():
    return [
        {"id": "all", "label": "Все"},
        {"id": "бизнес", "label": "Бизнес"},
        {"id": "бьюти", "label": "Бьюти"},
        {"id": "фитнес", "label": "Фитнес"},
        {"id": "еда", "label": "Еда"},
        {"id": "психология", "label": "Психология"},
        {"id": "мода", "label": "Мода"},
        {"id": "tech", "label": "Tech & AI"},
        {"id": "путешествия", "label": "Путешествия"},
        {"id": "юмор", "label": "Юмор"},
        {"id": "lifestyle", "label": "Lifestyle"},
    ]

@router.post("/scrape")
async def trigger_scrape():
    """Manually trigger scraping (admin only)."""
    from app.services.tasks import scrape_trends_task
    scrape_trends_task.delay()
    return {"status": "scraping started"}
