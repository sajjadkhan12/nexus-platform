import React from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';

interface PasswordStrengthProps {
    password: string;
}

interface StrengthCheck {
    label: string;
    passed: boolean;
}

export const PasswordStrength: React.FC<PasswordStrengthProps> = ({ password }) => {
    if (!password) return null;

    const checks: StrengthCheck[] = [
        {
            label: 'At least 12 characters',
            passed: password.length >= 12
        },
        {
            label: 'At least one uppercase letter',
            passed: /[A-Z]/.test(password)
        },
        {
            label: 'At least one lowercase letter',
            passed: /[a-z]/.test(password)
        },
        {
            label: 'At least one number',
            passed: /[0-9]/.test(password)
        },
        {
            label: 'At least one special character',
            passed: /[!@#$%^&*()\-_+=\[\]{}|;:,.<>?/~`]/.test(password)
        }
    ];

    const passedCount = checks.filter(c => c.passed).length;
    const strength = passedCount === checks.length ? 'strong' : passedCount >= 3 ? 'medium' : 'weak';
    
    const strengthColors = {
        weak: 'bg-red-500',
        medium: 'bg-yellow-500',
        strong: 'bg-green-500'
    };

    const strengthText = {
        weak: 'Weak',
        medium: 'Medium',
        strong: 'Strong'
    };

    return (
        <div className="mt-2 space-y-2">
            <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Password Strength:</span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                    strength === 'strong' ? 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/30' :
                    strength === 'medium' ? 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-950/30' :
                    'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30'
                }`}>
                    {strengthText[strength]}
                </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                <div 
                    className={`h-1.5 rounded-full transition-all duration-300 ${strengthColors[strength]}`}
                    style={{ width: `${(passedCount / checks.length) * 100}%` }}
                />
            </div>
            <div className="space-y-1.5 mt-2">
                {checks.map((check, index) => (
                    <div key={index} className="flex items-center gap-2 text-xs">
                        {check.passed ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
                        ) : (
                            <XCircle className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                        )}
                        <span className={check.passed ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'}>
                            {check.label}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
};

