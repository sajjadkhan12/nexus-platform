from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "DevPlatform IDP"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Admin credentials
    ADMIN_EMAIL: str
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str
    
    # Plugin system
    PLUGINS_STORAGE_PATH: str = "./storage/plugins"
    ENCRYPTION_KEY: str = "" 
    PULUMI_CONFIG_PASSPHRASE: str = "default-passphrase"  # SECURITY: Change this in production!
    PULUMI_ACCESS_TOKEN: str = ""  # Pulumi Cloud access token (optional, for cloud backend)
    
    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    BACKEND_CORS_ORIGINS: List[str] = []
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse CORS_ORIGINS string into list if BACKEND_CORS_ORIGINS is empty
        if not self.BACKEND_CORS_ORIGINS and self.CORS_ORIGINS:
            self.BACKEND_CORS_ORIGINS = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    # OIDC Provider Configuration
    OIDC_ISSUER: str = ""  # Set in .env, e.g., https://nexus.nexgendevworks.com
    
    @field_validator("OIDC_ISSUER")
    def validate_oidc_issuer(cls, v: str) -> str:
        if not v or not v.strip():
            # In development we might want to allow empty but user requested configurable issuer
            # raising error enforces it's set
            pass 
        return v.rstrip('/')

    # AWS Configuration
    AWS_ROLE_ARN: str = "" # The role the IDP assumes for testing
    AWS_REGION: str = "us-east-1"
    
    # GCP Configuration
    GCP_WORKLOAD_IDENTITY_POOL_ID: str = ""
    GCP_WORKLOAD_IDENTITY_PROVIDER_ID: str = ""
    GCP_SERVICE_ACCOUNT_EMAIL: str = ""
    GCP_PROJECT_ID: str = ""  # Project ID for API calls
    GCP_PROJECT_NUMBER: str = ""  # Project Number for Workload Identity audience (required)
    
    # Azure Configuration
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = "" # Optional if using certificate but useful for testing
    
    class Config:
        # Look for .env file in the backend directory (parent of app/)
        env_file = str(Path(__file__).parent.parent / ".env")
        case_sensitive = True

settings = Settings()
