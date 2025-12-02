"""
OIDC Provider Core Module

This module provides OIDC token generation and JWKS endpoint functionality.
It generates RSA keys for signing JWT tokens with proper OIDC claims.

Keys are persisted to disk to ensure consistency across multiple processes
(main app and Celery workers).
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import jwt  # PyJWT
from app.config import settings


class OIDCProvider:
    """
    OIDC Provider that generates JWT tokens with OIDC claims
    and exposes JWKS endpoint for key verification.
    
    Keys are persisted to ensure consistency across processes.
    """
    
    def __init__(self, key_file: Optional[str] = None):
        """
        Initialize the OIDC provider with RSA key pair.
        
        Args:
            key_file: Path to store/load RSA keys. Defaults to .oidc_keys.json in storage dir
        """
        self._private_key: Optional[rsa.RSAPrivateKey] = None
        self._public_key: Optional[rsa.RSAPublicKey] = None
        self._key_id: str = "oidc-key-1"
        self._jwks_cache: Optional[Dict[str, Any]] = None  # Cache JWKS for performance
        
        # Determine key file path
        if key_file is None:
            # Use parent directory of plugins storage
            storage_dir = Path(settings.PLUGINS_STORAGE_PATH).parent
            storage_dir.mkdir(parents=True, exist_ok=True)
            key_file = str(storage_dir / ".oidc_keys.json")
        
        self._key_file = key_file
        
        # Load or generate keys
        self._load_or_generate_keys()
    
    def _load_or_generate_keys(self):
        """Load existing keys from file or generate new ones"""
        if os.path.exists(self._key_file):
            try:
                self._load_keys_from_file()
                print(f"[OIDC] Loaded existing RSA keys from {self._key_file}")
                return
            except Exception as e:
                print(f"[OIDC] Failed to load keys from file: {e}. Generating new keys...")
        
        # Generate new keys if file doesn't exist or loading failed
        self._generate_keys()
        self._save_keys_to_file()
        print(f"[OIDC] Generated and saved new RSA keys to {self._key_file}")
    
    def _generate_keys(self):
        """Generate RSA key pair for signing JWT tokens"""
        # Generate 2048-bit RSA key pair
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self._public_key = self._private_key.public_key()
    
    def _save_keys_to_file(self):
        """Save RSA keys to file in PEM format"""
        private_pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        key_data = {
            "private_key": private_pem,
            "public_key": public_pem,
            "key_id": self._key_id
        }
        
        with open(self._key_file, 'w') as f:
            json.dump(key_data, f, indent=2)
        
        # Set restrictive permissions (owner read/write only)
        os.chmod(self._key_file, 0o600)
    
    def _load_keys_from_file(self):
        """Load RSA keys from file"""
        with open(self._key_file, 'r') as f:
            key_data = json.load(f)
        
        # Load private key
        private_pem = key_data["private_key"].encode('utf-8')
        self._private_key = serialization.load_pem_private_key(
            private_pem,
            password=None,
            backend=default_backend()
        )
        
        # Load public key
        public_pem = key_data["public_key"].encode('utf-8')
        self._public_key = serialization.load_pem_public_key(
            public_pem,
            backend=default_backend()
        )
        
        # Load key ID
        self._key_id = key_data.get("key_id", "oidc-key-1")
    
    def get_private_key_pem(self) -> str:
        """Get private key in PEM format"""
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
    
    def get_public_key_pem(self) -> str:
        """Get public key in PEM format"""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    
    def get_jwks(self) -> Dict[str, Any]:
        """
        Generate JWKS (JSON Web Key Set) for the public key.
        This is used by cloud providers to verify tokens.
        
        Returns cached JWKS for performance (keys don't change during runtime).
        """
        # Return cached JWKS if available (keys don't change)
        if self._jwks_cache is not None:
            return self._jwks_cache
        
        # Get public key numbers
        public_numbers = self._public_key.public_numbers()
        
        # Convert to JWK format
        # RSA public key in JWK format requires: n (modulus) and e (exponent)
        import base64
        
        def int_to_base64url(value: int) -> str:
            """Convert integer to base64url-encoded string"""
            # Convert to bytes (big-endian)
            value_bytes = value.to_bytes((value.bit_length() + 7) // 8, 'big')
            # Base64 encode
            encoded = base64.urlsafe_b64encode(value_bytes)
            # Remove padding
            return encoded.decode('utf-8').rstrip('=')
        
        jwk = {
            "kty": "RSA",
            "kid": self._key_id,
            "use": "sig",
            "alg": "RS256",
            "n": int_to_base64url(public_numbers.n),
            "e": int_to_base64url(public_numbers.e)
        }
        
        jwks = {
            "keys": [jwk]
        }
        
        # Cache the result
        self._jwks_cache = jwks
        
        return jwks
    
    def create_oidc_token(
        self,
        subject: str,
        audience: str,
        issuer: Optional[str] = None,
        expires_in: int = 3600,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create an OIDC-compliant JWT token.
        
        Args:
            subject: The subject (sub) claim - typically user ID
            audience: The audience (aud) claim - who the token is intended for
            issuer: The issuer (iss) claim - defaults to OIDC_ISSUER from settings
            expires_in: Token expiration time in seconds (default: 1 hour)
            additional_claims: Additional claims to include in the token
        
        Returns:
            Encoded JWT token string
        """
        now = datetime.utcnow()
        
        # Build token claims
        claims = {
            "iss": issuer or settings.OIDC_ISSUER,  # Issuer
            "sub": subject,  # Subject (user identifier)
            "aud": audience,  # Audience (who the token is for)
            "iat": int(now.timestamp()),  # Issued at
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),  # Expiration
        }
        
        # Add additional claims if provided
        if additional_claims:
            claims.update(additional_claims)
        
        # Sign token with RSA private key
        token = jwt.encode(
            claims,
            self.get_private_key_pem(),
            algorithm="RS256",
            headers={"kid": self._key_id}
        )
        
        return token


# Global OIDC provider instance
oidc_provider = OIDCProvider()

