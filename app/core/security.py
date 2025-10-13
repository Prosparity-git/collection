from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
import secrets

# Password hashing context - using bcrypt for enhanced security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """
    Verify JWT token and return user ID
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except JWTError:
        return None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plain password against hashed password
    """
    # Handle None values
    if plain_password is None or hashed_password is None:
        return False
    
    # Convert to string if not already
    plain_password_str = str(plain_password)
    
    # Truncate password to 72 characters to avoid bcrypt limitation
    truncated_password = plain_password_str[:72]
    
    try:
        return pwd_context.verify(truncated_password, hashed_password)
    except Exception as e:
        # Log the error for debugging but don't expose it
        print(f"Password verification error: {str(e)}")
        return False

def get_password_hash(password: str) -> str:
    """
    Hash password using bcrypt
    """
    # Ensure password is not None and is a string
    if password is None:
        raise ValueError("Password cannot be None")
    
    # Convert to string if not already
    password_str = str(password)
    
    # Truncate to 72 characters to avoid bcrypt limitation
    truncated_password = password_str[:72]
    
    try:
        return pwd_context.hash(truncated_password)
    except Exception as e:
        raise ValueError(f"Failed to hash password: {str(e)}") 

def generate_secure_token() -> str:
    """
    Generate secure random token for password reset
    """
    return secrets.token_urlsafe(32) 