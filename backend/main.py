from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import analyze, auth, settings_api, payments, trends, admin
from fastapi import Request
from app.core.database import get_supabase_admin

app = FastAPI(
    title="REELX API",
    description="Backend for REELX viral content analysis platform",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:8080",
        "https://reelx.app",
        "https://www.reelx.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(analyze.router)
app.include_router(settings_api.router)
app.include_router(payments.router)
app.include_router(trends.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    return {"status": "ok", "service": "REELX API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

import secrets
from datetime import datetime, timedelta

import asyncio
from fastapi.background import BackgroundTasks

@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    from app.services.telegram_bot import handle_update
    data = await request.json()
    background_tasks.add_task(handle_update, data)
    return {"ok": True}

@app.post("/api/telegram/link")
async def generate_link_token(request: Request):
    """Generate one-time token for Telegram account linking."""
    data = await request.json()
    user_id = data.get("user_id")
    if not user_id:
        from fastapi import HTTPException
        raise HTTPException(400, "user_id required")

    token = secrets.token_urlsafe(32)
    db_client = get_supabase_admin()
    db_client.table("telegram_link_tokens").insert({
        "token": token,
        "user_id": user_id,
        "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
    }).execute()

    bot_username = "ReelXapp_bot"  
    return {
        "token": token,
        "url": f"https://t.me/{bot_username}?start={token}"
    }