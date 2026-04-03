from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime
from enum import Enum

class PipelineStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    EXTRACTING_FRAMES = "extracting_frames"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    DONE = "done"
    FAILED = "failed"

class AnalyzeRequest(BaseModel):
    url: str
    user_id: str

class FrameAnalysis(BaseModel):
    timestamp: str
    frame_type: str  # "talking_head" | "cutaway"
    description: str
    frame_number: int

class HookVariant(BaseModel):
    number: int
    text: str
    explanation: str
    tag: str  # "strong" | "best" | "alternative"
    timing_seconds: float
    is_selected: bool = False

class AnalysisResult(BaseModel):
    job_id: str
    status: PipelineStatus
    video_meta: Optional[dict] = None
    script: Optional[str] = None
    hooks: Optional[List[HookVariant]] = None
    description: Optional[str] = None
    hashtags: Optional[List[str]] = None
    editor_brief: Optional[str] = None
    strategy: Optional[str] = None
    frames: Optional[List[FrameAnalysis]] = None
    transcript: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: PipelineStatus
    progress_percent: int
    current_step: str
    result: Optional[AnalysisResult] = None
    error: Optional[str] = None

class UserSettings(BaseModel):
    user_id: str
    language: str = "ru"
    about_me: str = ""
    tone: str = "conversational"
    script_ending: str = "Подписывайся, чтобы не пропустить следующее."
    description_ending: str = ""
    stop_words: str = ""
    video_format: str = "head_visual"
    interests: List[str] = []
    telegram_id: Optional[str] = None
    trend_notifications: bool = False
