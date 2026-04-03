import uuid
from typing import Tuple
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from app.core.database import get_supabase_admin
from app.services.tasks import analyze_video_task
from app.core.config import settings

router = APIRouter(prefix="/api/analyze", tags=["analyze"])

SUPPORTED_DOMAINS = [
    "instagram.com", "tiktok.com", "youtube.com",
    "youtu.be", "vm.tiktok.com", "www.tiktok.com"
]

class AnalyzeRequest(BaseModel):
    url: str
    user_id: str

def validate_url(url: str) -> bool:
    return any(d in url.lower() for d in SUPPORTED_DOMAINS)

def check_trial_limit(user_id: str) -> Tuple[bool, int]:
    """Returns (can_analyze, analyses_used)."""
    try:
        db = get_supabase_admin()
        # Check active subscription first
        sub = db.table("subscriptions").select("status").eq(
            "user_id", user_id
        ).eq("status", "active").execute()
        if sub.data:
            return True, 0  # Paid user — unlimited

        # Count all analyses for this user
        analyses = db.table("analyses").select("id", count="exact").eq(
            "user_id", user_id
        ).execute()
        used = analyses.count or 0
        can = used < settings.TRIAL_ANALYSES_LIMIT
        return can, used
    except Exception:
        return True, 0  # Fail open — don't block user on DB error

@router.post("/start")
async def start_analysis(req: AnalyzeRequest):
    if not req.url or len(req.url) < 10:
        raise HTTPException(400, "Укажите ссылку на видео")

    if not validate_url(req.url):
        raise HTTPException(
            400,
            "Неподдерживаемая платформа. Используйте ссылки Instagram, TikTok или YouTube."
        )

    can_analyze, used = check_trial_limit(req.user_id)
    if not can_analyze:
        raise HTTPException(
            402,
            f"Исчерпан лимит триала ({settings.TRIAL_ANALYSES_LIMIT} анализов). "
            "Оформите подписку за 2000₽/мес."
        )

    job_id = str(uuid.uuid4())

    # Create job record in DB
    try:
        db = get_supabase_admin()
        db.table("analyses").insert({
            "job_id": job_id,
            "user_id": req.user_id,
            "url": req.url,
            "status": "pending",
            "progress_percent": 0,
            "current_step": "В очереди…",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")

    # Load user settings for personalization
    user_settings = None
    try:
        db = get_supabase_admin()
        s = db.table("user_settings").select("*").eq(
            "user_id", req.user_id
        ).execute()
        if s.data:
            user_settings = s.data[0]
    except Exception:
        pass  # Continue without settings

    # Queue the Celery task
    analyze_video_task.delay(job_id, req.url, req.user_id, user_settings)

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Анализ поставлен в очередь",
        "trial_used": used + 1,
        "trial_limit": settings.TRIAL_ANALYSES_LIMIT,
    }

@router.get("/status/{job_id}")
async def get_status(job_id: str):
    try:
        db = get_supabase_admin()
        result = db.table("analyses").select("*").eq("job_id", job_id).execute()
        if not result.data:
            raise HTTPException(404, f"Job {job_id} not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/history/{user_id}")
async def get_history(user_id: str):
    try:
        db = get_supabase_admin()
        result = db.table("analyses").select(
            "job_id,url,status,video_meta,created_at,completed_at"
        ).eq("user_id", user_id).order(
            "created_at", desc=True
        ).limit(50).execute()
        return result.data or []
    except Exception as e:
        raise HTTPException(500, str(e))
