import uuid
from fastapi import APIRouter, HTTPException, Header
from app.core.database import get_supabase_admin
from app.core.config import settings
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["admin"])

def verify_admin(x_admin_key: str):
    if x_admin_key != settings.SECRET_KEY:
        raise HTTPException(403, "Forbidden")

@router.get("/stats")
async def get_stats(x_admin_key: str = Header(...)):
    verify_admin(x_admin_key)
    try:
        db = get_supabase_admin()
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0).isoformat()

        # Total users
        users = db.table("user_settings").select("user_id", count="exact").execute()
        total_users = users.count or 0

        # Active subscriptions
        subs = db.table("subscriptions").select("id", count="exact").eq("status", "active").execute()
        active_subs = subs.count or 0

        # New this month
        new_subs = db.table("subscriptions").select("id", count="exact")\
            .eq("status", "active")\
            .gte("started_at", month_start).execute()
        new_this_month = new_subs.count or 0

        # MRR / ARR
        mrr = active_subs * 2000
        arr = mrr * 12

        # Total analyses
        all_analyses = db.table("analyses").select("id", count="exact").execute()
        total_analyses = all_analyses.count or 0

        # This month analyses
        month_analyses = db.table("analyses").select("id", count="exact")\
            .gte("created_at", month_start).execute()
        analyses_this_month = month_analyses.count or 0

        # Recent payments
        payments = db.table("payments").select("*")\
            .eq("status", "paid")\
            .order("created_at", desc=True)\
            .limit(10).execute()

        return {
            "total_users": total_users,
            "active_subscriptions": active_subs,
            "new_subscriptions_this_month": new_this_month,
            "mrr_rub": mrr,
            "arr_rub": arr,
            "total_analyses": total_analyses,
            "analyses_this_month": analyses_this_month,
            "recent_payments": payments.data or [],
            "generated_at": now.isoformat(),
        }
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/users")
async def get_users(x_admin_key: str = Header(...), limit: int = 100):
    verify_admin(x_admin_key)
    try:
        db = get_supabase_admin()
        result = db.table("user_settings").select("*").limit(limit).execute()
        return result.data or []
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/referrals")
async def get_referrals(x_admin_key: str = Header(...)):
    verify_admin(x_admin_key)
    try:
        db = get_supabase_admin()
        result = db.table("referrals").select("*").order("created_at", desc=True).execute()
        return result.data or []
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/referrals/{user_id}/approve")
async def approve_referral(user_id: str, x_admin_key: str = Header(...)):
    verify_admin(x_admin_key)
    try:
        db = get_supabase_admin()
        ref_code = str(uuid.uuid4())[:8].upper()
        db.table("referrals").upsert({
            "user_id": user_id,
            "status": "approved",
            "ref_code": ref_code,
            "commission_percent": 15,
            "approved_at": datetime.utcnow().isoformat(),
        }).execute()
        return {"ref_code": ref_code, "message": "Referral approved"}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/referrals/{user_id}/reject")
async def reject_referral(user_id: str, x_admin_key: str = Header(...)):
    verify_admin(x_admin_key)
    try:
        db = get_supabase_admin()
        db.table("referrals").update({
            "status": "rejected"
        }).eq("user_id", user_id).execute()
        return {"message": "Referral rejected"}
    except Exception as e:
        raise HTTPException(500, str(e))
