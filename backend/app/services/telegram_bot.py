"""
REELX Telegram Bot
Webhook-based, runs as part of FastAPI
"""
import os
import httpx
import asyncio
from datetime import datetime
from app.core.config import settings
from app.core.database import get_supabase_admin

BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ─── SEND MESSAGE ────────────────────────────────────────
async def send_message(chat_id: int, text: str, parse_mode: str = "HTML"):
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        })

# ─── HANDLE UPDATE ───────────────────────────────────────
async def handle_update(update: dict):
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # /start с токеном привязки
    if text.startswith("/start"):
        parts = text.split(" ", 1)
        if len(parts) == 2:
            token = parts[1].strip()
            await handle_link_token(chat_id, token, message)
        else:
            await send_message(chat_id,
                "👋 Привет! Я бот REELX.\n\n"
                "Чтобы начать, привяжи свой аккаунт в настройках на <a href='https://reelx.app/settings.html'>reelx.app</a>.\n\n"
                "После привязки просто отправь мне ссылку на рилс, тикток или шортс — и я сделаю полный разбор."
            )
        return

    # Проверяем авторизован ли пользователь
    user_id = get_user_by_telegram(chat_id)
    if not user_id:
        await send_message(chat_id,
            "❌ Твой Telegram не привязан к аккаунту REELX.\n\n"
            "Зайди в <a href='https://reelx.app/settings.html'>настройки</a> и нажми «Привязать Telegram»."
        )
        return

    # Проверяем ссылку
    supported = ["instagram.com", "tiktok.com", "youtube.com", "youtu.be"]
    if any(d in text for d in supported):
        await handle_analyze(chat_id, text, user_id)
    else:
        await send_message(chat_id,
            "Отправь мне ссылку на видео:\n"
            "• Instagram Reels\n"
            "• TikTok\n"
            "• YouTube Shorts"
        )

# ─── LINK TOKEN ──────────────────────────────────────────
async def handle_link_token(chat_id: int, token: str, message: dict):
    try:
        db = get_supabase_admin()
        result = db.table("telegram_link_tokens").select("*").eq("token", token).eq("used", False).execute()

        if not result.data:
            await send_message(chat_id, "❌ Ссылка недействительна или устарела. Попробуй снова в настройках.")
            return

        row = result.data[0]

        # Проверяем срок действия
        expires = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
        if expires.replace(tzinfo=None) < datetime.utcnow():
            await send_message(chat_id, "❌ Ссылка истекла. Запроси новую в настройках.")
            return

        user_id = row["user_id"]
        tg_user = message.get("from", {})
        tg_username = tg_user.get("username", "")
        tg_name = tg_user.get("first_name", "")

        # Сохраняем telegram_id
        db.table("user_settings").update({
            "telegram_id": str(chat_id)
        }).eq("user_id", user_id).execute()

        # Помечаем токен как использованный
        db.table("telegram_link_tokens").update({"used": True}).eq("token", token).execute()

        await send_message(chat_id,
            f"✅ Аккаунт успешно привязан!\n\n"
            f"Теперь просто отправь мне ссылку на рилс, тикток или шортс — и я сделаю полный разбор за пару минут."
        )

    except Exception as e:
        print(f"[bot] link token error: {e}")
        await send_message(chat_id, "❌ Произошла ошибка. Попробуй ещё раз.")

# ─── ANALYZE ─────────────────────────────────────────────
async def handle_analyze(chat_id: int, url: str, user_id: str):
    try:
        await send_message(chat_id, "⏳ Запускаю анализ... Это займёт 1-2 минуты.")

        db = get_supabase_admin()

        # Проверяем триал
        sub = db.table("subscriptions").select("status").eq("user_id", user_id).eq("status", "active").execute()
        if not sub.data:
            analyses = db.table("analyses").select("id", count="exact").eq("user_id", user_id).execute()
            used = analyses.count or 0
            if used >= settings.TRIAL_ANALYSES_LIMIT:
                await send_message(chat_id,
                    f"❌ Исчерпан лимит триала ({settings.TRIAL_ANALYSES_LIMIT} анализов).\n\n"
                    f"Оформи подписку на <a href='https://reelx.app/pricing.html'>reelx.app</a> за 2000₽/мес."
                )
                return

        # Запускаем анализ через Celery
        import uuid
        job_id = str(uuid.uuid4())

        db.table("analyses").insert({
            "job_id": job_id,
            "user_id": user_id,
            "url": url,
            "status": "pending",
            "progress_percent": 0,
            "current_step": "В очереди…",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }).execute()

        # Загружаем настройки пользователя
        user_settings = None
        s = db.table("user_settings").select("*").eq("user_id", user_id).execute()
        if s.data:
            user_settings = s.data[0]

        from app.services.tasks import analyze_video_task
        analyze_video_task.delay(job_id, url, user_id, user_settings)

        # Ждём результат (polling каждые 3 сек, макс 3 мин)
        for _ in range(60):
            await asyncio.sleep(3)
            result = db.table("analyses").select("*").eq("job_id", job_id).execute()
            if not result.data:
                continue
            job = result.data[0]
            if job["status"] == "done":
                await send_result(chat_id, job)
                return
            elif job["status"] == "failed":
                await send_message(chat_id, f"❌ Ошибка анализа: {job.get('error', 'неизвестная ошибка')}")
                return

        await send_message(chat_id, "⏰ Анализ занял слишком много времени. Проверь результат на сайте.")

    except Exception as e:
        print(f"[bot] analyze error: {e}")
        await send_message(chat_id, "❌ Произошла ошибка при анализе. Попробуй ещё раз.")

# ─── SEND RESULT ─────────────────────────────────────────
async def send_result(chat_id: int, job: dict):
    meta = job.get("video_meta") or {}
    platform = meta.get("platform", "")
    uploader = meta.get("uploader", "")
    views = meta.get("view_count", 0)

    # Сценарий
    script = job.get("script", "")
    hooks = job.get("hooks") or []
    description = job.get("description", "")
    hashtags = job.get("hashtags") or []
    strategy = job.get("strategy", "")

    # Сообщение 1 — мета + сценарий
    msg1 = f"✅ <b>Разбор готов!</b>\n\n"
    if platform:
        msg1 += f"📱 <b>{platform}</b> @{uploader} · {format_number(views)} просм.\n\n"
    if script:
        msg1 += f"📝 <b>Сценарий:</b>\n{script[:1000]}"

    await send_message(chat_id, msg1)
    await asyncio.sleep(0.5)

    # Сообщение 2 — лучший хук
    if hooks:
        best = next((h for h in hooks if h.get("is_selected")), hooks[0])
        msg2 = f"🎣 <b>Лучший хук:</b>\n<i>{best.get('text', '')}</i>\n\n"
        msg2 += f"💡 {best.get('explanation', '')}"
        await send_message(chat_id, msg2)
        await asyncio.sleep(0.5)

    # Сообщение 3 — описание + хештеги
    if description or hashtags:
        msg3 = ""
        if description:
            msg3 += f"📄 <b>Описание:</b>\n{description[:500]}\n\n"
        if hashtags:
            msg3 += f"#️⃣ <b>Хештеги:</b>\n{' '.join(hashtags[:12])}"
        await send_message(chat_id, msg3)
        await asyncio.sleep(0.5)

    # Сообщение 4 — стратегия
    if strategy:
        msg4 = f"📊 <b>Стратегия:</b>\n{strategy[:800]}"
        await send_message(chat_id, msg4)

    # Ссылка на полный результат
    job_id = job.get("job_id", "")
    await send_message(chat_id,
        f"🔗 <a href='https://reelx.app/analyze.html?job={job_id}'>Открыть полный разбор на сайте</a>"
    )

# ─── HELPERS ─────────────────────────────────────────────
def get_user_by_telegram(chat_id: int) -> str | None:
    try:
        db = get_supabase_admin()
        result = db.table("user_settings").select("user_id").eq("telegram_id", str(chat_id)).execute()
        if result.data:
            return result.data[0]["user_id"]
    except Exception:
        pass
    return None

def format_number(n) -> str:
    if not n:
        return "0"
    n = int(n)
    if n >= 1000000:
        return f"{n/1000000:.1f}М"
    if n >= 1000:
        return f"{n/1000:.1f}К"
    return str(n)