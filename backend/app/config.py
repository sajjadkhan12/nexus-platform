from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, AnyHttpUrl
from typing import List, Union

class Settings(BaseSettings):
    PROJECT_NAME: str = "DevPlatform IDP"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Admin credentials (from .env)
    ADMIN_EMAIL: str
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str
    # Plugin system
    PLUGINS_STORAGE_PATH: str = "./storage/plugins"
    ENCRYPTION_KEY: str = ""  # Leave empty to auto-generate (development only)
    
    # Pulumi configuration
    PULUMI_CONFIG_PASSPHRASE: str = "default-passphrase"  # Change in production!
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    BACKEND_CORS_ORIGINS: List[str] = []
    
    # OIDC Provider Configuration
    # Set this in .env file - must be HTTPS for production (e.g., https://yourdomain.com)
    # This is the public URL where your OIDC provider is accessible
    OIDC_ISSUER: str = ""  # Your platform's OIDC issuer URL (REQUIRED - set in .env)
    
    @field_validator("OIDC_ISSUER")
    def validate_oidc_issuer(cls, v: str) -> str:
        """Validate that OIDC_ISSUER is set"""
        if not v or not v.strip():
            raise ValueError(
                "OIDC_ISSUER must be set in .env file. "
                "Example: OIDC_ISSUER=https://yourdomain.com"
            )
        # Ensure it doesn't end with a slash
        v = v.rstrip('/')
        # Warn if using HTTP in production (but allow it for development)
        if v.startswith("http://") and not v.startswith("http://localhost"):
            import warnings
            warnings.warn(
                "OIDC_ISSUER uses HTTP. Use HTTPS for production!",
                UserWarning
            )
        return v
    
    # AWS Workload Identity Federation
    AWS_ROLE_ARN: str = ""  # ARN of the IAM role to assume (e.g., arn:aws:iam::123456789012:role/MyRole)
    
    # GCP Workload Identity Federation
    GCP_STS_ENDPOINT: str = "https://sts.googleapis.com/v1/token"  # GCP STS endpoint
    GCP_SERVICE_ACCOUNT_EMAIL: str = ""  # Service account to impersonate (e.g., my-sa@project.iam.gserviceaccount.com)
    GCP_WORKLOAD_IDENTITY_POOL_ID: str = ""  # Workload Identity Pool ID
    GCP_WORKLOAD_IDENTITY_PROVIDER_ID: str = ""  # Workload Identity Provider ID
    GCP_PROJECT_NUMBER: str = ""  # GCP Project Number
    
    # Azure Federated Identity Credential
    AZURE_TENANT_ID: str = ""  # Azure AD Tenant ID
    AZURE_CLIENT_ID: str = ""  # Azure App Registration Client ID
    AZURE_TOKEN_ENDPOINT: str = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"  # Azure token endpoint template

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]], info) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        
        # Fallback to using CORS_ORIGINS if BACKEND_CORS_ORIGINS is not explicitly set
        # However, field_validator runs on the field itself. 
        # We can use a model_validator or just set it in __init__? 
        # Easier: just use a computed field or property, but main.py uses settings.BACKEND_CORS_ORIGINS
        
        return []

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.BACKEND_CORS_ORIGINS and self.CORS_ORIGINS:
            self.BACKEND_CORS_ORIGINS = [i.strip() for i in self.CORS_ORIGINS.split(",")]

settings = Settings()
