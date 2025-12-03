"""
OIDC Provider Core Module

This module provides OIDC token generation and JWKS endpoint functionality.
It generates RSA keys for signing JWT tokens with proper OIDC claims.

Keys are persisted to disk to ensure consistency across multiple processes.
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import jwt  # PyJWT
from app.config import settings
from app.logger import logger

class OIDCProvider:
    """
    OIDC Provider that generates JWT tokens with OIDC claims
    and exposes JWKS endpoint for key verification.
    """
    
    def __init__(self, key_file: Optional[str] = None):
        self._private_key: Optional[rsa.RSAPrivateKey] = None
        self._public_key: Optional[rsa.RSAPublicKey] = None
        self._key_id: str = "oidc-key-1"
        self._jwks_cache: Optional[Dict[str, Any]] = None
        
        if key_file is None:
            storage_dir = Path(settings.PLUGINS_STORAGE_PATH).parent
            storage_dir.mkdir(parents=True, exist_ok=True)
            key_file = str(storage_dir / ".oidc_keys.json")
        
        self._key_file = key_file
        self._load_or_generate_keys()
    
    def _load_or_generate_keys(self):
        """Load existing keys from file or generate new ones"""
        if os.path.exists(self._key_file):
            try:
                with open(self._key_file, 'r') as f:
                    data = json.load(f)
                    self._key_id = data.get('kid', self._key_id)
                    private_pem = data['private_key'].encode('utf-8')
                    self._private_key = serialization.load_pem_private_key(
                        private_pem,
                        password=None,
                        backend=default_backend()
                    )
                    self._public_key = self._private_key.public_key()
            except Exception as e:
                logger.warning(f"Error loading keys, regenerating: {e}")
                self._generate_keys()
        else:
            self._generate_keys()

    def _generate_keys(self):
        """Generate new RSA key pair"""
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self._public_key = self._private_key.public_key()
        
        # Save to file
        private_pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        with open(self._key_file, 'w') as f:
            json.dump({
                'kid': self._key_id,
                'private_key': private_pem.decode('utf-8')
            }, f)

    def get_jwks(self) -> Dict[str, Any]:
        """Return JWKS (JSON Web Key Set)"""
        if self._jwks_cache:
            return self._jwks_cache
            
        public_numbers = self._public_key.public_numbers()
        
        # Convert to JWK format
        jwk = {
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "kid": self._key_id,
            "n": self._int_to_base64(public_numbers.n),
            "e": self._int_to_base64(public_numbers.e)
        }
        
        self._jwks_cache = {"keys": [jwk]}
        return self._jwks_cache

    def create_oidc_token(self, subject: str, audience: str, expires_in: int = 3600, claims: Dict[str, Any] = None) -> str:
        """
        Create a signed ID token
        
        Args:
            subject: The user ID (sub)
            audience: The audience (aud) - e.g. sts.amazonaws.com
            expires_in: Token validity in seconds
            claims: Additional claims
        """
        now = int(time.time())
        
        payload = {
            "iss": settings.OIDC_ISSUER,
            "sub": subject,
            "aud": audience,
            "iat": now,
            "exp": now + expires_in,
            "nbf": now,
            "jti": str(uuid.uuid4())
        }
        
        if claims:
            payload.update(claims)
            
        # Get private key in PEM format for pyjwt
        private_pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        token = jwt.encode(
            payload,
            private_pem,
            algorithm="RS256",
            headers={"kid": self._key_id}
        )
        
        return token

    @staticmethod
    def _int_to_base64(value: int) -> str:
        """Convert integer to base64url-encoded string"""
        import base64
        value_hex = format(value, 'x')
        # Ensure even length
        if len(value_hex) % 2 == 1:
            value_hex = '0' + value_hex
        value_bytes = bytes.fromhex(value_hex)
        encoded = base64.urlsafe_b64encode(value_bytes).rstrip(b'=')
        return encoded.decode('utf-8')

# Global instance
oidc_provider = OIDCProvider()
