import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null
        };
    }

    static getDerivedStateFromError(error: Error): State {
        return {
            hasError: true,
            error,
            errorInfo: null
        };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        // Log error to console in development
        if (import.meta.env.DEV) {
            console.error('ErrorBoundary caught an error:', error, errorInfo);
        }

        // In production, you could send this to an error tracking service
        // e.g., Sentry, LogRocket, etc.

        this.setState({
            error,
            errorInfo
        });
    }

    handleReset = () => {
        this.setState({
            hasError: false,
            error: null,
            errorInfo: null
        });
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
                    <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
                        <div className="flex items-center gap-3 mb-4">
                            <AlertCircle className="w-8 h-8 text-red-500" />
                            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                                Something went wrong
                            </h2>
                        </div>
                        
                        <p className="text-gray-600 dark:text-gray-400 mb-4">
                            An unexpected error occurred. Please try refreshing the page.
                        </p>

                        {import.meta.env.DEV && this.state.error && (
                            <details className="mb-4 p-3 bg-gray-100 dark:bg-gray-700 rounded text-xs font-mono overflow-auto max-h-48">
                                <summary className="cursor-pointer text-gray-700 dark:text-gray-300 mb-2">
                                    Error Details (Development Only)
                                </summary>
                                <div className="text-red-600 dark:text-red-400">
                                    <div className="font-semibold mb-1">{this.state.error.name}:</div>
                                    <div className="mb-2">{this.state.error.message}</div>
                                    {this.state.errorInfo && (
                                        <div className="text-gray-600 dark:text-gray-400 mt-2">
                                            <div className="font-semibold mb-1">Stack Trace:</div>
                                            <pre className="whitespace-pre-wrap">
                                                {this.state.errorInfo.componentStack}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            </details>
                        )}

                        <div className="flex gap-3">
                            <button
                                onClick={this.handleReset}
                                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors"
                            >
                                <RefreshCw className="w-4 h-4" />
                                Try Again
                            </button>
                            <button
                                onClick={() => window.location.href = '/'}
                                className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg transition-colors"
                            >
                                Go Home
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;

