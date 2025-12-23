"""Security utilities - backward compatibility layer"""
# Import from service for backward compatibility
from app.services.security_service import (
    validate_password_strength,
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    security_service
)

# Re-export for backward compatibility
__all__ = [
    'validate_password_strength',
    'verify_password',
    'get_password_hash',
    'create_access_token',
    'create_refresh_token',
    'decode_token',
    'security_service'
]
