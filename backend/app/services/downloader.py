import yt_dlp
import os
import uuid
import tempfile
import subprocess
from pathlib import Path

DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "reelx_downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

def download_video(url: str) -> dict:
    """
    Download video from URL using yt-dlp.
    Returns dict with paths to video and audio files + metadata.
    """
    job_id = str(uuid.uuid4())
    output_dir = DOWNLOAD_DIR / job_id
    output_dir.mkdir(exist_ok=True)

    video_path = str(output_dir / "video.mp4")
    audio_path = str(output_dir / "audio.mp3")

    # Step 1: Download video only (best quality up to 720p)
    ydl_opts = {
        "format": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best",
        "outtmpl": video_path,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }

    meta = {}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            meta = {
                "title": info.get("title", ""),
                "uploader": info.get("uploader", "") or info.get("channel", ""),
                "duration": info.get("duration", 0),
                "view_count": info.get("view_count", 0),
                "like_count": info.get("like_count", 0),
                "platform": detect_platform(url),
                "original_url": url,
            }

        # Find the actual downloaded video file
        actual_video = None
        for ext in ["mp4", "webm", "mkv"]:
            candidate = str(output_dir / f"video.{ext}")
            if os.path.exists(candidate):
                actual_video = candidate
                break
        # yt-dlp sometimes adds suffix
        if not actual_video:
            for f in output_dir.iterdir():
                if f.suffix in [".mp4", ".webm", ".mkv"]:
                    actual_video = str(f)
                    break

        if not actual_video:
            raise RuntimeError("Video file not found after download")

        # Step 2: Extract audio with ffmpeg separately
        ffmpeg_cmd = [
            "ffmpeg", "-i", actual_video,
            "-vn", "-acodec", "mp3", "-ab", "128k",
            "-y", audio_path, "-loglevel", "error"
        ]
        subprocess.run(ffmpeg_cmd, check=False, capture_output=True)

        return {
            "job_id": job_id,
            "video_path": actual_video,
            "audio_path": audio_path if os.path.exists(audio_path) else None,
            "output_dir": str(output_dir),
            "meta": meta,
        }
    except Exception as e:
        raise RuntimeError(f"Download failed: {str(e)}")

def detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "instagram.com" in url_lower:
        return "Instagram"
    elif "tiktok.com" in url_lower:
        return "TikTok"
    elif "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "YouTube"
    return "Unknown"

def cleanup_job(output_dir: str):
    """Remove downloaded files after processing."""
    import shutil
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
