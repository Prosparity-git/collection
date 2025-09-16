import os
from typing import Optional

class Settings:
    # Database Configuration for Server
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "Prosapp_root#4312")
    db_host = os.getenv("DB_HOST", "13.203.110.46")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME", "prosparity_db_dev")

    # SQLAlchemy connection string
    DATABASE_URL: str = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "360"))
    
    # Security
    PASSWORD_MIN_LENGTH: int = 8
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "360"))
    
    # CORS
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000", 
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://0.0.0.0:3000",
        "http://0.0.0.0:5173",
        "http://*:3000",  # Allow any IP on port 3000
        "http://*:5173",  # Allow any IP on port 5173
        "*"  # Allow all origins for development
    ]

settings = Settings()

# Print database configuration for debugging (remove in production)
print("Database URL:", settings.DATABASE_URL)

