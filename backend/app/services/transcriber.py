from openai import OpenAI
from app.core.config import settings
import os

def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio file using OpenAI Whisper.
    Returns transcript as plain text with timestamps.
    """
    if not audio_path or not os.path.exists(audio_path):
        return ""

    # Check file size — Whisper limit is 25MB
    size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    if size_mb > 24:
        raise RuntimeError(f"Audio file too large: {size_mb:.1f}MB (max 24MB)")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    lines = []
    # Whisper verbose_json returns object with .segments list
    # Each segment is an object with .start, .end, .text attributes
    segments = getattr(response, "segments", None)
    if segments:
        for seg in segments:
            # Handle both object attributes and dict access
            if isinstance(seg, dict):
                start = seg.get("start", 0)
                text = seg.get("text", "").strip()
            else:
                start = getattr(seg, "start", 0)
                text = getattr(seg, "text", "").strip()

            if text:
                lines.append(f"{format_timestamp(start)}  {text}")
    else:
        # Fallback: plain text
        text = getattr(response, "text", "") or ""
        if text:
            lines.append(text)

    return "\n".join(lines)

def format_timestamp(seconds: float) -> str:
    total = int(seconds)
    m = total // 60
    s = total % 60
    return f"{m}:{s:02d}"
