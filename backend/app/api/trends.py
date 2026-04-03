from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.core.database import get_supabase_admin

router = APIRouter(prefix="/api/trends", tags=["trends"])

@router.get("/feed")
async def get_trends(
    niche: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    sort: str = Query("xfactor"),  # xfactor | views | fresh
    limit: int = Query(20),
    offset: int = Query(0),
):
    try:
        db = get_supabase_admin()
        query = db.table("trends").select("*").eq("is_active", True)

        if niche and niche != "all":
            query = query.eq("niche", niche)
        if platform and platform != "all":
            query = query.eq("platform", platform)

        if sort == "xfactor":
            query = query.order("xfactor", desc=True)
        elif sort == "views":
            query = query.order("view_count", desc=True)
        elif sort == "fresh":
            query = query.order("published_at", desc=True)

        result = query.range(offset, offset + limit - 1).execute()
        return result.data or []
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/niches")
async def get_niches():
    return [
        {"id": "business", "name": "Бизнес", "emoji": "💰"},
        {"id": "beauty", "name": "Бьюти", "emoji": "💄"},
        {"id": "fitness", "name": "Фитнес", "emoji": "💪"},
        {"id": "food", "name": "Еда", "emoji": "🍕"},
        {"id": "psychology", "name": "Психология", "emoji": "🧠"},
        {"id": "fashion", "name": "Мода", "emoji": "👗"},
        {"id": "tech", "name": "Tech & AI", "emoji": "🤖"},
        {"id": "travel", "name": "Путешествия", "emoji": "✈️"},
        {"id": "humor", "name": "Юмор", "emoji": "😂"},
        {"id": "other", "name": "Другое", "emoji": "🎯"},
    ]
