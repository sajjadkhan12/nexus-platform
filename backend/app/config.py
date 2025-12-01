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
