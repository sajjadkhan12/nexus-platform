/**
 * Centralized API configuration
 * All API URLs should use this constant to ensure consistency
 */
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Get the base API URL
 * Use this instead of hardcoding URLs
 */
export function getApiUrl(): string {
    return API_URL;
}

/**
 * Build a full API URL from an endpoint
 */
export function buildApiUrl(endpoint: string): string {
    const baseUrl = API_URL.endsWith('/') ? API_URL.slice(0, -1) : API_URL;
    const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    return `${baseUrl}${path}`;
}

