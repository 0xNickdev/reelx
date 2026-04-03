# Deploy to Railway

## Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial REELX backend"
git remote add origin https://github.com/YOUR_USERNAME/reelx-backend.git
git push -u origin main
```

## Step 2 — Create Railway project
1. Go to railway.app → New Project → Deploy from GitHub
2. Select your reelx-backend repo
3. Railway will auto-detect Python and deploy

## Step 3 — Add Redis
1. In Railway project → Add Service → Redis
2. Copy REDIS_URL from Redis service variables

## Step 4 — Set Environment Variables
In Railway → Your service → Variables, add ALL from .env.example:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
SUPABASE_URL=https://gevnzvkanggjeaebiwdx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...  (get from Supabase Settings → API → service_role key)
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=generate-random-32-char-string
ENVIRONMENT=production
FRONTEND_URL=https://reelx.app
```

## Step 5 — Add Celery Worker service
1. In Railway → Add Service → GitHub Repo (same repo)
2. Set start command to: `celery -A app.services.celery_app worker --loglevel=info --concurrency=2`
3. This is your separate worker service

## Step 6 — Run DB migrations
1. Go to Supabase → SQL Editor
2. Paste contents of supabase_schema.sql
3. Run it

## Step 7 — Get your API URL
Railway gives you a URL like: https://reelx-backend-production.up.railway.app
This goes into FRONTEND_URL of your frontend.

## Step 8 — Update frontend
In shared.js add:
```javascript
const API_URL = 'https://reelx-backend-production.up.railway.app';
```
