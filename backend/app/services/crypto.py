"""Encryption service for sensitive data like cloud credentials"""
from cryptography.fernet import Fernet
from app.config import settings
import base64
import json

class CryptoService:
    """Service for encrypting and decrypting sensitive data"""
    
    def __init__(self):
        # In production, ENCRYPTION_KEY MUST be set in environment
        if hasattr(settings, 'ENCRYPTION_KEY') and settings.ENCRYPTION_KEY:
            try:
                self.key = settings.ENCRYPTION_KEY.encode()
                # Validate key format
                Fernet(self.key)  # Will raise ValueError if invalid
            except (ValueError, AttributeError) as e:
                raise ValueError(
                    "ENCRYPTION_KEY is invalid. It must be a valid Fernet key. "
                    "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                ) from e
        else:
            # In production, fail if key is not set
            import os
            if os.getenv("ENVIRONMENT", "").lower() == "production" or not settings.DEBUG:
                raise ValueError(
                    "ENCRYPTION_KEY must be set in production environment. "
                    "Cannot generate a new key as it would make existing encrypted data unreadable."
                )
            # Only allow key generation in development
            import warnings
            warnings.warn(
                "ENCRYPTION_KEY not set. Generating a new key. "
                "This key will be lost on restart and encrypted data will be unreadable. "
                "Set ENCRYPTION_KEY in .env for production.",
                UserWarning
            )
            self.key = Fernet.generate_key()
        
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: dict) -> str:
        """Encrypt a dictionary to a base64-encoded string"""
        json_str = json.dumps(data)
        encrypted = self.cipher.encrypt(json_str.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> dict:
        """Decrypt a base64-encoded string back to a dictionary"""
        encrypted = base64.b64decode(encrypted_data.encode())
        decrypted = self.cipher.decrypt(encrypted)
        return json.loads(decrypted.decode())

# Singleton instance
crypto_service = CryptoService()
