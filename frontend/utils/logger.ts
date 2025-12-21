/**
 * Logger utility for frontend
 * Conditionally logs based on environment
 */
const isDevelopment = import.meta.env.DEV || import.meta.env.MODE === 'development';

export const appLogger = {
    log: (...args: any[]) => {
        if (isDevelopment) {
            console.log(...args);
        }
    },
    
    debug: (...args: any[]) => {
        if (isDevelopment) {
            console.debug(...args);
        }
    },
    
    error: (...args: any[]) => {
        // Always log errors, but in production, could send to error tracking service
        if (isDevelopment) {
            console.error(...args);
        } else {
            // In production, send to error tracking (e.g., Sentry)
            // For now, silently fail or send to API endpoint
            // TODO: Implement error tracking service
        }
    },
    
    warn: (...args: any[]) => {
        if (isDevelopment) {
            console.warn(...args);
        }
    },
    
    info: (...args: any[]) => {
        if (isDevelopment) {
            console.info(...args);
        }
    }
};

