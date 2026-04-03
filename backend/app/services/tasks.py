from app.services.celery_app import celery_app
from app.services.pipeline import run_pipeline

@celery_app.task(name="analyze_video", bind=True, max_retries=0)
def analyze_video_task(self, job_id: str, url: str, user_id: str, user_settings: dict = None):
    """Celery task that runs the full analysis pipeline."""
    run_pipeline(job_id, url, user_id, user_settings)
    return {"job_id": job_id, "status": "done"}
