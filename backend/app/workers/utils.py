"""Utility functions for workers"""


def categorize_error(error_msg: str) -> str:
    """
    Categorize error messages into error states for better tracking and debugging.
    """
    error_lower = error_msg.lower()
    
    if "credential" in error_lower or "authentication" in error_lower or "oidc" in error_lower or "token" in error_lower:
        return "credential_error"
    elif "pulumi" in error_lower or "stack" in error_lower or "preview" in error_lower:
        return "pulumi_error"
    elif "network" in error_lower or "connection" in error_lower or "timeout" in error_lower:
        return "network_error"
    elif "git" in error_lower or "repository" in error_lower or "branch" in error_lower:
        return "git_error"
    elif "validation" in error_lower or "invalid" in error_lower or "missing" in error_lower:
        return "validation_error"
    elif "permission" in error_lower or "forbidden" in error_lower or "access" in error_lower:
        return "permission_error"
    elif "quota" in error_lower or "limit" in error_lower or "rate" in error_lower:
        return "quota_error"
    else:
        return "unknown_error"

