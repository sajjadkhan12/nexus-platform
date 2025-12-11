/**
 * Token Utilities
 * Handles JWT token parsing and expiration checking
 */

interface JWTPayload {
    sub: string;
    exp: number;
    iat?: number;
    type?: string;
}

/**
 * Decode JWT token without verification (client-side only)
 * Note: This doesn't verify the signature - that's done by the server
 */
export function decodeToken(token: string): JWTPayload | null {
    try {
        const parts = token.split('.');
        if (parts.length !== 3) {
            return null;
        }
        
        const payload = parts[1];
        const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
        return JSON.parse(decoded);
    } catch (error) {
        console.error('Failed to decode token:', error);
        return null;
    }
}

/**
 * Check if a token is expired
 */
export function isTokenExpired(token: string): boolean {
    const payload = decodeToken(token);
    if (!payload || !payload.exp) {
        return true;
    }
    
    // Add 60 second buffer to refresh before actual expiration
    const expirationTime = payload.exp * 1000; // Convert to milliseconds
    const bufferTime = 60 * 1000; // 60 seconds
    return Date.now() >= (expirationTime - bufferTime);
}

/**
 * Get time until token expiration in milliseconds
 */
export function getTokenExpirationTime(token: string): number | null {
    const payload = decodeToken(token);
    if (!payload || !payload.exp) {
        return null;
    }
    
    const expirationTime = payload.exp * 1000; // Convert to milliseconds
    return expirationTime - Date.now();
}

/**
 * Check if token will expire soon (within 5 minutes)
 */
export function isTokenExpiringSoon(token: string, minutes: number = 5): boolean {
    const timeUntilExpiration = getTokenExpirationTime(token);
    if (timeUntilExpiration === null) {
        return true;
    }
    
    return timeUntilExpiration <= (minutes * 60 * 1000);
}

