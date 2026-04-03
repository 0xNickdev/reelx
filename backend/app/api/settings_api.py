from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import get_supabase_admin

router = APIRouter(prefix="/api/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    user_id: str
    language: Optional[str] = None
    about_me: Optional[str] = None
    tone: Optional[str] = None
    script_ending: Optional[str] = None
    description_ending: Optional[str] = None
    stop_words: Optional[str] = None
    video_format: Optional[str] = None
    interests: Optional[List[str]] = None
    trend_notifications: Optional[bool] = None

@router.get("/{user_id}")
async def get_settings(user_id: str):
    try:
        db = get_supabase_admin()
        res = db.table("user_settings").select("*").eq("user_id", user_id).single().execute()
        if res.data:
            return res.data
        # Return defaults if not found
        return {
            "user_id": user_id,
            "language": "ru",
            "tone": "conversational",
            "script_ending": "Подписывайся, чтобы не пропустить следующее.",
            "description_ending": "",
            "stop_words": "",
            "video_format": "head_visual",
            "interests": [],
            "trend_notifications": False,
        }
    except Exception as e:
        raise HTTPException(500, str(e))

@router.put("/update")
async def update_settings(req: SettingsUpdate):
    try:
        db = get_supabase_admin()
        update_data = {k: v for k, v in req.dict().items() if v is not None and k != "user_id"}
        if not update_data:
            return {"message": "Nothing to update"}

        # Upsert settings
        existing = db.table("user_settings").select("id").eq("user_id", req.user_id).execute()
        if existing.data:
            db.table("user_settings").update(update_data).eq("user_id", req.user_id).execute()
        else:
            db.table("user_settings").insert({"user_id": req.user_id, **update_data}).execute()

        return {"message": "Настройки сохранены"}
    except Exception as e:
        raise HTTPException(500, str(e))
