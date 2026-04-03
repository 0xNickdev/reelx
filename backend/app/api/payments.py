import uuid
import hmac
import hashlib
import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.core.config import settings
from app.core.database import get_supabase_admin

router = APIRouter(prefix="/api/payments", tags=["payments"])

PRICE_RUB = 2000
PRICE_USDT = 22

class CreatePaymentRequest(BaseModel):
    user_id: str
    method: str  # "yukassa" | "crypto"

@router.post("/create")
async def create_payment(req: CreatePaymentRequest):
    if req.method == "crypto":
        return await create_crypto_payment(req.user_id)
    elif req.method == "yukassa":
        return await create_yukassa_payment(req.user_id)
    raise HTTPException(400, "Unknown payment method. Use 'yukassa' or 'crypto'")

async def create_crypto_payment(user_id: str) -> dict:
    """Create USDT payment via NowPayments."""
    if not settings.NOWPAYMENTS_API_KEY:
        raise HTTPException(500, "NowPayments not configured")

    order_id = f"reelx_{user_id}_{int(datetime.utcnow().timestamp())}"

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            "https://api.nowpayments.io/v1/payment",
            headers={
                "x-api-key": settings.NOWPAYMENTS_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "price_amount": PRICE_USDT,
                "price_currency": "usd",
                "pay_currency": "usdttrc20",
                "order_id": order_id,
                "order_description": "REELX подписка 1 месяц",
                "ipn_callback_url": f"{settings.FRONTEND_URL}/api/payments/crypto/webhook",
            }
        )

    data = res.json()
    if "payment_id" not in data:
        raise HTTPException(500, f"NowPayments error: {data}")

    db = get_supabase_admin()
    db.table("payments").insert({
        "user_id": user_id,
        "method": "crypto",
        "external_id": str(data["payment_id"]),
        "amount": PRICE_USDT,
        "currency": "USDT",
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }).execute()

    return {
        "payment_id": data["payment_id"],
        "pay_address": data.get("pay_address"),
        "pay_amount": data.get("pay_amount"),
        "pay_currency": "USDT TRC-20",
        "expiration_estimate_date": data.get("expiration_estimate_date"),
    }

async def create_yukassa_payment(user_id: str) -> dict:
    """Create payment via ЮKassa."""
    if not settings.YUKASSA_SHOP_ID or not settings.YUKASSA_SECRET_KEY:
        raise HTTPException(500, "ЮKassa not configured")

    idempotence_key = str(uuid.uuid4())

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            "https://api.yookassa.ru/v3/payments",
            auth=(settings.YUKASSA_SHOP_ID, settings.YUKASSA_SECRET_KEY),
            headers={
                "Idempotence-Key": idempotence_key,
                "Content-Type": "application/json",
            },
            json={
                "amount": {"value": str(float(PRICE_RUB)), "currency": "RUB"},
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"{settings.FRONTEND_URL}/dashboard.html?payment=success"
                },
                "description": "REELX подписка 1 месяц",
                "metadata": {"user_id": user_id},
                "capture": True,
            }
        )

    data = res.json()
    if "id" not in data:
        raise HTTPException(500, f"ЮKassa error: {data}")

    db = get_supabase_admin()
    db.table("payments").insert({
        "user_id": user_id,
        "method": "yukassa",
        "external_id": data["id"],
        "amount": PRICE_RUB,
        "currency": "RUB",
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }).execute()

    return {
        "payment_id": data["id"],
        "confirmation_url": data["confirmation"]["confirmation_url"],
    }

def activate_subscription(user_id: str):
    """Activate 30-day subscription for user."""
    db = get_supabase_admin()
    now = datetime.utcnow()
    expires = now + timedelta(days=30)

    existing = db.table("subscriptions").select("id").eq("user_id", user_id).execute()
    if existing.data:
        db.table("subscriptions").update({
            "status": "active",
            "expires_at": expires.isoformat(),
            "updated_at": now.isoformat(),
        }).eq("user_id", user_id).execute()
    else:
        db.table("subscriptions").insert({
            "user_id": user_id,
            "status": "active",
            "started_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "created_at": now.isoformat(),
        }).execute()

@router.post("/crypto/webhook")
async def crypto_webhook(request: Request):
    """NowPayments IPN webhook — called when crypto payment confirmed."""
    body = await request.body()
    sig = request.headers.get("x-nowpayments-sig", "")

    # Verify signature if secret is set
    if settings.NOWPAYMENTS_IPN_SECRET and sig:
        expected = hmac.new(
            settings.NOWPAYMENTS_IPN_SECRET.encode(),
            body,
            hashlib.sha512
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(400, "Invalid signature")

    import json
    data = json.loads(body)
    payment_status = data.get("payment_status", "")

    if payment_status in ("finished", "confirmed"):
        order_id = data.get("order_id", "")
        parts = order_id.split("_")
        user_id = parts[1] if len(parts) >= 2 else None
        if user_id:
            activate_subscription(user_id)
            db = get_supabase_admin()
            db.table("payments").update({"status": "paid"}).eq(
                "external_id", str(data.get("payment_id"))
            ).execute()

    return {"status": "ok"}

@router.post("/yukassa/webhook")
async def yukassa_webhook(request: Request):
    """ЮKassa webhook — called when card/SBP payment confirmed."""
    data = await request.json()
    event = data.get("event", "")

    if event == "payment.succeeded":
        payment_obj = data.get("object", {})
        user_id = payment_obj.get("metadata", {}).get("user_id")
        payment_id = payment_obj.get("id")
        if user_id:
            activate_subscription(user_id)
            db = get_supabase_admin()
            db.table("payments").update({"status": "paid"}).eq(
                "external_id", payment_id
            ).execute()

    return {"status": "ok"}

@router.get("/subscription/{user_id}")
async def get_subscription(user_id: str):
    try:
        db = get_supabase_admin()
        res = db.table("subscriptions").select("*").eq("user_id", user_id).execute()
        if not res.data:
            return {"status": "none", "user_id": user_id}

        sub = res.data[0]
        # Check if expired
        expires_str = sub.get("expires_at", "")
        if expires_str:
            expires = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            if expires.replace(tzinfo=None) < datetime.utcnow():
                db.table("subscriptions").update({"status": "expired"}).eq(
                    "user_id", user_id
                ).execute()
                sub["status"] = "expired"
        return sub
    except Exception as e:
        raise HTTPException(500, str(e))
