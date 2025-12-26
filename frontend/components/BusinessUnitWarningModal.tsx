import React from 'react';
import { X, Building2, AlertTriangle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface BusinessUnitWarningModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSelectBusinessUnit: () => void;
    action: string; // e.g., "deploy", "update deployment"
}

export const BusinessUnitWarningModal: React.FC<BusinessUnitWarningModalProps> = ({
    isOpen,
    onClose,
    onSelectBusinessUnit,
    action
}) => {
    const { businessUnits, hasBusinessUnitAccess } = useAuth();

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-md w-full mx-4 border border-gray-200 dark:border-gray-800">
                <div className="p-6">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                                <AlertTriangle className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                            </div>
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                Business Unit Required
                            </h3>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                        >
                            <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="space-y-4">
                        <p className="text-gray-600 dark:text-gray-400">
                            You need to select a business unit before you can {action}. Business units help organize and separate infrastructure deployments within Foundry.
                        </p>

                        {!hasBusinessUnitAccess ? (
                            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                                <p className="text-sm text-yellow-800 dark:text-yellow-200">
                                    You don't have access to any business units yet. Please contact an administrator to be added to a business unit.
                                </p>
                            </div>
                        ) : businessUnits.length > 0 ? (
                            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                                <p className="text-sm text-blue-800 dark:text-blue-200 mb-2">
                                    Please select a business unit from the dropdown in the header to continue.
                                </p>
                                <button
                                    onClick={() => {
                                        onSelectBusinessUnit();
                                        onClose();
                                    }}
                                    className="w-full mt-3 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                                >
                                    <Building2 className="w-4 h-4" />
                                    Business Unit
                                </button>
                            </div>
                        ) : null}
                    </div>

                    {/* Footer */}
                    <div className="mt-6 flex justify-end gap-3">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors font-medium"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

