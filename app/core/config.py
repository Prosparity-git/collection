import os
from typing import Optional

class Settings:
    # Database Configuration for Server
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "Prosapp_root#4312")
    db_host = os.getenv("DB_HOST", "15.206.166.41")
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
        # Note: explicit origins only; no wildcard when allow_credentials=True
    ]
    
    # MSG91 Configuration
    MSG91_AUTH_KEY: str = os.getenv("MSG91_AUTH_KEY", "469204ALkC2wCpF68d26b7aP1")
    
    MSG91_OTP_LENGTH: int = int(os.getenv("MSG91_OTP_LENGTH", "4"))  # Changed to 4 digits
    MSG91_OTP_EXPIRE_MINUTES: int = int(os.getenv("MSG91_OTP_EXPIRE_MINUTES", "5"))
    
    # Redis Configuration (for OTP storage)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # AWS / S3 Configuration
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-south-1")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "")
    S3_PREFIX: str = os.getenv("S3_PREFIX", "field-visits/")
    PRESIGNED_TTL_SECONDS: int = int(os.getenv("PRESIGNED_TTL_SECONDS", "300"))
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "10"))
    CLOUDFRONT_URL: str = os.getenv("CLOUDFRONT_URL", "")

settings = Settings()

# Print database configuration for debugging (remove in production)
print("Database URL:", settings.DATABASE_URL)

