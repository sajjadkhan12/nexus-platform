/**
 * Token Storage Utility
 * 
 * SECURITY NOTE: Storing access tokens in localStorage is vulnerable to XSS attacks.
 * In a production environment, consider:
 * 1. Using httpOnly cookies for tokens (requires backend changes)
 * 2. Implementing Content Security Policy (CSP) to prevent XSS
 * 3. Using secure token storage mechanisms
 * 
 * For now, this utility centralizes token storage operations to make future migration easier.
 */

const ACCESS_TOKEN_KEY = 'access_token';

/**
 * Get the access token from storage
 */
export function getAccessToken(): string | null {
    try {
        return localStorage.getItem(ACCESS_TOKEN_KEY);
    } catch (error) {
        console.error('Failed to get access token from storage:', error);
        return null;
    }
}

/**
 * Set the access token in storage
 */
export function setAccessToken(token: string): void {
    try {
        localStorage.setItem(ACCESS_TOKEN_KEY, token);
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
    } catch (error) {
        console.error('Failed to remove access token from storage:', error);
    }
}

/**
 * Check if an access token exists
 */
export function hasAccessToken(): boolean {
    return getAccessToken() !== null;
}

