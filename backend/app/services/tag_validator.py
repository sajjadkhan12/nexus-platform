"""
Tag validation service for deployment tags
Enforces required tags and format rules
"""
import re
from typing import Dict, Tuple, Optional

# Required tags for all deployments
REQUIRED_TAGS = {
    "team": "Team name (e.g., backend, frontend, data, platform)",
    "owner": "Owner email or username responsible for this deployment",
    "purpose": "Purpose of deployment (e.g., api, worker, storage, database)"
}

# Tag key must be lowercase alphanumeric with hyphens only
TAG_KEY_PATTERN = re.compile(r'^[a-z0-9-]+$')

# Maximum length for tag values
TAG_VALUE_MAX_LENGTH = 255

# Reserved tag prefixes (system-managed tags)
RESERVED_PREFIXES = ['system-', 'Foundry-', 'internal-']


def validate_tags(tags: Dict[str, str], environment: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that all required tags are present and correctly formatted.
    
    Args:
        tags: Dictionary of tag key-value pairs
        environment: Deployment environment (development, staging, production)
        
    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is None
        If invalid, error_message contains the validation error
    """
    # 1. Check required tags are present
    for key, description in REQUIRED_TAGS.items():
        if key not in tags:
            return False, f"Missing required tag '{key}': {description}"
        
        if not tags[key] or not tags[key].strip():
            return False, f"Required tag '{key}' cannot be empty. {description}"
    
    # 2. Validate tag key format
    for key in tags.keys():
        # Check for reserved prefixes
        for prefix in RESERVED_PREFIXES:
            if key.startswith(prefix):
                return False, f"Tag key '{key}' uses reserved prefix '{prefix}'. Reserved prefixes: {', '.join(RESERVED_PREFIXES)}"
        
        # Check format: lowercase alphanumeric with hyphens
        if not TAG_KEY_PATTERN.match(key):
            return False, f"Tag key '{key}' is invalid. Must be lowercase alphanumeric characters and hyphens only (e.g., 'cost-center', 'team-name')"
    
    # 3. Validate tag value length
    for key, value in tags.items():
        if len(value) > TAG_VALUE_MAX_LENGTH:
            return False, f"Tag value for '{key}' exceeds maximum length of {TAG_VALUE_MAX_LENGTH} characters (current: {len(value)})"
    
    # 4. Additional validation for production environments
    if environment == "production":
        # Production deployments should have cost tracking
        if 'cost-center' not in tags and not tags.get('project-code'):
            return False, "Production deployments should have either 'cost-center' or 'project-code' tag for cost tracking"
    
    return True, None


def get_required_tags() -> Dict[str, str]:
    """Return the dictionary of required tags and their descriptions"""
    return REQUIRED_TAGS.copy()


def validate_tag_key(key: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a single tag key format.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check reserved prefixes
    for prefix in RESERVED_PREFIXES:
        if key.startswith(prefix):
            return False, f"Tag key uses reserved prefix '{prefix}'"
    
    # Check format
    if not TAG_KEY_PATTERN.match(key):
        return False, "Tag key must be lowercase alphanumeric characters and hyphens only"
    
    return True, None


def validate_tag_value(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a single tag value.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(value) > TAG_VALUE_MAX_LENGTH:
        return False, f"Tag value exceeds maximum length of {TAG_VALUE_MAX_LENGTH} characters"
    
    if not value or not value.strip():
        return False, "Tag value cannot be empty"
    
    return True, None
