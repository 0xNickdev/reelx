from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import analyze, auth, settings_api, payments, trends, admin

app = FastAPI(
    title="REELX API",
    description="Backend for REELX viral content analysis platform",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:8080",
        "https://reelx.app",
        "https://www.reelx.app",
        "*",  # Remove in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(analyze.router)
app.include_router(settings_api.router)
app.include_router(payments.router)
app.include_router(trends.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    return {"status": "ok", "service": "REELX API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
