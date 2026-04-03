from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"
    NOWPAYMENTS_API_KEY: str = ""
    NOWPAYMENTS_IPN_SECRET: str = ""
    USDT_WALLET_ADDRESS: str = ""
    YUKASSA_SHOP_ID: str = ""
    YUKASSA_SECRET_KEY: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TRIAL_ANALYSES_LIMIT: int = 5
    MAX_VIDEO_DURATION_SECONDS: int = 300

    class Config:
        env_file = ".env"

settings = Settings()
