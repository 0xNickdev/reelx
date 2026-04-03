# REELX Backend

## Stack
- FastAPI + Uvicorn
- Celery + Redis (task queue)
- Supabase (PostgreSQL + Auth)
- Claude API (vision + script generation)
- OpenAI Whisper (transcription)
- yt-dlp + ffmpeg (video download + frames)

## Local Setup

```bash
# 1. Clone and enter
cd reelx-backend

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env
# Fill in your keys in .env

# 5. Run Redis (Docker)
docker run -d -p 6379:6379 redis:alpine

# 6. Run API server
uvicorn main:app --reload --port 8000

# 7. Run Celery worker (separate terminal)
celery -A app.services.celery_app worker --loglevel=info

# 8. Open API docs
# http://localhost:8000/docs
```

## Deploy to Railway

See DEPLOY.md
