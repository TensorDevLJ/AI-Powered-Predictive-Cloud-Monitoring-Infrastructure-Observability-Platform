"""
Configuration settings for the Cloud Monitoring System
"""
import logging
from pydantic_settings import BaseSettings
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_SECRET_KEY = "your-secret-key-change-this-in-production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Cloud Monitoring System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Database
    # Defaults to a local SQLite file so the app runs out-of-the-box with
    # zero external setup. Override via .env for MySQL/Postgres, e.g.:
    #   mysql+pymysql://user:password@localhost:3306/cloud_monitor
    #   postgresql://user:password@localhost:5432/dbname
    DATABASE_URL: str = "sqlite:///./monitoring.db"
    
    # Prometheus
    PROMETHEUS_URL: str = "http://prometheus:9090"
    
    # Grafana
    GRAFANA_URL: str = "http://grafana:3000"
    GRAFANA_API_KEY: Optional[str] = None
    
    # Alert Manager
    ALERTMANAGER_URL: str = "http://alertmanager:9093"
    
    # Email Alerts
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    ALERT_EMAIL_FROM: str = "alerts@monitoring.com"
    ALERT_EMAIL_TO: str = "admin@example.com"
    
    # Monitoring Thresholds
    CPU_THRESHOLD: float = 80.0
    MEMORY_THRESHOLD: float = 85.0
    DISK_THRESHOLD: float = 90.0
    
    # Metrics Collection
    METRICS_SCRAPE_INTERVAL: int = 15  # seconds
    METRICS_RETENTION_DAYS: int = 30
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

if settings.SECRET_KEY == DEFAULT_SECRET_KEY:
    logger.warning(
        "SECURITY WARNING: SECRET_KEY is using the default placeholder value. "
        "Set a unique SECRET_KEY in your .env file before deploying to production "
        "(anyone can forge JWT tokens otherwise). "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )
