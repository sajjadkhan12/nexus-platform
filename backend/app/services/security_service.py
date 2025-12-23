"""Security service for password and token management"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import bcrypt
import re
from jose import JWTError, jwt
from app.config import settings


class SecurityService:
    """Service for password hashing, validation, and JWT token management"""
    
    def __init__(self, secret_key: str = None, algorithm: str = None, 
                 access_token_expire_minutes: int = None,
                 refresh_token_expire_days: int = None):
        self.secret_key = secret_key or settings.SECRET_KEY
        self.algorithm = algorithm or settings.ALGORITHM
        self.access_token_expire_minutes = access_token_expire_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = refresh_token_expire_days or settings.REFRESH_TOKEN_EXPIRE_DAYS
    
    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """
        Validate password strength.
        
        Requirements:
        - Minimum 12 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 12:
            return False, "Password must be at least 12 characters long"
        
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            return False, "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)"
        
        # Check against common weak passwords
        common_passwords = [
            "password", "password123", "12345678", "qwerty", "abc123",
            "letmein", "welcome", "monkey", "dragon", "master"
        ]
        if password.lower() in common_passwords:
            return False, "Password is too common. Please choose a more unique password"
        
        return True, ""
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: dict) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def decode_token(self, token: str) -> dict:
        """Decode and verify a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None


# Singleton instance
security_service = SecurityService()

# Backward compatibility: Export functions that delegate to the service
def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Backward compatibility wrapper"""
    return security_service.validate_password_strength(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Backward compatibility wrapper"""
    return security_service.verify_password(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Backward compatibility wrapper"""
    return security_service.hash_password(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Backward compatibility wrapper"""
    return security_service.create_access_token(data, expires_delta)

def create_refresh_token(data: dict) -> str:
    """Backward compatibility wrapper"""
    return security_service.create_refresh_token(data)

def decode_token(token: str) -> dict:
    """Backward compatibility wrapper"""
    return security_service.decode_token(token)

