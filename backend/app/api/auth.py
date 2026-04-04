# Fixed auth.py - returns name from user metadata
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.database import get_supabase_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
async def register(req: RegisterRequest):
    try:
        db = get_supabase_admin()
        res = db.auth.sign_up({
            "email": req.email,
            "password": req.password,
            "options": {"data": {"name": req.name}}
        })
        if res.user:
            db.table("user_settings").insert({
                "user_id": res.user.id,
                "language": "ru",
                "tone": "conversational",
                "script_ending": "Подписывайся, чтобы не пропустить следующее.",
            }).execute()
            return {
                "user_id": res.user.id,
                "email": res.user.email,
                "name": req.name,
            }
        raise HTTPException(400, "Registration failed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/login")
async def login(req: LoginRequest):
    try:
        db = get_supabase_admin()
        res = db.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password
        })
        if res.user and res.session:
            # Get name from user metadata
            meta = res.user.user_metadata or {}
            name = meta.get("name", "") or res.user.email.split("@")[0]
            return {
                "user_id": res.user.id,
                "email": res.user.email,
                "name": name,
                "access_token": res.session.access_token,
            }
        raise HTTPException(401, "Invalid credentials")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(401, str(e))
