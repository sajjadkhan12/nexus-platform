"""
Audit logging middleware to automatically log all write operations
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Optional, Dict, Any
from uuid import UUID
import json
import time
from app.logger import logger
from app.database import AsyncSessionLocal
from app.services.audit_service import log_audit_event
from app.api.deps import get_current_user
from jose import JWTError, jwt
from app.config import settings


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically log all write operations (POST, PUT, PATCH, DELETE)
    to the audit log table.
    """
    
    # Paths to skip audit logging
    SKIP_PATHS = [
        "/static/",
        "/storage/",
        "/.well-known/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/api/v1/auth/refresh",  # Don't log token refreshes
    ]
    
    # Methods that are considered write operations
    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    
    async def dispatch(self, request: Request, call_next):
        # Skip logging for certain paths
        if any(request.url.path.startswith(path) for path in self.SKIP_PATHS):
            return await call_next(request)
        
        # Only log write operations
        if request.method not in self.WRITE_METHODS:
            return await call_next(request)
        
        # Extract request data
        user_id: Optional[UUID] = None
        ip_address: Optional[str] = None
        request_body: Optional[Dict[str, Any]] = None
        resource_type: Optional[str] = None
        resource_id: Optional[str] = None
        action: str = request.method.lower()
        status = "success"
        
        # Get IP address
        if request.client:
            ip_address = request.client.host
            # Check for forwarded IP (from proxy/load balancer)
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                ip_address = forwarded_for.split(",")[0].strip()
        
        # Try to extract user from token
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                    user_id_str = payload.get("sub")
                    token_type = payload.get("type")
                    
                    if user_id_str and token_type == "access":
                        user_id = UUID(user_id_str)
                except (JWTError, ValueError):
                    # Invalid token, continue without user_id
                    pass
        except Exception:
            # Failed to extract user, continue without user_id
            pass
        
        # Extract request body
        request_body: Optional[Dict[str, Any]] = None
        content_type = request.headers.get("content-type", "").lower()
        
        try:
            if request.method in {"POST", "PUT", "PATCH"}:
                # For multipart/form-data (file uploads), don't read the body
                # as it will consume the stream and break the endpoint handler
                if "multipart/form-data" in content_type:
                    # Just log metadata about the file upload
                    # Extract filename from Content-Disposition header if available
                    content_disposition = request.headers.get("content-disposition", "")
                    filename = None
                    if "filename=" in content_disposition:
                        try:
                            filename = content_disposition.split("filename=")[1].strip('"\'')
                        except Exception:
                            pass
                    
                    request_body = {
                        "content_type": "multipart/form-data",
                        "note": "file_upload",
                        "filename": filename if filename else "unknown"
                    }
                elif "application/json" in content_type:
                    # Read JSON body - this is safe for JSON requests
                    body = await request.body()
                    if body:
                        try:
                            request_body = json.loads(body.decode("utf-8"))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            request_body = {"raw_body": body.decode("utf-8", errors="ignore")[:1000]}
                elif "application/x-www-form-urlencoded" in content_type:
                    # For URL-encoded forms, we can try to read but be careful
                    # Don't read if it might interfere with the endpoint
                    request_body = {"content_type": "application/x-www-form-urlencoded", "note": "form_data"}
                else:
                    # Other content types - don't read to avoid consuming stream
                    request_body = {"content_type": content_type, "note": "binary_or_unknown"}
        except Exception as e:
            logger.debug(f"Failed to read request body: {e}")
            request_body = None
        
        # Determine resource type and ID from path
        path_parts = request.url.path.strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] == "api" and path_parts[1] == "v1":
            # Extract resource type from path (e.g., /api/v1/users/{id} -> "users")
            if len(path_parts) >= 3:
                resource_type = path_parts[2]
                # Try to extract resource ID from path
                if len(path_parts) >= 4:
                    try:
                        resource_id = UUID(path_parts[3])
                    except (ValueError, IndexError):
                        # Not a UUID, might be a different identifier
                        resource_id_str = path_parts[3] if len(path_parts) > 3 else None
                        if resource_id_str:
                            resource_id = resource_id_str
            elif len(path_parts) >= 2:
                # Handle non-v1 paths (e.g., /api/provision)
                resource_type = path_parts[1] if len(path_parts) > 1 else None
        
        # Map HTTP methods to actions
        action_map = {
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete"
        }
        action = action_map.get(request.method, request.method.lower())
        
        # Special handling for specific endpoints
        if resource_type == "users" and "password" in request.url.path:
            action = "password_change"
        elif resource_type == "users" and "avatar" in request.url.path:
            action = "avatar_upload"
        elif resource_type == "notifications" and "read" in request.url.path:
            action = "mark_read"
        elif resource_type == "plugins" and "upload" in request.url.path:
            action = "upload"
        elif resource_type == "plugins" and "lock" in request.url.path:
            action = "lock" if action == "update" else action
        elif resource_type == "plugins" and "unlock" in request.url.path:
            action = "unlock" if action == "update" else action
        elif resource_type == "plugins" and "access" in request.url.path:
            if "request" in request.url.path:
                action = "access_request"
            elif "grant" in request.url.path:
                action = "access_grant"
        elif resource_type == "provision":
            action = "provision"
        elif resource_type == "jobs" and request.method == "DELETE":
            action = "job_delete"
        
        # Prepare details object
        details: Dict[str, Any] = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "request_body": request_body,
        }
        
        # Process request and capture response
        start_time = time.time()
        response: Response = None
        
        try:
            response = await call_next(request)
            
            # Determine status based on response code
            if response.status_code >= 400:
                status = "failure"
            else:
                status = "success"
            
            # Add response info to details
            details["response_status"] = response.status_code
            details["duration_ms"] = round((time.time() - start_time) * 1000, 2)
            
        except HTTPException as e:
            # HTTP exceptions are expected, log them
            status = "failure"
            details["response_status"] = e.status_code
            details["error"] = e.detail
            details["duration_ms"] = round((time.time() - start_time) * 1000, 2)
            # Re-raise to let FastAPI handle it
            raise
        except Exception as e:
            # Unexpected exceptions
            status = "failure"
            details["response_status"] = 500
            details["error"] = str(e)
            details["duration_ms"] = round((time.time() - start_time) * 1000, 2)
            # Re-raise to let FastAPI handle it
            raise
        
        # Log the audit event asynchronously (don't block the response)
        # Use a new database session for logging
        try:
            async with AsyncSessionLocal() as db:
                # Convert resource_id to UUID if it's a valid UUID string
                resource_uuid = None
                if resource_id:
                    try:
                        if isinstance(resource_id, str) and len(resource_id) == 36:
                            resource_uuid = UUID(resource_id)
                        elif isinstance(resource_id, UUID):
                            resource_uuid = resource_id
                    except (ValueError, AttributeError):
                        # Not a valid UUID, store as string in details
                        details["resource_id_str"] = str(resource_id)
                
                # Ensure we have at least basic details
                if not details:
                    details = {}
                
                # Add request metadata if not already present
                if "method" not in details:
                    details["method"] = request.method
                if "path" not in details:
                    details["path"] = request.url.path
                
                await log_audit_event(
                    db=db,
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_uuid,
                    details=details,
                    ip_address=ip_address,
                    status=status
                )
        except Exception as e:
            # Log error but don't break the request
            logger.error(f"Failed to log audit event for {request.method} {request.url.path}: {e}", exc_info=True)
        
        return response

