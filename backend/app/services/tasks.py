from app.services.celery_app import celery_app
from app.services.pipeline import run_pipeline
from app.core.database import get_supabase_admin

@celery_app.task(name="run_analysis")
def run_analysis_task(job_id: str, url: str, user_id: str, user_settings: dict = None):
    run_pipeline(job_id, url, user_id, user_settings)

# Alias for backward compatibility
analyze_video_task = run_analysis_task

@celery_app.task(name="scrape_trends")
def scrape_trends_task():
    from app.services.trends_scraper import run_full_scrape
    return run_full_scrape()

# Celery beat schedule - every 2 hours
from celery.schedules import crontab
celery_app.conf.beat_schedule = {
    "scrape-trends-every-2h": {
        "task": "scrape_trends",
        "schedule": crontab(minute=0, hour="*/2"),
    },
}
