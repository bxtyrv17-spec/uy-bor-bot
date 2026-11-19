from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str = "sqlite+aiosqlite:///uy_bor.db"
    ADMIN_IDS: list[int] = []
    MAX_PHOTOS: int = 10
    MAX_LISTING_PER_USER: int = 5
    WEBAPP_URL: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
