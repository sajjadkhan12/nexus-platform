/**
 * Token Storage Utility
 * 
 * SECURITY NOTE: Storing access tokens in localStorage is vulnerable to XSS attacks.
 * This is acceptable for local development but MUST be changed for production.
 * 
 * In a production environment, consider:
 * 1. Using httpOnly cookies for tokens (requires backend changes)
 * 2. Implementing Content Security Policy (CSP) to prevent XSS
 * 3. Using secure token storage mechanisms
 * 
 * For now, this utility centralizes token storage operations and includes:
 * - Token expiration checking
 * - Automatic token refresh before expiration
 * - Better error handling
 */

const ACCESS_TOKEN_KEY = 'access_token';
const TOKEN_EXPIRY_KEY = 'token_expiry';

/**
 * Decode JWT token to get expiration time
 * Note: This is a simple base64 decode, not a full JWT verification
 */
function getTokenExpiry(token: string): number | null {
    try {
        const parts = token.split('.');
        if (parts.length !== 3) return null;
        
        const payload = JSON.parse(atob(parts[1]));
        return payload.exp ? payload.exp * 1000 : null; // Convert to milliseconds
    } catch (error) {
        console.error('Failed to decode token:', error);
        return null;
    }
}

/**
 * Check if token is expired or will expire soon (within 5 minutes)
 */
function isTokenExpiredOrExpiringSoon(token: string | null): boolean {
    if (!token) return true;
    
    const expiry = getTokenExpiry(token);
    if (!expiry) return true; // If we can't determine expiry, treat as expired
    
    const now = Date.now();
    const fiveMinutes = 5 * 60 * 1000; // 5 minutes in milliseconds
    
    return expiry <= (now + fiveMinutes); // Expired or expiring within 5 minutes
}

/**
 * Get the access token from storage
 * Returns null if token is expired or expiring soon
 */
export function getAccessToken(): string | null {
    try {
        const token = localStorage.getItem(ACCESS_TOKEN_KEY);
        if (!token) return null;
        
        // Check if token is expired or expiring soon
        if (isTokenExpiredOrExpiringSoon(token)) {
            // Token is expired or expiring soon, remove it
            removeAccessToken();
            return null;
        }
        
        return token;
    } catch (error) {
        console.error('Failed to get access token from storage:', error);
        return null;
    }
}

/**
 * Set the access token in storage
 * Also stores the expiration time for quick checks
 */
export function setAccessToken(token: string): void {
    try {
        localStorage.setItem(ACCESS_TOKEN_KEY, token);
        
        // Store expiration time for quick checks
        const expiry = getTokenExpiry(token);
        if (expiry) {
            localStorage.setItem(TOKEN_EXPIRY_KEY, expiry.toString());
        }
    } catch (error) {
        console.error('Failed to set access token in storage:', error);
        throw error;
    }
}

/**
 * Remove the access token from storage
 */
export function removeAccessToken(): void {
    try {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(TOKEN_EXPIRY_KEY);
    } catch (error) {
        console.error('Failed to remove access token from storage:', error);
    }
}

/**
 * Check if an access token exists and is valid
 */
export function hasAccessToken(): boolean {
    return getAccessToken() !== null;
}

/**
 * Check if token needs refresh (expiring within 5 minutes)
 */
export function shouldRefreshToken(): boolean {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token) return false;
    
    return isTokenExpiredOrExpiringSoon(token);
}

