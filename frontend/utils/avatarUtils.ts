import { API_URL } from '../constants/api';

/**
 * Validates if an avatar URL is valid and non-empty
 */
export function isValidAvatarUrl(url: string | null | undefined): boolean {
    if (!url || typeof url !== 'string' || url.trim() === '') {
        return false;
    }
    
    // Reject invalid data URLs
    if (url.startsWith('data:') && (url === 'data:;base64,=' || url.includes('data:;base64,='))) {
        return false;
    }
    
    // Reject empty or malformed URLs
    if (url === 'null' || url === 'undefined' || url === 'false') {
        return false;
    }
    
    return true;
}

/**
 * Gets a valid avatar URL, constructing it if needed
 */
export function getAvatarUrl(avatarUrl: string | null | undefined): string | null {
    if (!isValidAvatarUrl(avatarUrl)) {
        return null;
    }
    
    // If it's already a full URL (http/https), return as is
    if (avatarUrl.startsWith('http://') || avatarUrl.startsWith('https://')) {
        return avatarUrl;
    }
    
    // If it's a data URL, return as is (for previews)
    if (avatarUrl.startsWith('data:')) {
        return avatarUrl;
    }
    
    // Otherwise, construct the full URL
    return `${API_URL}${avatarUrl.startsWith('/') ? avatarUrl : `/${avatarUrl}`}`;
}

