import os
import yt_dlp
import shutil
import tempfile

# Path to Instagram cookies file
COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instagram_cookies.txt')

def download_video(url: str) -> dict:
    output_dir = tempfile.mkdtemp(prefix='reelx_')
    video_path = os.path.join(output_dir, 'video.mp4')
    audio_path = os.path.join(output_dir, 'audio.mp3')

    ydl_opts = {
        'outtmpl': os.path.join(output_dir, 'video.%(ext)s'),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }

    # Add cookies for Instagram
    if 'instagram.com' in url and os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE
        print(f"[downloader] using Instagram cookies from {COOKIES_FILE}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        meta = {
            'title': info.get('title', ''),
            'uploader': info.get('uploader', info.get('channel', 'unknown')),
            'view_count': info.get('view_count', 0),
            'like_count': info.get('like_count', 0),
            'duration': info.get('duration', 0),
            'platform': _detect_platform(url),
            'url': url,
        }

    # Find downloaded video file
    for f in os.listdir(output_dir):
        if f.startswith('video') and f.endswith('.mp4'):
            video_path = os.path.join(output_dir, f)
            break

    # Extract audio
    audio_path = _extract_audio(video_path, output_dir)

    return {
        'video_path': video_path,
        'audio_path': audio_path,
        'output_dir': output_dir,
        'meta': meta,
    }

def _extract_audio(video_path: str, output_dir: str) -> str:
    audio_path = os.path.join(output_dir, 'audio.mp3')
    try:
        import subprocess
        result = subprocess.run([
            'ffmpeg', '-i', video_path,
            '-vn', '-acodec', 'mp3', '-ar', '16000', '-ac', '1',
            '-y', audio_path
        ], capture_output=True, timeout=60)
        if result.returncode == 0 and os.path.exists(audio_path):
            return audio_path
    except Exception as e:
        print(f"[downloader] audio extraction failed: {e}")
    return None

def _detect_platform(url: str) -> str:
    if 'instagram.com' in url: return 'Instagram'
    if 'tiktok.com' in url: return 'TikTok'
    if 'youtube.com' in url or 'youtu.be' in url: return 'YouTube'
    return 'Video'

def cleanup_job(output_dir: str):
    if output_dir and os.path.exists(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
