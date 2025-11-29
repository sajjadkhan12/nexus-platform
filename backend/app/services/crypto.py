"""Encryption service for sensitive data like cloud credentials"""
from cryptography.fernet import Fernet
from app.config import settings
import base64
import json

class CryptoService:
    """Service for encrypting and decrypting sensitive data"""
    
    def __init__(self):
        # In production, load this from environment or a secrets manager
        # For now, generate or use a fixed key (store in settings)
        if hasattr(settings, 'ENCRYPTION_KEY') and settings.ENCRYPTION_KEY:
            self.key = settings.ENCRYPTION_KEY.encode()
        else:
            # Generate a key - WARNING: This should be persistent in production
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
