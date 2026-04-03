"""
Main pipeline: URL -> download -> extract audio -> transcribe -> extract frames -> analyze -> generate
"""
import os
import traceback
from datetime import datetime
from app.services.downloader import download_video, cleanup_job
from app.services.transcriber import transcribe_audio
from app.services.frame_extractor import extract_frames
from app.services.analyzer import analyze_frames, generate_script
from app.core.database import get_supabase_admin

def update_job(job_id: str, status: str, progress: int, step_label: str, extra: dict = None):
    """Update job status in Supabase."""
    try:
        db = get_supabase_admin()
        data = {
            "status": status,
            "progress_percent": progress,
            "current_step": step_label,
            "updated_at": datetime.utcnow().isoformat(),
        }
        if extra:
            data.update(extra)
        db.table("analyses").update(data).eq("job_id", job_id).execute()
    except Exception as e:
        print(f"[update_job error] job={job_id} err={e}")

def run_pipeline(job_id: str, url: str, user_id: str, user_settings: dict = None):
    """
    Full analysis pipeline. Called synchronously inside Celery worker.
    """
    print(f"[pipeline] START job={job_id}")
    output_dir = None

    try:
        # ── STEP 1: Download video ──────────────────────────────────────
        update_job(job_id, "downloading", 5, "Скачиваем видео…")
        download_result = download_video(url)

        video_path = download_result["video_path"]
        audio_path = download_result["audio_path"]
        output_dir = download_result["output_dir"]
        video_meta = download_result["meta"]
        print(f"[pipeline] downloaded: platform={video_meta.get('platform')} "
              f"views={video_meta.get('view_count')} duration={video_meta.get('duration')}s")

        # ── STEP 2: Save meta ───────────────────────────────────────────
        update_job(job_id, "extracting_audio", 20, "Извлекаем аудио…", {
            "video_meta": video_meta
        })

        # ── STEP 3: Transcribe audio ────────────────────────────────────
        update_job(job_id, "transcribing", 38, "Транскрибируем речь…")
        transcript = ""
        if audio_path and os.path.exists(audio_path):
            try:
                transcript = transcribe_audio(audio_path)
                print(f"[pipeline] transcript: {len(transcript)} chars")
            except Exception as e:
                print(f"[pipeline] transcription skipped: {e}")
        else:
            print("[pipeline] no audio file — skipping transcription")

        # ── STEP 4: Extract frames ──────────────────────────────────────
        update_job(job_id, "extracting_frames", 55, "Извлекаем кадры…")
        frame_paths = []
        if video_path and os.path.exists(video_path):
            try:
                frame_paths = extract_frames(video_path, output_dir, fps=0.5)
                print(f"[pipeline] extracted {len(frame_paths)} frames")
            except Exception as e:
                print(f"[pipeline] frame extraction skipped: {e}")
        else:
            print("[pipeline] no video file — skipping frame extraction")

        # ── STEP 5: Analyze frames with Claude Vision ───────────────────
        update_job(job_id, "analyzing", 72, "Анализируем кадры…")
        frames_analysis = []
        if frame_paths:
            try:
                frames_analysis = analyze_frames(frame_paths)
                print(f"[pipeline] frame analysis: {len(frames_analysis)} frames analyzed")
            except Exception as e:
                print(f"[pipeline] frame analysis skipped: {e}")

        # ── STEP 6: Generate full script package ────────────────────────
        update_job(job_id, "generating", 88, "Генерируем сценарий…")
        result = generate_script(transcript, frames_analysis, video_meta, user_settings)
        print(f"[pipeline] script generated: keys={list(result.keys())}")

        # ── STEP 7: Save everything ─────────────────────────────────────
        update_job(job_id, "done", 100, "Готово!", {
            "transcript": transcript,
            "frames": frames_analysis,
            "script": result.get("script", ""),
            "hooks": result.get("hooks", []),
            "description": result.get("description", ""),
            "hashtags": result.get("hashtags", []),
            "editor_brief": result.get("editor_brief", ""),
            "strategy": result.get("strategy", ""),
            "completed_at": datetime.utcnow().isoformat(),
        })

        print(f"[pipeline] DONE job={job_id}")

    except Exception as e:
        error_msg = str(e)
        print(f"[pipeline] FAILED job={job_id}: {error_msg}")
        print(traceback.format_exc())
        update_job(job_id, "failed", 0, "Ошибка обработки", {
            "error": error_msg
        })

    finally:
        # Always clean up downloaded files
        if output_dir and os.path.exists(output_dir):
            try:
                cleanup_job(output_dir)
                print(f"[pipeline] cleaned up {output_dir}")
            except Exception as e:
                print(f"[pipeline] cleanup error: {e}")
