"""
Configuration settings for Discord Scraper Dashboard
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://discord_user:discord_password@localhost:5432/discord_scraper"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Discord OAuth
    discord_client_id: Optional[str] = None
    discord_client_secret: Optional[str] = None
    discord_redirect_uri: str = "http://localhost:8000/api/v1/auth/discord/callback"
    
    # Discord Bot
    discord_bot_token: Optional[str] = None
    
    # JWT
    jwt_secret_key: str = "default-dev-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24 * 7  # 1 week
    
    # Frontend
    frontend_url: str = "http://localhost:3000"
    
    # Storage
    exports_dir: str = "./exports"
    store_message_content: bool = False  # Only store metadata by default
    
    # API
    api_v1_prefix: str = "/api/v1"
    
    # Anti-detection settings
    enable_anti_detection: bool = True
    anti_detection_fallback: bool = True
    http_client_rotation_enabled: bool = True
    http_client_rotation_interval: int = 100
    browser_profiles: str = "chrome_win,chrome_mac,firefox_win"
    enable_browser_automation: bool = True
    browser_automation_timeout: int = 30
    browser_automation_headless: bool = True
    browser_automation_max_concurrent: int = 2
    browser_automation_resource_limit_mb: int = 512
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()