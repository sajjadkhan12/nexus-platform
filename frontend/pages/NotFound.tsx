import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, ArrowLeft, Search } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
            <div className="max-w-lg w-full text-center">
                {/* 404 Illustration */}
                <div className="relative mb-8">
                    <div className="absolute inset-0 flex items-center justify-center opacity-10 dark:opacity-5">
                        <span className="text-[12rem] font-bold text-orange-600">404</span>
                    </div>
                    <div className="relative z-10">
                        <div className="w-24 h-24 bg-orange-100 dark:bg-orange-900/30 rounded-full flex items-center justify-center mx-auto mb-6 animate-bounce">
                            <Search className="w-10 h-10 text-orange-600 dark:text-orange-400" />
                        </div>
                        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">Page Not Found</h1>
                        <p className="text-gray-500 dark:text-gray-400 text-lg">
                            Oops! The page you're looking for seems to have wandered off into the digital void.
                        </p>
                    </div>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                    <button
                        onClick={() => navigate(-1)}
                        className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors font-medium shadow-sm"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Go Back
                    </button>
                    <button
                        onClick={() => navigate('/')}
                        className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3 bg-orange-600 hover:bg-orange-700 text-white rounded-xl transition-colors font-medium shadow-lg shadow-orange-500/20"
                    >
                        <Home className="w-4 h-4" />
                        Back to Home
                    </button>
                </div>

                {/* Footer Message */}
                <p className="mt-12 text-sm text-gray-400 dark:text-gray-600">
                    Error Code: 404 • Resource Not Found
                </p>
            </div>
        </div>
    );
};
