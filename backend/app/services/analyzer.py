import anthropic
import json
import re
from typing import List
from app.core.config import settings
from app.services.frame_extractor import frame_to_base64, get_frame_timestamp

def get_client():
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

def parse_json_response(text: str) -> dict | list:
    """Robustly extract JSON from Claude response."""
    text = text.strip()

    # Remove markdown code blocks if present
    if "```" in text:
        # Extract content between ```json ... ``` or ``` ... ```
        match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text)
        if match:
            text = match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object/array in the text
        match = re.search(r'(\{[\s\S]+\}|\[[\s\S]+\])', text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        raise RuntimeError(f"Could not parse JSON from response: {text[:300]}")

def analyze_frames(frame_paths: List[str]) -> List[dict]:
    """
    Analyze video frames using Claude Vision.
    Returns list of frame descriptions with type labels.
    """
    if not frame_paths:
        return []

    client = get_client()

    # Limit to 8 frames to avoid token overflow
    frames_to_use = frame_paths[:8]
    content = []

    for i, frame_path in enumerate(frames_to_use):
        try:
            b64 = frame_to_base64(frame_path)
        except Exception:
            continue

        timestamp = get_frame_timestamp(i)
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}
        })
        content.append({
            "type": "text",
            "text": f"Frame {i+1} at {timestamp}:"
        })

    if not content:
        return []

    content.append({
        "type": "text",
        "text": (
            "Analyze each frame. Return a JSON array only, no explanation:\n"
            '[\n'
            '  {\n'
            '    "frame_number": 1,\n'
            '    "timestamp": "00:00",\n'
            '    "frame_type": "talking_head",\n'
            '    "description": "brief description in Russian"\n'
            '  }\n'
            ']\n'
            'frame_type must be "talking_head" or "cutaway". '
            'Return ONLY the JSON array.'
        )
    })

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": content}]
    )

    try:
        result = parse_json_response(response.content[0].text)
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"[analyze_frames] JSON parse error: {e}")
        return []

def generate_script(
    transcript: str,
    frames: List[dict],
    video_meta: dict,
    user_settings: dict = None
) -> dict:
    """
    Generate full content package using Claude.
    Returns: script, hooks, description, hashtags, editor_brief, strategy.
    """
    client = get_client()

    # Build user context
    settings_ctx = ""
    if user_settings:
        lang = user_settings.get("language", "ru")
        tone = user_settings.get("tone", "conversational")
        about = user_settings.get("about_me", "")
        ending = user_settings.get("script_ending", "")
        stop_words = user_settings.get("stop_words", "")
        fmt = user_settings.get("video_format", "head_visual")
        settings_ctx = f"""
USER SETTINGS:
- Language for output: {lang}
- Tone: {tone}
- About author: {about}
- Script ending phrase: {ending}
- FORBIDDEN words (never use): {stop_words}
- Video format: {fmt}
"""

    # Format frames
    frames_text = "\n".join([
        f"[{f.get('timestamp', '?')}] {f.get('frame_type', '?')} — {f.get('description', '')}"
        for f in frames
    ]) if frames else "No frame data available"

    # Format meta
    views = video_meta.get("view_count", 0)
    likes = video_meta.get("like_count", 0)
    duration = video_meta.get("duration", 0)
    platform = video_meta.get("platform", "Unknown")
    uploader = video_meta.get("uploader", "Unknown")

    prompt = f"""You are an expert viral content strategist for Russian-speaking creators.
Analyze this viral video and create a complete content adaptation package.

VIDEO INFO:
- Platform: {platform}
- Author: @{uploader}
- Duration: {duration}s
- Views: {views:,}
- Likes: {likes:,}
{settings_ctx}
TRANSCRIPT:
{transcript or "(no speech detected)"}

FRAME BREAKDOWN:
{frames_text}

Create a complete content package. Output ONLY a valid JSON object with exactly these keys:

{{
  "script": "Teleprompter-ready script in Russian with [0:00] timestamp markers. Max 8 lines. Natural speaking voice.",
  "hooks": [
    {{
      "number": 1,
      "text": "Hook option 1",
      "explanation": "Why this works — psychological mechanism in Russian",
      "tag": "strong",
      "timing_seconds": 2.5,
      "is_selected": true
    }},
    {{"number": 2, "text": "...", "explanation": "...", "tag": "best", "timing_seconds": 3.2, "is_selected": false}},
    {{"number": 3, "text": "...", "explanation": "...", "tag": "alternative", "timing_seconds": 4.0, "is_selected": false}},
    {{"number": 4, "text": "...", "explanation": "...", "tag": "alternative", "timing_seconds": 2.8, "is_selected": false}},
    {{"number": 5, "text": "...", "explanation": "...", "tag": "alternative", "timing_seconds": 3.5, "is_selected": false}}
  ],
  "description": "Instagram/TikTok caption in Russian. 4-6 lines. Includes CTA. Emojis.",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8", "#tag9", "#tag10", "#tag11", "#tag12"],
  "editor_brief": "Editor instructions with timecodes:\\n0:00-0:04\\nVisual: ...\\nText on screen: ...\\nTransition: cut\\n\\n0:04-0:08\\nVisual: ...\\nText on screen: ...\\nTransition: zoom in",
  "strategy": "2-3 paragraphs in Russian: why this went viral, key psychological triggers, best posting time, how to adapt for your audience."
}}

Rules:
- tag values: only "strong", "best", or "alternative"  
- exactly 5 hooks, exactly 1 with is_selected=true (the first one)
- 10-12 hashtags
- Output ONLY the JSON, nothing else"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    result = parse_json_response(response.content[0].text)
    if not isinstance(result, dict):
        raise RuntimeError("Claude returned non-object JSON")

    # Validate required keys exist
    required = ["script", "hooks", "description", "hashtags", "editor_brief", "strategy"]
    for key in required:
        if key not in result:
            result[key] = "" if key != "hooks" and key != "hashtags" else []

    return result
