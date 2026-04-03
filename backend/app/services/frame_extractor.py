import subprocess
import os
import base64
from pathlib import Path
from typing import List

def extract_frames(video_path: str, output_dir: str, fps: float = 0.5) -> List[str]:
    """
    Extract frames from video using ffmpeg.
    fps=0.5 means 1 frame every 2 seconds.
    Returns list of frame file paths.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    frames_dir = Path(output_dir) / "frames"
    frames_dir.mkdir(exist_ok=True)

    output_pattern = str(frames_dir / "frame_%04d.jpg")

    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps={fps},scale=720:-1",
        "-q:v", "3",
        "-y",
        output_pattern
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr}")

    frames = sorted(frames_dir.glob("frame_*.jpg"))
    return [str(f) for f in frames]

def frame_to_base64(frame_path: str) -> str:
    """Convert frame image to base64 for Claude Vision."""
    with open(frame_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def get_frame_timestamp(frame_index: int, fps: float = 0.5) -> str:
    """Calculate timestamp from frame index."""
    seconds = frame_index / fps
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"
