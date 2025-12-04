"""
Security middleware and utilities
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
from typing import Dict, Tuple
from app.config import settings
from app.logger import logger

# Try to use Redis for rate limiting, fallback to in-memory
try:
    from app.core.redis_client import RedisClient
    _use_redis = True
except Exception:
    _use_redis = False
    from collections import defaultdict
    _rate_limit_store: Dict[str, list] = defaultdict(list)
    logger.warning("Redis not available for rate limiting, using in-memory storage")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy
        # Allow same-origin and API calls
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # unsafe-inline/eval for dev - restrict in prod
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' " + (settings.OIDC_ISSUER if settings.OIDC_ISSUER else "") + "; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # HSTS (only if HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware"""
    
    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for certain paths
        skip_paths = [
            "/static/",
            "/storage/",
            "/.well-known/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
        ]
        
        if any(request.url.path.startswith(path) for path in skip_paths):
            response = await call_next(request)
            return response
        
        # Get client identifier (IP address or user ID if authenticated)
        client_id = request.client.host if request.client else "unknown"
        
        # Check rate limits
        now = time.time()
        minute_key = f"ratelimit:{client_id}:minute"
        hour_key = f"ratelimit:{client_id}:hour"
        
        use_redis_for_this_request = _use_redis
        
        if _use_redis:
            # Use Redis for rate limiting
            try:
                redis_client = RedisClient.get_instance()
                
                # Get current counts
                minute_count = await redis_client.get(minute_key)
                hour_count = await redis_client.get(hour_key)
                
                minute_count = int(minute_count) if minute_count else 0
                hour_count = int(hour_count) if hour_count else 0
                
                # Check limits
                if minute_count >= self.requests_per_minute:
                    logger.warning(f"Rate limit exceeded for {client_id}: {minute_count} requests/minute")
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded. Please try again later."}
                    )
                
                if hour_count >= self.requests_per_hour:
                    logger.warning(f"Hourly rate limit exceeded for {client_id}: {hour_count} requests/hour")
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Hourly rate limit exceeded. Please try again later."}
                    )
                
                # Increment counters with expiration (async operations)
                await redis_client.incr(minute_key)
                await redis_client.expire(minute_key, 60)
                await redis_client.incr(hour_key)
                await redis_client.expire(hour_key, 3600)
            except Exception as e:
                logger.error(f"Redis rate limiting error: {e}, falling back to in-memory")
                # Fall through to in-memory logic
                use_redis_for_this_request = False
        
        if not use_redis_for_this_request:
            # Fallback to in-memory rate limiting
            # Clean old entries
            _rate_limit_store[minute_key] = [
                ts for ts in _rate_limit_store[minute_key] if now - ts < 60
            ]
            _rate_limit_store[hour_key] = [
                ts for ts in _rate_limit_store[hour_key] if now - ts < 3600
            ]
            
            # Check limits
            if len(_rate_limit_store[minute_key]) >= self.requests_per_minute:
                logger.warning(f"Rate limit exceeded for {client_id}: {len(_rate_limit_store[minute_key])} requests/minute")
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please try again later."}
                )
            
            if len(_rate_limit_store[hour_key]) >= self.requests_per_hour:
                logger.warning(f"Hourly rate limit exceeded for {client_id}: {len(_rate_limit_store[hour_key])} requests/hour")
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Hourly rate limit exceeded. Please try again later."}
                )
            
            # Record request
            _rate_limit_store[minute_key].append(now)
            _rate_limit_store[hour_key].append(now)
        
        response = await call_next(request)
        return response

def sanitize_error_message(error: Exception, is_production: bool = not settings.DEBUG) -> str:
    """
    Sanitize error messages to prevent information disclosure
    
    Args:
        error: The exception that occurred
        is_production: Whether we're in production mode
    
    Returns:
        Safe error message for client
    """
    if is_production:
        # In production, return generic messages
        error_type = type(error).__name__
        
        if "database" in str(error).lower() or "sql" in str(error).lower():
            return "Database error occurred"
        elif "permission" in str(error).lower() or "forbidden" in str(error).lower():
            return "Permission denied"
        elif "not found" in str(error).lower():
            return "Resource not found"
        elif "validation" in str(error).lower():
            return "Invalid input provided"
        else:
            return "An error occurred processing your request"
    else:
        # In development, return full error
        return str(error)

