"""AI Cost Monitor — app 配置（环境变量驱动）"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "ai-cost-monitor"
    ENV: str = "dev"
    DATABASE_URL: str = "postgresql+asyncpg://acm:acm@localhost:5432/acm"
    JWT_SECRET: str = "change-me"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7

    class Config:
        env_file = ".env"


settings = Settings()
