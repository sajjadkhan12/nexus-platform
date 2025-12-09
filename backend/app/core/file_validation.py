import re
from pathlib import Path
from typing import Tuple

# Try to import magic for MIME type detection (optional)
_WARNED_ABOUT_MAGIC = [False]  # Use list to allow modification

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    # Only warn once at module import time
    import warnings
    if not _WARNED_ABOUT_MAGIC[0]:
        warnings.warn(
            "python-magic not installed. File type validation will be limited to extensions only. "
            "Install with: pip install python-magic-bin (Windows) or python-magic (Linux/Mac)",
            UserWarning,
            stacklevel=2
        )
        _WARNED_ABOUT_MAGIC[0] = True

# Allowed file types for avatars
ALLOWED_IMAGE_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'
}

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

# Max file sizes (in bytes)
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB
MAX_PLUGIN_SIZE = 50 * 1024 * 1024  # 50MB

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other attacks
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = Path(filename).name
    
    # Remove any non-alphanumeric characters except dots, hyphens, underscores
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    
    # Prevent hidden files
    if filename.startswith('.'):
        filename = filename[1:]
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename

def validate_file_type(file_content: bytes, filename: str, allowed_types: set, allowed_extensions: set) -> Tuple[bool, str]:
    """
    Validate file type using both MIME type and extension
    
    Args:
        file_content: File content as bytes
        filename: Original filename
        allowed_types: Set of allowed MIME types
        allowed_extensions: Set of allowed file extensions
    
    Returns:
        (is_valid, error_message)
    """
    # Check extension
    file_ext = Path(filename).suffix.lower()
    if file_ext not in allowed_extensions:
        return False, f"File extension {file_ext} not allowed"
    
    # Check MIME type using python-magic if available
    if HAS_MAGIC:
        try:
            mime = magic.Magic(mime=True)
            detected_type = mime.from_buffer(file_content)
            
            if detected_type not in allowed_types:
                return False, f"File type {detected_type} not allowed. Expected: {', '.join(allowed_types)}"
        except Exception:
            # If magic fails, fall back to extension check only
            pass
    
    # Extension check is already done above
    return True, ""

def validate_file_size(file_size: int, max_size: int) -> Tuple[bool, str]:
    """
    Validate file size
    
    Args:
        file_size: Size of file in bytes
        max_size: Maximum allowed size in bytes
    
    Returns:
        (is_valid, error_message)
    """
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"File size exceeds maximum allowed size of {max_mb:.1f}MB"
    return True, ""

def validate_avatar_upload(file_content: bytes, filename: str, file_size: int) -> Tuple[bool, str]:
    """
    Validate avatar file upload
    
    Returns:
        (is_valid, error_message)
    """
    # Check size
    is_valid, error = validate_file_size(file_size, MAX_AVATAR_SIZE)
    if not is_valid:
        return False, error
    
    # Check type
    is_valid, error = validate_file_type(
        file_content, 
        filename, 
        ALLOWED_IMAGE_TYPES, 
        ALLOWED_IMAGE_EXTENSIONS
    )
    if not is_valid:
        return False, error
    
    return True, ""

def validate_plugin_upload(file_content: bytes, filename: str, file_size: int) -> Tuple[bool, str]:
    """
    Validate plugin ZIP file upload
    
    Returns:
        (is_valid, error_message)
    """
    # Check size
    is_valid, error = validate_file_size(file_size, MAX_PLUGIN_SIZE)
    if not is_valid:
        return False, error
    
    # Check extension
    if not filename.lower().endswith('.zip'):
        return False, "Only ZIP files are allowed"
    
    # Could add ZIP file validation here (check if it's a valid ZIP)
    # For now, the plugin validator will handle that
    
    return True, ""

